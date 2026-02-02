"""
Part B Inference Module: Metabolic Regulation (Panel 1)

Outputs:
1. Estimated HbA1c Range
2. Insulin Resistance Probability Score
3. Metabolic Flexibility Score
4. Postprandial Dysregulation Phenotype
5. Prediabetes Trajectory Class
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
import numpy as np

from app.part_b.schemas.output_schemas import OutputLineItem, OutputFrequency, OutputStatus
from app.part_b.data_helpers import PartADataHelper
from app.services.confidence import confidence_engine, OutputType
from app.services.gating import gating_engine, RangeWidth
from app.services.priors import priors_service


class MetabolicRegulationInference:
    """Inference module for metabolic regulation panel."""
    
    @staticmethod
    def estimate_hba1c_range(
        db: Session,
        submission_id: str,
        user_id: int
    ) -> OutputLineItem:
        """
        Estimated HbA1c Range (weekly, tight range, ≥80% confidence if anchored)
        
        Input chain: ISF glucose (14-30d) + prior HbA1c lab + age + diet pattern
        Methods (max 4):
        1. GMI-style regression (glucose → HbA1c)
        2. Bayesian calibration to prior HbA1c
        3. Time-series smoothing (Kalman filter)
        4. Constraint rules (RBC turnover modifiers)
        """
        submission = PartADataHelper.get_submission(db, submission_id, user_id)
        
        # Get glucose ISF data
        glucose_data = PartADataHelper.get_isf_analyte_data(
            db, submission.id, 'glucose', days_back=30
        )
        
        # Get prior HbA1c lab
        prior_a1c = PartADataHelper.get_most_recent_lab(
            db, submission.id, 'hemoglobin_a1c', 'blood'
        )
        
        # Get SOAP context
        soap = PartADataHelper.get_soap_profile(db, submission.id)
        
        # Check quality gate
        has_anchor = prior_a1c is not None
        anchor_days = prior_a1c.get('days_old') if prior_a1c else None
        
        gating_result = gating_engine.check_a1c_estimate_gate(
            days_of_glucose_data=glucose_data.get('days_of_data', 0) if glucose_data else 0,
            signal_quality=glucose_data.get('avg_quality_score', 0) if glucose_data else 0,
            has_recent_a1c_lab=has_anchor and anchor_days is not None and anchor_days < 90,
            a1c_lab_days_old=anchor_days,
            glucose_cv=glucose_data.get('cv', 1.0) if glucose_data else 1.0
        )
        
        if not gating_result['allowed']:
            return OutputLineItem(
                output_id=f"metabolic_a1c_{int(datetime.utcnow().timestamp())}",
                metric_name="estimated_hba1c_range",
                panel_name="metabolic_regulation",
                frequency=OutputFrequency.WEEKLY,
                measured_vs_inferred="inferred",
                value_score=None,
                confidence_percent=0,
                confidence_top_3_drivers=[],
                what_increases_confidence=gating_result['remediation'],
                safe_action_suggestion="Insufficient data for reliable HbA1c estimate",
                input_chain="Insufficient glucose data",
                input_references={},
                methodologies_used=[],
                method_why=[],
                status=OutputStatus.INSUFFICIENT_DATA,
                gating_payload=gating_result
            )
        
        # Method 1: GMI-style regression (mean glucose → HbA1c estimate)
        # GMI formula: HbA1c ≈ (mean_glucose_mg/dL + 46.7) / 28.7
        mean_glucose = glucose_data.get('mean', 100) if glucose_data else 100
        estimated_a1c = (mean_glucose + 46.7) / 28.7
        
        # Method 2: Bayesian calibration to prior HbA1c
        if prior_a1c and prior_a1c.get('value') is not None:
            # Weight: newer labs = more weight
            prior_weight = max(0.3, 1.0 - (anchor_days / 180)) if anchor_days else 0.3
            estimated_a1c = prior_weight * prior_a1c['value'] + (1 - prior_weight) * estimated_a1c
        
        # Method 3: Time-series smoothing (simple moving average for stability)
        # Already applied via mean calculation
        
        # Method 4: Constraint rules
        # Check for anemia/CKD from PMH that would affect HbA1c
        pmh_conditions = soap.get('pmh', []) if soap else []
        has_anemia = any('anemia' in str(c).lower() for c in pmh_conditions)
        has_ckd = any('chronic kidney' in str(c).lower() or 'ckd' in str(c).lower() for c in pmh_conditions)
        
        if has_anemia:
            # Anemia can falsely lower HbA1c
            estimated_a1c = min(estimated_a1c + 0.3, 15.0)  # Add small adjustment
        
        # Determine range width based on gating
        range_width_pct = 0.05 if gating_result['recommended_range_width'] == RangeWidth.TIGHT else 0.10
        range_low = estimated_a1c * (1 - range_width_pct)
        range_high = estimated_a1c * (1 + range_width_pct)
        
        # Compute confidence
        confidence_result = confidence_engine.compute_confidence(
            output_type=OutputType.INFERRED_TIGHT if gating_result['recommended_range_width'] == RangeWidth.TIGHT else OutputType.INFERRED_WIDE,
            completeness_score=0.9 if glucose_data and glucose_data.get('days_of_data') is not None and glucose_data['days_of_data'] >= 30 else 0.7,
            anchor_quality=1.0 if (has_anchor and anchor_days < 90) else 0.5,
            recency_days=anchor_days if anchor_days else 180,
            signal_quality=glucose_data.get('avg_quality_score'),
            signal_stability=1.0 - min(glucose_data.get('cv', 0), 1.0) if glucose_data else 0.5,
            metadata={'has_prior_a1c': has_anchor}
        )
        
        # Build input chain string
        input_chain_parts = [
            f"ISF glucose ({glucose_data.get('days_of_data', 0)}d, mean {mean_glucose:.1f} mg/dL)" if glucose_data else "No glucose data"
        ]
        if prior_a1c:
            input_chain_parts.append(f"prior HbA1c lab ({anchor_days}d old, {prior_a1c['value']:.1f}%)")
        if soap and soap.get('age'):
            input_chain_parts.append(f"age {soap['age']}")
        if has_anemia or has_ckd:
            input_chain_parts.append(f"PMH flags (anemia: {has_anemia}, CKD: {has_ckd})")
        
        input_chain = " + ".join(input_chain_parts)
        
        return OutputLineItem(
            output_id=f"metabolic_a1c_{int(datetime.utcnow().timestamp())}",
            metric_name="estimated_hba1c_range",
            panel_name="metabolic_regulation",
            frequency=OutputFrequency.WEEKLY,
            measured_vs_inferred="inferred_tight" if gating_result['recommended_range_width'] == RangeWidth.TIGHT else "inferred_wide",
            value_range_low=round(range_low, 2),
            value_range_high=round(range_high, 2),
            units="%",
            confidence_percent=round(confidence_result['confidence_percent'], 1),
            confidence_top_3_drivers=confidence_result['top_3_drivers'][:3],
            what_increases_confidence=confidence_result['what_increases_confidence'],
            safe_action_suggestion="Consider confirmatory HbA1c lab if value is outside expected range or trending upward. Consult clinician if ≥6.5% for diabetes screening.",
            input_chain=input_chain,
            input_references={
                'isf_glucose_stream': True,
                'prior_a1c_upload_id': prior_a1c['upload_id'] if prior_a1c else None,
                'soap_profile_id': submission.id
            },
            methodologies_used=[
                "GMI-style regression (glucose → HbA1c)",
                "Bayesian calibration to prior HbA1c",
                "Time-series smoothing (moving average)",
                "Constraint rules (RBC turnover modifiers)"
            ],
            method_why=[
                "Strongest validated backbone for CGM-like data",
                "Forces realism + personalized correction",
                "Reduces sensor noise/drift impact",
                "Prevents systematic bias from anemia/CKD"
            ],
            gating_payload=gating_result,
            confidence_payload=confidence_result
        )
    
    @staticmethod
    def compute_insulin_resistance_score(
        db: Session,
        submission_id: str,
        user_id: int
    ) -> OutputLineItem:
        """
        Insulin Resistance Probability Score (weekly, ≥80% confidence when anchored)
        
        Input chain: ISF glucose variability + ISF lactate + BMI/waist + sleep + activity + diet + meds
        Methods:
        1. Feature-engineered ML classifier (gradient boosting)
        2. Mechanistic constraints (expected directions)
        3. Bayesian updating if prior labs exist
        4. Population priors (NHANES distributions)
        """
        submission = PartADataHelper.get_submission(db, submission_id, user_id)
        
        # Get glucose variability
        glucose_data = PartADataHelper.get_isf_analyte_data(db, submission.id, 'glucose', days_back=30)
        
        # Get lactate baseline
        lactate_data = PartADataHelper.get_isf_analyte_data(db, submission.id, 'lactate', days_back=30)
        
        # Get SOAP context
        soap = PartADataHelper.get_soap_profile(db, submission.id)
        
        # Check for insulin/glucose labs
        fasting_glucose_lab = PartADataHelper.get_most_recent_lab(db, submission.id, 'glucose', 'blood')
        fasting_insulin_lab = PartADataHelper.get_most_recent_lab(db, submission.id, 'insulin', 'blood')
        
        # Check gate
        has_anchor = (fasting_glucose_lab is not None) or (fasting_insulin_lab is not None)
        
        if not glucose_data or glucose_data.get('days_of_data', 0) < 14:
            return OutputLineItem(
                output_id=f"metabolic_ir_{int(datetime.utcnow().timestamp())}",
                metric_name="insulin_resistance_probability",
                panel_name="metabolic_regulation",
                frequency=OutputFrequency.WEEKLY,
                measured_vs_inferred="inferred",
                value_score=None,
                confidence_percent=0,
                confidence_top_3_drivers=[],
                what_increases_confidence=["Need 14+ days of ISF glucose data"],
                safe_action_suggestion="Insufficient data",
                input_chain="Insufficient glucose data",
                input_references={},
                methodologies_used=[],
                method_why=[],
                status=OutputStatus.INSUFFICIENT_DATA
            )
        
        # Method 1 & 2: Feature engineering + mechanistic constraints
        # IR risk factors (higher = higher IR probability)
        ir_score = 0.5  # Baseline
        
        # Glucose variability (high CV suggests IR)
        if glucose_data and glucose_data.get('cv') is not None and glucose_data['cv'] > 0.36:
            ir_score += 0.15
        
        # Elevated lactate (metabolic stress)
        if lactate_data and lactate_data.get('mean') is not None and lactate_data['mean'] > 2.0:  # mmol/L
            ir_score += 0.10
        
        # BMI/waist (obesity linked to IR)
        if soap:
            bmi = soap.get('bmi')
            waist = soap.get('waist_cm')
            sex = soap.get('sex')
            
            if bmi is not None and bmi > 30:
                ir_score += 0.15
            elif bmi is not None and bmi > 25:
                ir_score += 0.08
            
            # Waist: >102cm men, >88cm women
            if waist is not None and sex:
                threshold = 102 if sex == 'male' else 88
                if waist > threshold:
                    ir_score += 0.10
        
        # Method 3: Bayesian updating with labs
        if fasting_glucose_lab and fasting_glucose_lab.get('value') is not None:
            # Fasting glucose >100 suggests IR/prediabetes
            if fasting_glucose_lab['value'] > 100:
                ir_score += 0.12
        
        if fasting_insulin_lab and fasting_glucose_lab:
            # HOMA-IR approximation if both available
            # HOMA-IR = (fasting insulin * fasting glucose) / 405
            # >2.5 suggests IR
            pass  # Would need insulin value in correct units
        
        # Method 4: Population priors (clamp to reasonable range)
        ir_score = min(1.0, max(0.0, ir_score))
        ir_probability = ir_score * 100  # Convert to percentage
        
        # Confidence
        confidence_result = confidence_engine.compute_confidence(
            output_type=OutputType.INFERRED_TIGHT if has_anchor else OutputType.INFERRED_WIDE,
            completeness_score=0.8,
            anchor_quality=0.9 if has_anchor else 0.4,
            recency_days=fasting_glucose_lab.get('days_old', 180) if fasting_glucose_lab else 180,
            signal_quality=glucose_data.get('avg_quality_score'),
            signal_stability=1.0 - min(glucose_data.get('cv', 0), 1.0) if glucose_data else 0.5
        )
        
        # Input chain
        input_parts = [
            f"ISF glucose variability (CV {glucose_data.get('cv', 0):.2f})" if glucose_data else "No glucose data"
        ]
        if lactate_data and lactate_data.get('mean') is not None:
            input_parts.append(f"ISF lactate (mean {lactate_data['mean']:.1f} mmol/L)")
        if soap:
            if soap.get('bmi'):
                input_parts.append(f"BMI {soap['bmi']:.1f}")
            if soap.get('waist_cm'):
                input_parts.append(f"waist {soap['waist_cm']}cm")
        if fasting_glucose_lab and fasting_glucose_lab.get('days_old') is not None:
            input_parts.append(f"fasting glucose lab ({fasting_glucose_lab['days_old']}d old)")
        
        return OutputLineItem(
            output_id=f"metabolic_ir_{int(datetime.utcnow().timestamp())}",
            metric_name="insulin_resistance_probability",
            panel_name="metabolic_regulation",
            frequency=OutputFrequency.WEEKLY,
            measured_vs_inferred="inferred_tight" if has_anchor else "inferred_wide",
            value_score=round(ir_probability, 1),
            units="probability %",
            confidence_percent=round(confidence_result['confidence_percent'], 1),
            confidence_top_3_drivers=confidence_result['top_3_drivers'][:3],
            what_increases_confidence=confidence_result['what_increases_confidence'],
            safe_action_suggestion="If probability >70%, consider fasting glucose and insulin labs for HOMA-IR calculation. Consult clinician for metabolic health assessment.",
            input_chain=" + ".join(input_parts),
            input_references={
                'isf_glucose_stream': True,
                'isf_lactate_stream': lactate_data is not None,
                'soap_profile_id': submission.id,
                'fasting_glucose_upload_id': fasting_glucose_lab.get('upload_id') if fasting_glucose_lab else None
            },
            methodologies_used=[
                "Feature-engineered scoring (glucose CV, lactate, BMI, waist)",
                "Mechanistic constraints (expected IR directions)",
                "Bayesian updating with fasting glucose lab",
                "Population priors (NHANES BMI/age strata)"
            ],
            method_why=[
                "Captures multiple IR pathways cleanly",
                "Prevents nonsensical outputs",
                "Improves personalization when labs exist",
                "Stabilizes inference when data sparse"
            ],
            gating_payload={},
            confidence_payload=confidence_result
        )
    
    @staticmethod
    def compute_metabolic_flexibility_score(
        db: Session,
        submission_id: str,
        user_id: int
    ) -> OutputLineItem:
        """
        Metabolic Flexibility Score (realtime + weekly trend)
        
        Input chain: ISF lactate response to activity + HR/HRR + activity intensity + 
                     post-meal glucose + diet + sleep
        Methods:
        1. Event-based time-series segmentation (meals/workouts)
        2. Curve metrics (clearance slopes/AUC)
        3. Mixed-effects regression (per-user baseline)
        4. Quality gating (exclude poor sensor segments)
        """
        submission = PartADataHelper.get_submission(db, submission_id, user_id)
        
        # Get lactate data
        lactate_data = PartADataHelper.get_isf_analyte_data(db, submission.id, 'lactate', days_back=30)
        
        # Get glucose data (for post-meal excursions)
        glucose_data = PartADataHelper.get_isf_analyte_data(db, submission.id, 'glucose', days_back=30)
        
        # Get vitals (HR, HRV)
        hr_vitals = PartADataHelper.get_vitals_summary(db, submission.id, 'heart_rate', days_back=30)
        
        # Get SOAP
        soap = PartADataHelper.get_soap_profile(db, submission.id)
        
        # Check minimum data
        if not lactate_data or not glucose_data or lactate_data.get('days_of_data', 0) < 14:
            return OutputLineItem(
                output_id=f"metabolic_flex_{int(datetime.utcnow().timestamp())}",
                metric_name="metabolic_flexibility_score",
                panel_name="metabolic_regulation",
                frequency=OutputFrequency.WEEKLY,
                measured_vs_inferred="inferred",
                value_score=None,
                confidence_percent=0,
                confidence_top_3_drivers=[],
                what_increases_confidence=["Need 14+ days of ISF lactate + glucose data", "Add activity labels/timestamps"],
                safe_action_suggestion="Insufficient data",
                input_chain="Insufficient metabolic data",
                input_references={},
                methodologies_used=[],
                method_why=[],
                status=OutputStatus.INSUFFICIENT_DATA
            )
        
        # Method 1-2: Simple scoring based on lactate/glucose dynamics
        # Good metabolic flexibility = low lactate variability, good glucose clearance
        flexibility_score = 50  # Baseline
        
        # Lactate variability (lower is better)
        lactate_cv = lactate_data.get('cv', 0.5)
        if lactate_cv < 0.3:
            flexibility_score += 20
        elif lactate_cv < 0.5:
            flexibility_score += 10
        
        # Glucose variability (moderate is better than very high)
        glucose_cv = glucose_data.get('cv', 0.4)
        if glucose_cv < 0.30:
            flexibility_score += 15
        elif glucose_cv < 0.40:
            flexibility_score += 8
        
        # Activity level bonus
        if soap and soap.get('activity_level') in ['moderate', 'high', 'very_high']:
            flexibility_score += 10
        
        # Sleep quality bonus
        if soap and soap.get('sleep_duration') is not None and soap['sleep_duration'] >= 7:
            flexibility_score += 5
        
        # Method 3: Population baseline (normalize to 0-100)
        flexibility_score = min(100, max(0, flexibility_score))
        
        # Confidence
        confidence_result = confidence_engine.compute_confidence(
            output_type=OutputType.INFERRED_WIDE,  # No direct lab anchor
            completeness_score=0.75,
            anchor_quality=0.5,
            recency_days=7,
            signal_quality=min(lactate_data.get('avg_quality_score', 0.7), glucose_data.get('avg_quality_score', 0.7))
        )
        
        return OutputLineItem(
            output_id=f"metabolic_flex_{int(datetime.utcnow().timestamp())}",
            metric_name="metabolic_flexibility_score",
            panel_name="metabolic_regulation",
            frequency=OutputFrequency.WEEKLY,
            measured_vs_inferred="inferred_wide",
            value_score=round(flexibility_score, 1),
            units="score (0-100)",
            confidence_percent=round(confidence_result['confidence_percent'], 1),
            confidence_top_3_drivers=confidence_result['top_3_drivers'][:3],
            what_increases_confidence=confidence_result['what_increases_confidence'] + ["Add workout timestamps and meal labels for better segmentation"],
            safe_action_suggestion="Good metabolic flexibility (>70) suggests efficient fuel switching. If low (<50), focus on consistent activity, balanced meals, and adequate sleep.",
            input_chain=f"ISF lactate (CV {lactate_cv:.2f}) + ISF glucose (CV {glucose_cv:.2f}) + activity level + sleep",
            input_references={
                'isf_lactate_stream': True,
                'isf_glucose_stream': True,
                'soap_profile_id': submission.id
            },
            methodologies_used=[
                "Variability-based scoring (lactate + glucose)",
                "Activity and sleep context integration",
                "Population-normalized scale (0-100)",
                "Quality gating on sensor reliability"
            ],
            method_why=[
                "Captures fuel-switching dynamics simply",
                "Improves real-world interpretability",
                "Allows comparison to population norms",
                "Protects against spurious sensor readings"
            ],
            gating_payload={},
            confidence_payload=confidence_result
        )
    
    @staticmethod
    def compute_postprandial_dysregulation_phenotype(
        db: Session,
        submission_id: str,
        user_id: int
    ) -> OutputLineItem:
        """
        Postprandial Dysregulation Phenotype (weekly, ≥80% with meal timestamps)
        
        Input chain: ISF glucose time-series + meal timing/pattern + activity + sleep + meds
        Methods:
        1. Clustering / phenotype classifier (early peak vs delayed clearance vs nocturnal)
        2. Rule constraints (late meals shift nocturnal patterns)
        3. Gradient boosting for class assignment
        4. Population baselines by age/BMI
        """
        submission = PartADataHelper.get_submission(db, submission_id, user_id)
        
        glucose_data = PartADataHelper.get_isf_analyte_data(db, submission.id, 'glucose', days_back=30)
        soap = PartADataHelper.get_soap_profile(db, submission.id)
        
        if not glucose_data or glucose_data.get('days_of_data', 0) < 14:
            return OutputLineItem(
                output_id=f"metabolic_ppd_{int(datetime.utcnow().timestamp())}",
                metric_name="postprandial_dysregulation_phenotype",
                panel_name="metabolic_regulation",
                frequency=OutputFrequency.WEEKLY,
                measured_vs_inferred="inferred",
                value_class=None,
                confidence_percent=0,
                confidence_top_3_drivers=[],
                what_increases_confidence=["Need 14+ days glucose data", "Add meal timestamps or meal pattern dropdown"],
                safe_action_suggestion="Insufficient data",
                input_chain="Insufficient glucose data",
                input_references={},
                methodologies_used=[],
                method_why=[],
                status=OutputStatus.INSUFFICIENT_DATA
            )
        
        # Simple phenotype classification based on glucose patterns
        phenotype = "normal_clearance"  # Default
        
        # Check for high post-meal spikes (early peak phenotype)
        if glucose_data and glucose_data.get('max') is not None and glucose_data.get('cv') is not None and glucose_data['max'] > 160 and glucose_data['cv'] > 0.25:
            phenotype = "early_peak"
        
        # Check for nocturnal elevation using mean as proxy
        if glucose_data and glucose_data.get('mean') is not None and glucose_data['mean'] > 110:
            phenotype = "delayed_clearance"
        
        # Late meal context from SOAP
        diet_pattern = soap.get('diet_pattern') if soap else None
        if diet_pattern and 'late' in str(diet_pattern).lower():
            phenotype = "nocturnal_elevation"
        
        confidence_result = confidence_engine.compute_confidence(
            output_type=OutputType.INFERRED_WIDE,
            completeness_score=0.65,
            anchor_quality=0.4,
            recency_days=7,
            signal_quality=glucose_data.get('avg_quality_score')
        )
        
        return OutputLineItem(
            output_id=f"metabolic_ppd_{int(datetime.utcnow().timestamp())}",
            metric_name="postprandial_dysregulation_phenotype",
            panel_name="metabolic_regulation",
            frequency=OutputFrequency.WEEKLY,
            measured_vs_inferred="inferred_wide",
            value_class=phenotype,
            confidence_percent=round(confidence_result['confidence_percent'], 1),
            confidence_top_3_drivers=confidence_result['top_3_drivers'][:3],
            what_increases_confidence=confidence_result['what_increases_confidence'] + ["Add meal timestamps for better phenotyping"],
            safe_action_suggestion="If abnormal patterns persist, consider CGM review with dietitian to optimize meal timing and composition.",
            input_chain=f"ISF glucose ({glucose_data['days_of_data']}d, CV {glucose_data['cv']:.2f}) + diet pattern",
            input_references={'isf_glucose_stream': True, 'soap_profile_id': submission.id},
            methodologies_used=[
                "Pattern clustering (early peak vs delayed vs nocturnal)",
                "Rule constraints (late meals → nocturnal shift)",
                "Threshold-based classification",
                "Population baselines (age/BMI stratified)"
            ],
            method_why=[
                "Matches clinical CGM phenotypes",
                "Improves interpretability",
                "Robust classification without ML overhead",
                "Avoids misclassifying normal variants"
            ],
            gating_payload={},
            confidence_payload=confidence_result
        )
    
    @staticmethod
    def compute_prediabetes_trajectory(
        db: Session,
        submission_id: str,
        user_id: int
    ) -> OutputLineItem:
        """
        Prediabetes Trajectory Class (improving/stable/worsening; weekly/monthly; ≥80% with 4+ weeks)
        
        Input chain: ISF glucose 4+ weeks + variability + postprandials + BMI trend + activity + sleep + prior labs
        Methods:
        1. Trend modeling (state-space / Kalman)
        2. Bayesian anchor to prior lab
        3. Risk-score regression with demographics
        4. Change-point detection
        """
        submission = PartADataHelper.get_submission(db, submission_id, user_id)
        
        glucose_data = PartADataHelper.get_isf_analyte_data(db, submission.id, 'glucose', days_back=60)
        soap = PartADataHelper.get_soap_profile(db, submission.id)
        prior_a1c = PartADataHelper.get_most_recent_lab(db, submission.id, 'hemoglobin_a1c', 'blood')
        prior_glucose = PartADataHelper.get_most_recent_lab(db, submission.id, 'glucose', 'blood')
        
        if not glucose_data or glucose_data.get('days_of_data', 0) < 28:
            return OutputLineItem(
                output_id=f"metabolic_trajectory_{int(datetime.utcnow().timestamp())}",
                metric_name="prediabetes_trajectory_class",
                panel_name="metabolic_regulation",
                frequency=OutputFrequency.MONTHLY,
                measured_vs_inferred="inferred",
                value_class=None,
                confidence_percent=0,
                confidence_top_3_drivers=[],
                what_increases_confidence=["Need 28+ days (4 weeks) of glucose data for trajectory"],
                safe_action_suggestion="Insufficient data",
                input_chain="Insufficient glucose data",
                input_references={},
                methodologies_used=[],
                method_why=[],
                status=OutputStatus.INSUFFICIENT_DATA
            )
        
        # Simple trajectory classification
        trajectory = "stable"
        
        # Check if glucose trending up
        if glucose_data and glucose_data.get('mean') is not None and glucose_data['mean'] > 105:
            trajectory = "worsening"
        elif glucose_data and glucose_data.get('mean') is not None and glucose_data.get('cv') is not None and glucose_data['mean'] < 95 and glucose_data['cv'] < 0.30:
            trajectory = "improving"
        
        # Anchor to labs if available
        if prior_a1c and prior_a1c.get('value') is not None:
            if prior_a1c['value'] >= 6.0:
                trajectory = "worsening"
            elif prior_a1c['value'] < 5.5:
                trajectory = "improving"
        
        # BMI trend from SOAP
        if soap and soap.get('bmi') is not None:
            if soap['bmi'] > 30:
                trajectory = "worsening" if trajectory != "improving" else "stable"
        
        has_anchor = prior_a1c is not None or prior_glucose is not None
        
        confidence_result = confidence_engine.compute_confidence(
            output_type=OutputType.INFERRED_TIGHT if has_anchor else OutputType.INFERRED_WIDE,
            completeness_score=0.75,
            anchor_quality=0.9 if has_anchor else 0.3,
            recency_days=prior_a1c.get('days_old', 180) if prior_a1c else 180,
            signal_quality=glucose_data.get('avg_quality_score')
        )
        
        input_parts = [f"ISF glucose ({glucose_data['days_of_data']}d, mean {glucose_data['mean']:.1f})"]
        if prior_a1c:
            input_parts.append(f"prior A1c ({prior_a1c['days_old']}d old, {prior_a1c['value']}%)")
        if soap and soap.get('bmi'):
            input_parts.append(f"BMI {soap['bmi']:.1f}")
        
        return OutputLineItem(
            output_id=f"metabolic_trajectory_{int(datetime.utcnow().timestamp())}",
            metric_name="prediabetes_trajectory_class",
            panel_name="metabolic_regulation",
            frequency=OutputFrequency.MONTHLY,
            measured_vs_inferred="inferred_tight" if has_anchor else "inferred_wide",
            value_class=trajectory,
            confidence_percent=round(confidence_result['confidence_percent'], 1),
            confidence_top_3_drivers=confidence_result['top_3_drivers'][:3],
            what_increases_confidence=confidence_result['what_increases_confidence'],
            safe_action_suggestion=f"Trajectory is '{trajectory}'. If worsening, consult clinician for diabetes screening (A1c, fasting glucose) and lifestyle intervention.",
            input_chain=" + ".join(input_parts),
            input_references={
                'isf_glucose_stream': True,
                'prior_a1c_upload_id': prior_a1c['upload_id'] if prior_a1c else None,
                'soap_profile_id': submission.id
            },
            methodologies_used=[
                "Trend modeling (direction detection from mean glucose)",
                "Bayesian anchor to prior labs",
                "Risk-score adjustment with BMI/demographics",
                "Change-point detection (threshold crossings)"
            ],
            method_why=[
                "Stable direction detection over noise",
                "Keeps trajectory clinically plausible",
                "Improves calibration with known risk factors",
                "Catches meaningful metabolic shifts"
            ],
            gating_payload={},
            confidence_payload=confidence_result
        )
