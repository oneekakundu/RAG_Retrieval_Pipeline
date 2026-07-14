"""Standalone Docling exploration for one Crop Weather Watch Group PDF.

This script deliberately imports no code from Crop_Weather_Watch.  Run it from
the repository root with: venv\\Scripts\\python.exe Webscraping_Methods\\docling_test.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from docling.document_converter import DocumentConverter


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PDF_NAME = "Minutes of the meeting of CWWG as on 08.06.2026.pdf"
OUTPUT_DIR = Path(__file__).resolve().parent / "docling_output"


def find_pdf() -> Path:
    """Find the one requested PDF without importing or calling production code."""
    candidates = (
        PROJECT_ROOT / "Crop_Weather_Watch" / "PDFs" / PDF_NAME,
        # Present project layouts store downloaded PDFs in this data directory.
        PROJECT_ROOT / "Crop_Weather_Watch" / "data" / "pdfs" / PDF_NAME,
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    locations = "\n".join(f"  - {path}" for path in candidates)
    raise FileNotFoundError(f"The requested PDF was not found. Checked:\n{locations}")


def extract_pdf(pdf_path: Path) -> Any:
    """Convert a local PDF into Docling's structured DoclingDocument object."""
    try:
        result = DocumentConverter().convert(pdf_path)
        return result.document
    except Exception as exc:
        raise RuntimeError(f"Docling could not convert '{pdf_path.name}'.") from exc


def save_markdown(document: Any, output_path: Path) -> str:
    """Export Docling's ordered structure to human-readable Markdown."""
    markdown = document.export_to_markdown()
    output_path.write_text(markdown, encoding="utf-8")
    return markdown


def save_json(document: Any, output_path: Path) -> None:
    """Save the full, lossless Docling document model as formatted JSON."""
    structure = document.export_to_dict()
    output_path.write_text(json.dumps(structure, indent=2, ensure_ascii=False), encoding="utf-8")


def save_text(markdown: str, output_path: Path) -> None:
    """Save a simple text view; Markdown is retained separately for structure."""
    output_path.write_text(markdown, encoding="utf-8")


def document_statistics(document: Any, markdown: str) -> dict[str, int]:
    """Count the principal document item types detected by Docling."""
    labels: list[str] = []
    for item, _level in document.iterate_items():
        label = getattr(item, "label", None)
        labels.append(getattr(label, "value", str(label)).lower())

    return {
        "pages": len(document.pages),
        "headings": sum(label == "section_header" for label in labels),
        "tables": sum(label == "table" for label in labels),
        "images": sum(label in {"picture", "figure"} for label in labels),
        "total_text_length": len(markdown),
    }


def print_summary(pdf_path: Path, output_dir: Path, stats: dict[str, int]) -> None:
    """Print a concise result that makes this exploratory run easy to verify."""
    print("\nDocling extraction completed")
    print(f"PDF: {pdf_path}")
    print(f"Output directory: {output_dir}")
    for label, value in stats.items():
        print(f"{label.replace('_', ' ').title()}: {value}")


def main() -> None:
    """Run conversion and write every requested Docling export."""
    try:
        pdf_path = find_pdf()
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        document = extract_pdf(pdf_path)

        markdown = save_markdown(document, OUTPUT_DIR / "cwwg_08_06_2026.md")
        save_json(document, OUTPUT_DIR / "cwwg_08_06_2026.json")
        save_text(markdown, OUTPUT_DIR / "cwwg_08_06_2026.txt")
        print_summary(pdf_path, OUTPUT_DIR, document_statistics(document, markdown))
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
