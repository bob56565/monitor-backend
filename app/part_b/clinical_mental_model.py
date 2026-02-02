"""
Part 2: Clinical Mental Model & Lab-Analog Communication Layer
SOURCE OF TRUTH: ISSUES AND IMPROVEMENTS.txt + PART 2 SCHEMA

This module defines the clinical explanation framework for all 35 Part B outputs.
Every metric must be communicated like a lab report, not a database.

Core Principle: Lab-Analog Estimation
- Outputs are inferred states derived from partial biomarkers, physiologic constraints,
  priors, and temporal coherence.
- This is clinically legitimate if framed identically to existing derived lab practices
  (e.g., calculated LDL, eGFR from creatinine, A1c as estimated average glucose).
- NULL is never acceptable if confidence > 0.
"""

from typing import Dict, List, Tuple, Optional, Literal
from pydantic import BaseModel, Field
from enum import Enum


class AnalogType(str, Enum):
    """Type of clinical analog."""
    TRUE_LAB_ANALOG = "true_lab_analog"  # Direct correspondence to serum test
    CLINICIAN_SYNTHESIS_ANALOG = "clinician_synthesis_analog"  # Integrative assessment


class LabAnalogExplanation(BaseModel):
    """
    Lab-Analog Explanation Block (MANDATORY for every metric).
    
    Structure mirrors how clinicians explain indirect or calculated results.
    """
    what_this_represents: str = Field(
        ...,
        description="Explicitly state: estimated, inferred, not a direct draw"
    )
    lab_correspondence: str = Field(
        ...,
        description="Closest serum analyte and approximate range"
    )
    why_we_believe_this: List[str] = Field(
        ...,
        min_length=2,
        max_length=4,
        description="2-4 physiologic drivers max"
    )
    confidence_level: str = Field(
        ...,
        description="Moderate / Moderate-High / High, bounded phrasing"
    )
    what_would_tighten_estimate: str = Field(
        ...,
        description="Single blood test that would improve precision"
    )
    safety_language: str = Field(
        default="This is an estimate, not a diagnostic value. Interpret in clinical context with your healthcare provider.",
        description="Non-diagnostic safety disclaimer"
    )
    analog_type: AnalogType = Field(
        ...,
        description="True Lab Analog or Clinician-Synthesis Analog"
    )


class MetricDefinition(BaseModel):
    """
    Complete definition for one of the 35 Part B metrics.
    Includes clinical framing, lab correspondence, and presentation rules.
    """
    metric_id: str = Field(..., description="Unique metric identifier (snake_case)")
    domain: Literal[
        "Metabolic Regulation",
        "Lipid + Cardiometabolic",
        "Micronutrient + Vitamin",
        "Inflammatory + Immune",
        "Endocrine + Neurohormonal",
        "Renal + Hydration",
        "Comprehensive + Integrated"
    ]
    display_name: str = Field(..., description="User-facing metric name")
    lab_analog: str = Field(..., description="Closest clinical lab equivalent")
    where_seen: str = Field(
        ...,
        description="Where this would appear in clinical practice"
    )
    stands_in_for: str = Field(
        ...,
        description="What lab result(s) this estimates"
    )
    analog_type: AnalogType
    value_type: Literal["range", "score", "probability", "class"] = Field(
        ...,
        description="How value is presented"
    )
    typical_units: Optional[str] = Field(
        None,
        description="Units if applicable"
    )
    null_replacement_strategy: str = Field(
        ...,
        description="How to handle low-confidence estimates (never show NULL)"
    )


# ============================================================================
# COMPLETE 35-METRIC DEFINITION REGISTRY
# ============================================================================

METRIC_REGISTRY: Dict[str, MetricDefinition] = {
    # ========== METABOLIC REGULATION (5 metrics) ==========
    "estimated_hba1c_range": MetricDefinition(
        metric_id="estimated_hba1c_range",
        domain="Metabolic Regulation",
        display_name="Estimated HbA1c Range",
        lab_analog="Hemoglobin A1c (%)",
        where_seen="Annual physical labs, diabetes screening panels",
        stands_in_for="Lab-like A1c % range (optional eAG mapping)",
        analog_type=AnalogType.TRUE_LAB_ANALOG,
        value_type="range",
        typical_units="%",
        null_replacement_strategy="Show wide bounded range (e.g., 5.0-6.0%) with 'Low confidence' label"
    ),
    
    "insulin_resistance_probability": MetricDefinition(
        metric_id="insulin_resistance_probability",
        domain="Metabolic Regulation",
        display_name="Insulin Resistance Probability",
        lab_analog="HOMA-IR (fasting insulin + glucose)",
        where_seen="Metabolic clinics, IR workups",
        stands_in_for="Probability HOMA-IR would be elevated",
        analog_type=AnalogType.TRUE_LAB_ANALOG,
        value_type="probability",
        typical_units="%",
        null_replacement_strategy="Show probability with wide confidence interval"
    ),
    
    "metabolic_flexibility_score": MetricDefinition(
        metric_id="metabolic_flexibility_score",
        domain="Metabolic Regulation",
        display_name="Metabolic Flexibility Score",
        lab_analog="OGTT dynamics + lactate response",
        where_seen="Sports performance, endocrinology",
        stands_in_for="Fuel-switching efficiency proxy",
        analog_type=AnalogType.CLINICIAN_SYNTHESIS_ANALOG,
        value_type="score",
        typical_units="/100",
        null_replacement_strategy="Show score with 'Moderate-Low confidence' grade"
    ),
    
    "postprandial_dysregulation_phenotype": MetricDefinition(
        metric_id="postprandial_dysregulation_phenotype",
        domain="Metabolic Regulation",
        display_name="Postprandial Dysregulation Phenotype",
        lab_analog="OGTT curve + CGM-like excursions",
        where_seen="Prediabetes prevention, CGM reports",
        stands_in_for="Curve phenotype classification",
        analog_type=AnalogType.CLINICIAN_SYNTHESIS_ANALOG,
        value_type="class",
        typical_units=None,
        null_replacement_strategy="Show 'Insufficient postprandial data' with data improvement pathway"
    ),
    
    "prediabetes_trajectory_class": MetricDefinition(
        metric_id="prediabetes_trajectory_class",
        domain="Metabolic Regulation",
        display_name="Prediabetes Trajectory Class",
        lab_analog="HbA1c + fasting glucose trend",
        where_seen="Primary care longitudinal charts",
        stands_in_for="Risk trajectory classification",
        analog_type=AnalogType.CLINICIAN_SYNTHESIS_ANALOG,
        value_type="class",
        typical_units=None,
        null_replacement_strategy="Show 'Insufficient longitudinal data' with minimum requirements"
    ),
    
    # ========== LIPID + CARDIOMETABOLIC (6 metrics) ==========
    "ldl_pattern_risk_proxy": MetricDefinition(
        metric_id="ldl_pattern_risk_proxy",
        domain="Lipid + Cardiometabolic",
        display_name="LDL Pattern Risk Proxy",
        lab_analog="Calculated LDL-C (Friedewald equation)",
        where_seen="Standard lipid panels",
        stands_in_for="LDL cholesterol estimate (Pattern A vs B inference)",
        analog_type=AnalogType.TRUE_LAB_ANALOG,
        value_type="range",
        typical_units="mg/dL",
        null_replacement_strategy="Show wide range with population priors (e.g., 100-140 mg/dL)"
    ),
    
    "hdl_functional_likelihood": MetricDefinition(
        metric_id="hdl_functional_likelihood",
        domain="Lipid + Cardiometabolic",
        display_name="HDL Functional Likelihood",
        lab_analog="HDL-C + HDL particle count",
        where_seen="Advanced lipid panels",
        stands_in_for="HDL cholesterol + functional capacity estimate",
        analog_type=AnalogType.TRUE_LAB_ANALOG,
        value_type="range",
        typical_units="mg/dL",
        null_replacement_strategy="Show range with population 50th percentile anchor"
    ),
    
    "triglyceride_elevation_probability": MetricDefinition(
        metric_id="triglyceride_elevation_probability",
        domain="Lipid + Cardiometabolic",
        display_name="Triglyceride Elevation Probability",
        lab_analog="Fasting triglycerides",
        where_seen="Lipid panels, metabolic syndrome workup",
        stands_in_for="Probability TG > 150 mg/dL",
        analog_type=AnalogType.TRUE_LAB_ANALOG,
        value_type="probability",
        typical_units="%",
        null_replacement_strategy="Show probability with wide interval based on glucose patterns"
    ),
    
    "atherogenic_risk_phenotype": MetricDefinition(
        metric_id="atherogenic_risk_phenotype",
        domain="Lipid + Cardiometabolic",
        display_name="Atherogenic Risk Phenotype",
        lab_analog="Non-HDL-C, Apo B, LDL particle count",
        where_seen="Cardiovascular risk assessments",
        stands_in_for="Atherogenic lipoprotein burden classification",
        analog_type=AnalogType.CLINICIAN_SYNTHESIS_ANALOG,
        value_type="class",
        typical_units=None,
        null_replacement_strategy="Show 'Moderate-risk assumed' with confidence drivers"
    ),
    
    "cardiometabolic_risk_score": MetricDefinition(
        metric_id="cardiometabolic_risk_score",
        domain="Lipid + Cardiometabolic",
        display_name="Cardiometabolic Risk Score",
        lab_analog="Framingham-style risk score",
        where_seen="Primary care prevention",
        stands_in_for="Integrated CV + metabolic risk",
        analog_type=AnalogType.CLINICIAN_SYNTHESIS_ANALOG,
        value_type="score",
        typical_units="/100",
        null_replacement_strategy="Show score with age/BP/glucose anchors"
    ),
    
    "metabolic_inflammatory_coupling_index": MetricDefinition(
        metric_id="metabolic_inflammatory_coupling_index",
        domain="Lipid + Cardiometabolic",
        display_name="Metabolic-Inflammatory Coupling Index",
        lab_analog="HbA1c + hs-CRP interaction",
        where_seen="Integrative medicine, metabolic-immune research",
        stands_in_for="Metabolic dysfunction amplifying inflammation",
        analog_type=AnalogType.CLINICIAN_SYNTHESIS_ANALOG,
        value_type="score",
        typical_units="/100",
        null_replacement_strategy="Show score with drivers: glucose volatility + autonomic stress"
    ),
    
    # ========== MICRONUTRIENT + VITAMIN (5 metrics) ==========
    "vitamin_d_sufficiency_likelihood": MetricDefinition(
        metric_id="vitamin_d_sufficiency_likelihood",
        domain="Micronutrient + Vitamin",
        display_name="Vitamin D Sufficiency Likelihood",
        lab_analog="Serum 25-OH Vitamin D",
        where_seen="Annual wellness labs, bone health workups",
        stands_in_for="Estimated 25-OH D range (ng/mL)",
        analog_type=AnalogType.TRUE_LAB_ANALOG,
        value_type="range",
        typical_units="ng/mL",
        null_replacement_strategy="Show wide range (20-35 ng/mL) with sun/supplement signals"
    ),
    
    "b12_functional_adequacy_score": MetricDefinition(
        metric_id="b12_functional_adequacy_score",
        domain="Micronutrient + Vitamin",
        display_name="B12 Functional Adequacy Score",
        lab_analog="Serum B12 + methylmalonic acid (MMA)",
        where_seen="Fatigue workups, vegan/vegetarian monitoring",
        stands_in_for="B12 functional status (serum + metabolite proxy)",
        analog_type=AnalogType.TRUE_LAB_ANALOG,
        value_type="score",
        typical_units="/100",
        null_replacement_strategy="Show score with diet pattern + fatigue signal anchors"
    ),
    
    "iron_utilization_status_class": MetricDefinition(
        metric_id="iron_utilization_status_class",
        domain="Micronutrient + Vitamin",
        display_name="Iron Utilization Status Class",
        lab_analog="Ferritin + TIBC + transferrin saturation",
        where_seen="Anemia workups, endurance athlete monitoring",
        stands_in_for="Iron stores + utilization classification",
        analog_type=AnalogType.TRUE_LAB_ANALOG,
        value_type="class",
        typical_units=None,
        null_replacement_strategy="Show 'Replete assumed' with dietary intake confidence"
    ),
    
    "magnesium_adequacy_proxy": MetricDefinition(
        metric_id="magnesium_adequacy_proxy",
        domain="Micronutrient + Vitamin",
        display_name="Magnesium Adequacy Proxy",
        lab_analog="Serum magnesium (RBC magnesium if available)",
        where_seen="Muscle cramps, cardiac arrhythmia workups",
        stands_in_for="Magnesium status estimate",
        analog_type=AnalogType.TRUE_LAB_ANALOG,
        value_type="range",
        typical_units="mg/dL",
        null_replacement_strategy="Show range (1.8-2.2 mg/dL) with dietary + symptom signals"
    ),
    
    "micronutrient_risk_summary": MetricDefinition(
        metric_id="micronutrient_risk_summary",
        domain="Micronutrient + Vitamin",
        display_name="Micronutrient Risk Summary",
        lab_analog="Multi-micronutrient panel synthesis",
        where_seen="Integrative medicine, nutrition optimization",
        stands_in_for="Aggregate micronutrient deficiency risk",
        analog_type=AnalogType.CLINICIAN_SYNTHESIS_ANALOG,
        value_type="class",
        typical_units=None,
        null_replacement_strategy="Show 'Low-Moderate risk' with diet diversity score"
    ),
    
    # ========== INFLAMMATORY + IMMUNE (5 metrics) ==========
    "chronic_inflammation_index": MetricDefinition(
        metric_id="chronic_inflammation_index",
        domain="Inflammatory + Immune",
        display_name="Chronic Inflammation Index",
        lab_analog="hs-CRP (high-sensitivity C-reactive protein)",
        where_seen="CV risk panels, inflammatory disease monitoring",
        stands_in_for="Estimated hs-CRP range (mg/L)",
        analog_type=AnalogType.TRUE_LAB_ANALOG,
        value_type="range",
        typical_units="mg/L",
        null_replacement_strategy="Show wide range (1.0-3.0 mg/L) with HRV + recovery signals"
    ),
    
    "acute_vs_chronic_pattern_classifier": MetricDefinition(
        metric_id="acute_vs_chronic_pattern_classifier",
        domain="Inflammatory + Immune",
        display_name="Acute vs Chronic Pattern Classifier",
        lab_analog="CRP + ESR + CBC pattern analysis",
        where_seen="Inflammatory disease differential diagnosis",
        stands_in_for="Acute spike vs chronic elevation classification",
        analog_type=AnalogType.CLINICIAN_SYNTHESIS_ANALOG,
        value_type="class",
        typical_units=None,
        null_replacement_strategy="Show 'Chronic low-grade assumed' with temporal pattern"
    ),
    
    "inflammation_driven_ir_modifier": MetricDefinition(
        metric_id="inflammation_driven_ir_modifier",
        domain="Inflammatory + Immune",
        display_name="Inflammation-Driven IR Modifier",
        lab_analog="hs-CRP × HOMA-IR interaction",
        where_seen="Metabolic-immune research, integrative medicine",
        stands_in_for="How inflammation amplifies insulin resistance",
        analog_type=AnalogType.CLINICIAN_SYNTHESIS_ANALOG,
        value_type="score",
        typical_units="/100",
        null_replacement_strategy="Show score with glucose variability + autonomic drivers"
    ),
    
    "cardio_inflammatory_coupling_index": MetricDefinition(
        metric_id="cardio_inflammatory_coupling_index",
        domain="Inflammatory + Immune",
        display_name="Cardio-Inflammatory Coupling Index",
        lab_analog="hs-CRP + HRV + BP variability",
        where_seen="Cardiovascular-inflammatory research",
        stands_in_for="Inflammatory burden affecting cardiac autonomic regulation",
        analog_type=AnalogType.CLINICIAN_SYNTHESIS_ANALOG,
        value_type="score",
        typical_units="/100",
        null_replacement_strategy="Show score with HRV + BP + recovery signals"
    ),
    
    "recovery_capacity_score": MetricDefinition(
        metric_id="recovery_capacity_score",
        domain="Inflammatory + Immune",
        display_name="Recovery Capacity Score",
        lab_analog="HRV recovery + lactate clearance + sleep efficiency",
        where_seen="Sports medicine, overtraining assessments",
        stands_in_for="Physiologic recovery efficiency",
        analog_type=AnalogType.CLINICIAN_SYNTHESIS_ANALOG,
        value_type="score",
        typical_units="/100",
        null_replacement_strategy="Show score with sleep + HRV baseline drivers"
    ),
    
    # ========== ENDOCRINE + NEUROHORMONAL (6 metrics) ==========
    "cortisol_rhythm_integrity_score": MetricDefinition(
        metric_id="cortisol_rhythm_integrity_score",
        domain="Endocrine + Neurohormonal",
        display_name="Cortisol Rhythm Integrity Score",
        lab_analog="4-point salivary cortisol curve",
        where_seen="Adrenal fatigue workups, functional medicine",
        stands_in_for="Cortisol diurnal rhythm quality",
        analog_type=AnalogType.TRUE_LAB_ANALOG,
        value_type="score",
        typical_units="/100",
        null_replacement_strategy="Show score with HRV circadian + glucose pattern drivers"
    ),
    
    "thyroid_functional_pattern": MetricDefinition(
        metric_id="thyroid_functional_pattern",
        domain="Endocrine + Neurohormonal",
        display_name="Thyroid Functional Pattern",
        lab_analog="TSH + Free T3/T4 pattern analysis",
        where_seen="Thyroid workups, metabolic clinics",
        stands_in_for="Thyroid function classification (euthyroid/subclinical hypo/hyper)",
        analog_type=AnalogType.TRUE_LAB_ANALOG,
        value_type="class",
        typical_units=None,
        null_replacement_strategy="Show 'Euthyroid assumed' with basal metabolic rate signals"
    ),
    
    "autonomic_status": MetricDefinition(
        metric_id="autonomic_status",
        domain="Endocrine + Neurohormonal",
        display_name="Autonomic Status",
        lab_analog="HRV + orthostatic vitals + Valsalva maneuver",
        where_seen="Neurology, cardiology, sports medicine",
        stands_in_for="Autonomic nervous system balance (sympathetic vs parasympathetic)",
        analog_type=AnalogType.CLINICIAN_SYNTHESIS_ANALOG,
        value_type="class",
        typical_units=None,
        null_replacement_strategy="Show 'Balanced' with HRV + resting HR drivers"
    ),
    
    "sympathetic_dominance_index": MetricDefinition(
        metric_id="sympathetic_dominance_index",
        domain="Endocrine + Neurohormonal",
        display_name="Sympathetic Dominance Index",
        lab_analog="HRV LF/HF ratio + resting HR + BP",
        where_seen="Stress physiology, performance optimization",
        stands_in_for="Degree of sympathetic nervous system activation",
        analog_type=AnalogType.CLINICIAN_SYNTHESIS_ANALOG,
        value_type="score",
        typical_units="/100",
        null_replacement_strategy="Show score with resting HR + HRV RMSSD baseline"
    ),
    
    "stress_adaptation_vs_maladaptation_classifier": MetricDefinition(
        metric_id="stress_adaptation_vs_maladaptation_classifier",
        domain="Endocrine + Neurohormonal",
        display_name="Stress Adaptation vs Maladaptation Classifier",
        lab_analog="Cortisol + HRV + sleep + recovery patterns",
        where_seen="Functional medicine, burnout assessments",
        stands_in_for="Adaptive vs maladaptive stress response classification",
        analog_type=AnalogType.CLINICIAN_SYNTHESIS_ANALOG,
        value_type="class",
        typical_units=None,
        null_replacement_strategy="Show 'Adaptive' with recovery + sleep quality drivers"
    ),
    
    "burnout_risk_trajectory": MetricDefinition(
        metric_id="burnout_risk_trajectory",
        domain="Endocrine + Neurohormonal",
        display_name="Burnout Risk Trajectory",
        lab_analog="Cortisol dysregulation + HRV suppression + sleep debt",
        where_seen="Occupational health, executive wellness",
        stands_in_for="Physiologic burnout trajectory classification",
        analog_type=AnalogType.CLINICIAN_SYNTHESIS_ANALOG,
        value_type="class",
        typical_units=None,
        null_replacement_strategy="Show 'Low-Moderate risk' with stress load estimates"
    ),
    
    # ========== RENAL + HYDRATION (5 metrics) ==========
    "hydration_status": MetricDefinition(
        metric_id="hydration_status",
        domain="Renal + Hydration",
        display_name="Hydration Status",
        lab_analog="Urine specific gravity + serum osmolality",
        where_seen="Emergency medicine, sports medicine",
        stands_in_for="Hydration adequacy classification",
        analog_type=AnalogType.TRUE_LAB_ANALOG,
        value_type="class",
        typical_units=None,
        null_replacement_strategy="Show 'Adequate' with fluid intake + activity patterns"
    ),
    
    "electrolyte_regulation_efficiency_score": MetricDefinition(
        metric_id="electrolyte_regulation_efficiency_score",
        domain="Renal + Hydration",
        display_name="Electrolyte Regulation Efficiency Score",
        lab_analog="Serum Na/K/Cl + urine electrolytes",
        where_seen="Nephrology, endurance athlete monitoring",
        stands_in_for="Electrolyte homeostasis quality",
        analog_type=AnalogType.TRUE_LAB_ANALOG,
        value_type="score",
        typical_units="/100",
        null_replacement_strategy="Show score with hydration + dietary sodium patterns"
    ),
    
    "renal_stress_index": MetricDefinition(
        metric_id="renal_stress_index",
        domain="Renal + Hydration",
        display_name="Renal Stress Index",
        lab_analog="Creatinine + BUN + eGFR + urine albumin",
        where_seen="Nephrology, hypertension management",
        stands_in_for="Kidney stress burden estimate",
        analog_type=AnalogType.CLINICIAN_SYNTHESIS_ANALOG,
        value_type="score",
        typical_units="/100",
        null_replacement_strategy="Show score with BP + hydration + protein intake signals"
    ),
    
    "dehydration_driven_creatinine_elevation_risk": MetricDefinition(
        metric_id="dehydration_driven_creatinine_elevation_risk",
        domain="Renal + Hydration",
        display_name="Dehydration-Driven Creatinine Elevation Risk",
        lab_analog="Creatinine + hydration status interaction",
        where_seen="Nephrology, interpreting borderline creatinine",
        stands_in_for="Probability creatinine elevated due to volume depletion vs intrinsic renal issue",
        analog_type=AnalogType.CLINICIAN_SYNTHESIS_ANALOG,
        value_type="probability",
        typical_units="%",
        null_replacement_strategy="Show probability with fluid intake + activity heat exposure"
    ),
    
    "egfr_trajectory_class": MetricDefinition(
        metric_id="egfr_trajectory_class",
        domain="Renal + Hydration",
        display_name="eGFR Trajectory Class",
        lab_analog="Estimated GFR from creatinine (CKD-EPI equation)",
        where_seen="Nephrology, diabetes clinics, primary care",
        stands_in_for="Estimated GFR trend classification",
        analog_type=AnalogType.TRUE_LAB_ANALOG,
        value_type="class",
        typical_units=None,
        null_replacement_strategy="Show 'Normal trajectory assumed' with age + BP drivers"
    ),
    
    # ========== COMPREHENSIVE + INTEGRATED (3 metrics) ==========
    "allostatic_load_proxy": MetricDefinition(
        metric_id="allostatic_load_proxy",
        domain="Comprehensive + Integrated",
        display_name="Allostatic Load Proxy",
        lab_analog="Multi-system burden index (HPA + immune + metabolic + CV)",
        where_seen="Integrative medicine, stress physiology research",
        stands_in_for="Cumulative physiologic wear-and-tear estimate",
        analog_type=AnalogType.CLINICIAN_SYNTHESIS_ANALOG,
        value_type="score",
        typical_units="/100",
        null_replacement_strategy="Show score with autonomic + metabolic + inflammatory drivers"
    ),
    
    "homeostatic_resilience_score": MetricDefinition(
        metric_id="homeostatic_resilience_score",
        domain="Comprehensive + Integrated",
        display_name="Homeostatic Resilience Score",
        lab_analog="HRV recovery + metabolic flexibility + adaptation capacity",
        where_seen="Functional medicine, longevity optimization",
        stands_in_for="Capacity to maintain homeostasis under stress",
        analog_type=AnalogType.CLINICIAN_SYNTHESIS_ANALOG,
        value_type="score",
        typical_units="/100",
        null_replacement_strategy="Show score with recovery + flexibility + autonomic baseline"
    ),
    
    "physiological_age_proxy": MetricDefinition(
        metric_id="physiological_age_proxy",
        domain="Comprehensive + Integrated",
        display_name="Physiological Age Proxy",
        lab_analog="Biological age algorithms (PhenoAge, GrimAge, etc.)",
        where_seen="Longevity clinics, preventive medicine",
        stands_in_for="Physiologic age vs chronologic age estimate",
        analog_type=AnalogType.CLINICIAN_SYNTHESIS_ANALOG,
        value_type="range",
        typical_units="years",
        null_replacement_strategy="Show range ±5 years around chronologic age"
    ),
}


# ============================================================================
# VALIDATION: Ensure exactly 35 metrics
# ============================================================================

assert len(METRIC_REGISTRY) == 35, f"CRITICAL: METRIC_REGISTRY must have exactly 35 metrics, found {len(METRIC_REGISTRY)}"

# Validate all metric IDs are unique
assert len(set(METRIC_REGISTRY.keys())) == 35, "CRITICAL: Duplicate metric IDs found"

# Validate all domains are covered
EXPECTED_DOMAINS = {
    "Metabolic Regulation",
    "Lipid + Cardiometabolic",
    "Micronutrient + Vitamin",
    "Inflammatory + Immune",
    "Endocrine + Neurohormonal",
    "Renal + Hydration",
    "Comprehensive + Integrated"
}
actual_domains = {m.domain for m in METRIC_REGISTRY.values()}
assert actual_domains == EXPECTED_DOMAINS, f"CRITICAL: Domain mismatch. Expected {EXPECTED_DOMAINS}, got {actual_domains}"


def get_metric_definition(metric_id: str) -> MetricDefinition:
    """Get metric definition by ID."""
    if metric_id not in METRIC_REGISTRY:
        raise ValueError(f"Unknown metric ID: {metric_id}. Must be one of {list(METRIC_REGISTRY.keys())}")
    return METRIC_REGISTRY[metric_id]


def get_metrics_by_domain(domain: str) -> List[MetricDefinition]:
    """Get all metrics for a specific domain."""
    return [m for m in METRIC_REGISTRY.values() if m.domain == domain]


def validate_all_metrics_present(metric_ids: List[str]) -> Tuple[bool, List[str]]:
    """
    Validate that all 35 metrics are present in the provided list.
    Returns (is_complete, missing_metrics).
    """
    expected = set(METRIC_REGISTRY.keys())
    actual = set(metric_ids)
    missing = expected - actual
    return len(missing) == 0, list(missing)
