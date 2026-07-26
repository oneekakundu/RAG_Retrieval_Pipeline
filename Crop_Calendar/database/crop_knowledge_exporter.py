import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

sys.path.append(str(Path(__file__).resolve().parents[1]))
import config
from database.sqlite_manager import SQLiteManager

logger = logging.getLogger("CropKnowledgeExporter")

class CropKnowledgeExporter:
    """
    Exports structured, year-partitioned Master Crop Knowledge Views 
    from SQLite into data/crop_knowledge/<CropName>/<Year>.json.
    """

    def __init__(self, db_manager: SQLiteManager = None):
        self.db = db_manager or SQLiteManager()
        self.knowledge_dir = config.CROP_KNOWLEDGE_DIR
        self.knowledge_dir.mkdir(parents=True, exist_ok=True)

    def export_all(self) -> Dict[str, int]:
        """
        Query crop_records from SQLite, group by (crop, year), and write/update year-partitioned JSON files.
        Returns dictionary mapping CropName -> total_observations.
        """
        records = self.db.load_all_records()
        if not records:
            logger.info("No crop records found in database to export to Crop Knowledge Base.")
            return {}

        # Group by crop -> year -> list of observation dicts
        crop_year_map: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}

        for rec in records:
            crop = rec.get("crop", "Unknown")
            report_date = rec.get("report_date") or rec.get("report_week", "")
            
            # Extract year from YYYY-MM-DD
            year = "2026"
            if report_date and len(report_date) >= 4 and report_date[:4].isdigit():
                year = report_date[:4]

            crop_year_map.setdefault(crop, {}).setdefault(year, []).append(rec)

        summary_counts = {}

        for crop_name, year_dict in crop_year_map.items():
            # Create subfolder data/crop_knowledge/<CropName>/
            crop_dir = self.knowledge_dir / crop_name
            crop_dir.mkdir(parents=True, exist_ok=True)

            total_crop_obs = 0

            for year, obs_list in year_dict.items():
                total_crop_obs += len(obs_list)

                # Compute pre-aggregated statistics for fast UI queries
                states_observed = sorted(list(set(r.get("state") for r in obs_list if r.get("state"))))
                growth_stages = sorted(list(set(r.get("growth_stage") for r in obs_list if r.get("growth_stage"))))
                common_pests = sorted(list(set(r.get("pest") or r.get("pest_or_disease") for r in obs_list if (r.get("pest") or r.get("pest_or_disease")) and (r.get("pest") or r.get("pest_or_disease")).lower() not in ["none", "none reported"])))
                common_diseases = sorted(list(set(r.get("disease") or r.get("pest_or_disease") for r in obs_list if (r.get("disease") or r.get("pest_or_disease")) and (r.get("disease") or r.get("pest_or_disease")).lower() not in ["none", "none reported"])))
                
                dates = [r.get("report_date") for r in obs_list if r.get("report_date")]
                first_app = min(dates) if dates else ""
                latest_app = max(dates) if dates else ""

                formatted_observations = []
                for r in obs_list:
                    formatted_observations.append({
                        "id": r.get("id"),
                        "date": r.get("report_date") or r.get("report_week"),
                        "report_week": r.get("report_date") or r.get("report_week"),
                        "state": r.get("state"),
                        "district": r.get("district", "State-wide"),
                        "growth_stage": r.get("growth_stage"),
                        "crop_operation": r.get("crop_operation"),
                        "weather_condition": r.get("weather_condition"),
                        "pest": r.get("pest") or r.get("pest_or_disease"),
                        "disease": r.get("disease") or r.get("pest_or_disease"),
                        "pest_or_disease": r.get("pest_or_disease"),
                        "severity": r.get("severity"),
                        "affected_area": r.get("affected_area"),
                        "irrigation": r.get("irrigation"),
                        "nutrient_management": r.get("nutrient_management"),
                        "expected_impact": r.get("expected_impact"),
                        "evidence": r.get("evidence") or r.get("raw_text") or r.get("original_text", ""),
                        "provenance": {
                            "source_pdf": r.get("source_pdf", "unknown.pdf"),
                            "page_number": r.get("page_number", 1),
                            "section_heading": r.get("section_heading", "General Observation"),
                            "confidence": r.get("confidence", 0.95),
                            "source_method": r.get("source_method", "rule_based")
                        }
                    })

                payload = {
                    "crop": crop_name,
                    "year": year,
                    "metadata": {
                        "generated_at": datetime.now().isoformat(),
                        "total_observations": len(obs_list),
                        "pipeline_version": config.PIPELINE_VERSION
                    },
                    "statistics": {
                        "states_observed": states_observed,
                        "growth_stages": growth_stages,
                        "common_pests": common_pests,
                        "common_diseases": common_diseases,
                        "first_appearance": first_app,
                        "latest_appearance": latest_app
                    },
                    "observations": formatted_observations
                }

                out_json_path = crop_dir / f"{year}.json"
                with open(out_json_path, "w", encoding="utf-8") as f:
                    json.dump(payload, f, indent=2, ensure_ascii=False)

            summary_counts[crop_name] = total_crop_obs

        # Generate lightweight summary file (knowledge_summary.json)
        knowledge_summary = {}
        for crop_name, year_dict in crop_year_map.items():
            all_crop_recs = []
            for obs_list in year_dict.values():
                all_crop_recs.extend(obs_list)
            
            states_count = len(set(r.get("state") for r in all_crop_recs if r.get("state")))
            dates = [r.get("report_date") or r.get("report_week") for r in all_crop_recs if (r.get("report_date") or r.get("report_week"))]
            dates = [d for d in dates if d and len(d) >= 4]
            first_report = min(dates) if dates else ""
            latest_report = max(dates) if dates else ""
            
            knowledge_summary[crop_name] = {
                "observations": len(all_crop_recs),
                "states": states_count,
                "first_report": first_report,
                "latest_report": latest_report
            }

        # Write knowledge_summary.json to crop_knowledge folder and data folder
        summary_paths = [
            self.knowledge_dir / "knowledge_summary.json",
            config.DATA_DIR / "knowledge_summary.json"
        ]
        for sp in summary_paths:
            try:
                with open(sp, "w", encoding="utf-8") as f:
                    json.dump(knowledge_summary, f, indent=2, ensure_ascii=False)
                logger.info(f"Generated lightweight knowledge summary at {sp}")
            except Exception as e:
                logger.warning(f"Failed writing summary to {sp}: {e}")

        logger.info(f"Exported Crop Knowledge Base views for {len(summary_counts)} crops to {self.knowledge_dir}")
        return summary_counts

if __name__ == "__main__":
    exporter = CropKnowledgeExporter()
    res = exporter.export_all()
    print("Crop Knowledge Export Summary:", res)
    print("Crop Knowledge Export Summary:", res)
