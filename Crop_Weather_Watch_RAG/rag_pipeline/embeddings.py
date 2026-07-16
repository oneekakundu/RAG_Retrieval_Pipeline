from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from sentence_transformers import SentenceTransformer

from .utils import ensure_directory, setup_logger


class EmbeddingIndexer:
    """Generate embeddings with a free sentence-transformer model."""

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2", output_dir: Optional[os.PathLike | str] = None, logger=None):
        self.model_name = model_name
        self.output_dir = Path(output_dir or Path(__file__).resolve().parents[1] / "data" / "embeddings")
        self.logger = logger or setup_logger("embeddings")
        ensure_directory(self.output_dir)
        self.model = SentenceTransformer(self.model_name)

    def embed_chunks(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create embeddings for each chunk and save them to disk."""
        texts = [chunk.get("text", "") for chunk in chunks]
        embeddings = self.model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
        for chunk, embedding in zip(chunks, embeddings):
            chunk["embedding"] = embedding.tolist()
            embedding_path = self.output_dir / f"{chunk['chunk_id']}.json"
            embedding_path.write_text(__import__("json").dumps({"chunk_id": chunk["chunk_id"], "embedding": chunk["embedding"]}, indent=2), encoding="utf-8")
        return chunks
