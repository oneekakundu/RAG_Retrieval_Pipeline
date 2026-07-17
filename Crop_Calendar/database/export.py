import json
from pathlib import Path
import pandas as pd
import sys

# Import config & database
sys.path.append(str(Path(__file__).resolve().parents[1]))
import config
from database.sqlite import DatabaseManager

class DataExporter:
    """Exports SQLite tables to CSV and JSON formats."""

    def __init__(self, db_manager: DatabaseManager = None):
        self.db = db_manager or DatabaseManager()

    def export_all(self):
        """Export all evidence and crop calendar records to CSV and JSON files."""
        # Load data
        evidence = self.db.load_all_evidence()
        calendar = self.db.load_all_calendar()
        
        # 1. Export Evidence
        evidence_csv_path = config.EVIDENCE_DIR / "evidence.csv"
        evidence_json_path = config.EVIDENCE_DIR / "evidence.json"
        
        if evidence:
            df_evidence = pd.DataFrame(evidence)
            df_evidence.to_csv(evidence_csv_path, index=False, encoding="utf-8")
            df_evidence.to_json(evidence_json_path, orient="records", indent=2, force_ascii=False)
            print(f"Exported {len(evidence)} evidence records to {config.EVIDENCE_DIR}")
        else:
            print("No evidence to export.")

        # 2. Export Calendar
        calendar_csv_path = config.CALENDAR_DIR / "crop_calendar.csv"
        calendar_json_path = config.CALENDAR_DIR / "crop_calendar.json"
        
        if calendar:
            df_calendar = pd.DataFrame(calendar)
            df_calendar.to_csv(calendar_csv_path, index=False, encoding="utf-8")
            df_calendar.to_json(calendar_json_path, orient="records", indent=2, force_ascii=False)
            print(f"Exported {len(calendar)} calendar entries to {config.CALENDAR_DIR}")
        else:
            print("No crop calendar entries to export.")

if __name__ == "__main__":
    exporter = DataExporter()
    exporter.export_all()
