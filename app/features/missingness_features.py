"""
Missingness-aware feature construction for feature_pack_v2.
Treats missingness as a first-class feature, not a gap to ignore.
"""

from typing import Dict, List, Tuple, Set
from app.models.run_v2 import RunV2, MissingTypeEnum, SpecimenRecord
from app.models.feature_pack_v2 import MissingnessFeatureVector


# Domain definitions
DOMAINS = {
    "metabolic": ["glucose", "lactate", "pyruvate"],
    "renal": ["creatinine", "bun", "uacr", "microalbumin"],
    "electrolyte": ["sodium_na", "potassium_k", "chloride_cl"],
    "hydration": ["specific_gravity", "urine_sg", "fluid_intake_ml_24h"],
    "liver": ["ast", "alt", "bilirubin_total", "alk_phos"],
    "lipid": ["chol_total", "ldl", "hdl", "triglycerides"],
    "endocrine": ["a1c", "tsh", "free_t4", "fasting_insulin"],
    "vitamins": ["vitamin_d_25oh", "b12", "folate", "ferritin", "iron"],
    "inflammation": ["crp", "esr", "crp_proxy", "cytokine_proxy_il6"],
    "autoimmune": ["ana", "rf", "anti_ccp", "dsdna"],
    "hematology": ["hgb", "hct", "wbc", "rbc", "platelets"],
}

# Critical anchors per domain (must be present for valid domain analysis)
CRITICAL_ANCHORS = {
    "metabolic": {"glucose"},
    "renal": {"creatinine"},
    "electrolyte": {"sodium_na", "potassium_k"},
    "hydration": {"specific_gravity"},
    "liver": {"ast", "alt"},
    "lipid": {"chol_total"},
    "endocrine": {"a1c", "tsh"},
    "vitamins": {"vitamin_d_25oh"},
    "inflammation": {"crp"},
    "autoimmune": {"ana"},
    "hematology": {"hgb", "wbc"},
}


def compute_missingness_feature_vector(run_v2: RunV2) -> MissingnessFeatureVector:
    """
    Compute missingness features for all variables across all specimens.
    
    Returns:
        MissingnessFeatureVector with:
        - Per-variable present flags
        - Missing type embeddings (one-hot)
        - Domain missingness scores
        - Critical anchor missing flags
    """
    
    specimen_present_flags = {}
    missing_type_embeddings = {}
    domain_var_presence = {domain: [] for domain in DOMAINS}
    
    # Iterate through specimens to gather missingness info
    for specimen in run_v2.specimens:
        specimen_id = specimen.specimen_id
        specimen_present_flags[specimen_id] = {}
        missing_type_embeddings[specimen_id] = {}
        
        for var_name, missingness_record in specimen.missingness.items():
            # Flag: is variable present?
            is_present = not missingness_record.is_missing
            specimen_present_flags[specimen_id][var_name] = is_present
            
            # One-hot encoding for missing_type
            missing_type_onehot = _encode_missing_type(missingness_record.missing_type)
            missing_type_embeddings[specimen_id][var_name] = missing_type_onehot
            
            # Track domain presence
            for domain, vars_in_domain in DOMAINS.items():
                if var_name in vars_in_domain:
                    domain_var_presence[domain].append(is_present)
    
    # Compute domain missingness scores
    domain_missingness_scores = {}
    domain_critical_missing_flags = {}
    
    for domain, var_list in DOMAINS.items():
        presence_for_domain = domain_var_presence.get(domain, [])
        
        if not presence_for_domain:
            # No variables from this domain present
            domain_missingness_scores[domain] = 1.0
            domain_critical_missing_flags[domain] = True
        else:
            # Fraction of variables present in this domain
            present_count = sum(presence_for_domain)
            missingness_fraction = 1.0 - (present_count / len(presence_for_domain))
            domain_missingness_scores[domain] = missingness_fraction
            
            # Critical anchor check
            has_critical_missing = False
            for specimen in run_v2.specimens:
                for critical_var in CRITICAL_ANCHORS.get(domain, set()):
                    # Defensive: check if variable exists in missingness dict
                    if critical_var in specimen.missingness:
                        missingness_entry = specimen.missingness[critical_var]
                        if hasattr(missingness_entry, 'is_missing') and missingness_entry.is_missing:
                            has_critical_missing = True
                            break
                    else:
                        # Variable not in missingness dict = missing
                        has_critical_missing = True
                        break
            domain_critical_missing_flags[domain] = has_critical_missing
    
    # Compute aggregate missingness
    all_present_flags = []
    for spec_flags in specimen_present_flags.values():
        all_present_flags.extend(spec_flags.values())
    
    aggregate_missingness = 1.0 - (sum(all_present_flags) / len(all_present_flags)) if all_present_flags else 0.0
    
    return MissingnessFeatureVector(
        specimen_variable_present_flags=specimen_present_flags,
        missing_type_embeddings=missing_type_embeddings,
        domain_missingness_scores=domain_missingness_scores,
        domain_critical_missing_flags=domain_critical_missing_flags,
        aggregate_missingness_0_1=aggregate_missingness,
    )


def _encode_missing_type(missing_type: str) -> List[int]:
    """
    One-hot encode missing_type.
    Order: not_collected, user_skipped, biologically_unavailable, temporarily_unavailable, sensor_unavailable, not_applicable
    """
    missing_types = [
        "not_collected",
        "user_skipped",
        "biologically_unavailable",
        "temporarily_unavailable",
        "sensor_unavailable",
        "not_applicable",
    ]
    
    if missing_type is None:
        # Not missing
        return [0] * len(missing_types)
    
    try:
        idx = missing_types.index(missing_type)
        encoding = [0] * len(missing_types)
        encoding[idx] = 1
        return encoding
    except (ValueError, AttributeError):
        # Unknown type
        return [0] * len(missing_types)


def get_domain_presence_summary(run_v2: RunV2) -> Dict[str, bool]:
    """
    Quick check: which domains have at least one variable present?
    """
    domain_present = {domain: False for domain in DOMAINS}
    
    for specimen in run_v2.specimens:
        for var_name in specimen.raw_values.keys():
            for domain, vars_in_domain in DOMAINS.items():
                # Defensive: check if variable exists in missingness dict
                if var_name in vars_in_domain and var_name in specimen.missingness:
                    missingness_entry = specimen.missingness[var_name]
                    is_missing = missingness_entry.is_missing if hasattr(missingness_entry, 'is_missing') else True
                    if not is_missing:
                        domain_present[domain] = True
    
    return domain_present
