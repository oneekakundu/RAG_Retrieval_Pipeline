import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
from database.sqlite_manager import SQLiteManager

class DatabaseManager(SQLiteManager):
    """Wrapper class around SQLiteManager for backwards compatibility."""
    
    def save_evidence_records(self, records: list[dict]):
        if not records:
            return
        source_pdf = records[0].get("source_pdf", "unknown.pdf")
        page_no = records[0].get("page_number", 1)
        raw_txt = records[0].get("original_text", "")
        self.save_crop_records(records, source_pdf=source_pdf, page_number=page_no, raw_text=raw_txt)

    def save_calendar_entries(self, entries: list[dict]):
        self.rebuild_calendar()

if __name__ == "__main__":
    db = DatabaseManager()
    print("DatabaseManager initialized. Stats:", db.get_stats())
