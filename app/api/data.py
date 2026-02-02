from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import logging
from app.db.session import get_db
from app.models import User, RawSensorData, CalibratedFeatures
from app.features.calibration import calibrate_sensor_readings, get_calibration_metadata
from app.features.derived import compute_derived_metric
from app.api.deps import get_current_user
from app.api.runs import legacy_raw_ingestion_to_runv2_adapter, store_runv2_in_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/data", tags=["data"])


class RawDataRequest(BaseModel):
    timestamp: Optional[str] = None
    specimen_type: Optional[str] = None
    observed: Optional[dict] = None
    context: Optional[dict] = None


class RawDataResponse(BaseModel):
    id: int
    timestamp: Optional[datetime]
    specimen_type: Optional[str]
    observed: Optional[dict]
    context: Optional[dict]

    class Config:
        from_attributes = True


class PreprocessRequest(BaseModel):
    raw_id: int


class PreprocessResponse(BaseModel):
    id: int
    calibrated_metric: float
    features: dict
    created_at: datetime

    class Config:
        from_attributes = True


@router.post("/raw", response_model=RawDataResponse, status_code=201)
def ingest_raw_data(
    request: RawDataRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Ingest raw sensor data."""
    # Extract sensor values from observed dict or use defaults
    observed = request.observed or {}
    glucose = observed.get("glucose_mg_dl", 100.0)
    lactate = observed.get("lactate_mmol_l", 1.5)
    context = request.context or {}
    
    raw_data = RawSensorData(
        user_id=current_user.id,
        timestamp=datetime.fromisoformat(request.timestamp.replace('Z', '+00:00')) if request.timestamp else datetime.utcnow(),
        sensor_value_1=float(glucose),
        sensor_value_2=float(lactate),
        sensor_value_3=0.0,
        raw_data={
            "specimen_type": request.specimen_type,
            "observed": observed,
            "context": context,
        }
    )
    db.add(raw_data)
    db.commit()
    db.refresh(raw_data)
    
    # COMPATIBILITY ADAPTER (M7): Wrap legacy raw data into RunV2 silently
    try:
        run_v2 = legacy_raw_ingestion_to_runv2_adapter(
            user_id=current_user.id,
            raw_record=raw_data,
            specimen_type=request.specimen_type,
        )
        store_runv2_in_db(run_v2, current_user.id, db)
        logger.info(f"Created RunV2 {run_v2.run_id} from legacy raw ingestion {raw_data.id}")
    except Exception as e:
        logger.warning(f"Failed to create RunV2 from legacy raw data: {str(e)}")
        # Do not fail the original endpoint; legacy behavior must remain intact
    
    return RawDataResponse(
        id=raw_data.id,
        timestamp=raw_data.timestamp,
        specimen_type=request.specimen_type,
        observed=observed,
        context=context,
    )


@router.post("/preprocess", response_model=PreprocessResponse)
def preprocess_data(
    request: PreprocessRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Preprocess raw sensor data: calibration + feature extraction.
    """
    raw_data = db.query(RawSensorData).filter(
        RawSensorData.id == request.raw_id,
        RawSensorData.user_id == current_user.id,
    ).first()
    
    if not raw_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Raw sensor data not found",
        )
    
    # Calibration
    raw_values = [raw_data.sensor_value_1, raw_data.sensor_value_2, raw_data.sensor_value_3]
    calibrated = calibrate_sensor_readings(raw_values)
    
    # Feature engineering
    derived = compute_derived_metric(calibrated)
    
    # Store calibrated features
    cal_features = CalibratedFeatures(
        user_id=current_user.id,
        raw_sensor_id=request.raw_id,
        feature_1=calibrated[0],
        feature_2=calibrated[1],
        feature_3=calibrated[2],
        derived_metric=derived,
    )
    db.add(cal_features)
    db.commit()
    db.refresh(cal_features)
    
    return PreprocessResponse(
        id=cal_features.id,
        calibrated_metric=cal_features.derived_metric,
        features={
            "feature_1": cal_features.feature_1,
            "feature_2": cal_features.feature_2,
            "feature_3": cal_features.feature_3,
        },
        created_at=cal_features.created_at,
    )
