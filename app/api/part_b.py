"""
Part B API Endpoints

RESTful endpoints for generating and retrieving Part B inference reports.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.part_b.schemas.output_schemas import (
    PartBGenerationRequest,
    PartBGenerationResponse,
    PartBReport
)
from app.part_b.orchestrator import PartBOrchestrator

router = APIRouter(prefix="/part-b", tags=["Part B Reports"])


@router.post("/generate", response_model=PartBGenerationResponse)
def generate_part_b_report(
    request: PartBGenerationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Generate Part B inference report from Part A submission.
    
    **Safety Guard (Non-Breaking)**:
    - Additive endpoint only (does not modify Part A)
    - Uses ONLY Part A stored inputs
    - Integrates A2 gating → compute → confidence → provenance workflow
    
    **Workflow**:
    1. Validate Part A submission exists and meets minimums
    2. For each output: call A2 gating first
    3. If allowed: compute output
    4. Call A2 confidence engine
    5. Persist provenance record
    6. Return structured report
    
    **Returns**:
    - Full Part B report with 7 panel sections
    - Each output includes: measured/inferred label, value, confidence %, 
      top 3 drivers, improvement suggestions, safe action, input chain, methods (≤4)
    - Gating blocked outputs return "insufficient_data" with remediation steps
    """
    try:
        response = PartBOrchestrator.generate_report(
            db=db,
            user_id=current_user.id,
            request=request
        )
        
        return response
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating Part B report: {str(e)}"
        )


@router.get("/report/{submission_id}", response_model=Optional[PartBReport])
def get_part_b_report(
    submission_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve most recent Part B report for a submission (future: store in DB).
    
    Note: Current implementation regenerates on-demand.
    Future: Store reports in database for historical tracking.
    """
    # For now, regenerate the report
    # Future: Query stored reports from database
    request = PartBGenerationRequest(submission_id=submission_id)
    
    response = PartBOrchestrator.generate_report(
        db=db,
        user_id=current_user.id,
        request=request
    )
    
    if response.status == "error":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Could not generate report: {', '.join(response.errors)}"
        )
    
    return response.report
