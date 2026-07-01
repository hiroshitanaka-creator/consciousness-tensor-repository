from __future__ import annotations

import re
from pathlib import Path


REQUIRED_SECTIONS = [
    "What is being chosen?",
    "What is being destroyed by this choice?",
    "Which alternatives are rejected?",
    "Why is postponement dishonest?",
    "Who or what bears the cost?",
    "What failure would prove this decision wrong?",
    "What cannot be undone after merge?",
]

PLACEHOLDERS = {"...", "todo", "tbd", "later", "to be decided", "n/a"}


def _section_body(markdown: str, heading: str) -> str:
    pattern = re.compile(
        rf"^##\s+{re.escape(heading)}\s*$([\s\S]*?)(?=^##\s+|\Z)",
        re.MULTILINE,
    )
    match = pattern.search(markdown)
    return match.group(1).strip() if match else ""


def check_decision_rite(path: Path) -> tuple[list[str], dict[str, object]]:
    evidence: dict[str, object] = {"path": path.as_posix(), "sections": {}}
    demands: list[str] = []
    if not path.exists():
        return ["Create rituals/decision_rite.md."], evidence

    markdown = path.read_text(encoding="utf-8")
    for section in REQUIRED_SECTIONS:
        body = _section_body(markdown, section)
        evidence["sections"][section] = len(body)
        normalized = body.strip().lower()
        if not body:
            demands.append(f"Fill Decision Rite section: {section}")
            continue
        if normalized in PLACEHOLDERS or any(token in normalized for token in ("todo", "tbd")):
            demands.append(f"Replace placeholder in Decision Rite section: {section}")
        if len(body.split()) < 6:
            demands.append(f"Make Decision Rite section concrete: {section}")

    alternatives = _section_body(markdown, "Which alternatives are rejected?")
    rejected_count = len(re.findall(r"^\s*(?:[-*]|\d+\.)\s+", alternatives, flags=re.MULTILINE))
    evidence["rejected_alternatives"] = rejected_count
    if rejected_count < 2:
        demands.append("List at least two rejected alternatives in the Decision Rite.")

    return demands, evidence
