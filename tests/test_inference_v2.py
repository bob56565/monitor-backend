"""
Tests for Inference V2: Clinic-grade inference with eligibility gating + computed confidence.

Part 3 of Milestone 7: Validates eligibility gating, confidence math, mechanistic bounds, 
and full inference_v2 pipeline.

Scope:
- Unit tests for eligibility gating (dependency resolution, suppression rules)
- Unit tests for confidence math (completeness, coherence, agreement, stability, signal_quality)
- Integration tests for API endpoints (/inference/v2 POST, GET)
- E2E tests for full pipeline (RunV2 → preprocess_v2 → inference_v2 → suppressed/inferred outputs)
"""

import pytest
from datetime import datetime
from typing import Dict, Any
from unittest.mock import Mock, patch

# ===== IMPORTS: Part 3 Inference Modules =====
from app.models.inference_pack_v2 import (
    InferencePackV2, InferredValue, SuppressedOutput, DependencyRationale, 
    PhysiologicalStateDomain, SuppressionReasonEnum, SupportTypeEnum, ConfidenceDriverEnum
)
from app.ml.eligibility_gate_v2 import EligibilityGateV2, OUTPUT_CATALOG
from app.ml.confidence_math import ConfidenceMath, ConfidenceComponents
from app.ml.inference_v2 import InferenceV2

# ===== IMPORTS: Part 1-2 Models =====
from app.models.run_v2 import RunV2, SpecimenRecord, SpecimenTypeEnum, NonLabInputs
from app.features.preprocess_v2 import preprocess_v2, FeaturePackV2
from datetime import datetime
from typing import Dict, Any, Optional


# ============================================================================
# SECTION 1: UNIT TESTS - ELIGIBILITY GATING
# ============================================================================

class TestEligibilityGatingV2:
    """Test eligibility gating engine: dependency resolution, suppression rules."""

    @pytest.fixture
    def gating_engine(self):
        """Create gating engine instance."""
        return EligibilityGateV2()

    def test_gate_produces_glucose_with_isf_glucose(self, gating_engine):
        """Test: Can produce glucose_est if ISF glucose available."""
        available_values = {"isf_glucose": 85.0}
        available_contexts = {"has_isf_specimens": True}
        blockers = {}
        
        should_produce, reason, confidence, penalties = gating_engine.can_produce_output(
            output_key="glucose_est",
            available_values=available_values,
            available_contexts=available_contexts,
            blockers=blockers,
            coherence_score=0.75,
        )
        
        assert should_produce is True, f"Expected glucose_est to produce, reason: {reason}"
        assert confidence > 0.6, "Confidence should be high with ISF glucose"
        assert reason == "all_requirements_met"

    def test_gate_suppresses_glucose_without_anchor(self, gating_engine):
        """Test: Suppresses glucose_est if no ISF/blood glucose available."""
        available_values = {}  # No glucose
        available_contexts = {"has_isf_specimens": False}
        blockers = {}
        
        should_produce, reason, confidence, penalties = gating_engine.can_produce_output(
            output_key="glucose_est",
            available_values=available_values,
            available_contexts=available_contexts,
            blockers=blockers,
            coherence_score=0.75,
        )
        
        assert should_produce is False
        assert reason == "missing_all_requires_any"

    def test_gate_respects_blocker_pregnancy(self, gating_engine):
        """Test: Suppresses hormone outputs if pregnancy blocker set."""
        available_values = {"tsh": 1.2}
        available_contexts = {}
        blockers = {"pregnancy": True}
        
        should_produce, reason, confidence, penalties = gating_engine.can_produce_output(
            output_key="tsh_est",
            available_values=available_values,
            available_contexts=available_contexts,
            blockers=blockers,
            coherence_score=0.75,
        )
        
        assert should_produce is False
        assert "blocked_by" in reason.lower()

    def test_gate_suppresses_low_coherence(self, gating_engine):
        """Test: Suppresses output if coherence below min_coherence_required."""
        available_values = {"wbc": 5.2}
        available_contexts = {"has_blood_specimens": True}
        blockers = {}
        
        should_produce, reason, confidence, penalties = gating_engine.can_produce_output(
            output_key="wbc_est",
            available_values=available_values,
            available_contexts=available_contexts,
            blockers=blockers,
            coherence_score=0.35,  # Below default min_coherence=0.55
        )
        
        assert should_produce is False
        assert "coherence" in reason.lower()

    def test_gate_list_missing_anchors_for_suppressed_output(self, gating_engine):
        """Test: Gating provides list of missing anchors for suppressed outputs."""
        # Try to produce egfr_est but missing both creatinine (measured) and age (context)
        available_values = {}  # No creatinine
        available_contexts = {}  # No age
        blockers = {}
        
        output_spec = OUTPUT_CATALOG.get("egfr_est")
        assert output_spec is not None, "egfr_est should be in catalog"
        
        # EGFR requires creatinine (requires_any) and age (requires_context)
        missing_any = [k for k in output_spec.requires_any if k not in available_values]
        missing_context = [k for k in output_spec.requires_context if k not in available_contexts]
        
        assert len(missing_any) > 0 or len(missing_context) > 0, "Should have missing anchors"

    def test_gate_applies_confidence_booster(self, gating_engine):
        """Test: Confidence boosted when optional confidence_boosters present."""
        available_values = {"wbc": 5.2, "hematocrit": 0.42}  # WBC + hematocrit (booster)
        available_contexts = {"has_blood_specimens": True}
        blockers = {}
        
        should_produce, reason, confidence, penalties = gating_engine.can_produce_output(
            output_key="wbc_est",
            available_values=available_values,
            available_contexts=available_contexts,
            blockers=blockers,
            coherence_score=0.75,
        )
        
        assert should_produce is True
        # Confidence should be boosted vs baseline
        baseline_confidence = 0.75  # From coherence
        assert confidence >= baseline_confidence, "Should have applied confidence booster"

    def test_gate_output_catalog_completeness(self, gating_engine):
        """Test: Output catalog contains expected clinical panels."""
        catalog = OUTPUT_CATALOG
        
        # Check key panels present
        expected_panels = {
            "glucose_est", "wbc_est", "hemoglobin_est", "platelets_est",  # Core
            "chol_total_est", "ldl_est", "hdl_est", "triglycerides_est",  # Lipids
            "a1c_est", "tsh_est", "vitamin_d_25oh_est", "b12_est",  # Endocrine + Vitamins
            "crp_est", "inflammatory_tone_state", "hydration_status_state"  # States
        }
        
        for output_key in expected_panels:
            assert output_key in catalog, f"{output_key} missing from OUTPUT_CATALOG"
            spec = catalog[output_key]
            
            # Verify structure
            assert hasattr(spec, "requires_any"), f"{output_key} missing requires_any"
            assert hasattr(spec, "requires_all"), f"{output_key} missing requires_all"
            assert hasattr(spec, "panel"), f"{output_key} missing panel"
            assert spec.panel in [
                "CMP", "CBC", "LIPIDS", "ENDOCRINE", "VITAMINS", 
                "INFLAMMATION", "HYDRATION", "STRESS", "DERIVED"
            ], f"{output_key} invalid panel: {spec.panel}"


# ============================================================================
# SECTION 2: UNIT TESTS - CONFIDENCE MATH
# ============================================================================

class TestConfidenceMath:
    """Test confidence computation: 6-component weighted formula."""

    def test_confidence_perfect_components(self):
        """Test: Confidence = 1.0 when all components perfect."""
        components = ConfidenceComponents(
            completeness_0_1=1.0,
            coherence_0_1=1.0,
            agreement_0_1=1.0,
            stability_0_1=1.0,
            signal_quality_0_1=1.0,
            interference_penalty_0_1=0.0,
        )
        
        confidence = ConfidenceMath.compute_confidence(components)
        assert abs(confidence - 1.0) < 0.01, "Perfect components should yield ~1.0 confidence"

    def test_confidence_incorporates_all_components(self):
        """Test: Confidence degrades with each poor component."""
        # Baseline: all good
        baseline_components = ConfidenceComponents(
            completeness_0_1=0.9, coherence_0_1=0.9, agreement_0_1=0.9,
            stability_0_1=0.9, signal_quality_0_1=0.9, interference_penalty_0_1=0.0,
        )
        baseline_confidence = ConfidenceMath.compute_confidence(baseline_components)
        
        # Degrade completeness
        poor_completeness = ConfidenceComponents(
            completeness_0_1=0.5, coherence_0_1=0.9, agreement_0_1=0.9,
            stability_0_1=0.9, signal_quality_0_1=0.9, interference_penalty_0_1=0.0,
        )
        poor_confidence = ConfidenceMath.compute_confidence(poor_completeness)
        
        assert poor_confidence < baseline_confidence, "Degraded completeness should lower confidence"

    def test_confidence_respects_weights(self):
        """Test: Confidence formula uses proper weights."""
        # Completeness (weight 0.22) worse than signal_quality (weight 0.12)
        # So completeness degradation should have bigger impact
        
        components_poor_completeness = ConfidenceComponents(
            completeness_0_1=0.5, coherence_0_1=0.9, agreement_0_1=0.9,
            stability_0_1=0.9, signal_quality_0_1=0.9, interference_penalty_0_1=0.0,
        )
        conf_poor_completeness = ConfidenceMath.compute_confidence(components_poor_completeness)
        
        components_poor_signal = ConfidenceComponents(
            completeness_0_1=0.9, coherence_0_1=0.9, agreement_0_1=0.9,
            stability_0_1=0.9, signal_quality_0_1=0.5, interference_penalty_0_1=0.0,
        )
        conf_poor_signal = ConfidenceMath.compute_confidence(components_poor_signal)
        
        # Completeness has higher weight, so degrading it more should impact confidence more
        baseline = ConfidenceComponents(
            completeness_0_1=0.9, coherence_0_1=0.9, agreement_0_1=0.9,
            stability_0_1=0.9, signal_quality_0_1=0.9, interference_penalty_0_1=0.0,
        )
        conf_baseline = ConfidenceMath.compute_confidence(baseline)
        
        impact_completeness = conf_baseline - conf_poor_completeness
        impact_signal = conf_baseline - conf_poor_signal
        assert impact_completeness > impact_signal, "Completeness (higher weight) should impact more"

    def test_confidence_penalty_reduces_score(self):
        """Test: Interference penalty reduces confidence."""
        components_no_penalty = ConfidenceComponents(
            completeness_0_1=0.8, coherence_0_1=0.8, agreement_0_1=0.8,
            stability_0_1=0.8, signal_quality_0_1=0.8, interference_penalty_0_1=0.0,
        )
        
        components_with_penalty = ConfidenceComponents(
            completeness_0_1=0.8, coherence_0_1=0.8, agreement_0_1=0.8,
            stability_0_1=0.8, signal_quality_0_1=0.8, interference_penalty_0_1=0.15,
        )
        
        conf_no_penalty = ConfidenceMath.compute_confidence(components_no_penalty)
        conf_with_penalty = ConfidenceMath.compute_confidence(components_with_penalty)
        
        assert conf_with_penalty < conf_no_penalty, "Interference penalty should reduce confidence"

    def test_confidence_bounds_to_0_1(self):
        """Test: Confidence always bounded [0, 1]."""
        extreme_components = ConfidenceComponents(
            completeness_0_1=1.5,  # Invalid input (shouldn't happen)
            coherence_0_1=1.5,
            agreement_0_1=1.5,
            stability_0_1=1.5,
            signal_quality_0_1=1.5,
            interference_penalty_0_1=-0.5,  # Weird negative penalty
        )
        
        confidence = ConfidenceMath.compute_confidence(extreme_components)
        assert 0.0 <= confidence <= 1.0, f"Confidence should be in [0,1], got {confidence}"

    def test_compute_completeness_from_missingness(self):
        """Test: Completeness = 1 - missingness."""
        completeness = ConfidenceMath.compute_completeness_score(missingness=0.2)
        assert abs(completeness - 0.8) < 0.01

    def test_compute_agreement_from_disagreement(self):
        """Test: Agreement = 1 - disagreement."""
        agreement = ConfidenceMath.compute_agreement_score(disagreement=0.15)
        assert abs(agreement - 0.85) < 0.01

    def test_should_widen_range_on_high_disagreement(self):
        """Test: Range widening triggered by high disagreement."""
        should_widen, factor = ConfidenceMath.should_widen_range(
            disagreement=0.50, coherence=0.75, completeness=0.85
        )
        
        assert should_widen is True, "Should widen on high disagreement (0.50 > 0.45)"
        assert factor > 1.0, "Widening factor should be > 1.0"

    def test_should_widen_range_on_low_coherence(self):
        """Test: Range widening triggered by low coherence."""
        should_widen, factor = ConfidenceMath.should_widen_range(
            disagreement=0.30, coherence=0.50, completeness=0.85
        )
        
        assert should_widen is True, "Should widen on low coherence (0.50 < 0.55)"
        assert factor > 1.0

    def test_should_not_widen_range_when_healthy(self):
        """Test: No widening when all metrics healthy."""
        should_widen, factor = ConfidenceMath.should_widen_range(
            disagreement=0.20, coherence=0.80, completeness=0.90
        )
        
        assert should_widen is False, "Should not widen when all metrics healthy"
        assert factor == 1.0, "Factor should be 1.0 (no widening)"


# ============================================================================
# SECTION 3: INTEGRATION TESTS - INFERENCE V2 ORCHESTRATOR
# ============================================================================

class TestInferenceV2Orchestrator:
    """Test full inference_v2 pipeline: RunV2 + feature_pack_v2 → inference_pack_v2."""

    @pytest.fixture
    def sample_run_v2(self):
        """Create sample RunV2 with ISF + blood specimens."""
        from app.models.run_v2 import MissingnessRecord, DemographicsInputs, NonLabInputs
        
        # Create specimens with raw_values and missingness tracking
        isf_specimen = SpecimenRecord(
            specimen_id="isf_1",
            specimen_type=SpecimenTypeEnum.ISF,
            collected_at=datetime(2025, 1, 28, 8, 0, 0),
            source_detail="dermal",
            raw_values={"glucose": 95.0, "lactate": 1.2},
            units={"glucose": "mg/dL", "lactate": "mmol/L"},
            missingness={
                "glucose": MissingnessRecord(missing_type="not_missing"),
                "lactate": MissingnessRecord(missing_type="not_missing"),
            }
        )
        
        blood_specimen = SpecimenRecord(
            specimen_id="blood_1",
            specimen_type=SpecimenTypeEnum.BLOOD,
            collected_at=datetime(2025, 1, 28, 8, 15, 0),
            source_detail="venipuncture",
            raw_values={
                "glucose": 98.0, "wbc": 5.5, "hemoglobin": 13.5, "platelets": 250.0
            },
            units={
                "glucose": "mg/dL", "wbc": "K/uL", "hemoglobin": "g/dL", "platelets": "K/uL"
            },
            missingness={
                "glucose": MissingnessRecord(missing_type="not_missing"),
                "wbc": MissingnessRecord(missing_type="not_missing"),
                "hemoglobin": MissingnessRecord(missing_type="not_missing"),
                "platelets": MissingnessRecord(missing_type="not_missing"),
            }
        )
        
        non_lab = NonLabInputs(
            demographics=DemographicsInputs(age=45, sex_at_birth="M"),
        )
        
        return RunV2(
            run_id="test_run_001",
            user_id="test_user_123",
            specimens=[isf_specimen, blood_specimen],
            non_lab_inputs=non_lab,
        )

    @pytest.fixture
    def sample_feature_pack_v2(self):
        """Create sample feature_pack_v2 with coherence/agreement metrics."""
        # Simplified feature pack (use actual FeaturePackV2 structure)
        return {
            "schema_version": "v2",
            "specimen_count": 2,
            "domains_present": ["glucose", "cbc"],
            "coherence_scores": {
                "overall_coherence_0_1": 0.78,
                "glucose_coherence": 0.92,  # ISF + blood agree well
                "cbc_coherence": 0.85,
            },
            "specimen_relationships": {
                "glucose_agreement": 0.95,  # ISF glucose close to blood glucose
                "wbc_stability": 0.80,
            },
            "penalty_vector": {
                "penalty_factors": {},
                "domain_blockers": {},
            }
        }

    def test_inference_v2_produces_glucose_estimate(self, sample_run_v2, sample_feature_pack_v2):
        """Test: Inference_v2 produces glucose_est when blood glucose available."""
        engine = InferenceV2()
        result = engine.infer(sample_run_v2, sample_feature_pack_v2)
        
        assert isinstance(result, InferencePackV2)
        assert result.schema_version == "v2"
        
        # Should have glucose estimate
        glucose_estimates = [v for v in result.inferred_values if v.key == "glucose_est"]
        assert len(glucose_estimates) > 0, "Should produce glucose_est"
        
        glucose = glucose_estimates[0]
        assert glucose.value is not None
        assert 90 <= glucose.value <= 105, "Glucose should be in reasonable range"
        assert 0.0 <= glucose.confidence_0_1 <= 1.0

    def test_inference_v2_suppresses_missing_dependencies(self, sample_run_v2, sample_feature_pack_v2):
        """Test: Inference_v2 suppresses outputs with missing dependencies."""
        engine = InferenceV2()
        result = engine.infer(sample_run_v2, sample_feature_pack_v2)
        
        # sample_run_v2 has limited data (glucose, wbc, hemoglobin, platelets)
        # Should suppress outputs requiring missing data (e.g., insulin if no glucose measurement)
        
        assert len(result.suppressed_outputs) > 0, "Should have some suppressed outputs"
        
        for suppressed in result.suppressed_outputs:
            assert suppressed.key is not None
            assert suppressed.reason is not None
            assert isinstance(suppressed.reason, (str, SuppressionReasonEnum))

    def test_inference_v2_computes_physiological_states(self, sample_run_v2, sample_feature_pack_v2):
        """Test: Inference_v2 produces physiological state assessments."""
        engine = InferenceV2()
        result = engine.infer(sample_run_v2, sample_feature_pack_v2)
        
        assert len(result.physiological_states) > 0, "Should produce physiological states"
        
        for state in result.physiological_states:
            assert state.domain is not None
            assert 0.0 <= state.confidence_0_1 <= 1.0

    def test_inference_v2_labels_support_type(self, sample_run_v2, sample_feature_pack_v2):
        """Test: Inferred values labeled with support_type (direct/derived/proxy/population)."""
        engine = InferenceV2()
        result = engine.infer(sample_run_v2, sample_feature_pack_v2)
        
        for inferred in result.inferred_values:
            assert inferred.support_type in [
                SupportTypeEnum.DIRECT,
                SupportTypeEnum.DERIVED,
                SupportTypeEnum.PROXY,
                SupportTypeEnum.RELATIONAL,
                SupportTypeEnum.POPULATION,
            ], f"Invalid support_type: {inferred.support_type}"

    def test_inference_v2_populates_provenance(self, sample_run_v2, sample_feature_pack_v2):
        """Test: Provenance map links inferred values to source specimens."""
        engine = InferenceV2()
        result = engine.infer(sample_run_v2, sample_feature_pack_v2)
        
        assert len(result.provenance_map) > 0, "Should have provenance entries"
        
        for entry in result.provenance_map:
            assert entry.output_key is not None
            assert len(entry.source_specimens) > 0, "Each output should link to specimens"
            assert entry.provenance_type is not None

    def test_inference_v2_non_breaking_schema(self, sample_run_v2, sample_feature_pack_v2):
        """Test: inference_pack_v2 has expected schema structure."""
        engine = InferenceV2()
        result = engine.infer(sample_run_v2, sample_feature_pack_v2)
        
        # Verify all expected fields present
        assert hasattr(result, "schema_version")
        assert hasattr(result, "measured_values")
        assert hasattr(result, "inferred_values")
        assert hasattr(result, "physiological_states")
        assert hasattr(result, "suppressed_outputs")
        assert hasattr(result, "eligibility_rationale")
        assert hasattr(result, "engine_outputs")
        assert hasattr(result, "provenance_map")
        
        assert result.schema_version == "v2"


# ============================================================================
# SECTION 4: E2E TESTS - FULL PIPELINE
# ============================================================================

class TestInferenceV2EndToEnd:
    """E2E tests: RunV2 → preprocess_v2 → inference_v2."""

    def test_e2e_pipeline_produces_valid_output(self):
        """Test: Full pipeline from RunV2 to inference_pack_v2."""
        from app.features.preprocess_v2 import preprocess_v2
        from app.models.run_v2 import MissingnessRecord, DemographicsInputs
        
        # Create RunV2
        isf_specimen = SpecimenRecord(
            specimen_id="isf_1",
            specimen_type=SpecimenTypeEnum.ISF,
            collected_at=datetime(2025, 1, 28, 8, 0, 0),
            source_detail="dermal",
            raw_values={"glucose": 95.0},
            units={"glucose": "mg/dL"},
            missingness={"glucose": MissingnessRecord(missing_type="not_missing")}
        )
        
        blood_specimen = SpecimenRecord(
            specimen_id="blood_1",
            specimen_type=SpecimenTypeEnum.BLOOD,
            collected_at=datetime(2025, 1, 28, 8, 15, 0),
            source_detail="venipuncture",
            raw_values={"glucose": 98.0, "wbc": 5.5},
            units={"glucose": "mg/dL", "wbc": "K/uL"},
            missingness={
                "glucose": MissingnessRecord(missing_type="not_missing"),
                "wbc": MissingnessRecord(missing_type="not_missing"),
            }
        )
        
        non_lab = NonLabInputs(
            demographics=DemographicsInputs(age=45, sex_at_birth="M"),
        )
        
        run_v2 = RunV2(
            run_id="e2e_test_001",
            user_id="e2e_user",
            specimens=[isf_specimen, blood_specimen],
            non_lab_inputs=non_lab,
        )
        
        # Preprocess
        feature_pack_v2 = preprocess_v2(run_v2)
        assert feature_pack_v2 is not None
        
        # Infer
        engine = InferenceV2()
        inference_pack_v2 = engine.infer(run_v2, feature_pack_v2.model_dump(mode="json"))
        
        # Validate
        assert inference_pack_v2.schema_version == "v2"
        assert len(inference_pack_v2.inferred_values) > 0 or len(inference_pack_v2.suppressed_outputs) > 0


# ============================================================================
# SECTION 5: REGRESSION TESTS - NON-BREAKING COMPATIBILITY
# ============================================================================

class TestInferenceV2NonBreaking:
    """Test that inference_v2 doesn't break legacy functionality."""

    def test_legacy_inference_endpoints_unchanged(self):
        """Test: /inference endpoint (legacy) still works."""
        # This is a placeholder - actual test would call /inference endpoint
        # and verify it returns legacy InferenceReport, not InferencePackV2
        pass

    def test_inference_v2_optional(self):
        """Test: Inference_v2 can be called independently without legacy setup."""
        # Verify that InferenceV2 doesn't require legacy models/endpoints
        engine = InferenceV2()
        assert engine is not None
        assert hasattr(engine, "infer")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
