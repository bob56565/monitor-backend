"""
Data Quality API Endpoints

Additive API endpoints for surfacing data completeness, quality summaries,
and confidence improvement recommendations to the UI.

These endpoints do NOT implement Part B outputs - they only provide
scaffolding for data quality assessment.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional, Dict
from datetime import datetime, timedelta
from pydantic import BaseModel, Field

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.part_a_models import PartASubmission, SpecimenUpload, ISFAnalyteStream, VitalsRecord
from app.services.confidence import confidence_engine
from app.services.priors import priors_service


router = APIRouter(prefix="/data-quality", tags=["data-quality"])


# Response schemas
class CompletenessScore(BaseModel):
    """Data completeness breakdown."""
    overall_score: float = Field(..., ge=0.0, le=1.0, description="Overall completeness (0-1)")
    component_scores: Dict[str, float] = Field(..., description="Scores by component")
    missing_critical: List[str] = Field(..., description="List of missing critical items")


class DataQualitySummary(BaseModel):
    """Comprehensive data quality summary."""
    completeness: CompletenessScore
    data_counts: Dict[str, int] = Field(..., description="Counts of data by type")
    most_recent_data: Dict[str, Optional[str]] = Field(..., description="Most recent data timestamps by type")
    sensor_quality: Optional[Dict[str, float]] = Field(None, description="Sensor quality metrics if available")
    recommendations: List[str] = Field(..., description="Top recommendations to improve data quality")


class AnchorSummary(BaseModel):
    """Summary of available anchor data (uploaded labs)."""
    has_blood: bool = Field(..., description="Has blood panel uploads")
    blood_count: int = Field(..., description="Number of blood uploads")
    most_recent_blood: Optional[str] = Field(None, description="Most recent blood upload timestamp")
    blood_types: List[str] = Field(..., description="Types of blood panels uploaded")
    
    has_urine: bool = Field(..., description="Has urine specimen uploads")
    urine_count: int = Field(..., description="Number of urine uploads")
    
    has_saliva: bool = Field(..., description="Has saliva specimen uploads")
    saliva_count: int = Field(..., description="Number of saliva uploads")
    
    has_sweat: bool = Field(..., description="Has sweat specimen uploads")
    sweat_count: int = Field(..., description="Number of sweat uploads")
    
    total_anchors: int = Field(..., description="Total anchor data points")


class RecommendationItem(BaseModel):
    """Actionable recommendation to improve confidence."""
    priority: str = Field(..., description="Priority: 'high', 'medium', 'low'")
    category: str = Field(..., description="Category: 'completeness', 'recency', 'quality', 'anchors'")
    title: str = Field(..., description="Short title")
    description: str = Field(..., description="Detailed description")
    expected_impact: str = Field(..., description="Expected confidence improvement")


# Endpoints

@router.get("/completeness", response_model=CompletenessScore)
def get_data_completeness(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get data completeness score for current user.
    
    Returns breakdown of completeness by component (specimens, ISF, vitals, SOAP)
    and list of missing critical items.
    """
    # Count data by type
    specimen_count = db.query(SpecimenUpload).filter(
        SpecimenUpload.user_id == current_user.id
    ).count()
    
    isf_streams = db.query(ISFAnalyteStream).filter(
        ISFAnalyteStream.user_id == current_user.id
    ).all()
    isf_days = len(set(s.timestamp.date() for s in isf_streams if s.timestamp)) if isf_streams else 0
    
    vitals_count = db.query(VitalsRecord).filter(
        VitalsRecord.user_id == current_user.id
    ).count()
    
    # Check for SOAP profile (from PART A submissions)
    soap_submissions = db.query(PartASubmission).filter(
        PartASubmission.user_id == current_user.id,
        PartASubmission.full_payload_json.isnot(None)
    ).all()
    has_soap = any(
        s.full_payload_json and s.full_payload_json.get('soap_profile')
        for s in soap_submissions
    )
    soap_completeness = 0.8 if has_soap else 0.0  # Simplified
    
    # Compute completeness
    completeness = confidence_engine.compute_data_completeness(
        has_specimen_uploads=(specimen_count > 0),
        specimen_count=specimen_count,
        has_isf_monitor=(isf_days > 0),
        isf_days=isf_days,
        has_vitals=(vitals_count > 0),
        vitals_count=vitals_count,
        has_soap_profile=has_soap,
        soap_completeness=soap_completeness
    )
    
    return CompletenessScore(
        overall_score=completeness['completeness_score'],
        component_scores=completeness['component_scores'],
        missing_critical=completeness['missing_critical']
    )


@router.get("/summary", response_model=DataQualitySummary)
def get_data_quality_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive data quality summary for current user.
    
    Includes completeness, data counts, recency, and recommendations.
    """
    # Get completeness
    completeness = get_data_completeness(current_user, db)
    
    # Count data by type
    specimen_count = db.query(SpecimenUpload).filter(
        SpecimenUpload.user_id == current_user.id
    ).count()
    
    isf_count = db.query(ISFAnalyteStream).filter(
        ISFAnalyteStream.user_id == current_user.id
    ).count()
    
    vitals_count = db.query(VitalsRecord).filter(
        VitalsRecord.user_id == current_user.id
    ).count()
    
    submission_count = db.query(PartASubmission).filter(
        PartASubmission.user_id == current_user.id
    ).count()
    
    # Find most recent data
    most_recent_specimen = db.query(SpecimenUpload).filter(
        SpecimenUpload.user_id == current_user.id
    ).order_by(SpecimenUpload.upload_timestamp.desc()).first()
    
    most_recent_isf = db.query(ISFAnalyteStream).filter(
        ISFAnalyteStream.user_id == current_user.id
    ).order_by(ISFAnalyteStream.timestamp.desc()).first()
    
    most_recent_vitals = db.query(VitalsRecord).filter(
        VitalsRecord.user_id == current_user.id
    ).order_by(VitalsRecord.timestamp.desc()).first()
    
    # Generate recommendations
    recommendations = _generate_recommendations(
        completeness=completeness.overall_score,
        missing_critical=completeness.missing_critical,
        specimen_count=specimen_count,
        isf_count=isf_count,
        vitals_count=vitals_count,
        most_recent_specimen=most_recent_specimen,
        most_recent_isf=most_recent_isf
    )
    
    return DataQualitySummary(
        completeness=completeness,
        data_counts={
            "specimens": specimen_count,
            "isf_readings": isf_count,
            "vitals": vitals_count,
            "submissions": submission_count
        },
        most_recent_data={
            "specimen": most_recent_specimen.upload_timestamp.isoformat() if most_recent_specimen else None,
            "isf": most_recent_isf.timestamp.isoformat() if most_recent_isf else None,
            "vitals": most_recent_vitals.timestamp.isoformat() if most_recent_vitals else None
        },
        sensor_quality=None,  # To be implemented with actual sensor data
        recommendations=recommendations
    )


@router.get("/anchors", response_model=AnchorSummary)
def get_available_anchors(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get summary of available anchor data (uploaded lab results).
    
    Anchor data is critical for tight-range estimates in Part B.
    """
    # Query specimens by type
    specimens = db.query(SpecimenUpload).filter(
        SpecimenUpload.user_id == current_user.id
    ).all()
    
    blood_specimens = [s for s in specimens if s.specimen_type == 'blood']
    urine_specimens = [s for s in specimens if s.specimen_type == 'urine']
    saliva_specimens = [s for s in specimens if s.specimen_type == 'saliva']
    sweat_specimens = [s for s in specimens if s.specimen_type == 'sweat']
    
    # Identify blood panel types
    blood_types = []
    for s in blood_specimens:
        if s.parsed_data and 'panel_types' in s.parsed_data:
            blood_types.extend(s.parsed_data['panel_types'])
    blood_types = list(set(blood_types))
    
    # Most recent blood
    most_recent_blood = max(
        (s.upload_timestamp for s in blood_specimens),
        default=None
    )
    
    return AnchorSummary(
        has_blood=len(blood_specimens) > 0,
        blood_count=len(blood_specimens),
        most_recent_blood=most_recent_blood.isoformat() if most_recent_blood else None,
        blood_types=blood_types,
        has_urine=len(urine_specimens) > 0,
        urine_count=len(urine_specimens),
        has_saliva=len(saliva_specimens) > 0,
        saliva_count=len(saliva_specimens),
        has_sweat=len(sweat_specimens) > 0,
        sweat_count=len(sweat_specimens),
        total_anchors=len(specimens)
    )


@router.get("/recommendations", response_model=List[RecommendationItem])
def get_recommendations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get prioritized recommendations to improve data quality and confidence.
    
    Returns actionable steps ranked by expected impact.
    """
    # Get current state
    completeness = get_data_completeness(current_user, db)
    anchors = get_available_anchors(current_user, db)
    
    # Build prioritized recommendations
    recommendations = []
    
    # High priority: Missing critical anchors
    if not anchors.has_blood:
        recommendations.append(RecommendationItem(
            priority="high",
            category="anchors",
            title="Upload Blood Panel",
            description="Upload a recent blood panel (CMP, CBC, or lipid) to enable tight-range estimates for glucose, cholesterol, and kidney function.",
            expected_impact="+15-20% confidence on metabolic outputs"
        ))
    
    # High priority: Insufficient monitoring duration
    if completeness.component_scores.get('isf_monitor', 0) < 0.5:
        recommendations.append(RecommendationItem(
            priority="high",
            category="completeness",
            title="Collect More ISF Monitor Data",
            description="Continue ISF monitoring for at least 14 days to enable stable glucose and A1c estimates.",
            expected_impact="+10-15% confidence on glucose outputs"
        ))
    
    # Medium priority: Missing vitals
    if completeness.component_scores.get('vitals', 0) < 0.5:
        recommendations.append(RecommendationItem(
            priority="medium",
            category="completeness",
            title="Add Vital Signs",
            description="Record blood pressure, heart rate, and weight measurements to improve cardiovascular risk assessment.",
            expected_impact="+8-12% confidence on cardiovascular outputs"
        ))
    
    # Medium priority: Older anchor data
    if anchors.has_blood and anchors.most_recent_blood:
        days_old = (datetime.utcnow() - datetime.fromisoformat(anchors.most_recent_blood.replace('Z', '+00:00'))).days
        if days_old > 90:
            recommendations.append(RecommendationItem(
                priority="medium",
                category="recency",
                title="Update Blood Panel",
                description=f"Your blood panel is {days_old} days old. Upload a recent panel for improved accuracy.",
                expected_impact="+5-10% confidence on anchored outputs"
            ))
    
    # Low priority: SOAP profile completeness
    if completeness.component_scores.get('soap_profile', 0) < 0.7:
        recommendations.append(RecommendationItem(
            priority="low",
            category="completeness",
            title="Complete Health Profile",
            description="Fill in medical history, medications, and lifestyle factors to improve risk stratification.",
            expected_impact="+3-5% confidence on all outputs"
        ))
    
    return recommendations


# Helper functions

def _generate_recommendations(
    completeness: float,
    missing_critical: List[str],
    specimen_count: int,
    isf_count: int,
    vitals_count: int,
    most_recent_specimen,
    most_recent_isf
) -> List[str]:
    """Generate simple recommendation strings."""
    recommendations = []
    
    if completeness < 0.5:
        recommendations.append("Upload critical missing data to reach 50% completeness")
    
    if specimen_count == 0:
        recommendations.append("Upload your first blood panel to enable anchored estimates")
    
    if isf_count < 100:  # ~7 days at 15-min intervals
        recommendations.append("Collect 7+ days of ISF monitoring for stable baselines")
    
    if vitals_count < 5:
        recommendations.append("Record vital signs regularly (BP, HR, weight)")
    
    if most_recent_specimen and (datetime.utcnow() - most_recent_specimen.upload_timestamp).days > 90:
        recommendations.append("Update blood panel (current is >90 days old)")
    
    return recommendations[:5]  # Top 5
