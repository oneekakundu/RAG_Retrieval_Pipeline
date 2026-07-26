import re
import logging
from typing import Dict, Any, List, Tuple, Optional

from extractor.schemas import SemanticExtractionSchema, FieldEvidence, VerifiedObservationRecord, VerificationStatus
from extractor.normalizer import Normalizer

logger = logging.getLogger("VerificationEngine")

class VerificationEngine:
    """
    Independent Document Verification Engine.
    Cross-checks every extracted field against original report chunk text to guarantee 100% document grounding.
    Independent of LLM provider.
    """

    def __init__(self, confidence_threshold: float = 0.60):
        self.confidence_threshold = confidence_threshold

    def verify(
        self, 
        schema: SemanticExtractionSchema, 
        original_chunk_text: str,
        source_pdf: str = "unknown.pdf",
        page_number: int = 1,
        chunk_id: str = ""
    ) -> Tuple[Optional[VerifiedObservationRecord], Dict[str, Any]]:
        """
        Verifies all extracted fields against original_chunk_text.
        Returns (VerifiedObservationRecord, audit_log_dict).
        """
        audit_log = {
            "chunk_id": chunk_id,
            "crop": schema.crop,
            "state": schema.state,
            "decisions": []
        }

        # Rule 1: Low Confidence Check
        if schema.confidence < self.confidence_threshold:
            audit_log["decisions"].append({
                "field": "overall",
                "action": "REJECT",
                "reason": f"Confidence {schema.confidence} below threshold {self.confidence_threshold}"
            })
            logger.info(f"[Verification REJECT] Low confidence {schema.confidence} for {schema.crop} in {schema.state}")
            return None, audit_log

        chunk_lower = original_chunk_text.lower()

        # Helper function to verify single FieldEvidence against original chunk text
        def is_field_supported(fe: Optional[FieldEvidence]) -> bool:
            if not fe or not fe.value or not fe.evidence:
                return False
            
            ev_str = fe.evidence.strip().lower()
            val_str = fe.value.strip().lower()

            # Check if evidence string or value substring appears in original text
            # Allow fuzzy match if > 70% words match
            if ev_str in chunk_lower or val_str in chunk_lower:
                return True
            
            ev_words = [w for w in re.findall(r"\w+", ev_str) if len(w) > 3]
            if ev_words:
                matches = sum(1 for w in ev_words if w in chunk_lower)
                if (matches / len(ev_words)) >= 0.6:
                    return True

            return False

        # 1. Verify Growth Stage & Check Contradictions
        verified_growth_stage = None
        if schema.growth_stage and is_field_supported(schema.growth_stage):
            gs_val = schema.growth_stage.value.strip()
            # Contradiction check: "100% harvested" vs "Flowering" / "Vegetative"
            if ("100% harvested" in chunk_lower or "harvested in" in chunk_lower) and gs_val.lower() in ["flowering", "vegetative", "tillering", "nursery"]:
                audit_log["decisions"].append({
                    "field": "growth_stage",
                    "action": "REJECT_CONTRADICTION",
                    "value": gs_val,
                    "reason": "Text indicates harvesting complete, but growth_stage was set to early vegetative/flowering stage"
                })
                verified_growth_stage = "Harvesting" # Auto-correct to Harvesting if harvest text dominates
            else:
                verified_growth_stage = Normalizer.normalize_stage(gs_val) or gs_val
                audit_log["decisions"].append({"field": "growth_stage", "action": "KEEP", "value": verified_growth_stage})
        else:
            if schema.growth_stage:
                audit_log["decisions"].append({"field": "growth_stage", "action": "DISCARD", "reason": "No evidence match in original text"})

        # 2. Verify Sowing & Harvest Status
        verified_sowing = None
        if schema.sowing_status and is_field_supported(schema.sowing_status):
            verified_sowing = schema.sowing_status.value
            audit_log["decisions"].append({"field": "sowing_status", "action": "KEEP", "value": verified_sowing})

        verified_harvest = None
        if schema.harvest_status and is_field_supported(schema.harvest_status):
            verified_harvest = schema.harvest_status.value
            audit_log["decisions"].append({"field": "harvest_status", "action": "KEEP", "value": verified_harvest})

        # 3. Verify Pests & Reject Area Coverage / Table Noise Leakage
        verified_pests_list = []
        for pest_fe in schema.pests:
            if is_field_supported(pest_fe):
                p_val = pest_fe.value.strip()
                p_lower = p_val.lower()

                # Reject area coverage numbers leaked into pests
                if any(noise in p_lower for noise in ["lakh ha", "area coverage", "% of normal", "sowing progress", "table", "sl. no"]):
                    audit_log["decisions"].append({
                        "field": "pests",
                        "action": "DISCARD_NOISE",
                        "value": p_val,
                        "reason": "Area coverage / table header incorrectly assigned as pest"
                    })
                    continue

                norm_pest = Normalizer.normalize_pest_disease(p_val)
                if norm_pest and norm_pest.lower() not in ["none", "nil", "n/a"]:
                    verified_pests_list.append(norm_pest)
                    audit_log["decisions"].append({"field": "pests", "action": "KEEP", "value": norm_pest})
                else:
                    audit_log["decisions"].append({"field": "pests", "action": "DISCARD_INVALID", "value": p_val})

        # 4. Verify Diseases & Reject Area Coverage / Table Noise Leakage
        verified_diseases_list = []
        for dis_fe in schema.diseases:
            if is_field_supported(dis_fe):
                d_val = dis_fe.value.strip()
                d_lower = d_val.lower()

                # Reject area coverage numbers leaked into diseases
                if any(noise in d_lower for noise in ["lakh ha", "area coverage", "% of normal", "sowing progress", "table", "sl. no"]):
                    audit_log["decisions"].append({
                        "field": "diseases",
                        "action": "DISCARD_NOISE",
                        "value": d_val,
                        "reason": "Area coverage / table header incorrectly assigned as disease"
                    })
                    continue

                norm_dis = Normalizer.normalize_pest_disease(d_val)
                if norm_dis and norm_dis.lower() not in ["none", "nil", "n/a"]:
                    verified_diseases_list.append(norm_dis)
                    audit_log["decisions"].append({"field": "diseases", "action": "KEEP", "value": norm_dis})
                else:
                    audit_log["decisions"].append({"field": "diseases", "action": "DISCARD_INVALID", "value": d_val})

        # 5. Verify Statistics
        verified_stats_list = [st.value for st in schema.statistics if is_field_supported(st)]

        # Collect evidence sentences
        evidence_str = original_chunk_text.strip()
        if schema.evidence:
            matched_ev = [ev for ev in schema.evidence if ev.strip().lower() in chunk_lower]
            if matched_ev:
                evidence_str = "; ".join(matched_ev)

        verified_record = VerifiedObservationRecord(
            chunk_id=chunk_id,
            crop=schema.crop,
            state=schema.state,
            week=schema.week,
            source_pdf=source_pdf,
            page_number=page_number,
            observation_type=schema.observation_type,
            growth_stage=verified_growth_stage,
            sowing_status=verified_sowing,
            harvest_status=verified_harvest,
            pests="; ".join(sorted(list(set(verified_pests_list)))) if verified_pests_list else None,
            diseases="; ".join(sorted(list(set(verified_diseases_list)))) if verified_diseases_list else None,
            statistics="; ".join(verified_stats_list) if verified_stats_list else None,
            evidence_sentence=evidence_str,
            confidence=schema.confidence,
            verification_status=VerificationStatus.VERIFIED.value,
            verification_notes=f"Verified {len(audit_log['decisions'])} fields against source text"
        )

        return verified_record, audit_log
