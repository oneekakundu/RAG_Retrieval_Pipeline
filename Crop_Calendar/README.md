# 🌱 India Crop Calendar AI Extraction Project

An end-to-end information extraction pipeline and dashboard designed to build a standardized, up-to-date weekly crop calendar for India using Crop Weather Watch Group (CWWG) meeting minutes.

## 📖 Project Overview

CWWG reports are published weekly by the Ministry of Agriculture & Farmers Welfare, Government of India. These reports contain rich qualitative details on crop growth stages, weather parameters, and pest or disease warning conditions. However, this intelligence is scattered across hundreds of pages of meeting minutes.

This project implements a custom pipeline to extract agricultural facts and compile them into a unified week-by-week crop calendar database.

---

## 🛠️ Technology & Architecture

The pipeline processes documents in a self-contained sequential flow:

1.  **Downloader (`downloader/download_reports.py`)**: Fetches weekly meeting minutes PDFs from the national agriwelfare portal.
2.  **Parser (`extraction/docling_parser.py`)**: Employs **Docling** to accurately parse PDFs and structure tables, headers, and layouts.
3.  **Semantic Chunker (`extraction/semantic_chunker.py`)**: Splits the parsed document content into micro-observation units at boundary points (e.g., when Crop, State, or District context changes).
4.  **Entity Extractor (`extraction/entity_extractor.py`)**: Leverages a zero-shot **GLiNER NER model** (`urchade/gliner_medium-v2.1`) to locate targets like Crops, States, Growth Stages, Pests, Diseases, and Advisories.
5.  **Evidence Builder (`extraction/evidence_builder.py`)**: Normalizes values and structures observations into database-friendly schema records.
6.  **Calendar Generator (`extraction/calendar_builder.py`)**: Groups observations chronologically to compile the consolidated calendar matrix.
7.  **Database Layer (`database/sqlite.py` & `export.py`)**: Stores everything in a local SQLite file (`crop_calendar.db`) and exports reports to CSV and JSON formats.
8.  **Visual Interface (`streamlit/app.py`)**: Interactive multi-page Streamlit portal to explore the data and charts.

---

## 🚀 Running the Project

### 1. Initialize Database & Run Pipeline

Run the pipeline from the workspace root to download sample reports, extract entities, build the calendar, and generate exports:

```bash
.\venv\Scripts\python.exe Crop_Calendar\run_pipeline.py
```

### 2. Launch the Streamlit Portal

Launch the visual dashboard:

```bash
.\venv\Scripts\streamlit.exe run Crop_Calendar\streamlit\app.py
```

---

## 📂 Project Structure

*   `data/`: Raw report PDFs, Docling JSON models, structured evidence files, and the output SQLite DB.
*   `downloader/`: Script to fetch weekly PDF reports.
*   `extraction/`: Core extraction logic (parsing, chunking, GLiNER extraction, normalizer, and calendar builder).
*   `database/`: SQLite table schemas and export functions.
*   `streamlit/`: Code for the multi-page portal.
