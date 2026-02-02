"""
A2 Processing Database Models

Persistence layer for A2 data quality analysis, orchestration, and canonical summaries.
Additive-only, non-breaking extension to existing schema.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Text, JSON, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.db.base import Base
import enum


class A2StatusEnum(str, enum.Enum):
    """A2 run status states."""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class A2Run(Base):
    """A2 orchestration run record - tracks status and lifecycle of A2 analysis."""
    __tablename__ = "a2_runs"

    id = Column(Integer, primary_key=True, index=True)
    a2_run_id = Column(String, unique=True, index=True, nullable=False, comment="UUID for this A2 run")
    submission_id = Column(String, ForeignKey("part_a_submissions.submission_id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Status tracking
    status = Column(SQLEnum(A2StatusEnum), default=A2StatusEnum.QUEUED, nullable=False, index=True)
    progress = Column(Float, default=0.0, nullable=False, comment="Progress 0.0-1.0")
    error_message = Column(Text, nullable=True, comment="Error detail if failed")
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Metadata
    triggered_by = Column(String, default="auto", comment="auto/manual/retry")
    superseded = Column(Boolean, default=False, comment="True if superseded by a newer run")
    computation_time_ms = Column(Integer, nullable=True)
    
    # Relationships
    summary = relationship("A2Summary", back_populates="run", uselist=False, cascade="all, delete-orphan")
    user = relationship("User", backref="a2_runs")


class A2Summary(Base):
    """Canonical A2 Summary record - the single source of truth for A2 results."""
    __tablename__ = "a2_summaries"

    id = Column(Integer, primary_key=True, index=True)
    a2_run_id = Column(String, ForeignKey("a2_runs.a2_run_id"), unique=True, nullable=False, index=True)
    submission_id = Column(String, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Stream coverage (days_covered, missing_rate, last_seen_ts, quality_score per stream)
    stream_coverage = Column(JSON, nullable=False, comment="Coverage per stream: glucose, lactate, vitals, sleep, pros, labs")
    
    # Gating (eligible_for_part_b + reasons)
    gating = Column(JSON, nullable=False, comment="Eligibility for Part B and reasons")
    
    # Priors and decay
    priors_used = Column(JSON, nullable=False, comment="Priors applied during A2")
    prior_decay_state = Column(JSON, nullable=False, comment="Prior decay status")
    
    # Conflict detection
    conflict_flags = Column(JSON, nullable=False, comment="Detected conflicts between inputs")
    
    # Derived features
    derived_features_count = Column(Integer, default=0, nullable=False)
    derived_features_detail = Column(JSON, nullable=True, comment="Details of derived calculators")
    
    # Anchor strength by domain
    anchor_strength_by_domain = Column(JSON, nullable=False, comment="Anchor strength: metabolic, cardio, renal, inflammation, nutrition, other")
    
    # Confidence caps
    confidence_distribution = Column(JSON, nullable=True, comment="A/B/C/D grade distribution")
    
    # Metadata
    schema_version = Column(String, default="1.0.0", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    run = relationship("A2Run", back_populates="summary")
    user = relationship("User", backref="a2_summaries")


class A2Artifact(Base):
    """A2 artifact records - completeness check and other intermediate artifacts."""
    __tablename__ = "a2_artifacts"

    id = Column(Integer, primary_key=True, index=True)
    a2_run_id = Column(String, ForeignKey("a2_runs.a2_run_id"), nullable=False, index=True)
    submission_id = Column(String, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    artifact_type = Column(String, nullable=False, index=True, comment="completeness_check/coverage_analysis/gating_result/etc")
    artifact_data = Column(JSON, nullable=False, comment="Structured artifact payload")
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", backref="a2_artifacts")
