import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

import config
from extractor.docling_parser import DoclingParser
from extractor.section_detector import SectionDetector
from extractor.crop_chunker import CropChunker
from extractor.context_resolver import ContextResolver
from extractor.rule_based_extractor import RuleBasedExtractor

def run_stage5_pipeline_debug(pdf_filename: str = "Minutes of the meeting of CWWG as on 01.06.2026.pdf"):
    pdf_path = config.RAW_PDFS_DIR / pdf_filename
    if not pdf_path.exists():
        print(f"Error: PDF not found at {pdf_path}")
        return None

    print("==========================================================")
    print(f"STAGE 5: FULL PIPELINE DEBUG DRY-RUN ({pdf_path.name})")
    print("==========================================================")

    parser = DoclingParser()
    doc_dict, md_content, report_week = parser.parse_pdf(pdf_path)

    detector = SectionDetector()
    filtered_blocks = detector.filter_document(doc_dict, md_content)

    chunker = CropChunker()
    raw_chunks = chunker.create_crop_chunks(filtered_blocks, pdf_path.name)

    resolver = ContextResolver()
    chunks = resolver.resolve_context(raw_chunks)

    rule_extractor = RuleBasedExtractor()
    total_extractions = []

    for idx, chunk in enumerate(chunks, 1):
        recs, is_ambiguous = rule_extractor.extract(chunk, report_week)
        for r in recs:
            r["chunk_index"] = idx
            total_extractions.append(r)

    print(f"\n[DRY RUN SUMMARY]")
    print(f"Report Date:            {report_week}")
    print(f"Docling Sections:       {len(filtered_blocks)}")
    print(f"Crop Chunks:            {len(chunks)}")
    print(f"Total Extractions:      {len(total_extractions)}")
    print("----------------------------------------------------------\n")

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "Minutes of the meeting of CWWG as on 01.06.2026.pdf"
    run_stage5_pipeline_debug(target)
