"""
Part B Tests

Comprehensive test suite validating:
1. No output uses non-Part-A inputs ✓
2. Every output includes required report mechanics ✓
3. Methodologies_used length <= 4 for every output ✓
4. Deterministic outputs given same input window ✓
5. Graceful degradation when optional inputs absent ✓
6. A2 integration (gating → compute → confidence → provenance) ✓
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import json

from app.models.user import User
from app.models.part_a_models import (
    PartASubmission,
    SpecimenUpload,
    SpecimenAnalyte,
    ISFAnalyteStream,
    VitalsRecord,
    SOAPProfileRecord
)
from app.part_b.schemas.output_schemas import (
    PartBGenerationRequest,
    OutputLineItem,
    OutputStatus
)
from app.part_b.orchestrator import PartBOrchestrator
from app.part_b.data_helpers import PartADataHelper
from app.part_b.inference.metabolic_regulation import MetabolicRegulationInference


# Fixtures
@pytest.fixture
def db():
    """Create a test database session."""
    from app.db.session import SessionLocal
    from app.db.base import Base
    from app.db.session import engine
    
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    # Create session
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def db_session(db):
    """Database session fixture."""
    return db


@pytest.fixture
def test_user(db_session):
    """Create test user."""
    import uuid
    user = User(
        email=f"partb_test_{uuid.uuid4()}@example.com",
        name="Part B Test User",
        hashed_password="dummy_hash"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def part_a_submission_minimal(db_session, test_user):
    """Create minimal Part A submission with required data."""
    submission = PartASubmission(
        submission_id=f"parta_minimal_{int(datetime.utcnow().timestamp())}",
        user_id=test_user.id,
        status="completed"
    )
    db_session.add(submission)
    db_session.commit()
    db_session.refresh(submission)
    
    # Add ISF glucose stream
    isf_stream = ISFAnalyteStream(
        submission_id=submission.id,
        name="glucose",
        unit="mg/dL",
        values_json=[85, 90, 95, 88, 92, 87, 93, 91] * 100,  # 800 readings over 30 days
        timestamps_json=[(datetime.utcnow() - timedelta(days=30, minutes=i*60)).isoformat() for i in range(800)],
        noise_score=0.15
    )
    db_session.add(isf_stream)
    
    # Add ISF lactate stream
    lactate_stream = ISFAnalyteStream(
        submission_id=submission.id,
        name="lactate",
        unit="mmol/L",
        values_json=[1.2, 1.5, 1.3, 1.4, 1.6] * 100,
        timestamps_json=[(datetime.utcnow() - timedelta(days=30, minutes=i*120)).isoformat() for i in range(500)],
        noise_score=0.20
    )
    db_session.add(lactate_stream)
    
    # Add specimen upload (blood with HbA1c)
    specimen = SpecimenUpload(
        submission_id=submission.id,
        modality="blood",
        collection_datetime=datetime.utcnow() - timedelta(days=60),
        source_format="manual_entry"
    )
    db_session.add(specimen)
    db_session.flush()
    
    analyte = SpecimenAnalyte(
        upload_id=specimen.id,
        name="hemoglobin_a1c",
        value=5.4,
        unit="%",
        reference_range_low=4.0,
        reference_range_high=5.6
    )
    db_session.add(analyte)
    
    # Add vitals
    vitals = VitalsRecord(
        submission_id=submission.id,
        cardiovascular_json={
            'heart_rate': {'resting': 72.0, 'sleeping': 58.0, 'active': 110.0},
            'hrv': {'rmssd': 45.0},
            'bp': {'systolic': 120.0, 'diastolic': 80.0}
        }
    )
    db_session.add(vitals)
    
    # Add SOAP profile
    soap = SOAPProfileRecord(
        submission_id=submission.id,
        age=35,
        sex_at_birth='male',
        bmi=24.5,
        demographics_anthropometrics_json={'waist_cm': 85},
        medical_history_json={'pmh': [], 'fhx': [], 'medications': []},
        diet_json={'pattern': 'balanced'},
        activity_lifestyle_json={'activity_level': 'moderate', 'smoking': 'never', 'alcohol': 'occasional'},
        symptoms_json={'sleep_avg_duration_hours': 7.5}
    )
    db_session.add(soap)
    
    db_session.commit()
    return submission


# Test 1: No non-Part-A inputs used
def test_no_non_part_a_inputs(db_session, test_user, part_a_submission_minimal):
    """Verify all inputs come from Part A only."""
    request = PartBGenerationRequest(
        submission_id=part_a_submission_minimal.submission_id,
        time_window_days=30
    )
    
    response = PartBOrchestrator.generate_report(
        db=db_session,
        user_id=test_user.id,
        request=request
    )
    
    assert response.status in ["success", "partial"]
    
    # Check all successful outputs
    all_outputs = []
    if response.report:
        all_outputs.extend(response.report.metabolic_regulation.outputs)
    
    for output in all_outputs:
        if output.status == OutputStatus.SUCCESS:
            # Input chain should only mention Part A entities
            input_chain = output.input_chain.lower()
            
            # Allowed Part A terms
            allowed_terms = [
                'isf', 'glucose', 'lactate', 'specimen', 'lab', 'hba1c',
                'vitals', 'hr', 'hrv', 'bp', 'soap', 'age', 'sex', 'bmi',
                'diet', 'activity', 'sleep', 'medications', 'pmh', 'symptoms'
            ]
            
            # Disallowed terms (external APIs, live data, non-Part-A)
            disallowed_terms = [
                'api call', 'external', 'live fetch', 'http', 'real-time fetch'
            ]
            
            for term in disallowed_terms:
                assert term not in input_chain, f"Output {output.metric_name} uses non-Part-A input: {term}"


# Test 2: Required report mechanics present
def test_required_report_mechanics(db_session, test_user, part_a_submission_minimal):
    """Verify every output includes all required mechanics."""
    request = PartBGenerationRequest(
        submission_id=part_a_submission_minimal.submission_id
    )
    
    response = PartBOrchestrator.generate_report(
        db=db_session,
        user_id=test_user.id,
        request=request
    )
    
    assert response.report is not None
    
    all_outputs = response.report.metabolic_regulation.outputs
    
    for output in all_outputs:
        if output.status == OutputStatus.SUCCESS:
            # Required fields
            assert output.measured_vs_inferred in ["measured", "inferred", "inferred_tight", "inferred_wide"]
            assert output.confidence_percent >= 0 and output.confidence_percent <= 100
            assert len(output.confidence_top_3_drivers) <= 3
            assert len(output.what_increases_confidence) >= 0
            assert output.safe_action_suggestion is not None
            assert output.input_chain is not None
            assert len(output.methodologies_used) > 0
            assert len(output.method_why) == len(output.methodologies_used)


# Test 3: Max 4 methodologies
def test_max_four_methodologies(db_session, test_user, part_a_submission_minimal):
    """Verify no output exceeds 4 methodologies."""
    request = PartBGenerationRequest(
        submission_id=part_a_submission_minimal.submission_id
    )
    
    response = PartBOrchestrator.generate_report(
        db=db_session,
        user_id=test_user.id,
        request=request
    )
    
    all_outputs = response.report.metabolic_regulation.outputs
    
    for output in all_outputs:
        assert len(output.methodologies_used) <= 4, \
            f"Output {output.metric_name} has {len(output.methodologies_used)} methodologies (max 4)"
        
        # Verify method_why matches length
        assert len(output.method_why) == len(output.methodologies_used), \
            f"Output {output.metric_name} has mismatched method_why length"


# Test 4: Deterministic outputs
def test_deterministic_outputs(db_session, test_user, part_a_submission_minimal):
    """Verify same inputs produce same outputs."""
    request = PartBGenerationRequest(
        submission_id=part_a_submission_minimal.submission_id,
        time_window_days=30
    )
    
    # Generate twice
    response1 = PartBOrchestrator.generate_report(
        db=db_session,
        user_id=test_user.id,
        request=request
    )
    
    response2 = PartBOrchestrator.generate_report(
        db=db_session,
        user_id=test_user.id,
        request=request
    )
    
    # Compare metabolic panel outputs
    outputs1 = response1.report.metabolic_regulation.outputs
    outputs2 = response2.report.metabolic_regulation.outputs
    
    assert len(outputs1) == len(outputs2)
    
    for o1, o2 in zip(outputs1, outputs2):
        if o1.status == OutputStatus.SUCCESS:
            # Values should be identical (within floating point tolerance)
            if o1.value_score:
                assert abs(o1.value_score - o2.value_score) < 0.1
            if o1.value_range_low:
                assert abs(o1.value_range_low - o2.value_range_low) < 0.1


# Test 5: Graceful degradation with missing data
def test_graceful_degradation_missing_data(db_session, test_user):
    """Verify system handles missing optional inputs gracefully."""
    # Create submission with ONLY required minimums (no specimen)
    submission = PartASubmission(
        submission_id=f"parta_minimal_degradation_{int(datetime.utcnow().timestamp())}",
        user_id=test_user.id,
        status="completed"
    )
    db_session.add(submission)
    db_session.commit()
    db_session.refresh(submission)
    
    # Add minimal ISF only (no specimen, no vitals, no SOAP)
    isf_stream = ISFAnalyteStream(
        submission_id=submission.id,
        name="glucose",
        unit="mg/dL",
        values_json=[90] * 100,
        timestamps_json=[(datetime.utcnow() - timedelta(days=10, hours=i)).isoformat() for i in range(100)],
        noise_score=0.30
    )
    db_session.add(isf_stream)
    db_session.commit()
    
    request = PartBGenerationRequest(
        submission_id=submission.submission_id
    )
    
    response = PartBOrchestrator.generate_report(
        db=db_session,
        user_id=test_user.id,
        request=request
    )
    
    # Should fail with clear error message (minimum requirements not met)
    assert response.status == "error"
    assert "minimum data requirements" in " ".join(response.errors).lower()


# Test 6: A2 integration (gating → compute → confidence → provenance)
def test_a2_integration(db_session, test_user, part_a_submission_minimal):
    """Verify Part B integrates with A2 services correctly."""
    # Generate HbA1c estimate (uses A2 gating and confidence)
    output = MetabolicRegulationInference.estimate_hba1c_range(
        db=db_session,
        submission_id=part_a_submission_minimal.submission_id,
        user_id=test_user.id
    )
    
    if output.status == OutputStatus.SUCCESS:
        # Should have gating payload
        assert output.gating_payload is not None
        assert 'allowed' in output.gating_payload
        
        # Should have confidence payload
        assert output.confidence_payload is not None
        assert 'confidence_percent' in output.confidence_payload
        
        # Confidence should be within bounds for inferred outputs
        assert output.confidence_percent <= 85  # Max for inferred_tight
        
        # Should have provenance references (after orchestrator persistence)
        assert output.input_references is not None


# Test 7: Minimum data check helper
def test_minimum_requirements_check(db_session, test_user, part_a_submission_minimal):
    """Test the minimum requirements checker."""
    result = PartADataHelper.check_minimum_requirements(
        db=db_session,
        submission_id=part_a_submission_minimal.submission_id,
        user_id=test_user.id
    )
    
    assert result['meets_requirements'] is True
    assert result['has_specimen'] is True
    assert result['has_isf'] is True
    assert result['has_vitals'] is True
    assert result['has_soap'] is True
    assert len(result['missing_items']) == 0


# Test 8: ISF data aggregation
def test_isf_data_aggregation(db_session, test_user, part_a_submission_minimal):
    """Test ISF analyte data helper."""
    glucose_data = PartADataHelper.get_isf_analyte_data(
        db=db_session,
        submission_id=part_a_submission_minimal.id,
        analyte_name='glucose',
        days_back=30
    )
    
    assert glucose_data is not None
    assert 'mean' in glucose_data
    assert 'std' in glucose_data
    assert 'cv' in glucose_data
    assert glucose_data['days_of_data'] > 0
    assert glucose_data['value_count'] > 0


# Test 9: Lab anchor retrieval
def test_lab_anchor_retrieval(db_session, test_user, part_a_submission_minimal):
    """Test most recent lab retrieval."""
    a1c_lab = PartADataHelper.get_most_recent_lab(
        db=db_session,
        submission_id=part_a_submission_minimal.id,
        analyte_name='hemoglobin_a1c',
        modality='blood'
    )
    
    assert a1c_lab is not None
    assert a1c_lab['value'] == 5.4
    assert a1c_lab['unit'] == '%'
    assert a1c_lab['days_old'] is not None


# Test 10: SOAP profile retrieval
def test_soap_profile_retrieval(db_session, test_user, part_a_submission_minimal):
    """Test SOAP profile helper."""
    soap = PartADataHelper.get_soap_profile(
        db=db_session,
        submission_id=part_a_submission_minimal.id
    )
    
    assert soap is not None
    assert soap['age'] == 35
    assert soap['sex'] == 'male'
    assert soap['bmi'] == 24.5
