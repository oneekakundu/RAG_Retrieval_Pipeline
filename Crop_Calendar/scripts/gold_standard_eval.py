import csv
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple

import config
from database.sqlite_manager import SQLiteManager

logger = logging.getLogger("GoldStandardEvaluator")

class GoldStandardEvaluator:
    """
    Performs Gold Standard Evaluation comparing extracted pipeline observations 
    against a human-verified ground-truth dataset for a representative CWWG report.
    Calculates True Positives (TP), False Positives (FP), False Negatives (FN), 
    Precision, Recall, and F1-Score.
    """

    def __init__(self, ground_truth_path: Path = None, db: SQLiteManager = None):
        self.ground_truth_path = ground_truth_path or (config.DATA_DIR / "gold_standard_ground_truth.csv")
        self.db = db or SQLiteManager()

    def load_ground_truth(self) -> List[Dict[str, str]]:
        """Load ground truth expected observations from CSV."""
        expected = []
        if not self.ground_truth_path.exists():
            logger.error(f"Ground truth CSV not found at {self.ground_truth_path}")
            return []

        with open(self.ground_truth_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                expected.append({
                    "crop": row.get("Expected Crop", "").strip(),
                    "state": row.get("Expected State", "").strip(),
                    "growth_stage": row.get("Expected Stage", "").strip(),
                    "pest": None if row.get("Expected Pest", "-").strip() in ["-", "None", ""] else row.get("Expected Pest").strip(),
                    "disease": None if row.get("Expected Disease", "-").strip() in ["-", "None", ""] else row.get("Expected Disease").strip()
                })
        return expected

    def evaluate(self, target_pdf: str = "Minutes of the meeting of CWWG as on 13.04.2026.pdf") -> Dict[str, Any]:
        """
        Evaluate extracted records for target PDF against ground truth expectations.
        """
        ground_truth = self.load_ground_truth()
        if not ground_truth:
            return {"error": "Ground truth dataset empty or missing"}

        all_records = self.db.load_all_records()
        extracted_for_pdf = [r for r in all_records if r.get("source_pdf") == target_pdf]

        if not extracted_for_pdf:
            # Fallback: query any records matching date '2026-04-13'
            extracted_for_pdf = [r for r in all_records if r.get("report_date") == "2026-04-13"]

        true_positives = 0
        false_positives = 0
        matched_gt = set()
        matched_ext = set()

        # Match extracted records against ground truth by (crop, state)
        for ext_idx, ext in enumerate(extracted_for_pdf):
            ext_crop = ext.get("crop", "").lower()
            ext_state = ext.get("state", "").lower()

            found_match = False
            for gt_idx, gt in enumerate(ground_truth):
                if gt_idx in matched_gt:
                    continue
                
                gt_crop = gt["crop"].lower()
                gt_state = gt["state"].lower()

                # Match crop and state
                if (gt_crop in ext_crop or ext_crop in gt_crop) and (gt_state in ext_state or ext_state in gt_state):
                    true_positives += 1
                    matched_gt.add(gt_idx)
                    matched_ext.add(ext_idx)
                    found_match = True
                    break
            
            if not found_match:
                false_positives += 1

        false_negatives = len(ground_truth) - len(matched_gt)

        precision = round(true_positives / (true_positives + false_positives), 4) if (true_positives + false_positives) > 0 else 0.0
        recall = round(true_positives / (true_positives + false_negatives), 4) if (true_positives + false_negatives) > 0 else 0.0
        f1_score = round(2 * (precision * recall) / (precision + recall), 4) if (precision + recall) > 0 else 0.0

        missed_observations = [ground_truth[i] for i in range(len(ground_truth)) if i not in matched_gt]

        report = {
            "target_pdf": target_pdf,
            "total_ground_truth": len(ground_truth),
            "total_extracted": len(extracted_for_pdf),
            "true_positives": true_positives,
            "false_positives": false_positives,
            "false_negatives": false_negatives,
            "precision": precision,
            "recall": recall,
            "f1_score": f1_score,
            "missed_observations": missed_observations
        }

        # Export report to JSON and CSV
        out_json = config.DATA_DIR / "gold_standard_report.json"
        with open(out_json, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        logger.info(f"Gold Standard Evaluation complete. Results saved to {out_json}")
        return report

if __name__ == "__main__":
    evaluator = GoldStandardEvaluator()
    res = evaluator.evaluate()
    print("\n--- GOLD STANDARD EVALUATION REPORT ---")
    print(json.dumps(res, indent=2))
