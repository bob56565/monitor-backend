"""
PART A Database Models
Additive-only database models for storing all PART A raw data inputs.
Non-breaking extension to existing schema.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Text, JSON, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.db.base import Base
import enum


class SubmissionStatusEnum(str, enum.Enum):
    """Status of a PART A submission."""
    DRAFT = "draft"
    SUBMITTED = "submitted"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class PartASubmission(Base):
    """Master table for PART A submissions."""
    __tablename__ = "part_a_submissions"

    id = Column(Integer, primary_key=True, index=True)
    submission_id = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    schema_version = Column(String, default="1.0.0", nullable=False)
    status = Column(SQLEnum(SubmissionStatusEnum), default=SubmissionStatusEnum.DRAFT, nullable=False)
    submission_timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # JSON storage for complete schema-validated data
    full_payload_json = Column(JSON, nullable=True, comment="Complete PartAInputSchema JSON")
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    processing_notes = Column(Text, nullable=True)
    validation_errors = Column(JSON, nullable=True)

    # Relationships
    user = relationship("User", backref="part_a_submissions")
    specimen_uploads = relationship("SpecimenUpload", back_populates="submission", cascade="all, delete-orphan")
    isf_streams = relationship("ISFAnalyteStream", back_populates="submission", cascade="all, delete-orphan")
    vitals_records = relationship("VitalsRecord", back_populates="submission", cascade="all, delete-orphan")
    soap_profiles = relationship("SOAPProfileRecord", back_populates="submission", cascade="all, delete-orphan")
    encoding_records = relationship("QualitativeEncodingRecord", back_populates="submission", cascade="all, delete-orphan")


class SpecimenUpload(Base):
    """Individual specimen upload (blood, saliva, sweat, urine, imaging)."""
    __tablename__ = "specimen_uploads"

    id = Column(Integer, primary_key=True, index=True)
    submission_id = Column(Integer, ForeignKey("part_a_submissions.id"), nullable=False)
    
    modality = Column(String, nullable=False, index=True, comment="blood/saliva/sweat/urine/imaging")
    collection_datetime = Column(DateTime, nullable=True)
    source_format = Column(String, nullable=False, comment="pdf/image/hl7/fhir/csv/manual_entry")
    
    # Raw artifact storage
    raw_artifact_path = Column(String, nullable=True, comment="Path to stored file in artifact storage")
    raw_artifact_hash = Column(String, nullable=True, comment="SHA256 hash for integrity")
    raw_artifact_size_bytes = Column(Integer, nullable=True)
    
    # Parsed data (JSON)
    parsed_data_json = Column(JSON, nullable=True, comment="Parsed structured data")
    parsing_status = Column(String, default="pending", comment="pending/success/failed/partial")
    parsing_errors = Column(JSON, nullable=True)
    parsing_notes = Column(Text, nullable=True)
    
    # Metadata
    lab_name = Column(String, nullable=True)
    lab_id = Column(String, nullable=True)
    fasting_status = Column(String, nullable=True, comment="fasting/non_fasting/unknown")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    submission = relationship("PartASubmission", back_populates="specimen_uploads")
    analytes = relationship("SpecimenAnalyte", back_populates="upload", cascade="all, delete-orphan")


class SpecimenAnalyte(Base):
    """Individual analyte value from a specimen."""
    __tablename__ = "specimen_analytes"

    id = Column(Integer, primary_key=True, index=True)
    upload_id = Column(Integer, ForeignKey("specimen_uploads.id"), nullable=False)
    
    name = Column(String, nullable=False, index=True, comment="glucose, sodium_na, WBC, etc.")
    value = Column(Float, nullable=True)
    value_string = Column(String, nullable=True, comment="For qualitative results")
    unit = Column(String, nullable=True)
    
    reference_range_low = Column(Float, nullable=True)
    reference_range_high = Column(Float, nullable=True)
    reference_range_text = Column(String, nullable=True)
    
    flag = Column(String, nullable=True, comment="H/L/Critical/Normal")
    method = Column(String, nullable=True)
    timestamp = Column(DateTime, nullable=True, comment="For time-specific analytes like cortisol")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    upload = relationship("SpecimenUpload", back_populates="analytes")


class ISFAnalyteStream(Base):
    """Time-series stream for ISF monitor data (A2)."""
    __tablename__ = "isf_analyte_streams"

    id = Column(Integer, primary_key=True, index=True)
    submission_id = Column(Integer, ForeignKey("part_a_submissions.id"), nullable=False)
    
    name = Column(String, nullable=False, index=True, comment="glucose, lactate, sodium_na, potassium_k, etc.")
    unit = Column(String, nullable=False)
    device_id = Column(String, nullable=True)
    sensor_type = Column(String, nullable=True)
    
    # Time-series data (JSON arrays)
    values_json = Column(JSON, nullable=False, comment="Array of float values")
    timestamps_json = Column(JSON, nullable=False, comment="Array of ISO timestamps")
    
    # Signal quality
    calibration_status = Column(String, nullable=True)
    sensor_drift_score = Column(Float, nullable=True)
    noise_score = Column(Float, nullable=True)
    dropout_percentage = Column(Float, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    submission = relationship("PartASubmission", back_populates="isf_streams")


class VitalsRecord(Base):
    """Vitals data record (A3)."""
    __tablename__ = "vitals_records"

    id = Column(Integer, primary_key=True, index=True)
    submission_id = Column(Integer, ForeignKey("part_a_submissions.id"), nullable=False)
    
    # Store complete vitals as JSON (flexible for various vitals types)
    cardiovascular_json = Column(JSON, nullable=True)
    respiratory_temperature_json = Column(JSON, nullable=True)
    sleep_recovery_activity_json = Column(JSON, nullable=True)
    
    baseline_learning_days = Column(Integer, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    submission = relationship("PartASubmission", back_populates="vitals_records")


class SOAPProfileRecord(Base):
    """SOAP-note health profile (A4)."""
    __tablename__ = "soap_profile_records"

    id = Column(Integer, primary_key=True, index=True)
    submission_id = Column(Integer, ForeignKey("part_a_submissions.id"), nullable=False)
    
    # Demographics (structured fields for common queries)
    age = Column(Integer, nullable=True)
    sex_at_birth = Column(String, nullable=True)
    height_cm = Column(Float, nullable=True)
    weight_kg = Column(Float, nullable=True)
    bmi = Column(Float, nullable=True)
    
    # Complete SOAP data as JSON
    demographics_anthropometrics_json = Column(JSON, nullable=True)
    medical_history_json = Column(JSON, nullable=True)
    medications_supplements_json = Column(JSON, nullable=True)
    diet_json = Column(JSON, nullable=True)
    activity_lifestyle_json = Column(JSON, nullable=True)
    symptoms_json = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    submission = relationship("PartASubmission", back_populates="soap_profiles")


class QualitativeEncodingRecord(Base):
    """Qualitative-to-quantitative encoding results (A5)."""
    __tablename__ = "qualitative_encoding_records"

    id = Column(Integer, primary_key=True, index=True)
    submission_id = Column(Integer, ForeignKey("part_a_submissions.id"), nullable=False)
    
    # Individual encoding rule application
    input_field = Column(String, nullable=False, index=True)
    input_value = Column(String, nullable=False)
    standardized_code = Column(String, nullable=False, index=True)
    numeric_weight = Column(Float, nullable=False)
    time_window = Column(String, nullable=False, comment="acute/chronic")
    
    # Direction of effect (JSON dictionary)
    direction_of_effect_json = Column(JSON, nullable=False)
    
    notes = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    submission = relationship("PartASubmission", back_populates="encoding_records")


# ============================================================================
# ADD TO app/models/__init__.py IMPORTS (NON-BREAKING)
# ============================================================================
# These models extend the existing schema and are imported in models/__init__.py
