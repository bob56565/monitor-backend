"""
Tests for A2 Backbone Layer

Comprehensive tests for:
- Priors service
- Confidence engine
- Gating engine
- Provenance model and helper
- Data quality API endpoints
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.services.priors import priors_service
from app.services.confidence import confidence_engine, OutputType
from app.services.gating import gating_engine, RangeWidth
from app.models.provenance import InferenceProvenance, ProvenanceHelper
from app.models.user import User


class TestPriorsService:
    """Test priors service functionality."""
    
    def test_priors_service_singleton(self):
        """Test that priors service is a singleton."""
        service1 = priors_service
        from app.services.priors import priors_service as service2
        assert service1 is service2
    
    def test_get_percentiles_resting_hr(self):
        """Test getting resting HR percentiles."""
        percentiles = priors_service.get_percentiles(
            metric='resting_hr_bpm',
            age=35,
            sex='M'
        )
        
        assert percentiles is not None
        assert 'p50' in percentiles
        assert 'p90' in percentiles
        assert percentiles['p50'] > 0
        assert percentiles['p90'] > percentiles['p50']
    
    def test_get_percentiles_different_ages(self):
        """Test percentiles change with age."""
        young = priors_service.get_percentiles('resting_hr_bpm', 25, 'F')
        older = priors_service.get_percentiles('resting_hr_bpm', 65, 'F')
        
        assert young is not None
        assert older is not None
        # Older adults typically have slightly higher resting HR
        assert older['p50'] >= young['p50']
    
    def test_get_percentile_rank(self):
        """Test percentile rank calculation."""
        rank = priors_service.get_percentile_rank(
            metric='resting_hr_bpm',
            value=70,
            age=35,
            sex='M'
        )
        
        assert rank is not None
        assert 0 <= rank <= 100
    
    def test_get_reference_interval_glucose(self):
        """Test getting glucose reference interval."""
        ref = priors_service.get_reference_interval(
            analyte='glucose',
            age=35,
            sex='M'
        )
        
        assert ref is not None
        assert 'ref_low' in ref
        assert 'ref_high' in ref
        assert 'critical_low' in ref
        assert 'critical_high' in ref
        assert ref['ref_low'] == 70
        assert ref['ref_high'] == 100
    
    def test_get_reference_interval_with_sex_specific(self):
        """Test sex-specific reference intervals."""
        male_ref = priors_service.get_reference_interval('hemoglobin', 35, 'M')
        female_ref = priors_service.get_reference_interval('hemoglobin', 35, 'F')
        
        assert male_ref is not None
        assert female_ref is not None
        # Male hemoglobin ranges are higher
        assert male_ref['ref_low'] > female_ref['ref_low']
    
    def test_validate_units_and_ranges_normal(self):
        """Test validation of normal lab value."""
        result = priors_service.validate_units_and_ranges(
            analyte='glucose',
            value=85,
            units='mg/dL',
            age=35,
            sex='M'
        )
        
        assert result['valid'] is True
        assert result['status'] == 'normal'
    
    def test_validate_units_and_ranges_abnormal(self):
        """Test validation of abnormal but not critical value."""
        result = priors_service.validate_units_and_ranges(
            analyte='glucose',
            value=110,
            units='mg/dL',
            age=35,
            sex='M'
        )
        
        assert result['valid'] is True
        assert result['status'] == 'abnormal'
    
    def test_validate_units_and_ranges_critical(self):
        """Test validation of critical value."""
        result = priors_service.validate_units_and_ranges(
            analyte='glucose',
            value=30,
            units='mg/dL',
            age=35,
            sex='M'
        )
        
        assert result['valid'] is False
        assert result['status'] == 'critical'
    
    def test_get_calibration_constant(self):
        """Test getting calibration constants."""
        min_days = priors_service.get_calibration_constant(
            'gating_thresholds.minimum_data_windows_days.a1c_estimate'
        )
        
        assert min_days == 30
    
    def test_get_calibration_constant_with_default(self):
        """Test calibration constant with default fallback."""
        value = priors_service.get_calibration_constant(
            'nonexistent.path',
            default=42
        )
        
        assert value == 42


class TestConfidenceEngine:
    """Test confidence engine functionality."""
    
    def test_confidence_engine_singleton(self):
        """Test that confidence engine is a singleton."""
        engine1 = confidence_engine
        from app.services.confidence import confidence_engine as engine2
        assert engine1 is engine2
    
    def test_compute_confidence_measured(self):
        """Test confidence calculation for measured output."""
        result = confidence_engine.compute_confidence(
            output_type=OutputType.MEASURED,
            completeness_score=0.9,
            anchor_quality=1.0,
            recency_days=5
        )
        
        assert 'confidence_percent' in result
        assert 'top_3_drivers' in result
        assert 'what_increases_confidence' in result
        
        # Measured output should have high confidence
        assert result['confidence_percent'] >= 85
        assert result['confidence_percent'] <= 95  # Capped at 95
        assert len(result['top_3_drivers']) <= 3
    
    def test_compute_confidence_inferred_tight(self):
        """Test confidence calculation for tight inferred output."""
        result = confidence_engine.compute_confidence(
            output_type=OutputType.INFERRED_TIGHT,
            completeness_score=0.8,
            anchor_quality=0.9,
            recency_days=10,
            signal_quality=0.85
        )
        
        assert result['confidence_percent'] <= 85  # Capped for tight inferred
        # Recommendations are optional - high quality data may not need any
        assert 'what_increases_confidence' in result
    
    def test_compute_confidence_wide_range(self):
        """Test confidence calculation for wide range output."""
        result = confidence_engine.compute_confidence(
            output_type=OutputType.INFERRED_WIDE,
            completeness_score=0.5,
            anchor_quality=0.5,
            recency_days=30,
            signal_quality=0.70
        )
        
        assert result['confidence_percent'] <= 70  # Capped for wide
    
    def test_compute_confidence_no_anchor(self):
        """Test confidence calculation without anchor."""
        result = confidence_engine.compute_confidence(
            output_type=OutputType.INFERRED_NO_ANCHOR,
            completeness_score=0.7,
            anchor_quality=0.0,
            recency_days=15
        )
        
        assert result['confidence_percent'] <= 55  # Capped for no anchor
    
    def test_confidence_bounded_0_100(self):
        """Test that confidence is always bounded 0-100."""
        # Extreme low values
        result1 = confidence_engine.compute_confidence(
            output_type=OutputType.INFERRED_NO_ANCHOR,
            completeness_score=0.0,
            anchor_quality=0.0,
            recency_days=365
        )
        assert 0 <= result1['confidence_percent'] <= 100
        
        # Extreme high values
        result2 = confidence_engine.compute_confidence(
            output_type=OutputType.MEASURED,
            completeness_score=1.0,
            anchor_quality=1.0,
            recency_days=1,
            signal_quality=1.0,
            signal_stability=1.0,
            modality_alignment=1.0
        )
        assert 0 <= result2['confidence_percent'] <= 100
    
    def test_compute_data_completeness(self):
        """Test data completeness calculation."""
        result = confidence_engine.compute_data_completeness(
            has_specimen_uploads=True,
            specimen_count=2,
            has_isf_monitor=True,
            isf_days=20,
            has_vitals=True,
            vitals_count=5,
            has_soap_profile=True,
            soap_completeness=0.8
        )
        
        assert 'completeness_score' in result
        assert 'component_scores' in result
        assert 'missing_critical' in result
        assert 0 <= result['completeness_score'] <= 1.0
    
    def test_completeness_with_missing_data(self):
        """Test completeness with missing critical data."""
        result = confidence_engine.compute_data_completeness(
            has_specimen_uploads=False,
            specimen_count=0,
            has_isf_monitor=False,
            isf_days=0,
            has_vitals=False,
            vitals_count=0,
            has_soap_profile=False,
            soap_completeness=0.0
        )
        
        assert result['completeness_score'] < 0.2
        assert len(result['missing_critical']) > 0


class TestGatingEngine:
    """Test gating engine functionality."""
    
    def test_gating_engine_singleton(self):
        """Test that gating engine is a singleton."""
        engine1 = gating_engine
        from app.services.gating import gating_engine as engine2
        assert engine1 is engine2
    
    def test_check_gate_sufficient_data(self):
        """Test gate check with sufficient data."""
        result = gating_engine.check_gate(
            output_name='a1c_estimate',
            days_of_data=35,
            signal_quality=0.85,
            has_anchor=True,
            anchor_recency_days=30
        )
        
        assert result['allowed'] is True
        assert result['recommended_range_width'] == RangeWidth.TIGHT
        assert len(result['reasons']) > 0
    
    def test_check_gate_insufficient_window(self):
        """Test gate check with insufficient data window."""
        result = gating_engine.check_gate(
            output_name='a1c_estimate',
            days_of_data=10,
            signal_quality=0.85
        )
        
        assert result['allowed'] is False
        assert result['recommended_range_width'] == RangeWidth.INSUFFICIENT
        assert any('Insufficient data' in r for r in result['reasons'])
        assert len(result['remediation']) > 0
    
    def test_check_gate_low_quality(self):
        """Test gate check with low signal quality."""
        result = gating_engine.check_gate(
            output_name='glucose_variability',
            days_of_data=20,
            signal_quality=0.40
        )
        
        assert result['allowed'] is False
        assert any('quality' in r.lower() for r in result['reasons'])
    
    def test_check_gate_wide_range_allowed(self):
        """Test gate allowing wide range but not tight."""
        result = gating_engine.check_gate(
            output_name='bp_estimate',
            days_of_data=10,
            signal_quality=0.72,
            has_anchor=False
        )
        
        assert result['allowed'] is True
        assert result['recommended_range_width'] == RangeWidth.WIDE
    
    def test_check_a1c_estimate_gate(self):
        """Test specialized A1c estimate gate."""
        result = gating_engine.check_a1c_estimate_gate(
            days_of_glucose_data=35,
            signal_quality=0.85,
            has_recent_a1c_lab=True,
            a1c_lab_days_old=45,
            glucose_cv=0.30
        )
        
        assert result['allowed'] is True
        assert 'gating_details' in result
    
    def test_check_a1c_gate_unstable_glucose(self):
        """Test A1c gate with very unstable glucose."""
        result = gating_engine.check_a1c_estimate_gate(
            days_of_glucose_data=35,
            signal_quality=0.85,
            glucose_cv=0.60  # Very high CV
        )
        
        # Should have additional check for stability
        assert 'gating_details' in result
        assert 'additional_checks' in result['gating_details']
    
    def test_check_bp_estimate_gate(self):
        """Test specialized BP estimate gate."""
        result = gating_engine.check_bp_estimate_gate(
            days_of_bp_data=10,
            signal_quality=0.75,
            has_bp_readings=True,
            bp_readings_count=5
        )
        
        assert result['allowed'] is True
        assert 'reading_count' in result['gating_details']['additional_checks']
    
    def test_check_bp_gate_insufficient_readings(self):
        """Test BP gate with too few readings."""
        result = gating_engine.check_bp_estimate_gate(
            days_of_bp_data=10,
            signal_quality=0.75,
            has_bp_readings=True,
            bp_readings_count=2
        )
        
        # Should note insufficient readings
        checks = result['gating_details']['additional_checks']
        assert 'reading_count' in checks
        assert not checks['reading_count']['passed']
    
    def test_check_lipid_trend_gate(self):
        """Test specialized lipid trend gate."""
        result = gating_engine.check_lipid_trend_gate(
            days_of_monitoring=95,
            has_lipid_panel=True,
            lipid_panel_days_old=60,
            has_dietary_data=True
        )
        
        assert result['allowed'] is True
    
    def test_get_minimum_window(self):
        """Test getting minimum data window."""
        min_days = gating_engine.get_minimum_window('a1c_estimate')
        assert min_days == 30
        
        default_days = gating_engine.get_minimum_window('unknown_output')
        assert default_days == 14  # Default fallback
    
    def test_get_quality_threshold(self):
        """Test getting quality thresholds."""
        tight_threshold = gating_engine.get_quality_threshold(RangeWidth.TIGHT)
        wide_threshold = gating_engine.get_quality_threshold(RangeWidth.WIDE)
        
        assert tight_threshold > wide_threshold
        assert tight_threshold == 0.85
        assert wide_threshold == 0.70


class TestProvenanceModel:
    """Test provenance model and helper."""
    
    def test_create_provenance_record(self, db: Session, test_user: User):
        """Test creating a provenance record."""
        confidence_payload = {
            'confidence_percent': 82.5,
            'top_3_drivers': [('Recent lab anchor', 'high'), ('Good completeness', 'medium')],
            'what_increases_confidence': ['Upload more vitals']
        }
        
        gating_payload = {
            'allowed': True,
            'recommended_range_width': 'tight',
            'reasons': ['Sufficient data window']
        }
        
        provenance = ProvenanceHelper.create_provenance_record(
            session=db,
            user_id=test_user.id,
            output_id='test_output_001',
            panel_name='metabolic',
            metric_name='a1c_estimate',
            output_type='inferred',
            input_chain='ISF glucose + lab A1c',
            raw_input_refs={'glucose_stream_id': 123, 'lab_id': 456},
            methodologies_used=['Linear calibration', 'NHANES percentiles'],
            confidence_payload=confidence_payload,
            gating_payload=gating_payload,
            output_value=5.7,
            output_units='%'
        )
        
        assert provenance is not None
        assert provenance.id is not None
        assert provenance.confidence_percent == 82.5
        assert provenance.gating_allowed == 'tight'
    
    def test_provenance_caps_methodologies(self, db: Session, test_user: User):
        """Test that methodologies are capped at 4."""
        provenance = ProvenanceHelper.create_provenance_record(
            session=db,
            user_id=test_user.id,
            output_id='test_output_002',
            panel_name='metabolic',
            metric_name='glucose_mean',
            output_type='measured',
            input_chain='ISF glucose',
            raw_input_refs={'glucose_stream_id': 123},
            methodologies_used=['Method 1', 'Method 2', 'Method 3', 'Method 4', 'Method 5'],
            confidence_payload={'confidence_percent': 90},
            gating_payload={'recommended_range_width': 'tight'}
        )
        
        assert len(provenance.methodologies_used) == 4
    
    def test_get_user_provenance_records(self, db: Session, test_user: User):
        """Test retrieving user's provenance records."""
        # Create a provenance record first
        ProvenanceHelper.create_provenance_record(
            session=db,
            user_id=test_user.id,
            output_id='test_output_003',
            panel_name='metabolic',
            metric_name='glucose_mean',
            output_type='measured',
            input_chain='ISF glucose',
            raw_input_refs={'glucose_stream_id': 123},
            methodologies_used=['Direct measurement'],
            confidence_payload={'confidence_percent': 90},
            gating_payload={'recommended_range_width': 'tight'}
        )
        db.commit()
        
        records = ProvenanceHelper.get_user_provenance_records(
            session=db,
            user_id=test_user.id
        )
        
        assert len(records) > 0
        assert all(r.user_id == test_user.id for r in records)
    
    def test_get_user_provenance_filtered_by_panel(self, db: Session, test_user: User):
        """Test retrieving provenance records filtered by panel."""
        # Create records for different panels
        ProvenanceHelper.create_provenance_record(
            session=db,
            user_id=test_user.id,
            output_id='test_output_004',
            panel_name='cardiovascular',
            metric_name='bp_estimate',
            output_type='inferred',
            input_chain='Vitals BP',
            raw_input_refs={'vitals_id': 789},
            methodologies_used=['BP monitoring'],
            confidence_payload={'confidence_percent': 75},
            gating_payload={'recommended_range_width': 'wide'}
        )
        db.commit()
        
        records = ProvenanceHelper.get_user_provenance_records(
            session=db,
            user_id=test_user.id,
            panel_name='cardiovascular'
        )
        
        assert all(r.panel_name == 'cardiovascular' for r in records)


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

@pytest.fixture(scope="function")
def test_user(db):
    """Create a test user with unique email per test."""
    import uuid
    unique_id = str(uuid.uuid4())[:8]
    user = User(
        email=f"test_a2_{unique_id}@example.com",
        name="Test A2 User",
        hashed_password="dummy_hash"
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
