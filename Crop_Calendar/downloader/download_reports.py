import os
import requests
import shutil
from pathlib import Path
import pandas as pd
from bs4 import BeautifulSoup
import sys

# Import config from parent directory
sys.path.append(str(Path(__file__).resolve().parents[1]))
import config

def clean_filename(filename: str) -> str:
    """Clean the filename to remove invalid characters."""
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, "_")
    return filename.strip()

def fetch_and_download(start_date: str = "15-07-2025", end_date: str = "16-07-2026"):
    """
    Fetch metadata from the government portal and download PDFs.
    Falls back to copying local files if download fails.
    """
    url = "https://agriwelfare.gov.in/en/getMOMDetail"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "X-Requested-With": "XMLHttpRequest"
    }
    payload = {
        "Category": "Minutes Of Meeting",
        "Status": "Y"
    }

    print("Fetching CWWG reports metadata from portal...")
    try:
        response = requests.post(url, headers=headers, data=payload, timeout=20)
        response.raise_for_status()
        json_data = response.json()
        records = json_data.get("data", [])
    except Exception as e:
        print(f"Error fetching metadata from portal: {e}")
        records = []

    rows = []
    for item in records:
        details = BeautifulSoup(item.get("Details", ""), "html.parser").get_text(strip=True)
        doc_path = item.get("document_path", "")
        pdf_link = "https://agriwelfare.gov.in" + doc_path if doc_path else ""
        rows.append({
            "Title": item.get("Title", "unknown"),
            "Publish Date": item.get("PublishDate", ""),
            "Details": details,
            "PDF Link": pdf_link
        })

    if rows:
        df = pd.DataFrame(rows)
        # Parse dates
        df["Publish Date Parsed"] = pd.to_datetime(df["Publish Date"], dayfirst=True, errors="coerce")
        start_dt = pd.to_datetime(start_date, dayfirst=True)
        end_dt = pd.to_datetime(end_date, dayfirst=True)

        filtered_df = df[
            (df["Publish Date Parsed"] >= start_dt) &
            (df["Publish Date Parsed"] <= end_dt)
        ]
        print(f"Found {len(filtered_df)} reports between {start_date} and {end_date} from portal.")

        # Download PDFs
        download_headers = {
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://agriwelfare.gov.in/en/weather-watch"
        }

        download_count = 0
        for index, row in filtered_df.iterrows():
            pdf_url = row["PDF Link"]
            if not pdf_url:
                continue
            title = row["Title"]
            safe_name = clean_filename(title) + ".pdf"
            dest_path = config.RAW_PDFS_DIR / safe_name

            if dest_path.exists():
                print(f"File already exists: {safe_name}")
                download_count += 1
                continue

            print(f"Downloading: {safe_name} ...")
            try:
                r = requests.get(pdf_url, headers=download_headers, timeout=30)
                if r.status_code == 200:
                    dest_path.write_bytes(r.content)
                    print(f"Saved {safe_name}")
                    download_count += 1
                else:
                    print(f"Failed to download {pdf_url} (Status: {r.status_code})")
            except Exception as e:
                print(f"Error downloading {safe_name}: {e}")

        if download_count > 0:
            print(f"Completed download of {download_count} PDFs.")
            return

    # Fallback to local files if we couldn't download anything
    print("Falling back to local PDFs in Crop_Weather_Watch_RAG...")
    local_source_dir = Path("c:/Web scraping/Crop_Weather_Watch_RAG/PDFs")
    if local_source_dir.is_dir():
        copied_count = 0
        for pdf_file in local_source_dir.glob("*.pdf"):
            dest_path = config.RAW_PDFS_DIR / pdf_file.name
            if not dest_path.exists():
                shutil.copy(pdf_file, dest_path)
                print(f"Copied {pdf_file.name} to raw_pdfs")
                copied_count += 1
            else:
                copied_count += 1
        print(f"Local fallback complete. {copied_count} PDFs are available.")
    else:
        print("No local source directory found. Sowing might fail without PDFs.")

if __name__ == "__main__":
    fetch_and_download()
