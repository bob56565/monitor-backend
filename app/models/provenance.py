"""
Provenance and Audit Trail Models

Additive database models for storing inference provenance and audit trails.
Enables full explainability and debugging of all computed outputs.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from app.db.base import Base


class InferenceProvenance(Base):
    """
    Audit trail for every inference output.
    
    Stores complete provenance: inputs used, methods applied, confidence
    computation, gating decisions, and timing. Enables debugging and
    explainability of all outputs shown to users.
    """
    __tablename__ = "inference_provenance"

    id = Column(Integer, primary_key=True, index=True)
    
    # Link to user and output
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    output_id = Column(String, nullable=False, index=True, comment="Unique ID for this inference output")
    
    # Output metadata
    panel_name = Column(String, nullable=False, index=True, comment="Panel name (e.g., 'metabolic', 'cardiovascular')")
    metric_name = Column(String, nullable=False, comment="Specific metric (e.g., 'a1c_estimate', 'glucose_mean')")
    output_type = Column(String, nullable=False, comment="'measured' or 'inferred'")
    
    # Time window
    time_window_start = Column(DateTime, nullable=True, comment="Start of data window used")
    time_window_end = Column(DateTime, nullable=True, comment="End of data window used")
    time_window_days = Column(Integer, nullable=True, comment="Days of data used")
    
    # Input chain (what went into this output)
    input_chain = Column(Text, nullable=False, comment="Human-readable: 'ISF glucose + lab A1c + SOAP diet'")
    raw_input_refs = Column(JSON, nullable=False, comment="Structured refs to source data IDs")
    derived_features = Column(JSON, nullable=True, comment="Intermediate computed features used")
    
    # Methodologies (max 4 per Part B spec)
    methodologies_used = Column(JSON, nullable=False, comment="List of up to 4 methodology strings")
    method_why = Column(Text, nullable=True, comment="Why these methods were chosen")
    
    # Confidence payload
    confidence_payload = Column(JSON, nullable=False, comment="Full confidence engine output")
    confidence_percent = Column(Float, nullable=False, index=True, comment="Final confidence %")
    
    # Gating payload
    gating_payload = Column(JSON, nullable=False, comment="Full gating engine output")
    gating_allowed = Column(String, nullable=False, comment="'allowed' or 'blocked' or 'wide_range'")
    
    # Output value (for reference)
    output_value = Column(Float, nullable=True, comment="Numeric output value if applicable")
    output_range_low = Column(Float, nullable=True, comment="Lower bound of range")
    output_range_high = Column(Float, nullable=True, comment="Upper bound of range")
    output_units = Column(String, nullable=True, comment="Units of output")
    
    # Schema version
    schema_version = Column(String, default="1.0.0", nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    computation_time_ms = Column(Integer, nullable=True, comment="Time taken to compute output")
    
    # Relationships
    user = relationship("User", backref="inference_provenances")


class ProvenanceHelper:
    """
    Helper class for writing provenance records.
    
    Provides a simplified interface for inference modules to log provenance.
    """
    
    @staticmethod
    def create_provenance_record(
        session,
        user_id: int,
        output_id: str,
        panel_name: str,
        metric_name: str,
        output_type: str,
        input_chain: str,
        raw_input_refs: dict,
        methodologies_used: list,
        confidence_payload: dict,
        gating_payload: dict,
        output_value: float = None,
        output_range_low: float = None,
        output_range_high: float = None,
        output_units: str = None,
        time_window_start: datetime = None,
        time_window_end: datetime = None,
        time_window_days: int = None,
        derived_features: dict = None,
        method_why: str = None,
        computation_time_ms: int = None
    ) -> InferenceProvenance:
        """
        Create and persist a provenance record.
        
        Args:
            session: SQLAlchemy session
            user_id: User ID
            output_id: Unique identifier for this output
            panel_name: Panel name (e.g., 'metabolic')
            metric_name: Metric name (e.g., 'a1c_estimate')
            output_type: 'measured' or 'inferred'
            input_chain: Human-readable input description
            raw_input_refs: Dict of source data IDs
            methodologies_used: List of up to 4 methodology strings
            confidence_payload: Full confidence engine output dict
            gating_payload: Full gating engine output dict
            output_value: Output numeric value (optional)
            output_range_low: Lower bound (optional)
            output_range_high: Upper bound (optional)
            output_units: Units (optional)
            time_window_start: Start datetime (optional)
            time_window_end: End datetime (optional)
            time_window_days: Days of data (optional)
            derived_features: Intermediate features (optional)
            method_why: Method selection rationale (optional)
            computation_time_ms: Computation time (optional)
        
        Returns:
            Created InferenceProvenance record
        """
        # Extract summary fields from payloads
        confidence_percent = confidence_payload.get('confidence_percent', 0.0)
        gating_allowed = gating_payload.get('recommended_range_width', 'unknown')
        
        provenance = InferenceProvenance(
            user_id=user_id,
            output_id=output_id,
            panel_name=panel_name,
            metric_name=metric_name,
            output_type=output_type,
            time_window_start=time_window_start,
            time_window_end=time_window_end,
            time_window_days=time_window_days,
            input_chain=input_chain,
            raw_input_refs=raw_input_refs,
            derived_features=derived_features,
            methodologies_used=methodologies_used[:4],  # Cap at 4
            method_why=method_why,
            confidence_payload=confidence_payload,
            confidence_percent=confidence_percent,
            gating_payload=gating_payload,
            gating_allowed=gating_allowed,
            output_value=output_value,
            output_range_low=output_range_low,
            output_range_high=output_range_high,
            output_units=output_units,
            computation_time_ms=computation_time_ms
        )
        
        session.add(provenance)
        session.flush()  # Get ID without committing
        
        return provenance
    
    @staticmethod
    def get_user_provenance_records(
        session,
        user_id: int,
        panel_name: str = None,
        limit: int = 100
    ) -> list:
        """
        Retrieve provenance records for a user.
        
        Args:
            session: SQLAlchemy session
            user_id: User ID
            panel_name: Optional filter by panel
            limit: Max records to return
        
        Returns:
            List of InferenceProvenance records
        """
        query = session.query(InferenceProvenance).filter(
            InferenceProvenance.user_id == user_id
        )
        
        if panel_name:
            query = query.filter(InferenceProvenance.panel_name == panel_name)
        
        query = query.order_by(InferenceProvenance.created_at.desc())
        query = query.limit(limit)
        
        return query.all()
