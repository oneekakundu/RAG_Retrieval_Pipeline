import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional
import sys

# Import config
sys.path.append(str(Path(__file__).resolve().parents[1]))
import config
from extractor.normalizer import Normalizer

class SQLiteManager:
    """Manages the SQLite database for storing agricultural crop records and crop calendar matrix."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or config.DB_PATH
        self.init_db()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        """Initializes redesigned database schema."""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Primary Crop Records Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS crop_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_date TEXT NOT NULL,
                crop TEXT NOT NULL,
                state TEXT NOT NULL,
                district TEXT DEFAULT 'State-wide',
                growth_stage TEXT,
                pest_or_disease TEXT,
                source_pdf TEXT,
                page_number INTEGER DEFAULT 1,
                raw_text TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Backward compatibility view or table for evidence
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS evidence (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                crop TEXT,
                state TEXT,
                district TEXT,
                report_date TEXT,
                report_week INTEGER,
                growth_stage TEXT,
                pest TEXT,
                disease TEXT,
                page_number INTEGER,
                source_pdf TEXT,
                confidence REAL,
                original_text TEXT
            )
        """)

        # Crop Calendar Summary Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS crop_calendar (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                crop TEXT NOT NULL,
                state TEXT NOT NULL,
                report_week TEXT NOT NULL,
                growth_stage TEXT,
                pests TEXT,
                diseases TEXT,
                pest_or_disease TEXT,
                evidence_count INTEGER DEFAULT 1,
                confidence REAL DEFAULT 1.0
            )
        """)

        # Dynamically ensure missing columns exist for backwards compatibility & provenance
        cursor.execute("PRAGMA table_info(crop_records)")
        cr_cols = set(row["name"] for row in cursor.fetchall())
        for col_def in [
            ("confidence", "REAL DEFAULT 0.95"),
            ("source_method", "TEXT DEFAULT 'rule_based'"),
            ("pipeline_version", "TEXT DEFAULT '2.1'"),
            ("dictionary_version", "TEXT DEFAULT '1.0'"),
            ("processing_timestamp", "TIMESTAMP"),
            ("crop_operation", "TEXT"),
            ("pest", "TEXT"),
            ("disease", "TEXT"),
            ("severity", "TEXT"),
            ("affected_area", "TEXT"),
            ("observation_type", "TEXT DEFAULT 'Other'"),
            ("sowing_status", "TEXT"),
            ("harvest_status", "TEXT"),
            ("statistics", "TEXT"),
            ("verification_status", "TEXT DEFAULT 'VERIFIED'"),
            ("verification_notes", "TEXT"),
            ("chunk_id", "TEXT"),
            ("evidence_sentence", "TEXT")
        ]:
            if col_def[0] not in cr_cols:
                cursor.execute(f"ALTER TABLE crop_records ADD COLUMN {col_def[0]} {col_def[1]}")

        cursor.execute("PRAGMA table_info(crop_calendar)")
        cc_cols = set(row["name"] for row in cursor.fetchall())
        for col_def in [
            ("sowing_status", "TEXT"),
            ("harvest_status", "TEXT"),
            ("statistics", "TEXT")
        ]:
            if col_def[0] not in cc_cols:
                cursor.execute(f"ALTER TABLE crop_calendar ADD COLUMN {col_def[0]} {col_def[1]}")

        cursor.execute("PRAGMA table_info(evidence)")
        ev_cols = set(row["name"] for row in cursor.fetchall())
        for col_def in [
            ("source_method", "TEXT DEFAULT 'rule_based'"),
            ("pipeline_version", "TEXT DEFAULT '2.1'"),
            ("dictionary_version", "TEXT DEFAULT '1.0'"),
            ("chunk_id", "TEXT"),
            ("verification_status", "TEXT DEFAULT 'VERIFIED'")
        ]:
            if col_def[0] not in ev_cols:
                cursor.execute(f"ALTER TABLE evidence ADD COLUMN {col_def[0]} {col_def[1]}")

        # PDF Registry Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS processed_pdfs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pdf_name TEXT UNIQUE NOT NULL,
                pdf_hash TEXT NOT NULL,
                report_date TEXT,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                pipeline_version TEXT,
                dictionary_version TEXT,
                docling_version TEXT,
                status TEXT DEFAULT 'SUCCESS',
                processing_time_seconds REAL DEFAULT 0.0,
                error_message TEXT
            )
        """)

        conn.commit()
        conn.close()

    def save_crop_records(self, records: List[Dict[str, Any]], source_pdf: str, page_number: int = 1, raw_text: str = ""):
        """Inserts validated crop records into crop_records and evidence tables using 4-tuple deduplication."""
        if not records:
            return 0

        conn = self._get_connection()
        cursor = conn.cursor()

        inserted_count = 0
        for rec in records:
            report_date = rec.get("report_week") or rec.get("report_date") or rec.get("week", "")
            crop = rec.get("crop", "Unknown")
            state = rec.get("state", "All India")
            district = rec.get("district", "State-wide")
            stage = rec.get("growth_stage")
            pest = rec.get("pest") or rec.get("pests")
            disease = rec.get("disease") or rec.get("diseases")
            pest_disease = rec.get("pest_or_disease") or pest or disease
            sowing_stat = rec.get("sowing_status")
            harvest_stat = rec.get("harvest_status")
            stats = rec.get("statistics")
            obs_type = rec.get("observation_type", "Other")
            chunk_id = rec.get("chunk_id", "")
            ver_status = rec.get("verification_status", "VERIFIED")
            
            # Helper to clean markdown artifacts safely
            def _clean(val):
                if not val: return val
                import re
                s = str(val).strip()
                s = re.sub(r"(?m)^\s*#+\s*", "", s)
                s = re.sub(r"\s*\|\s*", " ", s)
                s = re.sub(r"[ \t]{2,}", " ", s)
                return s.strip()

            chunk_evidence = rec.get("evidence_sentence") or rec.get("evidence") or rec.get("raw_text") or raw_text
            chunk_evidence = _clean(chunk_evidence)
            stats = _clean(stats) if stats else stats
            confidence = float(rec.get("confidence", 0.95))

            # Deduplication: (report_date, crop, state, chunk_evidence)
            cursor.execute("""
                SELECT id FROM crop_records 
                WHERE report_date = ? AND crop = ? AND state = ? 
                AND (raw_text = ? OR evidence = ? OR evidence_sentence = ?)
            """, (report_date, crop, state, chunk_evidence, chunk_evidence, chunk_evidence))
            
            if cursor.fetchone():
                continue

            cursor.execute("""
                INSERT INTO crop_records (
                    report_date, crop, state, district, growth_stage, 
                    pest_or_disease, source_pdf, page_number, raw_text,
                    confidence, source_method, pipeline_version, dictionary_version,
                    crop_operation, pest, disease, severity, affected_area,
                    irrigation, nutrient_management, section_heading, evidence, 
                    observation_type, sowing_status, harvest_status,
                    statistics, verification_status, chunk_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                report_date, crop, state, district, stage,
                pest_disease, rec.get("source_pdf", source_pdf), rec.get("page_number", page_number), chunk_evidence,
                confidence, rec.get("source_method", "rule_based"), config.PIPELINE_VERSION, config.DICTIONARY_VERSION,
                rec.get("crop_operation"), pest, disease, rec.get("severity"), rec.get("affected_area"),
                rec.get("irrigation"), rec.get("nutrient_management"), rec.get("section_heading", "General Observation"), chunk_evidence, 
                obs_type, sowing_stat, harvest_stat,
                stats, ver_status, chunk_id
            ))

            # Also populate legacy evidence table for Streamlit page compatibility
            cursor.execute("""
                INSERT INTO evidence (
                    crop, state, district, report_date, report_week,
                    growth_stage, pest, disease, page_number, 
                    source_pdf, confidence, original_text,
                    source_method, pipeline_version, dictionary_version, chunk_id, verification_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                crop, state, district, report_date, 
                int(report_date.split("-")[1]) if "-" in report_date else 1,
                stage or "Active Growth", pest or "None", disease or "None",
                rec.get("page_number", page_number), source_pdf, confidence, chunk_evidence,
                rec.get("source_method", "rule_based"), config.PIPELINE_VERSION, config.DICTIONARY_VERSION, chunk_id, ver_status
            ))

            inserted_count += 1

        conn.commit()
        conn.close()

        # Update crop_calendar table
        self.rebuild_calendar()
        return inserted_count

    def rebuild_calendar(self):
        """Aggregates verified crop_records into crop_calendar summary matrix."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM crop_calendar")
        cursor.execute("""
            SELECT crop, state, report_date, 
                   MAX(growth_stage) as growth_stage,
                   GROUP_CONCAT(DISTINCT sowing_status) as sowing_status,
                   GROUP_CONCAT(DISTINCT harvest_status) as harvest_status,
                   GROUP_CONCAT(DISTINCT pest) as pests,
                   GROUP_CONCAT(DISTINCT disease) as diseases,
                   GROUP_CONCAT(DISTINCT statistics) as statistics,
                   COUNT(*) as ev_count,
                   AVG(confidence) as avg_confidence
            FROM crop_records
            WHERE verification_status = 'VERIFIED' OR verification_status IS NULL
            GROUP BY crop, state, report_date
        """)
        rows = cursor.fetchall()

        from extractor.normalizer import Normalizer

        for row in rows:
            p_val = row["pests"]
            d_val = row["diseases"]

            # Filter out non-pest/disease text using strict Normalizer validation
            p_clean = "None Reported"
            if p_val:
                p_items = [Normalizer.normalize_pest_disease(p) for p in p_val.split(",") if Normalizer.normalize_pest_disease(p)]
                if p_items:
                    p_clean = "; ".join(sorted(list(set(p_items))))

            d_clean = "None Reported"
            if d_val:
                d_items = [Normalizer.normalize_pest_disease(d) for d in d_val.split(",") if Normalizer.normalize_pest_disease(d)]
                if d_items:
                    d_clean = "; ".join(sorted(list(set(d_items))))

            cursor.execute("""
                INSERT INTO crop_calendar (
                    crop, state, report_week, growth_stage, 
                    pests, diseases, pest_or_disease, 
                    evidence_count, confidence, sowing_status, harvest_status, statistics
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                row["crop"], row["state"], row["report_date"],
                row["growth_stage"] or "Active Growth",
                p_clean, d_clean, p_clean if p_clean != "None Reported" else d_clean,
                row["ev_count"],
                round(row["avg_confidence"] or 1.0, 2),
                row["sowing_status"],
                row["harvest_status"],
                row["statistics"]
            ))

        conn.commit()
        conn.close()

    def load_all_records(self) -> List[Dict[str, Any]]:
        """Load all crop records as list of dicts."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM crop_records ORDER BY report_date DESC, crop ASC")
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows

    def load_all_evidence(self) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM evidence ORDER BY report_date DESC")
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows

    def load_all_calendar(self) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM crop_calendar ORDER BY report_week DESC, crop ASC")
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows

    def get_stats(self) -> Dict[str, Any]:
        """Returns database counts and statistics."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM crop_records")
        total_records = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM crop_calendar")
        total_calendar = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(DISTINCT source_pdf) FROM crop_records")
        total_pdfs = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(DISTINCT crop) FROM crop_records")
        total_crops = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(DISTINCT state) FROM crop_records")
        total_states = cursor.fetchone()[0]

        conn.close()
        return {
            "total_evidence": total_records,
            "total_records": total_records,
            "total_calendar": total_calendar,
            "total_pdfs": total_pdfs,
            "total_crops": total_crops,
            "total_states": total_states
        }
    def get_processed_pdf(self, pdf_name: str) -> Optional[Dict[str, Any]]:
        """Get record from processed_pdfs registry for a given PDF name."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM processed_pdfs WHERE pdf_name = ?", (pdf_name,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def get_all_processed_pdfs(self) -> Dict[str, Dict[str, Any]]:
        """Get dictionary mapping pdf_name to registry info."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM processed_pdfs")
        rows = cursor.fetchall()
        conn.close()
        return {r["pdf_name"]: dict(r) for r in rows}

    def register_processed_pdf(
        self, 
        pdf_name: str, 
        pdf_hash: str, 
        report_date: str, 
        status: str = "SUCCESS", 
        processing_time: float = 0.0, 
        error_msg: Optional[str] = None
    ):
        """Register or update PDF processing status in the registry."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO processed_pdfs (
                pdf_name, pdf_hash, report_date, pipeline_version, 
                dictionary_version, docling_version, status, 
                processing_time_seconds, error_message
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(pdf_name) DO UPDATE SET
                pdf_hash = excluded.pdf_hash,
                report_date = excluded.report_date,
                processed_at = CURRENT_TIMESTAMP,
                pipeline_version = excluded.pipeline_version,
                dictionary_version = excluded.dictionary_version,
                docling_version = excluded.docling_version,
                status = excluded.status,
                processing_time_seconds = excluded.processing_time_seconds,
                error_message = excluded.error_message
        """, (
            pdf_name, pdf_hash, report_date, 
            config.PIPELINE_VERSION, config.DICTIONARY_VERSION, config.DOCLING_VERSION, 
            status, round(processing_time, 2), error_msg
        ))
        conn.commit()
        conn.close()

    def delete_records_by_pdf(self, pdf_name: str):
        """Remove crop records and evidence for a specific PDF (used before reprocessing)."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM crop_records WHERE source_pdf = ?", (pdf_name,))
        cursor.execute("DELETE FROM evidence WHERE source_pdf = ?", (pdf_name,))
        conn.commit()
        conn.close()

    def load_failed_pdfs(self) -> List[Dict[str, Any]]:
        """Load list of PDFs that failed processing."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM processed_pdfs WHERE status = 'FAILED'")
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows

if __name__ == "__main__":
    db = SQLiteManager()
    print("Database stats:", db.get_stats())