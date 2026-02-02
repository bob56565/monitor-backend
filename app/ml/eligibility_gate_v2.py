"""
Eligibility Gating Engine and Output Catalog.

Defines:
- Output dependency catalog (clinic-style panels + physiological domains)
- Eligibility gating logic (resolve dependencies, apply blockers, compute penalties)
- Gating behavior and threshold policies
"""

from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from app.models.inference_pack_v2 import SuppressionReasonEnum


# ============================================================================
# Dependency Schema and Output Catalog
# ============================================================================

@dataclass
class OutputDependency:
    """Declares dependencies for a single output."""
    output_key: str
    requires_any: List[str] = field(default_factory=list)  # At least one must be present
    requires_all: List[str] = field(default_factory=list)  # All must be present
    requires_context: List[str] = field(default_factory=list)  # Context variables
    blocked_by: List[str] = field(default_factory=list)  # Conditions that block output
    confidence_boosters: List[str] = field(default_factory=list)  # Increase confidence
    confidence_penalties: List[str] = field(default_factory=list)  # Decrease confidence
    min_coherence_required: float = 0.55
    min_signal_quality_required: float = 0.60
    panel: str = "GENERAL"
    domain: str = "GENERAL"


# ============================================================================
# Output Catalog: Panel Definitions with Dependencies
# ============================================================================

OUTPUT_CATALOG: Dict[str, OutputDependency] = {
    # ===== CMP/BMP =====
    "glucose_est": OutputDependency(
        output_key="glucose_est",
        requires_any=["isf.glucose", "blood.glucose_plasma", "blood.glucose_serum"],
        requires_context=["age", "sex_at_birth"],
        blocked_by=["pregnancy=confirmed_or_suspected"],
        confidence_boosters=["isf_glucose_direct", "blood_glucose_fresh", "temporal_stability"],
        confidence_penalties=["high_missingness", "meal_state_uncertain", "coherence_glucose_low"],
        min_coherence_required=0.50,
        panel="CMP",
        domain="metabolic",
    ),
    "bun_est": OutputDependency(
        output_key="bun_est",
        requires_any=["blood.bun"],
        requires_context=["age", "hydration_status"],
        blocked_by=["acute_kidney_injury_likely"],
        confidence_boosters=["creatinine_stable", "hydration_known"],
        confidence_penalties=["dehydration_suspected", "recent_diuretic"],
        min_coherence_required=0.55,
        panel="CMP",
        domain="renal",
    ),
    "creatinine_est": OutputDependency(
        output_key="creatinine_est",
        requires_any=["blood.creatinine"],
        requires_context=["age", "sex_at_birth", "weight_kg", "race"],
        confidence_boosters=["stable_egfr", "consistent_bun"],
        confidence_penalties=["muscle_wasting_suspected", "high_turnover_state"],
        min_coherence_required=0.55,
        panel="CMP",
        domain="renal",
    ),
    "egfr_est": OutputDependency(
        output_key="egfr_est",
        requires_all=["creatinine_est"],
        requires_context=["age", "sex_at_birth", "race"],
        confidence_boosters=["stable_creatinine", "consistent_bun"],
        confidence_penalties=["acute_kidney_injury", "rapid_creatinine_change"],
        min_coherence_required=0.55,
        panel="CMP",
        domain="renal",
    ),
    "sodium_na_est": OutputDependency(
        output_key="sodium_na_est",
        requires_any=["blood.sodium", "urine.sodium"],
        requires_context=["hydration_status", "fluid_intake"],
        blocked_by=["siadh_likely", "hypervolemia_obvious"],
        confidence_boosters=["osmolarity_consistent", "urine_osmolarity_available"],
        confidence_penalties=["diuretic_use", "hyperglycemia_present"],
        min_coherence_required=0.55,
        panel="CMP",
        domain="electrolyte",
    ),
    "potassium_k_est": OutputDependency(
        output_key="potassium_k_est",
        requires_any=["blood.potassium"],
        requires_context=["renal_function", "acid_base_status"],
        blocked_by=["hemolysis_likely"],
        confidence_boosters=["ph_normal", "co2_normal"],
        confidence_penalties=["acidemia", "dialysis_day", "acutes_meds"],
        min_coherence_required=0.55,
        panel="CMP",
        domain="electrolyte",
    ),
    "chloride_cl_est": OutputDependency(
        output_key="chloride_cl_est",
        requires_any=["blood.chloride", "isf.chloride_cl"],
        requires_context=[],  # Removed acid_base_status requirement
        confidence_boosters=["co2_available", "anion_gap_normal"],
        confidence_penalties=["metabolic_acidosis", "vomiting_active"],
        min_coherence_required=0.55,
        panel="CMP",
        domain="electrolyte",
    ),
    "lactate_est": OutputDependency(
        output_key="lactate_est",
        requires_any=["blood.lactate", "isf.lactate"],
        requires_context=[],  # Removed activity_level requirement
        blocked_by=["septic_shock"],
        confidence_boosters=["stable_activity", "normal_perfusion"],
        confidence_penalties=["exercise_recent", "hypoxia"],
        min_coherence_required=0.55,
        panel="METABOLIC",
        domain="metabolic",
    ),
    "calcium_est": OutputDependency(
        output_key="calcium_est",
        requires_any=["blood.calcium"],
        requires_context=["albumin", "vitamin_d_status"],
        confidence_boosters=["albumin_normal", "phosphate_available"],
        confidence_penalties=["hypoalbuminemia", "parathyroid_disease"],
        min_coherence_required=0.55,
        panel="CMP",
        domain="electrolyte",
    ),
    "magnesium_est": OutputDependency(
        output_key="magnesium_est",
        requires_any=["blood.magnesium"],
        requires_context=["diuretic_use"],
        confidence_boosters=["calcium_normal", "no_ppi_use"],
        confidence_penalties=["diuretic_chronic", "gi_loss"],
        min_coherence_required=0.55,
        panel="CMP",
        domain="electrolyte",
    ),
    "phosphate_est": OutputDependency(
        output_key="phosphate_est",
        requires_any=["blood.phosphate"],
        requires_context=["vitamin_d_status", "renal_function"],
        confidence_boosters=["calcium_available", "parathyroid_normal"],
        confidence_penalties=["ckd_stage_4_5", "tpn_active"],
        min_coherence_required=0.55,
        panel="CMP",
        domain="electrolyte",
    ),
    
    # ===== CBC =====
    "wbc_est": OutputDependency(
        output_key="wbc_est",
        requires_any=["blood.wbc"],
        requires_context=["age"],
        blocked_by=["acute_leukemia_suspected"],
        confidence_boosters=["differential_available", "left_shift_absent"],
        confidence_penalties=["infection_suspected", "immunosuppression"],
        min_coherence_required=0.55,
        panel="CBC",
        domain="hematology",
    ),
    "hemoglobin_est": OutputDependency(
        output_key="hemoglobin_est",
        requires_any=["blood.hemoglobin"],
        requires_context=["sex_at_birth", "altitude"],
        blocked_by=["acute_bleeding_obvious"],
        confidence_boosters=["iron_status_known", "chronic_stable"],
        confidence_penalties=["active_bleeding", "hemolysis_risk"],
        min_coherence_required=0.55,
        panel="CBC",
        domain="hematology",
    ),
    "platelets_est": OutputDependency(
        output_key="platelets_est",
        requires_any=["blood.platelets"],
        requires_context=["age"],
        blocked_by=["immune_thrombocytopenia_acute"],
        confidence_boosters=["mpv_normal", "coagulation_normal"],
        confidence_penalties=["sepsis_suspected", "drip_contamination_risk"],
        min_coherence_required=0.55,
        panel="CBC",
        domain="hematology",
    ),
    "rbc_est": OutputDependency(
        output_key="rbc_est",
        requires_any=["blood.rbc"],
        requires_context=["altitude"],
        confidence_boosters=["hemoglobin_consistent", "hematocrit_consistent"],
        confidence_penalties=["dehydration", "acute_blood_loss"],
        min_coherence_required=0.55,
        panel="CBC",
        domain="hematology",
    ),
    "hematocrit_est": OutputDependency(
        output_key="hematocrit_est",
        requires_any=["blood.hematocrit"],
        requires_context=["hydration_status"],
        confidence_boosters=["hemoglobin_available", "stable_volume"],
        confidence_penalties=["fluid_shifts", "bleeding_active"],
        min_coherence_required=0.55,
        panel="CBC",
        domain="hematology",
    ),
    "mcv_est": OutputDependency(
        output_key="mcv_est",
        requires_any=["blood.mcv"],
        requires_context=["age"],
        confidence_boosters=["iron_studies_available", "b12_folate_known"],
        confidence_penalties=["mixed_anemia", "recent_transfusion"],
        min_coherence_required=0.55,
        panel="CBC",
        domain="hematology",
    ),
    
    # ===== LIPIDS =====
    "chol_total_est": OutputDependency(
        output_key="chol_total_est",
        requires_any=["blood.cholesterol_total"],
        requires_context=["age", "sex_at_birth", "fasting_status"],
        blocked_by=["acute_illness"],
        confidence_boosters=["fasting_confirmed", "stable_diet"],
        confidence_penalties=["non_fasting", "recent_statin_change", "acute_stress"],
        min_coherence_required=0.55,
        panel="LIPIDS",
        domain="lipid",
    ),
    "ldl_est": OutputDependency(
        output_key="ldl_est",
        requires_any=["blood.ldl", "blood.cholesterol_total"],
        requires_context=["age", "sex_at_birth", "risk_category"],
        confidence_boosters=["triglycerides_low", "fasting_confirmed"],
        confidence_penalties=["triglycerides_high", "calculation_required"],
        min_coherence_required=0.55,
        panel="LIPIDS",
        domain="lipid",
    ),
    "triglycerides_est": OutputDependency(
        output_key="triglycerides_est",
        requires_any=["blood.triglycerides"],
        requires_context=["fasting_status"],
        blocked_by=["severe_hypertriglyceridemia_acute"],
        confidence_boosters=["fasting_confirmed", "ltm_stable"],
        confidence_penalties=["non_fasting", "recent_meal"],
        min_coherence_required=0.55,
        panel="LIPIDS",
        domain="lipid",
    ),
    "hdl_est": OutputDependency(
        output_key="hdl_est",
        requires_any=["blood.hdl", "blood.hdl_cholesterol"],
        requires_context=["sex_at_birth"],
        confidence_boosters=["ldl_available", "fasting_confirmed"],
        confidence_penalties=["non_fasting", "recent_exercise"],
        min_coherence_required=0.55,
        panel="LIPIDS",
        domain="lipid",
    ),
    "vldl_est": OutputDependency(
        output_key="vldl_est",
        requires_any=["blood.vldl", "blood.triglycerides"],
        requires_context=["fasting_status"],
        confidence_boosters=["triglycerides_available", "ldl_hdl_known"],
        confidence_penalties=["non_fasting", "hypertriglyceridemia"],
        min_coherence_required=0.55,
        panel="LIPIDS",
        domain="lipid",
    ),
    "ldl_hdl_ratio_est": OutputDependency(
        output_key="ldl_hdl_ratio_est",
        requires_any=["ldl_est", "hdl_est"],
        requires_context=["cardiovascular_risk"],
        confidence_boosters=["both_measured_directly", "fasting_confirmed"],
        confidence_penalties=["calculated_lipids", "statin_active"],
        min_coherence_required=0.55,
        panel="LIPIDS",
        domain="lipid",
    ),
    
    # ===== ENDOCRINE =====
    "a1c_est": OutputDependency(
        output_key="a1c_est",
        requires_any=["blood.a1c", "isf.glucose_time_features"],
        requires_context=["age", "race"],
        blocked_by=["hemoglobinopathy_known"],
        confidence_boosters=["stable_glucose", "long_glucose_history"],
        confidence_penalties=["acute_hemolysis", "anemia_significant"],
        min_coherence_required=0.55,
        panel="ENDOCRINE",
        domain="endocrine",
    ),
    "tsh_est": OutputDependency(
        output_key="tsh_est",
        requires_any=["blood.tsh"],
        requires_context=["age", "sex_at_birth", "pregnancy_status"],
        blocked_by=["pituitary_disease_acute"],
        confidence_boosters=["free_t4_available", "stable_thyroid_meds"],
        confidence_penalties=["thyroid_meds_recent_change", "sick_euthyroid"],
        min_coherence_required=0.55,
        panel="ENDOCRINE",
        domain="endocrine",
    ),
    "insulin_resistance_proxy": OutputDependency(
        output_key="insulin_resistance_proxy",
        requires_any=["blood.a1c", "blood.fasting_insulin", "isf.glucose_time_features"],
        requires_context=["age", "sex_at_birth", "bmi_or_weight_height"],
        blocked_by=["pregnancy=confirmed_or_suspected"],
        confidence_boosters=["sleep_duration_known", "activity_level_known"],
        confidence_penalties=["acute_stress", "recent_medication_change"],
        min_coherence_required=0.55,
        panel="ENDOCRINE",
        domain="endocrine",
    ),
    "alt_est": OutputDependency(
        output_key="alt_est",
        requires_any=["blood.alt"],
        requires_context=["age", "alcohol_intake"],
        confidence_boosters=["ast_available", "no_acute_hepatitis"],
        confidence_penalties=["muscle_injury", "medication_hepatotoxic"],
        min_coherence_required=0.55,
        panel="LIVER",
        domain="liver",
    ),
    "ast_est": OutputDependency(
        output_key="ast_est",
        requires_any=["blood.ast"],
        requires_context=["age", "cardiac_status"],
        confidence_boosters=["alt_available", "stable_baseline"],
        confidence_penalties=["myocardial_injury", "hemolysis"],
        min_coherence_required=0.55,
        panel="LIVER",
        domain="liver",
    ),
    "alp_est": OutputDependency(
        output_key="alp_est",
        requires_any=["blood.alp"],
        requires_context=["age", "bone_health"],
        confidence_boosters=["ggt_available", "calcium_phosphate_normal"],
        confidence_penalties=["pregnancy", "bone_metastases"],
        min_coherence_required=0.55,
        panel="LIVER",
        domain="liver",
    ),
    "bilirubin_total_est": OutputDependency(
        output_key="bilirubin_total_est",
        requires_any=["blood.bilirubin_total"],
        requires_context=["age", "hemolysis_risk"],
        confidence_boosters=["direct_bilirubin_available", "no_hemolysis"],
        confidence_penalties=["gilbert_syndrome", "acute_hemolysis"],
        min_coherence_required=0.55,
        panel="LIVER",
        domain="liver",
    ),
    "albumin_est": OutputDependency(
        output_key="albumin_est",
        requires_any=["blood.albumin"],
        requires_context=["age", "nutritional_status"],
        confidence_boosters=["total_protein_available", "stable_nutrition"],
        confidence_penalties=["chronic_illness", "protein_losing"],
        min_coherence_required=0.55,
        panel="LIVER",
        domain="liver",
    ),
    "total_protein_est": OutputDependency(
        output_key="total_protein_est",
        requires_any=["blood.total_protein"],
        requires_context=["hydration_status"],
        confidence_boosters=["albumin_available", "globulin_available"],
        confidence_penalties=["dehydration", "paraproteinemia"],
        min_coherence_required=0.55,
        panel="LIVER",
        domain="liver",
    ),
    
    # ===== VITAMINS =====
    "vitamin_d_25oh_est": OutputDependency(
        output_key="vitamin_d_25oh_est",
        requires_any=["blood.vitamin_d_25oh"],
        requires_context=["age", "season", "sun_exposure"],
        confidence_boosters=["calcium_normal", "phosphate_normal"],
        confidence_penalties=["renal_disease", "malabsorption_suspected"],
        min_coherence_required=0.55,
        panel="VITAMINS",
        domain="vitamin",
    ),
    "b12_est": OutputDependency(
        output_key="b12_est",
        requires_any=["blood.b12"],
        requires_context=["age", "diet_type"],
        blocked_by=["pernicious_anemia_acute"],
        confidence_boosters=["folate_normal", "methylmalonic_acid_low"],
        confidence_penalties=["vegan_diet_long_term", "gi_malabsorption"],
        min_coherence_required=0.55,
        panel="VITAMINS",
        domain="vitamin",
    ),
    "folate_est": OutputDependency(
        output_key="folate_est",
        requires_any=["blood.folate"],
        requires_context=["diet_type"],
        confidence_boosters=["b12_normal", "mcv_normal"],
        confidence_penalties=["alcohol_abuse", "malabsorption"],
        min_coherence_required=0.55,
        panel="VITAMINS",
        domain="vitamin",
    ),
    "iron_est": OutputDependency(
        output_key="iron_est",
        requires_any=["blood.iron"],
        requires_context=["age", "menstrual_status"],
        confidence_boosters=["ferritin_available", "tibc_available"],
        confidence_penalties=["inflammation_active", "recent_meal"],
        min_coherence_required=0.55,
        panel="VITAMINS",
        domain="vitamin",
    ),
    "ferritin_est": OutputDependency(
        output_key="ferritin_est",
        requires_any=["blood.ferritin"],
        requires_context=["inflammation_status"],
        confidence_boosters=["iron_available", "no_inflammation"],
        confidence_penalties=["acute_phase_response", "liver_disease"],
        min_coherence_required=0.55,
        panel="VITAMINS",
        domain="vitamin",
    ),
    "cortisol_est": OutputDependency(
        output_key="cortisol_est",
        requires_any=["blood.cortisol", "saliva.cortisol"],
        requires_context=["time_of_day", "stress_level"],
        confidence_boosters=["morning_sample", "fasting_confirmed"],
        confidence_penalties=["evening_sample", "acute_stress"],
        min_coherence_required=0.55,
        panel="ENDOCRINE",
        domain="endocrine",
    ),
    "testosterone_est": OutputDependency(
        output_key="testosterone_est",
        requires_any=["blood.testosterone_total"],
        requires_context=["age", "sex_at_birth", "time_of_day"],
        confidence_boosters=["morning_sample", "shbg_available"],
        confidence_penalties=["evening_sample", "recent_exercise"],
        min_coherence_required=0.55,
        panel="ENDOCRINE",
        domain="endocrine",
    ),
    "estradiol_est": OutputDependency(
        output_key="estradiol_est",
        requires_any=["blood.estradiol_e2"],
        requires_context=["age", "sex_at_birth", "menstrual_phase"],
        confidence_boosters=["cycle_day_known", "lh_fsh_available"],
        confidence_penalties=["menopause", "hrt_active"],
        min_coherence_required=0.55,
        panel="ENDOCRINE",
        domain="endocrine",
    ),
    
    # ===== INFLAMMATION =====
    "crp_est": OutputDependency(
        output_key="crp_est",
        requires_any=["blood.crp"],
        requires_context=["age"],
        blocked_by=["acute_infection_obvious"],
        confidence_boosters=["esr_consistent", "wbc_normal"],
        confidence_penalties=["active_infection", "recent_surgery"],
        min_coherence_required=0.55,
        panel="INFLAMMATION",
        domain="inflammation",
    ),
    "inflammatory_tone_state": OutputDependency(
        output_key="inflammatory_tone_state",
        requires_any=["crp_est", "blood.esr", "encoding_outputs.effect_vector"],
        requires_context=["age"],
        confidence_boosters=["multiple_markers", "consistent_sleep"],
        confidence_penalties=["acute_illness", "stress_high"],
        min_coherence_required=0.55,
        panel="INFLAMMATION",
        domain="inflammation",
    ),
    
    # ===== HYDRATION/RENAL URINE =====
    "hydration_status_state": OutputDependency(
        output_key="hydration_status_state",
        requires_any=["urine.specific_gravity", "blood.osmolarity", "blood.sodium"],
        requires_context=["fluid_intake", "sweat_loss_estimate"],
        confidence_boosters=["multiple_markers_consistent", "urine_color_known"],
        confidence_penalties=["diuretic_use", "diarrhea_active"],
        min_coherence_required=0.55,
        panel="HYDRATION",
        domain="hydration",
    ),
    "renal_stress_state": OutputDependency(
        output_key="renal_stress_state",
        requires_any=["egfr_est", "urine.protein", "urine.specific_gravity"],
        requires_context=["age", "hypertension_status"],
        confidence_boosters=["stable_egfr", "no_proteinuria"],
        confidence_penalties=["acute_kidney_injury", "rapid_egfr_decline"],
        min_coherence_required=0.55,
        panel="HYDRATION",
        domain="renal",
    ),
    
    # ===== STRESS/SLEEP/RECOVERY =====
    "stress_axis_state": OutputDependency(
        output_key="stress_axis_state",
        requires_any=["blood.cortisol", "saliva.cortisol", "encoding_outputs.effect_vector"],
        requires_context=["sleep_quality", "stress_level_reported"],
        confidence_boosters=["morning_cortisol_available", "normal_circadian"],
        confidence_penalties=["acute_stressor", "poor_sleep"],
        min_coherence_required=0.55,
        panel="STRESS",
        domain="stress_recovery",
    ),
    "recovery_state": OutputDependency(
        output_key="recovery_state",
        requires_any=["hrv", "feature_pack_v2.pattern_combination_features"],
        requires_context=["activity_level", "sleep_duration"],
        confidence_boosters=["stable_regime", "normal_patterns"],
        confidence_penalties=["poor_sleep", "high_stress"],
        min_coherence_required=0.55,
        panel="STRESS",
        domain="stress_recovery",
    ),
}


# ============================================================================
# Gating Behavior and Threshold Policies
# ============================================================================

@dataclass
class GatingThresholdPolicy:
    """Default threshold policy for eligibility gating."""
    min_coherence_default: float = 0.55
    min_signal_quality_default: float = 0.60
    suppress_if_confidence_below: float = 0.35
    widen_range_if_disagreement_above: float = 0.45
    range_widening_factor_mild: float = 1.25  # 25% wider
    range_widening_factor_severe: float = 1.40  # 40% wider
    confidence_penalty_disagreement: float = 0.10
    confidence_penalty_coherence: float = 0.18
    confidence_penalty_incompleteness: float = 0.15


DEFAULT_GATING_POLICY = GatingThresholdPolicy()


# ============================================================================
# Eligibility Gate V2: Main Logic
# ============================================================================

class EligibilityGateV2:
    """
    Eligibility gate that resolves dependencies, applies blockers,
    and determines if an output should be produced, widened, or suppressed.
    """
    
    def __init__(self, policy: GatingThresholdPolicy = DEFAULT_GATING_POLICY):
        self.policy = policy
    
    def can_produce_output(
        self,
        output_key: str,
        available_values: Dict[str, bool],
        available_contexts: Dict[str, bool],
        blockers: Dict[str, bool],
        coherence_score: Optional[float] = None,
        signal_quality: Optional[float] = None,
        base_confidence: Optional[float] = None,
    ) -> Tuple[bool, str, Optional[float], List[str]]:
        """
        Determine if an output should be produced, and if so, return adjusted confidence and penalties.
        
        Returns:
            (should_produce: bool, reason: str, adjusted_confidence: float|None, applied_penalties: List[str])
        """
        if output_key not in OUTPUT_CATALOG:
            return False, f"Unknown output_key: {output_key}", None, []
        
        dep = OUTPUT_CATALOG[output_key]
        applied_penalties = []
        
        # Check blockers first
        for blocker in dep.blocked_by:
            if blockers.get(blocker, False):
                return (
                    False,
                    f"Blocker met: {blocker}",
                    None,
                    [f"blocker_{blocker}"]
                )
        
        # Check requires_all
        for req in dep.requires_all:
            if not available_values.get(req, False):
                return (
                    False,
                    f"Missing required anchor: {req}",
                    None,
                    [f"missing_{req}"]
                )
        
        # Check requires_any
        if dep.requires_any:
            any_met = any(available_values.get(req, False) for req in dep.requires_any)
            if not any_met:
                return (
                    False,
                    f"No required anchors met (requires_any: {dep.requires_any})",
                    None,
                    [f"no_requires_any_met"]
                )
        
        # Check requires_context
        for ctx in dep.requires_context:
            if not available_contexts.get(ctx, False):
                return (
                    False,
                    f"Missing required context: {ctx}",
                    None,
                    [f"missing_context_{ctx}"]
                )
        
        # Coherence check
        if coherence_score is not None:
            if coherence_score < dep.min_coherence_required:
                applied_penalties.append("low_coherence")
        
        # Signal quality check
        if signal_quality is not None:
            if signal_quality < dep.min_signal_quality_required:
                applied_penalties.append("low_signal_quality")
        
        # If all checks pass, produce output
        adjusted_confidence = base_confidence or 0.75
        
        # Apply penalties
        for penalty in applied_penalties:
            if penalty == "low_coherence":
                adjusted_confidence -= self.policy.confidence_penalty_coherence
            elif penalty == "low_signal_quality":
                adjusted_confidence -= 0.10
        
        adjusted_confidence = max(0.0, min(1.0, adjusted_confidence))
        
        # Check if confidence is above suppression threshold
        if adjusted_confidence < self.policy.suppress_if_confidence_below:
            return (
                False,
                f"Confidence below threshold ({adjusted_confidence:.2f} < {self.policy.suppress_if_confidence_below})",
                None,
                applied_penalties
            )
        
        return (True, "Eligibility met", adjusted_confidence, applied_penalties)
    
    def get_output_dependency(self, output_key: str) -> Optional[OutputDependency]:
        """Fetch dependency spec for an output."""
        return OUTPUT_CATALOG.get(output_key)
