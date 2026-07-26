from enum import Enum
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, field_validator

class ObservationType(str, Enum):
    GROWTH_STAGE = "Growth Stage"
    HARVEST_PROGRESS = "Harvest Progress"
    SOWING_PROGRESS = "Sowing Progress"
    PEST_INCIDENCE = "Pest Incidence"
    DISEASE_INCIDENCE = "Disease Incidence"
    IRRIGATION = "Irrigation"
    NUTRIENT_DEFICIENCY = "Nutrient Deficiency"
    CROP_CONDITION = "Crop Condition"
    AREA_COVERAGE = "Area Coverage"
    YIELD = "Yield"
    MARKET_INFORMATION = "Market Information"
    OTHER = "Other"

class FieldEvidence(BaseModel):
    value: str = Field(..., description="Extracted value")
    evidence: str = Field(..., description="Supporting exact sentence from text")

class SemanticExtractionSchema(BaseModel):
    crop: str = Field(..., description="Standardized crop name")
    state: str = Field(default="All India", description="State or Union Territory name")
    week: str = Field(..., description="Report date in YYYY-MM-DD or week format")
    observation_type: str = Field(default="Other", description="Primary observation type category")
    growth_stage: Optional[FieldEvidence] = Field(default=None, description="Growth stage with evidence")
    sowing_status: Optional[FieldEvidence] = Field(default=None, description="Sowing progress or area sown with evidence")
    harvest_status: Optional[FieldEvidence] = Field(default=None, description="Harvest progress or percentage with evidence")
    pests: List[FieldEvidence] = Field(default_factory=list, description="Verified pest occurrences with evidence")
    diseases: List[FieldEvidence] = Field(default_factory=list, description="Verified disease occurrences with evidence")
    nutrient_deficiencies: List[FieldEvidence] = Field(default_factory=list, description="Nutrient deficiencies with evidence")
    statistics: List[FieldEvidence] = Field(default_factory=list, description="Area coverage or statistical figures with evidence")
    evidence: List[str] = Field(default_factory=list, description="Supporting exact text sentences")
    confidence: float = Field(default=0.95, description="Confidence score between 0.0 and 1.0")

class VerificationStatus(str, Enum):
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    MODIFIED = "MODIFIED"

class VerifiedObservationRecord(BaseModel):
    id: Optional[int] = None
    chunk_id: str = Field(default="", description="Unique chunk identifier")
    crop: str
    state: str
    week: str
    source_pdf: str
    page_number: int = 1
    observation_type: str = "Other"
    growth_stage: Optional[str] = None
    sowing_status: Optional[str] = None
    harvest_status: Optional[str] = None
    pests: Optional[str] = None
    diseases: Optional[str] = None
    statistics: Optional[str] = None
    evidence_sentence: str = ""
    confidence: float = 0.95
    verification_status: str = "VERIFIED"
    verification_notes: Optional[str] = None
    timestamp: str = ""
