"""
Unit Normalization and Reference Intervals Module.

Implements Requirement A2.2: Unit and reference normalization.
- Stores raw_value + raw_unit exactly as received
- Stores std_value + std_unit using canonical internal units
- Attaches stratified reference intervals (age, sex, pregnancy, BMI band)
- Normalization is deterministic and reversible
- Existing calculations continue to function unchanged (additive only)
"""

from typing import Dict, Optional, Tuple, Any
from enum import Enum
from pydantic import BaseModel, Field
import logging

logger = logging.getLogger(__name__)


class CanonicalUnit(str, Enum):
    """Standard internal units for consistency."""
    # Metabolic
    MG_DL = "mg/dL"
    MMOL_L = "mmol/L"
    G_DL = "g/dL"
    
    # Electrolytes
    MEQ_L = "mEq/L"
    
    # Enzymes
    U_L = "U/L"
    
    # Hematology
    K_UL = "10^3/uL"
    M_UL = "10^6/uL"
    FL = "fL"
    PG = "pg"
    PERCENT = "%"
    
    # Endocrine
    UIU_ML = "uIU/mL"
    NG_DL = "ng/dL"
    PG_ML = "pg/mL"
    
    # Vitals
    BPM = "bpm"
    MMHG = "mmHg"
    CELSIUS = "°C"
    
    # Generic
    RELATIVE_INDEX = "relative_index"
    PH = "pH"


class ReferenceIntervalType(str, Enum):
    """Types of reference stratification."""
    POPULATION_ALL = "population_all"
    AGE_STRATIFIED = "age_stratified"
    SEX_STRATIFIED = "sex_stratified"
    PREGNANCY_ADJUSTED = "pregnancy_adjusted"
    BMI_STRATIFIED = "bmi_stratified"
    COMBINED = "combined"


class ReferenceInterval(BaseModel):
    """Stratified reference interval for a variable."""
    low: Optional[float] = None
    high: Optional[float] = None
    unit: str
    interval_type: ReferenceIntervalType
    source: str = "clinical_guidelines"
    
    # Stratification criteria
    age_min: Optional[int] = None
    age_max: Optional[int] = None
    sex: Optional[str] = None  # "M", "F", "all"
    is_pregnant: Optional[bool] = None
    bmi_min: Optional[float] = None
    bmi_max: Optional[float] = None
    
    notes: Optional[str] = None


class NormalizedValue(BaseModel):
    """
    Normalized value with raw preservation and reference intervals.
    Completely additive - preserves original data.
    """
    variable_name: str
    
    # Raw (as received)
    raw_value: Optional[float] = None
    raw_unit: Optional[str] = None
    
    # Standardized (canonical units)
    std_value: Optional[float] = None
    std_unit: Optional[str] = None
    
    # Reference intervals (stratified)
    applicable_references: list[ReferenceInterval] = Field(default_factory=list)
    
    # Normalization metadata
    conversion_factor: Optional[float] = None
    conversion_method: Optional[str] = None
    normalization_timestamp: Optional[str] = None
    is_within_reference: Optional[bool] = None
    distance_from_midpoint: Optional[float] = None  # For confidence scaling
    
    class Config:
        json_schema_extra = {
            "example": {
                "variable_name": "glucose",
                "raw_value": 5.5,
                "raw_unit": "mmol/L",
                "std_value": 99.0,
                "std_unit": "mg/dL",
                "conversion_factor": 18.0,
                "applicable_references": [
                    {"low": 70, "high": 100, "unit": "mg/dL", "interval_type": "population_all"}
                ]
            }
        }


# Conversion factors (to canonical units)
UNIT_CONVERSIONS: Dict[str, Dict[str, Tuple[CanonicalUnit, float]]] = {
    "glucose": {
        "mmol/L": (CanonicalUnit.MG_DL, 18.0),  # mmol/L * 18 = mg/dL
        "mg/dL": (CanonicalUnit.MG_DL, 1.0),
        "mg/dl": (CanonicalUnit.MG_DL, 1.0),
    },
    "creatinine": {
        "umol/L": (CanonicalUnit.MG_DL, 0.0113),  # umol/L * 0.0113 = mg/dL
        "mg/dL": (CanonicalUnit.MG_DL, 1.0),
        "mg/dl": (CanonicalUnit.MG_DL, 1.0),
    },
    "cholesterol": {
        "mmol/L": (CanonicalUnit.MG_DL, 38.67),
        "mg/dL": (CanonicalUnit.MG_DL, 1.0),
    },
    "triglycerides": {
        "mmol/L": (CanonicalUnit.MG_DL, 88.57),
        "mg/dL": (CanonicalUnit.MG_DL, 1.0),
    },
    "bun": {
        "mmol/L": (CanonicalUnit.MG_DL, 2.8),
        "mg/dL": (CanonicalUnit.MG_DL, 1.0),
    },
    # Add more as needed
}


# Reference intervals (simplified - would be more comprehensive in production)
REFERENCE_INTERVALS: Dict[str, list[ReferenceInterval]] = {
    "glucose": [
        ReferenceInterval(low=70, high=100, unit="mg/dL", interval_type=ReferenceIntervalType.POPULATION_ALL,
                         sex="all", source="ADA_fasting"),
        ReferenceInterval(low=70, high=140, unit="mg/dL", interval_type=ReferenceIntervalType.POPULATION_ALL,
                         sex="all", source="ADA_postprandial"),
    ],
    "creatinine": [
        ReferenceInterval(low=0.7, high=1.3, unit="mg/dL", interval_type=ReferenceIntervalType.SEX_STRATIFIED,
                         sex="M", source="NHANES"),
        ReferenceInterval(low=0.6, high=1.1, unit="mg/dL", interval_type=ReferenceIntervalType.SEX_STRATIFIED,
                         sex="F", source="NHANES"),
    ],
    "sodium_na": [
        ReferenceInterval(low=135, high=145, unit="mmol/L", interval_type=ReferenceIntervalType.POPULATION_ALL,
                         sex="all"),
    ],
    "potassium_k": [
        ReferenceInterval(low=3.5, high=5.0, unit="mmol/L", interval_type=ReferenceIntervalType.POPULATION_ALL,
                         sex="all"),
    ],
    "bun": [
        ReferenceInterval(low=7, high=20, unit="mg/dL", interval_type=ReferenceIntervalType.POPULATION_ALL,
                         sex="all"),
    ],
    "chol_total": [
        ReferenceInterval(low=125, high=200, unit="mg/dL", interval_type=ReferenceIntervalType.POPULATION_ALL,
                         sex="all", source="ATP_III"),
    ],
    "ldl": [
        ReferenceInterval(low=0, high=100, unit="mg/dL", interval_type=ReferenceIntervalType.POPULATION_ALL,
                         sex="all", source="ATP_III_optimal"),
    ],
    "hdl": [
        ReferenceInterval(low=40, high=999, unit="mg/dL", interval_type=ReferenceIntervalType.SEX_STRATIFIED,
                         sex="M", source="ATP_III"),
        ReferenceInterval(low=50, high=999, unit="mg/dL", interval_type=ReferenceIntervalType.SEX_STRATIFIED,
                         sex="F", source="ATP_III"),
    ],
    "triglycerides": [
        ReferenceInterval(low=0, high=150, unit="mg/dL", interval_type=ReferenceIntervalType.POPULATION_ALL,
                         sex="all", source="ATP_III"),
    ],
    "a1c": [
        ReferenceInterval(low=4.0, high=5.6, unit="%", interval_type=ReferenceIntervalType.POPULATION_ALL,
                         sex="all", source="ADA_normal"),
    ],
}


def normalize_value(
    variable_name: str,
    raw_value: float,
    raw_unit: str,
    patient_age: Optional[int] = None,
    patient_sex: Optional[str] = None,
    is_pregnant: Optional[bool] = None,
    patient_bmi: Optional[float] = None,
) -> NormalizedValue:
    """
    Normalize a value to canonical units and attach reference intervals.
    
    Args:
        variable_name: Name of the variable (e.g., "glucose", "creatinine")
        raw_value: Original value as received
        raw_unit: Original unit as received
        patient_age: Patient age for stratification
        patient_sex: Patient sex ("M", "F") for stratification
        is_pregnant: Pregnancy status for stratification
        patient_bmi: BMI for stratification
    
    Returns:
        NormalizedValue with standardized value and applicable references
    """
    # Get conversion if available
    conversion_info = UNIT_CONVERSIONS.get(variable_name, {}).get(raw_unit)
    
    if conversion_info:
        canonical_unit, conversion_factor = conversion_info
        std_value = raw_value * conversion_factor
        std_unit = canonical_unit.value
        conversion_method = f"multiply_by_{conversion_factor}"
    else:
        # No conversion available - pass through
        std_value = raw_value
        std_unit = raw_unit
        conversion_factor = 1.0
        conversion_method = "passthrough"
        logger.debug(f"No conversion found for {variable_name} in {raw_unit}, using passthrough")
    
    # Get applicable reference intervals
    all_refs = REFERENCE_INTERVALS.get(variable_name, [])
    applicable_refs = []
    
    for ref in all_refs:
        # Check if reference applies to this patient
        applicable = True
        
        if ref.sex and ref.sex != "all" and patient_sex:
            if ref.sex != patient_sex:
                applicable = False
        
        if ref.age_min is not None and patient_age is not None:
            if patient_age < ref.age_min:
                applicable = False
        
        if ref.age_max is not None and patient_age is not None:
            if patient_age > ref.age_max:
                applicable = False
        
        if ref.is_pregnant is not None and is_pregnant is not None:
            if ref.is_pregnant != is_pregnant:
                applicable = False
        
        if ref.bmi_min is not None and patient_bmi is not None:
            if patient_bmi < ref.bmi_min:
                applicable = False
        
        if ref.bmi_max is not None and patient_bmi is not None:
            if patient_bmi > ref.bmi_max:
                applicable = False
        
        if applicable:
            applicable_refs.append(ref)
    
    # Determine if within reference range
    is_within_reference = None
    distance_from_midpoint = None
    
    if applicable_refs:
        # Use first applicable reference (could be improved to use most specific)
        primary_ref = applicable_refs[0]
        if primary_ref.low is not None and primary_ref.high is not None:
            is_within_reference = (primary_ref.low <= std_value <= primary_ref.high)
            midpoint = (primary_ref.low + primary_ref.high) / 2.0
            range_width = primary_ref.high - primary_ref.low
            distance_from_midpoint = abs(std_value - midpoint) / (range_width / 2.0) if range_width > 0 else 0.0
    
    from datetime import datetime
    
    return NormalizedValue(
        variable_name=variable_name,
        raw_value=raw_value,
        raw_unit=raw_unit,
        std_value=std_value,
        std_unit=std_unit,
        applicable_references=applicable_refs,
        conversion_factor=conversion_factor,
        conversion_method=conversion_method,
        normalization_timestamp=datetime.utcnow().isoformat(),
        is_within_reference=is_within_reference,
        distance_from_midpoint=distance_from_midpoint,
    )


def normalize_specimen_values(
    specimen_values: Dict[str, float],
    specimen_units: Optional[Dict[str, str]] = None,
    patient_age: Optional[int] = None,
    patient_sex: Optional[str] = None,
    is_pregnant: Optional[bool] = None,
    patient_bmi: Optional[float] = None,
) -> Dict[str, NormalizedValue]:
    """
    Normalize all values in a specimen.
    
    Args:
        specimen_values: Dict of variable_name -> value
        specimen_units: Optional dict of variable_name -> unit (defaults to canonical)
        patient_age: Patient age
        patient_sex: Patient sex
        is_pregnant: Pregnancy status
        patient_bmi: Patient BMI
    
    Returns:
        Dict of variable_name -> NormalizedValue
    """
    normalized = {}
    
    for var_name, var_value in specimen_values.items():
        if var_value is None:
            continue
        
        # Determine unit
        if specimen_units and var_name in specimen_units:
            var_unit = specimen_units[var_name]
        else:
            # Default to canonical unit for that variable
            var_unit = _get_default_unit(var_name)
        
        normalized[var_name] = normalize_value(
            variable_name=var_name,
            raw_value=var_value,
            raw_unit=var_unit,
            patient_age=patient_age,
            patient_sex=patient_sex,
            is_pregnant=is_pregnant,
            patient_bmi=patient_bmi,
        )
    
    return normalized


def _get_default_unit(variable_name: str) -> str:
    """Get default unit for a variable (simplified)."""
    defaults = {
        "glucose": "mg/dL",
        "creatinine": "mg/dL",
        "bun": "mg/dL",
        "sodium_na": "mmol/L",
        "potassium_k": "mmol/L",
        "chloride_cl": "mmol/L",
        "chol_total": "mg/dL",
        "ldl": "mg/dL",
        "hdl": "mg/dL",
        "triglycerides": "mg/dL",
        "a1c": "%",
    }
    return defaults.get(variable_name, "unit")
