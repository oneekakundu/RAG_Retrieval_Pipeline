import json
import logging
import os
import re
import time
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional

import requests

import config
from extractor.schemas import SemanticExtractionSchema, ObservationType, FieldEvidence
from extractor.normalizer import Normalizer

logger = logging.getLogger("SemanticInterpreter")

SEMANTIC_INTERPRETER_PROMPT = """You are an authenticated, document-grounded Agricultural Semantic Interpreter.
Your sole job is to extract factual, evidence-backed agricultural observations from the provided report text.

CRITICAL DIRECTIVES:
1. DO NOT HALLUCINATE.
2. DO NOT INFER agricultural facts not explicitly present in the text.
3. If a field is unsupported or not mentioned in the text, leave it NULL / empty.
4. Only populate values explicitly supported by the provided text evidence.
5. NEVER assign area coverage numbers (e.g., "108.77 lakh ha", "84% of normal area") to pests or diseases. Area coverage, normal area, and acreage statistics belong strictly under "statistics" or "sowing_status" or "harvest_status".
6. Pests and diseases MUST BE actual biological organism names (e.g., "Stem borer", "Brown plant hopper", "Downy mildew", "Blast"). If no pest or disease organism is named in the text, pests and diseases MUST BE EMPTY ARRAYS [].

Report Metadata:
- Crop: {crop}
- State Context: {state}
- Report Week: {week}
- Source Page: {page}

Report Chunk Text:
\"\"\"
{chunk_text}
\"\"\"

Classify the text into ONE primary observation_type from this exact list:
- "Growth Stage"
- "Harvest Progress"
- "Sowing Progress"
- "Pest Incidence"
- "Disease Incidence"
- "Irrigation"
- "Nutrient Deficiency"
- "Crop Condition"
- "Area Coverage"
- "Yield"
- "Market Information"
- "Other"

For EVERY extracted field (growth_stage, sowing_status, harvest_status, pests, diseases, nutrient_deficiencies, statistics), you MUST provide a JSON object containing:
  "value": The exact extracted factual value.
  "evidence": The exact verbatim sentence from the chunk text that proves this value.

If there is no exact sentence supporting a field, DO NOT EXTRACT IT.

Return ONLY a valid JSON object matching this schema:
{{
  "crop": "{crop}",
  "state": "{state}",
  "week": "{week}",
  "observation_type": "Primary observation type",
  "growth_stage": {{ "value": "Flowering", "evidence": "Exact sentence..." }} OR null,
  "sowing_status": {{ "value": "Sowing 80% complete", "evidence": "Exact sentence..." }} OR null,
  "harvest_status": {{ "value": "100% harvested", "evidence": "Exact sentence..." }} OR null,
  "pests": [ {{ "value": "Stem borer", "evidence": "Exact sentence..." }} ],
  "diseases": [ {{ "value": "Blast", "evidence": "Exact sentence..." }} ],
  "nutrient_deficiencies": [],
  "statistics": [ {{ "value": "108.77 lakh ha area covered", "evidence": "Exact sentence..." }} ],
  "evidence": [ "Sentence 1", "Sentence 2" ],
  "confidence": 0.95
}}
"""

class SemanticInterpreter:
    """
    Semantic Interpretation Layer using Gemini LLM.
    Parses cleaned crop chunks into strict, evidence-grounded Pydantic schemas.
    """

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        self.api_key = api_key or config.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY")
        self.model_name = model_name or config.LLM_MODEL or "gemini-2.5-flash"
        self.cache_dir = config.CACHE_DIR / "semantic_interpretation"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _compute_chunk_hash(self, chunk: Dict[str, Any], week: str) -> str:
        content = f"{chunk.get('source_pdf')}_{chunk.get('page_number')}_{chunk.get('detected_crop')}_{chunk.get('chunk_text')}_{week}"
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def interpret(self, chunk: Dict[str, Any], report_week: str) -> Optional[SemanticExtractionSchema]:
        """
        Interprets a cleaned crop chunk into a strict SemanticExtractionSchema.
        Includes local file-level response caching and API retry logic.
        """
        chunk_text = chunk.get("chunk_text", "").strip()
        if not chunk_text or len(chunk_text) < 5:
            return None

        crop = chunk.get("detected_crop") or Normalizer.normalize_crop(chunk_text)
        state = chunk.get("state_context") or Normalizer.normalize_state(chunk_text)
        page = chunk.get("page_number", 1)

        # Check local cache first
        chunk_hash = self._compute_chunk_hash(chunk, report_week)
        cache_file = self.cache_dir / f"{chunk_hash}.json"

        if config.CACHE_ENABLED and cache_file.exists():
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    cached_data = json.load(f)
                logger.info(f"[Cache Hit] Loaded semantic interpretation for {crop} ({state})")
                return SemanticExtractionSchema(**cached_data)
            except Exception as e:
                logger.warning(f"Failed to read cache {cache_file}: {e}")

        # Rule-based fast interpretation if no API key
        if not self.api_key:
            logger.info("[SemanticInterpreter] No GEMINI_API_KEY found, performing deterministic rule-based semantic mapping...")
            schema_data = self._fallback_rule_interpret(chunk, crop, state, report_week, page)
            self._save_cache(cache_file, schema_data)
            return SemanticExtractionSchema(**schema_data)

        # Call Gemini API
        prompt = SEMANTIC_INTERPRETER_PROMPT.format(
            crop=crop,
            state=state,
            week=report_week,
            page=page,
            chunk_text=chunk_text
        )

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={self.api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.0, "responseMimeType": "application/json"}
        }

        raw_response_text = None
        for attempt in range(3):
            try:
                resp = requests.post(url, json=payload, timeout=30)
                if resp.status_code == 429:
                    time.sleep(2.0 * (attempt + 1))
                    continue
                if resp.status_code == 404 and "2.5" in self.model_name:
                    fallback_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.api_key}"
                    resp = requests.post(fallback_url, json=payload, timeout=30)

                resp.raise_for_status()
                res_data = resp.json()
                candidates = res_data.get("candidates", [])
                if candidates:
                    raw_response_text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                    break
            except Exception as e:
                logger.warning(f"API Attempt {attempt+1} failed for {crop}: {e}")
                time.sleep(1.0)

        if not raw_response_text:
            logger.warning(f"[SemanticInterpreter] API calls exhausted for {crop}. Falling back to rule-based interpreter.")
            schema_data = self._fallback_rule_interpret(chunk, crop, state, report_week, page)
            self._save_cache(cache_file, schema_data)
            return SemanticExtractionSchema(**schema_data)

        # Parse JSON
        parsed_schema = self._parse_json_to_schema(raw_response_text, crop, state, report_week, page, chunk_text)
        if parsed_schema:
            self._save_cache(cache_file, parsed_schema.model_dump())
            return parsed_schema

        # Fallback if parsing fails
        schema_data = self._fallback_rule_interpret(chunk, crop, state, report_week, page)
        self._save_cache(cache_file, schema_data)
        return SemanticExtractionSchema(**schema_data)

    def _parse_json_to_schema(
        self, 
        raw_json: str, 
        crop: str, 
        state: str, 
        week: str, 
        page: int, 
        chunk_text: str
    ) -> Optional[SemanticExtractionSchema]:
        try:
            cleaned = re.sub(r"^```(?:json)?\s*", "", raw_json.strip(), flags=re.IGNORECASE)
            cleaned = re.sub(r"\s*```$", "", cleaned).strip()
            match = re.search(r"(\{.*\})", cleaned, re.DOTALL)
            if match:
                cleaned = match.group(1)

            data = json.loads(cleaned)
            data["crop"] = Normalizer.normalize_crop(data.get("crop") or crop)
            data["state"] = Normalizer.normalize_state(data.get("state") or state)
            data["week"] = week

            # Sanitize pest/disease entries to prevent table noise leakage
            sanitized_pests = []
            for item in data.get("pests", []):
                if isinstance(item, dict) and item.get("value"):
                    norm_pest = Normalizer.normalize_pest_disease(item["value"])
                    if norm_pest and norm_pest.lower() not in ["none", "nil", "n/a"]:
                        sanitized_pests.append({"value": norm_pest, "evidence": item.get("evidence", chunk_text[:200])})
            data["pests"] = sanitized_pests

            sanitized_diseases = []
            for item in data.get("diseases", []):
                if isinstance(item, dict) and item.get("value"):
                    norm_disease = Normalizer.normalize_pest_disease(item["value"])
                    if norm_disease and norm_disease.lower() not in ["none", "nil", "n/a"]:
                        sanitized_diseases.append({"value": norm_disease, "evidence": item.get("evidence", chunk_text[:200])})
            data["diseases"] = sanitized_diseases

            return SemanticExtractionSchema(**data)
        except Exception as e:
            logger.error(f"Failed to parse LLM JSON response: {e}")
            return None

    def _fallback_rule_interpret(
        self, 
        chunk: Dict[str, Any], 
        crop: str, 
        state: str, 
        week: str, 
        page: int
    ) -> Dict[str, Any]:
        text = chunk.get("chunk_text", "").strip()
        t_lower = text.lower()

        obs_type = ObservationType.OTHER.value
        growth_stage = None
        sowing_status = None
        harvest_status = None
        pests = []
        diseases = []
        statistics = []

        # Check harvest vs sowing vs area coverage vs plant protection
        if "harvest" in t_lower or "harvested" in t_lower:
            obs_type = ObservationType.HARVEST_PROGRESS.value
            growth_stage = {"value": "Harvesting", "evidence": text}
            harvest_status = {"value": text, "evidence": text}
        elif "sown" in t_lower or "sowing" in t_lower:
            obs_type = ObservationType.SOWING_PROGRESS.value
            growth_stage = {"value": "Sowing", "evidence": text}
            sowing_status = {"value": text, "evidence": text}
        elif "lakh ha" in t_lower or "area coverage" in t_lower or "% of normal" in t_lower:
            obs_type = ObservationType.AREA_COVERAGE.value
            statistics.append({"value": text, "evidence": text})
        
        # Check actual pest or disease presence
        norm_pd = Normalizer.normalize_pest_disease(text)
        if norm_pd:
            obs_type = ObservationType.PEST_INCIDENCE.value
            pests.append({"value": norm_pd, "evidence": text})

        return {
            "crop": crop,
            "state": state,
            "week": week,
            "observation_type": obs_type,
            "growth_stage": growth_stage,
            "sowing_status": sowing_status,
            "harvest_status": harvest_status,
            "pests": pests,
            "diseases": diseases,
            "nutrient_deficiencies": [],
            "statistics": statistics,
            "evidence": [text],
            "confidence": 0.90 if (harvest_status or sowing_status or pests or diseases) else 0.70
        }

    def _save_cache(self, cache_file: Path, data: Dict[str, Any]):
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"Failed writing cache to {cache_file}: {e}")
