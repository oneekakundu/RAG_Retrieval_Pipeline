import hashlib
import json
import logging
import pickle
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

import config
from database.sqlite_manager import SQLiteManager
from extractor.docling_parser import DoclingParser
from extractor.section_detector import SectionDetector
from extractor.crop_chunker import CropChunker
from extractor.context_resolver import ContextResolver
from extractor.llm_extractor import get_extractor
from extractor.validators import validate_and_clean_record

logger = logging.getLogger("PipelineManager")

class PipelineManager:
    """
    Production-grade ETL Controller for Crop Calendar Processing.
    Handles PDF registry, SHA256 hashing, multi-stage caching, version-aware reprocessing,
    and resilience against pipeline failures.
    """

    def __init__(self, provider: Optional[str] = None):
        self.db = SQLiteManager()
        self.parser = DoclingParser()
        self.detector = SectionDetector()
        self.chunker = CropChunker()
        self.resolver = ContextResolver()
        self.extractor = get_extractor(provider)

    @staticmethod
    def compute_sha256(file_path: Path) -> str:
        """Calculate SHA256 hash of a file."""
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def get_cache_filepath(self, stage: str, pdf_stem: str, ext: str = ".json") -> Path:
        """Construct cache filepath for a given stage."""
        stage_dir = config.CACHE_DIR / stage
        stage_dir.mkdir(parents=True, exist_ok=True)
        return stage_dir / f"{pdf_stem}{ext}"

    def save_stage_cache(self, stage: str, pdf_stem: str, data: Any, ext: str = ".json"):
        """Save data to stage cache with metadata."""
        if not config.CACHE_ENABLED:
            return

        cache_path = self.get_cache_filepath(stage, pdf_stem, ext)
        meta_payload = {
            "metadata": {
                "pipeline_version": config.PIPELINE_VERSION,
                "dictionary_version": config.DICTIONARY_VERSION,
                "normalization_version": config.NORMALIZATION_VERSION,
                "timestamp": datetime.now().isoformat()
            },
            "data": data
        }

        try:
            if ext == ".json":
                with open(cache_path, "w", encoding="utf-8") as f:
                    json.dump(meta_payload, f, indent=2, ensure_ascii=False)
            elif ext == ".pkl":
                with open(cache_path, "wb") as f:
                    pickle.dump(meta_payload, f)
        except Exception as e:
            logger.warning(f"Failed to write stage cache for {stage}/{pdf_stem}: {e}")

    def load_stage_cache(self, stage: str, pdf_stem: str, ext: str = ".json") -> Optional[Any]:
        """Load data from stage cache if valid."""
        if not config.CACHE_ENABLED:
            return None

        cache_path = self.get_cache_filepath(stage, pdf_stem, ext)
        if not cache_path.exists():
            return None

        try:
            if ext == ".json":
                with open(cache_path, "r", encoding="utf-8") as f:
                    payload = json.load(f)
            elif ext == ".pkl":
                with open(cache_path, "rb") as f:
                    payload = pickle.load(f)

            meta = payload.get("metadata", {})
            # Ensure cache was produced by compatible pipeline version
            if meta.get("pipeline_version") == config.PIPELINE_VERSION:
                return payload.get("data")
        except Exception as e:
            logger.warning(f"Cache load failed for {stage}/{pdf_stem}: {e}")

        return None

    def scan_pdfs(self) -> List[Tuple[Path, str]]:
        """Scan PDF directory and return list of (pdf_path, pdf_hash)."""
        logger.info("Scanning PDF folder...")
        pdf_files = list(config.RAW_PDFS_DIR.glob("*.pdf"))
        results = []
        for pdf_path in pdf_files:
            pdf_hash = self.compute_sha256(pdf_path)
            results.append((pdf_path, pdf_hash))
        return results

    def should_process(
        self, 
        pdf_name: str, 
        pdf_hash: str, 
        force: bool = False, 
        upgrade: bool = False
    ) -> bool:
        """Determines if a PDF needs processing based on hash, status, and pipeline version."""
        if force:
            return True

        registry_record = self.db.get_processed_pdf(pdf_name)
        if not registry_record:
            return True # New PDF

        if registry_record.get("status") == "FAILED":
            return True # Failed previous attempt

        if registry_record.get("pdf_hash") != pdf_hash:
            logger.info(f"PDF hash changed for {pdf_name}. Reprocessing...")
            return True # PDF file content changed

        if upgrade and registry_record.get("pipeline_version") != config.PIPELINE_VERSION:
            logger.info(f"Older pipeline version detected for {pdf_name} ({registry_record.get('pipeline_version')}). Reprocessing...")
            return True

        return False # Already processed

    def process_single_pdf(
        self, 
        pdf_path: Path, 
        pdf_hash: str, 
        from_cache: bool = False
    ) -> Dict[str, Any]:
        """
        Executes multi-stage cached processing on a single PDF file.
        Returns execution statistics dictionary.
        """
        pdf_name = pdf_path.name
        pdf_stem = pdf_path.stem
        start_time = time.time()

        logger.info(f"--- Processing PDF: {pdf_name} ---")

        try:
            # Clear old records if reprocessing
            self.db.delete_records_by_pdf(pdf_name)

            # Check if pre-processed numbered JSON record already exists
            existing_processed_files = list(config.PROCESSED_RECORDS_DIR.glob(f"*_{pdf_stem}.json"))
            if not existing_processed_files:
                for pfile in config.PROCESSED_RECORDS_DIR.glob("*.json"):
                    try:
                        with open(pfile, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            if data.get("pdf_name") == pdf_name and data.get("pdf_hash") == pdf_hash:
                                existing_processed_files.append(pfile)
                                break
                    except Exception:
                        pass

            if existing_processed_files and not from_cache:
                proc_file = existing_processed_files[0]
                logger.info(f"[LOG: Processed Store] Using already processed numbered record file: {proc_file.name} for {pdf_name}")
                with open(proc_file, "r", encoding="utf-8") as f:
                    proc_data = json.load(f)
                valid_records = proc_data.get("records", [])
                report_week = proc_data.get("report_week", "")
                inserted = self.db.save_crop_records(valid_records, pdf_name)
                elapsed = time.time() - start_time
                self.db.register_processed_pdf(pdf_name, pdf_hash, report_week, "SUCCESS", elapsed)
                return {
                    "pdf_name": pdf_name,
                    "status": "SUCCESS",
                    "records_inserted": inserted,
                    "elapsed_seconds": elapsed
                }

            # Stage 1: Docling Parsing
            doc_dict = None
            md_content = None
            report_week = None

            if from_cache:
                docling_cache = self.load_stage_cache("docling", pdf_stem, ".json")
                if docling_cache:
                    logger.info(f"Loading cached Docling output for {pdf_name}")
                    doc_dict = docling_cache.get("doc_dict")
                    md_content = docling_cache.get("md_content")
                    report_week = docling_cache.get("report_week")

            if not doc_dict or not md_content or not report_week:
                doc_dict, md_content, report_week = self.parser.parse_pdf(pdf_path)
                self.save_stage_cache("docling", pdf_stem, {
                    "doc_dict": doc_dict, "md_content": md_content, "report_week": report_week
                }, ".json")
                logger.info(f"Docling parsing complete for {pdf_name} (report_week: {report_week})")

            # Stage 2: Section Detection & Removal
            filtered_blocks = None
            if from_cache:
                filtered_blocks = self.load_stage_cache("cleaned", pdf_stem, ".json")
                if filtered_blocks:
                    logger.info(f"Loading cached cleaned sections for {pdf_name}")

            if not filtered_blocks:
                filtered_blocks = self.detector.filter_document(doc_dict, md_content)
                self.save_stage_cache("cleaned", pdf_stem, filtered_blocks, ".json")
                logger.info(f"Filtered {len(filtered_blocks)} clean section blocks for {pdf_name}")

            # Stage 3: Crop Paragraph Chunking & Context Resolution
            chunks = None
            if from_cache:
                chunks = self.load_stage_cache("chunks", pdf_stem, ".json")
                if chunks:
                    logger.info(f"Loading cached chunks for {pdf_name}")

            if not chunks:
                raw_chunks = self.chunker.create_crop_chunks(filtered_blocks, pdf_name)
                chunks = self.resolver.resolve_context(raw_chunks)
                self.save_stage_cache("chunks", pdf_stem, chunks, ".json")
                logger.info(f"Generated {len(chunks)} crop description chunks for {pdf_name}")

            # Stage 4: Semantic Interpretation, Stage 5: Document Verification, Stage 6: Validation
            valid_records = []
            if from_cache:
                valid_records = self.load_stage_cache("validated", pdf_stem, ".json")
                if valid_records:
                    logger.info(f"Loading cached validated records for {pdf_name}")

            if not valid_records:
                from extractor.semantic_interpreter import SemanticInterpreter
                from extractor.verification_engine import VerificationEngine
                from extractor.validator_layer import ValidationLayer
                from database.crop_knowledge import CropKnowledgeManager

                interpreter = SemanticInterpreter()
                verifier = VerificationEngine()
                validator = ValidationLayer()
                ckm = CropKnowledgeManager()

                logger.info(f"Running Document-Grounded Semantic Interpretation & Verification for {len(chunks)} chunks...")
                verified_records = []

                for idx, chunk in enumerate(chunks, 1):
                    try:
                        chunk_id = f"{pdf_stem}_p{chunk.get('page_number', 1)}_c{idx}"
                        chunk["chunk_id"] = chunk_id
                        
                        # Save original chunk to permanent evidence repository
                        ckm.save_chunk(chunk, pdf_name, pdf_hash, report_week)

                        # 1. Semantic Interpretation
                        schema = interpreter.interpret(chunk, report_week)
                        if not schema:
                            continue

                        # 2. Document Verification against original chunk text
                        verified_rec, audit_log = verifier.verify(
                            schema=schema,
                            original_chunk_text=chunk.get("chunk_text", ""),
                            source_pdf=pdf_name,
                            page_number=chunk.get("page_number", 1),
                            chunk_id=chunk_id
                        )

                        if verified_rec:
                            verified_records.append(verified_rec)

                    except Exception as chunk_err:
                        logger.error(f"Chunk {idx} error in {pdf_name}: {chunk_err}")
                        continue

                # 3. Post-Verification Validation Layer
                valid_records_obj, rejected_count = validator.validate_records(verified_records)
                logger.info(f"[LOG: Validation Layer] Validated {len(valid_records_obj)} records ({rejected_count} rejected) for {pdf_name}")

                valid_records = [r.model_dump() for r in valid_records_obj]
                self.save_stage_cache("validated", pdf_stem, valid_records, ".json")

            # Stage 6: Database Insertion
            inserted = self.db.save_crop_records(valid_records, pdf_name)
            elapsed = time.time() - start_time

            # Save numbered processed JSON record to data/processed_records/
            existing_count = len(list(config.PROCESSED_RECORDS_DIR.glob("*.json"))) + 1
            proc_file = config.PROCESSED_RECORDS_DIR / f"{existing_count:03d}_{pdf_stem}.json"
            if not proc_file.exists():
                with open(proc_file, "w", encoding="utf-8") as f:
                    json.dump({
                        "seq_index": existing_count,
                        "pdf_name": pdf_name,
                        "pdf_hash": pdf_hash,
                        "report_week": report_week,
                        "processed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "record_count": len(valid_records),
                        "records": valid_records
                    }, f, indent=2, ensure_ascii=False)
                logger.info(f"Saved numbered processed record file: {proc_file.name}")

            # Register success in registry
            self.db.register_processed_pdf(
                pdf_name=pdf_name,
                pdf_hash=pdf_hash,
                report_date=report_week,
                status="SUCCESS",
                processing_time=elapsed
            )

            logger.info(f"Inserted {inserted} records for {pdf_name} in {elapsed:.2f} seconds")
            return {
                "pdf_name": pdf_name,
                "status": "SUCCESS",
                "records_inserted": inserted,
                "elapsed_seconds": elapsed
            }

        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"Failed processing {pdf_name}: {e}")
            self.db.register_processed_pdf(
                pdf_name=pdf_name,
                pdf_hash=pdf_hash,
                report_date="UNKNOWN",
                status="FAILED",
                processing_time=elapsed,
                error_msg=str(e)
            )
            return {
                "pdf_name": pdf_name,
                "status": "FAILED",
                "records_inserted": 0,
                "elapsed_seconds": elapsed,
                "error": str(e)
            }

    def sync_processed_records(self):
        """Generates numbered processed JSON record files for all processed PDFs in PROCESSED_RECORDS_DIR."""
        records = self.db.load_all_records()
        by_pdf = {}
        for r in records:
            pdf = r.get("source_pdf", "unknown.pdf")
            by_pdf.setdefault(pdf, []).append(r)

        for idx, (pdf_name, recs) in enumerate(by_pdf.items(), 1):
            pdf_stem = Path(pdf_name).stem
            proc_file = config.PROCESSED_RECORDS_DIR / f"{idx:03d}_{pdf_stem}.json"
            if not proc_file.exists():
                report_week = recs[0].get("report_week") if recs else ""
                with open(proc_file, "w", encoding="utf-8") as f:
                    json.dump({
                        "seq_index": idx,
                        "pdf_name": pdf_name,
                        "report_week": report_week,
                        "processed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "record_count": len(recs),
                        "records": recs
                    }, f, indent=2, ensure_ascii=False)
                logger.info(f"Synced numbered record file: {proc_file.name}")

    def run_pipeline(
        self, 
        mode_new: bool = True, 
        force: bool = False, 
        upgrade: bool = False, 
        pdf_name_filter: Optional[str] = None,
        from_cache: bool = False,
        from_db: bool = False,
        provider: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Main entry point for pipeline execution.
        Supports CLI flags: --new, --force, --upgrade, --pdf, --from-cache, --from-db
        """
        start_pipeline_time = time.time()
        logger.info("Checking registry...")

        # If --from-db mode, regenerate crop calendar matrix and export without parsing PDFs
        if from_db:
            logger.info("[MODE: FROM-DB] Rebuilding Crop Calendar matrix directly from SQLite database...")
            self.db.rebuild_calendar()
            self.sync_processed_records()
            from database.export import DataExporter
            exporter = DataExporter(self.db)
            exporter.export_all()
            
            from database.crop_knowledge import CropKnowledgeManager
            ckm = CropKnowledgeManager()
            ckm.export_derived_csvs(self.db)
            total_elapsed = time.time() - start_pipeline_time
            stats = self.db.get_stats()
            print("\n------------------------------------")
            print("Mode:               FROM-DB (No PDF Parsing)")
            print(f"Total Records:      {stats['total_records']}")
            print(f"Calendar Entries:   {stats['total_calendar']}")
            print(f"Processing Time:    {total_elapsed:.2f} sec")
            print("------------------------------------\n")
            return stats

        # Scan PDF directory
        scanned_pdfs = self.scan_pdfs()
        total_found = len(scanned_pdfs)

        if pdf_name_filter:
            scanned_pdfs = [(path, h) for path, h in scanned_pdfs if path.name == pdf_name_filter or pdf_name_filter in path.name]

        processed_count = 0
        skipped_count = 0
        total_inserted = 0

        for pdf_path, pdf_hash in scanned_pdfs:
            if not self.should_process(pdf_path.name, pdf_hash, force=force, upgrade=upgrade):
                logger.info(f"Already processed: {pdf_path.name} -> Skipping")
                skipped_count += 1
                continue

            result = self.process_single_pdf(pdf_path, pdf_hash, from_cache=from_cache)
            if result["status"] == "SUCCESS":
                processed_count += 1
                total_inserted += result["records_inserted"]
            else:
                logger.warning(f"Processing failed for {pdf_path.name}, continuing next PDF...")

        # Rebuild calendar matrix & export files
        self.db.rebuild_calendar()
        self.sync_processed_records()
        from database.export import DataExporter
        exporter = DataExporter(self.db)
        exporter.export_all()
        
        from database.crop_knowledge import CropKnowledgeManager
        ckm = CropKnowledgeManager()
        ckm.export_derived_csvs(self.db)

        # Run Evaluation metrics export
        from scripts.evaluation import Evaluator
        evaluator = Evaluator(self.db)
        eval_metrics = evaluator.evaluate()

        total_elapsed_time = time.time() - start_pipeline_time

        # Print formatted summary table as specified in requirements
        print("\n------------------------------------")
        print(f"PDFs Found          {total_found}")
        print(f"Processed           {processed_count}")
        print(f"Skipped             {skipped_count}")
        print(f"Records Inserted    {total_inserted}")
        print(f"Precision           {eval_metrics.get('precision', 1.0)}")
        print(f"Recall              {eval_metrics.get('recall', 1.0)}")
        print(f"F1 Score            {eval_metrics.get('f1_score', 1.0)}")
        print(f"Processing Time     {total_elapsed_time:.1f} sec")
        print("------------------------------------\n")

        return {
            "total_found": total_found,
            "processed": processed_count,
            "skipped": skipped_count,
            "records_inserted": total_inserted,
            "elapsed_seconds": total_elapsed_time
        }
