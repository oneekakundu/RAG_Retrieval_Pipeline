import sqlite3
import logging
from database.sqlite_manager import SQLiteManager
from extractor.knowledge_verifier import KnowledgeVerifier
from extractor.normalizer import Normalizer
from database.export import DataExporter
from database.crop_knowledge_exporter import CropKnowledgeExporter

logger = logging.getLogger("CleanDB")

def sanitize_and_audit_database():
    db = SQLiteManager()
    verifier = KnowledgeVerifier()

    records = db.load_all_records()
    logger.info(f"Auditing {len(records)} existing database records...")

    conn = db._get_connection()
    cursor = conn.cursor()

    cleaned_count = 0
    deleted_count = 0

    for rec in records:
        rec_id = rec["id"]
        crop = rec.get("crop", "")
        evidence_text = rec.get("raw_text") or rec.get("evidence") or rec.get("evidence_sentence") or ""

        # Reject invalid crop headers or empty evidence
        if not crop or crop.upper() in ["GENERAL", "UNKNOWN", "SALIENT FEATURES"] or len(evidence_text.strip()) < 5:
            cursor.execute("DELETE FROM crop_records WHERE id = ?", (rec_id,))
            cursor.execute("DELETE FROM evidence WHERE id = ?", (rec_id,))
            deleted_count += 1
            continue

        # Perform Knowledge Verifier Audit
        audited = verifier.audit_record(rec, evidence_text)

        # Update row in crop_records
        cursor.execute("""
            UPDATE crop_records SET
                crop = ?,
                state = ?,
                observation_type = ?,
                growth_stage = ?,
                sowing_status = ?,
                harvest_status = ?,
                pest = ?,
                disease = ?,
                pest_or_disease = ?,
                statistics = ?,
                evidence_sentence = ?,
                confidence = ?,
                verification_status = ?
            WHERE id = ?
        """, (
            audited["crop"],
            audited["state"],
            audited["observation_type"],
            audited["growth_stage"],
            audited["sowing_status"],
            audited["harvest_status"],
            audited["pest"],
            audited["disease"],
            audited["pest_or_disease"],
            audited["statistics"],
            audited["evidence_sentence"],
            audited["confidence"],
            audited["verification_status"],
            rec_id
        ))

        # Update row in evidence table
        cursor.execute("""
            UPDATE evidence SET
                crop = ?,
                state = ?,
                growth_stage = ?,
                pest = ?,
                disease = ?,
                confidence = ?,
                verification_status = ?
            WHERE id = ?
        """, (
            audited["crop"],
            audited["state"],
            audited["growth_stage"] or "Active Growth",
            audited["pest"] or "None",
            audited["disease"] or "None",
            audited["confidence"],
            audited["verification_status"],
            rec_id
        ))

        cleaned_count += 1

    conn.commit()
    conn.close()

    print(f"[Database Audit Complete] Cleaned {cleaned_count} records, deleted {deleted_count} invalid noise rows.")

    # Rebuild calendar matrix & re-export all Knowledge Base JSONs and CSVs
    db.rebuild_calendar()
    
    exporter = DataExporter(db)
    exporter.export_all()

    ck_exporter = CropKnowledgeExporter(db)
    ck_exporter.export_all()

    print("All crop knowledge views, knowledge_summary.json, and CSV files successfully re-exported.")

if __name__ == "__main__":
    sanitize_and_audit_database()
