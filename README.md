# Weather Watch RAG Preprocessing Pipeline

This project builds a modular retrieval pipeline for Weather Watch PDF reports from the Ministry of Agriculture portal.

## Features
- Downloads Weather Watch PDFs from the existing portal scraper logic
- Extracts text, tables, images, and layout metadata separately
- Links extracted elements into page-level structures
- Merges the outputs into a unified document representation
- Builds semantic chunks and embeddings
- Stores embeddings in a FAISS index for retrieval

## Run

```bash
python Crop_Weather_Watch/run_rag_pipeline.py --start-date 01-06-2026 --end-date 30-06-2026 --limit 10
```

The pipeline now asks for the start and end dates, downloads only the reports in that range, stores one full text file per PDF, marks embedded images with explicit tags such as [IMAGE page_05_img_1], and then lets you ask retrieval questions. The retrieved chunks are printed as output.

## Setup

Creation of venv: python -m venv venv
Activation: .\venv\Scripts\Activate.ps1
Install requirements: pip install -r requirements.txt

python Crop_Weather_Watch/run_rag_pipeline.py --start-date 01-06-2026 --end-date 08-06-2026 --limit 10