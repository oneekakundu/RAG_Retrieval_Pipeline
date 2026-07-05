from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import faiss
import numpy as np

from .utils import ensure_directory, setup_logger


class FaissIndexer:
    """Store chunk embeddings in a FAISS index."""

    def __init__(self, output_dir: Optional[os.PathLike | str] = None, logger=None):
        self.output_dir = Path(output_dir or Path(__file__).resolve().parents[1] / "data" / "faiss")
        self.logger = logger or setup_logger("faiss")
        ensure_directory(self.output_dir)

    def build_index(self, chunks: List[Dict[str, Any]]) -> Any:
        """Build a FlatL2 FAISS index from chunk embeddings."""
        embeddings = np.array([chunk.get("embedding", []) for chunk in chunks], dtype="float32")
        if embeddings.ndim != 2 or embeddings.shape[0] == 0:
            raise ValueError("No embeddings available to index")
        index = faiss.IndexFlatL2(embeddings.shape[1])
        index.add(embeddings)
        faiss.write_index(index, str(self.output_dir / "chunks.index"))
        return index

    def save_metadata(self, chunks: List[Dict[str, Any]]) -> None:
        metadata_path = self.output_dir / "chunks_metadata.json"
        metadata_path.write_text(__import__("json").dumps(chunks, indent=2), encoding="utf-8")
