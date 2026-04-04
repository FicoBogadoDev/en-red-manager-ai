from __future__ import annotations

import argparse
import json
import shutil
import time
from dataclasses import asdict, dataclass
from pathlib import Path


SUBDIR_BY_SUFFIX = {
    ".txt": "transcript",
    ".png": "images",
    ".jpg": "images",
    ".jpeg": "images",
    ".opus": "audio",
    ".mp3": "audio",
    ".wav": "audio",
    ".m4a": "audio",
    ".mp4": "video",
    ".mov": "video",
    ".avi": "video",
    ".pdf": "docs",
    ".doc": "docs",
    ".docx": "docs",
    ".vcf": "contacts",
}

CONVERSATION_ROOTS = [
    "Chat de WhatsApp con +44 7484 335536",
    "Chat de WhatsApp con AzOOmate Rosario",
    "Chat de WhatsApp con Cecilia Pellegrini 326",
    "Chat de WhatsApp con Julieta Potalivo 924",
    "Chat de WhatsApp con Mariana Nanni Cl.226",
    "Chat de WhatsApp con Pablo Molina 226",
]

ROOT_ASSIGNMENTS = {
    "Mariana Nanni 1.png": (
        "Chat de WhatsApp con Mariana Nanni Cl.226",
        "matched",
        "high",
        "Root filename matches conversation participant name exactly.",
    ),
    "Mariana Nanni 2.png": (
        "Chat de WhatsApp con Mariana Nanni Cl.226",
        "matched",
        "high",
        "Root filename matches conversation participant name exactly.",
    ),
    "Pablo Molina 1.png": (
        "Chat de WhatsApp con Pablo Molina 226",
        "matched",
        "high",
        "Root filename matches conversation participant name exactly.",
    ),
    "Pablo Molina 2.png": (
        "Chat de WhatsApp con Pablo Molina 226",
        "matched",
        "high",
        "Root filename matches conversation participant name exactly.",
    ),
    "Ing. Pellegrinet 1.png": (
        "Chat de WhatsApp con Cecilia Pellegrini 326",
        "matched",
        "high",
        "Conversation transcript references Ing. Pellegrinet / Cecilia Antiba.",
    ),
    "Ing. Pellegrinet 2.png": (
        "Chat de WhatsApp con Cecilia Pellegrini 326",
        "matched",
        "high",
        "Conversation transcript references Ing. Pellegrinet / Cecilia Antiba.",
    ),
    "Maite Fernandez Costa 1.png": (
        "unassigned",
        "unassigned",
        "medium",
        "No confident transcript match exists in current export folders.",
    ),
    "Maite Fernandez Costa 2.png": (
        "unassigned",
        "unassigned",
        "medium",
        "No confident transcript match exists in current export folders.",
    ),
    "Maria Angeles Gonzales.png": (
        "unassigned",
        "unassigned",
        "medium",
        "No confident transcript match exists in current export folders.",
    ),
    "Maria angelica gonzales.png": (
        "unassigned",
        "unassigned",
        "medium",
        "No confident transcript match exists in current export folders.",
    ),
}

IGNORED_FILES = {"Para fico.rar"}


@dataclass
class MoveRecord:
    original_path: str
    new_path: str
    assignment_status: str
    confidence: str
    rationale: str


def subdir_for(path: Path) -> str:
    return SUBDIR_BY_SUFFIX.get(path.suffix.lower(), "docs")


def build_plan(base_dir: Path) -> tuple[list[MoveRecord], list[str]]:
    records: list[MoveRecord] = []
    ignored: list[str] = []

    for folder_name in CONVERSATION_ROOTS:
        folder = base_dir / folder_name
        for item in sorted(folder.iterdir()):
            if item.is_dir():
                continue
            target = folder / subdir_for(item) / item.name
            records.append(
                MoveRecord(
                    original_path=str(item.relative_to(base_dir)),
                    new_path=str(target.relative_to(base_dir)),
                    assignment_status="kept-in-place",
                    confidence="high",
                    rationale="Existing conversation asset sorted into standard subfolder by file type.",
                )
            )

    for item in sorted(base_dir.iterdir()):
        if item.is_dir():
            continue
        if item.name in IGNORED_FILES:
            ignored.append(str(item.relative_to(base_dir)))
            continue

        assignment = ROOT_ASSIGNMENTS.get(item.name)
        if assignment is None:
            target = base_dir / "unassigned" / subdir_for(item) / item.name
            status = "unassigned"
            confidence = "low"
            rationale = "No explicit mapping rule found; placed in unassigned."
        else:
            destination_root, status, confidence, rationale = assignment
            if destination_root == "unassigned":
                target = base_dir / "unassigned" / subdir_for(item) / item.name
            else:
                target = base_dir / destination_root / subdir_for(item) / item.name

        records.append(
            MoveRecord(
                original_path=str(item.relative_to(base_dir)),
                new_path=str(target.relative_to(base_dir)),
                assignment_status=status,
                confidence=confidence,
                rationale=rationale,
            )
        )

    return records, ignored


def ensure_layout(base_dir: Path) -> None:
    for folder_name in CONVERSATION_ROOTS:
        folder = base_dir / folder_name
        for subdir in {"transcript", "images", "audio", "video", "docs", "contacts"}:
            (folder / subdir).mkdir(exist_ok=True)
    for subdir in {"images", "audio", "video", "docs", "contacts", "transcript"}:
        (base_dir / "unassigned" / subdir).mkdir(parents=True, exist_ok=True)


def safe_move(source: Path, destination: Path) -> None:
    if source == destination:
        return

    destination.parent.mkdir(parents=True, exist_ok=True)

    if destination.exists():
        same_size = source.exists() and source.stat().st_size == destination.stat().st_size
        if same_size:
            unlink_with_retry(source)
            return
        raise FileExistsError(f"Destination already exists with different content: {destination}")

    shutil.copy2(source, destination)
    unlink_with_retry(source)


def unlink_with_retry(path: Path) -> None:
    last_error: Exception | None = None
    for _ in range(10):
        try:
            path.unlink()
            return
        except PermissionError as exc:
            last_error = exc
            time.sleep(0.2)
    if last_error is not None:
        raise last_error


def apply_plan(base_dir: Path, records: list[MoveRecord]) -> None:
    ensure_layout(base_dir)
    for record in records:
        source = base_dir / record.original_path
        destination = base_dir / record.new_path
        if source == destination:
            continue
        if not source.exists():
            continue
        safe_move(source, destination)


def write_manifest(base_dir: Path, records: list[MoveRecord], ignored: list[str], dry_run: bool) -> Path:
    payload = {
        "base_dir": str(base_dir),
        "dry_run": dry_run,
        "ignored_files": ignored,
        "records": [asdict(record) for record in records],
    }
    manifest_path = base_dir / "reorganization_manifest.json"
    manifest_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return manifest_path


def validate(base_dir: Path) -> dict[str, object]:
    summary: dict[str, object] = {
        "conversation_transcripts": {},
        "top_level_files": [],
    }

    top_level_files = [
        str(path.name)
        for path in sorted(base_dir.iterdir())
        if path.is_file() and path.name not in {"Para fico.rar", "reorganization_manifest.json"}
    ]
    summary["top_level_files"] = top_level_files

    per_conversation: dict[str, int] = {}
    for folder_name in CONVERSATION_ROOTS:
        transcript_dir = base_dir / folder_name / "transcript"
        per_conversation[folder_name] = len(list(transcript_dir.glob("*.txt")))
    summary["conversation_transcripts"] = per_conversation
    summary["unassigned_files"] = len([p for p in (base_dir / "unassigned").rglob("*") if p.is_file()]) if (base_dir / "unassigned").exists() else 0
    return summary


def print_plan(records: list[MoveRecord], ignored: list[str]) -> None:
    print("DRY RUN REORGANIZATION PLAN")
    print(f"Moves/planned placements: {len(records)}")
    print(f"Ignored files: {len(ignored)}")
    for record in records:
        print(
            f"- [{record.assignment_status}/{record.confidence}] "
            f"{record.original_path} -> {record.new_path} | {record.rationale}"
        )
    for item in ignored:
        print(f"- [ignored] {item}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalize source_data layout before research.")
    parser.add_argument("--base-dir", default="source_data")
    parser.add_argument("--apply", action="store_true", help="Perform the moves.")
    args = parser.parse_args()

    base_dir = Path(args.base_dir).resolve()
    records, ignored = build_plan(base_dir)

    if not args.apply:
        print_plan(records, ignored)
        return

    apply_plan(base_dir, records)
    manifest_path = write_manifest(base_dir, records, ignored, dry_run=False)
    summary = validate(base_dir)

    print(f"Wrote manifest: {manifest_path}")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
