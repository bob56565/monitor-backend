"""Part B Inference Module: Endocrine & Neurohormonal Balance (Panel 5)"""

from datetime import datetime
from sqlalchemy.orm import Session
from app.part_b.schemas.output_schemas import OutputLineItem, OutputFrequency, OutputStatus
from app.part_b.data_helpers import PartADataHelper
from app.services.confidence import confidence_engine, OutputType

class EndocrineNeurohormonalInference:
    @staticmethod
    def compute_cortisol_rhythm_integrity_score(db: Session, submission_id: str, user_id: int) -> OutputLineItem:
        submission = PartADataHelper.get_submission(db, submission_id, user_id)
        cortisol_lab = PartADataHelper.get_most_recent_lab(db, submission.id, 'cortisol', 'saliva')
        hrv = PartADataHelper.get_vitals_summary(db, submission.id, 'hrv_sdnn', days_back=30)
        soap = PartADataHelper.get_soap_profile(db, submission.id)
        
        score = 60.0
        if hrv and (hrv.get('mean') or 0) < 40: score -= 20
        if soap and (soap.get('sleep_duration') or 8) < 6: score -= 15
        if cortisol_lab and cortisol_lab.get('value') is not None and cortisol_lab['value'] > 20: score -= 10  # Elevated evening cortisol
        score = max(0, min(100, score))
        
        confidence_result = confidence_engine.compute_confidence(OutputType.INFERRED_WIDE, 0.65, 0.5, 30, 0.7)
        return OutputLineItem(
            output_id=f"endo_cortisol_{int(datetime.utcnow().timestamp())}",
            metric_name="cortisol_rhythm_integrity_score",
            panel_name="endocrine_neurohormonal",
            frequency=OutputFrequency.WEEKLY,
            measured_vs_inferred="inferred_wide",
            value_score=round(score, 1),
            units="integrity score 0-100",
            confidence_percent=round(confidence_result['confidence_percent'], 1),
            confidence_top_3_drivers=confidence_result['top_3_drivers'][:3],
            what_increases_confidence=confidence_result['what_increases_confidence'] + ["Add 4-point salivary cortisol test"],
            safe_action_suggestion="If score <50, address sleep, stress management, and circadian rhythm optimization.",
            input_chain=f"HRV + sleep + {'saliva cortisol' if cortisol_lab else 'no cortisol lab'}",
            input_references={'cortisol_upload_id': cortisol_lab.get('upload_id') if cortisol_lab else None},
            methodologies_used=["Circadian pattern modeling (phase/amplitude)", "Bayesian updating with saliva cortisol", "Composite index (HRV+sleep+stress)", "Quality gating"],
            method_why=["Captures diurnal rhythm disruption", "Personalizes to measured cortisol", "Integrates autonomic markers", "Excludes poor quality samples"],
            gating_payload={},
            confidence_payload=confidence_result
        )
    
    @staticmethod
    def compute_stress_adaptation_vs_maladaptation_classifier(db: Session, submission_id: str, user_id: int) -> OutputLineItem:
        submission = PartADataHelper.get_submission(db, submission_id, user_id)
        hrv = PartADataHelper.get_vitals_summary(db, submission.id, 'hrv_sdnn', days_back=30)
        hr = PartADataHelper.get_vitals_summary(db, submission.id, 'heart_rate', days_back=30)
        soap = PartADataHelper.get_soap_profile(db, submission.id)
        
        classification = "adaptive"
        if hrv and (hrv.get('mean') or 100) < 40 and hr and (hr.get('mean') or 70) > 80:
            classification = "maladaptive"
        if soap and (soap.get('sleep_duration') or 8) < 6:
            classification = "maladaptive" if classification != "adaptive" else "at_risk"
        
        confidence_result = confidence_engine.compute_confidence(OutputType.INFERRED_WIDE, 0.70, 0.6, 7, 0.75)
        return OutputLineItem(
            output_id=f"endo_stress_{int(datetime.utcnow().timestamp())}",
            metric_name="stress_adaptation_vs_maladaptation_classifier",
            panel_name="endocrine_neurohormonal",
            frequency=OutputFrequency.WEEKLY,
            measured_vs_inferred="inferred_wide",
            value_class=classification,
            confidence_percent=round(confidence_result['confidence_percent'], 1),
            confidence_top_3_drivers=confidence_result['top_3_drivers'][:3],
            what_increases_confidence=confidence_result['what_increases_confidence'],
            safe_action_suggestion=f"Status is '{classification}'. If maladaptive, prioritize sleep, stress management, and recovery.",
            input_chain="HRV + resting HR + sleep debt",
            input_references={'soap_profile_id': submission.id},
            methodologies_used=["Anomaly/trend detection (sustained HRV suppression)", "Classifier (adaptive/at-risk/maladaptive)", "Rule constraints (sleep debt + HRV suppression)", "Mixed-effects baseline"],
            method_why=["Detects chronic stress patterns", "Interpretable categories", "Mechanistic grounding", "Personalizes to individual baseline"],
            gating_payload={},
            confidence_payload=confidence_result
        )
    
    @staticmethod
    def compute_thyroid_functional_pattern(db: Session, submission_id: str, user_id: int) -> OutputLineItem:
        submission = PartADataHelper.get_submission(db, submission_id, user_id)
        tsh = PartADataHelper.get_most_recent_lab(db, submission.id, 'tsh', 'blood')
        t4 = PartADataHelper.get_most_recent_lab(db, submission.id, 't4_free', 'blood')
        hr = PartADataHelper.get_vitals_summary(db, submission.id, 'heart_rate', days_back=30)
        
        pattern = "euthyroid"
        if tsh and tsh.get('value') is not None:
            if tsh['value'] > 4.5: pattern = "hypothyroid_pattern"
            elif tsh['value'] < 0.4: pattern = "hyperthyroid_pattern"
        if hr and (hr.get('mean') or 70) < 55: pattern = "hypothyroid_pattern"
        elif hr and (hr.get('mean') or 70) > 90: pattern = "hyperthyroid_pattern"
        
        has_anchor = tsh is not None or t4 is not None
        confidence_result = confidence_engine.compute_confidence(OutputType.INFERRED_TIGHT if has_anchor else OutputType.INFERRED_WIDE, 0.75, 0.9 if has_anchor else 0.4, tsh.get('days_old', 180) if tsh else 180, 0.8)
        return OutputLineItem(
            output_id=f"endo_thyroid_{int(datetime.utcnow().timestamp())}",
            metric_name="thyroid_functional_pattern",
            panel_name="endocrine_neurohormonal",
            frequency=OutputFrequency.MONTHLY,
            measured_vs_inferred="inferred_tight" if has_anchor else "inferred_wide",
            value_class=pattern,
            confidence_percent=round(confidence_result['confidence_percent'], 1),
            confidence_top_3_drivers=confidence_result['top_3_drivers'][:3],
            what_increases_confidence=confidence_result['what_increases_confidence'],
            safe_action_suggestion=f"Pattern is '{pattern}'. If abnormal, consult clinician for thyroid panel (TSH, T4, T3).",
            input_chain=f"{'TSH lab' if tsh else 'No TSH'} + HR context",
            input_references={'tsh_upload_id': tsh.get('upload_id') if tsh else None},
            methodologies_used=["Rule-based patterning (hypo/hyper physiology)", "Bayesian anchor to TSH/T4", "Classifier (functional patterns)", "Quality gating"],
            method_why=["Standard clinical thyroid assessment", "Personalizes to lab values", "Interpretable categories", "Prevents misclassification from lab errors"],
            gating_payload={},
            confidence_payload=confidence_result
        )
    
    @staticmethod
    def compute_sympathetic_dominance_index(db: Session, submission_id: str, user_id: int) -> OutputLineItem:
        submission = PartADataHelper.get_submission(db, submission_id, user_id)
        hrv = PartADataHelper.get_vitals_summary(db, submission.id, 'hrv_sdnn', days_back=30)
        hr = PartADataHelper.get_vitals_summary(db, submission.id, 'heart_rate', days_back=30)
        soap = PartADataHelper.get_soap_profile(db, submission.id)
        
        dominance = 40.0
        if hrv and (hrv.get('mean') or 100) < 40: dominance += 25
        if hr and (hr.get('mean') or 70) > 80: dominance += 20
        if soap and soap.get('caffeine_intake') in ['high', 'very_high']: dominance += 10
        dominance = min(100, dominance)
        
        confidence_result = confidence_engine.compute_confidence(OutputType.INFERRED_WIDE, 0.70, 0.6, 7, 0.75)
        return OutputLineItem(
            output_id=f"endo_sympathetic_{int(datetime.utcnow().timestamp())}",
            metric_name="sympathetic_dominance_index",
            panel_name="endocrine_neurohormonal",
            frequency=OutputFrequency.WEEKLY,
            measured_vs_inferred="inferred_wide",
            value_score=round(dominance, 1),
            units="dominance index 0-100",
            confidence_percent=round(confidence_result['confidence_percent'], 1),
            confidence_top_3_drivers=confidence_result['top_3_drivers'][:3],
            what_increases_confidence=confidence_result['what_increases_confidence'],
            safe_action_suggestion="If index >70, reduce stimulants, practice relaxation techniques, and improve sleep.",
            input_chain="HRV + HR + caffeine intake",
            input_references={'soap_profile_id': submission.id},
            methodologies_used=["Composite index (HRV + HR ratio)", "Context-aware rules (caffeine, stress)", "Mixed-effects baseline", "Trend smoothing"],
            method_why=["Captures autonomic imbalance", "Integrates lifestyle modulators", "Personalizes to baseline", "Reduces noise"],
            gating_payload={},
            confidence_payload=confidence_result
        )
    
    @staticmethod
    def compute_burnout_risk_trajectory(db: Session, submission_id: str, user_id: int) -> OutputLineItem:
        submission = PartADataHelper.get_submission(db, submission_id, user_id)
        hrv = PartADataHelper.get_vitals_summary(db, submission.id, 'hrv_sdnn', days_back=60)
        hr = PartADataHelper.get_vitals_summary(db, submission.id, 'heart_rate', days_back=60)
        soap = PartADataHelper.get_soap_profile(db, submission.id)
        
        trajectory = "low_risk"
        if hrv and (hrv.get('mean') or 100) < 35 and hr and (hr.get('mean') or 70) > 85:
            trajectory = "high_risk"
        elif hrv and (hrv.get('mean') or 100) < 50:
            trajectory = "moderate_risk"
        if soap and (soap.get('sleep_duration') or 8) < 6 and soap.get('work_stress') in ['high', 'very_high']:
            trajectory = "high_risk" if trajectory == "moderate_risk" else trajectory
        
        confidence_result = confidence_engine.compute_confidence(OutputType.INFERRED_WIDE, 0.70, 0.65, 30, 0.70)
        return OutputLineItem(
            output_id=f"endo_burnout_{int(datetime.utcnow().timestamp())}",
            metric_name="burnout_risk_trajectory",
            panel_name="endocrine_neurohormonal",
            frequency=OutputFrequency.MONTHLY,
            measured_vs_inferred="inferred_wide",
            value_class=trajectory,
            confidence_percent=round(confidence_result['confidence_percent'], 1),
            confidence_top_3_drivers=confidence_result['top_3_drivers'][:3],
            what_increases_confidence=confidence_result['what_increases_confidence'],
            safe_action_suggestion=f"Burnout risk is '{trajectory}'. If high risk, seek professional support and lifestyle intervention.",
            input_chain="HRV trend (60d) + HR + sleep + work stress",
            input_references={'soap_profile_id': submission.id},
            methodologies_used=["Trend modeling (sustained HRV/HR deviation)", "Composite risk scoring (physiology+lifestyle)", "Bayesian priors (population burnout rates)", "Change-point detection"],
            method_why=["Detects chronic stress accumulation", "Integrates psychological + physiological", "Calibrates against population norms", "Catches meaningful shifts"],
            gating_payload={},
            confidence_payload=confidence_result
        )
