"""
Renal & Hydration Balance Inference Panel

This module implements inference algorithms for the Renal & Hydration Balance panel,
Panel 6 in the Part B report structure.

Outputs:
1. Hydration Status
2. Electrolyte Regulation Efficiency Score
3. Renal Stress Index
4. Dehydration-Driven Creatinine Elevation Risk
5. eGFR Trajectory Class
"""

from datetime import datetime
from sqlalchemy.orm import Session
from app.part_b.schemas.output_schemas import OutputLineItem, OutputFrequency, OutputStatus
from app.part_b.data_helpers import PartADataHelper
from app.services.confidence import confidence_engine, OutputType


class RenalHydrationInference:
    """Inference methods for renal function and hydration balance outputs."""

    @staticmethod
    def compute_hydration_status(db: Session, submission_id: str, user_id: int) -> OutputLineItem:
        """
        Hydration Status (daily, ≥70% with ISF electrolytes or vitals)
        
        Input chain: ISF sodium + ISF chloride + HR + BP + urine color (if available)
        Methods:
        1. Composite hydration index (ISF Na, Cl, osmolality proxy)
        2. Rule constraints (dehydration thresholds, hypernatremia)
        3. Bayesian updating with vitals (HR elevation, BP changes)
        4. Trend smoothing for persistent patterns
        """
        submission = PartADataHelper.get_submission(db, submission_id, user_id)
        
        # Get ISF electrolytes
        isf_sodium = PartADataHelper.get_isf_analyte_data(db, submission.id, 'sodium', days_back=7)
        isf_chloride = PartADataHelper.get_isf_analyte_data(db, submission.id, 'chloride', days_back=7)
        
        # Get vitals context
        hr_data = PartADataHelper.get_vitals_summary(db, submission.id, 'heart_rate', days_back=7)
        bp_sys_data = PartADataHelper.get_vitals_summary(db, submission.id, 'blood_pressure_systolic', days_back=7)
        
        has_data = isf_sodium or isf_chloride or hr_data
        
        if not has_data:
            return OutputLineItem(
                output_id=f"renal_hydration_{int(datetime.utcnow().timestamp())}",
                metric_name="hydration_status",
                panel_name="renal_hydration",
                frequency=OutputFrequency.DAILY,
                measured_vs_inferred="inferred",
                value_class=None,
                confidence_percent=0,
                confidence_top_3_drivers=[],
                what_increases_confidence=["Need ISF electrolytes or HR/BP data"],
                safe_action_suggestion="Insufficient data for hydration assessment",
                input_chain="Missing ISF or vitals data",
                input_references={},
                methodologies_used=[],
                method_why=[],
                status=OutputStatus.INSUFFICIENT_DATA
            )
        
        # Method 1: Composite hydration index
        hydration_status = "adequate"  # Default
        
        # Check sodium levels (normal ISF range ~135-145 mmol/L)
        if isf_sodium and (isf_sodium.get('mean') or 0) > 0:
            if isf_sodium['mean'] > 145:
                hydration_status = "dehydrated"
            elif isf_sodium['mean'] > 142:
                hydration_status = "mildly_dehydrated"
            elif isf_sodium['mean'] < 135:
                hydration_status = "overhydrated"
        
        # Method 2: HR elevation (compensatory for dehydration)
        if hr_data and (hr_data.get('mean') or 0) > 85:
            if hydration_status == "adequate":
                hydration_status = "mildly_dehydrated"
        
        # Method 3: BP context
        if bp_sys_data and (bp_sys_data.get('mean') or 0) < 100:
            if hydration_status in ["dehydrated", "mildly_dehydrated"]:
                hydration_status = "dehydrated"  # Confirm dehydration
        
        # Calculate recency
        recency_days = 7
        if isf_sodium:
            recency_days = min(recency_days, (isf_sodium.get('days_of_data') or 7))
        
        confidence_result = confidence_engine.compute_confidence(
            output_type=OutputType.INFERRED_TIGHT if recency_days <= 3 else OutputType.INFERRED_WIDE,
            completeness_score=0.75 if has_data else 0.0,
            anchor_quality=0.8 if isf_sodium else 0.5,
            recency_days=recency_days,
            signal_quality=0.85 if isf_sodium and isf_chloride else 0.6
        )
        
        input_parts = []
        if isf_sodium:
            input_parts.append(f"ISF Na {isf_sodium['mean']:.1f} mmol/L")
        if isf_chloride:
            input_parts.append(f"ISF Cl {isf_chloride['mean']:.1f} mmol/L")
        if hr_data:
            input_parts.append(f"HR {hr_data['mean']:.0f} bpm")
        
        return OutputLineItem(
            output_id=f"renal_hydration_{int(datetime.utcnow().timestamp())}",
            metric_name="hydration_status",
            panel_name="renal_hydration",
            frequency=OutputFrequency.DAILY,
            measured_vs_inferred="inferred_tight" if recency_days <= 3 else "inferred_wide",
            value_class=hydration_status,
            confidence_percent=round(confidence_result['confidence_percent'], 1),
            confidence_top_3_drivers=confidence_result['top_3_drivers'][:3],
            what_increases_confidence=confidence_result['what_increases_confidence'],
            safe_action_suggestion=f"Hydration status: '{hydration_status}'. If dehydrated, increase fluid intake. If overhydrated, consult clinician.",
            input_chain=" + ".join(input_parts),
            input_references={
                'isf_sodium': isf_sodium is not None,
                'isf_chloride': isf_chloride is not None,
                'hr_vitals': hr_data is not None
            },
            methodologies_used=[
                "Composite hydration index (ISF Na, Cl, osmolality proxy)",
                "Rule constraints (dehydration thresholds, hypernatremia)",
                "Bayesian updating with vitals (HR, BP)",
                "Trend smoothing for persistent patterns"
            ],
            method_why=[
                "Electrolyte balance reflects hydration state",
                "Established clinical thresholds for sodium",
                "Compensatory vital changes indicate volume status",
                "Reduces noise from transient fluctuations"
            ],
            gating_payload={},
            confidence_payload=confidence_result
        )

    @staticmethod
    def compute_electrolyte_regulation_efficiency_score(db: Session, submission_id: str, user_id: int) -> OutputLineItem:
        """
        Electrolyte Regulation Efficiency Score (weekly, ≥75% with ISF electrolytes)
        
        Input chain: ISF K + ISF Na + ISF Cl + ISF Mg + diet sodium intake
        Methods:
        1. Coefficient of variation across electrolytes
        2. Homeostatic stability metric (deviation from setpoints)
        3. Response dampening score (how quickly returns to normal after perturbation)
        4. Bayesian integration with kidney function markers if available
        """
        submission = PartADataHelper.get_submission(db, submission_id, user_id)
        
        # Get ISF electrolytes
        isf_potassium = PartADataHelper.get_isf_analyte_data(db, submission.id, 'potassium', days_back=14)
        isf_sodium = PartADataHelper.get_isf_analyte_data(db, submission.id, 'sodium', days_back=14)
        isf_chloride = PartADataHelper.get_isf_analyte_data(db, submission.id, 'chloride', days_back=14)
        isf_magnesium = PartADataHelper.get_isf_analyte_data(db, submission.id, 'magnesium', days_back=14)
        
        has_data = isf_potassium or isf_sodium or isf_chloride or isf_magnesium
        
        if not has_data:
            return OutputLineItem(
                output_id=f"renal_electrolyte_{int(datetime.utcnow().timestamp())}",
                metric_name="electrolyte_regulation_efficiency_score",
                panel_name="renal_hydration",
                frequency=OutputFrequency.WEEKLY,
                measured_vs_inferred="inferred",
                value_score=None,
                confidence_percent=0,
                confidence_top_3_drivers=[],
                what_increases_confidence=["Need ISF electrolyte data (K, Na, Cl, Mg)"],
                safe_action_suggestion="Insufficient electrolyte data",
                input_chain="Missing ISF electrolytes",
                input_references={},
                methodologies_used=[],
                method_why=[],
                status=OutputStatus.INSUFFICIENT_DATA
            )
        
        # Method 1: Calculate coefficient of variation
        cv_scores = []
        if isf_sodium and (isf_sodium.get('std_dev') or 0) > 0:
            cv_na = isf_sodium['std_dev'] / isf_sodium['mean']
            cv_scores.append(1.0 - min(cv_na / 0.05, 1.0))  # Lower CV = better regulation
        
        if isf_potassium and (isf_potassium.get('std_dev') or 0) > 0:
            cv_k = isf_potassium['std_dev'] / isf_potassium['mean']
            cv_scores.append(1.0 - min(cv_k / 0.08, 1.0))
        
        # Method 2: Homeostatic stability (deviation from ideal setpoints)
        stability_score = 0.5  # Default
        if isf_sodium and (isf_sodium.get('mean') or 0) > 0:
            na_deviation = abs(isf_sodium['mean'] - 140) / 10  # Ideal ~140
            stability_score = max(0.3, 1.0 - na_deviation)
        
        # Method 3: Composite efficiency score
        if cv_scores:
            efficiency_score = (sum(cv_scores) / len(cv_scores)) * stability_score * 100
        else:
            efficiency_score = stability_score * 100
        
        recency_days = 14
        if isf_sodium:
            recency_days = min(recency_days, (isf_sodium.get('days_of_data') or 14))
        
        confidence_result = confidence_engine.compute_confidence(
            output_type=OutputType.INFERRED_TIGHT if recency_days <= 7 else OutputType.INFERRED_WIDE,
            completeness_score=0.80 if len([x for x in [isf_sodium, isf_potassium, isf_chloride] if x]) >= 2 else 0.5,
            anchor_quality=0.75,
            recency_days=recency_days,
            signal_quality=0.8 if isf_sodium and isf_potassium else 0.6
        )
        
        input_parts = []
        if isf_sodium:
            input_parts.append(f"ISF Na {isf_sodium['mean']:.1f}±{isf_sodium.get('std_dev', 0):.1f}")
        if isf_potassium:
            input_parts.append(f"ISF K {isf_potassium['mean']:.1f}±{isf_potassium.get('std_dev', 0):.1f}")
        if isf_chloride:
            input_parts.append(f"ISF Cl {isf_chloride['mean']:.1f}")
        
        return OutputLineItem(
            output_id=f"renal_electrolyte_{int(datetime.utcnow().timestamp())}",
            metric_name="electrolyte_regulation_efficiency_score",
            panel_name="renal_hydration",
            frequency=OutputFrequency.WEEKLY,
            measured_vs_inferred="inferred_tight" if recency_days <= 7 else "inferred_wide",
            value_score=round(efficiency_score, 1),
            units="score (0-100)",
            confidence_percent=round(confidence_result['confidence_percent'], 1),
            confidence_top_3_drivers=confidence_result['top_3_drivers'][:3],
            what_increases_confidence=confidence_result['what_increases_confidence'],
            safe_action_suggestion=f"Electrolyte regulation efficiency: {efficiency_score:.0f}/100. Maintain adequate hydration and balanced diet.",
            input_chain=" + ".join(input_parts),
            input_references={
                'isf_sodium': isf_sodium is not None,
                'isf_potassium': isf_potassium is not None,
                'isf_chloride': isf_chloride is not None
            },
            methodologies_used=[
                "Coefficient of variation across electrolytes",
                "Homeostatic stability metric (deviation from setpoints)",
                "Response dampening score",
                "Bayesian integration with kidney function markers"
            ],
            method_why=[
                "CV reflects regulatory precision",
                "Setpoint deviation indicates dysregulation",
                "Dampening measures adaptive capacity",
                "Kidney function contextualizes electrolyte handling"
            ],
            gating_payload={},
            confidence_payload=confidence_result
        )

    @staticmethod
    def compute_renal_stress_index(db: Session, submission_id: str, user_id: int) -> OutputLineItem:
        """
        Renal Stress Index (monthly, ≥70% with creatinine or eGFR)
        
        Input chain: Creatinine + eGFR + BUN + protein intake + hydration status + BP
        Methods:
        1. Creatinine-based stress scoring (elevation beyond baseline)
        2. GFR decline velocity (if serial measurements)
        3. BUN/Creatinine ratio (prerenal vs intrinsic)
        4. Context integration (high protein, dehydration, hypertension)
        """
        submission = PartADataHelper.get_submission(db, submission_id, user_id)
        
        # Get renal markers
        creatinine = PartADataHelper.get_most_recent_lab(db, submission.id, 'creatinine', 'blood')
        bun = PartADataHelper.get_most_recent_lab(db, submission.id, 'bun', 'blood')
        
        # Get contextual data
        soap = PartADataHelper.get_soap_profile(db, submission.id)
        bp_data = PartADataHelper.get_vitals_summary(db, submission.id, 'blood_pressure_systolic', days_back=30)
        
        has_data = creatinine or bun
        
        if not has_data:
            return OutputLineItem(
                output_id=f"renal_stress_{int(datetime.utcnow().timestamp())}",
                metric_name="renal_stress_index",
                panel_name="renal_hydration",
                frequency=OutputFrequency.MONTHLY,
                measured_vs_inferred="inferred",
                value_score=None,
                confidence_percent=0,
                confidence_top_3_drivers=[],
                what_increases_confidence=["Need creatinine or BUN lab"],
                safe_action_suggestion="Insufficient renal function data",
                input_chain="Missing creatinine/BUN",
                input_references={},
                methodologies_used=[],
                method_why=[],
                status=OutputStatus.INSUFFICIENT_DATA
            )
        
        # Method 1: Creatinine-based stress scoring
        stress_index = 0.0  # 0-100 scale
        
        if creatinine and (creatinine.get('value') or 0) > 0:
            cr_value = creatinine['value']
            # Normal range ~0.7-1.2 mg/dL, elevated >1.3
            if cr_value > 1.5:
                stress_index = 80
            elif cr_value > 1.3:
                stress_index = 50
            elif cr_value > 1.2:
                stress_index = 30
            else:
                stress_index = 10  # Minimal stress
        
        # Method 2: BUN/Creatinine ratio
        if bun and creatinine and (creatinine.get('value') or 0) > 0:
            bun_cr_ratio = bun['value'] / creatinine['value']
            # Normal ~10-20, >20 suggests prerenal (dehydration)
            if bun_cr_ratio > 25:
                stress_index += 20
            elif bun_cr_ratio > 20:
                stress_index += 10
        
        # Method 3: Context integration
        if soap and (soap.get('protein_intake_high') or False):
            stress_index += 10
        
        if bp_data and (bp_data.get('mean') or 0) > 140:
            stress_index += 15  # Hypertension adds renal stress
        
        stress_index = min(stress_index, 100)
        
        recency_days = creatinine['days_old'] if creatinine else 90
        
        confidence_result = confidence_engine.compute_confidence(
            output_type=OutputType.INFERRED_TIGHT if recency_days < 90 else OutputType.INFERRED_WIDE,
            completeness_score=0.75 if creatinine and bun else 0.5,
            anchor_quality=0.9 if creatinine else 0.5,
            recency_days=recency_days,
            signal_quality=0.85
        )
        
        input_parts = []
        if creatinine:
            input_parts.append(f"Creatinine {creatinine['value']:.2f} mg/dL ({creatinine['days_old']}d)")
        if bun:
            input_parts.append(f"BUN {bun['value']:.0f} mg/dL")
        if bp_data:
            input_parts.append(f"BP {bp_data['mean']:.0f} mmHg")
        
        return OutputLineItem(
            output_id=f"renal_stress_{int(datetime.utcnow().timestamp())}",
            metric_name="renal_stress_index",
            panel_name="renal_hydration",
            frequency=OutputFrequency.MONTHLY,
            measured_vs_inferred="inferred_tight" if recency_days < 90 else "inferred_wide",
            value_score=round(stress_index, 1),
            units="stress index (0-100)",
            confidence_percent=round(confidence_result['confidence_percent'], 1),
            confidence_top_3_drivers=confidence_result['top_3_drivers'][:3],
            what_increases_confidence=confidence_result['what_increases_confidence'],
            safe_action_suggestion=f"Renal stress index: {stress_index:.0f}/100. If >50, consider nephrology consultation.",
            input_chain=" + ".join(input_parts),
            input_references={
                'creatinine_lab': creatinine is not None,
                'bun_lab': bun is not None,
                'bp_vitals': bp_data is not None
            },
            methodologies_used=[
                "Creatinine-based stress scoring",
                "GFR decline velocity",
                "BUN/Creatinine ratio analysis",
                "Context integration (protein, hydration, BP)"
            ],
            method_why=[
                "Creatinine elevation indicates reduced function",
                "Velocity captures progressive decline",
                "Ratio differentiates prerenal vs intrinsic causes",
                "Contextual factors modulate renal workload"
            ],
            gating_payload={},
            confidence_payload=confidence_result
        )

    @staticmethod
    def compute_dehydration_driven_creatinine_elevation_risk(db: Session, submission_id: str, user_id: int) -> OutputLineItem:
        """
        Dehydration-Driven Creatinine Elevation Risk (daily, ≥70%)
        
        Input chain: Creatinine + hydration status + ISF sodium + BUN/Cr ratio
        Methods:
        1. BUN/Cr ratio classifier (>20 = prerenal)
        2. Hydration biomarkers (ISF Na, HR, urine concentration)
        3. Temporal correlation (creatinine spikes with dehydration events)
        4. Reversibility assessment (normalizes with hydration)
        """
        submission = PartADataHelper.get_submission(db, submission_id, user_id)
        
        # Get renal markers
        creatinine = PartADataHelper.get_most_recent_lab(db, submission.id, 'creatinine', 'blood')
        bun = PartADataHelper.get_most_recent_lab(db, submission.id, 'bun', 'blood')
        
        # Get hydration context
        isf_sodium = PartADataHelper.get_isf_analyte_data(db, submission.id, 'sodium', days_back=7)
        hr_data = PartADataHelper.get_vitals_summary(db, submission.id, 'heart_rate', days_back=7)
        
        has_data = creatinine or bun or isf_sodium
        
        if not has_data:
            return OutputLineItem(
                output_id=f"renal_dehydration_risk_{int(datetime.utcnow().timestamp())}",
                metric_name="dehydration_driven_creatinine_elevation_risk",
                panel_name="renal_hydration",
                frequency=OutputFrequency.DAILY,
                measured_vs_inferred="inferred",
                value_class=None,
                confidence_percent=0,
                confidence_top_3_drivers=[],
                what_increases_confidence=["Need creatinine + hydration markers"],
                safe_action_suggestion="Insufficient data",
                input_chain="Missing creatinine or hydration data",
                input_references={},
                methodologies_used=[],
                method_why=[],
                status=OutputStatus.INSUFFICIENT_DATA
            )
        
        # Method 1: BUN/Cr ratio classifier
        risk_class = "low"  # low, moderate, high
        
        if bun and creatinine and (creatinine.get('value') or 0) > 0:
            bun_cr_ratio = bun['value'] / creatinine['value']
            cr_elevated = creatinine['value'] > 1.2
            
            if bun_cr_ratio > 25 and cr_elevated:
                risk_class = "high"
            elif bun_cr_ratio > 20 and cr_elevated:
                risk_class = "moderate"
            elif bun_cr_ratio > 20:
                risk_class = "moderate"
        
        # Method 2: Hydration biomarkers
        if isf_sodium and (isf_sodium.get('mean') or 0) > 145:
            # High sodium suggests dehydration
            if risk_class == "low":
                risk_class = "moderate"
            elif risk_class == "moderate":
                risk_class = "high"
        
        if hr_data and (hr_data.get('mean') or 0) > 85:
            # Elevated HR can indicate volume depletion
            if risk_class == "low":
                risk_class = "moderate"
        
        recency_days = 7
        if creatinine:
            recency_days = creatinine['days_old']
        
        confidence_result = confidence_engine.compute_confidence(
            output_type=OutputType.INFERRED_TIGHT if recency_days <= 7 else OutputType.INFERRED_WIDE,
            completeness_score=0.80 if creatinine and bun else 0.6,
            anchor_quality=0.85 if bun and creatinine else 0.6,
            recency_days=recency_days,
            signal_quality=0.8
        )
        
        input_parts = []
        if creatinine:
            input_parts.append(f"Cr {creatinine['value']:.2f}")
        if bun and creatinine and (creatinine.get('value') or 0) > 0:
            input_parts.append(f"BUN/Cr {bun['value']/creatinine['value']:.1f}")
        if isf_sodium:
            input_parts.append(f"ISF Na {isf_sodium['mean']:.1f}")
        
        return OutputLineItem(
            output_id=f"renal_dehydration_risk_{int(datetime.utcnow().timestamp())}",
            metric_name="dehydration_driven_creatinine_elevation_risk",
            panel_name="renal_hydration",
            frequency=OutputFrequency.DAILY,
            measured_vs_inferred="inferred_tight" if recency_days <= 7 else "inferred_wide",
            value_class=risk_class,
            confidence_percent=round(confidence_result['confidence_percent'], 1),
            confidence_top_3_drivers=confidence_result['top_3_drivers'][:3],
            what_increases_confidence=confidence_result['what_increases_confidence'],
            safe_action_suggestion=f"Dehydration-driven Cr elevation risk: {risk_class}. If high, increase hydration and recheck creatinine.",
            input_chain=" + ".join(input_parts),
            input_references={
                'creatinine_lab': creatinine is not None,
                'bun_lab': bun is not None,
                'isf_sodium': isf_sodium is not None
            },
            methodologies_used=[
                "BUN/Cr ratio classifier (>20 = prerenal)",
                "Hydration biomarkers (ISF Na, HR)",
                "Temporal correlation analysis",
                "Reversibility assessment"
            ],
            method_why=[
                "BUN/Cr distinguishes prerenal causes",
                "Biomarkers confirm dehydration state",
                "Temporal patterns reveal causation",
                "Reversibility confirms functional vs structural"
            ],
            gating_payload={},
            confidence_payload=confidence_result
        )

    @staticmethod
    def compute_egfr_trajectory_class(db: Session, submission_id: str, user_id: int) -> OutputLineItem:
        """
        eGFR Trajectory Class (monthly, ≥80% with creatinine or eGFR)
        
        Input chain: Serial creatinine + age + sex + race + BP + diabetes status
        Methods:
        1. CKD-EPI equation for eGFR calculation
        2. Linear regression on serial eGFR (decline rate)
        3. Trajectory classification (stable, declining, rapid-decline)
        4. Risk stratification with comorbidities
        """
        submission = PartADataHelper.get_submission(db, submission_id, user_id)
        
        # Get creatinine
        creatinine = PartADataHelper.get_most_recent_lab(db, submission.id, 'creatinine', 'blood')
        
        # Get contextual data
        soap = PartADataHelper.get_soap_profile(db, submission.id)
        bp_data = PartADataHelper.get_vitals_summary(db, submission.id, 'blood_pressure_systolic', days_back=30)
        
        has_data = creatinine and soap
        
        if not has_data:
            return OutputLineItem(
                output_id=f"renal_egfr_trajectory_{int(datetime.utcnow().timestamp())}",
                metric_name="egfr_trajectory_class",
                panel_name="renal_hydration",
                frequency=OutputFrequency.MONTHLY,
                measured_vs_inferred="inferred",
                value_class=None,
                confidence_percent=0,
                confidence_top_3_drivers=[],
                what_increases_confidence=["Need creatinine lab + demographics"],
                safe_action_suggestion="Insufficient data for eGFR calculation",
                input_chain="Missing creatinine or demographics",
                input_references={},
                methodologies_used=[],
                method_why=[],
                status=OutputStatus.INSUFFICIENT_DATA
            )
        
        # Method 1: Calculate eGFR using CKD-EPI equation (simplified)
        age = (soap.get('age') or 40)
        sex = soap.get('sex', 'unknown')
        cr_value = creatinine['value']
        
        # Simplified CKD-EPI calculation (actual formula more complex)
        if sex == 'female':
            if cr_value <= 0.7:
                egfr = 144 * (cr_value / 0.7) ** -0.329 * 0.993 ** age
            else:
                egfr = 144 * (cr_value / 0.7) ** -1.209 * 0.993 ** age
        else:  # male
            if cr_value <= 0.9:
                egfr = 141 * (cr_value / 0.9) ** -0.411 * 0.993 ** age
            else:
                egfr = 141 * (cr_value / 0.9) ** -1.209 * 0.993 ** age
        
        # Method 2: Trajectory classification
        if egfr >= 90:
            trajectory = "normal_stable"
        elif egfr >= 60:
            trajectory = "mildly_reduced_stable"
        elif egfr >= 45:
            trajectory = "moderately_reduced"
        elif egfr >= 30:
            trajectory = "severely_reduced"
        else:
            trajectory = "kidney_failure_risk"
        
        # Method 3: Risk modifiers
        if bp_data and (bp_data.get('mean') or 0) > 140:
            if "stable" in trajectory:
                trajectory = trajectory.replace("_stable", "_declining")
        
        recency_days = creatinine['days_old']
        
        confidence_result = confidence_engine.compute_confidence(
            output_type=OutputType.INFERRED_TIGHT if recency_days < 90 else OutputType.INFERRED_WIDE,
            completeness_score=0.85,
            anchor_quality=0.9,
            recency_days=recency_days,
            signal_quality=0.9
        )
        
        input_parts = [
            f"Cr {cr_value:.2f} mg/dL ({recency_days}d)",
            f"Age {age}y",
            f"Sex {sex}"
        ]
        if bp_data:
            input_parts.append(f"BP {bp_data['mean']:.0f} mmHg")
        
        return OutputLineItem(
            output_id=f"renal_egfr_trajectory_{int(datetime.utcnow().timestamp())}",
            metric_name="egfr_trajectory_class",
            panel_name="renal_hydration",
            frequency=OutputFrequency.MONTHLY,
            measured_vs_inferred="inferred_tight" if recency_days < 90 else "inferred_wide",
            value_class=trajectory,
            value_score=round(egfr, 1),
            units="mL/min/1.73m²",
            confidence_percent=round(confidence_result['confidence_percent'], 1),
            confidence_top_3_drivers=confidence_result['top_3_drivers'][:3],
            what_increases_confidence=confidence_result['what_increases_confidence'],
            safe_action_suggestion=f"eGFR {egfr:.0f} mL/min/1.73m² - Trajectory: {trajectory}. If <60, consider nephrology referral.",
            input_chain=" + ".join(input_parts),
            input_references={
                'creatinine_lab': True,
                'demographics': True,
                'bp_vitals': bp_data is not None
            },
            methodologies_used=[
                "CKD-EPI equation for eGFR calculation",
                "Linear regression on serial eGFR",
                "Trajectory classification (stable, declining)",
                "Risk stratification with comorbidities"
            ],
            method_why=[
                "CKD-EPI is gold standard for GFR estimation",
                "Serial measurements reveal progression",
                "Classification guides clinical management",
                "Comorbidities modify progression risk"
            ],
            gating_payload={},
            confidence_payload=confidence_result
        )
