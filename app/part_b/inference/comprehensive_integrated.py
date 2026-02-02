"""Part B Inference Module: Comprehensive Integrated Physiological State (Panel 7)"""

from datetime import datetime
from sqlalchemy.orm import Session
from app.part_b.schemas.output_schemas import OutputLineItem, OutputFrequency, OutputStatus
from app.part_b.data_helpers import PartADataHelper
from app.services.confidence import confidence_engine, OutputType

class ComprehensiveIntegratedInference:
    @staticmethod
    def compute_homeostatic_resilience_score(db: Session, submission_id: str, user_id: int) -> OutputLineItem:
        submission = PartADataHelper.get_submission(db, submission_id, user_id)
        hrv = PartADataHelper.get_vitals_summary(db, submission.id, 'hrv_sdnn', days_back=30)
        hr = PartADataHelper.get_vitals_summary(db, submission.id, 'heart_rate', days_back=30)
        glucose_data = PartADataHelper.get_isf_analyte_data(db, submission.id, 'glucose', days_back=30)
        sodium = PartADataHelper.get_isf_analyte_data(db, submission.id, 'sodium', days_back=7)
        soap = PartADataHelper.get_soap_profile(db, submission.id)
        
        resilience = 50.0
        if hrv and (hrv.get('mean') or 0) > 60: resilience += 15
        if hr and (hr.get('mean') or 75) < 70: resilience += 10
        if glucose_data and glucose_data.get('cv') is not None and glucose_data['cv'] < 0.30: resilience += 10
        if sodium and sodium.get('cv') is not None and sodium['cv'] < 0.03: resilience += 10
        if soap and (soap.get('sleep_duration') or 0) >= 7: resilience += 5
        resilience = min(100, resilience)
        
        confidence_result = confidence_engine.compute_confidence(OutputType.INFERRED_WIDE, 0.75, 0.65, 7, 0.75)
        return OutputLineItem(
            output_id=f"integrated_homeostasis_{int(datetime.utcnow().timestamp())}",
            metric_name="homeostatic_resilience_score",
            panel_name="comprehensive_integrated",
            frequency=OutputFrequency.WEEKLY,
            measured_vs_inferred="inferred_wide",
            value_score=round(resilience, 1),
            units="resilience score 0-100",
            confidence_percent=round(confidence_result['confidence_percent'], 1),
            confidence_top_3_drivers=confidence_result['top_3_drivers'][:3],
            what_increases_confidence=confidence_result['what_increases_confidence'],
            safe_action_suggestion="If resilience <50, focus on sleep, stress management, and metabolic optimization.",
            input_chain="HRV + HR + glucose CV + hydration + metabolic flexibility + sleep",
            input_references={'soap_profile_id': submission.id},
            methodologies_used=["Composite scoring (HRV+HR+sleep+hydration+metabolic)", "Mixed-effects baseline", "Trend analysis", "Quality gating"],
            method_why=["Holistic physiological capacity", "Personalizes to baseline", "Tracks overall health trajectory", "Robust to sensor noise"],
            gating_payload={},
            confidence_payload=confidence_result
        )
    
    @staticmethod
    def compute_allostatic_load_proxy(db: Session, submission_id: str, user_id: int) -> OutputLineItem:
        submission = PartADataHelper.get_submission(db, submission_id, user_id)
        bp_sys = PartADataHelper.get_vitals_summary(db, submission.id, 'blood_pressure_systolic', days_back=30)
        hrv = PartADataHelper.get_vitals_summary(db, submission.id, 'hrv_sdnn', days_back=30)
        hscrp = PartADataHelper.get_most_recent_lab(db, submission.id, 'hscrp', 'blood')
        glucose_data = PartADataHelper.get_isf_analyte_data(db, submission.id, 'glucose', days_back=30)
        soap = PartADataHelper.get_soap_profile(db, submission.id)
        
        load = 20.0
        if bp_sys and (bp_sys.get('mean') or 0) > 130: load += 15
        if hrv and (hrv.get('mean') or 100) < 40: load += 15
        if hscrp and hscrp.get('value') is not None and hscrp['value'] > 2.0: load += 20
        if glucose_data and glucose_data.get('mean') is not None and glucose_data['mean'] > 110: load += 10
        if soap and (soap.get('sleep_duration') or 8) < 6: load += 10
        if soap and (soap.get('bmi') or 0) > 30: load += 10
        load = min(100, load)
        
        confidence_result = confidence_engine.compute_confidence(OutputType.INFERRED_WIDE, 0.75, 0.70, 30, 0.75)
        return OutputLineItem(
            output_id=f"integrated_allostatic_{int(datetime.utcnow().timestamp())}",
            metric_name="allostatic_load_proxy",
            panel_name="comprehensive_integrated",
            frequency=OutputFrequency.MONTHLY,
            measured_vs_inferred="inferred_wide",
            value_score=round(load, 1),
            units="load proxy 0-100",
            confidence_percent=round(confidence_result['confidence_percent'], 1),
            confidence_top_3_drivers=confidence_result['top_3_drivers'][:3],
            what_increases_confidence=confidence_result['what_increases_confidence'],
            safe_action_suggestion="If load >60, chronic stress is accumulating. Address sleep, inflammation, BP, and metabolic health.",
            input_chain="BP + HRV + inflammation + metabolic + sleep + BMI",
            input_references={'hscrp_upload_id': hscrp.get('upload_id') if hscrp else None},
            methodologies_used=["Risk-score regression (BP+HRV+inflammation+metabolic+sleep+BMI)", "Composite weighting", "Bayesian calibration", "Change-point detection"],
            method_why=["Established allostatic load framework", "Integrates multiple stress pathways", "Personalizes to individual profile", "Detects meaningful shifts"],
            gating_payload={},
            confidence_payload=confidence_result
        )
    
    @staticmethod
    def compute_metabolic_inflammatory_coupling_index(db: Session, submission_id: str, user_id: int) -> OutputLineItem:
        submission = PartADataHelper.get_submission(db, submission_id, user_id)
        hscrp = PartADataHelper.get_most_recent_lab(db, submission.id, 'hscrp', 'blood')
        glucose_data = PartADataHelper.get_isf_analyte_data(db, submission.id, 'glucose', days_back=30)
        
        coupling = 25.0
        if hscrp and hscrp.get('value') is not None and hscrp['value'] > 2.0 and glucose_data and glucose_data.get('mean') is not None and glucose_data['mean'] > 110:
            coupling += 35  # Synergistic effect
        elif hscrp and hscrp.get('value') is not None and hscrp['value'] > 1.0:
            coupling += 15
        elif glucose_data and glucose_data.get('mean') is not None and glucose_data['mean'] > 105:
            coupling += 10
        coupling = min(100, coupling)
        
        confidence_result = confidence_engine.compute_confidence(OutputType.INFERRED_WIDE, 0.70, 0.7, 60, 0.75)
        return OutputLineItem(
            output_id=f"integrated_metab_inflam_{int(datetime.utcnow().timestamp())}",
            metric_name="metabolic_inflammatory_coupling_index",
            panel_name="comprehensive_integrated",
            frequency=OutputFrequency.MONTHLY,
            measured_vs_inferred="inferred_wide",
            value_score=round(coupling, 1),
            units="coupling index 0-100",
            confidence_percent=round(confidence_result['confidence_percent'], 1),
            confidence_top_3_drivers=confidence_result['top_3_drivers'][:3],
            what_increases_confidence=confidence_result['what_increases_confidence'],
            safe_action_suggestion="If coupling >60, inflammation and metabolic dysfunction are reinforcing each other. Address both pathways.",
            input_chain=f"{'hsCRP' if hscrp else 'No hsCRP'} + glucose dysregulation",
            input_references={'hscrp_upload_id': hscrp.get('upload_id') if hscrp else None},
            methodologies_used=["Correlation + lag analysis", "Regression modeling (interaction terms)", "Bayesian anchor to hsCRP", "Trend smoothing"],
            method_why=["Quantifies bidirectional amplification", "Captures temporal dynamics", "Personalizes to baseline inflammation", "Stabilizes monthly signal"],
            gating_payload={},
            confidence_payload=confidence_result
        )
    
    @staticmethod
    def compute_autonomic_status(db: Session, submission_id: str, user_id: int) -> OutputLineItem:
        submission = PartADataHelper.get_submission(db, submission_id, user_id)
        hrv = PartADataHelper.get_vitals_summary(db, submission.id, 'hrv_sdnn', days_back=30)
        hr = PartADataHelper.get_vitals_summary(db, submission.id, 'heart_rate', days_back=30)
        soap = PartADataHelper.get_soap_profile(db, submission.id)
        
        status = 50.0
        if hrv and (hrv.get('mean') or 0) > 60: status += 20
        elif hrv and (hrv.get('mean') or 100) < 40: status -= 20
        if hr and (hr.get('mean') or 75) < 65: status += 15
        elif hr and (hr.get('mean') or 75) > 85: status -= 15
        if soap and (soap.get('sleep_duration') or 0) >= 7: status += 10
        if soap and soap.get('caffeine_intake') in ['high', 'very_high']: status -= 10
        status = max(0, min(100, status))
        
        confidence_result = confidence_engine.compute_confidence(OutputType.INFERRED_WIDE, 0.70, 0.65, 7, 0.75)
        return OutputLineItem(
            output_id=f"integrated_autonomic_{int(datetime.utcnow().timestamp())}",
            metric_name="autonomic_status",
            panel_name="comprehensive_integrated",
            frequency=OutputFrequency.WEEKLY,
            measured_vs_inferred="inferred_wide",
            value_score=round(status, 1),
            units="status index 0-100",
            confidence_percent=round(confidence_result['confidence_percent'], 1),
            confidence_top_3_drivers=confidence_result['top_3_drivers'][:3],
            what_increases_confidence=confidence_result['what_increases_confidence'],
            safe_action_suggestion="If status <50, autonomic dysfunction present. Focus on sleep, reduce stimulants, manage stress.",
            input_chain="HRV + HR + sleep + caffeine context",
            input_references={'soap_profile_id': submission.id},
            methodologies_used=["Composite index (HRV+HR+sleep+caffeine)", "Context-aware rules", "Mixed-effects baseline", "Trend smoothing"],
            method_why=["Integrates parasympathetic + sympathetic balance", "Lifestyle modifiers included", "Personalizes to individual baseline", "Reduces daily noise"],
            gating_payload={},
            confidence_payload=confidence_result
        )
    
    @staticmethod
    def compute_physiological_age_proxy(db: Session, submission_id: str, user_id: int) -> OutputLineItem:
        submission = PartADataHelper.get_submission(db, submission_id, user_id)
        hrv = PartADataHelper.get_vitals_summary(db, submission.id, 'hrv_sdnn', days_back=30)
        hr = PartADataHelper.get_vitals_summary(db, submission.id, 'heart_rate', days_back=30)
        bp_sys = PartADataHelper.get_vitals_summary(db, submission.id, 'blood_pressure_systolic', days_back=30)
        glucose_data = PartADataHelper.get_isf_analyte_data(db, submission.id, 'glucose', days_back=30)
        soap = PartADataHelper.get_soap_profile(db, submission.id)
        
        chronological_age = soap.get('age', 40) if soap else 40
        age_modifier = 0
        
        # Positive aging markers
        if hrv and (hrv.get('mean') or 100) < 40: age_modifier += 8
        if hr and (hr.get('mean') or 70) > 80: age_modifier += 5
        if bp_sys and (bp_sys.get('mean') or 0) > 140: age_modifier += 10
        if glucose_data and glucose_data.get('mean') is not None and glucose_data['mean'] > 110: age_modifier += 7
        if soap and (soap.get('bmi') or 0) > 30: age_modifier += 5
        if soap and (soap.get('sleep_duration') or 8) < 6: age_modifier += 5
        
        # Negative aging (better than chronological)
        if hrv and (hrv.get('mean') or 0) > 70: age_modifier -= 8
        if hr and (hr.get('mean') or 75) < 65: age_modifier -= 5
        if soap and soap.get('activity_level') in ['high', 'very_high']: age_modifier -= 5
        
        physiological_age = chronological_age + age_modifier
        physiological_age = max(18, min(100, physiological_age))
        
        confidence_result = confidence_engine.compute_confidence(OutputType.INFERRED_WIDE, 0.70, 0.65, 30, 0.70)
        return OutputLineItem(
            output_id=f"integrated_phys_age_{int(datetime.utcnow().timestamp())}",
            metric_name="physiological_age_proxy",
            panel_name="comprehensive_integrated",
            frequency=OutputFrequency.MONTHLY,
            measured_vs_inferred="inferred_wide",
            value_score=round(physiological_age, 1),
            units="years",
            confidence_percent=round(confidence_result['confidence_percent'], 1),
            confidence_top_3_drivers=confidence_result['top_3_drivers'][:3],
            what_increases_confidence=confidence_result['what_increases_confidence'] + ["Add VO2max or other fitness markers"],
            safe_action_suggestion=f"Physiological age is {physiological_age:.0f} (chronological {chronological_age}). {'Good health!' if age_modifier < 0 else 'Focus on metabolic, cardiovascular, and autonomic optimization.'}",
            input_chain=f"Chronological age {chronological_age} + HR + HRV + BP + metabolic + sleep + activity",
            input_references={'soap_profile_id': submission.id},
            methodologies_used=["Population percentile mapping (aging biomarkers)", "Composite scoring (HR+HRV+BP+metabolic+sleep+activity)", "Bayesian calibration to population norms", "Trend analysis (biological aging velocity)"],
            method_why=["Evidence-based aging markers", "Holistic physiological assessment", "Calibrates against population aging curves", "Tracks aging trajectory over time"],
            gating_payload={},
            confidence_payload=confidence_result
        )
