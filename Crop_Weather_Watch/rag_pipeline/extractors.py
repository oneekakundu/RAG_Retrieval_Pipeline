import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import fitz  # PyMuPDF
import pdfplumber
from PIL import Image

from .utils import ensure_directory, setup_logger


class BaseExtractor:
    """Common utilities for PDF extractors."""

    def __init__(self, output_dir: Optional[os.PathLike | str] = None, logger=None):
        self.output_dir = Path(output_dir or Path(__file__).resolve().parents[1] / "data")
        self.logger = logger or setup_logger("extractors")

    def _page_output_dir(self, week_name: str, kind: str) -> Path:
        return ensure_directory(self.output_dir / kind / week_name)


class TextExtractor(BaseExtractor):
    """Extract machine-readable text for the entire PDF and store it in one file with image markers."""

    def extract(self, pdf_path: Path, week_name: str) -> Dict[str, Any]:
        text_dir = self._page_output_dir(week_name, "text")
        full_text_path = text_dir / "full_document.txt"
        doc = fitz.open(pdf_path)
        page_texts = []
        parts = []
        for page_number, page in enumerate(doc, start=1):
            text = (page.get_text("text") or "").strip()
            image_markers = []
            for img_index, _ in enumerate(page.get_images(full=True), start=1):
                image_markers.append(f"[IMAGE page_{page_number:02d}_img_{img_index}]")
            marker_block = "\n".join(image_markers)
            cleaned_text = text or ""
            if cleaned_text and marker_block:
                combined_text = f"{cleaned_text}\n{marker_block}"
            else:
                combined_text = cleaned_text or marker_block
            page_texts.append({"page": page_number, "content": combined_text})
            parts.append(f"[PAGE {page_number}]\n{combined_text}\n")
        full_text = "\n".join(parts).strip()
        full_text_path.write_text(full_text or "", encoding="utf-8")
        doc.close()
        return {"full_text_path": str(full_text_path), "content": full_text or "", "page_texts": page_texts}


class TableExtractor(BaseExtractor):
    """Extract tables using pdfplumber and store CSV/JSON representations."""

    def extract(self, pdf_path: Path, week_name: str) -> List[Dict[str, Any]]:
        table_dir = self._page_output_dir(week_name, "tables")
        table_records = []
        with pdfplumber.open(pdf_path) as pdf:
            for page_number, page in enumerate(pdf.pages, start=1):
                tables = page.extract_tables()
                for table_index, table in enumerate(tables or [], start=1):
                    if not table:
                        continue
                    rows = [row for row in table if any(cell is not None and str(cell).strip() for cell in row)]
                    csv_path = table_dir / f"page_{page_number:02d}_table_{table_index}.csv"
                    json_path = table_dir / f"page_{page_number:02d}_table_{table_index}.json"
                    import pandas as pd
                    df = pd.DataFrame(rows)
                    df.to_csv(csv_path, index=False)
                    df.to_json(json_path, orient="records", indent=2)
                    table_records.append({"page": page_number, "table_index": table_index, "csv_path": str(csv_path), "json_path": str(json_path)})
        return table_records


class ImageExtractor(BaseExtractor):
    """Extract embedded images and write them as JPEG files safely for alpha-bearing images."""

    def extract(self, pdf_path: Path, week_name: str) -> List[Dict[str, Any]]:
        image_dir = self._page_output_dir(week_name, "images")
        image_records = []
        doc = fitz.open(pdf_path)
        for page_number, page in enumerate(doc, start=1):
            image_list = page.get_images(full=True)
            for img_index, img in enumerate(image_list, start=1):
                xref = img[0]
                pix = fitz.Pixmap(doc, xref)
                try:
                    if pix.alpha or pix.colorspace.name != "DeviceRGB":
                        pix = fitz.Pixmap(fitz.csRGB, pix)
                    image_path = image_dir / f"page_{page_number:02d}_img_{img_index}.jpg"
                    pix.save(image_path)
                except Exception as exc:
                    self.logger.warning("Could not save image %s for page %s: %s", img_index, page_number, exc)
                    continue
                pix = None
                image_records.append({"page": page_number, "image_index": img_index, "path": str(image_path)})
        doc.close()
        return image_records


class MetadataExtractor(BaseExtractor):
    """Collect page and layout metadata to aid reconstruction."""

    def extract(self, pdf_path: Path, week_name: str) -> Dict[str, Any]:
        metadata_dir = self._page_output_dir(week_name, "metadata")
        metadata = {"week": week_name, "pages": []}
        doc = fitz.open(pdf_path)
        for page_number, page in enumerate(doc, start=1):
            page_meta = {
                "page": page_number,
                "width": page.rect.width,
                "height": page.rect.height,
                "blocks": [],
            }
            for block_index, block in enumerate(page.get_text("blocks"), start=1):
                x0, y0, x1, y1, text, block_no, block_type = block[:7]
                page_meta["blocks"].append({
                    "block_index": block_index,
                    "page": page_number,
                    "bbox": [float(x0), float(y0), float(x1), float(y1)],
                    "text": text,
                    "type": "text" if text.strip() else "empty",
                    "source_type": "pdfblock",
                })
            metadata_path = metadata_dir / f"page_{page_number:02d}.json"
            metadata_path.write_text(json.dumps(page_meta, indent=2), encoding="utf-8")
            metadata["pages"].append(page_meta)
        doc.close()
        return metadata
