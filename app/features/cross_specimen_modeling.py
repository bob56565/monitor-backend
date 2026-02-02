"""
Cross-specimen relationship modeling: kinetics, conservation, triangulation, artifact.
"""

from typing import Dict, Optional, Tuple, List
import math
from app.models.run_v2 import RunV2, SpecimenTypeEnum
from app.models.feature_pack_v2 import (
    LagModelParams, PlausibilityParams, TriangulationScores, ArtifactAndInterferenceRisks,
    CrossSpecimenRelationships
)


def model_lag_kinetics(run_v2: RunV2) -> LagModelParams:
    """
    Estimate lag between ISF and blood glucose using kinetic models.
    
    Returns lag in minutes + coherence score.
    Typical ISF→Blood lag: 5-15 minutes depending on individual and conditions.
    """
    
    isf_glucose = _get_specimen_value(run_v2, SpecimenTypeEnum.ISF, "glucose")
    blood_glucose_cap = _get_specimen_value(run_v2, SpecimenTypeEnum.BLOOD_CAPILLARY, "glucose")
    blood_glucose_ven = _get_specimen_value(run_v2, SpecimenTypeEnum.BLOOD_VENOUS, "glucose")
    blood_glucose = blood_glucose_cap or blood_glucose_ven
    
    lag_estimate = None
    lag_uncertainty = None
    lag_coherence = 0.5
    event_anchored_lags = {}
    
    if isf_glucose is not None and blood_glucose is not None:
        # Simple heuristic: if ISF is lower than blood, ISF likely lags behind
        diff = blood_glucose - isf_glucose
        
        if abs(diff) < 10:
            # Close agreement → lag ~5-8 minutes
            lag_estimate = 6.0
            lag_uncertainty = 2.0
            lag_coherence = 0.9
        elif diff > 10:
            # ISF lower → might lag or low perfusion
            lag_estimate = 8.0
            lag_uncertainty = 4.0
            lag_coherence = 0.7
        elif diff < -10:
            # ISF higher than blood → unusual, possible artifact or lag in reverse
            lag_estimate = 4.0
            lag_uncertainty = 5.0
            lag_coherence = 0.5
    
    # Event anchoring: if diet/activity/sleep markers present
    qualitative = run_v2.qualitative_inputs
    
    # Postprandial scenario
    if qualitative and qualitative.diet_recent and qualitative.diet_recent.get("fasting_state") == "fed":
        event_anchored_lags["postprandial"] = lag_estimate + 2.0 if lag_estimate else 8.0
    
    # Activity scenario
    if qualitative and qualitative.symptoms and qualitative.symptoms.get("palpitations"):
        event_anchored_lags["exertion_like"] = lag_estimate + 1.0 if lag_estimate else 7.0
    
    return LagModelParams(
        isf_blood_lag_minutes_estimate=lag_estimate,
        lag_uncertainty_minutes=lag_uncertainty,
        event_anchored_lags=event_anchored_lags,
        lag_coherence_score_0_1=lag_coherence,
    )


def model_conservation_and_plausibility(run_v2: RunV2) -> PlausibilityParams:
    """
    Check mass balance and conservation laws for electrolytes and fluid.
    
    Electrolyte conservation: Na in = Na out (sweat + urine + internal redistribution)
    Hydration balance: fluid_in + metabolic_water ≈ sweat + urine + respiratory_loss
    """
    
    penalties = []
    electrolyte_balance_score = 0.8  # Default: assume reasonable
    hydration_balance_score = 0.8
    
    # Electrolyte conservation check
    blood_na = _get_specimen_value(run_v2, SpecimenTypeEnum.BLOOD_VENOUS, "sodium_na")
    sweat_na = _get_specimen_value(run_v2, SpecimenTypeEnum.SWEAT, "sodium_na")
    sweat_rate = _get_specimen_value(run_v2, SpecimenTypeEnum.SWEAT, "sweat_rate")
    
    if blood_na is not None and sweat_na is not None and sweat_rate is not None:
        # Rough check: if high sweat rate but normal blood Na, suggests adequate replacement
        if sweat_rate > 1.0 and blood_na > 145:  # High sweat + hypernatremia
            electrolyte_balance_score = 0.4
            penalties.append("high_sweat_rate_with_hypernatremia_suggests_inadequate_intake")
        elif sweat_rate > 1.0 and blood_na > 140:
            electrolyte_balance_score = 0.6
            penalties.append("high_sweat_rate_with_elevated_sodium")
    
    # Hydration balance check
    fluid_intake = _get_nonlab_value(run_v2, "intake_exposure.fluid_intake_ml_24h")
    urine_sg = _get_specimen_value(run_v2, SpecimenTypeEnum.URINE_SPOT, "specific_gravity")
    
    if fluid_intake is not None and urine_sg is not None:
        # High fluid intake with high urine SG (dilute urine) = good hydration
        if fluid_intake > 2000 and urine_sg > 1.020:
            hydration_balance_score = 0.5
            penalties.append("high_fluid_intake_but_concentrated_urine_suggests_poor_absorption_or_losses")
        elif fluid_intake < 1000 and urine_sg > 1.025:
            hydration_balance_score = 0.3
            penalties.append("low_fluid_intake_with_concentrated_urine_indicates_dehydration")
        elif fluid_intake > 2000 and urine_sg < 1.010:
            hydration_balance_score = 0.9  # Good hydration signal
    
    return PlausibilityParams(
        electrolyte_balance_score_0_1=electrolyte_balance_score,
        hydration_mass_balance_score_0_1=hydration_balance_score,
        plausibility_penalties=penalties,
    )


def model_proxy_triangulation(run_v2: RunV2) -> TriangulationScores:
    """
    Triangulate between proxy measures to assess internal consistency.
    
    - Stress axis: saliva cortisol + HRV + sleep quality should align
    - Metabolic exertion: lactate + glucose + activity level should align
    - Inflammation/sleep: CRP + sleep fragmentation should align
    """
    
    stress_coherence = 0.5
    metabolic_exertion_coherence = 0.5
    inflammation_sleep_coherence = 0.5
    
    # Stress axis triangulation
    cortisol_morning = _get_specimen_value(run_v2, SpecimenTypeEnum.SALIVA, "cortisol_morning")
    hrv = _get_nonlab_value(run_v2, "vitals_physiology.hrv")
    sleep_quality = _get_nonlab_value(run_v2, "sleep_activity.sleep_quality_0_10")
    
    if cortisol_morning is not None and hrv is not None and sleep_quality is not None:
        # Normal cortisol + high HRV + good sleep = good agreement
        if cortisol_morning < 20 and hrv > 30 and sleep_quality > 6:
            stress_coherence = 0.9
        # High cortisol + low HRV + poor sleep = high stress state (coherent)
        elif cortisol_morning > 20 and hrv < 20 and sleep_quality < 5:
            stress_coherence = 0.8  # Coherent but stressed
        # Mixed signals
        else:
            stress_coherence = 0.5
    
    # Metabolic exertion triangulation
    lactate = _get_specimen_value(run_v2, SpecimenTypeEnum.ISF, "lactate")
    glucose = _get_specimen_value(run_v2, SpecimenTypeEnum.ISF, "glucose")
    activity_level = _get_nonlab_value(run_v2, "sleep_activity.activity_level_0_10")
    
    if lactate is not None and glucose is not None and activity_level is not None:
        # High activity + high lactate/glucose = coherent exertion
        if activity_level > 7 and lactate > 2.0 and glucose > 120:
            metabolic_exertion_coherence = 0.9
        # Low activity + normal lactate/glucose = coherent rest
        elif activity_level < 3 and lactate < 1.5 and glucose < 110:
            metabolic_exertion_coherence = 0.8
        # Activity high but lactate flat = possible lag or low intensity
        elif activity_level > 7 and lactate < 1.5:
            metabolic_exertion_coherence = 0.4  # Incoherent
    
    # Inflammation/sleep triangulation
    crp = _get_specimen_value(run_v2, SpecimenTypeEnum.BLOOD_VENOUS, "crp")
    sleep_duration = _get_nonlab_value(run_v2, "sleep_activity.sleep_duration_hr")
    
    if crp is not None and sleep_duration is not None:
        # High CRP + low sleep = coherent (both suggest inflammation/stress)
        if crp > 3.0 and sleep_duration < 6:
            inflammation_sleep_coherence = 0.8
        # Low CRP + good sleep = coherent (both good)
        elif crp < 1.0 and sleep_duration > 7:
            inflammation_sleep_coherence = 0.9
    
    return TriangulationScores(
        stress_axis_coherence_0_1=stress_coherence,
        metabolic_exertion_coherence_0_1=metabolic_exertion_coherence,
        inflammation_sleep_coherence_0_1=inflammation_sleep_coherence,
    )


def model_artifact_and_interference(run_v2: RunV2) -> ArtifactAndInterferenceRisks:
    """
    Assess risk of data quality issues and medication/physiological confounds.
    """
    
    motion_artifact_risk = 0.0
    topical_contamination_risk = 0.0
    dehydration_confounding_risk = 0.0
    medication_interference_flags = []
    
    # Motion artifact: check if wearable signal quality is poor
    # (This would come from ISF sensor metadata if available)
    # For now, use HRV variability as proxy for motion
    hrv = _get_nonlab_value(run_v2, "vitals_physiology.hrv")
    if hrv is not None and hrv < 10:
        motion_artifact_risk = 0.6  # Very low HRV might indicate motion or stress
    
    # Topical contamination (sweat): if skin temp high or exertion high, contamination risk increases
    skin_temp = _get_specimen_value(run_v2, SpecimenTypeEnum.SWEAT, "skin_temp")
    exertion = _get_specimen_value(run_v2, SpecimenTypeEnum.SWEAT, "exertion_level")
    
    if skin_temp is not None and skin_temp > 35:
        topical_contamination_risk = 0.5  # High skin temp increases sweat collection artifact risk
    if exertion is not None and exertion > 8:
        topical_contamination_risk += 0.3
    topical_contamination_risk = min(topical_contamination_risk, 1.0)
    
    # Dehydration confounding (urine interpretation affected by hydration state)
    urine_sg = _get_specimen_value(run_v2, SpecimenTypeEnum.URINE_SPOT, "specific_gravity")
    if urine_sg is not None and urine_sg > 1.025:
        dehydration_confounding_risk = 0.7  # High SG makes urine tests hard to interpret
    
    # Medication interference: check medication list
    medications = run_v2.non_lab_inputs.medications or []
    interference_drugs = {
        "diuretic": ["furosemide", "thiazide", "spironolactone"],
        "steroid": ["prednisone", "dexamethasone", "hydrocortisone"],
        "beta_agonist": ["albuterol", "salbutamol"],
        "thyroid": ["levothyroxine", "liothyronine"],
    }
    
    for med in medications:
        drug_name = (med.drug or "").lower()
        for drug_class, drug_list in interference_drugs.items():
            if any(d in drug_name for d in drug_list):
                medication_interference_flags.append(f"{drug_class}_may_affect_metabolism_and_fluid_balance")
    
    # Aggregate interference
    aggregate_interference = (motion_artifact_risk + topical_contamination_risk + dehydration_confounding_risk) / 3.0
    
    return ArtifactAndInterferenceRisks(
        motion_artifact_risk_0_1=motion_artifact_risk,
        topical_contamination_risk_0_1=topical_contamination_risk,
        dehydration_confounding_risk_0_1=dehydration_confounding_risk,
        medication_interference_flags=medication_interference_flags,
        aggregate_interference_score_0_1=aggregate_interference,
    )


def build_cross_specimen_relationships(run_v2: RunV2) -> CrossSpecimenRelationships:
    """
    Orchestrate all cross-specimen modules and return consolidated output.
    """
    lag_model = model_lag_kinetics(run_v2)
    plausibility = model_conservation_and_plausibility(run_v2)
    triangulation = model_proxy_triangulation(run_v2)
    artifact_risks = model_artifact_and_interference(run_v2)
    
    return CrossSpecimenRelationships(
        lag_model=lag_model,
        plausibility=plausibility,
        triangulation=triangulation,
        artifact_risks=artifact_risks,
    )


# Helper functions
def _get_specimen_value(run_v2: RunV2, specimen_type: SpecimenTypeEnum, variable_name: str) -> Optional[float]:
    """Get a specific variable value from a specimen of given type."""
    for specimen in run_v2.specimens:
        if specimen.specimen_type == specimen_type:
            # Defensive: check if variable exists in missingness dict
            if variable_name in specimen.missingness:
                missingness_entry = specimen.missingness[variable_name]
                is_missing = missingness_entry.is_missing if hasattr(missingness_entry, 'is_missing') else True
                if not is_missing:
                    val = specimen.raw_values.get(variable_name)
                    return float(val) if val is not None else None
    return None


def _get_nonlab_value(run_v2: RunV2, path: str) -> Optional[float]:
    """
    Get a non-lab value using dot-notation path.
    E.g., "demographics.age" or "vitals_physiology.heart_rate"
    """
    parts = path.split(".")
    obj = run_v2.non_lab_inputs
    
    for part in parts:
        if obj is None:
            return None
        if isinstance(obj, dict):
            obj = obj.get(part)
        else:
            obj = getattr(obj, part, None)
    
    return float(obj) if obj is not None else None
