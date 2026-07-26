import json
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import config
from extractor.docling_parser import DoclingParser
from extractor.section_detector import SectionDetector, EXCLUDED_SECTION_HEADERS

def run_stage2_sections(pdf_filename: str = "Minutes of the meeting of CWWG as on 01.06.2026.pdf"):
    pdf_path = config.RAW_PDFS_DIR / pdf_filename
    if not pdf_path.exists():
        print(f"Error: PDF not found at {pdf_path}")
        return None

    parser = DoclingParser()
    doc_dict, md_content, report_week = parser.parse_pdf(pdf_path)

    detector = SectionDetector()
    filtered_blocks = detector.filter_document(doc_dict, md_content)

    output_dir = PROJECT_ROOT / "debug" / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)

    print("==========================================================")
    print(f"STAGE 2: SECTION DETECTION DEBUG ({pdf_path.name})")
    print("==========================================================")

    # Track headings found in document
    all_headings = []
    removed_headings = []
    retained_headings = []

    lines = md_content.splitlines()
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            heading_text = stripped.lstrip("#").strip()
            all_headings.append(heading_text)
            if detector._is_excluded_section(heading_text):
                removed_headings.append(heading_text)
            else:
                retained_headings.append(heading_text)

    print(f"\n[REMOVED SECTIONS ({len(removed_headings)})]:")
    print("----------------------------------------------------------")
    for h in set(removed_headings):
        print(f"  ❌ Excluded: {h}")

    print(f"\n[RETAINED CROP SECTIONS ({len(retained_headings)})]:")
    print("----------------------------------------------------------")
    for h in set(retained_headings):
        print(f"  ✅ Retained: {h}")

    print(f"\nTotal Clean Section Blocks Produced: {len(filtered_blocks)}")
    
    (output_dir / "stage2_sections.json").write_text(json.dumps(filtered_blocks, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nStage 2 output saved to: {output_dir / 'stage2_sections.json'}\n")

    return filtered_blocks

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "Minutes of the meeting of CWWG as on 01.06.2026.pdf"
    run_stage2_sections(target)
