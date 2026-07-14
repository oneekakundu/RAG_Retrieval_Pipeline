"""Standalone zero-shot GLiNER exploration using Docling's Markdown export."""

from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from gliner import GLiNER


SCRIPT_DIR = Path(__file__).resolve().parent
MARKDOWN_PATH = SCRIPT_DIR / "docling_output" / "cwwg_08_06_2026.md"
OUTPUT_DIR = SCRIPT_DIR / "gliner_output"
MODEL_NAME = "urchade/gliner_medium-v2.1"
THRESHOLD = 0.45
LABELS = [
    "crop", "crop variety", "growth stage", "disease", "pest", "insect",
    "state", "district", "rainfall", "temperature", "irrigation",
    "fertilizer", "nutrient", "weather parameter",
]


def read_markdown(markdown_path: Path) -> str:
    """Read the Markdown created by docling_test.py."""
    if not markdown_path.is_file():
        raise FileNotFoundError(
            f"Markdown input is missing: {markdown_path}. Run docling_test.py first."
        )
    return markdown_path.read_text(encoding="utf-8")


def split_text(text: str, max_characters: int = 3_500) -> list[tuple[int, str]]:
    """Split long reports at line boundaries so every GLiNER call has local context."""
    chunks: list[tuple[int, str]] = []
    start = 0
    current = ""
    for line in text.splitlines(keepends=True):
        if current and len(current) + len(line) > max_characters:
            chunks.append((start, current))
            start += len(current)
            current = ""
        current += line
    if current:
        chunks.append((start, current))
    return chunks


def run_gliner(text: str) -> list[dict[str, Any]]:
    """Load GLiNER and predict requested labels without task-specific training."""
    try:
        model = GLiNER.from_pretrained(MODEL_NAME)
        entities: list[dict[str, Any]] = []
        for offset, chunk in split_text(text):
            for entity in model.predict_entities(chunk, LABELS, threshold=THRESHOLD):
                entities.append({
                    "text": entity["text"],
                    "label": entity["label"],
                    "score": round(float(entity["score"]), 6),
                    "start": int(entity["start"]) + offset,
                    "end": int(entity["end"]) + offset,
                })
        # A boundary can be included twice only if a future splitter changes;
        # deduplication keeps saved results stable and easy to inspect.
        unique = {(e["text"], e["label"], e["start"], e["end"]): e for e in entities}
        return sorted(unique.values(), key=lambda item: (item["start"], item["end"], item["label"]))
    except Exception as exc:
        raise RuntimeError(f"GLiNER extraction with '{MODEL_NAME}' failed.") from exc


def save_entities(entities: list[dict[str, Any]], output_dir: Path) -> None:
    """Save machine-readable JSON and spreadsheet-friendly CSV versions."""
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "entities.json").write_text(
        json.dumps(entities, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    with (output_dir / "entities.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["text", "label", "score", "start", "end"])
        writer.writeheader()
        writer.writerows(entities)


def print_summary(entities: list[dict[str, Any]]) -> None:
    """Show counts and normalized distinct values for quick exploratory review."""
    by_label: dict[str, list[str]] = defaultdict(list)
    for entity in entities:
        by_label[entity["label"]].append(entity["text"])

    print("\nGLiNER extraction completed")
    print(f"Total entities: {len(entities)}")
    print("Entities grouped by label:")
    for label in LABELS:
        values = by_label.get(label, [])
        print(f"  {label}: {len(values)}")
    print("Unique entity values:")
    for label in LABELS:
        values = sorted({value.strip() for value in by_label.get(label, [])}, key=str.casefold)
        if values:
            print(f"  {label}: {', '.join(values)}")


def main() -> None:
    """Read Docling Markdown, extract entities, save them, and report the results."""
    try:
        entities = run_gliner(read_markdown(MARKDOWN_PATH))
        save_entities(entities, OUTPUT_DIR)
        print_summary(entities)
        print(f"Output directory: {OUTPUT_DIR}")
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
