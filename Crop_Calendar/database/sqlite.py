import sqlite3
from pathlib import Path
import sys

# Import config
sys.path.append(str(Path(__file__).resolve().parents[1]))
import config

class DatabaseManager:
    """Manages the SQLite database for storing agricultural evidence and crop calendars."""

    def __init__(self, db_path: Path = None):
        self.db_path = db_path or config.DB_PATH
        self.init_db()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        """Initializes database tables if they do not exist."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Evidence Table
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
                weather_condition TEXT,
                advisory TEXT,
                page_number INTEGER,
                source_pdf TEXT,
                confidence REAL,
                original_text TEXT
            )
        """)

        # Crop Calendar Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS crop_calendar (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                crop TEXT,
                state TEXT,
                report_week INTEGER,
                growth_stage TEXT,
                pests TEXT,
                diseases TEXT,
                advisories TEXT,
                evidence_count INTEGER,
                confidence REAL
            )
        """)
        
        conn.commit()
        conn.close()

    def save_evidence_records(self, records: list[dict]):
        """Inserts multiple evidence records into the database."""
        if not records:
            return
            
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Check for duplicates by comparing crop, state, report_date, page_number and original_text
        cursor.executemany("""
            INSERT INTO evidence (
                crop, state, district, report_date, report_week, 
                growth_stage, pest, disease, weather_condition, 
                advisory, page_number, source_pdf, confidence, original_text
            ) VALUES (
                :crop, :state, :district, :report_date, :report_week, 
                :growth_stage, :pest, :disease, :weather_condition, 
                :advisory, :page_number, :source_pdf, :confidence, :original_text
            )
        """, records)
        
        conn.commit()
        conn.close()

    def save_calendar_entries(self, entries: list[dict]):
        """Saves crop calendar entries, clearing old ones first."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM crop_calendar")
        
        cursor.executemany("""
            INSERT INTO crop_calendar (
                crop, state, report_week, growth_stage, 
                pests, diseases, advisories, evidence_count, confidence
            ) VALUES (
                :crop, :state, :report_week, :growth_stage, 
                :pests, :diseases, :advisories, :evidence_count, :confidence
            )
        """, entries)
        
        conn.commit()
        conn.close()

    def load_all_evidence(self) -> list[dict]:
        """Loads all evidence records as a list of dicts."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM evidence")
        rows = cursor.fetchall()
        
        results = [dict(row) for row in rows]
        conn.close()
        return results

    def load_all_calendar(self) -> list[dict]:
        """Loads all crop calendar entries as a list of dicts."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM crop_calendar")
        rows = cursor.fetchall()
        
        results = [dict(row) for row in rows]
        conn.close()
        return results

    def get_stats(self) -> dict:
        """Returns processing statistics from the database."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM evidence")
        total_evidence = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM crop_calendar")
        total_calendar = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT source_pdf) FROM evidence")
        total_pdfs = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT crop) FROM evidence")
        total_crops = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT state) FROM evidence")
        total_states = cursor.fetchone()[0]
        
        conn.close()
        return {
            "total_evidence": total_evidence,
            "total_calendar": total_calendar,
            "total_pdfs": total_pdfs,
            "total_crops": total_crops,
            "total_states": total_states
        }

if __name__ == "__main__":
    db = DatabaseManager()
    print("Database stats:", db.get_stats())
