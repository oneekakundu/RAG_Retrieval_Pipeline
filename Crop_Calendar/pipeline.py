import argparse
import logging
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parent))
import config
from pipeline_manager import PipelineManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stdout
)
logger = logging.getLogger("CropCalendarPipeline")

class CropCalendarPipeline:
    """Wrapper class linking legacy calls to the production PipelineManager."""

    def __init__(self, provider: str = None):
        self.manager = PipelineManager(provider=provider)

    def run(
        self, 
        limit: int = None, 
        force: bool = False, 
        upgrade: bool = False, 
        pdf_filter: str = None,
        from_cache: bool = False,
        from_db: bool = False
    ):
        return self.manager.run_pipeline(
            force=force,
            upgrade=upgrade,
            pdf_name_filter=pdf_filter,
            from_cache=from_cache,
            from_db=from_db
        )

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Incremental Crop Calendar ETL Pipeline")
    parser.add_argument("--new", action="store_true", default=True, help="Process only new or modified PDFs")
    parser.add_argument("--force", action="store_true", help="Reprocess every PDF")
    parser.add_argument("--pdf", type=str, default=None, help="Process a specific PDF report by filename")
    parser.add_argument("--upgrade", action="store_true", help="Reprocess PDFs generated with older pipeline versions")
    parser.add_argument("--from-cache", action="store_true", help="Use cached intermediate outputs whenever available")
    parser.add_argument("--from-db", action="store_true", help="Generate crop calendar directly from SQLite without reading PDFs")
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
