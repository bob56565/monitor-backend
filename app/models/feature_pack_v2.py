"""
Feature Pack V2 schema and output structures.
Contains missingness-aware features, cross-specimen relationships, patterns, and coherence scores.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field


class RegimeEnum(str, Enum):
    """Activity/metabolic regimes detected from pattern analysis."""
    REST = "rest"
    EXERTION = "exertion"
    POSTPRANDIAL = "postprandial"
    SLEEP = "sleep"
    UNKNOWN = "unknown"


class MotifEnum(str, Enum):
    """Named metabolic/physiological motifs."""
    GLUCOSE_LACTATE_UP_EXERTION = "glucose_lactate_up_exertion"
    GLUCOSE_LACTATE_UP_MEAL = "glucose_lactate_up_meal"
    DEHYDRATION_STRESS = "dehydration_stress"
    INFLAMMATORY_SLEEP_FRAGMENTATION = "inflammatory_sleep_fragmentation"
    UNKNOWN = "unknown"


class MissingnessFeatureVector(BaseModel):
    """Missingness-aware features for each variable and domain."""
    specimen_variable_present_flags: Dict[str, Dict[str, bool]]  # specimen_id -> {var: bool}
    missing_type_embeddings: Dict[str, Dict[str, List[int]]]  # specimen_id -> {var: one-hot}
    domain_missingness_scores: Dict[str, float]  # domain -> score 0-1 (0=all present, 1=all missing)
    domain_critical_missing_flags: Dict[str, bool]  # domain -> has_critical_missing
    aggregate_missingness_0_1: float  # Overall missingness across all vars


class SpecimenNormalizedValues(BaseModel):
    """Normalized and standardized values per specimen."""
    specimen_id: str
    specimen_type: str
    normalized_values: Dict[str, Optional[float]]  # var -> z-score or normalized value
    normalization_references_used: Dict[str, str]  # var -> "population_mean" | "ref_range_midpoint" | "self_baseline"
    value_validity_flags: Dict[str, bool]  # var -> within_valid_range


class DerivedTemporalFeatures(BaseModel):
    """Temporal features computed within and across specimens."""
    specimen_id: str
    volatility_5m: Optional[float] = None
    volatility_30m: Optional[float] = None
    volatility_2h: Optional[float] = None
    stability_score_0_1: Optional[float] = None  # How stable/smooth vs noisy
    trend_direction: Optional[str] = None  # "up" | "down" | "stable"
    regime_detected: RegimeEnum = RegimeEnum.UNKNOWN
    regime_confidence_0_1: float = 0.0


class LagModelParams(BaseModel):
    """Cross-specimen kinetics/lag estimation."""
    isf_blood_lag_minutes_estimate: Optional[float] = None
    lag_uncertainty_minutes: Optional[float] = None
    event_anchored_lags: Dict[str, float] = Field(default_factory=dict)  # event_type -> lag_minutes
    lag_coherence_score_0_1: float = 0.5


class PlausibilityParams(BaseModel):
    """Conservation and mass balance plausibility checks."""
    electrolyte_balance_score_0_1: float = 0.5  # 1 = perfectly balanced, 0 = implausible
    hydration_mass_balance_score_0_1: float = 0.5  # Based on sweat/urine/intake consistency
    plausibility_penalties: List[str] = Field(default_factory=list)  # e.g., ["high_sweat_loss_inconsistent_fluid"]


class TriangulationScores(BaseModel):
    """Cross-proxy agreement scores."""
    stress_axis_coherence_0_1: Optional[float] = None  # Cortisol/HRV/sleep agreement
    metabolic_exertion_coherence_0_1: Optional[float] = None  # Lactate/glucose/activity agreement
    inflammation_sleep_coherence_0_1: Optional[float] = None  # CRP/sleep fragmentation agreement


class ArtifactAndInterferenceRisks(BaseModel):
    """Risk scores for data quality issues and medication/physiological confounds."""
    motion_artifact_risk_0_1: float = 0.0  # From signal quality
    topical_contamination_risk_0_1: float = 0.0  # For sweat
    dehydration_confounding_risk_0_1: float = 0.0  # For urine
    medication_interference_flags: List[str] = Field(default_factory=list)  # e.g., ["diuretic_may_affect_urine_sg"]
    aggregate_interference_score_0_1: float = 0.0


class CrossSpecimenRelationships(BaseModel):
    """Consolidated cross-specimen relationship outputs."""
    lag_model: LagModelParams
    plausibility: PlausibilityParams
    triangulation: TriangulationScores
    artifact_risks: ArtifactAndInterferenceRisks


class MotifDetection(BaseModel):
    """Detected patterns/motifs in the data."""
    motif_type: MotifEnum
    motif_strength_0_1: float
    supporting_variables: List[str]
    expected_context: str  # e.g., "post-exercise" or "post-meal"
    confidence_0_1: float


class PatternCombinationFeatures(BaseModel):
    """High-level pattern and combination features."""
    detected_motifs: List[MotifDetection]
    temporal_windows_features: Dict[str, Dict[str, float]]  # window_id -> {feature_name: value}
    regime_labels: List[Dict[str, Any]]  # [{time_window: "...", regime: RegimeEnum, confidence: float}, ...]


class DiscordanceDetection(BaseModel):
    """Specimen disagreement and inconsistency detection."""
    discordance_flags: List[str]  # e.g., ["blood_normal_isf_abnormal", "activity_high_lactate_flat"]
    discordance_explanations: List[Dict[str, str]]  # [{flag: "...", explanation_bucket: "lag|artifact|unknown"}, ...]
    specimen_agreement_scores: Dict[str, float]  # pair_id (e.g., "isf_vs_blood") -> score 0-1


class CoherenceScores(BaseModel):
    """Summary coherence metrics across all cross-specimen relationships."""
    overall_coherence_0_1: float  # Weighted average of all coherence sources
    lag_coherence_0_1: float
    plausibility_coherence_0_1: float
    triangulation_coherence_0_1: float
    artifact_interference_coherence_0_1: float
    coherence_driver: str  # Which factor most influences overall coherence


class PenaltyVector(BaseModel):
    """Accumulated penalties for inference gating in Phase 3."""
    penalty_factors: List[str]  # e.g., ["high_missingness", "artifact_risk_high", "incoherent_lags"]
    domain_blockers: List[str]  # e.g., ["metabolic_domain_missing_critical_values"]
    confidence_reduction_factor_0_1: float  # Multiply inference confidence by this


class FeaturePackV2(BaseModel):
    """
    Complete feature_pack_v2 output from preprocess v2 pipeline.
    Contains missingness-aware features, cross-specimen relationships, patterns, and coherence scores.
    Designed to be stored alongside legacy features and used by Phase 3 inference gating.
    """
    run_id: str
    created_at: datetime
    schema_version: str = "feature_pack_v2.1"
    
    # Core feature components
    missingness_feature_vector: MissingnessFeatureVector
    specimen_normalized_values: List[SpecimenNormalizedValues]
    derived_temporal_features: List[DerivedTemporalFeatures]
    cross_specimen_relationships: CrossSpecimenRelationships
    pattern_combination_features: PatternCombinationFeatures
    discordance_detection: DiscordanceDetection
    
    # Summary metrics for Phase 3
    coherence_scores: CoherenceScores
    penalty_vector: PenaltyVector
    
    # Metadata
    specimen_count: int
    domains_present: List[str]
    qualitative_effect_vector: Optional[Dict[str, float]] = None  # From RunV2.encoding_outputs if available
    processing_notes: Optional[List[str]] = None

    class Config:
        from_attributes = True
