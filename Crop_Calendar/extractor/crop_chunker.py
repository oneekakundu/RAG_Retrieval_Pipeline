import re
from typing import List, Dict, Any, Optional
from extractor.normalizer import CROP_MAPPING, STATE_MAPPING, Normalizer
from extractor.validators import APPROVED_CROPS
from extractor.table_interpreter import TableInterpreter

# Known crop keywords for fast detection
CROP_KEYWORDS = sorted(list(set(CROP_MAPPING.keys())), key=len, reverse=True)
STATE_KEYWORDS = list(set(STATE_MAPPING.keys()))

# Keywords identifying statistical area/price/financial tables
PURE_STATISTICAL_KEYWORDS = [
    "retail prices", "% variation over", "1 month ago", "1 year ago",
    "advance estimates", "normal area (des)", "progressive area sown",
    "increase (+) / decrease (-)", "buffer norm", "lmt"
]

class CropChunker:
    """
    Classifies document blocks into STATISTICAL vs QUALITATIVE_OBSERVATION,
    and extracts crop-centric observation units / atomic events.
    """

    def __init__(self):
        self.crop_regexes = {
            crop: re.compile(rf"\b{re.escape(crop)}\b", re.IGNORECASE)
            for crop in CROP_KEYWORDS
        }

    def _detect_crop_in_text(self, text: str) -> Optional[str]:
        """Detect if text contains a valid crop keyword from controlled dictionary."""
        if not text or len(text.strip()) < 2:
            return None
        norm = Normalizer.normalize_crop(text)
        if norm != "Unknown" and (norm in APPROVED_CROPS or norm.title() in APPROVED_CROPS):
            return norm
        return None

    def _is_pure_statistical_table(self, text: str) -> bool:
        """
        Check if a table block is strictly statistical (area/price/stock) 
        without qualitative crop health, stage, or advisory details.
        """
        t_lower = text.lower()
        has_stat_kw = any(kw in t_lower for kw in PURE_STATISTICAL_KEYWORDS)
        
        has_qualitative = any(kw in t_lower for kw in [
            "harvested", "harvesting", "sown", "sowing", "transplanting", 
            "vegetative", "flowering", "pest", "disease", "etl", "advisory", 
            "advised", "infestation", "mildew", "blight", "borer", "rust", "weeding"
        ])

        if has_stat_kw and not has_qualitative:
            return True
        return False

    def create_crop_chunks(self, filtered_blocks: List[Dict[str, Any]], source_pdf: str) -> List[Dict[str, Any]]:
        """
        Classifies blocks and extracts qualitative crop observation units and atomic table events.
        """
        chunks = []
        chunk_idx = 0

        for block in filtered_blocks:
            heading = block.get("heading", "")
            text = block.get("text", "")
            page_no = block.get("page_number", 1)

            if not text.strip():
                continue

            # Classify Block: Skip pure statistical tables
            if self._is_pure_statistical_table(text):
                continue

            # Split text into bullet items or markdown table rows or lines
            lines = [l.strip() for l in re.split(r"\n+|(?:^|\s)[•\-]\s*", text) if l.strip()]

            current_crop = None
            current_lines = []

            for line in lines:
                # Skip statistical header rows
                if any(sk in line.lower() for sk in PURE_STATISTICAL_KEYWORDS):
                    continue

                detected = self._detect_crop_in_text(line)
                if detected:
                    current_crop = detected

                # Branching Strategy: Structured Table Multi-State Row -> TableInterpreter Atomic Events
                if TableInterpreter.is_multi_state_row(line):
                    # Flush prior narrative lines if any
                    if current_lines:
                        c_text = "\n".join(current_lines).strip()
                        if c_text and current_crop:
                            chunks.append({
                                "chunk_id": f"{source_pdf}_{chunk_idx}",
                                "chunk_text": c_text,
                                "detected_crop": current_crop,
                                "heading": heading,
                                "page_number": page_no,
                                "source_pdf": source_pdf
                            })
                            chunk_idx += 1
                        current_lines = []

                    # Expand table row into atomic single-state events
                    expanded_events = TableInterpreter.expand_table_row(
                        current_crop or "Crop", line, heading, page_no, source_pdf
                    )
                    for ev in expanded_events:
                        ev["chunk_id"] = f"{source_pdf}_{chunk_idx}"
                        chunks.append(ev)
                        chunk_idx += 1
                    continue

                # Narrative Pipeline: Flush chunk if new valid crop detected and lines accumulated
                if detected and current_crop and detected != current_crop and current_lines:
                    chunk_text = "\n".join(current_lines).strip()
                    if chunk_text:
                        chunks.append({
                            "chunk_id": f"{source_pdf}_{chunk_idx}",
                            "chunk_text": chunk_text,
                            "detected_crop": current_crop,
                            "heading": heading,
                            "page_number": page_no,
                            "source_pdf": source_pdf
                        })
                        chunk_idx += 1
                    current_lines = []

                current_lines.append(line)

            # Flush remaining lines for the block
            if current_lines:
                chunk_text = "\n".join(current_lines).strip()
                if chunk_text:
                    has_agri = current_crop or any(kw in chunk_text.lower() for kw in [
                        "stage", "pest", "disease", "sowing", "threshold", "advisory", "advised", 
                        "incidence", "harvested", "harvesting", "mildew", "blight", "borer", "rust", "farmer"
                    ])
                    
                    if has_agri:
                        chunks.append({
                            "chunk_id": f"{source_pdf}_{chunk_idx}",
                            "chunk_text": chunk_text,
                            "detected_crop": current_crop,
                            "heading": heading,
                            "page_number": page_no,
                            "source_pdf": source_pdf
                        })
                        chunk_idx += 1

        return chunks
