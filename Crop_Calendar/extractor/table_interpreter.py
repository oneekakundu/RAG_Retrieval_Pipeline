import re
from typing import List, Dict, Any, Optional
from extractor.normalizer import Normalizer, STATE_MAPPING
from extractor.validators import APPROVED_STATES, APPROVED_CROPS

class TableInterpreter:
    """
    Parses structured table rows into individual Atomic Observation Units 
    (one per State/Crop event) before passing to the Extractor.
    """

    @staticmethod
    def is_multi_state_row(text: str) -> bool:
        """Check if row text contains multiple state names or state percentage patterns."""
        # Find all state occurrences
        states_found = set()
        for st_syn, st_norm in STATE_MAPPING.items():
            if re.search(rf"\b{re.escape(st_syn)}\b", text, re.IGNORECASE):
                if st_norm != "All India":
                    states_found.add(st_norm)
        return len(states_found) >= 2 or bool(re.search(r"[A-Za-z\s]+\s*\(\d+%\)", text))

    @staticmethod
    def expand_table_row(crop: str, text: str, heading: str, page_number: int, source_pdf: str) -> List[Dict[str, Any]]:
        """
        Expands a multi-state table row into atomic, single-state observation units.
        Example Input: 
          'Tamil Nadu (90%), Kerala (98%), Andhra Pradesh (75%), Telangana (52%) etc has already been harvested.'
        Output:
          List of atomic units for Tamil Nadu, Kerala, Andhra Pradesh, and Telangana.
        """
        atomic_units = []

        # Extract 100% harvested states group if present: e.g., "100% Harvested in Gujarat, Maharashtra, Tamil Nadu..."
        hundred_match = re.search(r"100%\s*harvested\s+in\s+([^\.\n;]+)", text, re.IGNORECASE)
        if hundred_match:
            hundred_states_str = hundred_match.group(1)
            for st_syn, st_norm in STATE_MAPPING.items():
                if st_norm != "All India" and re.search(rf"\b{re.escape(st_syn)}\b", hundred_states_str, re.IGNORECASE):
                    atomic_units.append({
                        "detected_crop": crop,
                        "state_context": st_norm,
                        "harvest_progress": "100%",
                        "chunk_text": f"{crop} is 100% harvested in {st_norm}.",
                        "heading": heading,
                        "page_number": page_number,
                        "source_pdf": source_pdf,
                        "is_atomic_event": True
                    })

        # Extract percentage state matches: e.g. "Tamil Nadu (90%)", "AP (85%)"
        pct_matches = re.findall(r"([A-Za-z\s&]+)\s*\(\s*(\d+%?)\s*\)", text)
        for state_str, pct in pct_matches:
            st_norm = Normalizer.normalize_state(state_str.strip())
            if st_norm != "All India" and st_norm in APPROVED_STATES:
                # Check duplicate state
                if not any(u["state_context"] == st_norm for u in atomic_units):
                    pct_val = pct if "%" in pct else f"{pct}%"
                    atomic_units.append({
                        "detected_crop": crop,
                        "state_context": st_norm,
                        "harvest_progress": f"{pct_val} Harvested",
                        "chunk_text": f"{crop} in {st_norm} has {pct_val} harvested.",
                        "heading": heading,
                        "page_number": page_number,
                        "source_pdf": source_pdf,
                        "is_atomic_event": True
                    })

        # Fallback if no specific state pattern was split
        if not atomic_units:
            # Fallback to single chunk
            atomic_units.append({
                "detected_crop": crop,
                "state_context": Normalizer.normalize_state(text),
                "chunk_text": text,
                "heading": heading,
                "page_number": page_number,
                "source_pdf": source_pdf,
                "is_atomic_event": False
            })

        return atomic_units
