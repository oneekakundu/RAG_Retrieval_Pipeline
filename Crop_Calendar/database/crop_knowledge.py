import json
import csv
import logging
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
import sys

# Ensure config is importable
sys.path.append(str(Path(__file__).resolve().parents[1]))
import config

logger = logging.getLogger("CropKnowledgeManager")

class CropKnowledgeManager:
    """
    Manages the permanent Crop Evidence Repository (Single Source of Truth).
    Handles incremental chunk storage, CSV generation, and metadata tracking.
    """
    def __init__(self):
        self.knowledge_dir = config.CROP_KNOWLEDGE_DIR
        self.knowledge_dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.knowledge_dir / "crop_index.json"

    def _get_hash(self, text: str) -> str:
        return hashlib.sha256(str(text).encode('utf-8')).hexdigest()

    def load_index(self) -> Dict[str, Any]:
        if self.index_path.exists():
            try:
                with open(self.index_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def save_index(self, index_data: Dict[str, Any]):
        with open(self.index_path, "w", encoding="utf-8") as f:
            json.dump(index_data, f, indent=2, ensure_ascii=False)

    def save_chunk(self, chunk: Dict[str, Any], pdf_name: str, pdf_hash: str, report_week: str) -> bool:
        """
        Saves the original chunk BEFORE interpretation. 
        Returns True if newly saved, False if already existed.
        """
        crop = chunk.get("crop")
        if not crop or crop == "Unknown":
            return False

        # Build schema as requested
        chunk_text = chunk.get("chunk_text", "")
        chunk_hash = self._get_hash(chunk_text)
        year = report_week[:4] if report_week and len(report_week) >= 4 else "unknown_year"

        # Directory structure: data/crop_knowledge/<Crop>/chunks/<Year>/
        crop_dir = self.knowledge_dir / crop
        chunks_dir = crop_dir / "chunks" / year
        chunks_dir.mkdir(parents=True, exist_ok=True)

        chunk_id = chunk.get("chunk_id", f"{pdf_name}_p{chunk.get('page_number', 1)}_{chunk_hash[:8]}")
        
        # Check if already exists by checking if a file with this hash exists (or similar logic)
        # Using chunk_id in filename
        chunk_file = chunks_dir / f"{chunk_id}.json"
        if chunk_file.exists():
            return False

        chunk_payload = {
            "chunk_id": chunk_id,
            "pdf_name": pdf_name,
            "pdf_hash": pdf_hash,
            "page": chunk.get("page_number", 1),
            "report_date": report_week,
            "report_week": report_week,
            "section": chunk.get("section_heading", ""),
            "crop": crop,
            "states": chunk.get("states", []),
            "chunk_type": chunk.get("chunk_type", "Narrative"),
            "observation_hint": chunk.get("observation_hint", ""),
            "chunk_text": chunk_text,
            "processed_timestamp": datetime.now().isoformat()
        }

        with open(chunk_file, "w", encoding="utf-8") as f:
            json.dump(chunk_payload, f, indent=2, ensure_ascii=False)

        # Update index
        index = self.load_index()
        if crop not in index:
            index[crop] = {
                "total_chunks": 0,
                "total_observations": 0,
                "states": 0,
                "first_report": report_week,
                "latest_report": report_week,
                "last_updated": datetime.now().isoformat(),
                "states_set": []
            }
        
        index[crop]["total_chunks"] += 1
        index[crop]["last_updated"] = datetime.now().isoformat()
        
        # Track states for index
        current_states = set(index[crop].get("states_set", []))
        current_states.update(chunk.get("states", []))
        index[crop]["states_set"] = list(current_states)
        index[crop]["states"] = len(current_states)
        
        # Update dates
        if report_week < index[crop].get("first_report", report_week):
            index[crop]["first_report"] = report_week
        if report_week > index[crop].get("latest_report", report_week):
            index[crop]["latest_report"] = report_week

        self.save_index(index)
        return True

    def export_derived_csvs(self, db_manager):
        """Generates observations.csv, timeline.csv, statistics.csv directly from the validated DB records"""
        records = db_manager.load_all_records()
        if not records:
            return

        crop_records = {}
        for rec in records:
            crop = rec.get("crop", "Unknown")
            crop_records.setdefault(crop, []).append(rec)

        index = self.load_index()

        for crop, recs in crop_records.items():
            crop_dir = self.knowledge_dir / crop
            crop_dir.mkdir(parents=True, exist_ok=True)
            
            # Observations
            obs_dir = crop_dir / "observations"
            obs_dir.mkdir(exist_ok=True)
            obs_file = obs_dir / "observations.csv"
            
            # Timeline
            timeline_dir = crop_dir / "timeline"
            timeline_dir.mkdir(exist_ok=True)
            timeline_file = timeline_dir / "timeline.csv"

            # Statistics
            stat_dir = crop_dir / "statistics"
            stat_dir.mkdir(exist_ok=True)
            stat_file = stat_dir / "statistics.csv"

            # Sort records chronologically
            recs.sort(key=lambda x: x.get("report_date") or x.get("report_week", ""))

            # 1. OBSERVATIONS CSV
            obs_fieldnames = [
                "Date", "Week", "Crop", "State", "Observation Type", "Growth Stage", 
                "Crop Operation", "Sowing Status", "Harvest Status", "Pest", "Disease",
                "Weather", "Irrigation", "Nutrient Management", "Statistics",
                "Evidence", "PDF Name", "Page", "Chunk ID", "Confidence", "Verification Status", "Source Method"
            ]
            with open(obs_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=obs_fieldnames)
                writer.writeheader()
                for r in recs:
                    writer.writerow({
                        "Date": r.get("report_date", ""),
                        "Week": r.get("report_week", ""),
                        "Crop": r.get("crop", ""),
                        "State": r.get("state", ""),
                        "Observation Type": r.get("observation_type", ""),
                        "Growth Stage": r.get("growth_stage", ""),
                        "Crop Operation": r.get("crop_operation", ""),
                        "Sowing Status": r.get("sowing_status", ""),
                        "Harvest Status": r.get("harvest_status", ""),
                        "Pest": r.get("pest", ""),
                        "Disease": r.get("disease", ""),
                        "Weather": r.get("weather_condition", ""),
                        "Irrigation": r.get("irrigation", ""),
                        "Nutrient Management": r.get("nutrient_management", ""),
                        "Statistics": r.get("statistics", ""),
                        "Evidence": r.get("evidence_sentence") or r.get("raw_text") or "",
                        "PDF Name": r.get("source_pdf", ""),
                        "Page": r.get("page_number", ""),
                        "Chunk ID": r.get("chunk_id", ""),
                        "Confidence": r.get("confidence", ""),
                        "Verification Status": r.get("verification_status", ""),
                        "Source Method": r.get("source_method", "")
                    })

            # 2. TIMELINE CSV
            time_fieldnames = ["Date", "Observation", "Evidence"]
            with open(timeline_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=time_fieldnames)
                writer.writeheader()
                for r in recs:
                    obs_str = []
                    if r.get("growth_stage"): obs_str.append(f"{r['growth_stage']} Stage")
                    if r.get("pest"): obs_str.append(f"{r['pest']} observed")
                    if r.get("disease"): obs_str.append(f"{r['disease']} observed")
                    if r.get("sowing_status"): obs_str.append(f"Sowing: {r['sowing_status']}")
                    if r.get("harvest_status"): obs_str.append(f"Harvest: {r['harvest_status']}")
                    if not obs_str and r.get("observation_type"): obs_str.append(r["observation_type"])
                    
                    writer.writerow({
                        "Date": r.get("report_date") or r.get("report_week", ""),
                        "Observation": " | ".join(obs_str) if obs_str else "General Observation",
                        "Evidence": r.get("chunk_id", "")
                    })

            # 3. STATISTICS CSV (Only quantitative records)
            stat_fieldnames = ["Date", "State", "Parameter", "Value", "Chunk ID"]
            with open(stat_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=stat_fieldnames)
                writer.writeheader()
                for r in recs:
                    stats_val = r.get("statistics")
                    if stats_val and str(stats_val).strip() and str(stats_val).lower() not in ["none", "none reported"]:
                        writer.writerow({
                            "Date": r.get("report_date") or r.get("report_week", ""),
                            "State": r.get("state", ""),
                            "Parameter": "Reported Statistic",
                            "Value": stats_val,
                            "Chunk ID": r.get("chunk_id", "")
                        })

            # Update index with observations count
            if crop not in index:
                # Initialize since it wasn't created by save_chunk yet
                index[crop] = {
                    "total_chunks": 0,
                    "total_observations": 0,
                    "states": 0,
                    "first_report": "",
                    "latest_report": "",
                    "last_updated": datetime.now().isoformat()
                }
            index[crop]["total_observations"] = len(recs)
            
            # Dynamically update report dates based on available records
            if recs:
                first_date = recs[0].get("report_date") or recs[0].get("report_week") or ""
                last_date = recs[-1].get("report_date") or recs[-1].get("report_week") or ""
                index[crop]["first_report"] = first_date
                index[crop]["latest_report"] = last_date
            
            # Recalculate states from DB records
            unique_states = set()
            for r in recs:
                if r.get("state") and str(r.get("state")).strip().lower() != "unknown":
                    state_val = r.get("state")
                    if isinstance(state_val, str):
                        for s in state_val.split(","):
                            s = s.strip()
                            if s:
                                unique_states.add(s)
                    elif isinstance(state_val, list):
                        for s in state_val:
                            if str(s).strip():
                                unique_states.add(str(s).strip())
            index[crop]["states"] = len(unique_states)
            
            # Recalculate total_chunks from unique chunk_ids in records
            unique_chunks = set()
            for r in recs:
                cid = r.get("chunk_id")
                if cid and str(cid).strip():
                    unique_chunks.add(str(cid).strip())
            
            total_chunks = len(unique_chunks)
            
            # Fallback to chunks directory if it exists and has more chunks (e.g. some not in DB)
            chunks_dir = crop_dir / "chunks"
            if chunks_dir.exists():
                dir_chunks = 0
                for year_dir in chunks_dir.iterdir():
                    if year_dir.is_dir():
                        dir_chunks += len(list(year_dir.glob("*.json")))
                if dir_chunks > total_chunks:
                    total_chunks = dir_chunks
            
            index[crop]["total_chunks"] = total_chunks
        
        # Remove states_set before saving index
        for crop in index:
            if "states_set" in index[crop]:
                del index[crop]["states_set"]
                
        self.save_index(index)
        logger.info("Successfully updated Crop Knowledge Repository CSVs and index.")
