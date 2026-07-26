import re
from typing import Optional
from pydantic import BaseModel, Field, field_validator
from extractor.normalizer import Normalizer, STATE_MAPPING

# Approved dictionary sets
APPROVED_CROPS = {
    "Rice", "Wheat", "Maize", "Sugarcane", "Cotton", "Jute", "Soybean", 
    "Groundnut", "Mustard", "Pigeonpea (Arhar)", "Black Gram (Urad)", 
    "Green Gram (Moong)", "Bengal Gram (Gram/Chickpea)", "Lentil (Masur)", 
    "Pearl Millet (Bajra)", "Sorghum (Jowar)", "Finger Millet (Ragi)", 
    "Sesame (Sesamum)", "Sunflower", "Castor", "Coarse Cereals", "Pulses", "Oilseeds"
}

APPROVED_STATES = set(STATE_MAPPING.values()) | {"All India"}

INVALID_CROPS = {
    "GENERAL", "GENERAL SUMMARY", "WEATHER SUMMARY", "RAINFALL SUMMARY", 
    "INPUTS SITUATION", "FERTILIZER POSITION", "RESERVOIR STORAGE", 
    "MANDI WHOLESALE PRICES", "SALIENT FEATURES", "ADMINISTRATIVE NOTES", 
    "ATTENDANCE", "SUMMARY", "OVERVIEW", "KEY INSIGHTS", "COMMODITIES", 
    "PROGRESS OF AREA", "CROPS", "KHARIF CROPS", "RABI CROPS", "UNKNOWN"
}

class CropExtractionRecord(BaseModel):
    crop: str = Field(..., description="Crop name")
    state: str = Field(default="All India", description="Indian State or UT")
    report_week: str = Field(..., description="Report date in YYYY-MM-DD format")
    district: Optional[str] = Field(default="State-wide", description="District name")
    growth_stage: Optional[str] = Field(default=None, description="Growth stage")
    crop_operation: Optional[str] = Field(default=None, description="Agricultural operation (Sowing, Transplanting, Weeding, Harvesting)")
    pest_or_disease: Optional[str] = Field(default=None, description="Pest or disease details")
    pest: Optional[str] = Field(default=None, description="Specific pest name")
    disease: Optional[str] = Field(default=None, description="Specific disease name")
    severity: Optional[str] = Field(default=None, description="Severity rating (Low, Moderate, Severe, Above ETL)")
    affected_area: Optional[str] = Field(default=None, description="Geographic area or region affected")
    irrigation: Optional[str] = Field(default=None, description="Irrigation or water management status")
    nutrient_management: Optional[str] = Field(default=None, description="Fertilizer / nutrient application details")
    evidence: Optional[str] = Field(default=None, description="Original source sentence evidence text")
    raw_text: Optional[str] = Field(default=None, description="Raw sentence text")
    source_pdf: Optional[str] = Field(default="unknown.pdf", description="Source PDF filename")
    page_number: Optional[int] = Field(default=1, description="Source page number")
    section_heading: Optional[str] = Field(default="General Observation", description="Section heading")
    confidence: Optional[float] = Field(default=0.95, description="Confidence score")
    source_method: Optional[str] = Field(default="rule_based", description="Extraction method (rule_based or llm)")

    @field_validator("crop")
    @classmethod
    def validate_and_normalize_crop(cls, v: str) -> str:
        if not v or not isinstance(v, str):
            raise ValueError("Crop name cannot be empty")
        
        c_clean = v.strip()
        if c_clean.upper() in INVALID_CROPS:
            raise ValueError(f"'{v}' is a header/category title, not a valid crop")
        
        norm_crop = Normalizer.normalize_crop(c_clean)
        
        if norm_crop not in APPROVED_CROPS and norm_crop.title() not in APPROVED_CROPS:
            matched = False
            for app_crop in APPROVED_CROPS:
                if app_crop.lower() in norm_crop.lower() or norm_crop.lower() in app_crop.lower():
                    norm_crop = app_crop
                    matched = True
                    break
            if not matched:
                raise ValueError(f"Crop '{v}' (normalized: '{norm_crop}') is not in the approved crop list")
                
        return norm_crop

    @field_validator("state")
    @classmethod
    def validate_and_normalize_state(cls, v: Optional[str]) -> str:
        if not v or not isinstance(v, str) or v.strip().lower() in ["null", "none", ""]:
            return "All India"
        
        norm_state = Normalizer.normalize_state(v.strip())
        if norm_state not in APPROVED_STATES:
            matched = False
            for state in APPROVED_STATES:
                if state.lower() in norm_state.lower() or norm_state.lower() in state.lower():
                    norm_state = state
                    matched = True
                    break
            if not matched:
                raise ValueError(f"State '{v}' is not a recognized Indian State or UT")
                
        return norm_state

    @field_validator("growth_stage")
    @classmethod
    def validate_growth_stage(cls, v: Optional[str]) -> Optional[str]:
        return Normalizer.normalize_stage(v)

    @field_validator("pest_or_disease", "pest", "disease")
    @classmethod
    def validate_pest_disease(cls, v: Optional[str]) -> Optional[str]:
        return Normalizer.normalize_pest_disease(v)

    @field_validator("report_week")
    @classmethod
    def validate_report_week(cls, v: str) -> str:
        if not v or not re.match(r"^\d{4}-\d{2}-\d{2}$", v.strip()):
            raise ValueError(f"report_week '{v}' must be in YYYY-MM-DD format")
        return v.strip()

def validate_and_clean_record(data: dict, report_week: str) -> Optional[CropExtractionRecord]:
    """
    Validates a dict using CropExtractionRecord.
    Returns Pydantic model instance if valid, or None if invalid.
    """
    if not isinstance(data, dict):
        return None
    
    if not data.get("report_week"):
        data["report_week"] = report_week

    # Populate evidence defaults
    if not data.get("evidence") and data.get("raw_text"):
        data["evidence"] = data["raw_text"]

    try:
        record = CropExtractionRecord(**data)
        return record
    except Exception as e:
        return None
