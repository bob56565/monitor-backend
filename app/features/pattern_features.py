"""
Pattern and combination feature layer: temporal windows, motifs, discordance detection.
"""

from typing import Dict, List, Tuple, Optional
from app.models.run_v2 import RunV2, SpecimenTypeEnum
from app.models.feature_pack_v2 import (
    PatternCombinationFeatures, MotifDetection, MotifEnum, RegimeEnum,
    DerivedTemporalFeatures, DiscordanceDetection
)


def compute_temporal_features(run_v2: RunV2) -> List[DerivedTemporalFeatures]:
    """
    Compute temporal features for each specimen: volatility, stability, trend, regime.
    """
    temporal_features_list = []
    
    for specimen in run_v2.specimens:
        specimen_id = specimen.specimen_id
        
        # Get primary variable (glucose for ISF/Blood, cortisol for Saliva, etc.)
        primary_var = _get_primary_variable(specimen.specimen_type)
        
        # Defensive: check if primary variable exists in missingness dict
        if primary_var and primary_var in specimen.missingness:
            missingness_entry = specimen.missingness[primary_var]
            is_missing = missingness_entry.is_missing if hasattr(missingness_entry, 'is_missing') else True
            
            if not is_missing:
                value = specimen.raw_values.get(primary_var)
            
            # Compute volatility (would normally need time series, using static value as proxy)
            volatility_5m = _estimate_volatility(value, specimen.specimen_type, window="5m")
            volatility_30m = _estimate_volatility(value, specimen.specimen_type, window="30m")
            volatility_2h = _estimate_volatility(value, specimen.specimen_type, window="2h")
            
            # Stability score (inverse of volatility)
            avg_volatility = (volatility_5m + volatility_30m + volatility_2h) / 3.0
            stability_score = 1.0 - min(avg_volatility / 100.0, 1.0)  # Normalize
            
            # Trend direction (from non-lab context or specimen data)
            trend_direction = _infer_trend_direction(specimen, primary_var)
            
            # Regime detection
            regime, regime_confidence = _detect_regime(run_v2, specimen)
            
            temporal_features_list.append(
                DerivedTemporalFeatures(
                    specimen_id=specimen_id,
                    volatility_5m=volatility_5m,
                    volatility_30m=volatility_30m,
                    volatility_2h=volatility_2h,
                    stability_score_0_1=stability_score,
                    trend_direction=trend_direction,
                    regime_detected=regime,
                    regime_confidence_0_1=regime_confidence,
                )
            )
    
    return temporal_features_list


def detect_motifs(run_v2: RunV2, temporal_features: List[DerivedTemporalFeatures]) -> List[MotifDetection]:
    """
    Detect named metabolic/physiological motifs from multi-variable patterns.
    """
    detected_motifs = []
    
    # Extract ISF values if available
    isf_glucose = _get_value(run_v2, SpecimenTypeEnum.ISF, "glucose")
    isf_lactate = _get_value(run_v2, SpecimenTypeEnum.ISF, "lactate")
    
    # Extract blood values
    blood_glucose = _get_value(run_v2, SpecimenTypeEnum.BLOOD_VENOUS, "glucose")
    
    # Extract context
    activity_level = _get_nonlab(run_v2, "sleep_activity.activity_level_0_10")
    diet_pattern = None
    if run_v2.qualitative_inputs and run_v2.qualitative_inputs.diet_recent:
        diet_pattern = run_v2.qualitative_inputs.diet_recent.get("pattern")
    
    # Motif 1: Glucose + Lactate up with exertion marker
    if (isf_glucose is not None and isf_glucose > 120 and
        isf_lactate is not None and isf_lactate > 2.0 and
        activity_level is not None and activity_level > 7):
        
        detected_motifs.append(
            MotifDetection(
                motif_type=MotifEnum.GLUCOSE_LACTATE_UP_EXERTION,
                motif_strength_0_1=0.9,
                supporting_variables=["glucose", "lactate", "activity_level"],
                expected_context="post-exercise or active period",
                confidence_0_1=0.85,
            )
        )
    
    # Motif 2: Glucose + Lactate up with post-meal marker
    elif (isf_glucose is not None and isf_glucose > 130 and
          isf_lactate is not None and isf_lactate > 1.5 and
          diet_pattern in ["high_carb", "mixed"]):
        
        detected_motifs.append(
            MotifDetection(
                motif_type=MotifEnum.GLUCOSE_LACTATE_UP_MEAL,
                motif_strength_0_1=0.85,
                supporting_variables=["glucose", "lactate", "diet_pattern"],
                expected_context="post-prandial (2-3h after meal)",
                confidence_0_1=0.8,
            )
        )
    
    # Motif 3: Dehydration stress (electrolytes + hydration markers)
    na = _get_value(run_v2, SpecimenTypeEnum.BLOOD_VENOUS, "sodium_na")
    urine_sg = _get_value(run_v2, SpecimenTypeEnum.URINE_SPOT, "specific_gravity")
    hrv = _get_nonlab(run_v2, "vitals_physiology.hrv")
    
    if (na is not None and na > 145 and
        urine_sg is not None and urine_sg > 1.025 and
        hrv is not None and hrv < 20):
        
        detected_motifs.append(
            MotifDetection(
                motif_type=MotifEnum.DEHYDRATION_STRESS,
                motif_strength_0_1=0.8,
                supporting_variables=["sodium_na", "specific_gravity", "hrv"],
                expected_context="dehydration + sympathetic activation",
                confidence_0_1=0.75,
            )
        )
    
    # Motif 4: Inflammatory/sleep fragmentation
    crp = _get_value(run_v2, SpecimenTypeEnum.BLOOD_VENOUS, "crp")
    sleep_quality = _get_nonlab(run_v2, "sleep_activity.sleep_quality_0_10")
    
    if (crp is not None and crp > 3.0 and
        sleep_quality is not None and sleep_quality < 5):
        
        detected_motifs.append(
            MotifDetection(
                motif_type=MotifEnum.INFLAMMATORY_SLEEP_FRAGMENTATION,
                motif_strength_0_1=0.75,
                supporting_variables=["crp", "sleep_quality"],
                expected_context="systemic inflammation + poor sleep (bidirectional)",
                confidence_0_1=0.7,
            )
        )
    
    return detected_motifs


def compute_temporal_windows_features(run_v2: RunV2) -> Dict[str, Dict[str, float]]:
    """
    Compute aggregated features over multiple time windows (5m, 30m, 2h, 24h).
    """
    windows_features = {
        "5m": {},
        "30m": {},
        "2h": {},
        "24h": {},
    }
    
    # Aggregates per window (using static data, would need time series for full implementation)
    for specimen in run_v2.specimens:
        # Average glucose across windows (conceptual)
        glucose = specimen.raw_values.get("glucose")
        if glucose is not None:
            windows_features["5m"]["glucose_avg"] = glucose
            windows_features["30m"]["glucose_avg"] = glucose * 0.95  # Slight variation
            windows_features["2h"]["glucose_avg"] = glucose * 0.9
            windows_features["24h"]["glucose_avg"] = glucose * 0.85
    
    # Add lactate features
    for specimen in run_v2.specimens:
        lactate = specimen.raw_values.get("lactate")
        if lactate is not None:
            windows_features["5m"]["lactate_avg"] = lactate
            windows_features["30m"]["lactate_avg"] = lactate * 0.98
            windows_features["2h"]["lactate_avg"] = lactate * 0.9
    
    return windows_features


def detect_discordance(run_v2: RunV2) -> DiscordanceDetection:
    """
    Detect disagreement between specimens and unexplained inconsistencies.
    """
    discordance_flags = []
    discordance_explanations = []
    specimen_agreement_scores = {}
    
    # ISF vs Blood Glucose
    isf_glucose = _get_value(run_v2, SpecimenTypeEnum.ISF, "glucose")
    blood_glucose = _get_value(run_v2, SpecimenTypeEnum.BLOOD_VENOUS, "glucose")
    
    if isf_glucose is not None and blood_glucose is not None:
        diff_pct = abs(blood_glucose - isf_glucose) / max(isf_glucose, 1.0)
        
        if diff_pct > 0.2:  # >20% difference
            discordance_flags.append("blood_glucose_differs_from_isf_by_>20pct")
            
            # Explain the discordance
            if isf_glucose > blood_glucose * 1.2:
                explanation = "ISF is elevated relative to blood glucose. May be lag, local inflammation, or sensor artifact."
                discordance_explanations.append({
                    "flag": "blood_glucose_differs_from_isf_by_>20pct",
                    "explanation_bucket": "lag|artifact",
                })
            else:
                explanation = "Blood glucose elevated relative to ISF. Possible perfusion issue or ISF lag."
                discordance_explanations.append({
                    "flag": "blood_glucose_differs_from_isf_by_>20pct",
                    "explanation_bucket": "lag|unknown",
                })
        
        agreement_score = 1.0 - min(diff_pct, 1.0)
        specimen_agreement_scores["isf_vs_blood"] = agreement_score
    
    # Activity high but lactate flat
    lactate = _get_value(run_v2, SpecimenTypeEnum.ISF, "lactate")
    activity_level = _get_nonlab(run_v2, "sleep_activity.activity_level_0_10")
    
    if lactate is not None and activity_level is not None:
        if activity_level > 7 and lactate < 1.5:
            discordance_flags.append("activity_high_but_lactate_flat")
            discordance_explanations.append({
                "flag": "activity_high_but_lactate_flat",
                "explanation_bucket": "lag|unknown",
            })
            specimen_agreement_scores["activity_vs_lactate"] = 0.3
    
    return DiscordanceDetection(
        discordance_flags=discordance_flags,
        discordance_explanations=discordance_explanations,
        specimen_agreement_scores=specimen_agreement_scores,
    )


def build_pattern_combination_features(
    run_v2: RunV2,
    temporal_features: List[DerivedTemporalFeatures]
) -> PatternCombinationFeatures:
    """
    Orchestrate pattern detection and return consolidated output.
    """
    
    motifs = detect_motifs(run_v2, temporal_features)
    windows_features = compute_temporal_windows_features(run_v2)
    
    # Build regime labels from temporal features
    regime_labels = [
        {
            "time_window": f"specimen_{i}",
            "regime": tf.regime_detected.value,
            "confidence": tf.regime_confidence_0_1,
        }
        for i, tf in enumerate(temporal_features)
    ]
    
    return PatternCombinationFeatures(
        detected_motifs=motifs,
        temporal_windows_features=windows_features,
        regime_labels=regime_labels,
    )


# Helper functions
def _get_primary_variable(specimen_type: SpecimenTypeEnum) -> Optional[str]:
    """Get the primary measured variable for a specimen type."""
    mapping = {
        SpecimenTypeEnum.ISF: "glucose",
        SpecimenTypeEnum.BLOOD_CAPILLARY: "glucose",
        SpecimenTypeEnum.BLOOD_VENOUS: "glucose",
        SpecimenTypeEnum.SALIVA: "cortisol_morning",
        SpecimenTypeEnum.SWEAT: "sweat_rate",
        SpecimenTypeEnum.URINE_SPOT: "specific_gravity",
    }
    return mapping.get(specimen_type)


def _estimate_volatility(value: float, specimen_type: SpecimenTypeEnum, window: str) -> float:
    """
    Estimate volatility for a given value and specimen type.
    (In real implementation, would compute from time series)
    """
    # Baseline volatility by specimen type
    base_volatility = {
        SpecimenTypeEnum.ISF: 5.0,
        SpecimenTypeEnum.BLOOD_CAPILLARY: 8.0,
        SpecimenTypeEnum.BLOOD_VENOUS: 10.0,
        SpecimenTypeEnum.SALIVA: 15.0,
        SpecimenTypeEnum.SWEAT: 20.0,
        SpecimenTypeEnum.URINE_SPOT: 5.0,
    }
    
    base = base_volatility.get(specimen_type, 10.0)
    
    # Window scaling
    window_factor = {"5m": 1.0, "30m": 1.2, "2h": 1.5, "24h": 2.0}.get(window, 1.0)
    
    return base * window_factor


def _infer_trend_direction(specimen, primary_var: str) -> Optional[str]:
    """Infer trend from specimen data (would need time series in real scenario)."""
    # For now, return "stable" as default
    return "stable"


def _detect_regime(run_v2: RunV2, specimen) -> Tuple[RegimeEnum, float]:
    """Detect metabolic regime from specimen and context."""
    # Simple heuristic
    activity_level = _get_nonlab(run_v2, "sleep_activity.activity_level_0_10")
    sleep_quality = _get_nonlab(run_v2, "sleep_activity.sleep_quality_0_10")
    
    if sleep_quality is not None and sleep_quality > 7:
        return RegimeEnum.SLEEP, 0.8
    elif activity_level is not None and activity_level > 7:
        return RegimeEnum.EXERTION, 0.8
    else:
        return RegimeEnum.UNKNOWN, 0.5


def _get_value(run_v2: RunV2, specimen_type, var_name: str) -> Optional[float]:
    """Get a value from a specimen of a given type."""
    for specimen in run_v2.specimens:
        if specimen.specimen_type == specimen_type:
            # Defensive: check if variable exists in missingness dict
            if var_name in specimen.missingness:
                missingness_entry = specimen.missingness[var_name]
                is_missing = missingness_entry.is_missing if hasattr(missingness_entry, 'is_missing') else True
                if not is_missing:
                    val = specimen.raw_values.get(var_name)
                    return float(val) if val is not None else None
    return None
    return None


def _get_nonlab(run_v2: RunV2, path: str) -> Optional[float]:
    """Get non-lab input value by path."""
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
