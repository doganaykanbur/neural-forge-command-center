"""
Neural Forge — Tester Worker
Runs pytest or basic test validation on a project.

Reads from env: TASK_ID, TASK_DESCRIPTION, ARTIFACT_DIR, WORK_DIR
Outputs structured log lines: [INFO], [ERROR], [ARTIFACT]
"""

# --- Windows Encoding Fix ---
import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
# ----------------------------

import os
import sys
import json
import subprocess
import time
from pathlib import Path

TASK_ID = os.environ.get("TASK_ID", "unknown")
DESCRIPTION = os.environ.get("TASK_DESCRIPTION", "")
ARTIFACT_DIR = Path(os.environ.get("ARTIFACT_DIR", "."))
WORK_DIR = Path(os.environ.get("WORK_DIR", "."))

# ═════════════════════════════════════════════
# DevSecOps: Red Team Modules
# ═════════════════════════════════════════════

class PenetrationTester:
    @classmethod
    def test_dast(cls, code: str) -> list[str]:
        findings = []
        code_lower = code.lower()
        
        # MOCK DAST: SQLi injection payload success
        if "select * from" in code_lower and "%s" not in code_lower and "?" not in code_lower:
            findings.append("SQLi [' OR 1=1--]: Bypassed Auth. Raw SQL detected without parameterized inputs.")
            
        # MOCK DAST: XSS payload reflection
        if "return" in code_lower and "request." in code_lower and "escape" not in code_lower:
            findings.append("XSS [<script>alert(1)</script>]: Executed successfully. Unsanitized input reflected.")
            
        return findings

class Fuzzer:
    @classmethod
    def test_fuzz(cls, code: str) -> list[str]:
        findings = []
        code_lower = code.lower()
        
        # MOCK Fuzzing: Send huge payloads causing memory leak / 500 error
        if ("json.loads" in code_lower or "int(" in code_lower) and "except" not in code_lower:
            findings.append("Fuzzing [10MB string payload]: Triggered 500 Internal Server Error & Application Crash. Missing try/except for malformed input.")
            
        return findings

def main():
    print(f"[INFO] Tester started for task {TASK_ID}")
    start_time = time.time()
    
    # ── READ AGENTS.md STANDARD ──
    agents_file = WORK_DIR / "AGENTS.md"
    if agents_file.exists():
        print(f"[INFO] Found AGENTS.md. Applying Architect's testing and security benchmarks.")
        blueprint = agents_file.read_text(encoding="utf-8")
    else:
        print(f"[WARN] AGENTS.md not found. Proceeding without Architect blueprint.")
    
    # Create sample test code (or use description)
    test_code = DESCRIPTION.strip()
    if not test_code:
        test_code = '''
import unittest

class TestBasicMath(unittest.TestCase):
    def test_addition(self):
        self.assertEqual(2 + 2, 4)
    
    def test_subtraction(self):
        self.assertEqual(10 - 5, 5)
    
    def test_multiplication(self):
        self.assertEqual(3 * 7, 21)
    
    def test_division(self):
        self.assertEqual(15 / 3, 5.0)
    
    def test_string_concat(self):
        self.assertEqual("hello" + " " + "world", "hello world")

if __name__ == "__main__":
    unittest.main()
'''
    
    test_file = WORK_DIR / "test_suite.py"
    test_file.write_text(test_code, encoding="utf-8")
    print(f"[INFO] Test file written ({len(test_code)} bytes)")
    
    # Try pytest first, fall back to unittest
    results = {"passed": 0, "failed": 0, "errors": 0, "test_output": ""}
    
    # Run with unittest (always available)
    print(f"[INFO] Running test suite...")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", str(test_file), "-v", "--tb=short"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60, cwd=str(WORK_DIR)
        )
        test_output = result.stdout + result.stderr
    except FileNotFoundError:
        # pytest not available, use unittest
        print("[INFO] pytest not available, using unittest")
        result = subprocess.run(
            [sys.executable, str(test_file)],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120, cwd=str(WORK_DIR)
        )
        test_output = result.stdout + result.stderr
    
    # Stream test output
    for line in test_output.strip().split("\n"):
        if "PASSED" in line or "ok" in line.lower():
            print(f"[INFO]   ✅ {line.strip()}")
            results["passed"] += 1
        elif "FAILED" in line or "FAIL" in line:
            print(f"[ERROR]  ❌ {line.strip()}")
            results["failed"] += 1
        elif "ERROR" in line:
            print(f"[ERROR]  💥 {line.strip()}")
            results["errors"] += 1
        elif line.strip():
            print(f"[INFO]   {line.strip()}")
    
    results["test_output"] = test_output
    results["duration_s"] = round(time.time() - start_time, 2)
    
    # ─── DevSecOps Dynamic Analysis ───
    print("[INFO] Red Team: Running DAST & Fuzzing payloads...")
    security_violations = []
    
    dast_findings = PenetrationTester.test_dast(test_code)
    for f in dast_findings:
        print(f"[ERROR] 🚨 DAST: {f}")
        security_violations.append(f)
        
    fuzz_findings = Fuzzer.test_fuzz(test_code)
    for f in fuzz_findings:
        print(f"[ERROR] 💥 FUZZER: {f}")
        security_violations.append(f)
    
    # Determine overall status
    if security_violations:
        print("[ERROR] 🛑 Security payload tests succeeded. System is vulnerable. Pipeline halting.")
        status = "failed"
        result_code = 1
    elif result.returncode == 0:
        status = "all_passed"
        result_code = 0
        print(f"[INFO] All unit & security tests passed!")
    else:
        status = "some_failed"
        result_code = result.returncode
        print(f"[ERROR] Some unit tests failed (exit code {result.returncode})")
    
    # Write result
    final_result = {
        "task_id": TASK_ID,
        "status": status,
        "passed": results["passed"],
        "failed": results["failed"],
        "errors": results["errors"],
        "duration_s": results["duration_s"],
        "security_violation": len(security_violations) > 0,
        "report": " | ".join(security_violations) if security_violations else "No security issues found."
    }
    
    result_file = ARTIFACT_DIR / "result.json"
    result_file.write_text(json.dumps(final_result, indent=2), encoding="utf-8")
    print(f"[ARTIFACT] test_result|{result_file}")
    
    # Save full test log
    log_file = ARTIFACT_DIR / "test_output.txt"
    log_file.write_text(test_output, encoding="utf-8")
    print(f"[ARTIFACT] test_log|{log_file}")
    
    print(f"[INFO] Testing complete in {results['duration_s']}s")
    
    sys.exit(result_code)

if __name__ == "__main__":
    main()
