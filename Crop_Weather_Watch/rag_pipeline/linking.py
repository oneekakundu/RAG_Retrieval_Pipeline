from pathlib import Path
from typing import Any, Dict, List


def build_page_structure(page_number: int, text_blocks: List[Dict[str, Any]], tables: List[Dict[str, Any]], images: List[Dict[str, Any]], metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Create a linked, page-level representation of all extracted objects."""
    elements = []
    for text_block in text_blocks:
        elements.append({
            "type": "text",
            "page": page_number,
            "content": text_block.get("content", ""),
            "bbox": text_block.get("bbox"),
            "section_heading": text_block.get("section_heading"),
            "previous_element": None,
            "next_element": None,
            "page": page_number,
        })
    for table in tables:
        elements.append({
            "type": "table",
            "page": page_number,
            "path": table.get("csv_path"),
            "bbox": table.get("bbox"),
            "section_heading": table.get("section_heading"),
            "previous_element": None,
            "next_element": None,
        })
    for image in images:
        elements.append({
            "type": "image",
            "page": page_number,
            "path": image.get("path"),
            "bbox": image.get("bbox"),
            "section_heading": image.get("section_heading"),
            "previous_element": None,
            "next_element": None,
        })

    for index, element in enumerate(elements):
        if index > 0:
            element["previous_element"] = elements[index - 1].get("path") or elements[index - 1].get("content") or elements[index - 1]["type"]
        if index + 1 < len(elements):
            element["next_element"] = elements[index + 1].get("path") or elements[index + 1].get("content") or elements[index + 1]["type"]

    return {"page": page_number, "elements": elements, "metadata": metadata}


def build_document_representation(pdf_name: str, page_structures: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Merge all page structures into one unified document object."""
    return {"document_name": pdf_name, "pages": page_structures}
