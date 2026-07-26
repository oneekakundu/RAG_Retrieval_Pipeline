# 🌱 India Crop Calendar & Master Crop Knowledge Base Project

An end-to-end information extraction pipeline, Master Crop Knowledge Base, and interactive web portal designed to extract, normalize, store, and visualize qualitative agricultural intelligence from Government of India Crop Weather Watch Group (CWWG) meeting minutes.

## 📖 Project Overview

CWWG reports are published weekly by the Ministry of Agriculture & Farmers Welfare, Government of India. These reports contain rich qualitative details on crop growth stages, weather parameters, agricultural operations, and pest or disease warning conditions scattered across meeting minutes.

This project automatically extracts agricultural observations from these reports into a master SQLite database, constructs year-partitioned **Crop Knowledge Views** (`data/crop_knowledge/<CropName>/<Year>.json`), and aggregates them into interactive week-by-week crop calendar dashboards.

---

## 🎯 Primary Goals

- **Master Crop Knowledge Base**: Build a reliable, continuously growing crop-centric knowledge base containing every observation and sentence evidence from CWWG reports.
- **Canonical Schema**: Process every extracted observation through a unified `CropObservation` canonical object capturing rich attributes (`growth_stage`, `crop_operation`, `pest`, `disease`, `severity`, `affected_area`, `recommendation`, `irrigation`, `nutrient_management`, `expected_impact`) and full provenance (`evidence`, `source_pdf`, `page_number`, `section_heading`).
- **Single Source of Truth**: Treat SQLite (`crop_calendar.db`) as the master operational database for indexing, strict 4-tuple deduplication `(report_date, crop, state, evidence_text)`, and query execution.
- **Year-Partitioned Views**: Export structured, year-partitioned JSON views (`data/crop_knowledge/Rice/2026.json`) with pre-computed statistics and event arrays.
- **Incremental Pipeline**: Minimize repeated computation using SHA-256 PDF hashing and multi-stage cache layers.
- **Interactive Portal**: Provide an interactive web dashboard for exploring crop timelines, evidence logs, and agricultural analytics.

---

## 🛠️ System Architecture

Data flows strictly in one direction through the ingestion pipeline:

```
PDF Ingestion
   │
   ▼
Docling Parsing (docling_parser.py)
   │
   ▼
Section Noise Detection (section_detector.py)
   │
   ▼
Crop Micro-Chunking (crop_chunker.py)
   │
   ▼
Context Resolution (context_resolver.py)
   │
   ▼
Information Extraction (Rule-Based -> LLM Fallback)
   │
   ▼
Canonical Object Creation (CropObservation model)
   │
   ▼
Validation & Normalization (validators.py & normalizer.py)
   │
   ▼
SQLite Master Datastore (sqlite_manager.py - Deduplication & Storage)
   │
   ├───► Master Crop Knowledge Views (data/crop_knowledge/<CropName>/<Year>.json)
   │
   └───► Crop Calendar Matrix & Streamlit Portal
```

---

## ⚡ Processing & Deduplication Strategy

The pipeline is fully incremental:

1. **SHA-256 Registry Check**: Before processing a PDF, the pipeline computes its SHA-256 hash. If the report has already been processed with the current pipeline version, re-parsing is skipped automatically.
2. **Strict 4-Tuple Deduplication**: Duplicates are detected in SQLite using `(report_date, crop, state, evidence_text)`. Matching records are rejected before insertion.
3. **One-Way Knowledge View Generation**: After database updates, `CropKnowledgeExporter` updates year-partitioned crop knowledge files (`data/crop_knowledge/<CropName>/<Year>.json`) containing pre-computed statistics and evidence event lists.

---

## 📂 Repository Structure

```
Crop_Calendar/
│
├── downloader/          # CWWG PDF report scraping script
├── extractor/           # Docling parser, section detector, crop chunker, context resolver, rule extractor, LLM fallback, validators, normalizer
├── database/            # SQLite manager, CropObservation canonical model, DataExporter, CropKnowledgeExporter
├── resources/           # Standard dictionary CSV files (crops, states, stages, pests, diseases)
├── prompts/             # System prompt templates for LLM fallback extraction
├── streamlit/           # Multi-page Streamlit portal (Dashboard, Calendar, Evidence, Analytics)
├── data/                # Raw PDFs, Docling JSON models, cache folders, SQLite DB, Crop Knowledge Base, exports
├── run_pipeline.py      # Primary CLI entry point
├── pipeline_manager.py  # Production ETL Orchestrator
├── requirements.txt     # Dependencies
├── README.md            # Quick start and project overview
└── EXPLANATION.txt      # Deep technical architecture and design decisions
```

For deep technical details, algorithms, multi-stage caching, and design decisions, refer to [EXPLANATION.txt](EXPLANATION.txt).

---

## 🚀 Quick Start & Usage

### 1. Installation

Install dependencies from `requirements.txt`:

```bash
pip install -r Crop_Calendar/requirements.txt
```

### 2. Run the Ingestion & Knowledge Base Pipeline

Run the incremental pipeline CLI:

```bash
python Crop_Calendar/run_pipeline.py
```

Optional CLI flags:
- `--force`: Reprocess all raw PDFs regardless of registry status.
- `--from-cache`: Reuse intermediate stage cache outputs whenever available.
- `--from-db`: Rebuild Crop Knowledge Base views and calendar matrix directly from SQLite.
- `--pdf <filename>`: Process a single specific PDF file.
- `--provider <gemini|openai|claude|fallback>`: Specify the LLM provider for fallback extraction.

### 3. Launch the Streamlit Web Portal

Launch the interactive dashboard:

```bash
streamlit run Crop_Calendar/streamlit/app.py
```
