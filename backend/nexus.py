"""
Neural Forge — NEXUS Memory Manager
Reads and writes the modular memory system (.nexus/rules/).
"""

import os
from datetime import datetime, timezone
from pathlib import Path

# Default NEXUS directory (relative to project root)
PROJECT_ROOT = Path(r"c:\Users\doganay\.gemini\antigravity\scratch\neural_forge_command_center")
def get_default_nexus_dir() -> Path:
    # 1. Environment Variable
    env_dir = os.environ.get("NEXUS_DIR")
    if env_dir:
        return Path(env_dir)
    
    # 2. Local relative check (if in the actual source tree)
    local_dir = Path(__file__).parent.parent / ".nexus" / "rules"
    if local_dir.exists():
        return local_dir
    
    # 3. Absolute Fallback (for transient/isolated task environments)
    fallback = PROJECT_ROOT / ".nexus" / "rules"
    print(f"DEBUG: Nexus fallback selected: {fallback}")
    return fallback


class NexusMemory:
    """
    Manager for the NEXUS modular memory system.
    Phase 12: Distilled Memory Pattern (MEMORY.md + Topic Tags).
    """

    INDEX_FILE = "MEMORY.md"
    CORE_FILE = "NEXUS_CORE.md"

    def __init__(self, nexus_dir: Path | str | None = None):
        self.nexus_dir = Path(nexus_dir) if nexus_dir else get_default_nexus_dir()
        self.nexus_dir.mkdir(parents=True, exist_ok=True)
        # Ensure base files exist
        if not (self.nexus_dir / self.INDEX_FILE).exists():
            self._write_file(self.INDEX_FILE, "# NEXUS MEMORY INDEX\n- [Profile](profile.md) — Base system identity\n- [Core](NEXUS_CORE.md) — Routing map\n")
        if not (self.nexus_dir / self.CORE_FILE).exists():
            self._write_file(self.CORE_FILE, "## System Capabilities\n- Build/Review/Test/Execute pipeline\n- Multi-worker orchestration\n")

    def _read_file(self, filename: str) -> str:
        path = self.nexus_dir / filename
        if path.exists():
            return path.read_text(encoding="utf-8")
        return ""

    def _write_file(self, filename: str, content: str) -> None:
        path = self.nexus_dir / filename
        path.write_text(content, encoding="utf-8")

    def _append_file(self, filename: str, line: str) -> None:
        path = self.nexus_dir / filename
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"\n{line}")

    def get_index(self) -> str:
        """Get the MEMORY.md index."""
        return self._read_file(self.INDEX_FILE)

    def get_core(self) -> str:
        return self._read_file(self.CORE_FILE)

    def get_decisions(self) -> str:
        return self._read_file("decisions.md")

    def get_preferences(self) -> str:
        return self._read_file("preferences.md")

    def get_full_memory(self) -> dict[str, str]:
        """Read all known memory files into a dict."""
        result = {}
        for path in self.nexus_dir.glob("*.md"):
            result[path.name] = path.read_text(encoding="utf-8")
        return result

    def get_context(self, topic: str = "general") -> str:
        """
        Phase 12: Dynamic Context Selection.
        1. Reads MEMORY.md (Index) for orientation.
        2. Loads topic-specific files based on keywords.
        """
        parts = []
        parts.append(f"## NEXUS CORE\n{self.get_core()}")
        
        index = self.get_index()
        parts.append(f"## MEMORY INDEX (MEMORY.md)\n{index}")

        # Map topics to files dynamically based on keywords in both the goal and the index
        topic_lower = topic.lower()
        files_to_load = set()
        
        # Standard mappings
        if any(kw in topic_lower for kw in ["review", "code", "quality", "standard"]):
            files_to_load.add("preferences.md")
        if any(kw in topic_lower for kw in ["build", "deploy", "stack", "tech"]):
            files_to_load.add("profile.md")
            files_to_load.add("preferences.md")
        if any(kw in topic_lower for kw in ["decision", "architect", "design"]):
            files_to_load.add("decisions.md")
        if any(kw in topic_lower for kw in ["history", "session", "previous"]):
            files_to_load.add("sessions.md")
        if any(kw in topic_lower for kw in ["security", "threat", "vulnerability"]):
            files_to_load.add("threat_model.md")

        # Fallback: Load profile/preferences for general context
        if topic_lower == "general":
            files_to_load.update(["profile.md", "preferences.md"])

        for fname in files_to_load:
            content = self._read_file(fname)
            if content:
                parts.append(f"## {fname.upper()}\n{content}")

        return "\n\n---\n\n".join(parts)

    def record_lesson(self, lesson: str, topic_file: str = "preferences.md") -> None:
        """
        Corporate Memory Hook. 
        Appends a lesson to a specific topic file and ensures the index knows about it.
        """
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
        formatted = lesson.strip().replace("\n", " ")
        self._append_file(topic_file, f"- **[{now}] LESSON LEARNED:** {formatted}")
        
        # Simple Index Update logic: if the topic file isn't in the index, add it
        index = self._read_file(self.INDEX_FILE)
        if topic_file not in index:
            title = topic_file.replace(".md", "").capitalize()
            self._append_file(self.INDEX_FILE, f"- [{title}]({topic_file}) — Auto-generated topic")

    def record_decision(self, decision: str, rationale: str = "") -> None:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
        line = f"[{now}] DECISION: {decision}"
        if rationale:
            line += f" | RATIONALE: {rationale}"
        self._append_file("decisions.md", line)

    def record_threat(self, report: str) -> None:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
        formatted_report = report.strip().replace("\n", " ")
        self._append_file("threat_model.md", f"- **[{now}] VULNERABILITY DETECTED:** {formatted_report}")

    def list_files(self) -> list[dict]:
        """List all markdown files in the rules directory."""
        result = []
        for path in self.nexus_dir.glob("*.md"):
            result.append({
                "name": path.name,
                "exists": True,
                "size_bytes": path.stat().st_size,
                "path": str(path),
            })
        return result
