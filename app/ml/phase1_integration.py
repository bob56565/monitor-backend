"""
Phase 1 Integration Module.

Coordinates all Phase 1 A2 Processing and B Output enhancements:
- Coverage truth computation (Requirement A.1)
- Unit normalization (Requirement A.2)
- Derived feature computation (Requirement A.3)
- Conflict detection (Requirement A.4)
- Evidence grading assignment (Requirement B.5)
- Range-first output formatting (Requirement B.6)
"""

from typing import Dict, List, Optional, Any
import logging

from app.models.run_v2 import RunV2
from app.models.feature_pack_v2 import FeaturePackV2
from app.models.inference_pack_v2 import (
    InferredValue, EvidenceGrade, EVIDENCE_GRADE_CAPS,
    SupportTypeEnum, ProvenanceTypeEnum
)

# Import Phase 1 modules
from app.features.coverage_truth import (
    compute_coverage_truth_pack, CoverageTruthPack
)
from app.features.unit_normalization import (
    normalize_specimen_values, NormalizedValue
)
from app.features.derived_features import (
    compute_derived_features, DerivedFeature, DerivedFeaturePack
)
from app.features.conflict_detection import (
    detect_conflicts, ConflictDetectionReport
)

logger = logging.getLogger(__name__)


class Phase1Integrator:
    """
    Coordinates Phase 1 A2 Processing and B Output enhancements.
    All operations are additive and backward-compatible.
    """
    
    def __init__(self):
        """Initialize Phase 1 integrator."""
        pass
    
    def compute_coverage_truth(
        self,
        run_v2: RunV2,
        lookback_days: int = 90
    ) -> CoverageTruthPack:
        """
        Compute coverage truth for all data streams (Requirement A.1).
        
        Args:
            run_v2: Multi-specimen run
            lookback_days: Coverage window (default 90 days)
        
        Returns:
            CoverageTruthPack with per-stream coverage metrics
        """
        logger.info(f"Computing coverage truth for run_id {run_v2.run_id}")
        return compute_coverage_truth_pack(run_v2, lookback_days=lookback_days)
    
    def normalize_specimen_units(
        self,
        run_v2: RunV2,
        patient_age: Optional[int] = None,
        patient_sex: Optional[str] = None,
        is_pregnant: bool = False,
        bmi: Optional[float] = None
    ) -> Dict[str, Dict[str, NormalizedValue]]:
        """
        Normalize all specimen values to standard units (Requirement A.2).
        
        Args:
            run_v2: Multi-specimen run
            patient_age: Age in years (for stratified references)
            patient_sex: "M" or "F" (for stratified references)
            is_pregnant: Pregnancy status
            bmi: Body mass index
        
        Returns:
            Dict mapping specimen_id -> variable_name -> NormalizedValue
        """
        logger.info(f"Normalizing units for run_id {run_v2.run_id}")
        
        normalized = {}
        for specimen in run_v2.specimens:
            specimen_id = specimen.specimen_id
            normalized[specimen_id] = normalize_specimen_values(
                specimen=specimen,
                patient_age=patient_age,
                patient_sex=patient_sex,
                is_pregnant=is_pregnant,
                bmi=bmi
            )
        
        return normalized
    
    def compute_derived_features(
        self,
        run_v2: RunV2,
        normalized_values: Dict[str, Dict[str, NormalizedValue]],
        patient_age: Optional[int] = None,
        patient_sex: Optional[str] = None,
        patient_race: Optional[str] = None,
        is_pregnant: bool = False
    ) -> DerivedFeaturePack:
        """
        Compute deterministic derived features (Requirement A.3).
        
        Args:
            run_v2: Multi-specimen run
            normalized_values: Normalized values from normalize_specimen_units()
            patient_age: Age in years
            patient_sex: "M" or "F"
            patient_race: Race (for eGFR calculation)
            is_pregnant: Pregnancy status
        
        Returns:
            DerivedFeaturePack with computed derived features
        """
        logger.info(f"Computing derived features for run_id {run_v2.run_id}")
        
        # Flatten normalized values to simple dict
        flat_values = {}
        for specimen_values in normalized_values.values():
            for var_name, norm_val in specimen_values.items():
                # Use standardized value
                if norm_val.std_value is not None:
                    flat_values[var_name] = norm_val.std_value
        
        # Add patient info
        patient_info = {}
        if patient_age is not None:
            patient_info["age"] = patient_age
        if patient_sex is not None:
            patient_info["sex"] = patient_sex
        if patient_race is not None:
            patient_info["race"] = patient_race
        if is_pregnant:
            patient_info["is_pregnant"] = is_pregnant
        
        flat_values["run_id"] = run_v2.run_id
        
        return compute_derived_features(flat_values, patient_info)
    
    def detect_physiologic_conflicts(
        self,
        run_v2: RunV2,
        normalized_values: Dict[str, Dict[str, NormalizedValue]],
        derived_features: DerivedFeaturePack
    ) -> ConflictDetectionReport:
        """
        Detect physiologic conflicts and contradictions (Requirement A.4).
        
        Args:
            run_v2: Multi-specimen run
            normalized_values: Normalized values
            derived_features: Derived features
        
        Returns:
            ConflictDetectionReport with detected conflicts
        """
        logger.info(f"Detecting conflicts for run_id {run_v2.run_id}")
        
        # Flatten normalized values for conflict detection
        all_values = {}
        for specimen_values in normalized_values.values():
            all_values.update(specimen_values)
        
        # Flatten derived features to list
        all_derived = []
        if derived_features.renal_features:
            all_derived.extend(derived_features.renal_features)
        if derived_features.electrolyte_features:
            all_derived.extend(derived_features.electrolyte_features)
        if derived_features.lipid_features:
            all_derived.extend(derived_features.lipid_features)
        if derived_features.blood_pressure_features:
            all_derived.extend(derived_features.blood_pressure_features)
        
        return detect_conflicts(
            normalized_values=all_values,
            derived_features=all_derived
        )
    
    def assign_evidence_grade(
        self,
        inferred_value: InferredValue,
        coverage_truth: CoverageTruthPack,
        conflict_report: ConflictDetectionReport
    ) -> EvidenceGrade:
        """
        Assign evidence grade to an output (Requirement B.5).
        
        Grading logic:
        - A (max 0.90): Direct measurement or deterministic calculation
        - B (max 0.75): Multi-signal anchored inference
        - C (max 0.55): Proxy or indirect inference
        - D (max 0.35): Exploratory or weak anchor
        
        Args:
            inferred_value: Output to grade
            coverage_truth: Coverage metrics
            conflict_report: Conflict detection results
        
        Returns:
            EvidenceGrade (A/B/C/D)
        """
        
        # Grade A: Direct measurements or derived features
        if inferred_value.support_type == SupportTypeEnum.DIRECT:
            return EvidenceGrade.A
        
        if inferred_value.support_type == SupportTypeEnum.DERIVED:
            return EvidenceGrade.A
        
        # Grade B: Multi-specimen relational inference with good coverage
        if inferred_value.support_type == SupportTypeEnum.RELATIONAL:
            # Check if we have multiple high-quality specimens
            if len(inferred_value.source_specimen_types) >= 2:
                # Check coverage quality
                avg_quality = sum(
                    getattr(coverage_truth, stream_name, None).quality_score
                    for stream_name in inferred_value.source_specimen_types
                    if hasattr(coverage_truth, stream_name)
                ) / max(len(inferred_value.source_specimen_types), 1)
                
                if avg_quality >= 0.7:
                    return EvidenceGrade.B
        
        # Grade C: Single proxy or indirect inference
        if inferred_value.support_type == SupportTypeEnum.PROXY:
            return EvidenceGrade.C
        
        # Grade D: Population-based or weak anchor
        if inferred_value.support_type == SupportTypeEnum.POPULATION:
            return EvidenceGrade.D
        
        # Default to C for unknown cases
        return EvidenceGrade.C
    
    def apply_evidence_grade_cap(
        self,
        inferred_value: InferredValue
    ) -> InferredValue:
        """
        Enforce evidence grade confidence caps (Requirement B.5).
        
        Args:
            inferred_value: Output with evidence grade
        
        Returns:
            Updated InferredValue with capped confidence
        """
        if inferred_value.evidence_grade and inferred_value.evidence_grade in EVIDENCE_GRADE_CAPS:
            max_allowed = EVIDENCE_GRADE_CAPS[inferred_value.evidence_grade]
            if inferred_value.confidence_0_1 > max_allowed:
                logger.info(
                    f"Capping confidence for {inferred_value.key} from "
                    f"{inferred_value.confidence_0_1:.3f} to {max_allowed:.3f} "
                    f"(grade {inferred_value.evidence_grade.value})"
                )
                inferred_value.confidence_0_1 = max_allowed
                inferred_value.confidence_percent = int(max_allowed * 100)
        
        return inferred_value
    
    def format_range_first_output(
        self,
        inferred_value: InferredValue
    ) -> InferredValue:
        """
        Ensure range-first output formatting (Requirement B.6).
        
        Args:
            inferred_value: Output to format
        
        Returns:
            Updated InferredValue with standardized range fields
        """
        # Sync estimated_center with value
        if inferred_value.value is not None:
            inferred_value.estimated_center = inferred_value.value
        
        # Sync range aliases
        if inferred_value.range_lower is not None:
            inferred_value.range_low = inferred_value.range_lower
        if inferred_value.range_upper is not None:
            inferred_value.range_high = inferred_value.range_upper
        
        # Ensure confidence_percent is set
        if inferred_value.confidence_percent is None:
            inferred_value.confidence_percent = int(inferred_value.confidence_0_1 * 100)
        
        return inferred_value
    
    def populate_standardized_fields(
        self,
        inferred_value: InferredValue,
        coverage_truth: CoverageTruthPack,
        conflict_report: ConflictDetectionReport,
        derived_features: DerivedFeaturePack
    ) -> InferredValue:
        """
        Populate standardized output fields (Requirement B.7).
        
        Populates:
        - evidence_inputs_used
        - physiologic_drivers
        - drivers_of_uncertainty
        - what_would_tighten_this
        
        Args:
            inferred_value: Output to enhance
            coverage_truth: Coverage metrics
            conflict_report: Conflict detection results
            derived_features: Derived features
        
        Returns:
            Updated InferredValue with populated fields
        """
        
        # Evidence inputs used
        if inferred_value.source_specimen_types:
            inferred_value.evidence_inputs_used = [
                f"{specimen_type} specimen"
                for specimen_type in inferred_value.source_specimen_types
            ]
        
        # Physiologic drivers (from derived features if applicable)
        all_derived = []
        if derived_features.renal_features:
            all_derived.extend(derived_features.renal_features)
        if derived_features.electrolyte_features:
            all_derived.extend(derived_features.electrolyte_features)
        if derived_features.lipid_features:
            all_derived.extend(derived_features.lipid_features)
        if derived_features.blood_pressure_features:
            all_derived.extend(derived_features.blood_pressure_features)
        
        for derived in all_derived:
            if derived.feature_name in inferred_value.key:
                inferred_value.physiologic_drivers.append(
                    f"Calculated from {', '.join(derived.inputs_used.keys())}"
                )
        
        # Drivers of uncertainty
        if inferred_value.confidence_penalties:
            for penalty in inferred_value.confidence_penalties:
                inferred_value.drivers_of_uncertainty.append(penalty.value)
        
        # Add coverage-based uncertainty drivers
        for specimen_type in inferred_value.source_specimen_types:
            if hasattr(coverage_truth, specimen_type):
                stream_cov = getattr(coverage_truth, specimen_type)
                if stream_cov.missing_rate > 0.3:
                    inferred_value.drivers_of_uncertainty.append(
                        f"High missing rate ({stream_cov.missing_rate:.1%}) in {specimen_type}"
                    )
        
        # What would tighten this
        recommendations = []
        
        # Coverage recommendations
        for specimen_type in inferred_value.source_specimen_types:
            if hasattr(coverage_truth, specimen_type):
                stream_cov = getattr(coverage_truth, specimen_type)
                if stream_cov.missing_rate > 0.3:
                    recommendations.append(f"Increase {specimen_type} data collection")
                if stream_cov.data_points < 10:
                    recommendations.append(f"Collect more {specimen_type} measurements")
        
        # Conflict recommendations
        if conflict_report.conflicts:
            recommendations.append("Resolve physiologic conflicts before interpreting")
        
        # Grade-specific recommendations
        if inferred_value.evidence_grade == EvidenceGrade.D:
            recommendations.append("Obtain direct measurement to upgrade evidence grade")
        elif inferred_value.evidence_grade == EvidenceGrade.C:
            recommendations.append("Obtain multi-specimen confirmation to improve confidence")
        
        inferred_value.what_would_tighten_this = recommendations
        
        return inferred_value
    
    def integrate_phase1(
        self,
        run_v2: RunV2,
        feature_pack_v2: FeaturePackV2,
        inferred_values: List[InferredValue],
        patient_age: Optional[int] = None,
        patient_sex: Optional[str] = None,
        patient_race: Optional[str] = None,
        is_pregnant: bool = False,
        bmi: Optional[float] = None,
        lookback_days: int = 90
    ) -> Dict[str, Any]:
        """
        Complete Phase 1 integration pipeline.
        
        Executes all Phase 1 requirements in sequence:
        1. Compute coverage truth (A.1)
        2. Normalize units (A.2)
        3. Compute derived features (A.3)
        4. Detect conflicts (A.4)
        5. Assign evidence grades (B.5)
        6. Apply confidence caps (B.5)
        7. Format range-first outputs (B.6)
        8. Populate standardized fields (B.7)
        
        Args:
            run_v2: Multi-specimen run
            feature_pack_v2: Feature pack
            inferred_values: List of outputs to enhance
            patient_age: Age in years
            patient_sex: "M" or "F"
            patient_race: Race
            is_pregnant: Pregnancy status
            bmi: Body mass index
            lookback_days: Coverage window
        
        Returns:
            Dict with:
                - coverage_truth: CoverageTruthPack
                - conflict_report: ConflictDetectionReport
                - enhanced_values: List[InferredValue] with Phase 1 enhancements
                - derived_features: DerivedFeaturePack
        """
        logger.info(f"Starting Phase 1 integration for run_id {run_v2.run_id}")
        
        # A.1: Compute coverage truth
        coverage_truth = self.compute_coverage_truth(run_v2, lookback_days=lookback_days)
        
        # A.2: Normalize units
        normalized_values = self.normalize_specimen_units(
            run_v2=run_v2,
            patient_age=patient_age,
            patient_sex=patient_sex,
            is_pregnant=is_pregnant,
            bmi=bmi
        )
        
        # A.3: Compute derived features
        derived_features = self.compute_derived_features(
            run_v2=run_v2,
            normalized_values=normalized_values,
            patient_age=patient_age,
            patient_sex=patient_sex,
            patient_race=patient_race,
            is_pregnant=is_pregnant
        )
        
        # A.4: Detect conflicts
        conflict_report = self.detect_physiologic_conflicts(
            run_v2=run_v2,
            normalized_values=normalized_values,
            derived_features=derived_features
        )
        
        # B.5-B.7: Enhance each output
        enhanced_values = []
        for inferred_value in inferred_values:
            # B.5: Assign evidence grade
            inferred_value.evidence_grade = self.assign_evidence_grade(
                inferred_value=inferred_value,
                coverage_truth=coverage_truth,
                conflict_report=conflict_report
            )
            
            # B.5: Apply confidence cap
            inferred_value = self.apply_evidence_grade_cap(inferred_value)
            
            # B.6: Format range-first
            inferred_value = self.format_range_first_output(inferred_value)
            
            # B.7: Populate standardized fields
            inferred_value = self.populate_standardized_fields(
                inferred_value=inferred_value,
                coverage_truth=coverage_truth,
                conflict_report=conflict_report,
                derived_features=derived_features
            )
            
            enhanced_values.append(inferred_value)
        
        logger.info(
            f"Phase 1 integration complete: "
            f"{len(enhanced_values)} outputs enhanced, "
            f"{len(conflict_report.conflicts)} conflicts detected, "
            f"{derived_features.features_computed} derived features computed"
        )
        
        return {
            "coverage_truth": coverage_truth,
            "conflict_report": conflict_report,
            "enhanced_values": enhanced_values,
            "derived_features": derived_features,
        }
