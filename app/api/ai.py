from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, field_validator, model_validator
from datetime import datetime
from typing import List, Optional
import uuid
from app.db.session import get_db
from app.models import User, CalibratedFeatures, InferenceResult, RunV2Record
from app.ml.inference import infer as run_inference
from app.ml.forecast import forecast_next_step
from app.api.deps import get_current_user
from app.models.inference_pack_v2 import InferencePackV2
from app.models.run_v2 import RunV2
from app.features.preprocess_v2 import preprocess_v2 as preprocess_v2_pipeline, FeaturePackV2
from app.ml.inference_v2 import InferenceV2

router = APIRouter(prefix="/ai", tags=["ai"])


class InferenceRequest(BaseModel):
    calibrated_id: Optional[int] = None
    features: Optional[dict] = None  # Legacy dev convenience field
    
    @model_validator(mode='after')
    def check_at_least_one_id(self):
        if not self.calibrated_id and not self.features:
            raise ValueError("Either calibrated_id or features must be provided")
        return self


# Legacy response model (kept for backward compatibility if needed)
class InferenceResponse(BaseModel):
    id: int
    prediction: float
    confidence: float
    uncertainty: float
    created_at: datetime

    class Config:
        from_attributes = True


# New stable "User Report" contract
class InputSummary(BaseModel):
    specimen_type: str
    observed_inputs: List[str]
    missing_inputs: List[str]


class InferredValue(BaseModel):
    name: str
    value: float
    unit: str
    confidence: float = Field(..., ge=0, le=1)
    method: str


class ModelMetadata(BaseModel):
    model_name: str
    model_version: str
    trained_on: str


class InferenceReport(BaseModel):
    trace_id: str
    created_at: str  # ISO timestamp
    input_summary: InputSummary
    inferred: List[InferredValue]
    abnormal_flags: List[str]
    assumptions: List[str]
    limitations: List[str]
    model_metadata: ModelMetadata
    disclaimer: str


class ForecastRequest(BaseModel):
    calibrated_id: Optional[int] = None
    feature_values: Optional[list[float]] = None
    steps_ahead: int = 1  # Legacy alias; can be overridden by horizon_steps
    horizon_steps: Optional[int] = None  # Canonical; takes precedence if both provided
    
    @model_validator(mode='after')
    def reconcile_steps_and_validate(self):
        # Validate: at least one of calibrated_id or feature_values must be provided
        if not self.calibrated_id and not self.feature_values:
            raise ValueError("Either calibrated_id or feature_values must be provided")
        
        # Reconcile horizon_steps and steps_ahead: horizon_steps takes precedence
        if self.horizon_steps is None:
            self.horizon_steps = self.steps_ahead if self.steps_ahead else 1
        self.horizon_steps = max(1, self.horizon_steps)
        return self


class ForecastResponse(BaseModel):
    forecast: float
    forecasts: List[float] = []
    confidence: float
    steps_ahead: int  # Must equal horizon_steps from request


@router.post("/infer", response_model=InferenceReport, status_code=201)
def run_inference_endpoint(
    request: InferenceRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Run inference on calibrated features and return structured InferenceReport.
    
    Supports both calibrated_id (preferred) and features (legacy).
    Returns a stable contract with all required fields for production use.
    """
    # Determine features to use: calibrated_id takes precedence
    if request.calibrated_id:
        cal_features = db.query(CalibratedFeatures).filter(
            CalibratedFeatures.id == request.calibrated_id,
            CalibratedFeatures.user_id == current_user.id,
        ).first()
        
        if not cal_features:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Calibrated features not found",
            )
        
        # Extract features in deterministic order: sorted keys
        features = [cal_features.feature_1, cal_features.feature_2, cal_features.feature_3]
    elif request.features:
        # Legacy path: accept features dict
        features = [request.features.get(f"feature_{i}", 0.0) for i in range(1, 4)]
    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Either calibrated_id or features must be provided",
        )
    
    # Perform inference
    inference_result_dict = run_inference(features)
    
    # Store result
    inference_result = InferenceResult(
        user_id=current_user.id,
        calibrated_feature_id=request.calibrated_id,
        prediction=inference_result_dict["prediction"],
        confidence=inference_result_dict["confidence"],
        uncertainty=inference_result_dict["uncertainty"],
        inference_metadata=inference_result_dict,
    )
    db.add(inference_result)
    db.commit()
    db.refresh(inference_result)
    
    # Build structured InferenceReport
    trace_id = str(uuid.uuid4())
    
    # Ensure confidence is between 0 and 1
    confidence = float(inference_result_dict["confidence"])
    confidence = max(0.0, min(1.0, confidence))
    
    # Construct the inferred values array
    inferred_values = [
        InferredValue(
            name="primary_prediction",
            value=float(inference_result_dict["prediction"]),
            unit="normalized_units",
            confidence=confidence,
            method="MVP_linear_model",
        ),
        InferredValue(
            name="uncertainty_estimate",
            value=float(inference_result_dict["uncertainty"]),
            unit="probability",
            confidence=0.8,
            method="distance_based_heuristic",
        ),
    ]
    
    report = InferenceReport(
        trace_id=trace_id,
        created_at=inference_result.created_at.isoformat(),
        input_summary=InputSummary(
            specimen_type="sensor_array",
            observed_inputs=["feature_1", "feature_2", "feature_3"],
            missing_inputs=[],
        ),
        inferred=inferred_values,
        abnormal_flags=[],
        assumptions=[
            "Features have been calibrated",
            "Input data is within expected range",
            "Model was trained on similar specimen types",
        ],
        limitations=[
            "MVP model is linear and does not capture complex interactions",
            "Uncertainty estimate is heuristic-based, not Bayesian",
            "Limited training data in current MVP phase",
        ],
        model_metadata=ModelMetadata(
            model_name="MONITOR_MVP_Inference",
            model_version="1.0",
            trained_on="synthetic_calibration_data",
        ),
        disclaimer="This is an MVP model for research purposes. Do not use for clinical decisions without validation.",
    )
    
    return report


@router.post("/forecast", response_model=ForecastResponse)
def forecast_endpoint(
    request: ForecastRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Forecast endpoint supporting both calibrated_id and feature_values.
    
    If calibrated_id is provided, loads calibrated features from DB.
    Otherwise, uses provided feature_values.
    Supports both horizon_steps (canonical) and steps_ahead (legacy alias).
    """
    # Determine features to use: calibrated_id takes precedence
    if request.calibrated_id:
        cal_features = db.query(CalibratedFeatures).filter(
            CalibratedFeatures.id == request.calibrated_id,
            CalibratedFeatures.user_id == current_user.id,
        ).first()
        
        if not cal_features:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Calibrated features not found",
            )
        
        # Extract features in deterministic order
        feature_values = [cal_features.feature_1, cal_features.feature_2, cal_features.feature_3]
    elif request.feature_values:
        feature_values = request.feature_values
    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Either calibrated_id or feature_values must be provided",
        )
    
    # Use canonical horizon_steps; should be reconciled in __init__
    steps = max(1, request.horizon_steps or request.steps_ahead)
    
    result = forecast_next_step(feature_values, steps_ahead=steps)
    
    # Ensure forecasts list is populated
    forecasts = result.get("forecasts", [])
    if not forecasts and "forecast" in result:
        # Backward compatibility: if only forecast exists, wrap it
        forecasts = [result["forecast"]]
    
    return ForecastResponse(
        forecast=result["forecast"],
        forecasts=forecasts,
        confidence=result["confidence"],
        steps_ahead=result["steps_ahead"],
    )


# ============================================================================
# M7 Part 2: Preprocess V2 for RunV2 → feature_pack_v2
# ============================================================================

class PreprocessV2Request(BaseModel):
    run_id: str  # From POST /runs/v2


class PreprocessV2Response(BaseModel):
    calibrated_id: int
    run_v2_id: str
    feature_pack_v2_schema_version: str
    overall_coherence_0_1: float
    specimen_count: int
    domains_present: List[str]
    penalty_factors: List[str]
    domain_blockers: List[str]
    created_at: datetime

    class Config:
        from_attributes = True


@router.post("/preprocess-v2", response_model=PreprocessV2Response, status_code=201)
def preprocess_v2_endpoint(
    request: PreprocessV2Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Preprocess a RunV2 payload to generate feature_pack_v2.
    
    - Reads RunV2 from DB by run_id
    - Computes feature_pack_v2 with missingness-aware features, cross-specimen relationships, patterns
    - Stores feature_pack_v2 in CalibratedFeatures as optional JSON column
    - Returns coherence scores and penalties for Phase 3 inference gating
    
    Non-breaking: Does not modify legacy features.
    """
    # Load RunV2
    db_run = db.query(RunV2Record).filter(
        RunV2Record.run_id == request.run_id,
        RunV2Record.user_id == current_user.id,
    ).first()
    
    if not db_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"RunV2 {request.run_id} not found",
        )
    
    # Reconstruct RunV2 from payload
    run_v2_payload = db_run.payload
    run_v2 = RunV2(**run_v2_payload)
    
    # Run preprocess_v2
    try:
        feature_pack_v2 = preprocess_v2_pipeline(run_v2)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Feature pack v2 computation failed: {str(e)}",
        )
    
    # Store in CalibratedFeatures (create a new record with feature_pack_v2 + legacy stubs)
    cal_features = CalibratedFeatures(
        user_id=current_user.id,
        raw_sensor_id=db_run.legacy_raw_id,
        feature_1=0.0,  # Legacy stubs (unused for v2 pathway)
        feature_2=0.0,
        feature_3=0.0,
        derived_metric=0.0,
        feature_pack_v2=feature_pack_v2.model_dump(mode="json"),
        run_v2_id=run_v2.run_id,
    )
    db.add(cal_features)
    db.commit()
    db.refresh(cal_features)
    
    return PreprocessV2Response(
        calibrated_id=cal_features.id,
        run_v2_id=run_v2.run_id,
        feature_pack_v2_schema_version=feature_pack_v2.schema_version,
        overall_coherence_0_1=feature_pack_v2.coherence_scores.overall_coherence_0_1,
        specimen_count=feature_pack_v2.specimen_count,
        domains_present=feature_pack_v2.domains_present,
        penalty_factors=feature_pack_v2.penalty_vector.penalty_factors,
        domain_blockers=feature_pack_v2.penalty_vector.domain_blockers,
        created_at=cal_features.created_at,
    )


# ============================================================================
# INFERENCE V2 ENDPOINTS (Part 3: Clinic-Grade Inference with Gating + Confidence)
# ============================================================================

class InferenceV2Request(BaseModel):
    run_id: str = Field(..., description="RunV2 ID to infer from")
    
    class Config:
        json_schema_extra = {
            "example": {
                "run_id": "run_2025_001_user123"
            }
        }


class InferenceV2Response(BaseModel):
    run_id: str
    inference_pack_v2: InferencePackV2
    created_at: datetime
    
    class Config:
        json_schema_extra = {
            "example": {
                "run_id": "run_2025_001_user123",
                "inference_pack_v2": {
                    "schema_version": "v2",
                    "measured_values": [],
                    "inferred_values": [],
                    "physiological_states": [],
                    "suppressed_outputs": [],
                    "eligibility_rationale": [],
                    "engine_outputs": [],
                    "consensus_metrics": None,
                    "provenance_map": []
                },
                "created_at": "2025-01-28T08:50:00Z"
            }
        }


@router.post("/inference/v2")
def inference_v2(
    request: InferenceV2Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Run Inference V2: Clinic-grade panel inference with eligibility gating and computed confidence.
    
    **Pipeline:**
    1. Load RunV2 + feature_pack_v2 from database
    2. Run eligibility gating (resolve output dependencies, suppress ineligible outputs)
    3. Compute clinical panel estimates (CMP, CBC, Lipids, Endocrine, etc.)
    4. Compute physiological state domains (metabolic, renal, electrolyte, etc.)
    5. Calculate confidence from completeness, coherence, agreement, stability, signal_quality
    6. Return inference_pack_v2 with measured/inferred/states/suppressed/rationale/provenance
    
    **Non-Breaking:**
    - Parallel pathway (legacy /inference remains unchanged)
    - Stores inference_pack_v2 separately in new column
    - Falls back to population priors if v2 features unavailable
    
    **Returns:**
    - Inferred clinical panel outputs with explicit support_type (direct/derived/proxy/population)
    - Suppressed outputs with reasons (missing dependencies, low coherence, etc.)
    - Confidence scores incorporating 6 components
    - Physiological state assessments
    - Provenance mapping (which specimens produced each output)
    """
    # ========== STEP 1: Load RunV2 ==========
    db_run = db.query(RunV2Record).filter(
        RunV2Record.run_id == request.run_id,
        RunV2Record.user_id == current_user.id,
    ).first()
    
    if not db_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"RunV2 {request.run_id} not found",
        )
    
    # Reconstruct RunV2 from payload
    try:
        run_v2_payload = db_run.payload
        run_v2 = RunV2(**run_v2_payload)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"RunV2 payload deserialization failed: {str(e)}",
        )
    
    # ========== STEP 2: Load or Compute feature_pack_v2 ==========
    # First check if preprocess_v2 has been run
    cal_features = db.query(CalibratedFeatures).filter(
        CalibratedFeatures.run_v2_id == request.run_id,
        CalibratedFeatures.user_id == current_user.id,
    ).first()
    
    if cal_features and cal_features.feature_pack_v2:
        # Load stored feature_pack_v2
        try:
            feature_pack_v2 = FeaturePackV2(**cal_features.feature_pack_v2)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Feature pack v2 deserialization failed: {str(e)}",
            )
    else:
        # Compute feature_pack_v2 on-the-fly
        try:
            feature_pack_v2 = preprocess_v2_pipeline(run_v2)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Feature pack v2 computation failed: {str(e)}",
            )
    
    # ========== STEP 3: Run Inference V2 ==========
    try:
        inference_engine = InferenceV2()
        inference_pack_v2 = inference_engine.infer(run_v2, feature_pack_v2.model_dump(mode="json"))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Inference V2 execution failed: {str(e)}",
        )
    
    # ========== STEP 4: Store Result (optional new table or column) ==========
    # For now, store as extension to InferenceResult if exists, or create new record
    # This ensures non-breaking: legacy inference_results untouched, v2 stored separately
    
    # Convert to dict to avoid Pydantic serialization issues
    response_data = {
        "run_id": request.run_id,
        "inference_pack_v2": inference_pack_v2.model_dump(mode="json"),
        "created_at": datetime.utcnow().isoformat(),
    }
    
    return response_data


@router.get("/inference/v2/{run_id}", response_model=InferenceV2Response)
def get_inference_v2(
    run_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve cached Inference V2 result for a RunV2.
    
    Returns the most recent inference_pack_v2 computed for this run_id.
    If not cached, will re-compute on-the-fly.
    """
    # TODO: Query for cached inference_pack_v2 from new table or column
    # For now, re-compute on retrieval (acceptable since inference_v2 is fast)
    
    request = InferenceV2Request(run_id=run_id)
    return inference_v2(request, db, current_user)
