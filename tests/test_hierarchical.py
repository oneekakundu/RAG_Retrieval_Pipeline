import json
import tempfile
from pathlib import Path

from Crop_Weather_Watch.rag_pipeline.linking import build_page_structure, build_document_representation, detect_heading
from Crop_Weather_Watch.rag_pipeline.hierarchical_chunker import (
    build_parent_chunks,
    build_child_chunks,
    link_parent_child,
    prepare_chunks_for_embedding
)


def test_detect_heading():
    # Valid headings
    assert detect_heading("WEATHER WATCH REPORT") == "WEATHER WATCH REPORT"
    assert detect_heading("1. Introduction") == "1.1 Introduction" or detect_heading("1. Introduction") == "1. Introduction"
    assert detect_heading("Annexure-I: Weather Summary") == "Annexure-I: Weather Summary"
    
    # Non-headings (too long, not uppercase, etc.)
    long_text = "This is a very long paragraph that goes on and on to describe the weather conditions and agricultural Welfare in detail across multiple states."
    assert detect_heading(long_text) is None


def test_visual_sorting_and_positioning():
    # 2 text blocks, 1 table, 1 image
    text_blocks = [
        {"content": "Paragraph 1 (top)", "bbox": [50.0, 100.0, 500.0, 150.0]},
        {"content": "Paragraph 2 (bottom)", "bbox": [50.0, 400.0, 500.0, 450.0]}
    ]
    tables = [
        {"csv_path": "table1.csv", "bbox": [50.0, 200.0, 500.0, 300.0]}
    ]
    images = [
        {"path": "image1.jpg", "bbox": [50.0, 500.0, 500.0, 600.0]}
    ]
    metadata = {"width": 600, "height": 800}

    # Build page structure
    page_struct = build_page_structure(1, text_blocks, tables, images, metadata)
    elements = page_struct["elements"]

    # Verify visual order (sorted by y0):
    # Paragraph 1 (y0=100) -> Table 1 (y0=200) -> Paragraph 2 (y0=400) -> Image 1 (y0=500)
    assert elements[0]["type"] == "text" and elements[0]["content"] == "Paragraph 1 (top)"
    assert elements[1]["type"] == "table" and elements[1]["path"] == "table1.csv"
    assert elements[2]["type"] == "text" and elements[2]["content"] == "Paragraph 2 (bottom)"
    assert elements[3]["type"] == "image" and elements[3]["path"] == "image1.jpg"

    # Verify bidirectional element links (previous_element and next_element)
    assert elements[0]["next_element"] == "table1.csv"
    assert elements[1]["previous_element"] == "Paragraph 1 (top)"
    assert elements[1]["next_element"] == "Paragraph 2 (bottom)"
    assert elements[2]["previous_element"] == "table1.csv"

    # Build document representation (assigns global sequential position)
    doc = build_document_representation("test_doc.pdf", [page_struct])
    elements = doc["pages"][0]["elements"]
    assert elements[0]["position"] == 1
    assert elements[1]["position"] == 2
    assert elements[2]["position"] == 3
    assert elements[3]["position"] == 4


def test_closest_element_assignment_ties():
    # Test assignment logic for tables/images where distance is tied
    # Example page:
    # Pos 1: Text A
    # Pos 2: Text B
    # Pos 3: Table (tied distance 1 to Pos 2 and Pos 4)
    # Pos 4: Text C
    # Pos 5: Text D
    # Pos 6: Image (tied distance 1 to Pos 5 and Pos 7)
    # Pos 7: Text E
    
    page_elements = [
        {"type": "text", "page": 1, "content": " ".join(["word"] * 300), "bbox": [50, 50, 200, 70], "position": 1},
        {"type": "text", "page": 1, "content": " ".join(["word"] * 10), "bbox": [50, 100, 200, 120], "position": 2},
        {"type": "table", "page": 1, "path": "table1.csv", "bbox": [50, 150, 200, 250], "position": 3, "caption": "Table 1"},
        {"type": "text", "page": 1, "content": " ".join(["word"] * 300), "bbox": [50, 300, 200, 320], "position": 4},
        {"type": "text", "page": 1, "content": " ".join(["word"] * 10), "bbox": [50, 350, 200, 370], "position": 5},
        {"type": "image", "page": 1, "path": "image1.jpg", "bbox": [50, 400, 200, 500], "position": 6, "caption": "Image 1"},
        {"type": "text", "page": 1, "content": " ".join(["word"] * 300), "bbox": [50, 550, 200, 570], "position": 7},
    ]
    
    page_struct = {
        "page": 1,
        "elements": page_elements,
        "metadata": {}
    }
    
    document = {
        "document_name": "test_tie.pdf",
        "pages": [page_struct]
    }
    
    # Mock Parent Chunk
    parent_chunk = {
        "chunk_id": "test_week_page_01",
        "text": page_elements[0]["content"] + "\n\n" + page_elements[1]["content"] + "\n\n" + page_elements[3]["content"] + "\n\n" + page_elements[4]["content"] + "\n\n" + page_elements[6]["content"],
        "linked_tables": [],
        "linked_images": [],
        "metadata": {"page_numbers": [1], "source_pdf": "test_tie.pdf"},
        "children": []
    }
    
    # Let's say we split into 3 child chunks:
    # Child 1: Text A, Text B (positions 1, 2)
    # Child 2: Text C, Text D (positions 4, 5)
    # Child 3: Text E (position 7)
    #
    # Expected table/image assignment:
    # Table (3) is distance 1 from Child 1 (ends at 2) and Child 2 (starts at 4).
    # Since they are tied, it should be assigned to the earlier child chunk (Child 1).
    # Image (6) is distance 1 from Child 2 (ends at 5) and Child 3 (starts at 7).
    # Since they are tied, it should be assigned to the earlier child chunk (Child 2).
    
    child_chunks = build_child_chunks([parent_chunk], document)
    
    # Verify child chunks structure and element assignment
    assert len(child_chunks) == 3
    
    c1 = child_chunks[0]
    c2 = child_chunks[1]
    c3 = child_chunks[2]
    
    # Child 1 contains Text A & B
    assert page_elements[0]["content"] in c1["text"]
    assert page_elements[1]["content"] in c1["text"]
    # Table should be assigned to Child 1
    assert len(c1["linked_tables"]) == 1
    assert c1["linked_tables"][0]["path"] == "table1.csv"
    assert c1["linked_tables"][0]["position"] == 3
    
    # Child 2 contains Text C & D
    assert page_elements[3]["content"] in c2["text"]
    assert page_elements[4]["content"] in c2["text"]
    # Image should be assigned to Child 2
    assert len(c2["linked_images"]) == 1
    assert c2["linked_images"][0]["path"] == "image1.jpg"
    assert c2["linked_images"][0]["position"] == 6
    assert len(c2["linked_tables"]) == 0
    
    # Child 3 contains Text E
    assert page_elements[6]["content"] in c3["text"]
    assert len(c3["linked_tables"]) == 0
    assert len(c3["linked_images"]) == 0


def test_parent_child_linking_and_bidirectional_mapping():
    parent_chunks = [
        {"chunk_id": "p1", "text": "Parent 1 Text", "metadata": {"page_numbers": [1]}, "children": []}
    ]
    child_chunks = [
        {"child_chunk_id": "c1", "parent_chunk_id": "p1", "text": "Child 1 Text"},
        {"child_chunk_id": "c2", "parent_chunk_id": "p1", "text": "Child 2 Text"}
    ]
    
    link_parent_child(parent_chunks, child_chunks)
    
    assert parent_chunks[0]["children"] == ["c1", "c2"]
    
    prepared = prepare_chunks_for_embedding(child_chunks)
    assert prepared[0]["chunk_id"] == "c1"
    assert prepared[1]["chunk_id"] == "c2"
