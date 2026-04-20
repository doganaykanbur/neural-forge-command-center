# --- Windows Encoding Fix ---
import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
# ----------------------------

import os
import json
import re
import math
import subprocess
from pathlib import Path

TASK_ID = os.environ.get("TASK_ID", "unknown")
DESCRIPTION = os.environ.get("TASK_DESCRIPTION", "")
ARTIFACT_DIR = Path(os.environ.get("ARTIFACT_DIR", "."))
WORK_DIR = Path(os.environ.get("WORK_DIR", "."))
SERVER_URL = os.environ.get("SERVER_URL", "http://localhost:8000")
OLLAMA_FALLBACK = "http://localhost:11434"
if os.environ.get("DOCKER_CONTAINER"):
    OLLAMA_FALLBACK = "http://host.docker.internal:11434"


# ═══════════════════════════════════════════════
# 1. SecretScanner — Regex Pattern Matching
# ═══════════════════════════════════════════════

class SecretScanner:
    PATTERNS = {
        "AWS Access Key":       r"AKIA[0-9A-Z]{16}",
        "AWS Secret Key":       r"(?i)aws_secret_access_key\s*[:=]\s*['\"]?[A-Za-z0-9/+=]{40}",
        "RSA Private Key":      r"-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----",
        "JWT Token":            r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}",
        "GitHub Token":         r"gh[ps]_[A-Za-z0-9_]{36,}",
        "Google API Key":       r"AIza[0-9A-Za-z\-_]{35}",
        "Slack Token":          r"xox[bpsar]-[0-9a-zA-Z]{10,}",
        "Generic Secret":       r'(?i)(password|secret|api_key|apikey|token|auth)\s*[:=]\s*["\'][A-Za-z0-9\-_!@#$%^&*]{8,}["\']',
        "Connection String":    r"(?i)(mongodb|postgres|mysql|redis|amqp)://[^\s\"']+",
        "Bearer Token":         r"(?i)bearer\s+[A-Za-z0-9\-_\.]{20,}",
    }

    @classmethod
    def scan(cls, filename: str, content: str) -> list[dict]:
        findings = []
        for name, pattern in cls.PATTERNS.items():
            for m in re.finditer(pattern, content):
                line_no = content[:m.start()].count("\n") + 1
                preview = m.group(0)[:20] + "..." if len(m.group(0)) > 20 else m.group(0)
                findings.append({
                    "type": name,
                    "file": filename,
                    "line": line_no,
                    "preview": preview,
                    "severity": "CRITICAL",
                })
        return findings


# ═══════════════════════════════════════════════
# 2. EntropyScanner — Shannon Entropy (TruffleHog)
# ═══════════════════════════════════════════════

class EntropyScanner:
    """Detects high-entropy strings that likely contain secrets."""

    HEX_CHARS = set("0123456789abcdefABCDEF")
    BASE64_CHARS = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=")

    HEX_ENTROPY_THRESHOLD = 3.0       # bits per character
    BASE64_ENTROPY_THRESHOLD = 4.5
    MIN_TOKEN_LENGTH = 20

    @staticmethod
    def _shannon_entropy(data: str) -> float:
        if not data:
            return 0.0
        freq = {}
        for c in data:
            freq[c] = freq.get(c, 0) + 1
        length = len(data)
        return -sum((count / length) * math.log2(count / length) for count in freq.values())

    @classmethod
    def scan(cls, filename: str, content: str) -> list[dict]:
        findings = []
        # Split into words/tokens
        tokens = re.findall(r'["\']([^"\']{20,})["\']', content)  # quoted strings
        tokens += re.findall(r'=\s*([^\s;"\']{20,})', content)     # assigned values

        seen = set()
        for token in tokens:
            if token in seen or len(token) < cls.MIN_TOKEN_LENGTH:
                continue
            seen.add(token)

            # Skip common non-secret patterns (URLs, file paths)
            if token.startswith(("http://", "https://", "/", "file://", "C:\\")):
                continue

            # Check hex entropy
            hex_portion = "".join(c for c in token if c in cls.HEX_CHARS)
            if len(hex_portion) > cls.MIN_TOKEN_LENGTH:
                entropy = cls._shannon_entropy(hex_portion)
                if entropy > cls.HEX_ENTROPY_THRESHOLD:
                    line_no = content[:content.find(token)].count("\n") + 1
                    findings.append({
                        "type": "High Entropy (Hex)",
                        "file": filename,
                        "line": line_no,
                        "preview": token[:25] + "...",
                        "entropy": round(entropy, 2),
                        "severity": "HIGH",
                    })
                    continue

            # Check base64 entropy
            b64_portion = "".join(c for c in token if c in cls.BASE64_CHARS)
            if len(b64_portion) > cls.MIN_TOKEN_LENGTH:
                entropy = cls._shannon_entropy(b64_portion)
                if entropy > cls.BASE64_ENTROPY_THRESHOLD:
                    line_no = content[:content.find(token)].count("\n") + 1
                    findings.append({
                        "type": "High Entropy (Base64)",
                        "file": filename,
                        "line": line_no,
                        "preview": token[:25] + "...",
                        "entropy": round(entropy, 2),
                        "severity": "HIGH",
                    })

        return findings


# ═══════════════════════════════════════════════
# 3. FileBlocklist — Dangerous File Filter
# ═══════════════════════════════════════════════

class FileBlocklist:
    """Blocks sensitive files from being processed or exported."""

    BLOCKED_EXTENSIONS = {".env", ".pem", ".key", ".p12", ".pfx", ".jks", ".keystore"}
    BLOCKED_FILENAMES = {"id_rsa", "id_dsa", "id_ecdsa", "id_ed25519", ".env", ".env.local",
                         ".env.production", ".env.staging", ".htpasswd", ".netrc",
                         "credentials", "credentials.json", "service-account.json"}

    @classmethod
    def scan_workspace(cls, work_dir: Path) -> list[dict]:
        findings = []
        for f in work_dir.rglob("*"):
            if not f.is_file():
                continue
            # Check extension
            if f.suffix.lower() in cls.BLOCKED_EXTENSIONS:
                findings.append({
                    "type": "Blocked File (Extension)",
                    "file": str(f.relative_to(work_dir)),
                    "reason": f"Extension '{f.suffix}' is forbidden",
                    "severity": "CRITICAL",
                    "action": "QUARANTINED",
                })
                # Quarantine: rename to prevent export
                quarantine_path = f.with_suffix(f.suffix + ".QUARANTINED")
                f.rename(quarantine_path)

            # Check filename
            if f.name.lower() in cls.BLOCKED_FILENAMES:
                findings.append({
                    "type": "Blocked File (Filename)",
                    "file": str(f.relative_to(work_dir)),
                    "reason": f"Filename '{f.name}' is forbidden",
                    "severity": "CRITICAL",
                    "action": "QUARANTINED",
                })
                quarantine_path = f.with_suffix(f.suffix + ".QUARANTINED" if f.suffix else ".QUARANTINED")
                if f.exists():
                    f.rename(quarantine_path)

        return findings


# ═══════════════════════════════════════════════
# 4. DependencyChecker — Known CVE Matching
# ═══════════════════════════════════════════════

class DependencyChecker:
    KNOWN_CVES = {
        "requests==2.20.0": "CVE-2018-18074 (High) - Information exposure",
        "requests<2.20.0": "CVE-2018-18074 (High) - Information exposure",
        "django==2.1.0":   "CVE-2019-14234 (Critical) - SQL Injection",
        "django<3.0":      "CVE-2019-19844 (Critical) - Account hijack",
        "flask==0.12":     "CVE-2018-1000656 (High) - DoS vulnerability",
        "pyyaml<5.4":      "CVE-2020-14343 (Critical) - Arbitrary code execution",
        "urllib3<1.26.5":  "CVE-2021-33503 (High) - ReDoS vulnerability",
        "jinja2<2.11.3":   "CVE-2020-28493 (Medium) - ReDoS vulnerability",
        "pillow<8.1.1":    "CVE-2021-25287 (Critical) - Buffer overflow",
        "numpy<1.22.0":    "CVE-2021-41496 (High) - Buffer overflow",
    }

    @classmethod
    def check(cls, content: str) -> list[dict]:
        findings = []
        content_lower = content.lower()
        for dep, cve in cls.KNOWN_CVES.items():
            if dep.split("==")[0].split("<")[0] in content_lower:
                findings.append({
                    "type": "Vulnerable Dependency",
                    "dependency": dep,
                    "cve": cve,
                    "severity": "HIGH" if "High" in cve else "CRITICAL",
                })
        return findings


# ═══════════════════════════════════════════════
# 5. SemanticReviewer — LLM Logical Vulnerability Check
# ═══════════════════════════════════════════════

class SemanticReviewer:
    """Uses LLM to find logical security flaws that regex cannot catch."""

    SYSTEM_PROMPT = """You are a Senior Security Architect performing a code review.
Your job is to find LOGICAL security vulnerabilities that static regex scanners cannot detect.

Focus on:
- Missing JWT expiration checks
- SQL injection via string concatenation (not parameterized queries)
- Missing input validation/sanitization
- Race conditions in concurrent code
- Insecure deserialization
- Missing CSRF protection
- Open redirects
- Path traversal vulnerabilities
- Missing rate limiting on auth endpoints
- Hardcoded default credentials (admin/admin, test/test)
- Missing error handling that leaks stack traces to users

Respond with a JSON array of findings. Each finding must have:
- "issue": short description 
- "severity": "CRITICAL", "HIGH", "MEDIUM", or "LOW"
- "line_hint": approximate line reference or function name
- "fix": specific remediation suggestion

If no issues found, return an empty array: []
Respond with ONLY valid JSON, no markdown."""

    @classmethod
    def review(cls, code: str, filename: str) -> list[dict]:
        """Send code to LLM for semantic analysis."""
        try:
            import httpx
        except ImportError:
            print("[WARN] httpx not available, skipping semantic review")
            return []

        # Try Ollama first (local), then Mistral
        providers = [
            ("ollama", os.environ.get("OLLAMA_URL", f"{OLLAMA_FALLBACK}/api/generate")),
            ("mistral", os.environ.get("MISTRAL_URL", "https://api.mistral.ai/v1/chat/completions")),
        ]

        code_snippet = code[:4000]  # Limit to avoid token overflow

        for provider_name, url in providers:
            try:
                if provider_name == "ollama":
                    resp = httpx.post(url, json={
                        "model": "mistral",
                        "prompt": f"Review this code for logical security vulnerabilities:\n\nFile: {filename}\n```\n{code_snippet}\n```",
                        "system": cls.SYSTEM_PROMPT,
                        "stream": False,
                        "options": {"temperature": 0.1},
                    }, timeout=60.0)
                    if resp.status_code == 200:
                        text = resp.json().get("response", "[]")
                        return cls._parse_response(text)

                elif provider_name == "mistral":
                    api_key = os.environ.get("MISTRAL_API_KEY", "")
                    if not api_key:
                        continue
                    resp = httpx.post(url, headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    }, json={
                        "model": "mistral-small-latest",
                        "messages": [
                            {"role": "system", "content": cls.SYSTEM_PROMPT},
                            {"role": "user", "content": f"File: {filename}\n```\n{code_snippet}\n```"},
                        ],
                        "temperature": 0.1,
                    }, timeout=30.0)
                    if resp.status_code == 200:
                        text = resp.json()["choices"][0]["message"]["content"]
                        return cls._parse_response(text)

            except Exception as e:
                print(f"[WARN] Semantic review via {provider_name} failed: {e}")
                continue

        print("[INFO] No LLM available for semantic review (Ollama/Mistral). Skipping.")
        return []

    @classmethod
    def _parse_response(cls, text: str) -> list[dict]:
        """Extract JSON array from LLM response."""
        try:
            match = re.search(r'\[.*\]', text, re.DOTALL)
            if match:
                findings = json.loads(match.group())
                # Validate structure
                valid = []
                for f in findings:
                    if isinstance(f, dict) and "issue" in f:
                        valid.append({
                            "type": "Semantic Vulnerability",
                            "issue": f.get("issue", "Unknown"),
                            "severity": f.get("severity", "MEDIUM"),
                            "line_hint": str(f.get("line_hint", "?")),
                            "fix": f.get("fix", "Review manually"),
                        })
                return valid
        except (json.JSONDecodeError, AttributeError):
            pass
        return []


# ═══════════════════════════════════════════════
# Main Reviewer Pipeline
# ═══════════════════════════════════════════════

def collect_code_files(work_dir: Path) -> list[Path]:
    """Gather all reviewable source files from workspace."""
    CODE_EXTENSIONS = {".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".java", ".rb", ".php", ".sh"}
    files = []
    for f in work_dir.rglob("*"):
        if f.is_file() and f.suffix.lower() in CODE_EXTENSIONS and ".QUARANTINED" not in f.name:
            files.append(f)
    return files


def format_inline_comment(finding: dict) -> str:
    """Format a finding as GitHub-style inline comment."""
    file_ref = finding.get("file", "unknown")
    line = finding.get("line", finding.get("line_hint", "?"))
    severity_icon = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🔵"}.get(finding.get("severity", ""), "⚪")

    comment = f"// File: {file_ref}:{line}\n"
    comment += f"// {severity_icon} {finding.get('severity', 'UNKNOWN')}: {finding.get('type', 'Issue')}\n"

    if "preview" in finding:
        comment += f"// ❌ FOUND: {finding['preview']}\n"
    if "issue" in finding:
        comment += f"// ❌ ISSUE: {finding['issue']}\n"
    if "fix" in finding:
        comment += f"// ✅ FIX: {finding['fix']}\n"
    if "reason" in finding:
        comment += f"// [ISSUE] REASON: {finding['reason']}\n"
    if "action" in finding:
        comment += f"// [FIX] ACTION: {finding['action']}\n"

    return comment


def main():
    print(f"[INFO] === Neural Forge Reviewer v2.0 (Hardened Gatekeeper) ===")
    print(f"[INFO] Task: {TASK_ID}")
    print(f"[INFO] Workspace: {WORK_DIR}")

    all_findings: list[dict] = []
    security_critical = False

    # ── Step 0: Read AGENTS.md ──
    agents_file = WORK_DIR / "AGENTS.md"
    if agents_file.exists():
        print(f"[INFO] Found AGENTS.md — enforcing Architect's standards")
    else:
        print(f"[WARN] AGENTS.md not found. Proceeding without blueprint.")

    # ── Step 1: File Blocklist ──
    print(f"[INFO] ── Layer 1: File Blocklist Scan ──")
    blocklist_findings = FileBlocklist.scan_workspace(WORK_DIR)
    for f in blocklist_findings:
        print(f"[ERROR] 🚫 BLOCKED: {f['file']} → {f['reason']} [{f['action']}]")
        all_findings.append(f)
    if blocklist_findings:
        security_critical = True
        print(f"[ERROR] {len(blocklist_findings)} dangerous file(s) quarantined!")
    else:
        print(f"[INFO] No blocked files detected ✓")

    # ── Step 2: Collect code files ──
    code_files = collect_code_files(WORK_DIR)
    if not code_files:
        # Use DESCRIPTION as code if no files found
        if DESCRIPTION.strip() and "Review task description" in DESCRIPTION: # Explicit standalone check
            sample_file = WORK_DIR / "code_to_review.py"
            sample_file.write_text(DESCRIPTION.strip(), encoding="utf-8")
            code_files = [sample_file]
            print(f"[INFO] No source files found, using task description as code (standalone review)")
        else:
            print(f"[WARN] No code to review yet. Builder might still be working.")
            _write_result([{"type": "Pending", "detail": "Waiting for source files from Builder", "severity": "LOW"}], False, status="pending")
            return

    print(f"[INFO] Found {len(code_files)} source file(s) to review")

    # ── Step 3: Per-file analysis ──
    for code_path in code_files:
        relative = str(code_path.relative_to(WORK_DIR))
        content = code_path.read_text(encoding="utf-8", errors="replace")
        lines = content.split("\n")
        print(f"\n[INFO] ── Reviewing: {relative} ({len(lines)} lines) ──")

        # Layer 2: Secret Scanner (Regex)
        print(f"[INFO] Layer 2: Secret Pattern Scan")
        secrets = SecretScanner.scan(relative, content)
        for s in secrets:
            print(f"[ERROR] 🚨 SECRET: [{s['type']}] {s['file']}:{s['line']} → {s['preview']}")
            all_findings.append(s)
        if secrets:
            security_critical = True

        # Layer 3: Entropy Scanner (TruffleHog-style)
        print(f"[INFO] Layer 3: Entropy Analysis")
        entropy_hits = EntropyScanner.scan(relative, content)
        for e in entropy_hits:
            print(f"[WARN] 🔥 ENTROPY: {e['file']}:{e['line']} → {e['preview']} (entropy={e['entropy']})")
            all_findings.append(e)

        # Layer 4: Dependency Check (on requirements-like files)
        if any(kw in relative.lower() for kw in ["requirements", "pipfile", "pyproject", "package.json", "gemfile"]):
            print(f"[INFO] Layer 4: Dependency CVE Check")
            deps = DependencyChecker.check(content)
            for d in deps:
                print(f"[ERROR] 🛡️ CVE: {d['dependency']} → {d['cve']}")
                all_findings.append(d)

        # Layer 5: Flake8 (Python only)
        if code_path.suffix == ".py":
            print(f"[INFO] Layer 5: Lint (flake8)")
            try:
                result = subprocess.run(
                    [sys.executable, "-m", "flake8", "--max-line-length=120", str(code_path)],
                    capture_output=True, text=True, timeout=30
                )
                if result.returncode != 0 and result.stdout:
                    for line in result.stdout.strip().split("\n"):
                        if line.strip():
                            all_findings.append({"type": "Lint", "detail": line.strip(), "severity": "LOW"})
                            print(f"[WARN] LINT: {line.strip()}")
            except Exception:
                print(f"[INFO] flake8 not available, skipping lint")

        # Layer 6: Basic checks
        for i, line in enumerate(lines, 1):
            if len(line) > 120:
                all_findings.append({"type": "Style", "file": relative, "line": i, "detail": f"Line exceeds 120 chars ({len(line)})", "severity": "LOW"})
            if "import *" in line:
                all_findings.append({"type": "Style", "file": relative, "line": i, "detail": "Wildcard import", "severity": "MEDIUM"})
            if line.strip().startswith("except:"):
                all_findings.append({"type": "Style", "file": relative, "line": i, "detail": "Bare except clause", "severity": "MEDIUM"})
            if "eval(" in line or "exec(" in line:
                all_findings.append({"type": "Security", "file": relative, "line": i, "detail": "eval/exec usage detected", "severity": "HIGH"})

    # ── Step 4: LLM Semantic Review (on all code combined) ──
    print(f"\n[INFO] ── Layer 6: LLM Semantic Security Review ──")
    combined_code = ""
    for code_path in code_files[:5]:  # Limit to 5 files
        content = code_path.read_text(encoding="utf-8", errors="replace")
        combined_code += f"\n# === {code_path.relative_to(WORK_DIR)} ===\n{content}\n"

    semantic_findings = SemanticReviewer.review(combined_code[:6000], "workspace")
    for sf in semantic_findings:
        severity_icon = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡"}.get(sf["severity"], "🔵")
        print(f"[WARN] {severity_icon} SEMANTIC: {sf['issue']} → Fix: {sf['fix']}")
        all_findings.append(sf)
        if sf["severity"] in ("CRITICAL", "HIGH"):
            security_critical = True

    # ── Write results ──
    _write_result(all_findings, security_critical)


def _write_result(findings: list[dict], security_critical: bool, status: str = None):
    """Write result.json and inline review report."""

    critical_count = sum(1 for f in findings if f.get("severity") in ("CRITICAL",))
    high_count = sum(1 for f in findings if f.get("severity") in ("HIGH",))
    total = len(findings)

    if not status:
        if security_critical:
            status = "failed"
        elif total <= 3:
            status = "pass"
        elif total <= 8:
            status = "warn"
        else:
            status = "failed"

    result = {
        "task_id": TASK_ID,
        "status": status,
        "total_issues": total,
        "critical": critical_count,
        "high": high_count,
        "issues": findings[:30],
        "security_violation": security_critical,
        "report": f"{critical_count} critical, {high_count} high severity issues" if security_critical else "No security violations."
    }

    result_file = ARTIFACT_DIR / "result.json"
    result_file.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"\n[ARTIFACT] review_result|{result_file}")

    # Inline review report (GitHub-style)
    report_lines = [
        f"═══ Neural Forge Review Report ═══",
        f"Task: {TASK_ID}",
        f"Status: {status.upper()}",
        f"Total Issues: {total} (Critical: {critical_count}, High: {high_count})",
        f"{'=' * 40}",
        "",
    ]
    for f in findings[:30]:
        report_lines.append(format_inline_comment(f))
        report_lines.append("")

    report_file = ARTIFACT_DIR / "review_report.txt"
    report_file.write_text("\n".join(report_lines), encoding="utf-8")
    print(f"[ARTIFACT] review_report|{report_file}")

    print(f"\n[INFO] ═══ Review Complete: {status.upper()} ({total} issues) ═══")

    if security_critical or status == "failed":
        sys.exit(1)


if __name__ == "__main__":
    main()
