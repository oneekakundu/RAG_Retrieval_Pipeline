from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from .chunking import chunk_document
from .downloader import WeatherWatchDownloader
from .embeddings import EmbeddingIndexer
from .extractors import ImageExtractor, MetadataExtractor, TableExtractor, TextExtractor
from .faiss_index import FaissIndexer
from .linking import build_document_representation, build_page_structure
from .search import SemanticSearchEngine
from .utils import ensure_directory, safe_json_dump, setup_logger


class WeatherWatchRAGPipeline:
    """Coordinate the full Weather Watch preprocessing workflow."""

    def __init__(self, base_dir: Optional[os.PathLike | str] = None, logger=None):
        self.base_dir = Path(base_dir or Path(__file__).resolve().parents[1] / "data")
        self.logs_dir = ensure_directory(self.base_dir / "logs")
        self.logger = logger or setup_logger("pipeline", log_file=self.logs_dir / "pipeline.log")
        self.output_dir = ensure_directory(self.base_dir)
        self.downloader = WeatherWatchDownloader(output_dir=self.output_dir / "pdfs", logger=self.logger)
        self.text_extractor = TextExtractor(output_dir=self.output_dir, logger=self.logger)
        self.table_extractor = TableExtractor(output_dir=self.output_dir, logger=self.logger)
        self.image_extractor = ImageExtractor(output_dir=self.output_dir, logger=self.logger)
        self.metadata_extractor = MetadataExtractor(output_dir=self.output_dir, logger=self.logger)
        self.embedding_indexer = EmbeddingIndexer(output_dir=self.output_dir / "embeddings", logger=self.logger)
        self.faiss_indexer = FaissIndexer(output_dir=self.output_dir / "faiss", logger=self.logger)

    def process_reports(self, records: List[Dict[str, Any]], week_name: str, limit: Optional[int] = None) -> Dict[str, Any]:
        """Process one week of reports and save all intermediate artifacts."""
        downloaded = self.downloader.download_reports(records, week_name=week_name, limit=limit)
        results = []
        for report in downloaded:
            try:
                pdf_path = Path(report["pdf_path"])
                week_dir = self.output_dir / week_name
                ensure_directory(week_dir)
                text_doc = self.text_extractor.extract(pdf_path, week_name)
                table_pages = self.table_extractor.extract(pdf_path, week_name)
                image_pages = self.image_extractor.extract(pdf_path, week_name)
                metadata = self.metadata_extractor.extract(pdf_path, week_name)

                page_structures = []
                page_tables = {}
                for item in table_pages:
                    page_tables.setdefault(item["page"], []).append(item)
                page_images = {}
                for item in image_pages:
                    page_images.setdefault(item["page"], []).append(item)

                page_texts = {item["page"]: [{"content": item.get("content", ""), "page": item["page"], "bbox": None, "section_heading": None}] for item in text_doc.get("page_texts", [])}

                for page_number in range(1, len(metadata.get("pages", [])) + 1):
                    page_meta = metadata["pages"][page_number - 1]
                    blocks = page_meta.get("blocks", [])
                    if blocks:
                        text_blocks = []
                        for b in blocks:
                            if b.get("type") == "text" and b.get("text", "").strip():
                                text_blocks.append({
                                    "content": b.get("text", "").strip(),
                                    "page": page_number,
                                    "bbox": b.get("bbox"),
                                    "section_heading": None,
                                })
                    else:
                        text_blocks = page_texts.get(page_number, [{"content": "", "page": page_number, "bbox": None, "section_heading": None}])

                    page_structures.append(build_page_structure(page_number, text_blocks, page_tables.get(page_number, []), page_images.get(page_number, []), page_meta))

                document = build_document_representation(pdf_path.name, page_structures)
                merged_path = self.output_dir / "merged" / f"{week_name}.json"
                safe_json_dump(document, merged_path)

                from .hierarchical_chunker import build_parent_chunks, build_child_chunks, link_parent_child, prepare_chunks_for_embedding

                parent_chunks = build_parent_chunks(document, week_name)
                child_chunks = build_child_chunks(parent_chunks, document)
                link_parent_child(parent_chunks, child_chunks)

                # Save parent chunks to their own file
                parent_chunks_path = self.output_dir / "chunks" / f"{week_name}_parent.json"
                ensure_directory(parent_chunks_path.parent)
                parent_chunks_path.write_text(json.dumps(parent_chunks, indent=2), encoding="utf-8")

                # Save child chunks as the main chunks file for downstream tasks/indexers
                chunks_path = self.output_dir / "chunks" / f"{week_name}.json"
                ensure_directory(chunks_path.parent)
                chunks_path.write_text(json.dumps(child_chunks, indent=2), encoding="utf-8")

                # Prepare child chunks for embedding (adds chunk_id key matching child_chunk_id)
                prepared_chunks = prepare_chunks_for_embedding(child_chunks)
                embedded_chunks = self.embedding_indexer.embed_chunks(prepared_chunks)
                results.append({"pdf_path": str(pdf_path), "chunks": embedded_chunks})
            except Exception as exc:
                self.logger.exception("Failed to process report %s: %s", report.get("pdf_path"), exc)

        all_embedded_chunks = []
        for result in results:
            all_embedded_chunks.extend(result.get("chunks", []))

        if all_embedded_chunks:
            self.faiss_indexer.build_index(all_embedded_chunks)
            self.faiss_indexer.save_metadata(all_embedded_chunks)

        return {"week": week_name, "reports": results}

    def search(self, query: str, top_k: int = 5, expand_to_parent: bool = False) -> List[Dict[str, Any]]:
        engine = SemanticSearchEngine(index_path=self.output_dir / "faiss" / "chunks.index", metadata_path=self.output_dir / "faiss" / "chunks_metadata.json")
        return engine.search_hierarchical(query, top_k=top_k, expand_to_parent=expand_to_parent)
