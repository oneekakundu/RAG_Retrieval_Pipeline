import sys
from pathlib import Path

# Import config & normalizer
sys.path.append(str(Path(__file__).resolve().parents[1]))
import config
from extraction.normalizer import Normalizer

class EvidenceBuilder:
    """Combines text chunks, extracted entities, and metadata into structured evidence records."""

    def build_evidence(self, chunk: dict, extraction_result: dict) -> list[dict]:
        """
        Builds a list of structured evidence dictionaries from a chunk and its GLiNER entities.
        Generates Cartesian products for multiple crops and states to keep records atomic.
        """
        entities = extraction_result.get("entities", {})
        confidence = extraction_result.get("confidence", 1.0)
        
        # Get raw extracted texts
        raw_crops = [e["text"] for e in entities.get("crop", [])]
        raw_states = [e["text"] for e in entities.get("state", [])]
        raw_districts = [e["text"] for e in entities.get("district", [])]
        raw_stages = [e["text"] for e in entities.get("growth stage", [])]
        raw_pests = [e["text"] for e in entities.get("pest", [])] + [e["text"] for e in entities.get("insect", [])]
        raw_diseases = [e["text"] for e in entities.get("disease", [])]
        raw_weathers = [e["text"] for e in entities.get("weather condition", [])] + [e["text"] for e in entities.get("weather parameter", [])]
        raw_advisories = [e["text"] for e in entities.get("advisory", [])]

        # Use semantic chunk contexts as fallback
        if not raw_crops and chunk.get("crop_context"):
            raw_crops = [chunk["crop_context"]]
        if not raw_states and chunk.get("state_context"):
            raw_states = [chunk["state_context"]]

        # Default values if empty
        if not raw_crops:
            raw_crops = ["General"]
        if not raw_states:
            raw_states = ["All India"]

        # Parse date and week from source PDF
        report_date, report_week = Normalizer.parse_date_and_week(chunk["source_pdf"])

        # Normalize elements
        norm_crops = list(set(Normalizer.normalize_crop(c) for c in raw_crops))
        norm_states = list(set(Normalizer.normalize_state(s) for s in raw_states))
        
        # We group remaining fields to form a single observation.
        # If there are multiple stages, we join them or use the first.
        district_val = raw_districts[0].title() if raw_districts else "State-wide"
        stage_val = Normalizer.normalize_stage(raw_stages[0]) if raw_stages else "Active Growth"
        pest_val = Normalizer.normalize_pest_disease(raw_pests[0]) if raw_pests else "None"
        disease_val = Normalizer.normalize_pest_disease(raw_diseases[0]) if raw_diseases else "None"
        weather_val = raw_weathers[0].strip() if raw_weathers else "Normal"
        advisory_val = raw_advisories[0].strip() if raw_advisories else "No specific advisory"

        records = []
        
        # Cartesian product of crops and states
        for crop in norm_crops:
            for state in norm_states:
                # If it's a section heading, it might not be a real observation, so skip if both stage/pest/disease are defaults
                if chunk.get("type") == "heading":
                    continue
                
                records.append({
                    "crop": crop,
                    "state": state,
                    "district": district_val,
                    "report_date": report_date,
                    "report_week": report_week,
                    "growth_stage": stage_val,
                    "pest": pest_val,
                    "disease": disease_val,
                    "weather_condition": weather_val,
                    "advisory": advisory_val,
                    "page_number": chunk.get("page_number", 1),
                    "source_pdf": chunk.get("source_pdf", "unknown.pdf"),
                    "confidence": confidence,
                    "original_text": chunk.get("text", "")
                })
                
        return records

if __name__ == "__main__":
    builder = EvidenceBuilder()
    chunk = {
        "text": "Sowing of Paddy in Punjab is delayed due to weather.",
        "source_pdf": "Minutes of the meeting of CWWG as on 08.06.2026.pdf",
        "page_number": 2,
        "crop_context": None,
        "state_context": None
    }
    extracted = {
        "entities": {
            "crop": [{"text": "Paddy", "score": 0.99}],
            "state": [{"text": "Punjab", "score": 0.98}],
            "growth stage": [{"text": "Sowing", "score": 0.95}],
            "weather condition": [{"text": "delayed due to weather", "score": 0.8}]
        },
        "confidence": 0.93
    }
    print(builder.build_evidence(chunk, extracted))
