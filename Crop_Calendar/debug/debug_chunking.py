import json
import sys
from pathlib import Path

# Reconfigure stdout to utf-8 for Windows console support
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

import config
from extractor.docling_parser import DoclingParser
from extractor.section_detector import SectionDetector
from extractor.crop_chunker import CropChunker
from extractor.context_resolver import ContextResolver

def run_stage3_chunking(pdf_filename: str = "Minutes of the meeting of CWWG as on 01.06.2026.pdf", max_display: int = 30):
    pdf_path = config.RAW_PDFS_DIR / pdf_filename
    if not pdf_path.exists():
        print(f"Error: PDF not found at {pdf_path}")
        return None

    parser = DoclingParser()
    doc_dict, md_content, report_week = parser.parse_pdf(pdf_path)

    detector = SectionDetector()
    filtered_blocks = detector.filter_document(doc_dict, md_content)

    chunker = CropChunker()
    raw_chunks = chunker.create_crop_chunks(filtered_blocks, pdf_path.name)

    resolver = ContextResolver()
    resolved_chunks = resolver.resolve_context(raw_chunks)

    output_dir = PROJECT_ROOT / "debug" / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)

    print("==========================================================")
    print(f"STAGE 3: CHUNKING DEBUG ({pdf_path.name})")
    print(f"Total Chunks Generated: {len(resolved_chunks)}")
    print("==========================================================")

    display_count = min(max_display, len(resolved_chunks))

    for idx in range(display_count):
        c = resolved_chunks[idx]
        print(f"\n----------------------------------------------------------")
        print(f"Chunk #{idx + 1} | ID: {c.get('chunk_id')}")
        print(f"Crop:    {c.get('detected_crop') or 'Unknown / Unspecified'}")
        print(f"State:   {c.get('state_context') or 'All India'}")
        print(f"Page:    {c.get('page_number', 1)} | Section: {c.get('heading', 'General')}")
        print(f"Text:")
        print(c.get("chunk_text", "").strip())
        print(f"----------------------------------------------------------")

    (output_dir / "stage3_chunks.json").write_text(json.dumps(resolved_chunks, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nStage 3 output saved to: {output_dir / 'stage3_chunks.json'}\n")

    return resolved_chunks

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "Minutes of the meeting of CWWG as on 01.06.2026.pdf"
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    run_stage3_chunking(target, max_display=limit)
