import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

import config
from extractor.docling_parser import DoclingParser
from extractor.section_detector import SectionDetector
from extractor.crop_chunker import CropChunker
from extractor.context_resolver import ContextResolver
from extractor.rule_based_extractor import RuleBasedExtractor

def run_stage4_extraction(pdf_filename: str = "Minutes of the meeting of CWWG as on 18.05.2026.pdf", sample_limit: int = 10):
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
    obs_units = resolver.resolve_context(raw_chunks)

    rule_extractor = RuleBasedExtractor()

    print("==========================================================")
    print(f"STAGE 4: EXTRACTION & TABLE INTERPRETER DEBUG ({pdf_path.name})")
    print(f"Total Observation Units / Atomic Events: {len(obs_units)}")
    print("==========================================================")

    sample_count = min(sample_limit, len(obs_units))
    for i in range(sample_count):
        unit = obs_units[i]
        recs, is_ambiguous = rule_extractor.extract(unit, report_week)
        
        # Override harvest_progress if atomic table event matched
        if unit.get("harvest_progress") and recs:
            for r in recs:
                r["affected_area"] = unit.get("harvest_progress")
                r["growth_stage"] = "Harvesting"

        print(f"\n====================================")
        print(f"Observation Unit #{i + 1} | ID: {unit.get('chunk_id')}")
        print("------------------------------------")
        print("Original Text:")
        print(unit.get("chunk_text", "").strip())
        print("------------------------------------")
        print("Extractor Output:")
        formatted_output = []
        for r in recs:
            formatted_output.append({
                "crop": r.get("crop"),
                "state": r.get("state"),
                "growth_stage": r.get("growth_stage"),
                "crop_operation": r.get("crop_operation"),
                "pest": r.get("pest"),
                "disease": r.get("disease"),
                "affected_area": r.get("affected_area"),
                "recommendation": r.get("recommendation"),
                "evidence": r.get("evidence")
            })
        print(json.dumps(formatted_output, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "Minutes of the meeting of CWWG as on 18.05.2026.pdf"
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    run_stage4_extraction(target, sample_limit=limit)
