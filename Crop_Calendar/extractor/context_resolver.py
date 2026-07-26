from typing import List, Dict, Any, Optional
from extractor.normalizer import Normalizer

class ContextResolver:
    """Resolves missing crop, state, or date context across document sentences or adjacent chunks."""

    def resolve_context(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Propagates crop and state context across adjacent chunks if missing.
        """
        last_crop = None
        last_state = None

        resolved_chunks = []
        for chunk in chunks:
            text = chunk.get("chunk_text", "")
            detected_crop = chunk.get("detected_crop") or Normalizer.normalize_crop(text)

            if detected_crop and detected_crop != "Unknown":
                last_crop = detected_crop

            detected_state = Normalizer.normalize_state(text)
            if detected_state and detected_state != "All India":
                last_state = detected_state

            c_copy = chunk.copy()
            if not c_copy.get("detected_crop") and last_crop:
                c_copy["detected_crop"] = last_crop

            c_copy["state_context"] = last_state or "All India"
            resolved_chunks.append(c_copy)

        return resolved_chunks
