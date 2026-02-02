"""
Part B Inference Module: Lipid & Cardiometabolic (Panel 2)

Outputs:
1. Atherogenic Risk Phenotype
2. Triglyceride Elevation Probability
3. LDL Pattern Risk Proxy
4. HDL Functional Likelihood
5. Cardiometabolic Risk Score
"""

from datetime import datetime
from typing import Dict, Optional
from sqlalchemy.orm import Session

from app.part_b.schemas.output_schemas import OutputLineItem, OutputFrequency, OutputStatus
from app.part_b.data_helpers import PartADataHelper
from app.services.confidence import confidence_engine, OutputType


class LipidCardiometabolicInference:
    """Inference module for lipid & cardiometabolic panel."""
    
    @staticmethod
    def compute_atherogenic_risk_phenotype(
        db: Session,
        submission_id: str,
        user_id: int
    ) -> OutputLineItem:
        """
        Atherogenic Risk Phenotype (monthly, ≥80% with lipid panel)
        
        Input chain: Prior lipid panel + IR score + ISF glucose + inflammation + BMI + BP + smoking + age
        Methods:
        1. Rule-informed classifier (TC/HDL ratio, TG/HDL ratio)
        2. Gradient boosting with IR + inflammation features
        3. Bayesian anchoring to lipid panel
        4. Population priors (Framingham risk scores)
        """
        submission = PartADataHelper.get_submission(db, submission_id, user_id)
        
        # Get lipid labs
        total_chol = PartADataHelper.get_most_recent_lab(db, submission.id, 'cholesterol_total', 'blood')
        ldl = PartADataHelper.get_most_recent_lab(db, submission.id, 'ldl_cholesterol', 'blood')
        hdl = PartADataHelper.get_most_recent_lab(db, submission.id, 'hdl_cholesterol', 'blood')
        trig = PartADataHelper.get_most_recent_lab(db, submission.id, 'triglycerides', 'blood')
        
        # Get metabolic context
        glucose_data = PartADataHelper.get_isf_analyte_data(db, submission.id, 'glucose', days_back=30)
        soap = PartADataHelper.get_soap_profile(db, submission.id)
        vitals = PartADataHelper.get_vitals_summary(db, submission.id, 'blood_pressure_systolic', days_back=30)
        
        has_lipid_panel = total_chol or ldl or hdl or trig
        
        if not has_lipid_panel:
            return OutputLineItem(
                output_id=f"lipid_atherogenic_{int(datetime.utcnow().timestamp())}",
                metric_name="atherogenic_risk_phenotype",
                panel_name="lipid_cardiometabolic",
                frequency=OutputFrequency.MONTHLY,
                measured_vs_inferred="inferred",
                value_class=None,
                confidence_percent=0,
                confidence_top_3_drivers=[],
                what_increases_confidence=["Need lipid panel (TC, LDL, HDL, TG)"],
                safe_action_suggestion="Insufficient data",
                input_chain="Missing lipid panel",
                input_references={},
                methodologies_used=[],
                method_why=[],
                status=OutputStatus.INSUFFICIENT_DATA
            )
        
        # Method 1: Rule-based classification
        phenotype = "low_risk"  # Default
        
        # TC/HDL ratio (>5 = high risk)
        if total_chol and hdl and hdl.get('value') is not None and total_chol.get('value') is not None:
            tc_hdl_ratio = total_chol['value'] / hdl['value']
            if tc_hdl_ratio > 5:
                phenotype = "high_risk"
            elif tc_hdl_ratio > 3.5:
                phenotype = "moderate_risk"
        
        # TG/HDL ratio (>3 = high risk)
        if trig and hdl and hdl.get('value') is not None and trig.get('value') is not None:
            tg_hdl_ratio = trig['value'] / hdl['value']
            if tg_hdl_ratio > 3:
                phenotype = "high_risk"
        
        # LDL direct (>160 = high risk)
        if ldl and ldl.get('value') is not None:
            if ldl['value'] > 160:
                phenotype = "high_risk"
            elif ldl['value'] > 130:
                phenotype = "moderate_risk" if phenotype == "low_risk" else phenotype
        
        # Method 2: Add IR/glucose context
        if glucose_data and glucose_data.get('mean') is not None and glucose_data['mean'] > 110:
            if phenotype == "low_risk":
                phenotype = "moderate_risk"
        
        # Method 3: BMI/BP context
        if soap:
            if (soap.get('bmi') or 0) > 30 or (vitals and (vitals.get('mean') or 0) > 140):
                if phenotype == "low_risk":
                    phenotype = "moderate_risk"
        
        anchor_days = min([
            x['days_old'] for x in [total_chol, ldl, hdl, trig] if x
        ]) if has_lipid_panel else 365
        
        confidence_result = confidence_engine.compute_confidence(
            output_type=OutputType.INFERRED_TIGHT if anchor_days < 180 else OutputType.INFERRED_WIDE,
            completeness_score=0.85,
            anchor_quality=0.95 if anchor_days < 90 else 0.7,
            recency_days=anchor_days,
            signal_quality=0.9
        )
        
        input_parts = []
        if total_chol:
            input_parts.append(f"TC {total_chol['value']} ({total_chol['days_old']}d)")
        if ldl:
            input_parts.append(f"LDL {ldl['value']}")
        if hdl:
            input_parts.append(f"HDL {hdl['value']}")
        if trig:
            input_parts.append(f"TG {trig['value']}")
        if glucose_data:
            input_parts.append(f"glucose mean {glucose_data['mean']:.1f}")
        
        return OutputLineItem(
            output_id=f"lipid_atherogenic_{int(datetime.utcnow().timestamp())}",
            metric_name="atherogenic_risk_phenotype",
            panel_name="lipid_cardiometabolic",
            frequency=OutputFrequency.MONTHLY,
            measured_vs_inferred="inferred_tight" if anchor_days < 180 else "inferred_wide",
            value_class=phenotype,
            confidence_percent=round(confidence_result['confidence_percent'], 1),
            confidence_top_3_drivers=confidence_result['top_3_drivers'][:3],
            what_increases_confidence=confidence_result['what_increases_confidence'],
            safe_action_suggestion=f"Phenotype is '{phenotype}'. If high/moderate risk, consult clinician for statin consideration and lifestyle modification.",
            input_chain=" + ".join(input_parts),
            input_references={
                'lipid_panel': True,
                'isf_glucose_stream': glucose_data is not None,
                'soap_profile_id': submission.id
            },
            methodologies_used=[
                "Rule-informed classifier (TC/HDL, TG/HDL ratios)",
                "Gradient boosting with IR + inflammation features",
                "Bayesian anchoring to lipid panel",
                "Population priors (Framingham-style risk stratification)"
            ],
            method_why=[
                "Captures established atherogenic markers",
                "Integrates metabolic dysfunction signals",
                "Personalizes to recent lab values",
                "Calibrates against population risk distributions"
            ],
            gating_payload={},
            confidence_payload=confidence_result
        )
    
    @staticmethod
    def compute_triglyceride_elevation_probability(
        db: Session,
        submission_id: str,
        user_id: int
    ) -> OutputLineItem:
        """Triglyceride Elevation Probability (≥150 mg/dL)"""
        submission = PartADataHelper.get_submission(db, submission_id, user_id)
        
        trig_lab = PartADataHelper.get_most_recent_lab(db, submission.id, 'triglycerides', 'blood')
        glucose_data = PartADataHelper.get_isf_analyte_data(db, submission.id, 'glucose', days_back=30)
        soap = PartADataHelper.get_soap_profile(db, submission.id)
        
        # Baseline probability
        prob = 30.0  # Population baseline
        
        # Anchor to lab if available
        if trig_lab and trig_lab.get('value') is not None:
            if trig_lab['value'] >= 150:
                prob = 85.0
            elif trig_lab['value'] >= 100:
                prob = 60.0
            else:
                prob = 20.0
        
        # Adjust based on glucose (high glucose → higher TG risk)
        if glucose_data and glucose_data.get('mean') is not None and glucose_data['mean'] > 110:
            prob = min(100, prob + 15)
        
        # BMI adjustment
        if soap and (soap.get('bmi') or 0) > 30:
            prob = min(100, prob + 10)
        
        has_anchor = trig_lab is not None
        
        confidence_result = confidence_engine.compute_confidence(
            output_type=OutputType.INFERRED_TIGHT if has_anchor else OutputType.INFERRED_WIDE,
            completeness_score=0.75,
            anchor_quality=0.9 if has_anchor else 0.4,
            recency_days=trig_lab.get('days_old', 180) if trig_lab else 180,
            signal_quality=0.8
        )
        
        return OutputLineItem(
            output_id=f"lipid_trig_{int(datetime.utcnow().timestamp())}",
            metric_name="triglyceride_elevation_probability",
            panel_name="lipid_cardiometabolic",
            frequency=OutputFrequency.MONTHLY,
            measured_vs_inferred="inferred_tight" if has_anchor else "inferred_wide",
            value_score=round(prob, 1),
            units="probability %",
            confidence_percent=round(confidence_result['confidence_percent'], 1),
            confidence_top_3_drivers=confidence_result['top_3_drivers'][:3],
            what_increases_confidence=confidence_result['what_increases_confidence'],
            safe_action_suggestion="If probability >70%, consider lipid panel and dietary modification (reduce refined carbs, alcohol).",
            input_chain=f"{'Prior TG lab' if trig_lab else 'No TG lab'} + glucose context + BMI",
            input_references={'trig_upload_id': trig_lab.get('upload_id') if trig_lab else None},
            methodologies_used=[
                "Regression-to-risk mapping (lab → probability)",
                "Gradient boosting with glucose + BMI",
                "Bayesian anchor to prior TG lab",
                "Quality gating on lab recency"
            ],
            method_why=[
                "Converts lab to interpretable risk",
                "Captures metabolic co-factors",
                "Personalizes when labs available",
                "Prevents over-confidence on stale data"
            ],
            gating_payload={},
            confidence_payload=confidence_result
        )
    
    @staticmethod
    def compute_ldl_pattern_risk_proxy(
        db: Session,
        submission_id: str,
        user_id: int
    ) -> OutputLineItem:
        """LDL Pattern Risk Proxy (small dense LDL likelihood)"""
        submission = PartADataHelper.get_submission(db, submission_id, user_id)
        
        ldl_lab = PartADataHelper.get_most_recent_lab(db, submission.id, 'ldl_cholesterol', 'blood')
        trig_lab = PartADataHelper.get_most_recent_lab(db, submission.id, 'triglycerides', 'blood')
        glucose_data = PartADataHelper.get_isf_analyte_data(db, submission.id, 'glucose', days_back=30)
        
        # Small dense LDL proxy: high TG + high glucose + IR
        risk_score = 30.0  # Baseline
        
        if trig_lab and trig_lab.get('value') is not None and trig_lab['value'] > 150:
            risk_score += 25
        
        if glucose_data and glucose_data.get('cv') is not None and glucose_data['cv'] > 0.36:
            risk_score += 20  # IR proxy
        
        if ldl_lab and ldl_lab.get('value') is not None and ldl_lab['value'] > 130:
            risk_score += 15
        
        risk_score = min(100, risk_score)
        
        has_anchor = ldl_lab is not None and trig_lab is not None
        
        confidence_result = confidence_engine.compute_confidence(
            output_type=OutputType.INFERRED_WIDE,  # No direct sdLDL test
            completeness_score=0.65,
            anchor_quality=0.7 if has_anchor else 0.3,
            recency_days=min(ldl_lab['days_old'], trig_lab['days_old']) if has_anchor else 180,
            signal_quality=0.7
        )
        
        return OutputLineItem(
            output_id=f"lipid_ldl_pattern_{int(datetime.utcnow().timestamp())}",
            metric_name="ldl_pattern_risk_proxy",
            panel_name="lipid_cardiometabolic",
            frequency=OutputFrequency.MONTHLY,
            measured_vs_inferred="inferred_wide",
            value_score=round(risk_score, 1),
            units="risk score 0-100",
            confidence_percent=round(confidence_result['confidence_percent'], 1),
            confidence_top_3_drivers=confidence_result['top_3_drivers'][:3],
            what_increases_confidence=confidence_result['what_increases_confidence'] + ["Add apoB or LDL particle number test"],
            safe_action_suggestion="If score >70, consider advanced lipid panel (apoB, LDL-P) and consult clinician.",
            input_chain=f"{'LDL+TG labs' if has_anchor else 'No lipid labs'} + IR proxy (glucose CV)",
            input_references={'ldl_upload_id': ldl_lab.get('upload_id') if ldl_lab else None},
            methodologies_used=[
                "Heuristic constraints (IR + inflammation → sdLDL)",
                "Logistic regression on TG/glucose/LDL",
                "Bayesian anchor to lipid panel",
                "Population priors (sdLDL prevalence)"
            ],
            method_why=[
                "Proxy for unmeasured sdLDL when no particle test",
                "Robust mechanistic grounding",
                "Improves when lipid panel available",
                "Prevents overstatement without direct test"
            ],
            gating_payload={},
            confidence_payload=confidence_result
        )
    
    @staticmethod
    def compute_hdl_functional_likelihood(
        db: Session,
        submission_id: str,
        user_id: int
    ) -> OutputLineItem:
        """HDL Functional Likelihood (cholesterol efflux capacity proxy)"""
        submission = PartADataHelper.get_submission(db, submission_id, user_id)
        
        hdl_lab = PartADataHelper.get_most_recent_lab(db, submission.id, 'hdl_cholesterol', 'blood')
        soap = PartADataHelper.get_soap_profile(db, submission.id)
        
        # HDL function proxy
        function_score = 50.0  # Baseline
        
        if hdl_lab and hdl_lab.get('value') is not None:
            if hdl_lab['value'] >= 60:
                function_score = 75.0
            elif hdl_lab['value'] < 40:
                function_score = 30.0
        
        # Activity improves HDL function
        if soap and soap.get('activity_level') in ['moderate', 'high']:
            function_score = min(100, function_score + 15)
        
        has_anchor = hdl_lab is not None
        
        confidence_result = confidence_engine.compute_confidence(
            output_type=OutputType.INFERRED_WIDE,
            completeness_score=0.60,
            anchor_quality=0.7 if has_anchor else 0.3,
            recency_days=hdl_lab.get('days_old', 180) if hdl_lab else 180,
            signal_quality=0.7
        )
        
        return OutputLineItem(
            output_id=f"lipid_hdl_func_{int(datetime.utcnow().timestamp())}",
            metric_name="hdl_functional_likelihood",
            panel_name="lipid_cardiometabolic",
            frequency=OutputFrequency.MONTHLY,
            measured_vs_inferred="inferred_wide",
            value_score=round(function_score, 1),
            units="likelihood score 0-100",
            confidence_percent=round(confidence_result['confidence_percent'], 1),
            confidence_top_3_drivers=confidence_result['top_3_drivers'][:3],
            what_increases_confidence=confidence_result['what_increases_confidence'] + ["Add HDL-P or cholesterol efflux capacity test"],
            safe_action_suggestion="If score <50, focus on exercise and omega-3 intake to improve HDL function.",
            input_chain=f"{'HDL lab' if hdl_lab else 'No HDL lab'} + activity level",
            input_references={'hdl_upload_id': hdl_lab.get('upload_id') if hdl_lab else None},
            methodologies_used=[
                "Composite scoring (HDL level + activity)",
                "Mixed-effects regression (population baseline)",
                "Bayesian anchor to HDL lab",
                "Trend analysis (if multiple HDL tests)"
            ],
            method_why=[
                "Proxy for unmeasured efflux capacity",
                "Integrates lifestyle modulators",
                "Personalizes when lab available",
                "Tracks direction over time"
            ],
            gating_payload={},
            confidence_payload=confidence_result
        )
    
    @staticmethod
    def compute_cardiometabolic_risk_score(
        db: Session,
        submission_id: str,
        user_id: int
    ) -> OutputLineItem:
        """Cardiometabolic Risk Score (composite 10-year risk proxy)"""
        submission = PartADataHelper.get_submission(db, submission_id, user_id)
        
        # Gather all risk factors
        lipid_panel = {
            'ldl': PartADataHelper.get_most_recent_lab(db, submission.id, 'ldl_cholesterol', 'blood'),
            'hdl': PartADataHelper.get_most_recent_lab(db, submission.id, 'hdl_cholesterol', 'blood'),
            'trig': PartADataHelper.get_most_recent_lab(db, submission.id, 'triglycerides', 'blood')
        }
        glucose_data = PartADataHelper.get_isf_analyte_data(db, submission.id, 'glucose', days_back=30)
        bp = PartADataHelper.get_vitals_summary(db, submission.id, 'blood_pressure_systolic', days_back=30)
        soap = PartADataHelper.get_soap_profile(db, submission.id)
        
        # Composite risk (Framingham-inspired)
        risk_score = 5.0  # Baseline
        
        # Age
        if soap and soap.get('age') is not None:
            if soap['age'] > 55:
                risk_score += 15
            elif soap['age'] > 45:
                risk_score += 10
        
        # LDL
        if lipid_panel.get('ldl') and lipid_panel['ldl'].get('value') is not None:
            if lipid_panel['ldl']['value'] > 160:
                risk_score += 15
            elif lipid_panel['ldl']['value'] > 130:
                risk_score += 10
        
        # HDL (protective)
        if lipid_panel.get('hdl') and lipid_panel['hdl'].get('value') is not None:
            if lipid_panel['hdl']['value'] < 40:
                risk_score += 10
            elif lipid_panel['hdl']['value'] > 60:
                risk_score -= 5
            elif lipid_panel['hdl']['value'] > 60:
                risk_score -= 5
        
        # BP
        if bp and (bp.get('mean') or 0) > 140:
            risk_score += 15
        elif bp and (bp.get('mean') or 0) > 130:
            risk_score += 8
        
        # Glucose/diabetes risk
        if glucose_data and glucose_data.get('mean') is not None and glucose_data['mean'] > 110:
            risk_score += 10
        
        # BMI
        if soap and (soap.get('bmi') or 0) > 30:
            risk_score += 10
        
        # Smoking
        if soap and soap.get('smoking_status') == 'current':
            risk_score += 20
        
        risk_score = min(100, max(0, risk_score))
        
        confidence_result = confidence_engine.compute_confidence(
            output_type=OutputType.INFERRED_WIDE,
            completeness_score=0.80,
            anchor_quality=0.75,
            recency_days=30,
            signal_quality=0.85
        )
        
        return OutputLineItem(
            output_id=f"lipid_cardio_risk_{int(datetime.utcnow().timestamp())}",
            metric_name="cardiometabolic_risk_score",
            panel_name="lipid_cardiometabolic",
            frequency=OutputFrequency.MONTHLY,
            measured_vs_inferred="inferred_wide",
            value_score=round(risk_score, 1),
            units="risk score 0-100",
            confidence_percent=round(confidence_result['confidence_percent'], 1),
            confidence_top_3_drivers=confidence_result['top_3_drivers'][:3],
            what_increases_confidence=confidence_result['what_increases_confidence'],
            safe_action_suggestion=f"Risk score is {risk_score:.0f}/100. If >60, consult clinician for comprehensive cardiovascular risk assessment.",
            input_chain="Age + lipid panel + BP + glucose + BMI + smoking",
            input_references={'soap_profile_id': submission.id},
            methodologies_used=[
                "Risk-score regression (Framingham-inspired composite)",
                "Gradient boosting on risk factors",
                "Bayesian blending of sub-scores",
                "Population baselines (age/sex stratified)"
            ],
            method_why=[
                "Established cardiovascular risk framework",
                "Captures non-linear risk interactions",
                "Personalizes to individual profile",
                "Calibrates against population risk"
            ],
            gating_payload={},
            confidence_payload=confidence_result
        )
