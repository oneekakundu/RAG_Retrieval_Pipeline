import json
from pathlib import Path
import sys
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.datamodel.base_models import InputFormat

# Import config
sys.path.append(str(Path(__file__).resolve().parents[1]))
import config

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

    def parse_pdf(self, pdf_path: Path) -> dict:
        """
        Parse PDF and return structured dict representation.
        Saves the resulting JSON and Markdown files.
        """
        pdf_name = pdf_path.stem
        json_out_path = config.DOCLING_JSON_DIR / f"{pdf_name}.json"
        md_out_path = config.DOCLING_JSON_DIR / f"{pdf_name}.md"

        # Check if already processed to save time/compute
        if json_out_path.exists() and md_out_path.exists():
            print(f"Skipping Docling parse for {pdf_path.name} (cached JSON/Markdown exists)")
            try:
                with open(json_out_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading cached JSON: {e}, re-parsing...")

        print(f"Parsing PDF with Docling: {pdf_path.name} ...")
        try:
            result = self.converter.convert(pdf_path)
            doc = result.document
            
            # Export to dict and markdown
            doc_dict = doc.export_to_dict()
            markdown_content = doc.export_to_markdown()

            # Save files
            with open(json_out_path, "w", encoding="utf-8") as f:
                json.dump(doc_dict, f, indent=2, ensure_ascii=False)
            
            md_out_path.write_text(markdown_content, encoding="utf-8")
            print(f"Saved parsed representations to {config.DOCLING_JSON_DIR}")
            return doc_dict
        except Exception as e:
            print(f"Error parsing PDF with Docling: {e}")
            raise e

if __name__ == "__main__":
    # Test parser on first available PDF
    pdf_files = list(config.RAW_PDFS_DIR.glob("*.pdf"))
    if pdf_files:
        parser = DoclingParser()
        parser.parse_pdf(pdf_files[0])
    else:
        print("No raw PDFs found to parse.")
