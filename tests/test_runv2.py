"""
Tests for Milestone 7 Phase 3 Part 1: RunV2 Multi-Specimen Ingestion.
Non-breaking enhancement tests.
"""

import pytest
import uuid
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.base import Base
from app.db.session import get_db
from app.models.run_v2 import (
    SpecimenRecord, RunV2CreateRequest, NonLabInputs, SpecimenTypeEnum,
    MissingnessRecord, ProvenanceEnum, MissingTypeEnum, MissingImpactEnum,
    DemographicsInputs, AnthropometricsInputs, VitalsPhysiologyInputs,
)

# In-memory SQLite for tests
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


def generate_email():
    return f"test_{uuid.uuid4().hex[:8]}@example.com"


def signup_and_get_token():
    email = generate_email()
    resp = client.post("/auth/signup", json={"email": email, "password": "pass123"})
    data = resp.json()
    token = data.get("token") or data.get("access_token")
    return email, token


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


class TestRunV2Creation:
    """Test POST /runs/v2 endpoint."""

    def test_create_runv2_single_specimen(self):
        """Create a RunV2 with a single ISF specimen."""
        email, token = signup_and_get_token()
        
        # Build request
        specimen = SpecimenRecord(
            specimen_id=str(uuid.uuid4()),
            specimen_type=SpecimenTypeEnum.ISF,
            collected_at=datetime.utcnow(),
            source_detail="fingerstick",
            raw_values={
                "glucose": 120.5,
                "lactate": 1.8,
            },
            units={
                "glucose": "mg/dL",
                "lactate": "mmol/L",
            },
            missingness={
                "glucose": MissingnessRecord(
                    is_missing=False,
                    missing_type=None,
                    missing_impact=MissingImpactEnum.NEUTRAL,
                    provenance=ProvenanceEnum.MEASURED,
                    confidence_0_1=1.0,
                ),
                "lactate": MissingnessRecord(
                    is_missing=False,
                    missing_type=None,
                    missing_impact=MissingImpactEnum.NEUTRAL,
                    provenance=ProvenanceEnum.MEASURED,
                    confidence_0_1=1.0,
                ),
            },
        )
        
        request_data = RunV2CreateRequest(
            timezone="UTC",
            specimens=[specimen],
            non_lab_inputs=NonLabInputs(
                demographics=DemographicsInputs(age=40, sex_at_birth="male"),
            ),
        )
        
        response = client.post(
            "/runs/v2",
            json=request_data.model_dump(mode="json"),
            headers=auth_headers(token),
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["run_id"]
        assert data["specimen_count"] == 1
        assert data["schema_version"] == "runv2.1"
        assert len(data["specimens"]) == 1

    def test_create_runv2_multiple_specimens(self):
        """Create a RunV2 with multiple specimens (ISF + Blood)."""
        email, token = signup_and_get_token()
        
        # ISF specimen
        specimen1 = SpecimenRecord(
            specimen_id=str(uuid.uuid4()),
            specimen_type=SpecimenTypeEnum.ISF,
            collected_at=datetime.utcnow(),
            source_detail="microfluidic",
            raw_values={"glucose": 115.0, "lactate": 1.7},
            units={"glucose": "mg/dL", "lactate": "mmol/L"},
            missingness={
                "glucose": MissingnessRecord(
                    is_missing=False,
                    missing_type=None,
                    missing_impact=MissingImpactEnum.NEUTRAL,
                    provenance=ProvenanceEnum.MEASURED,
                ),
                "lactate": MissingnessRecord(
                    is_missing=False,
                    missing_type=None,
                    missing_impact=MissingImpactEnum.NEUTRAL,
                    provenance=ProvenanceEnum.MEASURED,
                ),
            },
        )
        
        # Blood specimen
        specimen2 = SpecimenRecord(
            specimen_id=str(uuid.uuid4()),
            specimen_type=SpecimenTypeEnum.BLOOD_VENOUS,
            collected_at=datetime.utcnow(),
            source_detail="venipuncture",
            raw_values={
                "glucose": 118.0,
                "hgb": 14.5,
                "wbc": 7.2,
            },
            units={
                "glucose": "mg/dL",
                "hgb": "g/dL",
                "wbc": "10^3/uL",
            },
            missingness={
                "glucose": MissingnessRecord(
                    is_missing=False, missing_impact=MissingImpactEnum.NEUTRAL,
                    provenance=ProvenanceEnum.MEASURED,
                ),
                "hgb": MissingnessRecord(
                    is_missing=False, missing_impact=MissingImpactEnum.NEUTRAL,
                    provenance=ProvenanceEnum.MEASURED,
                ),
                "wbc": MissingnessRecord(
                    is_missing=False, missing_impact=MissingImpactEnum.NEUTRAL,
                    provenance=ProvenanceEnum.MEASURED,
                ),
            },
        )
        
        request_data = RunV2CreateRequest(
            timezone="America/New_York",
            specimens=[specimen1, specimen2],
            non_lab_inputs=NonLabInputs(
                demographics=DemographicsInputs(age=35, sex_at_birth="female"),
                vitals_physiology=VitalsPhysiologyInputs(heart_rate=72, bp_systolic=120),
            ),
        )
        
        response = client.post(
            "/runs/v2",
            json=request_data.model_dump(mode="json"),
            headers=auth_headers(token),
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["specimen_count"] == 2
        assert len(data["specimens"]) == 2
        assert any(s["specimen_type"] == "ISF" for s in data["specimens"])
        assert any(s["specimen_type"] == "BLOOD_VENOUS" for s in data["specimens"])

    def test_create_runv2_validation_missing_specimens(self):
        """Validate that RunV2 requires at least one specimen."""
        email, token = signup_and_get_token()
        
        request_data = {
            "timezone": "UTC",
            "specimens": [],
            "non_lab_inputs": {},
        }
        
        response = client.post(
            "/runs/v2",
            json=request_data,
            headers=auth_headers(token),
        )
        
        assert response.status_code == 422
        data = response.json()
        assert "At least one specimen is required" in str(data)

    def test_create_runv2_validation_missing_missingness(self):
        """Validate that each specimen must have missingness records."""
        email, token = signup_and_get_token()
        
        # Specimen without missingness
        specimen = {
            "specimen_id": str(uuid.uuid4()),
            "specimen_type": "ISF",
            "collected_at": datetime.utcnow().isoformat(),
            "raw_values": {"glucose": 120.0},
            "units": {"glucose": "mg/dL"},
            "missingness": {},  # Missing!
        }
        
        request_data = {
            "timezone": "UTC",
            "specimens": [specimen],
            "non_lab_inputs": {},
        }
        
        response = client.post(
            "/runs/v2",
            json=request_data,
            headers=auth_headers(token),
        )
        
        assert response.status_code == 422


class TestRunV2Retrieval:
    """Test GET /runs/v2/{run_id} endpoint."""

    def test_get_runv2_detail(self):
        """Retrieve a RunV2 by run_id with full details."""
        email, token = signup_and_get_token()
        
        # Create a RunV2
        specimen = SpecimenRecord(
            specimen_id=str(uuid.uuid4()),
            specimen_type=SpecimenTypeEnum.ISF,
            collected_at=datetime.utcnow(),
            raw_values={"glucose": 110.0},
            units={"glucose": "mg/dL"},
            missingness={
                "glucose": MissingnessRecord(
                    is_missing=False,
                    missing_impact=MissingImpactEnum.NEUTRAL,
                    provenance=ProvenanceEnum.MEASURED,
                ),
            },
        )
        
        request_data = RunV2CreateRequest(
            timezone="UTC",
            specimens=[specimen],
            non_lab_inputs=NonLabInputs(),
        )
        
        create_response = client.post(
            "/runs/v2",
            json=request_data.model_dump(mode="json"),
            headers=auth_headers(token),
        )
        run_id = create_response.json()["run_id"]
        
        # Retrieve it
        get_response = client.get(
            f"/runs/v2/{run_id}",
            headers=auth_headers(token),
        )
        
        assert get_response.status_code == 200
        data = get_response.json()
        assert data["run_id"] == run_id
        assert data["schema_version"] == "runv2.1"
        assert len(data["specimens"]) == 1
        assert data["specimens"][0]["specimen_type"] == "ISF"

    def test_get_runv2_not_found(self):
        """Return 404 if RunV2 doesn't exist."""
        email, token = signup_and_get_token()
        
        response = client.get(
            f"/runs/v2/nonexistent-run-id",
            headers=auth_headers(token),
        )
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_runv2_authorization(self):
        """Only the owning user can retrieve a RunV2."""
        email1, token1 = signup_and_get_token()
        email2, token2 = signup_and_get_token()
        
        # User 1 creates a RunV2
        specimen = SpecimenRecord(
            specimen_id=str(uuid.uuid4()),
            specimen_type=SpecimenTypeEnum.ISF,
            collected_at=datetime.utcnow(),
            raw_values={"glucose": 100.0},
            units={"glucose": "mg/dL"},
            missingness={
                "glucose": MissingnessRecord(
                    is_missing=False,
                    missing_impact=MissingImpactEnum.NEUTRAL,
                    provenance=ProvenanceEnum.MEASURED,
                ),
            },
        )
        
        request_data = RunV2CreateRequest(
            timezone="UTC",
            specimens=[specimen],
            non_lab_inputs=NonLabInputs(),
        )
        
        create_response = client.post(
            "/runs/v2",
            json=request_data.model_dump(mode="json"),
            headers=auth_headers(token1),
        )
        run_id = create_response.json()["run_id"]
        
        # User 2 tries to retrieve it
        get_response = client.get(
            f"/runs/v2/{run_id}",
            headers=auth_headers(token2),
        )
        
        assert get_response.status_code == 404


class TestMissingnessAndProvenance:
    """Test missingness and provenance tracking."""

    def test_missingness_tracking_present_value(self):
        """Present values should have is_missing=False."""
        email, token = signup_and_get_token()
        
        specimen = SpecimenRecord(
            specimen_id=str(uuid.uuid4()),
            specimen_type=SpecimenTypeEnum.ISF,
            collected_at=datetime.utcnow(),
            raw_values={"glucose": 95.0},
            units={"glucose": "mg/dL"},
            missingness={
                "glucose": MissingnessRecord(
                    is_missing=False,
                    missing_type=None,
                    missing_impact=MissingImpactEnum.NEUTRAL,
                    provenance=ProvenanceEnum.MEASURED,
                    confidence_0_1=1.0,
                ),
            },
        )
        
        request_data = RunV2CreateRequest(
            timezone="UTC",
            specimens=[specimen],
            non_lab_inputs=NonLabInputs(),
        )
        
        response = client.post(
            "/runs/v2",
            json=request_data.model_dump(mode="json"),
            headers=auth_headers(token),
        )
        
        assert response.status_code == 201

    def test_missingness_tracking_missing_value(self):
        """Missing values should be tracked with reason and impact."""
        email, token = signup_and_get_token()
        
        specimen = SpecimenRecord(
            specimen_id=str(uuid.uuid4()),
            specimen_type=SpecimenTypeEnum.ISF,
            collected_at=datetime.utcnow(),
            raw_values={"glucose": None, "lactate": 1.9},
            units={"glucose": "mg/dL", "lactate": "mmol/L"},
            missingness={
                "glucose": MissingnessRecord(
                    is_missing=True,
                    missing_type=MissingTypeEnum.SENSOR_UNAVAILABLE,
                    missing_impact=MissingImpactEnum.CONFIDENCE_PENALTY,
                    provenance=ProvenanceEnum.MEASURED,
                    confidence_0_1=0.0,
                    notes="Sensor malfunction",
                ),
                "lactate": MissingnessRecord(
                    is_missing=False,
                    missing_impact=MissingImpactEnum.NEUTRAL,
                    provenance=ProvenanceEnum.MEASURED,
                ),
            },
        )
        
        request_data = RunV2CreateRequest(
            timezone="UTC",
            specimens=[specimen],
            non_lab_inputs=NonLabInputs(),
        )
        
        response = client.post(
            "/runs/v2",
            json=request_data.model_dump(mode="json"),
            headers=auth_headers(token),
        )
        
        assert response.status_code == 201

    def test_provenance_tracking_proxy_vs_measured(self):
        """Proxy vs measured provenance should be tracked."""
        email, token = signup_and_get_token()
        
        specimen = SpecimenRecord(
            specimen_id=str(uuid.uuid4()),
            specimen_type=SpecimenTypeEnum.ISF,
            collected_at=datetime.utcnow(),
            raw_values={
                "glucose": 105.0,
                "crp_proxy": 2.5,
            },
            units={
                "glucose": "mg/dL",
                "crp_proxy": "relative_index",
            },
            missingness={
                "glucose": MissingnessRecord(
                    is_missing=False,
                    missing_impact=MissingImpactEnum.NEUTRAL,
                    provenance=ProvenanceEnum.MEASURED,
                ),
                "crp_proxy": MissingnessRecord(
                    is_missing=False,
                    missing_impact=MissingImpactEnum.NEUTRAL,
                    provenance=ProvenanceEnum.PROXY,
                ),
            },
        )
        
        request_data = RunV2CreateRequest(
            timezone="UTC",
            specimens=[specimen],
            non_lab_inputs=NonLabInputs(),
        )
        
        response = client.post(
            "/runs/v2",
            json=request_data.model_dump(mode="json"),
            headers=auth_headers(token),
        )
        
        assert response.status_code == 201


class TestNonLabInputs:
    """Test non-lab inputs always-on functionality."""

    def test_nonlab_inputs_all_sections(self):
        """Create RunV2 with all non-lab input sections populated."""
        email, token = signup_and_get_token()
        
        specimen = SpecimenRecord(
            specimen_id=str(uuid.uuid4()),
            specimen_type=SpecimenTypeEnum.ISF,
            collected_at=datetime.utcnow(),
            raw_values={"glucose": 100.0},
            units={"glucose": "mg/dL"},
            missingness={
                "glucose": MissingnessRecord(
                    is_missing=False,
                    missing_impact=MissingImpactEnum.NEUTRAL,
                    provenance=ProvenanceEnum.MEASURED,
                ),
            },
        )
        
        non_lab = NonLabInputs(
            demographics=DemographicsInputs(age=45, sex_at_birth="male"),
            anthropometrics=AnthropometricsInputs(height_cm=180, weight_kg=85),
            vitals_physiology=VitalsPhysiologyInputs(heart_rate=75, bp_systolic=125),
        )
        
        request_data = RunV2CreateRequest(
            timezone="UTC",
            specimens=[specimen],
            non_lab_inputs=non_lab,
        )
        
        response = client.post(
            "/runs/v2",
            json=request_data.model_dump(mode="json"),
            headers=auth_headers(token),
        )
        
        assert response.status_code == 201
        
        # Retrieve and verify
        run_id = response.json()["run_id"]
        get_response = client.get(
            f"/runs/v2/{run_id}",
            headers=auth_headers(token),
        )
        
        assert get_response.status_code == 200
        data = get_response.json()
        assert data["non_lab_inputs"]["demographics"]["age"] == 45
        assert data["non_lab_inputs"]["anthropometrics"]["weight_kg"] == 85

    def test_nonlab_inputs_empty_allowed(self):
        """Empty non-lab inputs should be allowed."""
        email, token = signup_and_get_token()
        
        specimen = SpecimenRecord(
            specimen_id=str(uuid.uuid4()),
            specimen_type=SpecimenTypeEnum.ISF,
            collected_at=datetime.utcnow(),
            raw_values={"glucose": 100.0},
            units={"glucose": "mg/dL"},
            missingness={
                "glucose": MissingnessRecord(
                    is_missing=False,
                    missing_impact=MissingImpactEnum.NEUTRAL,
                    provenance=ProvenanceEnum.MEASURED,
                ),
            },
        )
        
        request_data = RunV2CreateRequest(
            timezone="UTC",
            specimens=[specimen],
            non_lab_inputs=NonLabInputs(),  # Empty
        )
        
        response = client.post(
            "/runs/v2",
            json=request_data.model_dump(mode="json"),
            headers=auth_headers(token),
        )
        
        assert response.status_code == 201


class TestSpecimenTypes:
    """Test handling of different specimen types."""

    def test_all_specimen_types(self):
        """Test creating specimens of all supported types."""
        email, token = signup_and_get_token()
        
        specimen_types = [
            (SpecimenTypeEnum.ISF, {"glucose": 100.0}, {"glucose": "mg/dL"}),
            (SpecimenTypeEnum.BLOOD_CAPILLARY, {"glucose": 105.0}, {"glucose": "mg/dL"}),
            (SpecimenTypeEnum.BLOOD_VENOUS, {"hgb": 14.0}, {"hgb": "g/dL"}),
            (SpecimenTypeEnum.SALIVA, {"cortisol_morning": 15.0}, {"cortisol_morning": "ug/dL"}),
            (SpecimenTypeEnum.SWEAT, {"sodium_na": 45.0}, {"sodium_na": "mmol/L"}),
            (SpecimenTypeEnum.URINE_SPOT, {"specific_gravity": 1.020}, {"specific_gravity": "unitless"}),
        ]
        
        for spec_type, raw_vals, units in specimen_types:
            specimen = SpecimenRecord(
                specimen_id=str(uuid.uuid4()),
                specimen_type=spec_type,
                collected_at=datetime.utcnow(),
                raw_values=raw_vals,
                units=units,
                missingness={
                    var_name: MissingnessRecord(
                        is_missing=False,
                        missing_impact=MissingImpactEnum.NEUTRAL,
                        provenance=ProvenanceEnum.MEASURED,
                    )
                    for var_name in raw_vals.keys()
                },
            )
            
            request_data = RunV2CreateRequest(
                timezone="UTC",
                specimens=[specimen],
                non_lab_inputs=NonLabInputs(),
            )
            
            response = client.post(
                "/runs/v2",
                json=request_data.model_dump(mode="json"),
                headers=auth_headers(token),
            )
            
            assert response.status_code == 201, f"Failed for specimen type {spec_type}"
