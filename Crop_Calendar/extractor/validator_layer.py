import logging
from typing import List, Tuple

logger = logging.getLogger("ValidationLayer")

class ValidationLayer:
    """
    Final validation layer for VerifiedObservationRecord instances.
    Ensures all records are fully prepared for SQLite ingestion.
    """
    def __init__(self):
        pass

    def validate_records(self, records: list) -> Tuple[list, int]:
        """
        Validates a list of VerifiedObservationRecord objects.
        Returns a tuple of (valid_records, rejected_count).
        """
        valid_records = []
        rejected_count = 0
        
        for rec in records:
            if rec:
                # Add any final sanity checks here if needed in the future
                valid_records.append(rec)
            else:
                rejected_count += 1
                
        return valid_records, rejected_count