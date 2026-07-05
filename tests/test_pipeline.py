import json
import tempfile
from pathlib import Path

import fitz
from PIL import Image as PILImage

from Crop_Weather_Watch.rag_pipeline.chunking import build_chunk_from_elements
from Crop_Weather_Watch.rag_pipeline.extractors import ImageExtractor, TextExtractor
from Crop_Weather_Watch.rag_pipeline.utils import ensure_directory


def test_build_chunk_from_elements_preserves_metadata():
    elements = [
        {"type": "text", "content": "Heading", "page": 1, "section_heading": "Weather Overview"},
        {"type": "table", "path": "table.csv", "page": 1, "section_heading": "Weather Overview"},
        {"type": "image", "path": "img.jpg", "page": 1, "section_heading": "Weather Overview"},
    ]

    chunk = build_chunk_from_elements(elements, chunk_id="chunk_001", source_pdf="report.pdf")

    assert chunk["chunk_id"] == "chunk_001"
    assert chunk["source_pdf"] == "report.pdf"
    assert chunk["linked_tables"] == ["table.csv"]
    assert chunk["linked_images"] == ["img.jpg"]
    assert chunk["metadata"]["page_numbers"] == [1]


def test_ensure_directory_creates_nested_paths():
    with tempfile.TemporaryDirectory() as tmpdir:
        target = Path(tmpdir) / "a" / "b" / "c"
        ensure_directory(target)
        assert target.exists() and target.is_dir()


def test_text_extractor_writes_one_full_document_text_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_path = Path(tmpdir) / "sample.pdf"
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((72, 72), "This is the full PDF text")
        doc.save(pdf_path)
        doc.close()

        extractor = TextExtractor(output_dir=Path(tmpdir))
        result = extractor.extract(pdf_path, "week_test")

        assert result["full_text_path"].endswith("full_document.txt")
        assert "This is the full PDF text" in Path(result["full_text_path"]).read_text(encoding="utf-8")


def test_image_extractor_handles_alpha_images():
    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_path = Path(tmpdir) / "sample_with_image.pdf"
        doc = fitz.open()
        page = doc.new_page()
        img = PILImage.new("RGBA", (50, 50), (255, 0, 0, 128))
        image_path = Path(tmpdir) / "sample.png"
        img.save(image_path)
        page.insert_image(page.rect, filename=str(image_path))
        doc.save(pdf_path)
        doc.close()

        extractor = ImageExtractor(output_dir=Path(tmpdir))
        images = extractor.extract(pdf_path, "week_test")

        assert images
        assert Path(images[0]["path"]).exists()
