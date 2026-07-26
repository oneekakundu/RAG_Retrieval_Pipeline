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
PROCESSED_RECORDS_DIR = DATA_DIR / "processed_records"
CROP_KNOWLEDGE_DIR = DATA_DIR / "crop_knowledge"

# SQLite DB Path
DB_PATH = DATA_DIR / "crop_calendar.db"

# Create directories if they don't exist
for d in [RAW_PDFS_DIR, DOCLING_JSON_DIR, EVIDENCE_DIR, PROCESSED_DIR, CALENDAR_DIR, PROCESSED_RECORDS_DIR, CROP_KNOWLEDGE_DIR]:
    d.mkdir(parents=True, exist_ok=True)

from dotenv import load_dotenv

# Load .env file from Crop_Calendar or workspace root
env_path = Path(__file__).resolve().parent / ".env"
if not env_path.exists():
    env_path = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(dotenv_path=env_path)

# LLM Configuration
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini")
LLM_MODEL = os.getenv("LLM_MODEL", "gemini-2.5-flash")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Prompts Path
PROMPTS_DIR = BASE_DIR / "prompts"
PROMPTS_DIR.mkdir(parents=True, exist_ok=True)

# ETL Pipeline Versioning & Settings
PIPELINE_VERSION = "2.1"
DICTIONARY_VERSION = "1.0"
NORMALIZATION_VERSION = "1.0"
DOCLING_VERSION = "2.112.0"

# Caching Configuration
CACHE_ENABLED = True
CACHE_DIR = DATA_DIR / "cache"
CACHE_DOCLING_DIR = CACHE_DIR / "docling"
CACHE_CLEANED_DIR = CACHE_DIR / "cleaned"
CACHE_CHUNKS_DIR = CACHE_DIR / "chunks"
CACHE_EXTRACTED_DIR = CACHE_DIR / "extracted"
CACHE_VALIDATED_DIR = CACHE_DIR / "validated"

# Supported File Extensions
SUPPORTED_FILE_TYPES = [".pdf"]

# Create cache directories
for d in [
    RAW_PDFS_DIR, DOCLING_JSON_DIR, EVIDENCE_DIR, PROCESSED_DIR, CALENDAR_DIR,
    CACHE_DIR, CACHE_DOCLING_DIR, CACHE_CLEANED_DIR, CACHE_CHUNKS_DIR, CACHE_EXTRACTED_DIR, CACHE_VALIDATED_DIR
]:
    d.mkdir(parents=True, exist_ok=True)

# GLiNER Settings (Legacy fallback)
GLINER_MODEL = "urchade/gliner_medium-v2.1"
GLINER_THRESHOLD = 0.45
GLINER_LABELS = [
    "crop", "crop variety", "growth stage", "disease", "pest", "insect",
    "state", "district", "weather condition", "advisory"
]


