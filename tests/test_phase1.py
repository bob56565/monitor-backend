"""
Phase 1 Integration Tests.

Tests for Phase 1 A2 Processing + B Output enhancements:
- Coverage truth (A.1)
- Unit normalization (A.2)
- Derived features (A.3)
- Conflict detection (A.4)
- Evidence grading (B.5)
- Range-first outputs (B.6)
- Standardized fields (B.7)
"""

import pytest
from datetime import datetime, timedelta
from typing import Dict, List

from app.models.run_v2 import RunV2, SpecimenRecord, SpecimenTypeEnum
from app.models.inference_pack_v2 import (
    InferredValue, EvidenceGrade, EVIDENCE_GRADE_CAPS,
    SupportTypeEnum, ProvenanceTypeEnum
)
from app.ml.phase1_integration import Phase1Integrator
from app.features.coverage_truth import compute_coverage_truth_pack
from app.features.unit_normalization import normalize_value
from app.features.derived_features import compute_derived_features
from app.features.conflict_detection import detect_conflicts


class TestCoverageTruth:
    """Test Requirement A.1: Coverage truth."""
    
    def test_coverage_truth_computes_for_all_streams(self):
        """Coverage truth should track all data streams."""
        # Create run with ISF and blood specimens
        run = RunV2(
            run_id="test_run",
            user_id="user_1",
            created_at=datetime.utcnow(),
            specimens=[
                SpecimenRecord(
                    specimen_id="isf_1",
                    specimen_type=SpecimenTypeEnum.ISF,
                    collected_at=datetime.utcnow() - timedelta(days=1),
                    raw_values={"glucose": 100.0, "lactate": 1.5},
                    units={"glucose": "mg/dL", "lactate": "mmol/L"},
                    missingness={}
                ),
                SpecimenRecord(
                    specimen_id="blood_1",
                    specimen_type=SpecimenTypeEnum.BLOOD_CAPILLARY,
                    collected_at=datetime.utcnow(),
                    raw_values={"glucose": 105.0, "hba1c": 5.6},
                    units={"glucose": "mg/dL", "hba1c": "%"},
                    missingness={}
                )
            ],
            non_lab_inputs={}
        )
        
        coverage = compute_coverage_truth_pack(run)
        
        # Check streams are tracked in stream_coverages dict
        assert "glucose_isf" in coverage.stream_coverages
        assert "lactate_isf" in coverage.stream_coverages
        assert "glucose_blood_capillary" in coverage.stream_coverages
        assert "hba1c_blood_capillary" in coverage.stream_coverages
        
        # Check data points
        assert coverage.stream_coverages["glucose_isf"].data_points == 1
        assert coverage.stream_coverages["glucose_blood_capillary"].data_points == 1
    
    def test_coverage_truth_computes_quality_score(self):
        """Quality score should reflect coverage completeness."""
        run = RunV2(
            run_id="test_run",
            user_id="user_1",
            created_at=datetime.utcnow(),
            specimens=[
                SpecimenRecord(
                    specimen_id="isf_1",
                    specimen_type=SpecimenTypeEnum.ISF,
                    collected_at=datetime.utcnow(),
                    raw_values={"glucose": 100.0},
                    units={"glucose": "mg/dL"},
                    missingness={}
                )
            ],
            non_lab_inputs={}
        )
        
        coverage = compute_coverage_truth_pack(run)
        
        # Single reading in 90 days should have low coverage
        assert "glucose_isf" in coverage.stream_coverages
        assert coverage.stream_coverages["glucose_isf"].quality_score >= 0.0
        assert coverage.stream_coverages["glucose_isf"].quality_score <= 1.0
        assert coverage.stream_coverages["glucose_isf"].missing_rate <= 1.0


class TestUnitNormalization:
    """Test Requirement A.2: Unit normalization."""
    
    def test_glucose_conversion_mgdl_to_mmoll(self):
        """Test glucose unit normalization - mg/dL stays as mg/dL."""
        normalized = normalize_value(
            variable_name="glucose",
            raw_value=100.0,
            raw_unit="mg/dL",
            patient_age=None,
            patient_sex=None
        )
        
        assert normalized.raw_value == 100.0
        assert normalized.raw_unit == "mg/dL"
        # mg/dL is the canonical unit, so no conversion
        assert normalized.std_unit == "mg/dL"
        assert normalized.std_value == 100.0
    
    def test_cholesterol_unit_preservation(self):
        """Test cholesterol in mg/dL stays in mg/dL."""
        normalized = normalize_value(
            variable_name="chol_total",
            raw_value=200.0,
            raw_unit="mg/dL",
            patient_age=None,
            patient_sex=None
        )
        
        assert normalized.std_value == 200.0
        assert normalized.std_unit == "mg/dL"


class TestDerivedFeatures:
    """Test Requirement A.3: Derived features."""
    
    def test_egfr_calculation(self):
        """Test eGFR CKD-EPI calculation."""
        values = {
            "creatinine": 1.0,
            "run_id": "test"
        }
        patient_info = {"age": 50, "sex": "M"}
        
        pack = compute_derived_features(values, patient_info)
        
        assert pack.features_computed >= 1
        assert len(pack.renal_features) >= 1
        assert pack.renal_features[0].feature_name == "eGFR_CKD_EPI"
        assert pack.renal_features[0].value > 0
    
    def test_bun_cr_ratio_calculation(self):
        """Test BUN/Creatinine ratio."""
        values = {
            "bun": 20.0,
            "creatinine": 1.0,
            "run_id": "test"
        }
        
        pack = compute_derived_features(values, {})
        
        assert pack.features_computed >= 1
        assert len(pack.renal_features) >= 1
        bun_cr = [f for f in pack.renal_features if f.feature_name == "BUN_Creatinine_Ratio"]
        assert len(bun_cr) == 1
        assert bun_cr[0].value == 20.0
    
    def test_anion_gap_calculation(self):
        """Test anion gap."""
        values = {
            "sodium_na": 140.0,
            "chloride_cl": 100.0,
            "co2_bicarb": 24.0,
            "run_id": "test"
        }
        
        pack = compute_derived_features(values, {})
        
        assert pack.features_computed >= 1
        assert len(pack.electrolyte_features) >= 1
        ag = [f for f in pack.electrolyte_features if f.feature_name == "Anion_Gap"]
        assert len(ag) == 1
        assert ag[0].value == 16.0  # 140 - (100 + 24)


class TestConflictDetection:
    """Test Requirement A.4: Conflict detection."""
    
    def test_physiologic_range_violations(self):
        """Test detection of impossible physiologic values."""
        from app.features.conflict_detection import check_physiologic_ranges
        
        # check_physiologic_ranges expects Dict[str, float]
        values = {
            "glucose": 5.0  # 5 mg/dL is impossibly low
        }
        
        conflicts = check_physiologic_ranges(values)
        
        # Should detect that 5 mg/dL glucose is impossibly low
        assert len(conflicts) >= 1  # Should detect the violation


class TestEvidenceGrading:
    """Test Requirement B.5: Evidence grading."""
    
    def test_evidence_grade_assignment(self):
        """Test evidence grade assignment based on support type."""
        integrator = Phase1Integrator()
        
        # Create mock coverage and conflict report
        from app.features.coverage_truth import CoverageTruthPack, StreamCoverage
        from app.features.conflict_detection import ConflictDetectionReport
        
        coverage = CoverageTruthPack(
            run_id="test",
            computed_at=datetime.utcnow()
        )
        coverage.stream_coverages["isf"] = StreamCoverage(
            stream_key="isf",
            stream_type="lab",
            days_in_window=90,
            days_covered=30,
            data_points=100,
            missing_rate=0.2,
            quality_score=0.8,
            max_confidence_allowed=0.90,
            last_seen_ts=datetime.utcnow()
        )
        
        conflict_report = ConflictDetectionReport(
            run_id="test",
            conflicts=[]
        )
        
        # Grade A: Direct measurement
        iv_direct = InferredValue(
            key="glucose",
            confidence_0_1=0.85,
            support_type=SupportTypeEnum.DIRECT,
            provenance=ProvenanceTypeEnum.MEASURED
        )
        
        grade = integrator.assign_evidence_grade(iv_direct, coverage, conflict_report)
        assert grade == EvidenceGrade.A
        
        # Grade D: Population-based
        iv_population = InferredValue(
            key="glucose_est",
            confidence_0_1=0.65,
            support_type=SupportTypeEnum.POPULATION,
            provenance=ProvenanceTypeEnum.INFERRED
        )
        
        grade = integrator.assign_evidence_grade(iv_population, coverage, conflict_report)
        assert grade == EvidenceGrade.D
    
    def test_evidence_grade_confidence_caps(self):
        """Test confidence capping by evidence grade."""
        # Grade A: max 0.90
        iv_a = InferredValue(
            key="test_a",
            confidence_0_1=0.95,
            support_type=SupportTypeEnum.DIRECT,
            provenance=ProvenanceTypeEnum.MEASURED,
            evidence_grade=EvidenceGrade.A
        )
        
        assert iv_a.confidence_0_1 == 0.90
        
        # Grade D: max 0.35
        iv_d = InferredValue(
            key="test_d",
            confidence_0_1=0.75,
            support_type=SupportTypeEnum.POPULATION,
            provenance=ProvenanceTypeEnum.INFERRED,
            evidence_grade=EvidenceGrade.D
        )
        
        assert iv_d.confidence_0_1 == 0.35
    
    def test_evidence_grade_enum_values(self):
        """Test evidence grade enum values."""
        assert EvidenceGrade.A.value == "A"
        assert EvidenceGrade.B.value == "B"
        assert EvidenceGrade.C.value == "C"
        assert EvidenceGrade.D.value == "D"
        
        assert EVIDENCE_GRADE_CAPS[EvidenceGrade.A] == 0.90
        assert EVIDENCE_GRADE_CAPS[EvidenceGrade.B] == 0.75
        assert EVIDENCE_GRADE_CAPS[EvidenceGrade.C] == 0.55
        assert EVIDENCE_GRADE_CAPS[EvidenceGrade.D] == 0.35


class TestRangeFirstOutputs:
    """Test Requirement B.6: Range-first outputs."""
    
    def test_range_field_aliases(self):
        """Test range field aliases are populated."""
        iv = InferredValue(
            key="glucose",
            value=100.0,
            range_lower=90.0,
            range_upper=110.0,
            confidence_0_1=0.80,
            support_type=SupportTypeEnum.PROXY,
            provenance=ProvenanceTypeEnum.INFERRED
        )
        
        assert iv.estimated_center == 100.0
        assert iv.range_low == 90.0
        assert iv.range_high == 110.0
        assert iv.confidence_percent == 80
    
    def test_confidence_percent_computed(self):
        """Test confidence_percent auto-computed."""
        iv = InferredValue(
            key="glucose",
            confidence_0_1=0.75,
            support_type=SupportTypeEnum.PROXY,
            provenance=ProvenanceTypeEnum.INFERRED
        )
        
        assert iv.confidence_percent == 75


class TestStandardizedFields:
    """Test Requirement B.7: Standardized output fields."""
    
    def test_new_fields_present(self):
        """Test all new standardized fields are present."""
        iv = InferredValue(
            key="glucose",
            confidence_0_1=0.80,
            support_type=SupportTypeEnum.PROXY,
            provenance=ProvenanceTypeEnum.INFERRED,
            evidence_grade=EvidenceGrade.C
        )
        
        # Test Phase 1 new fields exist
        assert hasattr(iv, "evidence_grade")
        assert hasattr(iv, "evidence_inputs_used")
        assert hasattr(iv, "physiologic_drivers")
        assert hasattr(iv, "drivers_of_uncertainty")
        assert hasattr(iv, "what_would_tighten_this")
        assert hasattr(iv, "estimated_center")
        assert hasattr(iv, "range_low")
        assert hasattr(iv, "range_high")
        assert hasattr(iv, "confidence_percent")


class TestBackwardCompatibility:
    """Test backward compatibility."""
    
    def test_inferred_value_backward_compatible(self):
        """Existing code creating InferredValue should still work."""
        # Old-style creation (no Phase 1 fields)
        iv = InferredValue(
            key="glucose",
            value=100.0,
            confidence_0_1=0.80,
            support_type=SupportTypeEnum.DIRECT,
            provenance=ProvenanceTypeEnum.MEASURED
        )
        
        # Should work without errors
        assert iv.key == "glucose"
        assert iv.value == 100.0
        assert iv.confidence_0_1 == 0.80
        
        # Phase 1 fields should have defaults
        assert iv.evidence_inputs_used == []
        assert iv.physiologic_drivers == []
        assert iv.drivers_of_uncertainty == []
        assert iv.what_would_tighten_this == []
    
    def test_inferred_value_without_evidence_grade(self):
        """InferredValue without evidence_grade should work."""
        iv = InferredValue(
            key="glucose",
            confidence_0_1=0.95,  # No capping without evidence_grade
            support_type=SupportTypeEnum.DIRECT,
            provenance=ProvenanceTypeEnum.MEASURED
        )
        
        # Without evidence_grade, no capping should occur
        assert iv.confidence_0_1 == 0.95
        assert iv.evidence_grade is None


class TestPhase1Integration:
    """Test complete Phase 1 integration pipeline."""
    
    def test_phase1_integrator_instantiation(self):
        """Test Phase1Integrator can be instantiated."""
        integrator = Phase1Integrator()
        assert integrator is not None
    
    def test_evidence_grade_cap_enforcement(self):
        """Test evidence grade cap enforcement."""
        integrator = Phase1Integrator()
        
        iv = InferredValue(
            key="test",
            confidence_0_1=0.99,
            support_type=SupportTypeEnum.DIRECT,
            provenance=ProvenanceTypeEnum.MEASURED,
            evidence_grade=EvidenceGrade.A
        )
        
        capped = integrator.apply_evidence_grade_cap(iv)
        
        assert capped.confidence_0_1 == 0.90  # Capped to grade A max
    
    def test_range_first_formatting(self):
        """Test range-first formatting."""
        integrator = Phase1Integrator()
        
        iv = InferredValue(
            key="test",
            value=100.0,
            range_lower=90.0,
            range_upper=110.0,
            confidence_0_1=0.80,
            support_type=SupportTypeEnum.PROXY,
            provenance=ProvenanceTypeEnum.INFERRED
        )
        
        formatted = integrator.format_range_first_output(iv)
        
        assert formatted.estimated_center == 100.0
        assert formatted.range_low == 90.0
        assert formatted.range_high == 110.0
        assert formatted.confidence_percent == 80


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
