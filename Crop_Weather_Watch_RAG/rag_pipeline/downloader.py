import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import pandas as pd
import requests

from .utils import clean_filename, ensure_directory, setup_logger


class WeatherWatchDownloader:
    """Download Weather Watch PDFs from the government portal."""

    def __init__(self, output_dir: Optional[os.PathLike | str] = None, logger=None):
        self.output_dir = Path(output_dir or Path(__file__).resolve().parents[1] / "data" / "pdfs")
        self.logger = logger or setup_logger("downloader")
        ensure_directory(self.output_dir)

    def fetch_metadata(self, url: str = "https://agriwelfare.gov.in/en/getMOMDetail") -> list[dict]:
        """Fetch metadata entries for Weather Watch documents from the portal."""
        headers = {
            "User-Agent": "Mozilla/5.0",
            "X-Requested-With": "XMLHttpRequest",
        }
        payload = {"Category": "Minutes Of Meeting", "Status": "Y"}
        response = requests.post(url, headers=headers, data=payload, timeout=30)
        response.raise_for_status()
        json_data = response.json()
        return json_data.get("data", [])

    def download_pdf(self, pdf_url: str, target_path: Path) -> bool:
        """Download a single PDF to the target path."""
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://agriwelfare.gov.in/en/weather-watch",
        }
        response = requests.get(pdf_url, headers=headers, timeout=60)
        if response.status_code != 200:
            self.logger.warning("Failed to download %s: %s", pdf_url, response.status_code)
            return False
        target_path.write_bytes(response.content)
        self.logger.info("Downloaded %s", target_path.name)
        return True

    def filter_by_date(self, records: List[dict], start_date: str, end_date: str) -> List[dict]:
        """Filter records between the provided start and end dates."""
        parsed_records = []
        for record in records:
            publish_date = record.get("PublishDate")
            if not publish_date:
                continue
            try:
                parsed_date = pd.to_datetime(publish_date, dayfirst=True)
            except Exception:
                continue
            parsed_records.append((parsed_date, record))

        start_dt = pd.to_datetime(start_date, dayfirst=True)
        end_dt = pd.to_datetime(end_date, dayfirst=True)
        filtered = [record for parsed_date, record in parsed_records if start_dt <= parsed_date <= end_dt]
        return filtered

    def download_reports(self, records: List[dict], week_name: str, limit: Optional[int] = None) -> List[dict]:
        """Download the requested number of reports and return metadata for the downloaded files."""
        if limit is not None:
            records = records[:limit]

        week_dir = self.output_dir / week_name / "pdf"
        ensure_directory(week_dir)
        downloaded = []
        for record in records:
            title = record.get("Title", "unknown")
            pdf_link = record.get("PDF Link") or ("https://agriwelfare.gov.in" + record.get("document_path", ""))
            if not pdf_link:
                continue
            safe_name = clean_filename(title) + ".pdf"
            target_path = week_dir / safe_name
            if target_path.exists():
                self.logger.info("Skipping existing PDF %s", target_path.name)
                downloaded.append({"title": title, "pdf_path": str(target_path), "pdf_url": pdf_link})
                continue
            if self.download_pdf(pdf_link, target_path):
                downloaded.append({"title": title, "pdf_path": str(target_path), "pdf_url": pdf_link})
        return downloaded
