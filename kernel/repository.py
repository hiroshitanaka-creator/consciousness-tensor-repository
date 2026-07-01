from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {".git", ".ctr", "__pycache__", ".pytest_cache", ".venv", "venv", "dist", "build"}


@dataclass
class AxisReport:
    axis: str
    score: float
    veto: bool
    demands: list[str] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def root_path() -> Path:
    return ROOT


def ctr_dir(root: Path | None = None) -> Path:
    base = root or ROOT
    path = base / ".ctr"
    path.mkdir(exist_ok=True)
    return path


def report_dir(root: Path | None = None) -> Path:
    path = ctr_dir(root) / "reports"
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_axis_report(report: AxisReport, root: Path | None = None) -> Path:
    path = report_dir(root) / f"{report.axis}.json"
    path.write_text(json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    return path


def load_axis_reports(root: Path | None = None) -> dict[str, dict[str, Any]]:
    path = report_dir(root)
    reports: dict[str, dict[str, Any]] = {}
    for report_path in sorted(path.glob("*.json")):
        data = json.loads(report_path.read_text(encoding="utf-8"))
        reports[data["axis"]] = data
    return reports


def read_text(relative_path: str, root: Path | None = None) -> str:
    path = (root or ROOT) / relative_path
    return path.read_text(encoding="utf-8")


def write_json(relative_path: str, data: Any, root: Path | None = None) -> Path:
    path = (root or ROOT) / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def parse_jsonl(relative_path: str, root: Path | None = None) -> list[dict[str, Any]]:
    path = (root or ROOT) / relative_path
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for index, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            record = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{relative_path}:{index}: invalid JSONL: {exc}") from exc
        if not isinstance(record, dict):
            raise ValueError(f"{relative_path}:{index}: JSONL record must be an object")
        records.append(record)
    return records


def list_repo_files(root: Path | None = None) -> list[Path]:
    base = root or ROOT
    files: list[Path] = []
    for current, dirs, names in os.walk(base):
        dirs[:] = [name for name in dirs if name not in SKIP_DIRS]
        current_path = Path(current)
        for name in names:
            path = current_path / name
            if any(part in SKIP_DIRS for part in path.relative_to(base).parts):
                continue
            files.append(path)
    return sorted(files)


def relative(path: Path, root: Path | None = None) -> str:
    return path.relative_to(root or ROOT).as_posix()


def nonempty_lines(text: str) -> list[str]:
    return [line for line in text.splitlines() if line.strip()]


def has_all_text(text: str, required: list[str]) -> list[str]:
    missing = []
    lowered = text.lower()
    for item in required:
        if item.lower() not in lowered:
            missing.append(item)
    return missing
