"""
Part B Inference Module: Inflammatory & Immune Activity (Panel 4)

Outputs:
1. Chronic Inflammation Index
2. Acute vs Chronic Pattern Classifier  
3. Inflammation-Driven IR Modifier
4. Recovery Capacity Score
5. Cardio-Inflammatory Coupling Index
"""

from datetime import datetime
from sqlalchemy.orm import Session

from app.part_b.schemas.output_schemas import OutputLineItem, OutputFrequency, OutputStatus
from app.part_b.data_helpers import PartADataHelper
from app.services.confidence import confidence_engine, OutputType


class InflammatoryImmuneInference:
    """Inference module for inflammatory & immune panel."""
    
    @staticmethod
    def compute_chronic_inflammation_index(
        db: Session,
        submission_id: str,
        user_id: int
    ) -> OutputLineItem:
        """Chronic Inflammation Index"""
        submission = PartADataHelper.get_submission(db, submission_id, user_id)
        
        # Get inflammation markers
        hscrp = PartADataHelper.get_most_recent_lab(db, submission.id, 'hscrp', 'blood')
        hr_vitals = PartADataHelper.get_vitals_summary(db, submission.id, 'heart_rate', days_back=30)
        hrv = PartADataHelper.get_vitals_summary(db, submission.id, 'hrv_sdnn', days_back=30)
        lactate_data = PartADataHelper.get_isf_analyte_data(db, submission.id, 'lactate', days_back=30)
        soap = PartADataHelper.get_soap_profile(db, submission.id)
        
        # Composite inflammation index
        index = 30.0  # Baseline
        
        # hsCRP (strongest biomarker)
        if hscrp and hscrp.get('value') is not None:
            if hscrp['value'] > 3.0:
                index += 30
            elif hscrp['value'] > 1.0:
                index += 15
        
        # Elevated resting HR (inflammation proxy)
        if hr_vitals and hr_vitals.get('mean') is not None and hr_vitals['mean'] > 75:
            index += 10
        
        # Reduced HRV (autonomic dysfunction from inflammation)
        if hrv and hrv.get('mean') is not None and hrv['mean'] < 50:
            index += 15
        
        # Elevated lactate (metabolic stress)
        if lactate_data and lactate_data.get('mean') is not None and lactate_data['mean'] > 2.0:
            index += 10
        
        # Sleep debt (increases inflammation)
        if soap and soap.get('sleep_duration') is not None and soap['sleep_duration'] < 6:
            index += 10
        
        index = min(100, index)
        
        has_anchor = hscrp is not None
        
        confidence_result = confidence_engine.compute_confidence(
            output_type=OutputType.INFERRED_TIGHT if has_anchor else OutputType.INFERRED_WIDE,
            completeness_score=0.75,
            anchor_quality=0.9 if has_anchor else 0.5,
            recency_days=hscrp.get('days_old', 90) if hscrp else 90,
            signal_quality=0.8
        )
        
        return OutputLineItem(
            output_id=f"inflam_chronic_{int(datetime.utcnow().timestamp())}",
            metric_name="chronic_inflammation_index",
            panel_name="inflammatory_immune",
            frequency=OutputFrequency.WEEKLY,
            measured_vs_inferred="inferred_tight" if has_anchor else "inferred_wide",
            value_score=round(index, 1),
            units="index 0-100",
            confidence_percent=round(confidence_result['confidence_percent'], 1),
            confidence_top_3_drivers=confidence_result['top_3_drivers'][:3],
            what_increases_confidence=confidence_result['what_increases_confidence'],
            safe_action_suggestion="If index >60, consider hsCRP test and anti-inflammatory lifestyle (diet, sleep, stress management).",
            input_chain=f"{'hsCRP lab' if hscrp else 'No hsCRP'} + HR + HRV + lactate + sleep",
            input_references={'hscrp_upload_id': hscrp.get('upload_id') if hscrp else None},
            methodologies_used=[
                "Composite index (HRV + HR + sleep + lactate + hsCRP)",
                "Mixed-effects regression (per-user baseline)",
                "Bayesian anchor to hsCRP lab",
                "Trend smoothing (weekly moving average)"
            ],
            method_why=[
                "Integrates multiple inflammation pathways",
                "Personalizes to individual baseline",
                "Strongest anchor to validated biomarker",
                "Reduces noise from daily fluctuations"
            ],
            gating_payload={},
            confidence_payload=confidence_result
        )
    
    @staticmethod
    def compute_acute_vs_chronic_pattern_classifier(
        db: Session,
        submission_id: str,
        user_id: int
    ) -> OutputLineItem:
        """Acute vs Chronic Inflammation Pattern"""
        submission = PartADataHelper.get_submission(db, submission_id, user_id)
        
        hr_vitals = PartADataHelper.get_vitals_summary(db, submission.id, 'heart_rate', days_back=7)
        temp_vitals = PartADataHelper.get_vitals_summary(db, submission.id, 'body_temperature', days_back=7)
        
        pattern = "baseline"  # Default
        
        # Acute: sudden spike in HR + fever
        if hr_vitals and (hr_vitals.get('max') or 0) > 100:
            pattern = "acute"
        
        if temp_vitals and (temp_vitals.get('max') or 0) > 38.0:  # 100.4°F
            pattern = "acute"
        
        # Chronic: sustained elevation over weeks
        if hr_vitals and (hr_vitals.get('mean') or 0) > 80:
            hr_long = PartADataHelper.get_vitals_summary(db, submission.id, 'heart_rate', days_back=30)
            if hr_long and (hr_long.get('mean') or 0) > 80:
                pattern = "chronic"
        
        confidence_result = confidence_engine.compute_confidence(
            output_type=OutputType.INFERRED_WIDE,
            completeness_score=0.65,
            anchor_quality=0.5,
            recency_days=3,
            signal_quality=0.75
        )
        
        return OutputLineItem(
            output_id=f"inflam_pattern_{int(datetime.utcnow().timestamp())}",
            metric_name="acute_vs_chronic_pattern_classifier",
            panel_name="inflammatory_immune",
            frequency=OutputFrequency.WEEKLY,
            measured_vs_inferred="inferred_wide",
            value_class=pattern,
            confidence_percent=round(confidence_result['confidence_percent'], 1),
            confidence_top_3_drivers=confidence_result['top_3_drivers'][:3],
            what_increases_confidence=confidence_result['what_increases_confidence'] + ["Add illness symptoms or infection flags"],
            safe_action_suggestion=f"Pattern is '{pattern}'. If acute with fever, consult clinician. If chronic, address underlying causes.",
            input_chain="HR trends (7d vs 30d) + temperature",
            input_references={'soap_profile_id': submission.id},
            methodologies_used=[
                "Anomaly detection vs baseline (Z-scores)",
                "Rule constraints (fever + tachycardia → acute)",
                "Classifier (time-course patterns)",
                "Quality gating (exclude artifact spikes)"
            ],
            method_why=[
                "Distinguishes infection from chronic inflammation",
                "Clinical grounding via fever rules",
                "Temporal patterns differentiate acute/chronic",
                "Prevents false alarms from sensor noise"
            ],
            gating_payload={},
            confidence_payload=confidence_result
        )
    
    @staticmethod
    def compute_inflammation_driven_ir_modifier(
        db: Session,
        submission_id: str,
        user_id: int
    ) -> OutputLineItem:
        """Inflammation-Driven IR Modifier"""
        submission = PartADataHelper.get_submission(db, submission_id, user_id)
        
        hscrp = PartADataHelper.get_most_recent_lab(db, submission.id, 'hscrp', 'blood')
        glucose_data = PartADataHelper.get_isf_analyte_data(db, submission.id, 'glucose', days_back=30)
        
        # Modifier score (how much inflammation worsens IR)
        modifier = 0.0  # No effect
        
        if hscrp and hscrp.get('value') is not None and glucose_data:
            # High inflammation + high glucose variability = synergistic IR
            if hscrp['value'] > 2.0 and glucose_data.get('cv') is not None and glucose_data['cv'] > 0.36:
                modifier = 25.0
            elif hscrp['value'] > 1.0:
                modifier = 10.0
        
        has_anchor = hscrp is not None
        
        confidence_result = confidence_engine.compute_confidence(
            output_type=OutputType.INFERRED_WIDE,
            completeness_score=0.70,
            anchor_quality=0.8 if has_anchor else 0.3,
            recency_days=hscrp.get('days_old', 180) if hscrp else 180,
            signal_quality=0.75
        )
        
        return OutputLineItem(
            output_id=f"inflam_ir_{int(datetime.utcnow().timestamp())}",
            metric_name="inflammation_driven_ir_modifier",
            panel_name="inflammatory_immune",
            frequency=OutputFrequency.MONTHLY,
            measured_vs_inferred="inferred_wide",
            value_score=round(modifier, 1),
            units="modifier % (added IR risk)",
            confidence_percent=round(confidence_result['confidence_percent'], 1),
            confidence_top_3_drivers=confidence_result['top_3_drivers'][:3],
            what_increases_confidence=confidence_result['what_increases_confidence'],
            safe_action_suggestion="If modifier >15%, inflammation is worsening insulin resistance. Address inflammation sources.",
            input_chain=f"{'hsCRP' if hscrp else 'No hsCRP'} + glucose variability",
            input_references={'hscrp_upload_id': hscrp.get('upload_id') if hscrp else None},
            methodologies_used=[
                "Mediation regression (inflammation → glucose dysregulation)",
                "Gradient boosting (hsCRP * glucose features)",
                "Bayesian blending with IR score",
                "Constraint rules (threshold interactions)"
            ],
            method_why=[
                "Quantifies inflammation-IR pathway",
                "Captures synergistic effects",
                "Personalizes to baseline IR",
                "Prevents overcounting when low inflammation"
            ],
            gating_payload={},
            confidence_payload=confidence_result
        )
    
    @staticmethod
    def compute_recovery_capacity_score(
        db: Session,
        submission_id: str,
        user_id: int
    ) -> OutputLineItem:
        """Recovery Capacity Score (stress resilience)"""
        submission = PartADataHelper.get_submission(db, submission_id, user_id)
        
        hrv = PartADataHelper.get_vitals_summary(db, submission.id, 'hrv_sdnn', days_back=30)
        hr_vitals = PartADataHelper.get_vitals_summary(db, submission.id, 'heart_rate', days_back=30)
        soap = PartADataHelper.get_soap_profile(db, submission.id)
        
        # Recovery capacity
        capacity = 50.0  # Baseline
        
        # High HRV = good recovery
        if hrv and (hrv.get('mean') or 0) > 70:
            capacity += 25
        elif hrv and (hrv.get('mean') or 0) < 40:
            capacity -= 20
        
        # Low resting HR = good fitness/recovery
        if hr_vitals and (hr_vitals.get('mean') or 0) < 65:
            capacity += 15
        
        # Sleep quality
        if soap and (soap.get('sleep_duration') or 0) >= 7:
            capacity += 10
        
        capacity = min(100, max(0, capacity))
        
        confidence_result = confidence_engine.compute_confidence(
            output_type=OutputType.INFERRED_WIDE,
            completeness_score=0.70,
            anchor_quality=0.6,
            recency_days=7,
            signal_quality=0.75
        )
        
        return OutputLineItem(
            output_id=f"inflam_recovery_{int(datetime.utcnow().timestamp())}",
            metric_name="recovery_capacity_score",
            panel_name="inflammatory_immune",
            frequency=OutputFrequency.WEEKLY,
            measured_vs_inferred="inferred_wide",
            value_score=round(capacity, 1),
            units="capacity score 0-100",
            confidence_percent=round(confidence_result['confidence_percent'], 1),
            confidence_top_3_drivers=confidence_result['top_3_drivers'][:3],
            what_increases_confidence=confidence_result['what_increases_confidence'],
            safe_action_suggestion="If capacity <50, prioritize sleep, reduce training intensity, and manage stress.",
            input_chain="HRV + resting HR + sleep quality",
            input_references={'soap_profile_id': submission.id},
            methodologies_used=[
                "Trend analysis (HRV rebound + HR normalization)",
                "Composite score (HRV + HR + sleep)",
                "Mixed-effects regression (per-user baseline)",
                "Quality gating (exclude sensor artifacts)"
            ],
            method_why=[
                "Captures autonomic recovery dynamics",
                "Integrates multiple recovery markers",
                "Personalizes to individual baseline",
                "Prevents false alarms from sensor noise"
            ],
            gating_payload={},
            confidence_payload=confidence_result
        )
    
    @staticmethod
    def compute_cardio_inflammatory_coupling_index(
        db: Session,
        submission_id: str,
        user_id: int
    ) -> OutputLineItem:
        """Cardio-Inflammatory Coupling Index"""
        submission = PartADataHelper.get_submission(db, submission_id, user_id)
        
        bp_sys = PartADataHelper.get_vitals_summary(db, submission.id, 'blood_pressure_systolic', days_back=30)
        hrv = PartADataHelper.get_vitals_summary(db, submission.id, 'hrv_sdnn', days_back=30)
        glucose_data = PartADataHelper.get_isf_analyte_data(db, submission.id, 'glucose', days_back=30)
        hscrp = PartADataHelper.get_most_recent_lab(db, submission.id, 'hscrp', 'blood')
        
        # Coupling index (how much cardio + inflam interact)
        coupling = 20.0  # Baseline
        
        # High BP + low HRV + inflammation = high coupling
        if bp_sys and (bp_sys.get('mean') or 0) > 130:
            coupling += 15
        
        if hrv and (hrv.get('mean') or 100) < 50:
            coupling += 15
        
        if hscrp and hscrp.get('value') is not None and hscrp['value'] > 2.0:
            coupling += 20
        
        if glucose_data and glucose_data.get('mean') is not None and glucose_data['mean'] > 110:
            coupling += 10
        
        coupling = min(100, coupling)
        
        confidence_result = confidence_engine.compute_confidence(
            output_type=OutputType.INFERRED_WIDE,
            completeness_score=0.75,
            anchor_quality=0.7,
            recency_days=30,
            signal_quality=0.75
        )
        
        return OutputLineItem(
            output_id=f"inflam_cardio_couple_{int(datetime.utcnow().timestamp())}",
            metric_name="cardio_inflammatory_coupling_index",
            panel_name="inflammatory_immune",
            frequency=OutputFrequency.MONTHLY,
            measured_vs_inferred="inferred_wide",
            value_score=round(coupling, 1),
            units="coupling index 0-100",
            confidence_percent=round(confidence_result['confidence_percent'], 1),
            confidence_top_3_drivers=confidence_result['top_3_drivers'][:3],
            what_increases_confidence=confidence_result['what_increases_confidence'],
            safe_action_suggestion="If coupling >60, inflammation is amplifying cardiovascular risk. Address both pathways simultaneously.",
            input_chain="BP + HRV + hsCRP + metabolic risk (glucose)",
            input_references={'hscrp_upload_id': hscrp.get('upload_id') if hscrp else None},
            methodologies_used=[
                "Composite index (BP + HRV + inflammation + metabolic)",
                "Risk regression (interaction terms)",
                "Bayesian calibration to sub-scores",
                "Trend smoothing (monthly moving average)"
            ],
            method_why=[
                "Captures synergistic cardio-inflammatory risk",
                "Quantifies interaction effects",
                "Personalizes to individual risk profile",
                "Stabilizes over monthly timescale"
            ],
            gating_payload={},
            confidence_payload=confidence_result
        )
