"""
A2 Processor Service

Core A2 data quality analysis processor. Computes coverage, gating, conflicts,
derived features, anchor strength, and produces the canonical A2 Summary record.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session

from app.models import (
    PartASubmission,
    SpecimenUpload,
    ISFAnalyteStream,
    VitalsRecord,
    SOAPProfileRecord,
    A2Run,
    A2Summary,
    A2Artifact,
    A2StatusEnum
)
from app.services.confidence import confidence_engine
from app.services.gating import gating_engine
from app.services.priors import priors_service

logger = logging.getLogger(__name__)


class A2Processor:
    """
    A2 Data Quality Processor.
    
    Analyzes Part A submission data and produces:
    - Stream coverage metrics
    - Gating decisions (eligible_for_part_b)
    - Conflict detection
    - Derived features
    - Anchor strength by domain
    - Canonical A2 Summary record
    """
    
    @staticmethod
    def process_submission(
        db: Session,
        a2_run_id: str,
        submission_id: str,
        user_id: int
    ) -> Dict[str, Any]:
        """
        Process A2 analysis for a Part A submission.
        
        Args:
            db: Database session
            a2_run_id: A2 run identifier
            submission_id: Part A submission ID
            user_id: User ID
            
        Returns:
            A2 summary data dictionary
            
        Raises:
            Exception: If submission not found or processing fails
        """
        logger.info(f"Starting A2 processing for submission {submission_id}")
        
        # Fetch Part A submission
        submission = db.query(PartASubmission).filter(
            PartASubmission.submission_id == submission_id,
            PartASubmission.user_id == user_id
        ).first()
        
        if not submission:
            raise ValueError(f"Submission {submission_id} not found for user {user_id}")
        
        # Compute stream coverage
        stream_coverage = A2Processor._compute_stream_coverage(db, submission, user_id)
        
        # Compute gating
        gating = A2Processor._compute_gating(db, submission, user_id, stream_coverage)
        
        # Detect conflicts
        conflict_flags = A2Processor._detect_conflicts(db, submission)
        
        # Compute derived features
        derived_features_count, derived_features_detail = A2Processor._compute_derived_features(
            db, submission
        )
        
        # Compute anchor strength by domain
        anchor_strength = A2Processor._compute_anchor_strength(db, submission, user_id)
        
        # Get priors used
        priors_used = A2Processor._get_priors_used()
        
        # Get prior decay state
        prior_decay_state = A2Processor._get_prior_decay_state()
        
        # Compute confidence distribution (optional)
        confidence_distribution = A2Processor._compute_confidence_distribution(stream_coverage)
        
        # Build canonical A2 summary
        summary_data = {
            "a2_run_id": a2_run_id,
            "submission_id": submission_id,
            "user_id": user_id,
            "stream_coverage": stream_coverage,
            "gating": gating,
            "priors_used": priors_used,
            "prior_decay_state": prior_decay_state,
            "conflict_flags": conflict_flags,
            "derived_features_count": derived_features_count,
            "derived_features_detail": derived_features_detail,
            "anchor_strength_by_domain": anchor_strength,
            "confidence_distribution": confidence_distribution,
            "schema_version": "1.0.0",
            "created_at": datetime.utcnow()
        }
        
        logger.info(f"A2 processing completed for submission {submission_id}")
        return summary_data
    
    @staticmethod
    def _compute_stream_coverage(
        db: Session,
        submission: PartASubmission,
        user_id: int
    ) -> Dict[str, Dict[str, Any]]:
        """
        Compute coverage metrics for each data stream.
        
        Returns dict with keys: glucose, lactate, vitals, sleep, pros, labs
        Each value: {days_covered, missing_rate, last_seen_ts, quality_score}
        """
        coverage = {}
        
        # ISF Glucose
        glucose_streams = db.query(ISFAnalyteStream).filter(
            ISFAnalyteStream.submission_id == submission.id,
            ISFAnalyteStream.name == "glucose"
        ).all()
        if glucose_streams:
            all_timestamps = []
            for s in glucose_streams:
                if s.timestamps_json:
                    # timestamps_json is an array of ISO strings, convert to datetime
                    from datetime import datetime
                    timestamps = [datetime.fromisoformat(ts.replace('Z', '+00:00')) for ts in s.timestamps_json]
                    all_timestamps.extend(timestamps)
            
            if all_timestamps:
                days_covered = (max(all_timestamps) - min(all_timestamps)).days + 1
                last_seen = max(all_timestamps)
                # Simple quality: completeness
                expected_readings = days_covered * 96  # 15-min intervals
                actual_readings = sum(len(s.values_json) for s in glucose_streams if s.values_json)
                quality_score = min(1.0, actual_readings / max(expected_readings, 1))
                missing_rate = 1.0 - quality_score
            else:
                days_covered = 0
                last_seen = None
                quality_score = 0.0
                missing_rate = 1.0
        else:
            days_covered = 0
            last_seen = None
            quality_score = 0.0
            missing_rate = 1.0
        
        coverage["glucose"] = {
            "days_covered": days_covered,
            "missing_rate": missing_rate,
            "last_seen_ts": last_seen.isoformat() if last_seen else None,
            "quality_score": quality_score
        }
        
        # ISF Lactate
        lactate_streams = db.query(ISFAnalyteStream).filter(
            ISFAnalyteStream.submission_id == submission.id,
            ISFAnalyteStream.name == "lactate"
        ).all()
        if lactate_streams:
            all_timestamps = []
            for s in lactate_streams:
                if s.timestamps_json:
                    from datetime import datetime
                    timestamps = [datetime.fromisoformat(ts.replace('Z', '+00:00')) for ts in s.timestamps_json]
                    all_timestamps.extend(timestamps)
            
            if all_timestamps:
                days_covered = (max(all_timestamps) - min(all_timestamps)).days + 1
                last_seen = max(all_timestamps)
                expected_readings = days_covered * 96
                actual_readings = sum(len(s.values_json) for s in lactate_streams if s.values_json)
                quality_score = min(1.0, actual_readings / max(expected_readings, 1))
                missing_rate = 1.0 - quality_score
            else:
                days_covered = 0
                last_seen = None
                quality_score = 0.0
                missing_rate = 1.0
        else:
            days_covered = 0
            last_seen = None
            quality_score = 0.0
            missing_rate = 1.0
        
        coverage["lactate"] = {
            "days_covered": days_covered,
            "missing_rate": missing_rate,
            "last_seen_ts": last_seen.isoformat() if last_seen else None,
            "quality_score": quality_score
        }
        
        # Vitals
        vitals = db.query(VitalsRecord).filter(
            VitalsRecord.submission_id == submission.id
        ).all()
        if vitals:
            # VitalsRecord doesn't have timestamp field, use created_at or skip temporal analysis
            all_timestamps = []
            for v in vitals:
                if v.created_at:
                    all_timestamps.append(v.created_at)
                # Could also extract timestamps from JSON data if present
                
            if all_timestamps:
                days_covered = (max(all_timestamps) - min(all_timestamps)).days + 1
                last_seen = max(all_timestamps)
                # Vitals: at least 1 per day is good quality
                expected_readings = days_covered
                actual_readings = len(vitals)
                quality_score = min(1.0, actual_readings / max(expected_readings, 1))
                missing_rate = max(0.0, 1.0 - quality_score)
            else:
                days_covered = 0
                last_seen = None
                quality_score = 0.0
                missing_rate = 1.0
        else:
            days_covered = 0
            last_seen = None
            quality_score = 0.0
            missing_rate = 1.0
        
        coverage["vitals"] = {
            "days_covered": days_covered,
            "missing_rate": missing_rate,
            "last_seen_ts": last_seen.isoformat() if last_seen else None,
            "quality_score": quality_score
        }
        
        # Sleep (from SOAP or vitals sleep_quality if available)
        # Simplified: check if sleep data present in payload
        has_sleep = False
        if submission.full_payload_json:
            vitals_data = submission.full_payload_json.get("vitals_data", {})
            has_sleep = bool(vitals_data.get("sleep_quality"))
        
        coverage["sleep"] = {
            "days_covered": 7 if has_sleep else 0,  # Estimate
            "missing_rate": 0.0 if has_sleep else 1.0,
            "last_seen_ts": datetime.utcnow().isoformat() if has_sleep else None,
            "quality_score": 0.7 if has_sleep else 0.0
        }
        
        # PROs (patient-reported outcomes from SOAP)
        has_pros = False
        if submission.full_payload_json:
            soap = submission.full_payload_json.get("soap_profile")
            has_pros = bool(soap)
        
        coverage["pros"] = {
            "days_covered": 1 if has_pros else 0,  # Snapshot
            "missing_rate": 0.0 if has_pros else 1.0,
            "last_seen_ts": submission.submission_timestamp.isoformat() if has_pros else None,
            "quality_score": 0.8 if has_pros else 0.0
        }
        
        # Labs (specimen uploads)
        specimens = db.query(SpecimenUpload).filter(
            SpecimenUpload.submission_id == submission.id
        ).all()
        if specimens:
            timestamps = [s.created_at for s in specimens if s.created_at]
            if timestamps:
                last_seen = max(timestamps)
                # Quality based on number and recency
                days_old = (datetime.utcnow() - last_seen).days
                quality_score = max(0.3, min(1.0, 1.0 - (days_old / 90.0)))
                missing_rate = 0.0
            else:
                last_seen = None
                quality_score = 0.0
                missing_rate = 1.0
        else:
            last_seen = None
            quality_score = 0.0
            missing_rate = 1.0
        
        coverage["labs"] = {
            "days_covered": len(specimens),  # Count as "days"
            "missing_rate": missing_rate,
            "last_seen_ts": last_seen.isoformat() if last_seen else None,
            "quality_score": quality_score
        }
        
        return coverage
    
    @staticmethod
    def _compute_gating(
        db: Session,
        submission: PartASubmission,
        user_id: int,
        stream_coverage: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Compute gating decision for Part B eligibility.
        
        Returns: {eligible_for_part_b: bool, reasons: [str]}
        """
        reasons = []
        eligible = True
        
        # Check glucose coverage (minimum 1 day for demo, 7 days ideal)
        glucose_days = stream_coverage["glucose"]["days_covered"]
        if glucose_days < 1:
            eligible = False
            reasons.append(f"Insufficient glucose monitoring ({glucose_days} days, need 1+)")
        elif glucose_days < 7:
            reasons.append(f"Limited glucose monitoring ({glucose_days} days, 7+ recommended for tighter estimates)")
            # Not blocking, just a warning
        
        # Check lab anchors
        specimens = db.query(SpecimenUpload).filter(
            SpecimenUpload.submission_id == submission.id
        ).count()
        if specimens == 0:
            reasons.append("No lab specimens uploaded (recommended for tighter estimates)")
            # Not blocking, just a warning
        
        # Check vitals
        vitals_quality = stream_coverage["vitals"]["quality_score"]
        if vitals_quality < 0.3:
            reasons.append("Limited vitals data (recommended for cardiovascular outputs)")
            # Not blocking
        
        # Check SOAP profile
        pros_quality = stream_coverage["pros"]["quality_score"]
        if pros_quality < 0.5:
            reasons.append("Incomplete clinical profile (recommended for personalization)")
            # Not blocking
        
        if eligible:
            reasons.append("All minimum data requirements met")
        
        return {
            "eligible_for_part_b": eligible,
            "reasons": reasons
        }
    
    @staticmethod
    def _detect_conflicts(db: Session, submission: PartASubmission) -> List[Dict[str, Any]]:
        """
        Detect conflicts between data sources.
        
        Returns list of conflict flags.
        """
        conflicts = []
        
        # Example: Check if ISF glucose conflicts with lab glucose
        # This is simplified; real implementation would do temporal overlap analysis
        
        return conflicts  # Empty for now
    
    @staticmethod
    def _compute_derived_features(
        db: Session,
        submission: PartASubmission
    ) -> Tuple[int, Optional[Dict[str, Any]]]:
        """
        Compute derived features (e.g., non-HDL, MAP, eGFR).
        
        Returns: (count, detail_dict)
        """
        derived = []
        
        # Example: Check if we can compute MAP from BP
        if submission.full_payload_json:
            vitals = submission.full_payload_json.get("vitals_data", {}).get("cardiovascular", {})
            systolic = vitals.get("bp_systolic")
            diastolic = vitals.get("bp_diastolic")
            if systolic and diastolic:
                # MAP = DBP + 1/3(SBP - DBP)
                map_value = diastolic[0] + (systolic[0] - diastolic[0]) / 3
                derived.append({"name": "MAP", "value": map_value, "unit": "mmHg"})
        
        detail = {"features": derived} if derived else None
        return len(derived), detail
    
    @staticmethod
    def _compute_anchor_strength(
        db: Session,
        submission: PartASubmission,
        user_id: int
    ) -> Dict[str, Dict[str, Any]]:
        """
        Compute anchor strength by clinical domain.
        
        Returns: {metabolic: {score, grade, reasons}, cardio: {...}, ...}
        """
        specimens = db.query(SpecimenUpload).filter(
            SpecimenUpload.submission_id == submission.id
        ).all()
        
        # Count analytes by domain
        metabolic_count = 0
        cardio_count = 0
        renal_count = 0
        inflammation_count = 0
        nutrition_count = 0
        other_count = 0
        
        for spec in specimens:
            if spec.parsed_data_json:
                analytes = spec.parsed_data_json.get("analytes", [])
                for a in analytes:
                    name = a.get("name", "").lower()
                    if any(x in name for x in ["glucose", "a1c", "insulin"]):
                        metabolic_count += 1
                    elif any(x in name for x in ["cholesterol", "ldl", "hdl", "triglyceride"]):
                        cardio_count += 1
                    elif any(x in name for x in ["creatinine", "egfr", "bun"]):
                        renal_count += 1
                    elif any(x in name for x in ["crp", "esr"]):
                        inflammation_count += 1
                    elif any(x in name for x in ["vitamin", "b12", "folate", "iron"]):
                        nutrition_count += 1
                    else:
                        other_count += 1
        
        def compute_domain_strength(count: int) -> Dict[str, Any]:
            if count >= 3:
                return {"score": 0.9, "grade": "A", "reasons": ["Multiple anchor points available"]}
            elif count == 2:
                return {"score": 0.7, "grade": "B", "reasons": ["Moderate anchor coverage"]}
            elif count == 1:
                return {"score": 0.5, "grade": "C", "reasons": ["Limited anchor coverage"]}
            else:
                return {"score": 0.2, "grade": "D", "reasons": ["No anchor data"]}
        
        return {
            "metabolic": compute_domain_strength(metabolic_count),
            "cardio": compute_domain_strength(cardio_count),
            "renal": compute_domain_strength(renal_count),
            "inflammation": compute_domain_strength(inflammation_count),
            "nutrition": compute_domain_strength(nutrition_count),
            "other": compute_domain_strength(other_count)
        }
    
    @staticmethod
    def _get_priors_used() -> Dict[str, Any]:
        """Get priors metadata used in A2."""
        try:
            manifest = priors_service.get_manifest()
            return {
                "source": manifest.get("source", "NHANES"),
                "version": manifest.get("version", "2017-2020"),
                "analytes_count": len(manifest.get("analytes", []))
            }
        except Exception:
            return {"source": "NHANES", "version": "2017-2020", "analytes_count": 0}
    
    @staticmethod
    def _get_prior_decay_state() -> Dict[str, Any]:
        """Get prior decay state (placeholder for now)."""
        return {
            "decay_enabled": False,
            "decay_rate": 0.0,
            "note": "Prior decay not yet implemented"
        }
    
    @staticmethod
    def _compute_confidence_distribution(stream_coverage: Dict[str, Dict[str, Any]]) -> Dict[str, int]:
        """
        Compute confidence grade distribution estimate.
        
        Returns: {A: count, B: count, C: count, D: count}
        """
        # Simplified: base on overall data completeness
        scores = [stream_coverage[k]["quality_score"] for k in stream_coverage]
        avg_quality = sum(scores) / len(scores) if scores else 0.0
        
        if avg_quality >= 0.8:
            return {"A": 70, "B": 25, "C": 5, "D": 0}
        elif avg_quality >= 0.6:
            return {"A": 50, "B": 40, "C": 10, "D": 0}
        elif avg_quality >= 0.4:
            return {"A": 30, "B": 50, "C": 15, "D": 5}
        else:
            return {"A": 10, "B": 30, "C": 40, "D": 20}


# Singleton instance
a2_processor = A2Processor()
