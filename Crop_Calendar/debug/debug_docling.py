import json
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

import config
from extractor.docling_parser import DoclingParser

def run_stage1_docling(pdf_filename: str = "Minutes of the meeting of CWWG as on 01.06.2026.pdf"):
    pdf_path = config.RAW_PDFS_DIR / pdf_filename
    if not pdf_path.exists():
        print(f"Error: Target PDF not found at {pdf_path}")
        return None

    print("==========================================================")
    print(f"STAGE 1: DOCLING DEBUG ({pdf_path.name})")
    print("==========================================================")

    parser = DoclingParser()
    doc_dict, md_content, report_week = parser.parse_pdf(pdf_path)

    output_dir = PROJECT_ROOT / "debug" / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save debug outputs
    (output_dir / "stage1_docling.json").write_text(json.dumps(doc_dict, indent=2, ensure_ascii=False), encoding="utf-8")
    (output_dir / "stage1_docling.md").write_text(md_content, encoding="utf-8")

    pages_count = len(doc_dict.get("pages", {})) if isinstance(doc_dict, dict) else "Unknown"

    print(f"\n[REPORT METADATA]")
    print(f"Filename:       {pdf_path.name}")
    print(f"Report Date:    {report_week}")
    print(f"Total Pages:    {pages_count}")
    print(f"Markdown Size:  {len(md_content)} characters")
    print(f"\n[MARKDOWN SAMPLE (First 500 chars)]:")
    print("----------------------------------------------------------")
    print(md_content[:500])
    print("----------------------------------------------------------")
    print(f"\nStage 1 outputs saved to: {output_dir / 'stage1_docling.json'} and stage1_docling.md\n")

    return doc_dict, md_content, report_week

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "Minutes of the meeting of CWWG as on 01.06.2026.pdf"
    run_stage1_docling(target)
