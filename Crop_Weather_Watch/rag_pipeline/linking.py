from pathlib import Path
from typing import Any, Dict, List, Optional


def detect_heading(text: str) -> Optional[str]:
    """Helper to detect if a text block is likely a section heading."""
    cleaned = text.strip()
    if not cleaned:
        return None
    lines = cleaned.split("\n")
    if len(lines) <= 2 and len(cleaned) < 120:
        words = cleaned.split()
        if words:
            letters = [c for c in cleaned if c.isalpha()]
            is_upper = all(c.isupper() for c in letters) if letters else False
            starts_with_num = words[0][0].isdigit() or words[0].startswith(("I", "V", "X", "Annex"))
            if is_upper or starts_with_num:
                return cleaned
    return None


def build_page_structure(page_number: int, text_blocks: List[Dict[str, Any]], tables: List[Dict[str, Any]], images: List[Dict[str, Any]], metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Create a linked, page-level representation of all extracted objects."""
    elements = []
    
    # 1. Text elements
    for text_block in text_blocks:
        content = text_block.get("content", "")
        heading = text_block.get("section_heading")
        if not heading and content:
            heading = detect_heading(content)
        elements.append({
            "type": "text",
            "page": page_number,
            "content": content,
            "bbox": text_block.get("bbox"),
            "section_heading": heading,
            "previous_element": None,
            "next_element": None,
        })
        
    # 2. Table elements
    for table in tables:
        elements.append({
            "type": "table",
            "page": page_number,
            "path": table.get("csv_path"),
            "bbox": table.get("bbox"),
            "section_heading": table.get("section_heading"),
            "caption": table.get("caption") or f"Table on page {page_number}",
            "previous_element": None,
            "next_element": None,
        })
        
    # 3. Image elements
    for image in images:
        elements.append({
            "type": "image",
            "page": page_number,
            "path": image.get("path"),
            "bbox": image.get("bbox"),
            "section_heading": image.get("section_heading"),
            "caption": image.get("caption") or f"Image on page {page_number}",
            "previous_element": None,
            "next_element": None,
        })

    # Sort elements on the page by vertical layout coordinate (y0), then horizontal (x0)
    def get_sort_key(el):
        bbox = el.get("bbox")
        y0 = bbox[1] if bbox and len(bbox) > 1 else 0.0
        x0 = bbox[0] if bbox and len(bbox) > 0 else 0.0
        return (y0, x0)

    elements.sort(key=get_sort_key)

    # Link the elements in their sorted reading order
    for index, element in enumerate(elements):
        if index > 0:
            element["previous_element"] = elements[index - 1].get("path") or elements[index - 1].get("content") or elements[index - 1]["type"]
        if index + 1 < len(elements):
            element["next_element"] = elements[index + 1].get("path") or elements[index + 1].get("content") or elements[index + 1]["type"]

    return {"page": page_number, "elements": elements, "metadata": metadata}


def build_document_representation(pdf_name: str, page_structures: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Merge all page structures into one unified document object, assigning sequential positions."""
    position = 1
    for page in page_structures:
        for element in page.get("elements", []):
            element["position"] = position
            position += 1
    return {"document_name": pdf_name, "pages": page_structures}
