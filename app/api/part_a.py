"""
PART A API Endpoints
Complete API for ingesting all PART A raw data user inputs.
Non-breaking, additive endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime
import logging
import uuid
import json

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models import User
from app.models.part_a_models import (
    PartASubmission,
    SpecimenUpload,
    SpecimenAnalyte,
    ISFAnalyteStream,
    VitalsRecord,
    SOAPProfileRecord,
    QualitativeEncodingRecord,
    SubmissionStatusEnum
)

from schemas.part_a.v1.main_schema import (
    PartAInputSchema,
    SpecimenDataUpload,
    ISFMonitorData,
    VitalsData,
    SOAPProfile,
    QualitativeEncoding,
    FileFormatEnum
)

from ingestion.specimens.blood import parse_blood_specimen
from ingestion.specimens.saliva import parse_saliva_specimen
from ingestion.specimens.sweat import parse_sweat_specimen
from ingestion.specimens.urine import parse_urine_specimen
from ingestion.reports.imaging import parse_imaging_report

from encoding.qualitative_to_quantitative import get_encoding_registry
from app.services.a2_orchestrator import a2_orchestrator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/part-a", tags=["part-a"])


@router.post("/submit", status_code=status.HTTP_201_CREATED)
def submit_part_a_data(
    part_a_data: PartAInputSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Submit complete PART A raw data user input.
    Validates against PartAInputSchema, stores in database, returns submission ID.
    """
    try:
        # Generate submission ID
        submission_id = str(uuid.uuid4())
        part_a_data.submission_id = submission_id
        part_a_data.user_id = current_user.id
        
        # Validate schema (Pydantic does this automatically)
        # Check that ≥1 specimen modality selected
        if not part_a_data.specimen_data.modalities_selected:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least 1 specimen modality must be selected (A1 requirement)"
            )
        
        # Apply qualitative encoding
        encoding_registry = get_encoding_registry()
        soap_dict = part_a_data.soap_profile.model_dump()
        applied_rules = encoding_registry.encode_qualitative_inputs(soap_dict)
        
        # Update qualitative encoding in submission
        part_a_data.qualitative_encoding.rules_applied = applied_rules
        part_a_data.qualitative_encoding.total_encoding_entries = len(applied_rules)
        
        # Create master submission record
        submission = PartASubmission(
            submission_id=submission_id,
            user_id=current_user.id,
            schema_version=part_a_data.schema_version,
            status=SubmissionStatusEnum.SUBMITTED,
            submission_timestamp=part_a_data.submission_timestamp,
            full_payload_json=part_a_data.model_dump(mode="json")
        )
        db.add(submission)
        db.flush()  # Get submission.id
        
        # Store specimen uploads
        _store_specimen_uploads(db, submission.id, part_a_data.specimen_data)
        
        # Store ISF streams
        _store_isf_streams(db, submission.id, part_a_data.isf_monitor_data)
        
        # Store vitals
        _store_vitals(db, submission.id, part_a_data.vitals_data)
        
        # Store SOAP profile
        _store_soap_profile(db, submission.id, part_a_data.soap_profile)
        
        # Store qualitative encoding
        _store_qualitative_encoding(db, submission.id, part_a_data.qualitative_encoding)
        
        # Update submission status
        submission.status = SubmissionStatusEnum.COMPLETED
        
        db.commit()
        
        # Trigger A2 processing synchronously (for demo/dev; could be async in production)
        try:
            a2_result = a2_orchestrator.run_synchronous(
                db=db,
                submission_id=submission_id,
                user_id=current_user.id,
                triggered_by="auto"
            )
            a2_run_id = a2_result.get("a2_run_id")
            a2_status = a2_result.get("status", "unknown")
        except Exception as e:
            # A2 failed, but Part A succeeded
            # Create a failed A2 run so UI can show error and retry
            logger.error(f"A2 auto-trigger failed for submission {submission_id}: {str(e)}")
            failed_run = a2_orchestrator.create_run(
                db=db,
                submission_id=submission_id,
                user_id=current_user.id,
                triggered_by="auto"
            )
            from app.models import A2StatusEnum
            failed_run.status = A2StatusEnum.FAILED
            failed_run.error_message = f"Auto-trigger failed: {str(e)}"
            db.commit()
            a2_run_id = failed_run.a2_run_id
            a2_status = "failed"
        
        return {
            "submission_id": submission_id,
            "status": "completed",
            "message": "PART A data successfully submitted and stored",
            "qualitative_encodings_applied": len(applied_rules),
            "timestamp": datetime.utcnow().isoformat(),
            # A2 contract fields
            "a2_run_id": a2_run_id,
            "a2_status": a2_status
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Submission failed: {str(e)}"
        )


@router.post("/upload-specimen", status_code=status.HTTP_201_CREATED)
def upload_specimen_file(
    modality: str = Form(...),
    source_format: str = Form(...),
    file: Optional[UploadFile] = File(None),
    metadata: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Upload individual specimen file (blood PDF, imaging report, etc.).
    Returns parsed data for review before final submission.
    """
    try:
        # Parse metadata JSON
        metadata_dict = json.loads(metadata) if metadata else {}
        
        # Read file content
        file_content = file.file.read() if file else None
        file_path = None  # In production, would save to artifact storage
        
        # Parse based on modality
        source_format_enum = FileFormatEnum(source_format)
        
        if modality == "blood":
            parsed_data, errors = parse_blood_specimen(
                file_path=file_path,
                file_content=file_content,
                source_format=source_format_enum,
                metadata=metadata_dict
            )
            result = parsed_data.model_dump(mode="json")
        elif modality == "saliva":
            parsed_data, errors = parse_saliva_specimen(
                file_content=file_content,
                source_format=source_format_enum,
                metadata=metadata_dict
            )
            result = parsed_data.model_dump(mode="json")
        elif modality == "sweat":
            parsed_data, errors = parse_sweat_specimen(
                file_content=file_content,
                source_format=source_format_enum,
                metadata=metadata_dict
            )
            result = parsed_data.model_dump(mode="json")
        elif modality == "urine":
            parsed_data, errors = parse_urine_specimen(
                file_content=file_content,
                source_format=source_format_enum,
                metadata=metadata_dict
            )
            result = parsed_data.model_dump(mode="json")
        elif modality == "imaging":
            parsed_data, errors = parse_imaging_report(
                file_path=file_path,
                file_content=file_content,
                source_format=source_format_enum,
                metadata=metadata_dict
            )
            result = parsed_data.model_dump(mode="json")
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported modality: {modality}"
            )
        
        return {
            "status": "parsed",
            "modality": modality,
            "parsed_data": result,
            "parsing_errors": errors,
            "message": "File parsed successfully. Review data and include in full PART A submission."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload failed: {str(e)}"
        )


@router.get("/submissions/{submission_id}")
def get_submission(
    submission_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve a PART A submission by ID."""
    submission = db.query(PartASubmission).filter(
        PartASubmission.submission_id == submission_id,
        PartASubmission.user_id == current_user.id
    ).first()
    
    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submission not found"
        )
    
    return {
        "submission_id": submission.submission_id,
        "status": submission.status.value,
        "submission_timestamp": submission.submission_timestamp.isoformat(),
        "schema_version": submission.schema_version,
        "full_payload": submission.full_payload_json,
        "created_at": submission.created_at.isoformat()
    }


@router.get("/submissions")
def list_submissions(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all PART A submissions for current user."""
    submissions = db.query(PartASubmission).filter(
        PartASubmission.user_id == current_user.id
    ).order_by(PartASubmission.submission_timestamp.desc()).offset(skip).limit(limit).all()
    
    return {
        "submissions": [
            {
                "submission_id": s.submission_id,
                "status": s.status.value,
                "submission_timestamp": s.submission_timestamp.isoformat(),
                "schema_version": s.schema_version
            }
            for s in submissions
        ],
        "total": len(submissions)
    }


@router.post("/validate")
def validate_part_a_schema(part_a_data: PartAInputSchema):
    """
    Validate PART A data against schema without storing.
    Useful for frontend validation.
    """
    try:
        # Pydantic validation happens automatically
        # Apply qualitative encoding to show what would be computed
        encoding_registry = get_encoding_registry()
        soap_dict = part_a_data.soap_profile.model_dump()
        applied_rules = encoding_registry.encode_qualitative_inputs(soap_dict)
        
        aggregate_modifiers = encoding_registry.compute_aggregate_modifiers(applied_rules)
        
        return {
            "valid": True,
            "message": "PART A schema validation passed",
            "modalities_selected": part_a_data.specimen_data.modalities_selected,
            "qualitative_encodings_count": len(applied_rules),
            "aggregate_modifiers": aggregate_modifiers,
            "qualitative_rules_preview": [
                {
                    "input_field": r.input_field,
                    "input_value": r.input_value,
                    "standardized_code": r.standardized_code,
                    "numeric_weight": r.numeric_weight,
                    "direction_of_effect": r.direction_of_effect
                }
                for r in applied_rules[:10]  # Preview first 10
            ]
        }
    except Exception as e:
        return {
            "valid": False,
            "errors": str(e)
        }


# ============================================================================
# INTERNAL HELPER FUNCTIONS
# ============================================================================

def _store_specimen_uploads(db: Session, submission_id: int, specimen_data: SpecimenDataUpload):
    """Store specimen uploads and their analytes."""
    # Blood specimens
    for blood in specimen_data.blood or []:
        upload = SpecimenUpload(
            submission_id=submission_id,
            modality="blood",
            collection_datetime=blood.collection_datetime,
            source_format=blood.source_format.value,
            raw_artifact_path=blood.raw_artifact_path,
            parsed_data_json=blood.model_dump(mode="json"),
            parsing_status="success",
            parsing_notes=blood.parsing_notes,
            lab_name=blood.lab_name,
            lab_id=blood.lab_id,
            fasting_status=blood.fasting_status.value
        )
        db.add(upload)
        db.flush()
        
        # Store analytes
        for analyte in blood.analytes:
            analyte_record = SpecimenAnalyte(
                upload_id=upload.id,
                name=analyte.name,
                value=analyte.value,
                value_string=analyte.value_string,
                unit=analyte.unit,
                reference_range_low=analyte.reference_range_low,
                reference_range_high=analyte.reference_range_high,
                reference_range_text=analyte.reference_range_text,
                flag=analyte.flag,
                method=analyte.method
            )
            db.add(analyte_record)
    
    # Saliva, sweat, urine, imaging - similar pattern
    for saliva in specimen_data.saliva or []:
        upload = SpecimenUpload(
            submission_id=submission_id,
            modality="saliva",
            source_format=saliva.source_format.value,
            parsed_data_json=saliva.model_dump(mode="json"),
            parsing_status="success"
        )
        db.add(upload)
    
    for sweat in specimen_data.sweat or []:
        upload = SpecimenUpload(
            submission_id=submission_id,
            modality="sweat",
            collection_datetime=sweat.collection_datetime,
            source_format=sweat.source_format.value,
            parsed_data_json=sweat.model_dump(mode="json"),
            parsing_status="success"
        )
        db.add(upload)
    
    for urine in specimen_data.urine or []:
        upload = SpecimenUpload(
            submission_id=submission_id,
            modality="urine",
            collection_datetime=urine.collection_datetime,
            source_format=urine.source_format.value,
            parsed_data_json=urine.model_dump(mode="json"),
            parsing_status="success"
        )
        db.add(upload)
    
    for imaging in specimen_data.imaging or []:
        upload = SpecimenUpload(
            submission_id=submission_id,
            modality="imaging",
            source_format=imaging.source_format.value,
            raw_artifact_path=imaging.raw_artifact_path,
            parsed_data_json=imaging.model_dump(mode="json"),
            parsing_status="success"
        )
        db.add(upload)


def _store_isf_streams(db: Session, submission_id: int, isf_data: ISFMonitorData):
    """Store ISF analyte streams."""
    all_streams = (isf_data.core_analytes or []) + \
                  (isf_data.electrolytes or []) + \
                  (isf_data.renal_metabolic or []) + \
                  (isf_data.inflammation_oxidative or [])
    
    for stream in all_streams:
        isf_stream = ISFAnalyteStream(
            submission_id=submission_id,
            name=stream.name,
            unit=stream.unit,
            device_id=stream.device_id,
            sensor_type=stream.sensor_type,
            values_json=[float(v) for v in stream.values],
            timestamps_json=[ts.isoformat() for ts in stream.timestamps],
            calibration_status=isf_data.signal_quality.calibration_status,
            sensor_drift_score=isf_data.signal_quality.sensor_drift_score,
            noise_score=isf_data.signal_quality.noise_score,
            dropout_percentage=isf_data.signal_quality.dropout_percentage
        )
        db.add(isf_stream)


def _store_vitals(db: Session, submission_id: int, vitals_data: VitalsData):
    """Store vitals record."""
    vitals_record = VitalsRecord(
        submission_id=submission_id,
        cardiovascular_json=vitals_data.cardiovascular.model_dump(mode="json"),
        respiratory_temperature_json=vitals_data.respiratory_temperature.model_dump(mode="json"),
        sleep_recovery_activity_json=vitals_data.sleep_recovery_activity.model_dump(mode="json"),
        baseline_learning_days=vitals_data.baseline_learning_days
    )
    db.add(vitals_record)


def _store_soap_profile(db: Session, submission_id: int, soap_profile: SOAPProfile):
    """Store SOAP profile."""
    demo = soap_profile.demographics_anthropometrics
    
    soap_record = SOAPProfileRecord(
        submission_id=submission_id,
        age=demo.age,
        sex_at_birth=demo.sex_at_birth,
        height_cm=demo.height_cm,
        weight_kg=demo.weight_kg,
        bmi=demo.bmi,
        demographics_anthropometrics_json=demo.model_dump(mode="json"),
        medical_history_json=soap_profile.medical_history.model_dump(mode="json"),
        medications_supplements_json=soap_profile.medications_supplements.model_dump(mode="json"),
        diet_json=soap_profile.diet.model_dump(mode="json"),
        activity_lifestyle_json=soap_profile.activity_lifestyle.model_dump(mode="json"),
        symptoms_json=soap_profile.symptoms.model_dump(mode="json")
    )
    db.add(soap_record)


def _store_qualitative_encoding(db: Session, submission_id: int, encoding: QualitativeEncoding):
    """Store qualitative encoding records."""
    for rule in encoding.rules_applied:
        encoding_record = QualitativeEncodingRecord(
            submission_id=submission_id,
            input_field=rule.input_field,
            input_value=rule.input_value,
            standardized_code=rule.standardized_code,
            numeric_weight=rule.numeric_weight,
            time_window=rule.time_window,
            direction_of_effect_json=rule.direction_of_effect,
            notes=rule.notes
        )
        db.add(encoding_record)
