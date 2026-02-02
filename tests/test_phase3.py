"""
Comprehensive Phase 3 Tests

Tests all Phase 3 components:
- Uncertainty reduction planner
- Cohort matching engine
- Change point detection
- Provider summary generator
- Cost/care impact modules
- Explainability engine
- Language control system
- Phase 3 integration
"""

import pytest
from datetime import datetime, timedelta
from app.features.uncertainty_reduction import (
    get_uncertainty_reduction_planner,
    UncertaintySource
)
from app.features.cohort_matching import (
    get_cohort_matching_engine,
    CohortMatchingProfile
)
from app.features.change_point_detection import (
    get_change_point_detector,
    ChangePointType,
    ChangeDirection
)
from app.features.provider_summary import get_provider_summary_generator
from app.features.cost_care_impact import (
    get_cost_care_impact_analyzer,
    ConfidenceLevel
)
from app.features.explainability import get_explainability_engine
from app.features.language_control import (
    get_language_controller,
    LanguageViolationType
)
from app.ml.phase3_integration import (
    get_phase3_integrator,
    Phase3FeatureFlags
)


# ===== Test Fixtures =====

@pytest.fixture
def sample_estimates():
    """Sample estimates for testing."""
    return {
        "glucose": {
            "estimated_value": 105.0,
            "estimated_value_low": 95.0,
            "estimated_value_high": 115.0,
            "confidence": 0.7,
            "evidence_grade": "B",
            "anchor_strength": "MODERATE",
            "primary_anchor": "glucose_isf"
        },
        "a1c": {
            "estimated_value": 5.8,
            "estimated_value_low": 5.5,
            "estimated_value_high": 6.1,
            "confidence": 0.6,
            "evidence_grade": "B",
            "anchor_strength": "WEAK"
        },
        "ldl": {
            "estimated_value": 120.0,
            "estimated_value_low": 100.0,
            "estimated_value_high": 140.0,
            "confidence": 0.4,
            "evidence_grade": "C",
            "anchor_strength": "NONE"
        }
    }


@pytest.fixture
def sample_historical_data():
    """Sample historical data for testing."""
    now = datetime.now()
    
    # Generate 60 days of glucose data
    glucose_data = [
        {
            "timestamp": now - timedelta(days=60-i),
            "value": 95.0 + (i % 20)  # Varies between 95-115
        }
        for i in range(60)
    ]
    
    # A1c data (sparse)
    a1c_data = [
        {"timestamp": now - timedelta(days=90), "value": 5.7},
        {"timestamp": now - timedelta(days=30), "value": 5.8}
    ]
    
    return {
        "glucose": glucose_data,
        "a1c": a1c_data,
        "weight": [],
        "heart_rate": []
    }


@pytest.fixture
def sample_measured_anchors():
    """Sample measured anchors."""
    return {
        "glucose_isf": 105.0,
        "a1c": None,
        "ldl": None
    }


@pytest.fixture
def sample_phase2_metadata():
    """Sample Phase 2 metadata."""
    return {
        "personal_baseline_used": True,
        "baseline_confidence": 0.7,
        "solver_agreement": {
            "converged": True,
            "agreement_score": 0.8
        },
        "temporal_stability_high": True,
        "constraint_conflicts": 0
    }


# ===== Uncertainty Reduction Planner Tests =====

class TestUncertaintyReductionPlanner:
    """Test uncertainty reduction planner."""
    
    def test_planner_initialization(self):
        """Test planner initializes correctly."""
        planner = get_uncertainty_reduction_planner()
        assert planner is not None
        assert planner.measurement_impact_graph is not None
    
    def test_plan_uncertainty_reduction(self, sample_estimates, sample_measured_anchors, sample_historical_data):
        """Test uncertainty reduction planning."""
        planner = get_uncertainty_reduction_planner()
        
        plan = planner.plan_uncertainty_reduction(
            current_estimates=sample_estimates,
            measured_anchors=sample_measured_anchors,
            historical_data=sample_historical_data,
            metadata={}
        )
        
        assert "uncertainty_profiles" in plan
        assert "top_recommendations" in plan
        assert "overall_uncertainty_score" in plan
        
        # Should have recommendations
        assert len(plan["top_recommendations"]) > 0
        
        # First recommendation should have required fields
        rec = plan["top_recommendations"][0]
        assert "measurement" in rec
        assert "outputs_affected" in rec
        assert "expected_reduction_percent" in rec
        assert "reason" in rec
    
    def test_uncertainty_profiles(self, sample_estimates, sample_measured_anchors, sample_historical_data):
        """Test uncertainty profile generation."""
        planner = get_uncertainty_reduction_planner()
        
        plan = planner.plan_uncertainty_reduction(
            current_estimates=sample_estimates,
            measured_anchors=sample_measured_anchors,
            historical_data=sample_historical_data,
            metadata={}
        )
        
        profiles = plan["uncertainty_profiles"]
        
        # Should have profiles for all estimates
        assert "glucose" in profiles
        assert "a1c" in profiles
        assert "ldl" in profiles
        
        # Profile should have required fields
        glucose_profile = profiles["glucose"]
        assert "confidence" in glucose_profile
        assert "range_width_percent" in glucose_profile
        assert "primary_source" in glucose_profile
        assert "anchor_strength" in glucose_profile


# ===== Cohort Matching Tests =====

class TestCohortMatching:
    """Test cohort matching engine."""
    
    def test_cohort_matching_initialization(self):
        """Test cohort matching engine initializes."""
        engine = get_cohort_matching_engine()
        assert engine is not None
        assert len(engine.reference_cohorts) > 0
    
    def test_match_cohort(self, sample_estimates, sample_measured_anchors, sample_historical_data):
        """Test cohort matching."""
        engine = get_cohort_matching_engine()
        
        match = engine.match_cohort(
            current_estimates=sample_estimates,
            measured_anchors=sample_measured_anchors,
            historical_data=sample_historical_data,
            user_metadata={"age": 45, "sex": "mixed"}
        )
        
        assert match.matched_cohort_id is not None
        assert match.overall_similarity_score >= 0.0
        assert match.overall_similarity_score <= 1.0
        assert match.similarity_level is not None
    
    def test_cohort_suppression(self, sample_estimates, sample_measured_anchors, sample_historical_data):
        """Test cohort suppression when similarity too low."""
        engine = get_cohort_matching_engine()
        
        match = engine.match_cohort(
            current_estimates=sample_estimates,
            measured_anchors=sample_measured_anchors,
            historical_data=sample_historical_data,
            user_metadata={}
        )
        
        # Should have suppression flag
        assert hasattr(match, "suppress_cohort_claims")


# ===== Change Point Detection Tests =====

class TestChangePointDetection:
    """Test change point detection."""
    
    def test_detector_initialization(self):
        """Test detector initializes correctly."""
        detector = get_change_point_detector()
        assert detector is not None
        assert detector.sensitivity_thresholds is not None
    
    def test_detect_change_points(self, sample_historical_data):
        """Test change point detection."""
        detector = get_change_point_detector()
        
        analysis = detector.detect_change_points(
            marker_id="glucose",
            historical_data=sample_historical_data["glucose"],
            marker_kinetics=None
        )
        
        assert analysis.marker_id == "glucose"
        assert isinstance(analysis.events, list)
        assert analysis.current_phase is not None
        assert analysis.overall_trend is not None
    
    def test_insufficient_data_handling(self):
        """Test handling of insufficient data."""
        detector = get_change_point_detector()
        
        # Too little data
        sparse_data = [
            {"timestamp": datetime.now(), "value": 100.0}
        ]
        
        analysis = detector.detect_change_points(
            marker_id="glucose",
            historical_data=sparse_data,
            marker_kinetics=None
        )
        
        assert analysis.current_phase == "insufficient_data"
        assert len(analysis.events) == 0


# ===== Provider Summary Tests =====

class TestProviderSummary:
    """Test provider summary generator."""
    
    def test_summary_generation(self, sample_estimates, sample_measured_anchors, sample_historical_data, sample_phase2_metadata):
        """Test provider summary generation."""
        generator = get_provider_summary_generator()
        
        summary = generator.generate_summary(
            patient_id="test_patient",
            estimates=sample_estimates,
            measured_anchors=sample_measured_anchors,
            historical_data=sample_historical_data,
            phase2_metadata=sample_phase2_metadata,
            phase3_metadata=None,
            previous_report=None
        )
        
        assert summary.patient_id == "test_patient"
        assert summary.data_quality_grade is not None
        assert summary.what_changed is not None
        assert summary.what_matters_now is not None
        assert summary.what_is_stable is not None
    
    def test_summary_formatting(self, sample_estimates, sample_measured_anchors, sample_historical_data):
        """Test summary formatting."""
        generator = get_provider_summary_generator()
        
        summary = generator.generate_summary(
            patient_id="test_patient",
            estimates=sample_estimates,
            measured_anchors=sample_measured_anchors,
            historical_data=sample_historical_data,
            phase2_metadata=None,
            phase3_metadata=None,
            previous_report=None
        )
        
        formatted = generator.format_for_display(summary)
        
        assert isinstance(formatted, str)
        assert len(formatted) > 0
        assert "PROVIDER SUMMARY REPORT" in formatted


# ===== Cost/Care Impact Tests =====

class TestCostCareImpact:
    """Test cost and care impact analyzer."""
    
    def test_impact_analysis(self, sample_estimates, sample_measured_anchors, sample_historical_data, sample_phase2_metadata):
        """Test impact analysis."""
        analyzer = get_cost_care_impact_analyzer()
        
        modules = analyzer.analyze_impact(
            estimates=sample_estimates,
            measured_anchors=sample_measured_anchors,
            historical_data=sample_historical_data,
            phase2_metadata=sample_phase2_metadata,
            phase3_metadata=None,
            user_metadata={}
        )
        
        assert "tests_avoided" in modules
        assert "earlier_intervention" in modules
        assert "longitudinal_value" in modules
        
        # Each module should have required fields
        for module in modules.values():
            assert hasattr(module, "should_render")
            assert hasattr(module, "overall_confidence")
    
    def test_impact_suppression(self):
        """Test impact module suppression when data insufficient."""
        analyzer = get_cost_care_impact_analyzer()
        
        # Minimal data
        sparse_estimates = {"glucose": {"estimated_value": 100, "confidence": 0.2}}
        sparse_history = {"glucose": []}
        
        modules = analyzer.analyze_impact(
            estimates=sparse_estimates,
            measured_anchors={},
            historical_data=sparse_history,
            phase2_metadata=None,
            phase3_metadata=None,
            user_metadata={}
        )
        
        # Should suppress some modules
        suppressed_count = sum(1 for m in modules.values() if not m.should_render)
        assert suppressed_count > 0


# ===== Explainability Tests =====

class TestExplainability:
    """Test explainability engine."""
    
    def test_explain_output(self, sample_estimates, sample_phase2_metadata):
        """Test output explanation."""
        engine = get_explainability_engine()
        
        explanation = engine.explain_output(
            output_id="glucose",
            estimate=sample_estimates["glucose"],
            phase2_metadata=sample_phase2_metadata,
            phase3_metadata=None
        )
        
        assert explanation.output_id == "glucose"
        assert explanation.confidence == 0.7
        assert len(explanation.top_drivers) > 0
        assert explanation.because_sentence is not None
        assert explanation.confidence_bar is not None
        assert len(explanation.what_would_change_this) > 0
    
    def test_explain_batch(self, sample_estimates, sample_phase2_metadata):
        """Test batch explanation."""
        engine = get_explainability_engine()
        
        explanations = engine.explain_batch(
            estimates=sample_estimates,
            phase2_metadata=sample_phase2_metadata,
            phase3_metadata=None
        )
        
        assert len(explanations) == len(sample_estimates)
        assert "glucose" in explanations
        assert "a1c" in explanations


# ===== Language Control Tests =====

class TestLanguageControl:
    """Test language control system."""
    
    def test_forbidden_phrase_detection(self):
        """Test detection of forbidden phrases."""
        controller = get_language_controller()
        
        # Test diagnostic claims
        violations = controller.validate_text("You have diabetes")
        assert len(violations) > 0
        assert any(v.violation_type == LanguageViolationType.DIAGNOSTIC_CLAIM for v in violations)
    
    def test_safe_text_passes(self):
        """Test safe text passes validation."""
        controller = get_language_controller()
        
        safe_text = "Pattern consistent with elevated glucose levels. Consider discussing with your healthcare provider."
        violations = controller.validate_text(safe_text)
        
        # Should have few or no violations
        assert len(violations) <= 1
    
    def test_safe_phrase_generation(self):
        """Test safe phrase generation."""
        controller = get_language_controller()
        
        phrase = controller.safe_phrase(
            category="range_statement",
            value=105.0,
            confidence=0.7,
            evidence_grade="B",
            marker="glucose",
            low=95,
            high=115,
            units="mg/dL"
        )
        
        assert isinstance(phrase, str)
        assert len(phrase) > 0


# ===== Phase 3 Integration Tests =====

class TestPhase3Integration:
    """Test Phase 3 integration."""
    
    def test_integrator_initialization(self):
        """Test integrator initializes correctly."""
        integrator = get_phase3_integrator()
        assert integrator is not None
        assert integrator.uncertainty_planner is not None
        assert integrator.cohort_engine is not None
        assert integrator.change_detector is not None
    
    def test_full_integration(self, sample_estimates, sample_measured_anchors, sample_historical_data, sample_phase2_metadata):
        """Test full Phase 3 integration."""
        integrator = get_phase3_integrator()
        
        # Create mock RunV2
        class MockRun:
            run_id = "test_run_123"
        
        result = integrator.integrate_phase3(
            patient_id="test_patient",
            run_v2=MockRun(),
            estimates=sample_estimates,
            measured_anchors=sample_measured_anchors,
            historical_data=sample_historical_data,
            events=None,
            phase2_metadata=sample_phase2_metadata,
            previous_report=None
        )
        
        assert "estimates" in result
        assert "phase3_metadata" in result
        
        metadata = result["phase3_metadata"]
        
        # Check all Phase 3 components
        assert "uncertainty_reduction" in metadata
        assert "cohort_match" in metadata
        assert "change_point_analysis" in metadata
        assert "explanations" in metadata
        assert "provider_summary" in metadata
        assert "cost_impact" in metadata
    
    def test_feature_flags(self, sample_estimates, sample_measured_anchors, sample_historical_data):
        """Test feature flag control."""
        integrator = get_phase3_integrator()
        
        # Disable some features
        flags = Phase3FeatureFlags(
            enable_uncertainty_reduction_planner=False,
            enable_cohort_matching=False,
            enable_change_point_detection=True,
            enable_provider_summary=True,
            enable_cost_impact_modules=False,
            enable_tight_explainability=True
        )
        integrator.FEATURE_FLAGS = flags
        
        class MockRun:
            run_id = "test_run_123"
        
        result = integrator.integrate_phase3(
            patient_id="test_patient",
            run_v2=MockRun(),
            estimates=sample_estimates,
            measured_anchors=sample_measured_anchors,
            historical_data=sample_historical_data,
            events=None,
            phase2_metadata=None,
            previous_report=None
        )
        
        metadata = result["phase3_metadata"]
        
        # Disabled features should not be present
        assert "uncertainty_reduction" not in metadata
        assert "cohort_match" not in metadata
        
        # Enabled features should be present
        assert "change_point_analysis" in metadata
        assert "provider_summary" in metadata


# ===== Backward Compatibility Tests =====

class TestBackwardCompatibility:
    """Test backward compatibility with Phase 1 and Phase 2."""
    
    def test_estimates_unchanged(self, sample_estimates, sample_measured_anchors, sample_historical_data):
        """Test that Phase 3 does not modify estimates."""
        integrator = get_phase3_integrator()
        
        original_estimates = {k: dict(v) for k, v in sample_estimates.items()}
        
        class MockRun:
            run_id = "test_run_123"
        
        result = integrator.integrate_phase3(
            patient_id="test_patient",
            run_v2=MockRun(),
            estimates=sample_estimates,
            measured_anchors=sample_measured_anchors,
            historical_data=sample_historical_data,
            events=None,
            phase2_metadata=None,
            previous_report=None
        )
        
        # Estimates should be unchanged
        assert result["estimates"] == original_estimates
    
    def test_phase3_metadata_additive(self, sample_estimates, sample_measured_anchors, sample_historical_data):
        """Test that Phase 3 metadata is purely additive."""
        integrator = get_phase3_integrator()
        
        class MockRun:
            run_id = "test_run_123"
        
        result = integrator.integrate_phase3(
            patient_id="test_patient",
            run_v2=MockRun(),
            estimates=sample_estimates,
            measured_anchors=sample_measured_anchors,
            historical_data=sample_historical_data,
            events=None,
            phase2_metadata=None,
            previous_report=None
        )
        
        # Should have both estimates and phase3_metadata
        assert "estimates" in result
        assert "phase3_metadata" in result
        
        # phase3_metadata should not override existing fields
        metadata = result["phase3_metadata"]
        assert "estimated_value" not in metadata
        assert "confidence" not in metadata


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
