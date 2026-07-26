import csv
import json
import logging
from pathlib import Path
from typing import List, Dict, Any

import config
from database.sqlite_manager import SQLiteManager

logger = logging.getLogger("Evaluation")

class Evaluator:
    """
    Evaluation Module for Crop Calendar Extraction Pipeline.
    Calculates Precision, Recall, F1, Duplicate Rate, Invalid Entity Rate,
    Missing Field Statistics, and Extraction Method Breakdown.
    """

    def __init__(self, db: SQLiteManager = None):
        self.db = db or SQLiteManager()

    def evaluate(self) -> Dict[str, Any]:
        """Runs pipeline evaluation against current database records."""
        records = self.db.load_all_records()
        total_records = len(records)

        if total_records == 0:
            logger.warning("No records found in database for evaluation.")
            return {"total_records": 0}

        # 1. Extraction Method Statistics
        method_counts = {}
        missing_counts = {
            "crop": 0, "state": 0, "growth_stage": 0, 
            "pest_or_disease": 0
        }
        invalid_entities = 0
        valid_records_count = 0

        for r in records:
            method = r.get("source_method", "rule_based")
            method_counts[method] = method_counts.get(method, 0) + 1

            # Missing field statistics
            for field in missing_counts.keys():
                val = r.get(field)
                if not val or str(val).strip().lower() in ["none", "null", "none reported", "unknown", "state-wide", "all india"]:
                    missing_counts[field] += 1

            # Invalid entity check
            crop = r.get("crop", "")
            state = r.get("state", "")
            if crop in ["GENERAL", "UNKNOWN"] or not crop:
                invalid_entities += 1
            else:
                valid_records_count += 1

        # 2. Precision, Recall, F1 Approximation
        # Precision = valid_records / total_extracted
        precision = round(valid_records_count / total_records, 4) if total_records > 0 else 0.0
        # Recall estimation based on non-empty crop-state pairs vs total chunks
        recall = round(valid_records_count / (valid_records_count + missing_counts["crop"]), 4) if (valid_records_count + missing_counts["crop"]) > 0 else 1.0
        f1 = round(2 * (precision * recall) / (precision + recall), 4) if (precision + recall) > 0 else 0.0

        invalid_rate = round(invalid_entities / total_records, 4) if total_records > 0 else 0.0

        # Duplicate Rate check
        from extractor.duplicate_detector import DuplicateDetector
        detector = DuplicateDetector()
        _, dup_count = detector.filter_duplicates(records)
        dup_rate = round(dup_count / total_records, 4) if total_records > 0 else 0.0

        # Gold Standard Evaluation Benchmark
        gold_metrics = {}
        try:
            import sys
            import os
            sys.path.append(os.path.dirname(__file__))
            from gold_standard_eval import GoldStandardEvaluator
            gs_evaluator = GoldStandardEvaluator(db=self.db)
            gold_metrics = gs_evaluator.evaluate()
        except Exception as e:
            logger.warning(f"Gold Standard Evaluation failed: {e}")

        metrics = {
            "total_records": total_records,
            "precision": gold_metrics.get("precision", precision),
            "recall": gold_metrics.get("recall", recall),
            "f1_score": gold_metrics.get("f1_score", f1),
            "heuristic_precision": precision,
            "heuristic_recall": recall,
            "duplicate_rate": dup_rate,
            "invalid_entity_rate": invalid_rate,
            "method_breakdown": method_counts,
            "gold_standard_report": gold_metrics,
            "missing_field_stats": {
                field: round(count / total_records, 4) for field, count in missing_counts.items()
            }
        }

        # Export metrics to CSV
        self.export_metrics_csv(metrics)
        return metrics

    def export_metrics_csv(self, metrics: Dict[str, Any]):
        """Export metrics to data/evaluation_metrics.csv."""
        csv_path = config.DATA_DIR / "evaluation_metrics.csv"
        proc_csv_path = config.PROCESSED_DIR / "evaluation_metrics.csv"
        try:
            for p in [csv_path, proc_csv_path]:
                with open(p, "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow(["Metric", "Value"])
                    writer.writerow(["Total Records", metrics.get("total_records", 0)])
                    writer.writerow(["Precision", metrics.get("precision", 0.0)])
                    writer.writerow(["Recall", metrics.get("recall", 0.0)])
                    writer.writerow(["F1 Score", metrics.get("f1_score", 0.0)])
                    writer.writerow(["Duplicate Rate", metrics.get("duplicate_rate", 0.0)])
                    writer.writerow(["Invalid Entity Rate", metrics.get("invalid_entity_rate", 0.0)])
                    writer.writerow(["Method Breakdown", json.dumps(metrics.get("method_breakdown", {}))])
                    writer.writerow(["Missing Field Rates", json.dumps(metrics.get("missing_field_stats", {}))])
            logger.info(f"Exported evaluation metrics to {csv_path} and {proc_csv_path}")
        except Exception as e:
            logger.error(f"Failed to export evaluation metrics: {e}")

if __name__ == "__main__":
    evaluator = Evaluator()
    results = evaluator.evaluate()
    print("Evaluation Results:", json.dumps(results, indent=2))
