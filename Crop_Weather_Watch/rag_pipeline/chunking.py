from __future__ import annotations

from typing import Any, Dict, List


def build_chunk_from_elements(elements: List[Dict[str, Any]], chunk_id: str, source_pdf: str, previous_chunk: str | None = None, next_chunk: str | None = None) -> Dict[str, Any]:
    """Create a semantic chunk that preserves linked tables, images, and metadata."""
    text_parts = []
    linked_tables = []
    linked_images = []
    page_numbers = []
    headings = []

    for element in elements:
        element_type = element.get("type")
        if element_type == "text":
            text_parts.append(str(element.get("content", "")).strip())
            heading = element.get("section_heading")
            if heading:
                headings.append(heading)
        elif element_type == "table":
            tbl_path = element.get("path")
            linked_tables.append(tbl_path)
            if tbl_path:
                from pathlib import Path
                text_parts.append(f"[TABLE {Path(tbl_path).stem}]")
        elif element_type == "image":
            img_path = element.get("path")
            linked_images.append(img_path)
            if img_path:
                from pathlib import Path
                text_parts.append(f"[IMAGE {Path(img_path).stem}]")

        if element.get("page") is not None:
            page_numbers.append(element["page"])

    return {
        "chunk_id": chunk_id,
        "text": "\n\n".join(part for part in text_parts if part),
        "linked_tables": [path for path in linked_tables if path],
        "linked_images": [path for path in linked_images if path],
        "metadata": {
            "page_numbers": sorted(set(page_numbers)),
            "headings": headings,
            "source_pdf": source_pdf,
        },
        "source_pdf": source_pdf,
        "previous_chunk": previous_chunk,
        "next_chunk": next_chunk,
    }


def chunk_document(document: Dict[str, Any], week_name: str) -> List[Dict[str, Any]]:
    """Create a simple late-chunking style grouping by page while preserving linked elements."""
    from pathlib import Path
    chunks = []
    for page_index, page in enumerate(document.get("pages", []), start=1):
        page_elements = page.get("elements", [])
        if not page_elements:
            continue
        doc_name = document.get("document_name", week_name)
        doc_stem = Path(doc_name).stem.replace(" ", "_").replace(".", "_")
        chunk_id = f"{week_name}_{doc_stem}_page_{page_index:02d}"
        chunk = build_chunk_from_elements(page_elements, chunk_id, doc_name)
        chunks.append(chunk)
    return chunks
