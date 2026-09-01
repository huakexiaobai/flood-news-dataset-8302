#!/usr/bin/env python3
"""Generate deterministic file-level inventory for the frozen dataset."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from datetime import datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = REPO_ROOT / "content"
INVENTORY = REPO_ROOT / "dataset_inventory.csv"
SUMMARY = REPO_ROOT / "dataset_summary.json"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    if not DATA_ROOT.is_dir():
        raise FileNotFoundError(DATA_ROOT)

    news_dirs = sorted(
        (path for path in DATA_ROOT.iterdir() if path.is_dir()),
        key=lambda path: path.name.encode("utf-8"),
    )
    if len(news_dirs) != 8302:
        raise RuntimeError(f"Expected 8302 news directories, found {len(news_dirs)}")

    rows: list[dict[str, str | int]] = []
    extensions: Counter[str] = Counter()
    total_bytes = 0
    primary_content_count = 0

    for news_dir in news_dirs:
        primary_content = news_dir / "content.md"
        if not primary_content.is_file():
            raise RuntimeError(f"Missing primary content: {primary_content}")
        primary_content_count += 1

        files = sorted(
            (
                path
                for path in news_dir.rglob("*")
                if path.is_file() and not path.name.startswith("._") and path.name != ".DS_Store"
            ),
            key=lambda path: str(path.relative_to(DATA_ROOT)).encode("utf-8"),
        )
        for path in files:
            relative_path = path.relative_to(DATA_ROOT)
            size = path.stat().st_size
            suffix = path.suffix.lower() or "<none>"
            extensions[suffix] += 1
            total_bytes += size
            rows.append(
                {
                    "news_id": news_dir.name,
                    "relative_path": relative_path.as_posix(),
                    "size_bytes": size,
                    "sha256": file_sha256(path),
                }
            )

    with INVENTORY.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["news_id", "relative_path", "size_bytes", "sha256"])
        writer.writeheader()
        writer.writerows(rows)

    summary = {
        "dataset": "flood-news-dataset-8302",
        "news_directories": len(news_dirs),
        "primary_content_files": primary_content_count,
        "tracked_dataset_files": len(rows),
        "total_dataset_bytes": total_bytes,
        "extensions": dict(sorted(extensions.items())),
        "news_id_definition": "top-level directory name under content/",
        "inventory_file": INVENTORY.name,
        "inventory_generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
