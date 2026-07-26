import json
from pathlib import Path
import sys
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.datamodel.base_models import InputFormat

# Add config path
sys.path.append(str(Path(__file__).resolve().parents[1]))
import config
from extractor.normalizer import Normalizer

class DoclingParser:
    """Parse PDF files using Docling and save structured JSON/Markdown formats."""

    def __init__(self):
        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = False
        self.converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            }
        )

    def parse_pdf(self, pdf_path: Path) -> tuple[dict, str, str]:
        """
        Parse PDF and return (doc_dict, markdown_content, report_week).
        Saves the resulting JSON and Markdown files.
        """
        pdf_name = pdf_path.stem
        json_out_path = config.DOCLING_JSON_DIR / f"{pdf_name}.json"
        md_out_path = config.DOCLING_JSON_DIR / f"{pdf_name}.md"

        doc_dict = None
        markdown_content = ""

        # Check if cached JSON & Markdown exist
        if json_out_path.exists() and md_out_path.exists():
            print(f"[Parser] Using cached Docling output for {pdf_path.name}")
            try:
                with open(json_out_path, "r", encoding="utf-8") as f:
                    doc_dict = json.load(f)
                markdown_content = md_out_path.read_text(encoding="utf-8")
            except Exception as e:
                print(f"[Parser] Error reading cache ({e}), re-parsing...")

        if doc_dict is None or not markdown_content:
            print(f"[Parser] Parsing PDF with Docling: {pdf_path.name} ...")
            result = self.converter.convert(pdf_path)
            doc = result.document
            
            doc_dict = doc.export_to_dict()
            markdown_content = doc.export_to_markdown()

            # Save files
            with open(json_out_path, "w", encoding="utf-8") as f:
                json.dump(doc_dict, f, indent=2, ensure_ascii=False)
            
            md_out_path.write_text(markdown_content, encoding="utf-8")

        # Extract report date / report_week once from metadata and header text
        report_week, _ = Normalizer.parse_date_and_week(pdf_path.name, markdown_content[:1000])
        print(f"[Parser] Extracted report_week: {report_week} from {pdf_path.name}")

        return doc_dict, markdown_content, report_week

if __name__ == "__main__":
    pdf_files = list(config.RAW_PDFS_DIR.glob("*.pdf"))
    if pdf_files:
        parser = DoclingParser()
        doc_dict, md, week = parser.parse_pdf(pdf_files[0])
        print("Report week:", week)
