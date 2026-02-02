from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Text, JSON
from sqlalchemy.orm import relationship
from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=True)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    raw_sensor_data = relationship("RawSensorData", back_populates="user")
    calibrated_features = relationship("CalibratedFeatures", back_populates="user")
    inference_results = relationship("InferenceResult", back_populates="user")


class RawSensorData(Base):
    __tablename__ = "raw_sensor_data"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    sensor_value_1 = Column(Float, nullable=False)
    sensor_value_2 = Column(Float, nullable=False)
    sensor_value_3 = Column(Float, nullable=False)
    raw_data = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="raw_sensor_data")


class CalibratedFeatures(Base):
    __tablename__ = "calibrated_features"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    raw_sensor_id = Column(Integer, ForeignKey("raw_sensor_data.id"), nullable=True)
    feature_1 = Column(Float, nullable=False)
    feature_2 = Column(Float, nullable=False)
    feature_3 = Column(Float, nullable=False)
    derived_metric = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # M7 Part 2: feature_pack_v2 storage (non-breaking)
    feature_pack_v2 = Column(JSON, nullable=True)  # Stores FeaturePackV2 as JSON
    run_v2_id = Column(String, nullable=True)  # Link to RunV2 if generated from it

    user = relationship("User", back_populates="calibrated_features")


class InferenceResult(Base):
    __tablename__ = "inference_results"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    calibrated_feature_id = Column(Integer, ForeignKey("calibrated_features.id"), nullable=True)
    prediction = Column(Float, nullable=False)
    confidence = Column(Float, nullable=False)
    uncertainty = Column(Float, nullable=False)
    inference_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="inference_results")


class RunV2Record(Base):
    """
    Non-breaking storage for RunV2 payloads.
    Contains multi-specimen ingestion + non-lab inputs + qual encoding outputs.
    """
    __tablename__ = "runs_v2"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    timezone = Column(String, default="UTC")
    legacy_raw_id = Column(Integer, ForeignKey("raw_sensor_data.id"), nullable=True)
    
    # Full RunV2 payload stored as JSON
    payload = Column(JSON, nullable=False)
    
    # Indexed fields for efficient queries
    schema_version = Column(String, default="runv2.1")
    specimen_count = Column(Integer, default=0)
    
    user = relationship("User")
    legacy_raw = relationship("RawSensorData")
