import re
from typing import List, Dict, Any, Tuple, Optional

import config
from extractor.normalizer import (
    Normalizer, CROP_MAPPING, STATE_MAPPING, STAGE_MAPPING, PEST_DISEASE_MAPPING
)
from extractor.validators import validate_and_clean_record

class RuleBasedExtractor:
    """
    Deterministic Rule-Based Extractor for Agricultural CWWG Reports.
    Parses core agricultural variables and sentence evidence context.
    """

    def __init__(self):
        self.crop_keywords = set(CROP_MAPPING.keys())
        self.state_keywords = set(STATE_MAPPING.keys())
        self.stage_keywords = set(STAGE_MAPPING.keys())
        self.pest_disease_keywords = set(PEST_DISEASE_MAPPING.keys())

    def _extract_severity(self, text: str) -> Optional[str]:
        t_lower = text.lower()
        if "above etl" in t_lower or "economic threshold level" in t_lower or "severe" in t_lower:
            return "Above ETL / Severe"
        elif "moderate" in t_lower or "medium" in t_lower:
            return "Moderate"
        elif "low" in t_lower or "trace" in t_lower or "below etl" in t_lower:
            return "Low / Below ETL"
        return None

    def _extract_crop_operation(self, text: str) -> Optional[str]:
        t_lower = text.lower()
        if "sowing" in t_lower or "sown" in t_lower:
            return "Sowing"
        elif "transplanting" in t_lower or "nursery" in t_lower:
            return "Transplanting / Nursery"
        elif "weeding" in t_lower or "hoeing" in t_lower:
            return "Interculture / Weeding"
        elif "harvesting" in t_lower or "harvest" in t_lower:
            return "Harvesting"
        elif "monitoring" in t_lower or "surveillance" in t_lower:
            return "Monitoring"
        return None

    def _extract_irrigation(self, text: str) -> Optional[str]:
        t_lower = text.lower()
        for kw in ["irrigation", "waterlogging", "submerged", "canal water", "rainfed", "water stress"]:
            if kw in t_lower:
                return kw.title()
        return None

    def _extract_nutrient_management(self, text: str) -> Optional[str]:
        t_lower = text.lower()
        for kw in ["fertilizer", "urea", "npk", "top dressing", "zinc", "manure"]:
            if kw in t_lower:
                return kw.title()
        return None

    def _extract_hyphenated_pattern(self, text: str, chunk: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Pattern: "Maize - vegetative stage - Downy mildew in Karnataka"
        """
        parts = [p.strip() for p in text.split("-") if p.strip()]
        if len(parts) >= 3:
            crop_candidate = parts[0]
            stage_candidate = parts[1]
            rem_candidate = parts[2]

            norm_crop = Normalizer.normalize_crop(crop_candidate)
            norm_stage = Normalizer.normalize_stage(stage_candidate)
            norm_state = Normalizer.normalize_state(rem_candidate)
            norm_pest = Normalizer.normalize_pest_disease(rem_candidate)

            if norm_crop != "Unknown":
                return {
                    "crop": norm_crop,
                    "state": norm_state,
                    "growth_stage": norm_stage,
                    "pest_or_disease": norm_pest,
                    "pest": norm_pest,
                    "severity": self._extract_severity(text),
                    "crop_operation": self._extract_crop_operation(text),
                    "evidence": text.strip(),
                    "raw_text": text.strip(),
                    "source_pdf": chunk.get("source_pdf", "unknown.pdf"),
                    "page_number": chunk.get("page_number", 1),
                    "section_heading": chunk.get("heading", "General Observation"),
                    "confidence": 0.95,
                    "source_method": "rule_based",
                    "is_ambiguous": False
                }
        return None

    def extract(self, chunk: Dict[str, Any], report_week: str) -> Tuple[List[Dict[str, Any]], bool]:
        """
        Extracts structured crop observations from chunk text deterministically.
        Returns (records_list, is_ambiguous_flag).
        """
        chunk_text = chunk.get("chunk_text", "")
        if not chunk_text or len(chunk_text.strip()) < 5:
            return [], False

        # Try pattern 1: Hyphenated format
        hyphen_rec = self._extract_hyphenated_pattern(chunk_text, chunk)
        if hyphen_rec:
            hyphen_rec["report_week"] = report_week
            record = validate_and_clean_record(hyphen_rec, report_week)
            if record:
                rec_dict = record.model_dump()
                rec_dict["confidence"] = 0.95
                rec_dict["source_method"] = "rule_based"
                return [rec_dict], False

        # Fallback to keyword matching & regex
        detected_crop = chunk.get("detected_crop") or Normalizer.normalize_crop(chunk_text)
        if detected_crop == "Unknown":
            return [], True

        detected_state = chunk.get("state_context") or Normalizer.normalize_state(chunk_text)
        detected_stage = Normalizer.normalize_stage(chunk_text)
        detected_pest = Normalizer.normalize_pest_disease(chunk_text)
        severity = self._extract_severity(chunk_text)
        crop_op = self._extract_crop_operation(chunk_text)
        irrigation = self._extract_irrigation(chunk_text)
        nutrient = self._extract_nutrient_management(chunk_text)

        has_detail = bool(detected_stage or detected_pest or crop_op)
        is_ambiguous = not has_detail

        confidence = 0.90 if has_detail else 0.60
        source_method = "rule_based"

        raw_item = {
            "crop": detected_crop,
            "state": detected_state,
            "district": "State-wide",
            "growth_stage": detected_stage,
            "crop_operation": crop_op,
            "pest_or_disease": detected_pest,
            "pest": detected_pest,
            "disease": detected_pest,
            "severity": severity,
            "irrigation": irrigation,
            "nutrient_management": nutrient,
            "evidence": chunk_text.strip(),
            "raw_text": chunk_text.strip(),
            "source_pdf": chunk.get("source_pdf", "unknown.pdf"),
            "page_number": chunk.get("page_number", 1),
            "section_heading": chunk.get("heading", "General Observation"),
            "report_week": report_week,
            "confidence": confidence,
            "source_method": source_method
        }

        record = validate_and_clean_record(raw_item, report_week)
        if record:
            rec_dict = record.model_dump()
            rec_dict["confidence"] = confidence
            rec_dict["source_method"] = source_method
            return [rec_dict], is_ambiguous
        
        return [], True
