import os
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
RAW_PDFS_DIR = DATA_DIR / "raw_pdfs"
DOCLING_JSON_DIR = DATA_DIR / "docling_json"
EVIDENCE_DIR = DATA_DIR / "evidence"
PROCESSED_DIR = DATA_DIR / "processed"
CALENDAR_DIR = DATA_DIR / "calendar"

# SQLite DB Path
DB_PATH = DATA_DIR / "crop_calendar.db"

# Create directories if they don't exist
for d in [RAW_PDFS_DIR, DOCLING_JSON_DIR, EVIDENCE_DIR, PROCESSED_DIR, CALENDAR_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# GLiNER Settings
GLINER_MODEL = "urchade/gliner_medium-v2.1"
GLINER_THRESHOLD = 0.45
GLINER_LABELS = [
    "crop", "crop variety", "growth stage", "disease", "pest", "insect",
    "state", "district", "weather condition", "advisory"
]
