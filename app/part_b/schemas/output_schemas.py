"""
Part B Output Schemas (Version 1.0.0)

Data contracts for all Part B inference outputs with required mechanics:
- Measured vs inferred label
- Value as score or tight range
- Confidence % + top 3 drivers
- What increases confidence
- Safe action suggestion
- Input chain (X+Y+Z from Part A only)
- Methodologies used (max 4)
"""

from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any, Literal
from enum import Enum
from datetime import datetime


class OutputFrequency(str, Enum):
    """Frequency of output generation."""
    REALTIME = "realtime"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class OutputStatus(str, Enum):
    """Status of output generation."""
    SUCCESS = "success"
    INSUFFICIENT_DATA = "insufficient_data"
    GATING_BLOCKED = "gating_blocked"
    ERROR = "error"


class OutputLineItem(BaseModel):
    """
    Single line item in Part B report.
    Includes all non-negotiable report mechanics.
    """
    # Identification
    output_id: str = Field(..., description="Unique ID for this output")
    metric_name: str = Field(..., description="Name of the metric")
    panel_name: str = Field(..., description="Panel this belongs to (e.g., 'metabolic_regulation')")
    frequency: OutputFrequency = Field(..., description="Frequency of this output")
    
    # Required mechanics
    measured_vs_inferred: Literal["measured", "inferred", "inferred_tight", "inferred_wide"] = Field(
        ..., description="Whether value is measured (uploaded) or inferred"
    )
    
    # Value (one of these must be present)
    value_score: Optional[float] = Field(None, description="Score value (0-100 or similar)")
    value_range_low: Optional[float] = Field(None, description="Lower bound of range")
    value_range_high: Optional[float] = Field(None, description="Upper bound of range")
    value_class: Optional[str] = Field(None, description="Classification value (e.g., 'improving/stable/worsening')")
    units: Optional[str] = Field(None, description="Units for the value")
    
    # Confidence
    confidence_percent: float = Field(..., ge=0, le=100, description="Confidence score 0-100%")
    confidence_top_3_drivers: List[tuple[str, str]] = Field(
        ..., max_length=3,
        description="Top 3 drivers of confidence: [(description, impact_level), ...]. Impact: high/medium/low"
    )
    what_increases_confidence: List[str] = Field(
        ..., description="Actionable steps to increase confidence (e.g., 'upload lipid panel')"
    )
    
    # Safe action suggestion
    safe_action_suggestion: str = Field(
        ..., description="Safe, non-diagnostic action suggestion"
    )
    
    # Input chain (Part A only)
    input_chain: str = Field(
        ..., description="Human-readable X+Y+Z chain using ONLY Part A inputs"
    )
    input_references: Dict[str, Any] = Field(
        ..., description="Structured references to Part A data sources"
    )
    
    # Methodologies (max 4)
    methodologies_used: List[str] = Field(
        ..., max_length=4,
        description="Methods used (max 4), in order of application"
    )
    method_why: List[str] = Field(
        ..., max_length=4,
        description="Why each method was used (same length as methodologies_used)"
    )
    
    # Metadata
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    status: OutputStatus = Field(OutputStatus.SUCCESS)
    schema_version: str = Field("1.0.0")
    
    # Gating and provenance payloads (for audit)
    gating_payload: Optional[Dict] = Field(None, description="Full gating check result")
    confidence_payload: Optional[Dict] = Field(None, description="Full confidence compute result")
    provenance_id: Optional[int] = Field(None, description="ID of provenance record in DB")
    
    @field_validator('methodologies_used')
    @classmethod
    def validate_max_four_methods(cls, v):
        if len(v) > 4:
            raise ValueError("Maximum 4 methodologies allowed per output")
        return v
    
    @field_validator('method_why')
    @classmethod
    def validate_method_why_length(cls, v, info):
        methodologies = info.data.get('methodologies_used', [])
        if len(v) != len(methodologies):
            raise ValueError("method_why must have same length as methodologies_used")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "output_id": "metabolic_a1c_20260129_001",
                "metric_name": "estimated_hba1c_range",
                "panel_name": "metabolic_regulation",
                "frequency": "weekly",
                "measured_vs_inferred": "inferred_tight",
                "value_range_low": 5.4,
                "value_range_high": 5.8,
                "units": "%",
                "confidence_percent": 82.5,
                "confidence_top_3_drivers": [
                    ("Recent HbA1c lab anchor (60 days old)", "high"),
                    ("30 days of ISF glucose data", "high"),
                    ("Good sensor quality (0.85)", "medium")
                ],
                "what_increases_confidence": [
                    "Upload more recent HbA1c lab (<30 days)",
                    "Continue monitoring for 14+ more days"
                ],
                "safe_action_suggestion": "Consider confirmatory HbA1c lab if value is outside expected range or trending upward",
                "input_chain": "ISF glucose (30d) + prior HbA1c lab (60d) + age + diet pattern (SOAP)",
                "input_references": {
                    "isf_stream_ids": [123],
                    "specimen_upload_ids": [456],
                    "soap_profile_id": 789
                },
                "methodologies_used": [
                    "GMI-style regression (glucose → HbA1c)",
                    "Bayesian calibration to prior HbA1c",
                    "Time-series smoothing (Kalman filter)",
                    "Constraint rules (RBC turnover modifiers)"
                ],
                "method_why": [
                    "Strongest validated backbone for CGM-like data",
                    "Forces realism + personalized correction",
                    "Reduces sensor noise/drift impact",
                    "Prevents systematic bias from anemia/CKD"
                ]
            }
        }


class PanelSection(BaseModel):
    """Section/subcategory within a panel."""
    panel_name: str
    panel_display_name: str
    outputs: List[OutputLineItem]
    summary_notes: Optional[str] = None


class PartBReport(BaseModel):
    """
    Complete Part B report for a user.
    Panel-structured with all 7 major sections.
    Phase-aware: references specific A2 run and includes A2 header block.
    """
    report_id: str = Field(..., description="Unique report ID")
    user_id: int
    submission_id: str = Field(..., description="Part A submission ID this report is based on")
    
    # A2 Phase-Awareness (required)
    a2_run_id: str = Field(..., description="A2 run ID this report references")
    a2_header_block: Dict[str, Any] = Field(
        ..., description="A2 snapshot: status, coverage, conflicts, anchor strength"
    )
    
    # Time window
    report_generated_at: datetime = Field(default_factory=datetime.utcnow)
    data_window_start: datetime
    data_window_end: datetime
    
    # Panels (7 major sections)
    metabolic_regulation: PanelSection
    lipid_cardiometabolic: PanelSection
    micronutrient_vitamin: PanelSection
    inflammatory_immune: PanelSection
    endocrine_neurohormonal: PanelSection
    renal_hydration: PanelSection
    comprehensive_integrated: PanelSection
    
    # Overall metadata
    schema_version: str = Field("1.0.0")
    total_outputs: int = Field(..., description="Total number of output line items")
    successful_outputs: int
    insufficient_data_outputs: int
    average_confidence: float = Field(..., ge=0, le=100)
    
    # Data quality summary
    data_quality_summary: Dict[str, Any] = Field(
        ..., description="Summary of Part A data completeness"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "report_id": "partb_user123_20260129",
                "user_id": 123,
                "submission_id": "parta_sub_20260129_001",
                "report_generated_at": "2026-01-29T10:00:00Z",
                "data_window_start": "2026-01-01T00:00:00Z",
                "data_window_end": "2026-01-29T23:59:59Z",
                "schema_version": "1.0.0",
                "total_outputs": 35,
                "successful_outputs": 30,
                "insufficient_data_outputs": 5,
                "average_confidence": 78.2
            }
        }


class InsufficientDataResponse(BaseModel):
    """Response when gating blocks an output due to insufficient data."""
    status: Literal["insufficient_data"] = "insufficient_data"
    metric_name: str
    panel_name: str
    reasons: List[str] = Field(..., description="Why output was blocked")
    remediation: List[str] = Field(..., description="Steps to fix the issue")
    required_minimums: Dict[str, Any] = Field(
        ..., description="Required minimum data windows/quality"
    )


class PartBGenerationRequest(BaseModel):
    """Request to generate Part B report."""
    submission_id: str = Field(..., description="Part A submission ID")
    time_window_days: Optional[int] = Field(30, ge=1, le=365, description="Days of data to use")
    frequency_filter: Optional[List[OutputFrequency]] = Field(
        None, description="Filter to specific frequencies (e.g., weekly only)"
    )
    panel_filter: Optional[List[str]] = Field(
        None, description="Filter to specific panels"
    )


class PartBGenerationResponse(BaseModel):
    """Response for Part B report generation."""
    status: Literal["success", "partial", "error"]
    report: Optional[PartBReport] = None
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    generation_time_ms: int
