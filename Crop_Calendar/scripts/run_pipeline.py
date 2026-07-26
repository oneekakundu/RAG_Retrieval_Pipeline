import argparse
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parent))
from pipeline_manager import PipelineManager

def main():
    parser = argparse.ArgumentParser(description="Incremental Crop Calendar ETL Pipeline CLI")
    parser.add_argument("--new", action="store_true", help="Process only new or modified PDFs (default)")
    parser.add_argument("--force", action="store_true", help="Reprocess every PDF regardless of registry")
    parser.add_argument("--pdf", type=str, default=None, help="Process a single specific PDF by filename")
    parser.add_argument("--upgrade", action="store_true", help="Reprocess PDFs generated with older pipeline versions")
    parser.add_argument("--from-cache", action="store_true", help="Use cached intermediate outputs whenever available")
    parser.add_argument("--from-db", action="store_true", help="Generate crop calendar directly from SQLite database")
    parser.add_argument("--provider", type=str, default=None, help="LLM Provider (gemini, openai, claude, fallback)")
    args = parser.parse_args()

    manager = PipelineManager(provider=args.provider)
    manager.run_pipeline(
        force=args.force,
        upgrade=args.upgrade,
        pdf_name_filter=args.pdf,
        from_cache=args.from_cache,
        from_db=args.from_db
    )

if __name__ == "__main__":
    main()
