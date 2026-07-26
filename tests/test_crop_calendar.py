import sys
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parents[1] / "Crop_Calendar"))

from extractor.normalizer import Normalizer
from extractor.validators import validate_and_clean_record, CropExtractionRecord
from extractor.section_detector import SectionDetector
from extractor.crop_chunker import CropChunker
from extractor.llm_extractor import FallbackExtractor

def test_user_example_extraction():
    """Tests the exact user prompt example: Maize - vegetative stage - Downy mildew in Karnataka."""
    chunk = {
        "chunk_text": "Maize - vegetative stage - Downy mildew in Karnataka.",
        "detected_crop": "Maize",
        "page_number": 1
    }
    report_week = "2026-06-22"
    
    extractor = FallbackExtractor()
    records = extractor.extract(chunk, report_week)
    
    assert len(records) == 1
    rec = records[0]
    assert rec["crop"] == "Maize"
    assert rec["state"] == "Karnataka"
    assert rec["growth_stage"] == "Vegetative"
    assert rec["pest_or_disease"] == "Downy mildew"
    assert rec["report_week"] == "2026-06-22"

def test_invalid_header_rejection():
    """Ensures document section headers like 'GENERAL' are rejected by validator."""
    data = {
        "crop": "GENERAL",
        "state": "Karnataka",
        "growth_stage": "Vegetative",
        "report_week": "2026-06-22"
    }
    record = validate_and_clean_record(data, "2026-06-22")
    assert record is None

def test_multiline_crop_chunking():
    """Tests chunking of scattered multi-line text into a single observation chunk."""
    text = "Rice\nFlowering stage.\nBlast incidence reported from Odisha."
    blocks = [{"heading": "4. Pests & Diseases", "text": text, "page_number": 1}]
    
    chunker = CropChunker()
    chunks = chunker.create_crop_chunks(blocks, "test.pdf")
    
    assert len(chunks) == 1
    assert "Rice" in chunks[0]["chunk_text"]
    assert "Blast" in chunks[0]["chunk_text"]
    
    extractor = FallbackExtractor()
    records = extractor.extract(chunks[0], "2026-06-22")
    assert len(records) == 1
    assert records[0]["crop"] == "Rice"
    assert records[0]["state"] == "Odisha"
    assert records[0]["growth_stage"] == "Flowering"
    assert records[0]["pest_or_disease"] == "Blast"
