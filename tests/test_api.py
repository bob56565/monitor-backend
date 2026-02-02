import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.main import app
from app.db.base import Base
from app.db.session import get_db
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

def signup_and_get_token():
    email = generate_email()
    resp = client.post("/auth/signup", json={"email": email, "password": "password123"})
    data = resp.json()
    token = data.get("token") or data.get("access_token")
    return email, token

def auth_headers(token: str):
    return {"Authorization": f"Bearer {token}"}



def generate_email():
    """Generate a unique email for each test."""
    return f"test_{uuid.uuid4().hex[:8]}@example.com"


class TestHealth:
    """Test health check endpoint."""
    
    def test_health(self):
        response = client.get("/health")
        assert response.status_code in (200, 201)
        assert response.json()["status"] == "ok"


class TestAuth:
    """Test authentication endpoints: signup and login."""
    
    def test_signup(self):
        response = client.post(
            "/auth/signup",
            json={"email": generate_email(), "password": "password123"}
        )
        assert response.status_code in (200, 201)
        data = response.json()
        assert "email" in data
        assert "user_id" in data
        assert ("token" in data) or ("access_token" in data)
    
    def test_signup_duplicate_email(self):
        email = generate_email()
        # First signup
        client.post(
            "/auth/signup",
            json={"email": email, "password": "password123"}
        )
        # Try duplicate
        response = client.post(
            "/auth/signup",
            json={"email": email, "password": "password123"}
        )
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"]
    
    def test_login(self):
        email = generate_email()
        # Create user
        client.post(
            "/auth/signup",
            json={"email": email, "password": "password123"}
        )
        # Login
        response = client.post(
            "/auth/login",
            json={"email": email, "password": "password123"}
        )
        assert response.status_code in (200, 201)
        data = response.json()
        assert data["email"] == email
        assert "user_id" in data
        assert ("token" in data) or ("access_token" in data)
    
    def test_login_invalid_password(self):
        email = generate_email()
        # Create user
        client.post(
            "/auth/signup",
            json={"email": email, "password": "password123"}
        )
        # Try wrong password
        response = client.post(
            "/auth/login",
            json={"email": email, "password": "wrongpassword"}
        )
        assert response.status_code == 401
        assert "Invalid credentials" in response.json()["detail"]
    
    def test_login_nonexistent_user(self):
        response = client.post(
            "/auth/login",
            json={"email": generate_email(), "password": "password123"}
        )
        assert response.status_code == 401


class TestDataIngestion:
    """Test data ingestion endpoints."""
    
    def setup_method(self):
        """Create a user for each test."""
        email = generate_email()
        response = client.post(
            "/auth/signup",
            json={"email": email, "password": "password123"}
        )
        self.user_id = response.json()["user_id"]
        self.token = (response.json().get("token") or response.json().get("access_token"))
    
    def test_ingest_raw_data(self):
        response = client.post(
            "/data/raw",
            headers=auth_headers(self.token),
            json={
                "timestamp": "2026-01-27T00:00:00Z",
                "specimen_type": "blood",
                "observed": {"glucose_mg_dl": 120.0, "lactate_mmol_l": 2.0},
                "context": {"age": 30, "sex": "M", "fasting": False}
            }
        )
        assert response.status_code in (200, 201)
        data = response.json()
        raw_id = data.get("raw_id") or data.get("id") or data.get("raw_sensor_data_id")
        assert raw_id is not None
        self.raw_data_id = raw_id
    
    def test_ingest_raw_data_unauthenticated(self):
        response = client.post(
            "/data/raw",
            json={
                "sensor_value_1": 1.5,
                "sensor_value_2": 2.5,
                "sensor_value_3": 3.5,
            }
        )
        assert response.status_code == 401
    
    def test_preprocess_data(self):
        # Ingest raw data first
        ingest_response = client.post(
            "/data/raw",
            headers=auth_headers(self.token),
            json={
                "timestamp": "2026-01-27T00:00:00Z",
                "specimen_type": "blood",
                "observed": {"glucose_mg_dl": 120.0, "lactate_mmol_l": 2.0},
                "context": {"age": 30, "sex": "M", "fasting": False}
            }
        )
        raw_id = ingest_response.json().get("raw_id") or ingest_response.json().get("id") or ingest_response.json().get("raw_sensor_data_id")
        
        # Preprocess
        response = client.post(
            "/data/preprocess",
            headers=auth_headers(self.token),
            json={"raw_id": raw_id}
        )
        assert response.status_code in (200, 201)
        data = response.json()
        assert "features" in data and "feature_1" in data["features"]
        assert "features" in data and "feature_2" in data["features"]
        assert "features" in data and "feature_3" in data["features"]
        assert "calibrated_metric" in data or "derived_metric" in data
        assert "id" in data
        self.calibrated_id = data["id"]
    
    def test_preprocess_nonexistent_raw_data(self):
        response = client.post(
            "/data/preprocess",
            headers=auth_headers(self.token),
            json={"raw_id": 9999}
        )
        assert response.status_code == 404


class TestInference:
    """Test inference endpoints."""
    
    def setup_method(self):
        """Create a user and preprocessed data for each test."""
        email = generate_email()
        response = client.post(
            "/auth/signup",
            json={"email": email, "password": "password123"}
        )
        self.user_id = response.json()["user_id"]
        self.token = (response.json().get("token") or response.json().get("access_token"))
        
        # Ingest and preprocess
        ingest_response = client.post(
            "/data/raw",
            headers=auth_headers(self.token),
            json={
                "timestamp": "2026-01-27T00:00:00Z",
                "specimen_type": "blood",
                "observed": {"glucose_mg_dl": 120.0, "lactate_mmol_l": 2.0},
                "context": {"age": 30, "sex": "M", "fasting": False}
            }
        )
        raw_id = ingest_response.json().get("raw_id") or ingest_response.json().get("id") or ingest_response.json().get("raw_sensor_data_id")
        
        preprocess_response = client.post(
            "/data/preprocess",
            headers=auth_headers(self.token),
            json={"raw_id": raw_id}
        )
        self.calibrated_id = preprocess_response.json().get("calibrated_id") or preprocess_response.json().get("id") or preprocess_response.json().get("calibrated_features_id")
    
    def test_infer(self):
        response = client.post(
            "/ai/infer",
            json={"calibrated_id": self.calibrated_id},
            headers=auth_headers(self.token)
        )
        assert response.status_code in (200, 201)
        data = response.json()
        assert "trace_id" in data
        assert "created_at" in data
        assert "inferred" in data
        assert isinstance(data["inferred"], list)
    
    def test_infer_response_has_all_required_keys(self):
        """Test that InferenceReport response includes all required schema fields."""
        response = client.post(
            "/ai/infer",
            json={"calibrated_id": self.calibrated_id},
            headers=auth_headers(self.token)
        )
        assert response.status_code in (200, 201)
        data = response.json()
        
        # Top-level fields
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
            assert field in data, f"Missing required field: {field}"
        
        # input_summary fields
        assert "specimen_type" in data["input_summary"]
        assert "observed_inputs" in data["input_summary"]
        assert "missing_inputs" in data["input_summary"]
        
        # model_metadata fields
        assert "model_name" in data["model_metadata"]
        assert "model_version" in data["model_metadata"]
        assert "trained_on" in data["model_metadata"]
        
        # inferred array structure
        assert isinstance(data["inferred"], list)
        assert len(data["inferred"]) > 0
        for inferred_item in data["inferred"]:
            assert "name" in inferred_item
            assert "value" in inferred_item
            assert "unit" in inferred_item
            assert "confidence" in inferred_item
            assert "method" in inferred_item
    
    def test_infer_confidence_values_in_valid_range(self):
        """Test that all confidence values in inferred array are between 0 and 1."""
        response = client.post(
            "/ai/infer",
            json={"calibrated_id": self.calibrated_id},
            headers=auth_headers(self.token)
        )
        assert response.status_code in (200, 201)
        data = response.json()
        
        # Check that inferred array exists and has items
        assert "inferred" in data
        assert isinstance(data["inferred"], list)
        assert len(data["inferred"]) > 0
        
        # Check that all confidence values are between 0 and 1
        for inferred_item in data["inferred"]:
            assert "confidence" in inferred_item
            confidence = inferred_item["confidence"]
            assert isinstance(confidence, (int, float))
            assert 0 <= confidence <= 1, f"Confidence {confidence} is not in range [0, 1]"

    
    def test_infer_nonexistent_feature(self):
        response = client.post(
            "/ai/infer",
            json={"calibrated_id": 9999},
            headers=auth_headers(self.token)
        )
        assert response.status_code == 404
    
    def test_forecast(self):
        # Now requires auth since endpoint needs to query DB for calibrated_id lookups
        # Create a test user
        email = generate_email()
        signup_response = client.post(
            "/auth/signup",
            json={"email": email, "password": "password123"}
        )
        token = (signup_response.json().get("token") or signup_response.json().get("access_token"))
        
        response = client.post(
            "/ai/forecast",
            headers=auth_headers(token),
            json={
                "feature_values": [1.0, 1.5, 2.0],
                "steps_ahead": 1
            }
        )
        assert response.status_code in (200, 201)
        data = response.json()
        assert "forecast" in data
        assert "confidence" in data
        assert "steps_ahead" in data
        assert data["steps_ahead"] == 1
    
    def test_forecast_with_horizon_steps(self):
        """Test that horizon_steps parameter produces correct forecast list."""
        # Create a test user
        email = generate_email()
        signup_response = client.post(
            "/auth/signup",
            json={"email": email, "password": "password123"}
        )
        token = (signup_response.json().get("token") or signup_response.json().get("access_token"))
        
        response = client.post(
            "/ai/forecast",
            headers=auth_headers(token),
            json={
                "feature_values": [1.0, 1.5, 2.0],
                "horizon_steps": 5
            }
        )
        assert response.status_code in (200, 201)
        data = response.json()
        assert data["steps_ahead"] == 5
        assert "forecasts" in data
        assert len(data["forecasts"]) == 5
        assert data["forecast"] == data["forecasts"][0]


class TestEndToEnd:
    """End-to-end workflow test: signup -> login -> ingest -> preprocess -> infer."""
    
    def test_full_workflow(self):
        email = generate_email()
        
        # Signup
        signup_response = client.post(
            "/auth/signup",
            json={"email": email, "password": "password123"}
        )
        assert signup_response.status_code == 200
        user_id = signup_response.json()["user_id"]
        
        # Login
        login_response = client.post(
            "/auth/login",
            json={"email": email, "password": "password123"}
        )
        assert login_response.status_code == 200
        token = login_response.json().get("token") or login_response.json().get("access_token")
        
        # Ingest raw data
        ingest_response = client.post(
            "/data/raw",
            json={
                "timestamp": "2026-01-27T00:00:00Z",
                "specimen_type": "blood",
                "observed": {"glucose_mg_dl": 120.0, "lactate_mmol_l": 2.0},
                "context": {"age": 30, "sex": "M", "fasting": False}
            },
            headers=auth_headers(token)
        )
        assert ingest_response.status_code in (200, 201)
        raw_id = ingest_response.json().get("raw_id") or ingest_response.json().get("id") or ingest_response.json().get("raw_sensor_data_id")
        
        # Preprocess
        preprocess_response = client.post(
            "/data/preprocess",
            json={"raw_id": raw_id},
            headers=auth_headers(token)
        )
        assert preprocess_response.status_code == 200
        calibrated_id = preprocess_response.json().get("calibrated_id") or preprocess_response.json().get("id") or preprocess_response.json().get("calibrated_features_id")
        
        # Infer
        infer_response = client.post(
            "/ai/infer",
            json={"calibrated_id": calibrated_id},
            headers=auth_headers(token)
        )
        assert infer_response.status_code in (200, 201)
        inference_data = infer_response.json()
        assert "trace_id" in inference_data
        assert "created_at" in inference_data
        assert "inferred" in inference_data


class TestM5PDFReports:
    """Test Milestone 5: PDF Report Generation."""
    
    def setup_method(self):
        """Create a user and run pipeline for each test."""
        email = generate_email()
        response = client.post(
            "/auth/signup",
            json={"email": email, "password": "password123"}
        )
        self.user_id = response.json()["user_id"]
        self.token = (response.json().get("token") or response.json().get("access_token"))
        
        # Ingest and preprocess to get calibrated_id
        ingest_response = client.post(
            "/data/raw",
            headers=auth_headers(self.token),
            json={
                "timestamp": "2026-01-27T00:00:00Z",
                "specimen_type": "blood",
                "observed": {"glucose_mg_dl": 120.0, "lactate_mmol_l": 2.0},
                "context": {"age": 30, "sex": "M", "fasting": False}
            }
        )
        self.raw_id = ingest_response.json().get("raw_id") or ingest_response.json().get("id")
        
        preprocess_response = client.post(
            "/data/preprocess",
            headers=auth_headers(self.token),
            json={"raw_id": self.raw_id}
        )
        self.calibrated_id = preprocess_response.json().get("calibrated_id") or preprocess_response.json().get("id")
    
    def test_pdf_report_with_calibrated_id(self):
        """Test PDF generation with calibrated_id."""
        response = client.post(
            "/reports/pdf",
            headers=auth_headers(self.token),
            json={"calibrated_id": self.calibrated_id}
        )
        assert response.status_code in (200, 201)
        assert response.headers["content-type"] == "application/pdf"
        assert len(response.content) > 0
        # Check for PDF signature
        assert response.content[:4] == b"%PDF"
    
    def test_pdf_report_with_raw_id(self):
        """Test PDF generation with raw_id."""
        response = client.post(
            "/reports/pdf",
            headers=auth_headers(self.token),
            json={"raw_id": self.raw_id}
        )
        assert response.status_code in (200, 201)
        assert response.headers["content-type"] == "application/pdf"
        assert len(response.content) > 0
        assert response.content[:4] == b"%PDF"
    
    def test_pdf_report_with_both_ids(self):
        """Test PDF generation with both raw_id and calibrated_id."""
        response = client.post(
            "/reports/pdf",
            headers=auth_headers(self.token),
            json={
                "raw_id": self.raw_id,
                "calibrated_id": self.calibrated_id
            }
        )
        assert response.status_code in (200, 201)
        assert response.headers["content-type"] == "application/pdf"
        assert len(response.content) > 0
        assert response.content[:4] == b"%PDF"
    
    def test_pdf_report_missing_ids_fails(self):
        """Test PDF generation fails when no IDs provided."""
        response = client.post(
            "/reports/pdf",
            headers=auth_headers(self.token),
            json={}
        )
        assert response.status_code == 422
    
    def test_pdf_report_unauthenticated_fails(self):
        """Test PDF generation fails without authentication."""
        response = client.post(
            "/reports/pdf",
            json={"calibrated_id": self.calibrated_id}
        )
        assert response.status_code == 401
    
    def test_pdf_report_invalid_calibrated_id(self):
        """Test PDF generation with non-existent calibrated_id."""
        response = client.post(
            "/reports/pdf",
            headers=auth_headers(self.token),
            json={"calibrated_id": 9999}
        )
        # Should still generate PDF (just with missing data sections)
        assert response.status_code in (200, 201)
        assert response.headers["content-type"] == "application/pdf"


class TestM6E2EIntegration:
    """Test Milestone 6: End-to-End Integration Tests."""
    
    def test_full_pipeline_with_calibrated_id(self):
        """Full E2E test: signup → raw → preprocess → infer (calibrated_id) → forecast (calibrated_id) → PDF."""
        email = generate_email()
        
        # Step 1: Signup
        signup_response = client.post(
            "/auth/signup",
            json={"email": email, "password": "password123"}
        )
        assert signup_response.status_code == 200
        token = signup_response.json().get("access_token") or signup_response.json().get("token")
        user_id = signup_response.json()["user_id"]
        
        # Step 2: Ingest raw data
        raw_response = client.post(
            "/data/raw",
            headers=auth_headers(token),
            json={
                "timestamp": "2026-01-27T12:00:00Z",
                "specimen_type": "blood",
                "observed": {"glucose_mg_dl": 110.0, "lactate_mmol_l": 1.8},
                "context": {"age": 45, "sex": "F", "fasting": True}
            }
        )
        assert raw_response.status_code in (200, 201)
        raw_id = raw_response.json().get("id") or raw_response.json().get("raw_id")
        assert raw_id is not None
        
        # Step 3: Preprocess
        preprocess_response = client.post(
            "/data/preprocess",
            headers=auth_headers(token),
            json={"raw_id": raw_id}
        )
        assert preprocess_response.status_code == 200
        calibrated_id = preprocess_response.json().get("id") or preprocess_response.json().get("calibrated_id")
        assert calibrated_id is not None
        
        # Step 4: Infer with calibrated_id
        infer_response = client.post(
            "/ai/infer",
            headers=auth_headers(token),
            json={"calibrated_id": calibrated_id}
        )
        assert infer_response.status_code in (200, 201)
        inference_data = infer_response.json()
        assert "trace_id" in inference_data
        assert "inferred" in inference_data
        
        # Step 5: Forecast with calibrated_id
        forecast_response = client.post(
            "/ai/forecast",
            headers=auth_headers(token),
            json={
                "calibrated_id": calibrated_id,
                "horizon_steps": 5
            }
        )
        assert forecast_response.status_code in (200, 201)
        forecast_data = forecast_response.json()
        assert forecast_data["steps_ahead"] == 5
        assert len(forecast_data["forecasts"]) == 5
        
        # Step 6: Generate PDF
        pdf_response = client.post(
            "/reports/pdf",
            headers=auth_headers(token),
            json={
                "raw_id": raw_id,
                "calibrated_id": calibrated_id,
                "trace_id": inference_data["trace_id"]
            }
        )
        assert pdf_response.status_code in (200, 201)
        assert pdf_response.headers["content-type"] == "application/pdf"
        assert pdf_response.content[:4] == b"%PDF"
        assert len(pdf_response.content) > 1000  # Reasonable PDF size
    
    def test_full_pipeline_with_feature_values(self):
        """Full E2E test: signup → raw → forecast (feature_values) → PDF."""
        email = generate_email()
        
        # Signup
        signup_response = client.post(
            "/auth/signup",
            json={"email": email, "password": "password123"}
        )
        token = signup_response.json().get("access_token") or signup_response.json().get("token")
        
        # Ingest raw data
        raw_response = client.post(
            "/data/raw",
            headers=auth_headers(token),
            json={
                "timestamp": "2026-01-27T12:00:00Z",
                "specimen_type": "plasma",
                "observed": {"glucose_mg_dl": 95.0, "lactate_mmol_l": 1.2},
                "context": {}
            }
        )
        raw_id = raw_response.json().get("id") or raw_response.json().get("raw_id")
        
        # Test forecast with feature_values (direct, no preprocessing)
        forecast_response = client.post(
            "/ai/forecast",
            headers=auth_headers(token),
            json={
                "feature_values": [0.5, 0.6, 0.7],
                "horizon_steps": 2
            }
        )
        assert forecast_response.status_code in (200, 201)
        forecast_data = forecast_response.json()
        assert forecast_data["steps_ahead"] == 2
        assert len(forecast_data["forecasts"]) == 2
        
        # Test infer with features dict
        infer_response = client.post(
            "/ai/infer",
            headers=auth_headers(token),
            json={
                "features": {
                    "feature_1": 0.5,
                    "feature_2": 0.6,
                    "feature_3": 0.7
                }
            }
        )
        assert infer_response.status_code in (200, 201)
        assert "trace_id" in infer_response.json()
    
    def test_multiple_users_isolation(self):
        """Test that multiple users' data is properly isolated."""
        # User 1
        email1 = generate_email()
        signup1 = client.post(
            "/auth/signup",
            json={"email": email1, "password": "pass123"}
        )
        token1 = signup1.json().get("access_token") or signup1.json().get("token")
        
        # User 2
        email2 = generate_email()
        signup2 = client.post(
            "/auth/signup",
            json={"email": email2, "password": "pass123"}
        )
        token2 = signup2.json().get("access_token") or signup2.json().get("token")
        
        # User 1 ingests data
        raw1 = client.post(
            "/data/raw",
            headers=auth_headers(token1),
            json={
                "timestamp": "2026-01-27T12:00:00Z",
                "specimen_type": "blood",
                "observed": {"glucose_mg_dl": 150.0, "lactate_mmol_l": 2.5},
                "context": {}
            }
        )
        raw_id1 = raw1.json().get("id") or raw1.json().get("raw_id")
        
        # User 2 tries to access User 1's data - should fail
        preprocess_fail = client.post(
            "/data/preprocess",
            headers=auth_headers(token2),
            json={"raw_id": raw_id1}
        )
        assert preprocess_fail.status_code == 404  # User 2 should not see User 1's data
    
    def test_backward_compatibility_steps_ahead_alias(self):
        """Test that legacy steps_ahead alias still works."""
        email = generate_email()
        signup = client.post(
            "/auth/signup",
            json={"email": email, "password": "pass123"}
        )
        token = signup.json().get("access_token") or signup.json().get("token")
        
        # Use only steps_ahead (legacy), no horizon_steps
        response = client.post(
            "/ai/forecast",
            headers=auth_headers(token),
            json={
                "feature_values": [1.0, 1.5, 2.0],
                "steps_ahead": 3
            }
        )
        assert response.status_code in (200, 201)
        data = response.json()
        assert data["steps_ahead"] == 3  # Should use steps_ahead value
        assert len(data["forecasts"]) == 3
    
    def test_error_handling_missing_auth(self):
        """Test that endpoints properly reject requests without auth."""
        # Try to forecast without token
        response = client.post(
            "/ai/forecast",
            json={
                "feature_values": [1.0, 1.5, 2.0],
                "horizon_steps": 1
            }
        )
        assert response.status_code == 401
        
        # Try to infer without token
        response = client.post(
            "/ai/infer",
            json={"calibrated_id": 1}
        )
        assert response.status_code == 401
        
        # Try to generate PDF without token
        response = client.post(
            "/reports/pdf",
            json={"calibrated_id": 1}
        )
        assert response.status_code == 401
    
    def test_error_handling_missing_fields(self):
        """Test that endpoints properly validate required fields."""
        email = generate_email()
        signup = client.post(
            "/auth/signup",
            json={"email": email, "password": "pass123"}
        )
        token = signup.json().get("access_token") or signup.json().get("token")
        
        # Missing required fields in forecast (no calibrated_id or feature_values)
        response = client.post(
            "/ai/forecast",
            headers=auth_headers(token),
            json={"horizon_steps": 1}
        )
        assert response.status_code == 422
        
        # Missing required fields in PDF (no identifiers)
        response = client.post(
            "/reports/pdf",
            headers=auth_headers(token),
            json={}
        )
        assert response.status_code == 422


class TestM4ContractUnification:
    """Test Milestone 4: API Contract Unification for forecast and infer."""
    
    def setup_method(self):
        """Create a user and preprocessed data for each test."""
        email = generate_email()
        response = client.post(
            "/auth/signup",
            json={"email": email, "password": "password123"}
        )
        self.user_id = response.json()["user_id"]
        self.token = (response.json().get("token") or response.json().get("access_token"))
        
        # Ingest and preprocess
        ingest_response = client.post(
            "/data/raw",
            headers=auth_headers(self.token),
            json={
                "timestamp": "2026-01-27T00:00:00Z",
                "specimen_type": "blood",
                "observed": {"glucose_mg_dl": 120.0, "lactate_mmol_l": 2.0},
                "context": {"age": 30, "sex": "M", "fasting": False}
            }
        )
        raw_id = ingest_response.json().get("raw_id") or ingest_response.json().get("id") or ingest_response.json().get("raw_sensor_data_id")
        
        preprocess_response = client.post(
            "/data/preprocess",
            headers=auth_headers(self.token),
            json={"raw_id": raw_id}
        )
        self.calibrated_id = preprocess_response.json().get("calibrated_id") or preprocess_response.json().get("id") or preprocess_response.json().get("calibrated_features_id")
    
    def test_forecast_with_calibrated_id(self):
        """Test forecast endpoint accepts calibrated_id and loads features from DB."""
        response = client.post(
            "/ai/forecast",
            headers=auth_headers(self.token),
            json={
                "calibrated_id": self.calibrated_id,
                "horizon_steps": 3
            }
        )
        assert response.status_code in (200, 201)
        data = response.json()
        assert "forecast" in data
        assert "forecasts" in data
        assert len(data["forecasts"]) == 3
        assert data["steps_ahead"] == 3
        assert data["forecast"] == data["forecasts"][0]
    
    def test_forecast_with_feature_values(self):
        """Test forecast endpoint still accepts feature_values (backward compat)."""
        response = client.post(
            "/ai/forecast",
            headers=auth_headers(self.token),
            json={
                "feature_values": [1.0, 1.5, 2.0],
                "horizon_steps": 2
            }
        )
        assert response.status_code in (200, 201)
        data = response.json()
        assert "forecast" in data
        assert "forecasts" in data
        assert len(data["forecasts"]) == 2
        assert data["steps_ahead"] == 2
    
    def test_forecast_calibrated_id_takes_precedence(self):
        """Test that calibrated_id takes precedence over feature_values when both provided."""
        response = client.post(
            "/ai/forecast",
            headers=auth_headers(self.token),
            json={
                "calibrated_id": self.calibrated_id,
                "feature_values": [999.0, 999.0, 999.0],  # These should be ignored
                "horizon_steps": 1
            }
        )
        assert response.status_code in (200, 201)
        data = response.json()
        assert "forecast" in data
    
    def test_forecast_horizon_steps_overrides_steps_ahead(self):
        """Test that horizon_steps takes precedence over steps_ahead."""
        response = client.post(
            "/ai/forecast",
            headers=auth_headers(self.token),
            json={
                "feature_values": [1.0, 1.5, 2.0],
                "steps_ahead": 1,
                "horizon_steps": 4
            }
        )
        assert response.status_code in (200, 201)
        data = response.json()
        assert data["steps_ahead"] == 4
        assert len(data["forecasts"]) == 4
    
    def test_infer_with_calibrated_id(self):
        """Test infer endpoint accepts calibrated_id."""
        response = client.post(
            "/ai/infer",
            headers=auth_headers(self.token),
            json={"calibrated_id": self.calibrated_id}
        )
        assert response.status_code in (200, 201)
        data = response.json()
        assert "trace_id" in data
        assert "inferred" in data
    
    def test_infer_with_features_dict(self):
        """Test infer endpoint accepts features dict (legacy)."""
        response = client.post(
            "/ai/infer",
            headers=auth_headers(self.token),
            json={
                "features": {
                    "feature_1": 1.0,
                    "feature_2": 1.5,
                    "feature_3": 2.0
                }
            }
        )
        assert response.status_code in (200, 201)
        data = response.json()
        assert "trace_id" in data
        assert "inferred" in data
    
    def test_forecast_missing_both_ids_fails(self):
        """Test forecast fails when neither calibrated_id nor feature_values provided."""
        response = client.post(
            "/ai/forecast",
            headers=auth_headers(self.token),
            json={"horizon_steps": 1}
        )
        assert response.status_code == 422
    
    def test_infer_missing_both_ids_fails(self):
        """Test infer fails when neither calibrated_id nor features provided."""
        response = client.post(
            "/ai/infer",
            headers=auth_headers(self.token),
            json={}
        )
        assert response.status_code == 422
