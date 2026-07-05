from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer


class SemanticSearchEngine:
    """Perform semantic retrieval from FAISS using the same embedding model."""

    def __init__(self, index_path: Optional[os.PathLike | str] = None, metadata_path: Optional[os.PathLike | str] = None, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.index_path = Path(index_path or Path(__file__).resolve().parents[1] / "data" / "faiss" / "chunks.index")
        self.metadata_path = Path(metadata_path or Path(__file__).resolve().parents[1] / "data" / "faiss" / "chunks_metadata.json")
        self.model = SentenceTransformer(model_name)
        self.index = faiss.read_index(str(self.index_path)) if self.index_path.exists() else None
        self.metadata = json.loads(self.metadata_path.read_text(encoding="utf-8")) if self.metadata_path.exists() else []

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        if self.index is None:
            raise FileNotFoundError("FAISS index not found")
        query_embedding = self.model.encode([query], convert_to_numpy=True, normalize_embeddings=True).astype("float32")
        scores, indices = self.index.search(query_embedding, min(top_k, len(self.metadata)))
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(self.metadata):
                continue
            chunk = self.metadata[idx]
            results.append({"score": float(score), "chunk_id": chunk.get("chunk_id"), "page_number": chunk.get("metadata", {}).get("page_numbers", [None])[0], "text": chunk.get("text", "")})
        return results
