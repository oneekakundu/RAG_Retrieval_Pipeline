from dataclasses import dataclass, field
from typing import Optional, Dict, Any

@dataclass
class CropObservation:
    """Canonical Crop Observation model representing an extracted agricultural event."""
    crop: str
    state: str
    report_date: str
    district: str = "State-wide"
    report_week: Optional[str] = None
    growth_stage: Optional[str] = None
    crop_operation: Optional[str] = None
    pest: Optional[str] = None
    disease: Optional[str] = None
    pest_or_disease: Optional[str] = None
    severity: Optional[str] = None
    affected_area: Optional[str] = None
    irrigation: Optional[str] = None
    nutrient_management: Optional[str] = None
    evidence: str = ""
    raw_text: str = ""
    source_pdf: str = "unknown.pdf"
    page_number: int = 1
    section_heading: str = "General Observation"
    confidence: float = 0.95
    source_method: str = "rule_based"
    pipeline_version: str = "2.1"
    dictionary_version: str = "1.0"
    is_ambiguous: bool = False
    id: Optional[int] = None
    created_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert canonical observation object to dictionary."""
        return {
            "crop": self.crop,
            "state": self.state,
            "district": self.district,
            "report_date": self.report_date,
            "report_week": self.report_week or self.report_date,
            "growth_stage": self.growth_stage,
            "crop_operation": self.crop_operation,
            "pest_or_disease": self.pest_or_disease or self.pest or self.disease,
            "severity": self.severity,
            "affected_area": self.affected_area,
            "irrigation": self.irrigation,
            "nutrient_management": self.nutrient_management,
            "evidence": self.evidence or self.raw_text,
            "raw_text": self.raw_text or self.evidence,
            "source_pdf": self.source_pdf,
            "page_number": self.page_number,
            "section_heading": self.section_heading,
            "confidence": self.confidence,
            "source_method": self.source_method,
            "pipeline_version": self.pipeline_version,
            "dictionary_version": self.dictionary_version,
            "id": self.id,
            "created_at": self.created_at
        }

# Alias for backward compatibility
CropRecord = CropObservation
