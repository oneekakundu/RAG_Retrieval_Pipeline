import json
from collections import defaultdict
from pathlib import Path
import pandas as pd
import sys

# Import config
sys.path.append(str(Path(__file__).resolve().parents[1]))
import config

class CalendarBuilder:
    """Aggregates individual evidence records into a standardized, week-by-week Crop Calendar."""

    def build_calendar(self, evidence_records: list[dict]) -> list[dict]:
        """
        Groups evidence by (crop, state, report_week) and aggregates the fields:
        - growth_stage: most frequent value (mode)
        - pests: list of unique pests
        - diseases: list of unique diseases
        - advisories: list of unique advisories
        """
        if not evidence_records:
            return []

        # Grouping container
        grouped = defaultdict(list)
        for record in evidence_records:
            # Skip records without valid crop/state
            crop = record.get("crop", "General")
            state = record.get("state", "All India")
            week = record.get("report_week")
            
            if not week:
                continue
                
            key = (crop, state, int(week))
            grouped[key].append(record)

        calendar_entries = []

        for (crop, state, week), records in grouped.items():
            # 1. Growth Stage: Mode (most frequent)
            stage_counts = defaultdict(int)
            for r in records:
                stage = r.get("growth_stage", "Active Growth")
                stage_counts[stage] += 1
            
            # Find the most frequent growth stage
            best_stage = max(stage_counts, key=stage_counts.get)

            # 2. Pests and Diseases: collect unique values
            pests = set()
            diseases = set()
            advisories = set()
            
            for r in records:
                p = r.get("pest", "None")
                d = r.get("disease", "None")
                adv = r.get("advisory", "")
                
                if p and p.lower() not in ["none", "none reported", "below etl"]:
                    pests.add(p)
                if d and d.lower() not in ["none", "none reported", "below etl"]:
                    diseases.add(d)
                if adv and adv.strip().lower() not in ["", "no specific advisory", "none"]:
                    # Clean and shorten advisory if it is too long
                    clean_adv = adv.strip()
                    if len(clean_adv) > 200:
                        clean_adv = clean_adv[:197] + "..."
                    advisories.add(clean_adv)

            pests_str = ", ".join(sorted(pests)) if pests else "None Reported"
            diseases_str = ", ".join(sorted(diseases)) if diseases else "None Reported"
            advisories_list = list(advisories) if advisories else ["Normal operations"]

            # Average confidence
            avg_conf = sum(r.get("confidence", 1.0) for r in records) / len(records)

            calendar_entries.append({
                "crop": crop,
                "state": state,
                "report_week": week,
                "growth_stage": best_stage,
                "pests": pests_str,
                "diseases": diseases_str,
                "advisories": "; ".join(advisories_list),
                "evidence_count": len(records),
                "confidence": round(avg_conf, 4)
            })

        # Sort calendar by Crop, State, Week
        calendar_entries.sort(key=lambda x: (x["crop"], x["state"], x["report_week"]))
        return calendar_entries

if __name__ == "__main__":
    builder = CalendarBuilder()
    test_evidence = [
        {"crop": "Rice", "state": "Odisha", "report_week": 25, "growth_stage": "Tillering", "pest": "Stem borer", "disease": "None"},
        {"crop": "Rice", "state": "Odisha", "report_week": 25, "growth_stage": "Tillering", "pest": "Stem borer", "disease": "Blast"},
        {"crop": "Rice", "state": "Odisha", "report_week": 26, "growth_stage": "Tillering", "pest": "Stem borer", "disease": "None"},
        {"crop": "Rice", "state": "Odisha", "report_week": 27, "growth_stage": "Panicle Initiation", "pest": "None", "disease": "Blast"}
    ]
    print(builder.build_calendar(test_evidence))
