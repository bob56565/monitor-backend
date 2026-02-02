"""
RunV2 and associated Pydantic models for multi-specimen ingestion and qualitative encoding.
Non-breaking extension to existing DB models.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field


# ============================================================================
# ENUMS
# ============================================================================

class SpecimenTypeEnum(str, Enum):
    """Specimen types supported by MONITOR MVP."""
    ISF = "ISF"
    BLOOD_CAPILLARY = "BLOOD_CAPILLARY"
    BLOOD_VENOUS = "BLOOD_VENOUS"
    SALIVA = "SALIVA"
    SWEAT = "SWEAT"
    URINE_SPOT = "URINE_SPOT"


class MissingTypeEnum(str, Enum):
    """Why a variable is missing."""
    NOT_COLLECTED = "not_collected"
    USER_SKIPPED = "user_skipped"
    BIOLOGICALLY_UNAVAILABLE = "biologically_unavailable"
    TEMPORARILY_UNAVAILABLE = "temporarily_unavailable"
    SENSOR_UNAVAILABLE = "sensor_unavailable"
    NOT_APPLICABLE = "not_applicable"


class MissingImpactEnum(str, Enum):
    """Impact of missingness on inference."""
    NEUTRAL = "neutral"
    CONFIDENCE_PENALTY = "confidence_penalty"
    INFERENCE_BLOCKER = "inference_blocker"


class ProvenanceEnum(str, Enum):
    """Source/method of data collection."""
    MEASURED = "measured"
    DIRECT = "direct"
    PROXY = "proxy"
    INFERRED = "inferred"
    POPULATION = "population"
    RELATIONAL = "relational"


class SupportTypeEnum(str, Enum):
    """Type of support for inference values."""
    DIRECT = "direct"
    PROXY = "proxy"
    RELATIONAL = "relational"
    POPULATION = "population"


# ============================================================================
# MISSINGNESS & PROVENANCE STRUCTURES
# ============================================================================

class MissingnessRecord(BaseModel):
    """
    Explicit missingness tracking for a single variable.
    Every value (present or absent) has a missingness record.
    """
    is_missing: bool
    missing_type: Optional[MissingTypeEnum] = None
    missing_impact: MissingImpactEnum = MissingImpactEnum.NEUTRAL
    provenance: ProvenanceEnum
    confidence_0_1: float = Field(default=1.0, ge=0.0, le=1.0)
    notes: Optional[str] = None


# ============================================================================
# SPECIMEN VARIABLE MAPS (Reference Structures for UI/Backend Validation)
# ============================================================================

class VariableSpec(BaseModel):
    """Specification for a single variable in a specimen."""
    unit: str
    var_type: str  # "number", "string", "boolean", "string|number"
    provenance_default: Optional[ProvenanceEnum] = ProvenanceEnum.MEASURED
    notes: Optional[str] = None


# ISF Variables
ISF_VARIABLES = {
    "glucose": VariableSpec(unit="mg/dL", var_type="number", provenance_default=ProvenanceEnum.MEASURED),
    "lactate": VariableSpec(unit="mmol/L", var_type="number", provenance_default=ProvenanceEnum.MEASURED),
    "sodium_na": VariableSpec(unit="mmol/L", var_type="number", provenance_default=ProvenanceEnum.MEASURED),
    "potassium_k": VariableSpec(unit="mmol/L", var_type="number", provenance_default=ProvenanceEnum.MEASURED),
    "chloride_cl": VariableSpec(unit="mmol/L", var_type="number", provenance_default=ProvenanceEnum.MEASURED),
    "ph": VariableSpec(unit="pH", var_type="number", provenance_default=ProvenanceEnum.MEASURED),
    "crp_proxy": VariableSpec(unit="relative_index", var_type="number", provenance_default=ProvenanceEnum.PROXY),
    "cytokine_proxy_il6": VariableSpec(unit="relative_index", var_type="number", provenance_default=ProvenanceEnum.PROXY),
    "drug_signal_proxy": VariableSpec(unit="relative_index", var_type="number", provenance_default=ProvenanceEnum.PROXY),
}

# Blood Common Variables
BLOOD_CMP_BMP = {
    "glucose": VariableSpec(unit="mg/dL", var_type="number"),
    "bun": VariableSpec(unit="mg/dL", var_type="number"),
    "creatinine": VariableSpec(unit="mg/dL", var_type="number"),
    "sodium_na": VariableSpec(unit="mmol/L", var_type="number"),
    "potassium_k": VariableSpec(unit="mmol/L", var_type="number"),
    "chloride_cl": VariableSpec(unit="mmol/L", var_type="number"),
    "co2_bicarb": VariableSpec(unit="mmol/L", var_type="number"),
    "calcium": VariableSpec(unit="mg/dL", var_type="number"),
    "total_protein": VariableSpec(unit="g/dL", var_type="number"),
    "albumin": VariableSpec(unit="g/dL", var_type="number"),
    "bilirubin_total": VariableSpec(unit="mg/dL", var_type="number"),
    "alk_phos": VariableSpec(unit="U/L", var_type="number"),
    "ast": VariableSpec(unit="U/L", var_type="number"),
    "alt": VariableSpec(unit="U/L", var_type="number"),
}

BLOOD_CBC = {
    "wbc": VariableSpec(unit="10^3/uL", var_type="number"),
    "rbc": VariableSpec(unit="10^6/uL", var_type="number"),
    "hgb": VariableSpec(unit="g/dL", var_type="number"),
    "hct": VariableSpec(unit="%", var_type="number"),
    "mcv": VariableSpec(unit="fL", var_type="number"),
    "mch": VariableSpec(unit="pg", var_type="number"),
    "mchc": VariableSpec(unit="g/dL", var_type="number"),
    "rdw": VariableSpec(unit="%", var_type="number"),
    "platelets": VariableSpec(unit="10^3/uL", var_type="number"),
    "neutrophils_pct": VariableSpec(unit="%", var_type="number"),
    "lymphocytes_pct": VariableSpec(unit="%", var_type="number"),
}

BLOOD_LIPIDS = {
    "chol_total": VariableSpec(unit="mg/dL", var_type="number"),
    "ldl": VariableSpec(unit="mg/dL", var_type="number"),
    "hdl": VariableSpec(unit="mg/dL", var_type="number"),
    "triglycerides": VariableSpec(unit="mg/dL", var_type="number"),
}

BLOOD_ENDOCRINE = {
    "a1c": VariableSpec(unit="%", var_type="number"),
    "fasting_insulin": VariableSpec(unit="uIU/mL", var_type="number"),
    "tsh": VariableSpec(unit="uIU/mL", var_type="number"),
    "free_t4": VariableSpec(unit="ng/dL", var_type="number"),
    "free_t3": VariableSpec(unit="pg/mL", var_type="number"),
}

BLOOD_VITAMINS_NUTRITION = {
    "vitamin_d_25oh": VariableSpec(unit="ng/mL", var_type="number"),
    "b12": VariableSpec(unit="pg/mL", var_type="number"),
    "folate": VariableSpec(unit="ng/mL", var_type="number"),
    "ferritin": VariableSpec(unit="ng/mL", var_type="number"),
    "iron": VariableSpec(unit="ug/dL", var_type="number"),
    "tibc": VariableSpec(unit="ug/dL", var_type="number"),
    "transferrin_sat": VariableSpec(unit="%", var_type="number"),
}

BLOOD_INFLAMMATION_CARDIOMETABOLIC = {
    "crp": VariableSpec(unit="mg/L", var_type="number"),
    "esr": VariableSpec(unit="mm/hr", var_type="number"),
    "uric_acid": VariableSpec(unit="mg/dL", var_type="number"),
}

BLOOD_AUTOIMMUNE_STRUCT = {
    "ana": VariableSpec(unit="titer_or_posneg", var_type="string|number"),
    "rf": VariableSpec(unit="IU/mL", var_type="number"),
    "anti_ccp": VariableSpec(unit="U/mL", var_type="number"),
    "dsdna": VariableSpec(unit="IU/mL", var_type="number"),
    "ena_panel": VariableSpec(unit="structured", var_type="object"),
}

BLOOD_ALL_VARIABLES = {
    **BLOOD_CMP_BMP,
    **BLOOD_CBC,
    **BLOOD_LIPIDS,
    **BLOOD_ENDOCRINE,
    **BLOOD_VITAMINS_NUTRITION,
    **BLOOD_INFLAMMATION_CARDIOMETABOLIC,
    **BLOOD_AUTOIMMUNE_STRUCT,
}

# Saliva Variables
SALIVA_VARIABLES = {
    "cortisol_morning": VariableSpec(unit="ug/dL_or_relative", var_type="number"),
    "cortisol_evening": VariableSpec(unit="ug/dL_or_relative", var_type="number"),
    "alpha_amylase": VariableSpec(unit="relative_index", var_type="number"),
    "ph": VariableSpec(unit="pH", var_type="number"),
    "flow_rate": VariableSpec(unit="mL/min", var_type="number"),
    "dryness_score": VariableSpec(unit="0_10", var_type="number"),
    "recent_alcohol_flag": VariableSpec(unit="boolean", var_type="boolean"),
    "recent_nicotine_flag": VariableSpec(unit="boolean", var_type="boolean"),
}

# Sweat Variables
SWEAT_VARIABLES = {
    "sodium_na": VariableSpec(unit="mmol/L", var_type="number"),
    "chloride_cl": VariableSpec(unit="mmol/L", var_type="number"),
    "potassium_k": VariableSpec(unit="mmol/L", var_type="number"),
    "sweat_rate": VariableSpec(unit="mL/hr", var_type="number"),
    "skin_temp": VariableSpec(unit="C", var_type="number"),
    "exertion_level": VariableSpec(unit="0_10", var_type="number"),
}

# Urine Spot Variables
URINE_SPOT_VARIABLES = {
    "specific_gravity": VariableSpec(unit="unitless", var_type="number"),
    "ph": VariableSpec(unit="pH", var_type="number"),
    "protein": VariableSpec(unit="mg/dL_or_posneg", var_type="string|number"),
    "glucose": VariableSpec(unit="mg/dL_or_posneg", var_type="string|number"),
    "ketones": VariableSpec(unit="posneg_or_mgdl", var_type="string|number"),
    "blood": VariableSpec(unit="posneg", var_type="string"),
    "leukocyte_esterase": VariableSpec(unit="posneg", var_type="string"),
    "nitrite": VariableSpec(unit="posneg", var_type="string"),
    "uacr": VariableSpec(unit="mg/g", var_type="number"),
    "microalbumin": VariableSpec(unit="mg/L", var_type="number"),
}

# Mapping from specimen type to variable specs
SPECIMEN_VARIABLE_MAP = {
    SpecimenTypeEnum.ISF: ISF_VARIABLES,
    SpecimenTypeEnum.BLOOD_CAPILLARY: BLOOD_ALL_VARIABLES,
    SpecimenTypeEnum.BLOOD_VENOUS: BLOOD_ALL_VARIABLES,
    SpecimenTypeEnum.SALIVA: SALIVA_VARIABLES,
    SpecimenTypeEnum.SWEAT: SWEAT_VARIABLES,
    SpecimenTypeEnum.URINE_SPOT: URINE_SPOT_VARIABLES,
}


# ============================================================================
# SPECIMEN RECORD
# ============================================================================

class SpecimenRecord(BaseModel):
    """
    One specimen sub-record within a Run.
    Supports multiple specimens per run.
    """
    specimen_id: str
    specimen_type: SpecimenTypeEnum
    collected_at: datetime
    source_detail: Optional[str] = None  # e.g., "fingerstick", "venipuncture"
    raw_values: Dict[str, Any]  # variable_name -> value
    units: Dict[str, str]  # variable_name -> unit
    missingness: Dict[str, MissingnessRecord]  # variable_name -> missingness record
    notes: Optional[str] = None

    class Config:
        use_enum_values = False  # Keep enums as objects


# ============================================================================
# NON-LAB INPUTS (Always-on)
# ============================================================================

class DemographicsInputs(BaseModel):
    """Demographics section of NonLabInputs."""
    age: Optional[int] = None
    sex_at_birth: Optional[str] = Field(None, pattern="^(female|male|intersex|unknown)$")


class AnthropometricsInputs(BaseModel):
    """Anthropometrics section of NonLabInputs."""
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    waist_cm: Optional[float] = None
    body_fat_pct: Optional[float] = None


class VitalsPhysiologyInputs(BaseModel):
    """Vitals and physiology section of NonLabInputs."""
    heart_rate: Optional[int] = None  # bpm
    hrv: Optional[float] = None  # ms
    bp_systolic: Optional[int] = None  # mmHg
    bp_diastolic: Optional[int] = None  # mmHg
    temperature_c: Optional[float] = None


class SleepActivityInputs(BaseModel):
    """Sleep and activity section of NonLabInputs."""
    sleep_duration_hr: Optional[float] = None
    sleep_quality_0_10: Optional[int] = Field(None, ge=0, le=10)
    activity_level_0_10: Optional[int] = Field(None, ge=0, le=10)


class IntakeExposureInputs(BaseModel):
    """Intake and exposure section of NonLabInputs."""
    fluid_intake_ml_24h: Optional[float] = None
    sodium_intake_mg_24h_est: Optional[float] = None
    alcohol_units_24h: Optional[float] = None
    caffeine_mg_24h: Optional[float] = None
    nicotine_use: Optional[str] = Field(None, pattern="^(none|occasional|daily|unknown)$")


class SupplementItem(BaseModel):
    """Single supplement entry."""
    name: str
    dose: Optional[str] = None
    frequency: Optional[str] = None


class MedicationItem(BaseModel):
    """Single medication entry."""
    drug: str
    dose: Optional[str] = None
    route: Optional[str] = None
    frequency: Optional[str] = None
    duration: Optional[str] = None
    indication: Optional[str] = None
    adherence: Optional[str] = Field(None, pattern="^(on_time|missed_recently|stopped_recently)$")


class NonLabInputs(BaseModel):
    """
    Always-on non-lab inputs section.
    Includes demographics, anthropometrics, vitals, sleep/activity, intake/exposure, supplements, medications.
    """
    demographics: Optional[DemographicsInputs] = None
    anthropometrics: Optional[AnthropometricsInputs] = None
    vitals_physiology: Optional[VitalsPhysiologyInputs] = None
    sleep_activity: Optional[SleepActivityInputs] = None
    intake_exposure: Optional[IntakeExposureInputs] = None
    supplements: Optional[List[SupplementItem]] = None
    medications: Optional[List[MedicationItem]] = None


# ============================================================================
# QUALITATIVE INPUTS & ENCODING
# ============================================================================

class QualitativeInputs(BaseModel):
    """Structured qualitative inputs (stress, sleep, diet, symptoms, hormonal context)."""
    
    stress: Optional[Dict[str, Any]] = None  # level_0_10, duration_days, trigger_type, chronicity, certainty_0_1
    sleep: Optional[Dict[str, Any]] = None  # regularity, awakenings_per_night, subjective_quality_0_10, certainty_0_1
    diet_recent: Optional[Dict[str, Any]] = None  # pattern, fasting_state, alcohol_last_24h, certainty_0_1
    symptoms: Optional[Dict[str, Any]] = None  # fatigue_0_10, palpitations, polyuria, polydipsia, weight_change_recent, gi_symptoms, certainty_0_1
    hormonal_context: Optional[Dict[str, Any]] = None  # menstrual_phase, contraception, trt, pregnancy, certainty_0_1


class QualEncodingOutputs(BaseModel):
    """
    Encoder outputs: numeric effect vector + uncertainty + measurement interference.
    Produced by qualitative encoder and stored in RunV2.
    """
    effect_vector: Dict[str, float]  # metabolic_pressure, inflammatory_tone, dehydration_pressure, endocrine_shift, measurement_interference
    uncertainty: Dict[str, Any]  # overall_reliability_0_1, drivers[], penalties[]


# ============================================================================
# RUNV2 MAIN STRUCTURE
# ============================================================================

class RunV2(BaseModel):
    """
    Non-breaking superset run structure supporting multi-specimen payloads + always-on non-lab inputs.
    Stored as JSON in DB or as new table as needed.
    """
    run_id: str
    user_id: str
    created_at: datetime
    timezone: Optional[str] = "UTC"
    legacy_raw_id: Optional[int] = None  # If wrapping from legacy endpoint
    specimens: List[SpecimenRecord]
    non_lab_inputs: NonLabInputs
    qualitative_inputs: Optional[QualitativeInputs] = None
    encoding_outputs: Optional[QualEncodingOutputs] = None
    provenance_map: Dict[str, str] = Field(default_factory=dict)  # variable -> provenance
    missingness_map: Dict[str, str] = Field(default_factory=dict)  # variable -> missing_type
    schema_version: str = "runv2.1"

    class Config:
        use_enum_values = False  # Keep enums as objects


# ============================================================================
# REQUEST/RESPONSE MODELS FOR ENDPOINTS
# ============================================================================

class RunV2CreateRequest(BaseModel):
    """Request to create a RunV2."""
    timezone: Optional[str] = "UTC"
    specimens: List[SpecimenRecord]
    non_lab_inputs: NonLabInputs
    qualitative_inputs: Optional[QualitativeInputs] = None


class RunV2Response(BaseModel):
    """Response from RunV2 endpoint."""
    run_id: str
    user_id: str
    created_at: datetime
    schema_version: str
    specimen_count: int
    specimens: List[Dict[str, Any]]

    class Config:
        from_attributes = True


class RunV2DetailResponse(BaseModel):
    """Detailed response for GET /runs/v2/{run_id}."""
    run_id: str
    user_id: str
    created_at: datetime
    timezone: str
    schema_version: str
    specimens: List[SpecimenRecord]
    non_lab_inputs: NonLabInputs
    qualitative_inputs: Optional[QualitativeInputs]
    encoding_outputs: Optional[QualEncodingOutputs]
    provenance_map: Dict[str, str]
    missingness_map: Dict[str, str]

    class Config:
        from_attributes = True
