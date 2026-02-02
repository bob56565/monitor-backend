"""
RunV2 API endpoints and compatibility adapter.
Part of Milestone 7 Phase 3 multi-specimen ingestion upgrade.
"""

import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import logging

from app.db.session import get_db
from app.models import User, RawSensorData, RunV2Record
from app.api.deps import get_current_user
from app.models.run_v2 import (
    RunV2, RunV2CreateRequest, RunV2Response, RunV2DetailResponse,
    SpecimenRecord, NonLabInputs, MissingnessRecord, ProvenanceEnum,
    MissingTypeEnum, MissingImpactEnum,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/runs", tags=["runs"])


# ============================================================================
# COMPATIBILITY ADAPTER: Legacy Raw Ingestion -> RunV2
# ============================================================================

def legacy_raw_ingestion_to_runv2_adapter(
    user_id: int,
    raw_record: RawSensorData,
    specimen_type: Optional[str] = None,
) -> RunV2:
    """
    Wrap legacy raw sensor data into a RunV2 structure.
    
    This adapter ensures:
    - Legacy endpoint response is unchanged
    - RunV2 payload is silently created and stored
    - Backward compatibility is maintained
    """
    # Determine specimen type (default ISF if legacy single entry)
    spec_type = specimen_type or "ISF"
    
    # Extract values from legacy record
    raw_data = raw_record.raw_data or {}
    observed = raw_data.get("observed", {})
    
    # Build missingness records for legacy values
    missingness = {}
    raw_values = {}
    units = {}
    
    # Glucose
    glucose_val = raw_record.sensor_value_1
    raw_values["glucose"] = glucose_val
    units["glucose"] = "mg/dL"
    missingness["glucose"] = MissingnessRecord(
        is_missing=glucose_val is None or glucose_val == 0,
        missing_type=MissingTypeEnum.NOT_COLLECTED if (glucose_val is None or glucose_val == 0) else None,
        missing_impact=MissingImpactEnum.CONFIDENCE_PENALTY if (glucose_val is None or glucose_val == 0) else MissingImpactEnum.NEUTRAL,
        provenance=ProvenanceEnum.MEASURED,
        confidence_0_1=1.0,
    )
    
    # Lactate
    lactate_val = raw_record.sensor_value_2
    raw_values["lactate"] = lactate_val
    units["lactate"] = "mmol/L"
    missingness["lactate"] = MissingnessRecord(
        is_missing=lactate_val is None or lactate_val == 0,
        missing_type=MissingTypeEnum.NOT_COLLECTED if (lactate_val is None or lactate_val == 0) else None,
        missing_impact=MissingImpactEnum.NEUTRAL,
        provenance=ProvenanceEnum.MEASURED,
        confidence_0_1=1.0,
    )
    
    # Create a SpecimenRecord from legacy data
    specimen = SpecimenRecord(
        specimen_id=str(uuid.uuid4()),
        specimen_type=spec_type,
        collected_at=raw_record.timestamp or datetime.utcnow(),
        source_detail="legacy_ingestion",
        raw_values=raw_values,
        units=units,
        missingness=missingness,
        notes="Auto-wrapped from legacy raw ingestion endpoint",
    )
    
    # Create RunV2 with minimal non-lab inputs
    run_v2 = RunV2(
        run_id=str(uuid.uuid4()),
        user_id=str(user_id),
        created_at=datetime.utcnow(),
        timezone="UTC",
        legacy_raw_id=raw_record.id,
        specimens=[specimen],
        non_lab_inputs=NonLabInputs(),  # Empty, user can update later
        schema_version="runv2.1",
    )
    
    return run_v2


def store_runv2_in_db(
    run_v2: RunV2,
    user_id: int,
    db: Session,
) -> RunV2Record:
    """Store RunV2 payload in database."""
    db_run = RunV2Record(
        run_id=run_v2.run_id,
        user_id=user_id,
        created_at=run_v2.created_at,
        timezone=run_v2.timezone or "UTC",
        legacy_raw_id=run_v2.legacy_raw_id,
        payload=run_v2.model_dump(mode="json"),
        schema_version=run_v2.schema_version,
        specimen_count=len(run_v2.specimens),
    )
    db.add(db_run)
    db.commit()
    db.refresh(db_run)
    return db_run


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/v2", response_model=RunV2Response, status_code=201)
def create_runv2(
    request: RunV2CreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new RunV2 with multiple specimens and non-lab inputs.
    
    - Accepts multi-specimen payloads
    - Always includes non-lab inputs section
    - Validates specimen types and variable mappings
    - Stores with explicit provenance and missingness tracking
    """
    # Validate specimens
    if not request.specimens:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="At least one specimen is required",
        )
    
    for specimen in request.specimens:
        if not specimen.raw_values:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Specimen {specimen.specimen_id} has no raw_values",
            )
        if not specimen.missingness:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Specimen {specimen.specimen_id} has no missingness records",
            )
    
    # Create RunV2
    run_v2 = RunV2(
        run_id=str(uuid.uuid4()),
        user_id=str(current_user.id),
        created_at=datetime.utcnow(),
        timezone=request.timezone or "UTC",
        specimens=request.specimens,
        non_lab_inputs=request.non_lab_inputs,
        qualitative_inputs=request.qualitative_inputs,
        schema_version="runv2.1",
    )
    
    # Store in DB
    db_run = store_runv2_in_db(run_v2, current_user.id, db)
    
    logger.info(
        f"Created RunV2 {run_v2.run_id} for user {current_user.id} with {len(run_v2.specimens)} specimens"
    )
    
    return RunV2Response(
        run_id=run_v2.run_id,
        user_id=str(current_user.id),
        created_at=run_v2.created_at,
        schema_version=run_v2.schema_version,
        specimen_count=len(run_v2.specimens),
        specimens=[
            {
                "specimen_id": s.specimen_id,
                "specimen_type": s.specimen_type,
                "collected_at": s.collected_at,
                "variable_count": len(s.raw_values),
            }
            for s in run_v2.specimens
        ],
    )


@router.get("/v2/{run_id}", response_model=RunV2DetailResponse)
def get_runv2(
    run_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve a RunV2 by run_id with full details including specimens, non-lab inputs, and qual encoding outputs.
    """
    db_run = db.query(RunV2Record).filter(
        RunV2Record.run_id == run_id,
        RunV2Record.user_id == current_user.id,
    ).first()
    
    if not db_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"RunV2 {run_id} not found",
        )
    
    # Reconstruct RunV2 from payload
    payload = db_run.payload
    run_v2 = RunV2(**payload)
    
    return RunV2DetailResponse(
        run_id=run_v2.run_id,
        user_id=str(current_user.id),
        created_at=run_v2.created_at,
        timezone=run_v2.timezone or "UTC",
        schema_version=run_v2.schema_version,
        specimens=run_v2.specimens,
        non_lab_inputs=run_v2.non_lab_inputs,
        qualitative_inputs=run_v2.qualitative_inputs,
        encoding_outputs=run_v2.encoding_outputs,
        provenance_map=run_v2.provenance_map,
        missingness_map=run_v2.missingness_map,
    )
