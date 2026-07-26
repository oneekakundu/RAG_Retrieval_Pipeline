import json
from pathlib import Path
from typing import Dict, List, Any
import sys

# Ensure config is importable
sys.path.append(str(Path(__file__).resolve().parent))
import config

class SearchEngine:
    """
    Search Engine specifically for the Crop Knowledge Repository.
    Searches ONLY the validated observations and evidence chunks.
    """
    def __init__(self):
        self.knowledge_dir = config.CROP_KNOWLEDGE_DIR

    def get_crop_index(self) -> Dict[str, Any]:
        index_file = self.knowledge_dir / "crop_index.json"
        if index_file.exists():
            with open(index_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def get_chunk(self, crop: str, chunk_id: str) -> Dict[str, Any]:
        """Retrieve original chunk exactly as extracted."""
        # Query database first
        try:
            from database.sqlite_manager import SQLiteManager
            db = SQLiteManager()
            conn = db._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM crop_records WHERE chunk_id = ? LIMIT 1", (chunk_id,))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                row = dict(row)
                return {
                    "pdf_name": row["source_pdf"],
                    "page": row["page_number"],
                    "report_date": row["report_date"],
                    "chunk_type": row.get("observation_type", "Narrative") if "observation_type" in row.keys() else "Narrative",
                    "section": row.get("section_heading", "General Observation") if "section_heading" in row.keys() else "General Observation",
                    "processed_timestamp": row.get("created_at", ""),
                    "chunk_text": row.get("evidence_sentence") or row.get("raw_text") or "No text available"
                }
        except Exception as e:
            print(f"Error querying db for chunk: {e}")
            
        crop_dir = self.knowledge_dir / crop / "chunks"
        if not crop_dir.exists():
            return {}
        
        # Traverse years to find the chunk_id
        for year_dir in crop_dir.iterdir():
            if year_dir.is_dir():
                chunk_file = year_dir / f"{chunk_id}.json"
                if chunk_file.exists():
                    with open(chunk_file, "r", encoding="utf-8") as f:
                        return json.load(f)
        return {}

    def search_observations(self, 
                            crop: str = None, 
                            state: str = None, 
                            keyword: str = None, 
                            growth_stage: str = None, 
                            pest: str = None, 
                            disease: str = None) -> List[Dict[str, Any]]:
        """
        Searches the JSON exports from Crop Knowledge Base (which contain validated observations).
        Returns matching observation records.
        """
        results = []
        
        if crop:
            crops_to_search = [crop]
        else:
            crops_to_search = list(self.get_crop_index().keys())

        for c in crops_to_search:
            crop_dir = self.knowledge_dir / c
            if not crop_dir.exists():
                continue
                
            for year_file in crop_dir.glob("*.json"):
                if year_file.name in ["crop_index.json", "metadata.json", "knowledge_summary.json"]:
                    continue
                    
                with open(year_file, "r", encoding="utf-8") as f:
                    try:
                        data = json.load(f)
                        obs_list = data.get("observations", [])
                        
                        for obs in obs_list:
                            match = True
                            if state and state.lower() not in obs.get("state", "").lower():
                                match = False
                            if growth_stage and growth_stage.lower() not in obs.get("growth_stage", "").lower():
                                match = False
                            if pest and pest.lower() not in obs.get("pest", "").lower():
                                match = False
                            if disease and disease.lower() not in obs.get("disease", "").lower():
                                match = False
                                
                            if match and keyword:
                                keyword_lower = keyword.lower()
                                text_to_search = " ".join([
                                    str(obs.get(k, "")) for k in ["state", "district", "growth_stage", "pest", "disease", "weather_condition", "crop_operation", "evidence", "narrative", "original_text"]
                                ]).lower()
                                if keyword_lower not in text_to_search:
                                    match = False
                                    
                            if match:
                                # Inject original chunk to the observation dict for UI convenience
                                chunk_id = obs.get("provenance", {}).get("chunk_id", "")
                                if not chunk_id:
                                    # Fallback to id mapping if available or rely on DB later
                                    chunk_id = f"chunk_{obs.get('id')}" 
                                obs["crop"] = c
                                results.append(obs)
                    except Exception:
                        pass
                        
        # Sort results chronologically
        results.sort(key=lambda x: x.get("date", ""), reverse=True)
        return results
