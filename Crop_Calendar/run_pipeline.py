import json
import os
import sys
from pathlib import Path

# Set up paths
sys.path.append(str(Path(__file__).resolve().parent))
import config
from downloader.download_reports import fetch_and_download
from extraction.docling_parser import DoclingParser
from extraction.semantic_chunker import SemanticChunker
from extraction.entity_extractor import EntityExtractor
from extraction.evidence_builder import EvidenceBuilder
from extraction.calendar_builder import CalendarBuilder
from database.sqlite import DatabaseManager
from database.export import DataExporter

def run_extraction_pipeline(limit=3):
    """Runs the entire download -> parse -> chunk -> extract -> database pipeline."""
    # 1. Download and fetch PDFs
    print("=== STEP 1: Downloading CWWG Reports ===")
    fetch_and_download()

    from extraction.normalizer import Normalizer
    pdf_files = list(config.RAW_PDFS_DIR.glob("*.pdf"))
    if not pdf_files:
        print("Error: No PDFs found in raw_pdfs. Exiting pipeline.")
        return

    # Sort files by parsed report date (newest first)
    pdf_files = sorted(
        pdf_files, 
        key=lambda p: Normalizer.parse_date_and_week(p.name)[0], 
        reverse=True
    )
    
    # Process a maximum of limit PDFs if they are not already processed to keep it fast
    # But if there are already processed ones, we don't count them towards the limit.
    print(f"Found {len(pdf_files)} PDF reports in raw_pdfs directory.")

    # Initialize modules
    db = DatabaseManager()
    parser = DoclingParser()
    chunker = SemanticChunker()
    builder = EvidenceBuilder()
    
    # Load GLiNER model once (lazy initialization to save memory if already done)
    extractor = None

    print("\n=== STEP 2: Parsing PDFs and Extracting Evidence ===")
    total_new_evidence = 0
    
    # Track which PDFs are already in the DB to avoid repeating extraction
    existing_evidence = db.load_all_evidence()
    processed_pdfs = set(r["source_pdf"] for r in existing_evidence)

    processed_count = 0
    for i, pdf_path in enumerate(pdf_files, 1):
        print(f"\n[{i}/{len(pdf_files)}] Processing: {pdf_path.name}")
        
        # Check if already processed in database
        if pdf_path.name in processed_pdfs:
            print(f"PDF {pdf_path.name} is already processed in database. Skipping entity extraction.")
            continue

        if limit is not None and processed_count >= limit:
            print(f"Limit of {limit} new PDF extractions reached. Skipping entity extraction for this file.")
            continue

        processed_count += 1

        try:
            # Parse PDF (caches JSON and Markdown)
            doc_dict = parser.parse_pdf(pdf_path)

            # Chunk document semantically
            chunks = chunker.chunk_document(doc_dict, pdf_path.name)
            print(f"Generated {len(chunks)} semantic observation chunks.")

            # Extract entities and build evidence for each chunk
            pdf_evidence = []
            
            # Lazy load GLiNER only if we actually need to extract new data
            if extractor is None:
                extractor = EntityExtractor()

            # Process chunks in batches or one by one
            for j, chunk in enumerate(chunks, 1):
                # Skip headings from entity extraction, they just provide context
                if chunk.get("type") == "heading":
                    continue
                
                # Predict entities
                extraction = extractor.extract_entities(chunk["text"])
                
                # Build atomic evidence records
                records = builder.build_evidence(chunk, extraction)
                if records:
                    pdf_evidence.extend(records)
                
                if j % 50 == 0:
                    print(f"  Processed {j}/{len(chunks)} chunks...")

            # Save to SQLite database
            if pdf_evidence:
                print(f"Extracted {len(pdf_evidence)} structured evidence records from {pdf_path.name}.")
                db.save_evidence_records(pdf_evidence)
                total_new_evidence += len(pdf_evidence)
            else:
                print(f"No structured evidence could be extracted from {pdf_path.name}.")

        except Exception as e:
            print(f"Error processing {pdf_path.name}: {e}")
            import traceback
            traceback.print_exc()

    print(f"\nEvidence extraction complete. Added {total_new_evidence} new records to database.")

    # 2. Build Crop Calendar
    print("\n=== STEP 3: Building Week-by-Week Crop Calendar ===")
    all_evidence = db.load_all_evidence()
    print(f"Total evidence records available in database: {len(all_evidence)}")

    if all_evidence:
        cal_builder = CalendarBuilder()
        calendar_entries = cal_builder.build_calendar(all_evidence)
        print(f"Aggregated evidence into {len(calendar_entries)} Crop Calendar weekly entries.")
        db.save_calendar_entries(calendar_entries)
    else:
        print("No evidence records found to build a Crop Calendar.")

    # 3. Export Data
    print("\n=== STEP 4: Exporting Database to CSV and JSON ===")
    exporter = DataExporter(db)
    exporter.export_all()

    print("\n=== PIPELINE RUN COMPLETE ===")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run Crop Calendar Extraction Pipeline")
    parser.add_argument("--limit", type=int, default=3, help="Limit the number of new PDFs to process (use -1 for no limit)")
    args = parser.parse_args()
    
    limit_val = None if args.limit < 0 else args.limit
    run_extraction_pipeline(limit=limit_val)
