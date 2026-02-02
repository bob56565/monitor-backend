"""
Tests for the InferenceReport schema contract.
These tests verify the /ai/infer endpoint returns the stable, product-ready schema.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.main import app
from app.db.base import Base
from app.db.session import get_db
from app.models import User, CalibratedFeatures
from app.api.security import get_password_hash, create_access_token
import uuid

# Create in-memory SQLite database for tests
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture
def setup_user_with_calibrated_features():
    """Set up a user with calibrated features for inference testing."""
    db = TestingSessionLocal()
    
    # Create a test user
    user = User(
        email=f"test_{uuid.uuid4().hex[:8]}@example.com",
        hashed_password=get_password_hash("password123"),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Create calibrated features
    cal_features = CalibratedFeatures(
        user_id=user.id,
        feature_1=-0.816,
        feature_2=0.0,
        feature_3=0.816,
        derived_metric=0.178,
    )
    db.add(cal_features)
    db.commit()
    db.refresh(cal_features)
    
    # Create a valid token for the user
    token = create_access_token(data={"sub": str(user.id)})
    
    db.close()
    
    return {
        "user_id": user.id,
        "calibrated_id": cal_features.id,
        "token": token,
    }


class TestInferenceReportSchema:
    """Test the new InferenceReport contract."""
    
    def test_infer_returns_201_status(self, setup_user_with_calibrated_features):
        """Test that /ai/infer returns 201 Created status."""
        setup = setup_user_with_calibrated_features
        
        response = client.post(
            "/ai/infer",
            json={"calibrated_id": setup["calibrated_id"]},
            headers={"Authorization": f"Bearer {setup['token']}"}
        )
        
        assert response.status_code == 201
    
    def test_infer_response_has_all_required_top_level_keys(self, setup_user_with_calibrated_features):
        """Test that InferenceReport response includes all required top-level fields."""
        setup = setup_user_with_calibrated_features
        
        response = client.post(
            "/ai/infer",
            json={"calibrated_id": setup["calibrated_id"]},
            headers={"Authorization": f"Bearer {setup['token']}"}
        )
        
        assert response.status_code == 201
        data = response.json()
        
        # Top-level fields must all be present
        required_top_level = [
            "trace_id",
            "created_at",
            "input_summary",
            "inferred",
            "abnormal_flags",
            "assumptions",
            "limitations",
            "model_metadata",
            "disclaimer",
        ]
        
        for field in required_top_level:
            assert field in data, f"Missing required top-level field: {field}"
        
        # Verify types
        assert isinstance(data["trace_id"], str)
        assert isinstance(data["created_at"], str)
        assert isinstance(data["input_summary"], dict)
        assert isinstance(data["inferred"], list)
        assert isinstance(data["abnormal_flags"], list)
        assert isinstance(data["assumptions"], list)
        assert isinstance(data["limitations"], list)
        assert isinstance(data["model_metadata"], dict)
        assert isinstance(data["disclaimer"], str)
    
    def test_infer_input_summary_structure(self, setup_user_with_calibrated_features):
        """Test that input_summary contains required nested fields."""
        setup = setup_user_with_calibrated_features
        
        response = client.post(
            "/ai/infer",
            json={"calibrated_id": setup["calibrated_id"]},
            headers={"Authorization": f"Bearer {setup['token']}"}
        )
        
        assert response.status_code == 201
        data = response.json()
        input_summary = data["input_summary"]
        
        # Verify input_summary fields
        assert "specimen_type" in input_summary
        assert "observed_inputs" in input_summary
        assert "missing_inputs" in input_summary
        
        assert isinstance(input_summary["specimen_type"], str)
        assert isinstance(input_summary["observed_inputs"], list)
        assert isinstance(input_summary["missing_inputs"], list)
    
    def test_infer_model_metadata_structure(self, setup_user_with_calibrated_features):
        """Test that model_metadata contains required nested fields."""
        setup = setup_user_with_calibrated_features
        
        response = client.post(
            "/ai/infer",
            json={"calibrated_id": setup["calibrated_id"]},
            headers={"Authorization": f"Bearer {setup['token']}"}
        )
        
        assert response.status_code == 201
        data = response.json()
        model_metadata = data["model_metadata"]
        
        # Verify model_metadata fields
        assert "model_name" in model_metadata
        assert "model_version" in model_metadata
        assert "trained_on" in model_metadata
        
        assert isinstance(model_metadata["model_name"], str)
        assert isinstance(model_metadata["model_version"], str)
        assert isinstance(model_metadata["trained_on"], str)
    
    def test_infer_inferred_array_structure(self, setup_user_with_calibrated_features):
        """Test that inferred array contains properly structured objects."""
        setup = setup_user_with_calibrated_features
        
        response = client.post(
            "/ai/infer",
            json={"calibrated_id": setup["calibrated_id"]},
            headers={"Authorization": f"Bearer {setup['token']}"}
        )
        
        assert response.status_code == 201
        data = response.json()
        inferred = data["inferred"]
        
        # Must have at least one inferred value
        assert len(inferred) > 0, "inferred array must contain at least one value"
        
        # Each inferred item must have required fields
        for inferred_item in inferred:
            assert "name" in inferred_item
            assert "value" in inferred_item
            assert "unit" in inferred_item
            assert "confidence" in inferred_item
            assert "method" in inferred_item
            
            # Verify types
            assert isinstance(inferred_item["name"], str)
            assert isinstance(inferred_item["value"], (int, float))
            assert isinstance(inferred_item["unit"], str)
            assert isinstance(inferred_item["confidence"], (int, float))
            assert isinstance(inferred_item["method"], str)
    
    def test_infer_confidence_values_in_valid_range(self, setup_user_with_calibrated_features):
        """Test that ALL confidence values are between 0 and 1 (this is the main assertion for test 2)."""
        setup = setup_user_with_calibrated_features
        
        response = client.post(
            "/ai/infer",
            json={"calibrated_id": setup["calibrated_id"]},
            headers={"Authorization": f"Bearer {setup['token']}"}
        )
        
        assert response.status_code == 201
        data = response.json()
        inferred = data["inferred"]
        
        # This is the critical test: validate all confidence values
        assert len(inferred) > 0, "inferred array must not be empty"
        
        for inferred_item in inferred:
            confidence = inferred_item["confidence"]
            assert isinstance(confidence, (int, float)), f"Confidence must be numeric, got {type(confidence)}"
            assert 0 <= confidence <= 1, f"Confidence {confidence} is not in range [0, 1]"
    
    def test_infer_nonexistent_calibrated_id_returns_404(self, setup_user_with_calibrated_features):
        """Test that requesting non-existent calibrated feature returns 404."""
        setup = setup_user_with_calibrated_features
        
        response = client.post(
            "/ai/infer",
            json={"calibrated_id": 99999},
            headers={"Authorization": f"Bearer {setup['token']}"}
        )
        
        assert response.status_code == 404
    
    def test_infer_without_auth_returns_401(self, setup_user_with_calibrated_features):
        """Test that /ai/infer requires authentication."""
        setup = setup_user_with_calibrated_features
        
        response = client.post(
            "/ai/infer",
            json={"calibrated_id": setup["calibrated_id"]}
        )
        
        assert response.status_code == 401
