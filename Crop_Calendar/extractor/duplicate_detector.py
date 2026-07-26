from typing import List, Dict, Any, Set, Tuple

class DuplicateDetector:
    """Detects and filters out duplicate observation records within a report or batch."""

    def __init__(self):
        self.seen_signatures: Set[Tuple[str, str, str, str, str]] = set()

    def make_signature(self, record: Dict[str, Any]) -> Tuple[str, str, str, str, str]:
        crop = str(record.get("crop") or "").lower().strip()
        state = str(record.get("state") or "").lower().strip()
        stage = str(record.get("growth_stage") or "").lower().strip()
        pest = str(record.get("pest_or_disease") or "").lower().strip()
        week = str(record.get("report_week") or "").lower().strip()
        return (crop, state, stage, pest, week)

    def is_duplicate(self, record: Dict[str, Any]) -> bool:
        sig = self.make_signature(record)
        if sig in self.seen_signatures:
            return True
        self.seen_signatures.add(sig)
        return False

    def filter_duplicates(self, records: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], int]:
        """
        Filter out duplicate records.
        Returns (unique_records, duplicate_count).
        """
        unique = []
        dupes = 0
        for rec in records:
            if self.is_duplicate(rec):
                dupes += 1
            else:
                unique.append(rec)
        return unique, dupes

    def clear(self):
        self.seen_signatures.clear()
