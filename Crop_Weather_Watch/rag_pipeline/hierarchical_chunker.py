from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import numpy as np

from .chunking import chunk_document


def build_parent_chunks(document: Dict[str, Any], week_name: str) -> List[Dict[str, Any]]:
    """Build parent page-wise chunks preserving metadata, tables, images, headings, and previous/next page links.
    
    Reuses the existing page-wise chunking logic and enriches it with visual elements and child links.
    """
    # 1. Call the existing chunk_document logic to get basic page-level chunks
    basic_chunks = chunk_document(document, week_name)
    
    # 2. Enrich each chunk as a Parent Chunk
    parent_chunks = []
    for i, chunk in enumerate(basic_chunks):
        page_numbers = chunk.get("metadata", {}).get("page_numbers", [])
        if not page_numbers:
            continue
            
        page_num = page_numbers[0]
        # Find the page structure from the document
        page = None
        for p in document.get("pages", []):
            if p.get("page") == page_num:
                page = p
                break
                
        if not page:
            continue
            
        # Replace linked_tables and linked_images with rich element dicts (with position/caption)
        rich_tables = [e for e in page.get("elements", []) if e.get("type") == "table"]
        rich_images = [e for e in page.get("elements", []) if e.get("type") == "image"]
        
        parent_chunk = {
            "chunk_id": chunk["chunk_id"],
            "text": chunk["text"],
            "linked_tables": rich_tables,
            "linked_images": rich_images,
            "metadata": chunk["metadata"],
            "children": [],
            "previous_chunk": basic_chunks[i - 1]["chunk_id"] if i > 0 else None,
            "next_chunk": basic_chunks[i + 1]["chunk_id"] if i + 1 < len(basic_chunks) else None,
        }
        parent_chunks.append(parent_chunk)
        
    return parent_chunks


def semantic_split_parent(parent_text: str, text_elements: List[Dict[str, Any]], parent_chunk_id: str) -> List[List[Dict[str, Any]]]:
    """Split the text elements of a page into semantic groups of approx 300-600 words.
    
    Uses SentenceTransformer embeddings to compute similarity between elements,
    with a robust fallback to a paragraph-aware splitter if needed.
    """
    if not text_elements:
        return []
        
    min_words = 200
    max_words = 500  # split around 500 words to keep target 300-600 words range
    
    try:
        from sentence_transformers import SentenceTransformer
        
        # Cache the SentenceTransformer model on the function to avoid reloading
        if not hasattr(semantic_split_parent, "_model"):
            semantic_split_parent._model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        model = semantic_split_parent._model
        
        if len(text_elements) <= 1:
            return [text_elements]
            
        texts = [e.get("content", "").strip() for e in text_elements if e.get("content", "").strip()]
        if len(texts) <= 1:
            return [text_elements]
            
        embeddings = model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
        
        similarities = []
        for i in range(len(embeddings) - 1):
            sim = float(np.dot(embeddings[i], embeddings[i+1]))
            similarities.append(sim)
            
        groups = []
        current_group = [text_elements[0]]
        current_word_count = len(text_elements[0].get("content", "").split())
        
        for i in range(len(text_elements) - 1):
            next_elem = text_elements[i+1]
            next_words = len(next_elem.get("content", "").split())
            sim = similarities[i]
            
            is_local_min = False
            if i > 0 and i < len(similarities) - 1:
                is_local_min = sim < similarities[i-1] and sim < similarities[i+1]
                
            should_split = (
                (current_word_count + next_words > max_words and current_word_count >= min_words) or
                (sim < 0.35 and current_word_count >= min_words) or
                (is_local_min and current_word_count >= min_words)
            )
            
            if should_split:
                groups.append(current_group)
                current_group = [next_elem]
                current_word_count = next_words
            else:
                current_group.append(next_elem)
                current_word_count += next_words
                
        if current_group:
            groups.append(current_group)
        return groups
        
    except Exception:
        # Paragraph-aware fallback splitter
        groups = []
        current_group = []
        current_word_count = 0
        for elem in text_elements:
            words = len(elem.get("content", "").split())
            if not words:
                continue
            if current_word_count + words > max_words and current_word_count >= min_words:
                groups.append(current_group)
                current_group = [elem]
                current_word_count = words
            else:
                current_group.append(elem)
                current_word_count += words
        if current_group:
            groups.append(current_group)
        return groups


def assign_linked_elements(child_chunks: List[Dict[str, Any]], parent_elements: List[Dict[str, Any]]) -> None:
    """Assign tables and images only to the child chunk that is closest in original document order.
    
    Prevents duplicating tables/images to every child chunk.
    """
    tables = [e for e in parent_elements if e.get("type") == "table"]
    images = [e for e in parent_elements if e.get("type") == "image"]
    
    for table in tables:
        table_pos = table.get("position")
        if table_pos is None:
            continue
            
        best_chunk = None
        min_dist = float("inf")
        
        for chunk in child_chunks:
            text_positions = chunk.get("_text_positions", [])
            if not text_positions:
                continue
            dist = min(abs(table_pos - tp) for tp in text_positions)
            # Use strict inequality to favor preceding chunks in case of ties
            if dist < min_dist:
                min_dist = dist
                best_chunk = chunk
                
        if best_chunk is not None:
            best_chunk["linked_tables"].append(table)
            
    for image in images:
        image_pos = image.get("position")
        if image_pos is None:
            continue
            
        best_chunk = None
        min_dist = float("inf")
        
        for chunk in child_chunks:
            text_positions = chunk.get("_text_positions", [])
            if not text_positions:
                continue
            dist = min(abs(image_pos - tp) for tp in text_positions)
            if dist < min_dist:
                min_dist = dist
                best_chunk = chunk
                
        if best_chunk is not None:
            best_chunk["linked_images"].append(image)


def build_child_chunks(parent_chunks: List[Dict[str, Any]], document: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Build semantic child chunks from every parent chunk.
    
    Preserves parent references, links consecutive child chunks, and maps tables/images to the closest child.
    """
    all_child_chunks = []
    
    for parent_chunk in parent_chunks:
        page_numbers = parent_chunk.get("metadata", {}).get("page_numbers", [])
        if not page_numbers:
            continue
            
        page_num = page_numbers[0]
        # Find the page structure from the document
        page = None
        for p in document.get("pages", []):
            if p.get("page") == page_num:
                page = p
                break
                
        if not page:
            continue
            
        # Get only the text elements on this page
        text_elements = [e for e in page.get("elements", []) if e.get("type") == "text"]
        
        # Split text elements semantically
        text_groups = semantic_split_parent(parent_chunk["text"], text_elements, parent_chunk["chunk_id"])
        
        child_chunks_for_page = []
        for index, group in enumerate(text_groups, start=1):
            child_chunk_id = f"{parent_chunk['chunk_id']}_child_{index:03d}"
            
            # Combine text content from the group
            text_parts = [e.get("content", "").strip() for e in group if e.get("content", "").strip()]
            joined_text = "\n\n".join(text_parts)
            
            # Gather headings inside the group
            headings = [e["section_heading"] for e in group if e.get("section_heading")]
            
            # Store temporary text element positions for element assignment
            text_positions = [e["position"] for e in group if e.get("position") is not None]
            
            child_chunk = {
                "child_chunk_id": child_chunk_id,
                "parent_chunk_id": parent_chunk["chunk_id"],
                "text": joined_text,
                "linked_tables": [],
                "linked_images": [],
                "metadata": {
                    "page_numbers": [page_num],
                    "headings": list(dict.fromkeys(headings)),  # Preserve order, remove duplicates
                    "source_pdf": parent_chunk["metadata"].get("source_pdf"),
                },
                "previous_child": None,
                "next_child": None,
                "_text_positions": text_positions,
            }
            child_chunks_for_page.append(child_chunk)
            
        # Assign tables/images on the page to their closest child chunk
        assign_linked_elements(child_chunks_for_page, page.get("elements", []))
        
        # Clean up temporary positions and append image/table markers to child chunk text
        for child in child_chunks_for_page:
            extra_markers = []
            for img in child.get("linked_images", []):
                img_path = img.get("path")
                if img_path:
                    extra_markers.append(f"[IMAGE {Path(img_path).stem}]")
            for tbl in child.get("linked_tables", []):
                tbl_path = tbl.get("path")
                if tbl_path:
                    extra_markers.append(f"[TABLE {Path(tbl_path).stem}]")
            
            if extra_markers:
                child["text"] = child["text"] + "\n" + "\n".join(extra_markers)

            if "_text_positions" in child:
                del child["_text_positions"]
                
        all_child_chunks.extend(child_chunks_for_page)
        
    # Link child chunks sequentially across the entire document
    for i, child in enumerate(all_child_chunks):
        child["previous_child"] = all_child_chunks[i - 1]["child_chunk_id"] if i > 0 else None
        child["next_child"] = all_child_chunks[i + 1]["child_chunk_id"] if i + 1 < len(all_child_chunks) else None
        
    return all_child_chunks


def link_parent_child(parent_chunks: List[Dict[str, Any]], child_chunks: List[Dict[str, Any]]) -> None:
    """Establish bidirectional IDs mapping between parent and child chunks."""
    parent_map = {p["chunk_id"]: p for p in parent_chunks}
    for child in child_chunks:
        pid = child["parent_chunk_id"]
        if pid in parent_map:
            parent_map[pid]["children"].append(child["child_chunk_id"])


def prepare_chunks_for_embedding(child_chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Map 'child_chunk_id' to 'chunk_id' to ensure compatibility with downstream embedding indexers."""
    for child in child_chunks:
        child["chunk_id"] = child["child_chunk_id"]
    return child_chunks


def load_parent_chunks_map(chunks_dir: Path) -> Dict[str, Dict[str, Any]]:
    """Load all parent chunks from the chunks directory and return a mapping by chunk_id."""
    parent_map = {}
    if not chunks_dir.exists():
        return parent_map
    for file in chunks_dir.glob("*_parent.json"):
        try:
            parents = json.loads(file.read_text(encoding="utf-8"))
            for p in parents:
                parent_map[p["chunk_id"]] = p
        except Exception:
            continue
    return parent_map
