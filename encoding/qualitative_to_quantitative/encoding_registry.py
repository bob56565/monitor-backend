"""
Qualitative to Quantitative Encoding System
Maps dropdown selections to standardized codes, numeric weights, time windows, and direction of effect.
Implements exact rules from PART A specification A5.
"""

from typing import Dict, List, Optional, Literal
from pydantic import BaseModel, Field
from schemas.part_a.v1.main_schema import QualitativeEncodingRule


class EncodingRegistry:
    """
    Central registry for all qualitative-to-quantitative encoding rules.
    Implements the exact example rules from A5 and provides extensible framework.
    """

    def __init__(self):
        self.rules: Dict[str, Dict[str, QualitativeEncodingRule]] = {}
        self._initialize_builtin_rules()

    def _initialize_builtin_rules(self):
        """Initialize all built-in encoding rules per A5 specification."""
        
        # ========================================================================
        # DIET-RELATED ENCODINGS (A5 Example Rules)
        # ========================================================================
        
        # "High sodium diet" → +0.35 dehydration risk weight, +0.20 BP risk weight
        self.register_rule(
            input_field="diet.sodium_intake",
            input_value="high",
            rule=QualitativeEncodingRule(
                input_field="diet.sodium_intake",
                input_value="high",
                standardized_code="DIET_SODIUM_HIGH",
                numeric_weight=1.35,
                time_window="chronic",
                direction_of_effect={
                    "dehydration_risk": 0.35,
                    "bp_risk": 0.20,
                    "sodium_na_expected": 0.15
                },
                notes="High sodium diet increases dehydration risk and BP risk per A5 example"
            )
        )
        
        self.register_rule(
            input_field="diet.sodium_intake",
            input_value="low",
            rule=QualitativeEncodingRule(
                input_field="diet.sodium_intake",
                input_value="low",
                standardized_code="DIET_SODIUM_LOW",
                numeric_weight=0.75,
                time_window="chronic",
                direction_of_effect={
                    "dehydration_risk": -0.15,
                    "bp_risk": -0.10,
                    "sodium_na_expected": -0.10
                },
                notes="Low sodium diet reduces baseline sodium and BP risk"
            )
        )
        
        # "Keto diet" → ketone likelihood +0.60, TG variability modifier +0.20
        self.register_rule(
            input_field="diet.pattern",
            input_value="keto",
            rule=QualitativeEncodingRule(
                input_field="diet.pattern",
                input_value="keto",
                standardized_code="DIET_PATTERN_KETO",
                numeric_weight=1.60,
                time_window="chronic",
                direction_of_effect={
                    "ketone_likelihood": 0.60,
                    "triglyceride_variability": 0.20,
                    "glucose_baseline_modifier": -0.15,
                    "insulin_resistance_modifier": -0.25
                },
                notes="Keto diet per A5 example: increases ketones, affects TG and glucose patterns"
            )
        )
        
        self.register_rule(
            input_field="diet.pattern",
            input_value="high_protein",
            rule=QualitativeEncodingRule(
                input_field="diet.pattern",
                input_value="high_protein",
                standardized_code="DIET_PATTERN_HIGH_PROTEIN",
                numeric_weight=1.20,
                time_window="chronic",
                direction_of_effect={
                    "bun_expected": 0.15,
                    "creatinine_expected": 0.10,
                    "uric_acid_expected": 0.12
                },
                notes="High protein diet affects renal markers"
            )
        )
        
        # Hydration
        self.register_rule(
            input_field="diet.hydration_intake",
            input_value="low",
            rule=QualitativeEncodingRule(
                input_field="diet.hydration_intake",
                input_value="low",
                standardized_code="HYDRATION_LOW",
                numeric_weight=1.40,
                time_window="acute",
                direction_of_effect={
                    "dehydration_risk": 0.40,
                    "sodium_na_expected": 0.20,
                    "hematocrit_expected": 0.10,
                    "urine_specific_gravity_expected": 0.15
                },
                notes="Low hydration increases dehydration risk and concentrates analytes"
            )
        )
        
        self.register_rule(
            input_field="diet.hydration_intake",
            input_value="high",
            rule=QualitativeEncodingRule(
                input_field="diet.hydration_intake",
                input_value="high",
                standardized_code="HYDRATION_HIGH",
                numeric_weight=0.75,
                time_window="acute",
                direction_of_effect={
                    "dehydration_risk": -0.25,
                    "sodium_na_expected": -0.10,
                    "hematocrit_expected": -0.05
                },
                notes="High hydration reduces dehydration risk"
            )
        )
        
        # Caffeine
        # "High caffeine" → sympathetic dominance modifier +0.20
        self.register_rule(
            input_field="diet.caffeine",
            input_value="high",
            rule=QualitativeEncodingRule(
                input_field="diet.caffeine",
                input_value="high",
                standardized_code="CAFFEINE_HIGH",
                numeric_weight=1.20,
                time_window="acute",
                direction_of_effect={
                    "sympathetic_dominance": 0.20,
                    "heart_rate_baseline": 0.10,
                    "cortisol_proxy": 0.15
                },
                notes="High caffeine per A5 example: sympathetic dominance +0.20"
            )
        )
        
        # Alcohol
        self.register_rule(
            input_field="diet.alcohol",
            input_value="high",
            rule=QualitativeEncodingRule(
                input_field="diet.alcohol",
                input_value="high",
                standardized_code="ALCOHOL_HIGH",
                numeric_weight=1.30,
                time_window="chronic",
                direction_of_effect={
                    "triglyceride_expected": 0.20,
                    "alt_expected": 0.15,
                    "ast_expected": 0.15,
                    "hdl_expected": 0.10,
                    "inflammation_modifier": 0.18
                },
                notes="High alcohol affects liver enzymes, lipids, and inflammation"
            )
        )
        
        # ========================================================================
        # MEDICATION-RELATED ENCODINGS (A5 Example Rules)
        # ========================================================================
        
        # "Diuretic use" → +0.45 electrolyte instability weight, +0.30 dehydration risk weight
        self.register_rule(
            input_field="medications.special_flags",
            input_value="diuretics",
            rule=QualitativeEncodingRule(
                input_field="medications.special_flags",
                input_value="diuretics",
                standardized_code="MED_DIURETIC",
                numeric_weight=1.45,
                time_window="chronic",
                direction_of_effect={
                    "electrolyte_instability": 0.45,
                    "dehydration_risk": 0.30,
                    "potassium_k_expected": -0.20,
                    "sodium_na_variability": 0.25
                },
                notes="Diuretic per A5 example: electrolyte instability +0.45, dehydration +0.30"
            )
        )
        
        self.register_rule(
            input_field="medications.special_flags",
            input_value="beta_blockers",
            rule=QualitativeEncodingRule(
                input_field="medications.special_flags",
                input_value="beta_blockers",
                standardized_code="MED_BETA_BLOCKER",
                numeric_weight=0.85,
                time_window="chronic",
                direction_of_effect={
                    "heart_rate_baseline": -0.20,
                    "hrv_expected": 0.10,
                    "exercise_heart_rate_response": -0.30
                },
                notes="Beta blockers reduce HR and blunt exercise response"
            )
        )
        
        self.register_rule(
            input_field="medications.special_flags",
            input_value="statins",
            rule=QualitativeEncodingRule(
                input_field="medications.special_flags",
                input_value="statins",
                standardized_code="MED_STATIN",
                numeric_weight=0.75,
                time_window="chronic",
                direction_of_effect={
                    "ldl_expected": -0.30,
                    "total_cholesterol_expected": -0.20,
                    "creatine_kinase_risk": 0.10
                },
                notes="Statins lower LDL/cholesterol, may affect CK"
            )
        )
        
        self.register_rule(
            input_field="medications.special_flags",
            input_value="glp1",
            rule=QualitativeEncodingRule(
                input_field="medications.special_flags",
                input_value="glp1",
                standardized_code="MED_GLP1",
                numeric_weight=0.80,
                time_window="chronic",
                direction_of_effect={
                    "glucose_baseline": -0.25,
                    "a1c_expected": -0.30,
                    "weight_trajectory": -0.15,
                    "triglyceride_expected": -0.10
                },
                notes="GLP-1 agonists improve glucose control and weight"
            )
        )
        
        self.register_rule(
            input_field="medications.special_flags",
            input_value="thyroid_meds",
            rule=QualitativeEncodingRule(
                input_field="medications.special_flags",
                input_value="thyroid_meds",
                standardized_code="MED_THYROID",
                numeric_weight=1.10,
                time_window="chronic",
                direction_of_effect={
                    "tsh_target_range_modifier": 0.15,
                    "metabolic_rate_modifier": 0.10,
                    "heart_rate_baseline": 0.08
                },
                notes="Thyroid meds affect TSH targets and metabolic rate"
            )
        )
        
        self.register_rule(
            input_field="medications.special_flags",
            input_value="steroids",
            rule=QualitativeEncodingRule(
                input_field="medications.special_flags",
                input_value="steroids",
                standardized_code="MED_STEROID",
                numeric_weight=1.40,
                time_window="acute",
                direction_of_effect={
                    "glucose_expected": 0.35,
                    "inflammation_markers_suppression": -0.40,
                    "wbc_expected": 0.20,
                    "insulin_resistance_modifier": 0.30
                },
                notes="Steroids increase glucose, suppress inflammatory markers"
            )
        )
        
        # ========================================================================
        # ACTIVITY & LIFESTYLE ENCODINGS
        # ========================================================================
        
        # "Poor sleep" → inflammation index modifier +0.25, insulin resistance modifier +0.20
        self.register_rule(
            input_field="activity_lifestyle.sleep_schedule_consistency",
            input_value="inconsistent",
            rule=QualitativeEncodingRule(
                input_field="activity_lifestyle.sleep_schedule_consistency",
                input_value="inconsistent",
                standardized_code="SLEEP_POOR",
                numeric_weight=1.25,
                time_window="chronic",
                direction_of_effect={
                    "inflammation_index": 0.25,
                    "insulin_resistance_modifier": 0.20,
                    "cortisol_variability": 0.18,
                    "hrv_expected": -0.15
                },
                notes="Poor sleep per A5 example: inflammation +0.25, insulin resistance +0.20"
            )
        )
        
        self.register_rule(
            input_field="activity_lifestyle.activity_level",
            input_value="sedentary",
            rule=QualitativeEncodingRule(
                input_field="activity_lifestyle.activity_level",
                input_value="sedentary",
                standardized_code="ACTIVITY_SEDENTARY",
                numeric_weight=1.20,
                time_window="chronic",
                direction_of_effect={
                    "insulin_resistance_modifier": 0.25,
                    "triglyceride_expected": 0.15,
                    "hdl_expected": -0.10,
                    "vo2max_proxy": -0.20
                },
                notes="Sedentary lifestyle increases metabolic risk"
            )
        )
        
        self.register_rule(
            input_field="activity_lifestyle.activity_level",
            input_value="high",
            rule=QualitativeEncodingRule(
                input_field="activity_lifestyle.activity_level",
                input_value="high",
                standardized_code="ACTIVITY_HIGH",
                numeric_weight=0.80,
                time_window="chronic",
                direction_of_effect={
                    "insulin_sensitivity_modifier": 0.20,
                    "hdl_expected": 0.15,
                    "triglyceride_expected": -0.12,
                    "vo2max_proxy": 0.25,
                    "creatine_kinase_baseline": 0.15
                },
                notes="High activity improves metabolic health, may elevate CK baseline"
            )
        )
        
        self.register_rule(
            input_field="activity_lifestyle.shift_work",
            input_value="true",
            rule=QualitativeEncodingRule(
                input_field="activity_lifestyle.shift_work",
                input_value="true",
                standardized_code="SHIFT_WORK_YES",
                numeric_weight=1.25,
                time_window="chronic",
                direction_of_effect={
                    "cortisol_rhythm_disruption": 0.30,
                    "glucose_variability": 0.18,
                    "inflammation_index": 0.15,
                    "sleep_quality_penalty": 0.20
                },
                notes="Shift work disrupts circadian rhythms and metabolic health"
            )
        )
        
        self.register_rule(
            input_field="activity_lifestyle.nicotine_tobacco",
            input_value="current",
            rule=QualitativeEncodingRule(
                input_field="activity_lifestyle.nicotine_tobacco",
                input_value="current",
                standardized_code="TOBACCO_CURRENT",
                numeric_weight=1.35,
                time_window="chronic",
                direction_of_effect={
                    "inflammation_index": 0.30,
                    "oxidative_stress_modifier": 0.35,
                    "hdl_expected": -0.12,
                    "wbc_expected": 0.15,
                    "cardiovascular_risk": 0.40
                },
                notes="Current tobacco use significantly increases inflammation and cardiovascular risk"
            )
        )
        
        # ========================================================================
        # MEDICAL HISTORY ENCODINGS
        # ========================================================================
        
        self.register_rule(
            input_field="medical_history.conditions",
            input_value="diabetes",
            rule=QualitativeEncodingRule(
                input_field="medical_history.conditions",
                input_value="diabetes",
                standardized_code="DX_DIABETES",
                numeric_weight=1.50,
                time_window="chronic",
                direction_of_effect={
                    "glucose_baseline": 0.40,
                    "a1c_expected": 0.45,
                    "triglyceride_expected": 0.20,
                    "egfr_risk_modifier": 0.25,
                    "cardiovascular_risk": 0.35
                },
                notes="Diabetes diagnosis affects glucose, A1C, lipids, and renal/CV risk"
            )
        )
        
        self.register_rule(
            input_field="medical_history.conditions",
            input_value="prediabetes",
            rule=QualitativeEncodingRule(
                input_field="medical_history.conditions",
                input_value="prediabetes",
                standardized_code="DX_PREDIABETES",
                numeric_weight=1.25,
                time_window="chronic",
                direction_of_effect={
                    "glucose_baseline": 0.20,
                    "a1c_expected": 0.22,
                    "insulin_resistance_modifier": 0.30,
                    "triglyceride_expected": 0.12
                },
                notes="Prediabetes indicates elevated glucose and insulin resistance"
            )
        )
        
        self.register_rule(
            input_field="medical_history.conditions",
            input_value="HTN",
            rule=QualitativeEncodingRule(
                input_field="medical_history.conditions",
                input_value="HTN",
                standardized_code="DX_HTN",
                numeric_weight=1.30,
                time_window="chronic",
                direction_of_effect={
                    "bp_baseline": 0.25,
                    "sodium_sensitivity": 0.20,
                    "egfr_risk_modifier": 0.18,
                    "cardiovascular_risk": 0.30
                },
                notes="Hypertension affects BP targets and CV/renal risk"
            )
        )
        
        self.register_rule(
            input_field="medical_history.conditions",
            input_value="CKD",
            rule=QualitativeEncodingRule(
                input_field="medical_history.conditions",
                input_value="CKD",
                standardized_code="DX_CKD",
                numeric_weight=1.40,
                time_window="chronic",
                direction_of_effect={
                    "creatinine_expected": 0.35,
                    "egfr_baseline": -0.40,
                    "potassium_k_risk": 0.25,
                    "phosphate_expected": 0.20,
                    "anemia_risk": 0.30
                },
                notes="CKD affects renal markers, electrolytes, and anemia risk"
            )
        )
        
        self.register_rule(
            input_field="medical_history.conditions",
            input_value="thyroid_disease",
            rule=QualitativeEncodingRule(
                input_field="medical_history.conditions",
                input_value="thyroid_disease",
                standardized_code="DX_THYROID",
                numeric_weight=1.20,
                time_window="chronic",
                direction_of_effect={
                    "tsh_monitoring_importance": 0.40,
                    "metabolic_rate_variability": 0.25,
                    "cholesterol_variability": 0.15,
                    "heart_rate_variability": 0.18
                },
                notes="Thyroid disease requires TSH monitoring and affects metabolism"
            )
        )
        
        # ========================================================================
        # DEMOGRAPHIC ENCODINGS (Age, Sex, Pregnancy)
        # ========================================================================
        
        self.register_rule(
            input_field="demographics.pregnancy_status",
            input_value="pregnant",
            rule=QualitativeEncodingRule(
                input_field="demographics.pregnancy_status",
                input_value="pregnant",
                standardized_code="PREG_YES",
                numeric_weight=1.30,
                time_window="acute",
                direction_of_effect={
                    "glucose_screening_importance": 0.50,
                    "hemoglobin_expected": -0.15,
                    "thyroid_monitoring_importance": 0.30,
                    "blood_volume_expansion": 0.25
                },
                notes="Pregnancy affects multiple analytes and monitoring priorities"
            )
        )

    def register_rule(self, input_field: str, input_value: str, rule: QualitativeEncodingRule):
        """Register a new encoding rule."""
        if input_field not in self.rules:
            self.rules[input_field] = {}
        self.rules[input_field][input_value.lower()] = rule

    def get_rule(self, input_field: str, input_value: str) -> Optional[QualitativeEncodingRule]:
        """Retrieve an encoding rule."""
        field_rules = self.rules.get(input_field, {})
        return field_rules.get(input_value.lower())

    def encode_qualitative_inputs(self, soap_profile: dict) -> List[QualitativeEncodingRule]:
        """
        Process a complete SOAP profile and return all applicable encoding rules.
        This is the main entry point for qualitative encoding.
        """
        applied_rules = []

        # Process diet fields
        if "diet" in soap_profile:
            diet = soap_profile["diet"]
            for field_name in ["sodium_intake", "hydration_intake", "caffeine", "alcohol", "pattern", "meal_timing"]:
                if field_name in diet and diet[field_name]:
                    rule = self.get_rule(f"diet.{field_name}", str(diet[field_name]))
                    if rule:
                        applied_rules.append(rule)

        # Process activity/lifestyle fields
        if "activity_lifestyle" in soap_profile:
            lifestyle = soap_profile["activity_lifestyle"]
            for field_name in ["activity_level", "sleep_schedule_consistency", "nicotine_tobacco", "shift_work"]:
                if field_name in lifestyle and lifestyle[field_name] is not None:
                    value = str(lifestyle[field_name])
                    rule = self.get_rule(f"activity_lifestyle.{field_name}", value)
                    if rule:
                        applied_rules.append(rule)

        # Process medical history conditions
        if "medical_history" in soap_profile and "conditions" in soap_profile["medical_history"]:
            for condition in soap_profile["medical_history"]["conditions"]:
                rule = self.get_rule("medical_history.conditions", condition)
                if rule:
                    applied_rules.append(rule)

        # Process medication special flags
        if "medications_supplements" in soap_profile:
            meds = soap_profile["medications_supplements"]
            if "medications" in meds:
                for med in meds["medications"]:
                    if "special_flags" in med:
                        for flag in med["special_flags"]:
                            rule = self.get_rule("medications.special_flags", flag)
                            if rule:
                                applied_rules.append(rule)

        # Process demographics (pregnancy)
        if "demographics_anthropometrics" in soap_profile:
            demo = soap_profile["demographics_anthropometrics"]
            if "pregnancy_status" in demo and demo["pregnancy_status"]:
                rule = self.get_rule("demographics.pregnancy_status", demo["pregnancy_status"])
                if rule:
                    applied_rules.append(rule)

        return applied_rules

    def compute_aggregate_modifiers(self, applied_rules: List[QualitativeEncodingRule]) -> Dict[str, float]:
        """
        Compute aggregate modifiers from all applied encoding rules.
        Returns a dictionary of output_key -> total_modifier.
        """
        aggregate = {}
        
        for rule in applied_rules:
            for output_key, effect_value in rule.direction_of_effect.items():
                if output_key not in aggregate:
                    aggregate[output_key] = 0.0
                aggregate[output_key] += effect_value
        
        return aggregate


# Global encoding registry instance
ENCODING_REGISTRY = EncodingRegistry()


def get_encoding_registry() -> EncodingRegistry:
    """Get the global encoding registry."""
    return ENCODING_REGISTRY
