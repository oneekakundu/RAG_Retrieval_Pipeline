# Weather Watch RAG Preprocessing Pipeline

This project builds a modular retrieval pipeline for Weather Watch PDF reports from the Ministry of Agriculture portal.This pipeline ingests weekly "Weather Watch" crop advisory PDFs published by the Government of India (agriwelfare.gov.in), extracts all content from them (text, tables, images), links every element spatially according to its position in the PDF, builds a two-level hierarchical chunk structure, encodes every chunk as a dense vector embedding, stores it in a FAISS index, and finally enables semantic retrieval from that index at query time.

## Features
- Downloads Weather Watch PDFs from the existing portal scraper logic
- Extracts text, tables, images, and layout metadata separately
- Links extracted elements into page-level structures
- Merges the outputs into a unified document representation
- Builds semantic chunks and embeddings
- Stores embeddings in a FAISS index for retrieval

## RAG Pipeline Modules

The pipeline is implemented across the following Python modules inside:
  Crop_Weather_Watch/rag_pipeline/
    downloader.py            — Phase 1: PDF Download
    extractors.py            — Phase 2: Multi-modal Extraction
    linking.py               — Phase 3: Spatial Linking & Merging
    chunking.py              — Phase 4a: Page-wise (Parent) Chunking
    hierarchical_chunker.py  — Phase 4b: Semantic (Child) Chunking
    embeddings.py            — Phase 5: Embedding Generation
    faiss_index.py           — Phase 6: FAISS Index Storage
    search.py                — Phase 7: Semantic Retrieval
    pipeline.py              — Orchestrator (calls all phases in order)

## Run

```bash
python Crop_Weather_Watch/run_rag_pipeline.py --start-date 01-06-2026 --end-date 30-06-2026 --limit 10
```

The pipeline now asks for the start and end dates, downloads only the reports in that range, stores one full text file per PDF, marks embedded images with explicit tags such as [IMAGE page_05_img_1], and then lets you ask retrieval questions. The retrieved chunks are printed as output.

## Setup

Creation of venv: python -m venv venv
Activation: .\venv\Scripts\Activate.ps1
Install requirements: pip install -r requirements.txt

## The run command along with sample questions to try !

python Crop_Weather_Watch/run_rag_pipeline.py --start-date 01-06-2026 --end-date 08-06-2026 --limit 10

1)what is Kharif Season Sowing Status?
2)table on kharif crop
3)MME forecast Tmax anomaly image