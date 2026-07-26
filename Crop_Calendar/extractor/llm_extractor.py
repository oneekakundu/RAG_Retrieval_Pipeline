import json
import os
import re
import time
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import requests

import config
from extractor.validators import validate_and_clean_record, CropExtractionRecord
from extractor.normalizer import Normalizer

class BaseExtractor(ABC):
    """Abstract Base Class for Crop Information Extractors."""

    def __init__(self, prompt_template_path: str = None):
        prompt_path = prompt_template_path or (config.PROMPTS_DIR / "extraction_prompt.txt")
        try:
            with open(prompt_path, "r", encoding="utf-8") as f:
                self.prompt_template = f.read()
        except Exception:
            self.prompt_template = (
                "Extract structured crop status from text.\nReport Week: {report_week}\nText: {chunk_text}\n"
                "Return JSON array with keys: crop, state, growth_stage, pest_or_disease, report_week"
            )

    @abstractmethod
    def extract(self, chunk: Dict[str, Any], report_week: str) -> List[Dict[str, Any]]:
        """
        Extract structured crop information records from a chunk.
        Must return a list of validated dicts.
        """
        pass

    def _parse_and_validate_json(self, raw_response: str, report_week: str) -> List[Dict[str, Any]]:
        """Helper to parse raw JSON output from LLM and validate via Pydantic validator."""
        if not raw_response:
            return []

        # Strip markdown block formatting
        cleaned = re.sub(r"^```(?:json)?\s*", "", raw_response.strip(), flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        cleaned = cleaned.strip()

        # Try regex extract array or dict if extra text surrounds JSON
        match = re.search(r"(\[.*\]|\{.*\})", cleaned, re.DOTALL)
        if match:
            cleaned = match.group(1)

        records_data = []
        try:
            parsed = json.loads(cleaned)
            if isinstance(parsed, dict):
                records_data = [parsed]
            elif isinstance(parsed, list):
                records_data = parsed
        except Exception as e:
            print(f"[LLMExtractor] JSON parse error: {e}. Raw text:\n{raw_response[:200]}")
            return []

        validated_records = []
        for item in records_data:
            if not isinstance(item, dict):
                continue
            item["report_week"] = report_week
            record = validate_and_clean_record(item, report_week)
            if record:
                validated_records.append(record.model_dump())
            else:
                print(f"[LLMExtractor] Record rejected by Pydantic validation: {item}")

        return validated_records


class GeminiExtractor(BaseExtractor):
    """Gemini LLM Provider Extractor."""

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        super().__init__()
        self.api_key = api_key or config.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY")
        self.model_name = model_name or config.LLM_MODEL or "gemini-2.5-flash"

    def extract(self, chunk: Dict[str, Any], report_week: str) -> List[Dict[str, Any]]:
        chunk_text = chunk.get("chunk_text", "")
        if not chunk_text.strip():
            return []

        if not self.api_key:
            print("[GeminiExtractor] No GEMINI_API_KEY found, falling back to RuleBasedExtractor")
            return FallbackExtractor().extract(chunk, report_week)

        prompt = self.prompt_template.replace("{report_week}", report_week).replace("{chunk_text}", chunk_text)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={self.api_key}"

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.1, "responseMimeType": "application/json"}
        }

        for attempt in range(4):
            try:
                resp = requests.post(url, json=payload, timeout=30)
                if resp.status_code == 429:
                    wait_sec = 2.0 * (attempt + 1)
                    time.sleep(wait_sec)
                    continue
                if resp.status_code == 404 and "2.5" in self.model_name:
                    fallback_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.api_key}"
                    resp = requests.post(fallback_url, json=payload, timeout=30)

                resp.raise_for_status()
                res_data = resp.json()
                candidates = res_data.get("candidates", [])
                if candidates:
                    text_out = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                    return self._parse_and_validate_json(text_out, report_week)
            except Exception as e:
                if attempt == 3:
                    print(f"[GeminiExtractor] API call failed after retries: {e}")
                time.sleep(1.0)

        return FallbackExtractor().extract(chunk, report_week)


class OpenAIExtractor(BaseExtractor):
    """OpenAI LLM Provider Extractor."""

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        super().__init__()
        self.api_key = api_key or config.OPENAI_API_KEY or os.getenv("OPENAI_API_KEY")
        self.model_name = model_name or "gpt-4o-mini"

    def extract(self, chunk: Dict[str, Any], report_week: str) -> List[Dict[str, Any]]:
        chunk_text = chunk.get("chunk_text", "")
        if not chunk_text.strip():
            return []

        if not self.api_key:
            print("[OpenAIExtractor] No OPENAI_API_KEY found, falling back to RuleBasedExtractor")
            return FallbackExtractor().extract(chunk, report_week)

        prompt = self.prompt_template.replace("{report_week}", report_week).replace("{chunk_text}", chunk_text)
        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": "You are a JSON-only agricultural extraction bot."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"}
        }

        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=30)
            resp.raise_for_status()
            res_data = resp.json()
            text_out = res_data["choices"][0]["message"]["content"]
            return self._parse_and_validate_json(text_out, report_week)
        except Exception as e:
            print(f"[OpenAIExtractor] API call failed: {e}")

        return FallbackExtractor().extract(chunk, report_week)


class ClaudeExtractor(BaseExtractor):
    """Anthropic Claude LLM Provider Extractor."""

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        super().__init__()
        self.api_key = api_key or config.ANTHROPIC_API_KEY or os.getenv("ANTHROPIC_API_KEY")
        self.model_name = model_name or "claude-3-5-haiku-20241022"

    def extract(self, chunk: Dict[str, Any], report_week: str) -> List[Dict[str, Any]]:
        chunk_text = chunk.get("chunk_text", "")
        if not chunk_text.strip():
            return []

        if not self.api_key:
            print("[ClaudeExtractor] No ANTHROPIC_API_KEY found, falling back to RuleBasedExtractor")
            return FallbackExtractor().extract(chunk, report_week)

        prompt = self.prompt_template.replace("{report_week}", report_week).replace("{chunk_text}", chunk_text)
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        payload = {
            "model": self.model_name,
            "max_tokens": 1000,
            "messages": [{"role": "user", "content": prompt}]
        }

        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=30)
            resp.raise_for_status()
            res_data = resp.json()
            text_out = res_data["content"][0]["text"]
            return self._parse_and_validate_json(text_out, report_week)
        except Exception as e:
            print(f"[ClaudeExtractor] API call failed: {e}")

        return FallbackExtractor().extract(chunk, report_week)


class FallbackExtractor(BaseExtractor):
    """Deterministic Rule-Based / Pattern Extractor for Offline & Fallback Execution."""

    def extract(self, chunk: Dict[str, Any], report_week: str) -> List[Dict[str, Any]]:
        chunk_text = chunk.get("chunk_text", "")
        if not chunk_text:
            return []

        # Example pattern matching for: "Maize - vegetative stage - Downy mildew in Karnataka."
        detected_crop = chunk.get("detected_crop") or Normalizer.normalize_crop(chunk_text)
        
        # State detection
        state = "All India"
        for st_key in config.NORMALIZER_STATES if hasattr(config, "NORMALIZER_STATES") else []:
            if re.search(rf"\b{re.escape(st_key)}\b", chunk_text, re.IGNORECASE):
                state = Normalizer.normalize_state(st_key)
                break
        if state == "All India":
            state = Normalizer.normalize_state(chunk_text)

        # Stage detection
        stage = Normalizer.normalize_stage(chunk_text)

        # Pest/Disease detection
        pest_disease = Normalizer.normalize_pest_disease(chunk_text)

        raw_item = {
            "crop": detected_crop,
            "state": state,
            "district": "State-wide",
            "growth_stage": stage,
            "pest_or_disease": pest_disease,
            "pest": pest_disease,
            "disease": pest_disease,
            "evidence": chunk_text.strip(),
            "raw_text": chunk_text.strip(),
            "source_pdf": chunk.get("source_pdf", "unknown.pdf"),
            "page_number": chunk.get("page_number", 1),
            "section_heading": chunk.get("heading", "General Observation"),
            "report_week": report_week
        }

        record = validate_and_clean_record(raw_item, report_week)
        return [record.model_dump()] if record else []


def get_extractor(provider_name: Optional[str] = None) -> BaseExtractor:
    """Factory function to get LLM Extractor instance based on provider name."""
    provider = (provider_name or config.LLM_PROVIDER or "gemini").lower().strip()
    if provider == "gemini":
        return GeminiExtractor()
    elif provider == "openai":
        return OpenAIExtractor()
    elif provider == "claude":
        return ClaudeExtractor()
    elif provider in ["fallback", "rule", "mock"]:
        return FallbackExtractor()
    else:
        print(f"[ExtractorFactory] Unknown provider '{provider}', defaulting to GeminiExtractor")
        return GeminiExtractor()
