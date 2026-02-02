"""
A2 API Endpoints

RESTful endpoints for A2 data quality processing:
- Status tracking
- Manual run controls
- Summary retrieval
- Per-submission operations
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime

from app.api.deps import get_db, get_current_user
from app.models import User
from app.services.a2_orchestrator import a2_orchestrator

router = APIRouter(prefix="/a2", tags=["A2 Data Quality"])


# Request/Response Schemas

class A2StatusResponse(BaseModel):
    """A2 run status response."""
    submission_id: str
    user_id: int
    a2_run_id: str
    status: str = Field(..., description="queued, running, completed, failed")
    progress: float = Field(..., ge=0.0, le=1.0)
    error_message: Optional[str] = None
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    updated_at: str


class A2SummaryResponse(BaseModel):
    """Canonical A2 Summary response."""
    submission_id: str
    user_id: int
    a2_run_id: str
    created_at: str
    stream_coverage: Dict[str, Dict[str, Any]]
    gating: Dict[str, Any]
    priors_used: Dict[str, Any]
    prior_decay_state: Dict[str, Any]
    conflict_flags: List[Dict[str, Any]]
    derived_features_count: int
    derived_features_detail: Optional[Dict[str, Any]] = None
    anchor_strength_by_domain: Dict[str, Dict[str, Any]]
    confidence_distribution: Optional[Dict[str, int]] = None
    schema_version: str


class A2RunRequest(BaseModel):
    """Request to manually trigger A2 run."""
    submission_id: str


class A2RunResponse(BaseModel):
    """Response after triggering A2 run."""
    a2_run_id: str
    submission_id: str
    status: str
    message: str


# Endpoints

@router.get("/status")
def get_a2_status(
    submission_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> A2StatusResponse:
    """
    Get A2 run status for a submission.
    
    Returns latest A2 run status including progress, errors, and timestamps.
    """
    status_data = a2_orchestrator.get_run_status(
        db=db,
        submission_id=submission_id,
        user_id=current_user.id
    )
    
    if not status_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No A2 run found for submission {submission_id}"
        )
    
    return A2StatusResponse(**status_data)


@router.get("/summary")
def get_a2_summary(
    submission_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> A2SummaryResponse:
    """
    Get canonical A2 Summary for a submission.
    
    Returns complete A2 analysis results including coverage, gating, conflicts, and anchor strength.
    """
    summary_data = a2_orchestrator.get_summary(
        db=db,
        submission_id=submission_id,
        user_id=current_user.id
    )
    
    if not summary_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No A2 summary found for submission {submission_id}. Run A2 first."
        )
    
    return A2SummaryResponse(**summary_data)


@router.post("/run")
def run_a2_analysis(
    request: A2RunRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> A2RunResponse:
    """
    Manually trigger A2 analysis for a submission.
    
    Creates a new A2 run and executes it synchronously.
    """
    try:
        result = a2_orchestrator.run_synchronous(
            db=db,
            submission_id=request.submission_id,
            user_id=current_user.id,
            triggered_by="manual"
        )
        
        if result["status"] == "failed":
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"A2 processing failed: {result.get('error', 'Unknown error')}"
            )
        
        return A2RunResponse(
            a2_run_id=result["a2_run_id"],
            submission_id=request.submission_id,
            status=result["status"],
            message="A2 analysis completed successfully"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error running A2 analysis: {str(e)}"
        )


@router.post("/retry")
def retry_a2_analysis(
    request: A2RunRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> A2RunResponse:
    """
    Retry A2 analysis for a submission.
    
    Creates a new run and marks previous run as superseded.
    """
    try:
        # Create retry run
        run = a2_orchestrator.retry_run(
            db=db,
            submission_id=request.submission_id,
            user_id=current_user.id
        )
        
        # Execute immediately
        result = a2_orchestrator.execute_run(db=db, a2_run_id=run.a2_run_id)
        
        if result["status"] == "failed":
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"A2 retry failed: {result.get('error', 'Unknown error')}"
            )
        
        return A2RunResponse(
            a2_run_id=run.a2_run_id,
            submission_id=request.submission_id,
            status=result["status"],
            message="A2 analysis retried successfully"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrying A2 analysis: {str(e)}"
        )


@router.get("/run-details")
def get_run_details(
    submission_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get detailed A2 run information including history.
    
    Returns run metadata, status transitions, and summary linkage.
    """
    from app.models import A2Run
    
    runs = db.query(A2Run).filter(
        A2Run.submission_id == submission_id,
        A2Run.user_id == current_user.id
    ).order_by(A2Run.created_at.desc()).all()
    
    if not runs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No A2 runs found for submission {submission_id}"
        )
    
    latest_run = runs[0]
    
    return {
        "submission_id": submission_id,
        "latest_run": {
            "a2_run_id": latest_run.a2_run_id,
            "status": latest_run.status.value,
            "triggered_by": latest_run.triggered_by,
            "created_at": latest_run.created_at.isoformat(),
            "started_at": latest_run.started_at.isoformat() if latest_run.started_at else None,
            "completed_at": latest_run.completed_at.isoformat() if latest_run.completed_at else None,
            "computation_time_ms": latest_run.computation_time_ms,
            "error_message": latest_run.error_message,
            "superseded": latest_run.superseded,
            "has_summary": latest_run.summary is not None
        },
        "run_history": [
            {
                "a2_run_id": r.a2_run_id,
                "status": r.status.value,
                "created_at": r.created_at.isoformat(),
                "superseded": r.superseded
            }
            for r in runs
        ],
        "total_runs": len(runs)
    }


# Backward-compatible per-submission completeness endpoint

@router.get("/completeness/{submission_id}")
def get_submission_completeness(
    submission_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get data completeness for a specific submission.
    
    Backward-compatible endpoint that returns completeness from A2 summary if available,
    or computes it on-the-fly if A2 hasn't run yet.
    """
    # Try to get A2 summary first
    summary_data = a2_orchestrator.get_summary(
        db=db,
        submission_id=submission_id,
        user_id=current_user.id
    )
    
    if summary_data:
        # Return completeness from A2 summary
        stream_coverage = summary_data["stream_coverage"]
        
        # Compute overall completeness
        quality_scores = [stream_coverage[k]["quality_score"] for k in stream_coverage]
        overall_score = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
        
        return {
            "submission_id": submission_id,
            "completeness_score": overall_score,
            "has_isf_monitor": stream_coverage["glucose"]["days_covered"] > 0,
            "has_specimens": stream_coverage["labs"]["days_covered"] > 0,
            "specimen_count": stream_coverage["labs"]["days_covered"],
            "has_vitals": stream_coverage["vitals"]["days_covered"] > 0,
            "has_soap": stream_coverage["pros"]["quality_score"] > 0,
            "stream_coverage": stream_coverage,
            "source": "a2_summary"
        }
    else:
        # A2 hasn't run yet - compute on-the-fly
        from app.models import PartASubmission, SpecimenUpload, ISFAnalyteStream, VitalsRecord
        
        submission = db.query(PartASubmission).filter(
            PartASubmission.submission_id == submission_id,
            PartASubmission.user_id == current_user.id
        ).first()
        
        if not submission:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Submission {submission_id} not found"
            )
        
        # Count data
        specimen_count = db.query(SpecimenUpload).filter(
            SpecimenUpload.submission_id == submission.id
        ).count()
        
        isf_count = db.query(ISFAnalyteStream).filter(
            ISFAnalyteStream.submission_id == submission.id
        ).count()
        
        vitals_count = db.query(VitalsRecord).filter(
            VitalsRecord.submission_id == submission.id
        ).count()
        
        has_soap = submission.full_payload_json and submission.full_payload_json.get("soap_profile")
        
        # Simple completeness score
        scores = []
        scores.append(1.0 if specimen_count > 0 else 0.0)
        scores.append(min(1.0, isf_count / 100.0) if isf_count > 0 else 0.0)
        scores.append(min(1.0, vitals_count / 5.0) if vitals_count > 0 else 0.0)
        scores.append(0.8 if has_soap else 0.0)
        
        overall_score = sum(scores) / len(scores)
        
        return {
            "submission_id": submission_id,
            "completeness_score": overall_score,
            "has_isf_monitor": isf_count > 0,
            "has_specimens": specimen_count > 0,
            "specimen_count": specimen_count,
            "has_vitals": vitals_count > 0,
            "has_soap": has_soap,
            "source": "on_the_fly",
            "note": "A2 analysis not run yet. Run A2 for detailed coverage metrics."
        }


@router.get("/gating-status/{submission_id}")
def get_submission_gating_status(
    submission_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get gating status for a specific submission.
    
    Returns eligibility for Part B and reasons.
    """
    summary_data = a2_orchestrator.get_summary(
        db=db,
        submission_id=submission_id,
        user_id=current_user.id
    )
    
    if not summary_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No A2 summary found for submission {submission_id}. Run A2 first."
        )
    
    gating = summary_data["gating"]
    
    return {
        "submission_id": submission_id,
        "eligible_for_part_b": gating["eligible_for_part_b"],
        "reasons": gating["reasons"],
        "stream_coverage": summary_data["stream_coverage"]
    }
