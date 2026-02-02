"""
Preprocess V2 Pipeline: Orchestrates all feature engineering modules.
Produces feature_pack_v2 with missingness-aware, cross-specimen coherence-aware features.
"""

from datetime import datetime
from typing import Optional, List
import logging

from app.models.run_v2 import RunV2
from app.models.feature_pack_v2 import (
    FeaturePackV2, SpecimenNormalizedValues, CoherenceScores, PenaltyVector
)
from app.features.missingness_features import (
    compute_missingness_feature_vector, get_domain_presence_summary
)
from app.features.cross_specimen_modeling import build_cross_specimen_relationships
from app.features.pattern_features import (
    compute_temporal_features, build_pattern_combination_features, detect_discordance
)

logger = logging.getLogger(__name__)


def preprocess_v2(run_v2: RunV2) -> FeaturePackV2:
    """
    Main preprocess v2 pipeline.
    
    Inputs: RunV2 with specimens, non_lab_inputs, qualitative_inputs
    Outputs: feature_pack_v2 with all advanced features, coherence scores, penalties
    
    Non-breaking: produces feature_pack_v2 without modifying legacy features.
    """
    
    logger.info(f"Starting preprocess_v2 for run_id {run_v2.run_id} with {len(run_v2.specimens)} specimens")
    
    # Step 1: Missingness-aware feature construction
    missingness_vector = compute_missingness_feature_vector(run_v2)
    logger.debug(f"Aggregate missingness: {missingness_vector.aggregate_missingness_0_1:.2f}")
    
    # Step 2: Normalize specimen values
    normalized_values = _compute_normalized_values(run_v2)
    
    # Step 3: Temporal features
    temporal_features = compute_temporal_features(run_v2)
    
    # Step 4: Cross-specimen relationships
    cross_specimen_rels = build_cross_specimen_relationships(run_v2)
    
    # Step 5: Pattern/combination features
    pattern_features = build_pattern_combination_features(run_v2, temporal_features)
    discordance = detect_discordance(run_v2)
    
    # Step 6: Compute coherence scores
    coherence_scores = _compute_coherence_scores(
        cross_specimen_rels,
        missingness_vector,
        pattern_features,
        discordance
    )
    
    # Step 7: Compute penalty vector for Phase 3 gating
    penalty_vector = _compute_penalty_vector(
        missingness_vector,
        cross_specimen_rels,
        coherence_scores
    )
    
    # Step 8: Extract qualitative effect vector if available
    qual_effect_vector = None
    if run_v2.encoding_outputs:
        qual_effect_vector = run_v2.encoding_outputs.effect_vector
    
    # Step 9: Gather domain presence
    domain_presence = get_domain_presence_summary(run_v2)
    domains_present = [d for d, present in domain_presence.items() if present]
    
    # Step 10: Build processing notes
    processing_notes = [
        f"Processed {len(run_v2.specimens)} specimens",
        f"Domains present: {', '.join(domains_present)}",
        f"Overall coherence: {coherence_scores.overall_coherence_0_1:.2f}",
        f"Missingness: {missingness_vector.aggregate_missingness_0_1:.2f}",
    ]
    
    # Construct feature_pack_v2
    feature_pack_v2 = FeaturePackV2(
        run_id=run_v2.run_id,
        created_at=datetime.utcnow(),
        schema_version="feature_pack_v2.1",
        missingness_feature_vector=missingness_vector,
        specimen_normalized_values=normalized_values,
        derived_temporal_features=temporal_features,
        cross_specimen_relationships=cross_specimen_rels,
        pattern_combination_features=pattern_features,
        discordance_detection=discordance,
        coherence_scores=coherence_scores,
        penalty_vector=penalty_vector,
        specimen_count=len(run_v2.specimens),
        domains_present=domains_present,
        qualitative_effect_vector=qual_effect_vector,
        processing_notes=processing_notes,
    )
    
    logger.info(f"Completed preprocess_v2 for run_id {run_v2.run_id}")
    return feature_pack_v2


def _compute_normalized_values(run_v2: RunV2) -> List[SpecimenNormalizedValues]:
    """
    Normalize specimen values using population reference ranges.
    """
    normalized_list = []
    
    # Simple reference ranges (would be more sophisticated in production)
    reference_ranges = {
        "glucose": {"min": 70, "max": 100, "ref_point": 85},
        "lactate": {"min": 0.5, "max": 2.0, "ref_point": 1.2},
        "sodium_na": {"min": 135, "max": 145, "ref_point": 140},
        "crp": {"min": 0.0, "max": 3.0, "ref_point": 1.0},
        "hgb": {"min": 12, "max": 17, "ref_point": 14.5},
    }
    
    for specimen in run_v2.specimens:
        normalized_vals = {}
        normalization_refs = {}
        validity_flags = {}
        
        for var_name, raw_value in specimen.raw_values.items():
            # Defensive: check if missingness entry exists
            is_missing = specimen.missingness.get(var_name, {}).get('is_missing', True) if isinstance(specimen.missingness.get(var_name), dict) else (specimen.missingness[var_name].is_missing if var_name in specimen.missingness else True)
            
            if is_missing or raw_value is None:
                normalized_vals[var_name] = None
                normalization_refs[var_name] = "missing"
                validity_flags[var_name] = False
            else:
                raw_float = float(raw_value)
                
                if var_name in reference_ranges:
                    ref = reference_ranges[var_name]
                    # Z-score normalization
                    ref_mean = ref["ref_point"]
                    ref_sd = (ref["max"] - ref["min"]) / 4.0  # Rough SD estimate
                    z_score = (raw_float - ref_mean) / ref_sd if ref_sd > 0 else 0.0
                    
                    normalized_vals[var_name] = z_score
                    normalization_refs[var_name] = "population_mean"
                    validity_flags[var_name] = ref["min"] <= raw_float <= ref["max"]
                else:
                    # Unknown variable, store raw
                    normalized_vals[var_name] = raw_float
                    normalization_refs[var_name] = "raw"
                    validity_flags[var_name] = True
        
        normalized_list.append(
            SpecimenNormalizedValues(
                specimen_id=specimen.specimen_id,
                specimen_type=specimen.specimen_type.value,
                normalized_values=normalized_vals,
                normalization_references_used=normalization_refs,
                value_validity_flags=validity_flags,
            )
        )
    
    return normalized_list


def _compute_coherence_scores(
    cross_specimen_rels,
    missingness_vector,
    pattern_features,
    discordance
) -> CoherenceScores:
    """
    Compute overall coherence score from all cross-specimen and pattern signals.
    """
    
    lag_coherence = cross_specimen_rels.lag_model.lag_coherence_score_0_1
    
    plausibility_coherence = (
        cross_specimen_rels.plausibility.electrolyte_balance_score_0_1 +
        cross_specimen_rels.plausibility.hydration_mass_balance_score_0_1
    ) / 2.0
    
    triangulation_coherence = (
        (cross_specimen_rels.triangulation.stress_axis_coherence_0_1 or 0.5) +
        (cross_specimen_rels.triangulation.metabolic_exertion_coherence_0_1 or 0.5) +
        (cross_specimen_rels.triangulation.inflammation_sleep_coherence_0_1 or 0.5)
    ) / 3.0
    
    artifact_interference_coherence = 1.0 - cross_specimen_rels.artifact_risks.aggregate_interference_score_0_1
    
    # Penalize missingness on coherence
    missingness_penalty = missingness_vector.aggregate_missingness_0_1 * 0.3
    
    # Penalize discordance
    discordance_penalty = len(discordance.discordance_flags) * 0.1
    discordance_penalty = min(discordance_penalty, 0.5)
    
    # Overall coherence is weighted average
    overall_coherence = (
        0.25 * lag_coherence +
        0.25 * plausibility_coherence +
        0.25 * triangulation_coherence +
        0.15 * artifact_interference_coherence +
        0.10 * (1.0 - missingness_penalty) -
        discordance_penalty
    )
    overall_coherence = max(0.0, min(overall_coherence, 1.0))
    
    # Determine driver
    if lag_coherence < 0.6:
        coherence_driver = "lag_estimates_uncertain"
    elif plausibility_coherence < 0.6:
        coherence_driver = "plausibility_checks_failed"
    elif triangulation_coherence < 0.6:
        coherence_driver = "proxy_triangulation_weak"
    elif artifact_interference_coherence < 0.6:
        coherence_driver = "artifact_or_interference_risk_high"
    elif missingness_vector.aggregate_missingness_0_1 > 0.5:
        coherence_driver = "high_missingness"
    else:
        coherence_driver = "good_overall_coherence"
    
    return CoherenceScores(
        overall_coherence_0_1=overall_coherence,
        lag_coherence_0_1=lag_coherence,
        plausibility_coherence_0_1=plausibility_coherence,
        triangulation_coherence_0_1=triangulation_coherence,
        artifact_interference_coherence_0_1=artifact_interference_coherence,
        coherence_driver=coherence_driver,
    )


def _compute_penalty_vector(
    missingness_vector,
    cross_specimen_rels,
    coherence_scores
) -> PenaltyVector:
    """
    Compute penalties for Phase 3 inference gating.
    """
    
    penalty_factors = []
    domain_blockers = []
    confidence_reduction = 1.0
    
    # Missingness penalties
    if missingness_vector.aggregate_missingness_0_1 > 0.7:
        penalty_factors.append("high_missingness_>70pct")
        confidence_reduction *= 0.7
    elif missingness_vector.aggregate_missingness_0_1 > 0.5:
        penalty_factors.append("moderate_missingness_>50pct")
        confidence_reduction *= 0.85
    
    # Domain-level blockers
    for domain, is_critical_missing in missingness_vector.domain_critical_missing_flags.items():
        if is_critical_missing:
            domain_blockers.append(f"{domain}_domain_critical_anchor_missing")
            confidence_reduction *= 0.7
    
    # Coherence penalties
    if coherence_scores.overall_coherence_0_1 < 0.5:
        penalty_factors.append("coherence_score_low")
        confidence_reduction *= 0.6
    elif coherence_scores.overall_coherence_0_1 < 0.7:
        penalty_factors.append("coherence_score_moderate")
        confidence_reduction *= 0.8
    
    # Artifact/interference penalties
    if cross_specimen_rels.artifact_risks.aggregate_interference_score_0_1 > 0.7:
        penalty_factors.append("artifact_or_interference_risk_high")
        confidence_reduction *= 0.7
    
    # Plausibility penalties
    if len(cross_specimen_rels.plausibility.plausibility_penalties) > 0:
        for penalty_text in cross_specimen_rels.plausibility.plausibility_penalties:
            penalty_factors.append(f"plausibility:{penalty_text}")
            confidence_reduction *= 0.85
    
    # Medication interference
    if len(cross_specimen_rels.artifact_risks.medication_interference_flags) > 0:
        for med_flag in cross_specimen_rels.artifact_risks.medication_interference_flags:
            penalty_factors.append(f"med_interference:{med_flag}")
            confidence_reduction *= 0.9
    
    # Ensure confidence reduction factor is in [0, 1]
    confidence_reduction = max(0.0, min(confidence_reduction, 1.0))
    
    return PenaltyVector(
        penalty_factors=penalty_factors,
        domain_blockers=domain_blockers,
        confidence_reduction_factor_0_1=confidence_reduction,
    )
