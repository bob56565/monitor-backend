"""
Inference Pack V2: Output schema for clinical-grade panel inference.

Includes:
- Measured values (echo, provenance-tagged)
- Inferred values (panelized)
- Physiological state domains
- Eligibility and dependency rationale
- Computed confidence
- Coherence and discordance notes
- Suppressed outputs with reasons
- Model disagreement logs
- Provenance map
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field


class EvidenceGrade(str, Enum):
    """
    Evidence grade for outputs (Phase 1 Requirement B.5).
    Each grade has a maximum allowed confidence.
    """
    A = "A"  # Anchored / deterministic (max confidence: 0.90)
    B = "B"  # Multi-signal anchored inference (max confidence: 0.75)
    C = "C"  # Proxy / indirect inference (max confidence: 0.55)
    D = "D"  # Exploratory / weak anchor (max confidence: 0.35)


# Evidence grade confidence caps (enforced automatically)
EVIDENCE_GRADE_CAPS = {
    EvidenceGrade.A: 0.90,
    EvidenceGrade.B: 0.75,
    EvidenceGrade.C: 0.55,
    EvidenceGrade.D: 0.35,
}


class SupportTypeEnum(str, Enum):
    """Type of support for an inferred/measured value."""
    DIRECT = "direct"  # Measured directly from specimen
    DERIVED = "derived"  # Direct calculation from measured values
    PROXY = "proxy"  # Inferred from related measurements
    RELATIONAL = "relational"  # Inferred from multi-specimen triangulation
    POPULATION = "population"  # Inferred mostly from priors


class ProvenanceTypeEnum(str, Enum):
    """Provenance/source type for values."""
    MEASURED = "measured"
    DIRECT = "direct"  # Calculated from measured
    INFERRED = "inferred"
    POPULATION = "population"
    PROXY = "proxy"


class ConfidenceDriverEnum(str, Enum):
    """Factors that increase confidence in an output."""
    HIGH_COMPLETENESS = "high_completeness"
    HIGH_COHERENCE = "high_coherence"
    STRONG_AGREEMENT = "strong_agreement"
    HIGH_STABILITY = "high_stability"
    HIGH_SIGNAL_QUALITY = "high_signal_quality"
    DIRECT_MEASUREMENT = "direct_measurement"
    MULTIPLE_SPECIMENS = "multiple_specimens"


class ConfidencePenaltyEnum(str, Enum):
    """Factors that reduce confidence in an output."""
    LOW_COMPLETENESS = "low_completeness"
    LOW_COHERENCE = "low_coherence"
    MODEL_DISAGREEMENT = "model_disagreement"
    LOW_STABILITY = "low_stability"
    INTERFERENCE_DETECTED = "interference_detected"
    ARTIFACT_RISK = "artifact_risk"
    PROXY_SUPPORT = "proxy_support"
    MEASUREMENT_DELAY = "measurement_delay"
    HIGH_MISSINGNESS = "high_missingness"


class SuppressionReasonEnum(str, Enum):
    """Reason why an output was suppressed."""
    MISSING_REQUIRED_ANCHOR = "missing_required_anchor"
    LOW_COHERENCE = "low_coherence"
    CONFIDENCE_BELOW_THRESHOLD = "confidence_below_threshold"
    BLOCKER_CONDITION_MET = "blocker_condition_met"
    INSUFFICIENT_SIGNAL = "insufficient_signal"
    KNOWN_INTERFERENCE = "known_interference"
    INCOMPLETENESS_CRITICAL = "incompleteness_critical"
    PREGNANCY_STATE = "pregnancy_state"
    ACUTE_ILLNESS = "acute_illness"


class ModelEnum(str, Enum):
    """Inference engine that produced this estimate."""
    POPULATION_CONDITIONER = "population_conditioner"
    PANEL_REGRESSOR = "panel_regressor"
    TEMPORAL_MODEL = "temporal_model"
    MECHANISTIC_BOUNDS = "mechanistic_bounds"
    CONSENSUS_FUSER = "consensus_fuser"


class PhysiologicalStateEnum(str, Enum):
    """Physiological state domains."""
    METABOLIC_STATE = "metabolic_state"
    RENAL_STATE = "renal_state"
    ELECTROLYTE_STATE = "electrolyte_state"
    HYDRATION_STATE = "hydration_state"
    LIVER_STATE = "liver_state"
    LIPID_STATE = "lipid_state"
    ENDOCRINE_STATE = "endocrine_state"
    VITAMIN_STATE = "vitamin_state"
    INFLAMMATION_STATE = "inflammation_state"
    AUTOIMMUNE_STATE = "autoimmune_state"
    HEMATOLOGY_STATE = "hematology_state"
    STRESS_RECOVERY_STATE = "stress_recovery_state"
    INFECTION_LIKELIHOOD = "infection_likelihood"


class InferredValue(BaseModel):
    """
    Single inferred or echoed value in the panel.
    Enhanced with Phase 1 standardized output schema (Requirement B.7).
    """
    key: str  # e.g., "glucose_est", "wbc_est"
    
    # Core value (backward compatible)
    value: Optional[float] = None
    range_lower: Optional[float] = None
    range_upper: Optional[float] = None
    range_unit: Optional[str] = None
    
    # Phase 1 additions: Standardized output fields
    estimated_center: Optional[float] = None  # Explicit center estimate (may differ from value)
    range_low: Optional[float] = None  # Alias for range_lower (standardized name)
    range_high: Optional[float] = None  # Alias for range_upper (standardized name)
    confidence_percent: Optional[int] = None  # Confidence as percent (0-100)
    confidence_interval_type: Optional[str] = "credible_interval"  # Type of CI
    
    # Evidence grading (Phase 1 Requirement B.5)
    evidence_grade: Optional[EvidenceGrade] = None
    evidence_inputs_used: List[str] = Field(default_factory=list)  # Which inputs/specimens
    
    # Physiologic drivers and uncertainty
    physiologic_drivers: List[str] = Field(default_factory=list)  # What drives the estimate
    drivers_of_uncertainty: List[str] = Field(default_factory=list)  # What increases uncertainty
    what_would_tighten_this: List[str] = Field(default_factory=list)  # Recommendations to improve
    
    # Backward compatible fields
    confidence_0_1: float = Field(ge=0.0, le=1.0)
    support_type: SupportTypeEnum
    provenance: ProvenanceTypeEnum
    source_specimen_types: List[str] = Field(default_factory=list)  # e.g., ["ISF", "BLOOD_CAPILLARY"]
    confidence_drivers: List[ConfidenceDriverEnum] = Field(default_factory=list)
    confidence_penalties: List[ConfidencePenaltyEnum] = Field(default_factory=list)
    notes: Optional[str] = None  # e.g., interference warning, stability concern
    engine_sources: List[ModelEnum] = Field(default_factory=list)  # Which engines produced this
    
    def model_post_init(self, __context):
        """Pydantic V2 post-init hook to enforce evidence grade caps and sync aliases."""
        # Enforce evidence grade confidence caps
        if self.evidence_grade and self.evidence_grade in EVIDENCE_GRADE_CAPS:
            max_allowed = EVIDENCE_GRADE_CAPS[self.evidence_grade]
            if self.confidence_0_1 > max_allowed:
                self.confidence_0_1 = max_allowed
        
        # Sync aliases
        if self.value is not None and self.estimated_center is None:
            self.estimated_center = self.value
        if self.range_lower is not None and self.range_low is None:
            self.range_low = self.range_lower
        if self.range_upper is not None and self.range_high is None:
            self.range_high = self.range_upper
        if self.confidence_percent is None:
            self.confidence_percent = int(self.confidence_0_1 * 100)


class SuppressedOutput(BaseModel):
    """Output that was suppressed due to missing dependencies or low confidence."""
    key: str
    reason: SuppressionReasonEnum
    reason_detail: Optional[str] = None
    missing_anchors: List[str] = Field(default_factory=list)
    min_coherence_required: Optional[float] = None
    actual_coherence: Optional[float] = None


class DependencyRationale(BaseModel):
    """Explanation of why an output was produced or suppressed."""
    output_key: str
    status: str  # "produced" | "suppressed" | "widened"
    requires_any: List[str] = Field(default_factory=list)
    requires_all: List[str] = Field(default_factory=list)
    blocked_by_conditions: List[str] = Field(default_factory=list)
    missing_dependencies: List[str] = Field(default_factory=list)
    met_boosters: List[str] = Field(default_factory=list)
    applied_penalties: List[str] = Field(default_factory=list)
    coherence_score: Optional[float] = None
    decision_log: str


class EngineOutput(BaseModel):
    """Summary output from a single inference engine."""
    engine: ModelEnum
    panel: str  # e.g., "CMP", "CBC", "ENDOCRINE"
    estimates: Dict[str, float] = Field(default_factory=dict)
    uncertainties: Dict[str, float] = Field(default_factory=dict)  # Standard deviations or ranges
    support_scores: Dict[str, float] = Field(default_factory=dict)  # Confidence per estimate


class ConsensusMetrics(BaseModel):
    """Multi-engine consensus and disagreement metrics."""
    disagreement_score_0_1: float = Field(ge=0.0, le=1.0)
    fusion_weights: Dict[str, float]  # Engine weights in consensus
    widening_applied: bool  # Whether ranges were widened due to disagreement
    widening_factor: Optional[float] = None  # e.g., 1.25 means 25% wider


class PhysiologicalStateDomain(BaseModel):
    """Assessment of a physiological state domain."""
    domain: PhysiologicalStateEnum
    summary: str  # Short assessment (e.g., "Metabolic stress detected")
    evidence: List[str] = Field(default_factory=list)  # Key values supporting this
    confidence_0_1: float = Field(ge=0.0, le=1.0)
    recommendations: List[str] = Field(default_factory=list)


class ProvenanceMapEntry(BaseModel):
    """Maps an output key to its source specimens and variables."""
    output_key: str
    specimen_types: List[str]
    specimen_ids: List[str]
    measured_variables: List[str]  # Raw variable names used
    feature_pack_drivers: List[str]  # feature_pack_v2 fields that influenced this


class InferencePackV2(BaseModel):
    """
    Complete inference output for a RunV2.
    Enhanced with Phase 1 A2 Processing and B Output requirements.
    """
    run_id: str
    schema_version: str = "v2"
    created_at: datetime
    
    # Phase 1 Addition: Coverage truth for all streams (Requirement A.1)
    coverage_truth: Optional[Any] = None  # CoverageTruthPack from coverage_truth module
    
    # Phase 1 Addition: Conflict detection (Requirement A.4)
    conflict_report: Optional[Any] = None  # ConflictDetectionReport from conflict_detection module
    
    # Core outputs
    measured_values: List[InferredValue] = Field(default_factory=list)  # Direct echoes
    inferred_values: List[InferredValue] = Field(default_factory=list)  # Inferred panels
    
    # Physiological state
    physiological_states: List[PhysiologicalStateDomain] = Field(default_factory=list)
    
    # Gating and eligibility
    produced_outputs_count: int
    suppressed_outputs_count: int
    suppressed_outputs: List[SuppressedOutput] = Field(default_factory=list)
    eligibility_rationale: List[DependencyRationale] = Field(default_factory=list)
    
    # Confidence and coherence
    overall_confidence_0_1: float = Field(ge=0.0, le=1.0)
    overall_coherence_0_1: Optional[float] = None
    
    # Multi-engine details
    engine_outputs: List[EngineOutput] = Field(default_factory=list)
    consensus_metrics: Optional[ConsensusMetrics] = None
    
    # Discordance and interference
    coherence_notes: List[str] = Field(default_factory=list)
    discordance_notes: List[str] = Field(default_factory=list)
    interference_warnings: List[str] = Field(default_factory=list)
    
    # Model comparison
    model_disagreement_log: List[Dict[str, Any]] = Field(default_factory=list)
    constraint_violations: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Traceability
    provenance_map: List[ProvenanceMapEntry] = Field(default_factory=list)
    
    # Metadata
    specimen_count: int
    domains_assessed: List[str] = Field(default_factory=list)
    processing_notes: Optional[str] = None


class InferencePackV2Response(BaseModel):
    """API response for inference_v2."""
    inference_id: int
    run_id: str
    schema_version: str
    overall_confidence_0_1: float
    produced_outputs_count: int
    suppressed_outputs_count: int
    physiological_states_count: int
    created_at: datetime

    class Config:
        from_attributes = True
