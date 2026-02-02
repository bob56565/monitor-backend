"""
PART A Main Schema v1.0.0
Complete schema definition for all raw data user inputs as specified in PART A requirements.
Non-breaking, additive schema supporting all specimen types, vitals, SOAP profile, and qualitative encoding.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Literal
from enum import Enum
from pydantic import BaseModel, Field, field_validator, model_validator


# ============================================================================
# A1) SPECIMEN DATA UPLOADS
# ============================================================================

class SpecimenModalityEnum(str, Enum):
    """All supported specimen modalities per A1."""
    BLOOD = "blood"
    SALIVA = "saliva"
    SWEAT = "sweat"
    URINE = "urine"
    IMAGING = "imaging"


class BloodPanelType(str, Enum):
    """Standard blood panels per A1.1."""
    METABOLIC_CMP = "metabolic_cmp"
    CBC = "cbc"
    LIPID = "lipid"
    ENDOCRINE = "endocrine"
    INFLAMMATION = "inflammation"
    VITAMINS_MINERALS = "vitamins_minerals"
    CUSTOM = "custom"


class FileFormatEnum(str, Enum):
    """Accepted file formats for uploads."""
    PDF = "pdf"
    IMAGE = "image"
    HL7 = "hl7"
    FHIR = "fhir"
    CSV = "csv"
    MANUAL_ENTRY = "manual_entry"


class FastingStatusEnum(str, Enum):
    """Fasting status for lab collections."""
    FASTING = "fasting"
    NON_FASTING = "non_fasting"
    UNKNOWN = "unknown"


# A1.1: Blood Specimen
class BloodAnalyte(BaseModel):
    """Individual analyte value from blood specimen."""
    name: str = Field(..., description="Analyte name (e.g., glucose, Na, WBC)")
    value: Optional[float] = Field(None, description="Numeric value")
    value_string: Optional[str] = Field(None, description="String value for qualitative results")
    unit: Optional[str] = Field(None, description="Unit of measure")
    reference_range_low: Optional[float] = None
    reference_range_high: Optional[float] = None
    reference_range_text: Optional[str] = Field(None, description="Text-based reference range")
    flag: Optional[str] = Field(None, description="H/L/Critical/Normal flag")
    method: Optional[str] = Field(None, description="Test method if available")


class BloodSpecimenData(BaseModel):
    """Blood specimen data per A1.1."""
    collection_datetime: datetime
    fasting_status: FastingStatusEnum = FastingStatusEnum.UNKNOWN
    panels: List[BloodPanelType] = Field(default_factory=list)
    analytes: List[BloodAnalyte] = Field(default_factory=list)
    lab_name: Optional[str] = None
    lab_id: Optional[str] = None
    source_format: FileFormatEnum
    raw_artifact_path: Optional[str] = Field(None, description="Path to stored raw file")
    parsing_notes: Optional[str] = Field(None, description="Notes from parsing process")


# A1.2: Saliva Specimen
class SalivaAnalyte(BaseModel):
    """Individual analyte from saliva specimen."""
    name: str = Field(..., description="cortisol, DHEA-S, salivary_crp, etc.")
    value: float
    unit: str
    timestamp: datetime = Field(..., description="Collection time (critical for cortisol rhythm)")
    reference_range_low: Optional[float] = None
    reference_range_high: Optional[float] = None


class SalivaSpecimenData(BaseModel):
    """Saliva specimen data per A1.2."""
    collection_type: Literal["spot", "serial"] = "spot"
    analytes: List[SalivaAnalyte] = Field(default_factory=list)
    source_format: FileFormatEnum
    raw_artifact_path: Optional[str] = None


# A1.3: Sweat Specimen
class SweatAnalyte(BaseModel):
    """Individual analyte from sweat specimen."""
    name: str = Field(..., description="Na, K, Cl, lactate, glucose, pH, etc.")
    value: float
    unit: str
    timestamp: Optional[datetime] = None
    reference_range_low: Optional[float] = None
    reference_range_high: Optional[float] = None


class SweatSpecimenData(BaseModel):
    """Sweat specimen data per A1.3."""
    analytes: List[SweatAnalyte] = Field(default_factory=list)
    sweat_rate: Optional[float] = Field(None, description="Sweat rate in mL/min or similar")
    osmolality: Optional[float] = None
    collection_datetime: Optional[datetime] = None
    source_format: FileFormatEnum
    raw_artifact_path: Optional[str] = None


# A1.4: Urine Specimen
class UrineAnalyte(BaseModel):
    """Individual analyte from urine specimen."""
    name: str = Field(..., description="specific_gravity, pH, ketones, glucose, protein, etc.")
    value: Optional[float] = None
    value_string: Optional[str] = Field(None, description="For qualitative dipstick: trace/1+/2+/3+")
    unit: Optional[str] = None
    reference_range_text: Optional[str] = None


class UrineSpecimenData(BaseModel):
    """Urine specimen data per A1.4."""
    collection_datetime: datetime
    collection_type: Literal["dipstick", "lab", "spot", "24hr"] = "spot"
    analytes: List[UrineAnalyte] = Field(default_factory=list)
    source_format: FileFormatEnum
    raw_artifact_path: Optional[str] = None


# A1.5: Imaging/Diagnostic Reports
class ImagingReportData(BaseModel):
    """Imaging or diagnostic report data per A1.5."""
    report_type: Literal["radiology", "echo", "ecg", "sleep_study", "other"] = "other"
    report_date: datetime
    impression: Optional[str] = Field(None, description="Primary impression/findings")
    key_measurements: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Extracted measurements")
    severity_statements: Optional[List[str]] = Field(default_factory=list)
    follow_up_recommendations: Optional[str] = None
    source_format: FileFormatEnum
    raw_artifact_path: Optional[str] = Field(None, description="Path to PDF/image")
    parsing_notes: Optional[str] = None


# Combined Specimen Upload
class SpecimenDataUpload(BaseModel):
    """Complete specimen data upload per A1. User must select ≥1 modality."""
    modalities_selected: List[SpecimenModalityEnum] = Field(..., min_length=1, description="REQUIRED: User must select ≥1 modality")
    blood: Optional[List[BloodSpecimenData]] = Field(default_factory=list)
    saliva: Optional[List[SalivaSpecimenData]] = Field(default_factory=list)
    sweat: Optional[List[SweatSpecimenData]] = Field(default_factory=list)
    urine: Optional[List[UrineSpecimenData]] = Field(default_factory=list)
    imaging: Optional[List[ImagingReportData]] = Field(default_factory=list)

    @model_validator(mode='after')
    def validate_modality_data(self):
        """Ensure selected modalities have corresponding data."""
        for modality in self.modalities_selected:
            data = getattr(self, modality.value, None)
            if not data or len(data) == 0:
                raise ValueError(f"Selected modality '{modality.value}' must have at least one data entry")
        return self


# ============================================================================
# A2) STANDARD ISF MONITOR DATA
# ============================================================================

class SignalQuality(BaseModel):
    """Signal quality metadata per A2.5."""
    calibration_status: str = Field(..., description="recent/stale/uncalibrated")
    sensor_drift_score: float = Field(..., ge=0.0, le=1.0, description="0=no drift, 1=high drift")
    noise_score: float = Field(..., ge=0.0, le=1.0)
    dropout_percentage: float = Field(..., ge=0.0, le=100.0)
    temperature_compensation_flags: Optional[List[str]] = Field(default_factory=list)


class ISFAnalyteStream(BaseModel):
    """Time-stamped stream for a single ISF analyte."""
    name: str = Field(..., description="glucose, lactate, sodium_na, potassium_k, etc.")
    values: List[float] = Field(..., min_length=1)
    timestamps: List[datetime] = Field(..., min_length=1)
    unit: str
    device_id: Optional[str] = None
    sensor_type: Optional[str] = None

    @model_validator(mode='after')
    def validate_lengths_match(self):
        """Ensure values and timestamps have same length."""
        if len(self.values) != len(self.timestamps):
            raise ValueError("values and timestamps must have same length")
        return self


class ISFMonitorData(BaseModel):
    """Complete ISF monitor data per A2."""
    core_analytes: List[ISFAnalyteStream] = Field(..., description="glucose, lactate (A2.1)")
    electrolytes: Optional[List[ISFAnalyteStream]] = Field(default_factory=list, description="Na+, K+, Cl−, etc (A2.2)")
    renal_metabolic: Optional[List[ISFAnalyteStream]] = Field(default_factory=list, description="urea, creatinine, uric acid (A2.3)")
    inflammation_oxidative: Optional[List[ISFAnalyteStream]] = Field(default_factory=list, description="CRP proxy, redox (A2.4)")
    signal_quality: SignalQuality


# ============================================================================
# A3) VITALS DATA
# ============================================================================

class CardiovascularVitals(BaseModel):
    """Cardiovascular vitals per A3.1."""
    heart_rate_resting: Optional[List[float]] = Field(default_factory=list, description="bpm")
    heart_rate_active: Optional[List[float]] = Field(default_factory=list)
    heart_rate_sleeping: Optional[List[float]] = Field(default_factory=list)
    hrv_rmssd: Optional[List[float]] = Field(default_factory=list, description="ms")
    hrv_sdnn: Optional[List[float]] = Field(default_factory=list)
    heart_rate_recovery_1min: Optional[float] = Field(None, description="bpm drop in 1 min post-exertion")
    heart_rate_recovery_2min: Optional[float] = None
    blood_pressure_systolic: Optional[List[int]] = Field(default_factory=list)
    blood_pressure_diastolic: Optional[List[int]] = Field(default_factory=list)
    bp_method: Optional[str] = Field(None, description="cuff/validated_estimate/device_name")
    timestamps: Optional[List[datetime]] = Field(default_factory=list)


class RespiratoryTemperatureVitals(BaseModel):
    """Respiratory and temperature vitals per A3.2."""
    respiratory_rate_sleep: Optional[List[float]] = Field(default_factory=list, description="breaths/min")
    respiratory_rate_rest: Optional[List[float]] = Field(default_factory=list)
    skin_temperature: Optional[List[float]] = Field(default_factory=list, description="°C or °F")
    core_temperature_proxy: Optional[List[float]] = Field(default_factory=list)
    spo2: Optional[List[float]] = Field(default_factory=list, description="SpO2 %")
    timestamps: Optional[List[datetime]] = Field(default_factory=list)


class SleepRecoveryActivityVitals(BaseModel):
    """Sleep, recovery, and activity vitals per A3.3."""
    total_sleep_time_hours: Optional[float] = None
    sleep_efficiency_percent: Optional[float] = Field(None, ge=0.0, le=100.0)
    awakenings_count: Optional[int] = None
    rem_sleep_hours: Optional[float] = None
    deep_sleep_hours: Optional[float] = None
    light_sleep_hours: Optional[float] = None
    steps_daily: Optional[int] = None
    active_minutes: Optional[int] = None
    met_minutes: Optional[int] = None
    vo2max_proxy: Optional[float] = Field(None, description="VO2max estimate from device")
    workouts: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="[{type, duration_min, intensity, perceived_exertion}]")


class VitalsData(BaseModel):
    """Complete vitals data per A3."""
    cardiovascular: CardiovascularVitals
    respiratory_temperature: RespiratoryTemperatureVitals
    sleep_recovery_activity: SleepRecoveryActivityVitals
    baseline_learning_days: Optional[int] = Field(None, description="Days of baseline data collected")


# ============================================================================
# A4) SOAP-NOTE LEVEL HEALTH PROFILE + WEEKLY CONTEXT
# ============================================================================

# A4.1: Demographics + Anthropometrics
class DemographicsAnthropometrics(BaseModel):
    """Structured demographics and anthropometrics per A4.1."""
    age: int = Field(..., ge=0, le=120)
    sex_at_birth: Literal["male", "female", "other", "prefer_not_to_say"]
    gender_identity: Optional[str] = None
    race_ethnicity: Optional[List[str]] = Field(default_factory=list, description="User-controlled for risk calibration")
    height_cm: float = Field(..., gt=0)
    weight_kg: float = Field(..., gt=0)
    bmi: Optional[float] = Field(None, description="Auto-calculated or user-provided")
    waist_circumference_cm: Optional[float] = None
    body_fat_percent: Optional[float] = Field(None, ge=0.0, le=100.0)
    pregnancy_status: Optional[Literal["pregnant", "not_pregnant", "postpartum", "not_applicable"]] = None
    menstrual_cycle_status: Optional[str] = Field(None, description="regular/irregular/menopausal/not_applicable")


# A4.2: PMH/PSH/FH (Dropdown Arrays)
class MedicalHistory(BaseModel):
    """Medical history via dropdown arrays per A4.2."""
    conditions: List[str] = Field(default_factory=list, description="diabetes, prediabetes, HTN, CKD, CAD, thyroid_disease, etc.")
    family_history: List[str] = Field(default_factory=list, description="early_cad, diabetes, thyroid, ckd, autoimmune, etc.")
    surgical_history: Optional[List[str]] = Field(default_factory=list)


# A4.3: Medications + Supplements
class Medication(BaseModel):
    """Individual medication/supplement per A4.3."""
    name: str
    dose: str
    frequency: str
    start_date: Optional[datetime] = None
    special_flags: Optional[List[str]] = Field(default_factory=list, description="steroids, thyroid_meds, glp1, beta_blockers, diuretics, statins, iron, b12, vitamin_d, magnesium")


class MedicationsSupplements(BaseModel):
    """Complete medication and supplement list per A4.3."""
    medications: List[Medication] = Field(default_factory=list)
    supplements: List[Medication] = Field(default_factory=list)


# A4.4: Diet (Dropdown-Driven, Structured)
class DietProfile(BaseModel):
    """Structured diet profile per A4.4."""
    pattern: Literal["standard", "mediterranean", "low_carb", "keto", "vegan", "vegetarian", "high_protein", "other"]
    sodium_intake: Literal["low", "normal", "high"]
    hydration_intake: Literal["low", "normal", "high"]
    hydration_ounces_per_day: Optional[float] = None
    caffeine: Literal["none", "low", "moderate", "high"]
    caffeine_cups_per_day: Optional[float] = None
    alcohol: Literal["none", "low", "moderate", "high"]
    alcohol_frequency: Optional[str] = Field(None, description="never/weekly/daily/etc")
    meal_timing: Literal["early", "late", "irregular", "consistent"]
    fasting_windows: Optional[str] = Field(None, description="e.g., 16:8, 18:6, none")


# A4.5: Activity + Lifestyle (Dropdown-Driven)
class ActivityLifestyle(BaseModel):
    """Structured activity and lifestyle per A4.5."""
    activity_level: Literal["sedentary", "light", "moderate", "high"]
    training_type: Optional[Literal["endurance", "strength", "mixed", "none"]] = None
    shift_work: bool = False
    sleep_schedule_consistency: Literal["consistent", "inconsistent", "variable"]
    nicotine_tobacco: Literal["none", "former", "current"]
    nicotine_frequency: Optional[str] = None
    recreational_substances: Optional[Literal["none", "occasional", "frequent"]] = "none"


# A4.6: Symptoms (Two Inputs)
class StructuredSymptom(BaseModel):
    """Structured symptom with severity, duration, triggers per A4.6."""
    category: str = Field(..., description="fatigue, polyuria, polydipsia, palpitations, heat_intolerance, cold_intolerance, muscle_cramps, dizziness, edema, sob, chest_pain, gi_symptoms, neuro_symptoms, etc.")
    severity: Literal["mild", "moderate", "severe"]
    duration: str = Field(..., description="days/weeks/months")
    triggers: Optional[List[str]] = Field(default_factory=list)
    notes: Optional[str] = None


class Symptoms(BaseModel):
    """Symptoms input per A4.6: free-text + structured dropdowns."""
    free_text: Optional[str] = Field(None, description="User's free-text symptom description")
    structured: List[StructuredSymptom] = Field(default_factory=list, description="Structured symptom dropdowns")


# Combined SOAP Profile
class SOAPProfile(BaseModel):
    """Complete SOAP-note level health profile per A4."""
    demographics_anthropometrics: DemographicsAnthropometrics
    medical_history: MedicalHistory
    medications_supplements: MedicationsSupplements
    diet: DietProfile
    activity_lifestyle: ActivityLifestyle
    symptoms: Symptoms


# ============================================================================
# A5) QUALITATIVE → QUANTITATIVE ENCODING
# ============================================================================

class QualitativeEncodingRule(BaseModel):
    """Individual encoding rule per A5."""
    input_field: str = Field(..., description="Field name, e.g., 'diet.sodium_intake'")
    input_value: str = Field(..., description="Selected dropdown value, e.g., 'high'")
    standardized_code: str = Field(..., description="Standardized code for this selection")
    numeric_weight: float = Field(..., description="Numeric weight/multiplier")
    time_window: Literal["acute", "chronic"]
    direction_of_effect: Dict[str, float] = Field(..., description="e.g., {'dehydration_risk': +0.35, 'bp_risk': +0.20}")
    notes: Optional[str] = None


class QualitativeEncoding(BaseModel):
    """Complete qualitative-to-quantitative encoding per A5."""
    rules_applied: List[QualitativeEncodingRule] = Field(default_factory=list)
    total_encoding_entries: int = Field(0, description="Count of encoded qualitative inputs")


# ============================================================================
# MASTER PART A INPUT SCHEMA
# ============================================================================

class PartAInputSchema(BaseModel):
    """
    Master schema for all PART A raw data user inputs.
    Version 1.0.0
    Non-breaking, additive, comprehensive.
    """
    schema_version: str = Field(default="1.0.0", description="Schema version")
    submission_id: Optional[str] = Field(None, description="Unique ID for this submission")
    user_id: Optional[int] = None
    submission_timestamp: datetime = Field(default_factory=datetime.utcnow)

    # A1: Specimen Data Uploads (≥1 required)
    specimen_data: SpecimenDataUpload

    # A2: Standard ISF Monitor Data (always included)
    isf_monitor_data: ISFMonitorData

    # A3: Vitals (current + daily/weekly trends)
    vitals_data: VitalsData

    # A4: SOAP-note level health profile + weekly context
    soap_profile: SOAPProfile

    # A5: Qualitative → Quantitative Encoding
    qualitative_encoding: QualitativeEncoding

    @model_validator(mode='after')
    def validate_complete_submission(self):
        """Final validation for complete PART A submission."""
        # Ensure at least 1 specimen modality selected
        if not self.specimen_data.modalities_selected or len(self.specimen_data.modalities_selected) == 0:
            raise ValueError("PART A requires at least 1 specimen modality to be selected")
        
        # Ensure ISF core analytes present
        if not self.isf_monitor_data.core_analytes or len(self.isf_monitor_data.core_analytes) == 0:
            raise ValueError("ISF monitor data must include at least glucose and lactate core analytes")
        
        return self

    class Config:
        json_schema_extra = {
            "example": {
                "schema_version": "1.0.0",
                "submission_id": "uuid-12345",
                "user_id": 1,
                "specimen_data": {
                    "modalities_selected": ["blood", "saliva"],
                    "blood": [{"collection_datetime": "2026-01-29T08:00:00Z", "fasting_status": "fasting", "source_format": "pdf"}],
                    "saliva": [{"collection_type": "serial", "source_format": "manual_entry"}]
                },
                "isf_monitor_data": {
                    "core_analytes": [
                        {"name": "glucose", "values": [95.0], "timestamps": ["2026-01-29T12:00:00Z"], "unit": "mg/dL"}
                    ],
                    "signal_quality": {"calibration_status": "recent", "sensor_drift_score": 0.1, "noise_score": 0.05, "dropout_percentage": 2.0}
                },
                "vitals_data": {
                    "cardiovascular": {"heart_rate_resting": [65]},
                    "respiratory_temperature": {},
                    "sleep_recovery_activity": {"total_sleep_time_hours": 7.5}
                },
                "soap_profile": {
                    "demographics_anthropometrics": {"age": 35, "sex_at_birth": "male", "height_cm": 175.0, "weight_kg": 75.0},
                    "medical_history": {"conditions": ["prediabetes"]},
                    "medications_supplements": {"medications": [], "supplements": []},
                    "diet": {"pattern": "mediterranean", "sodium_intake": "normal", "hydration_intake": "normal", "caffeine": "moderate", "alcohol": "low", "meal_timing": "consistent"},
                    "activity_lifestyle": {"activity_level": "moderate", "shift_work": False, "sleep_schedule_consistency": "consistent", "nicotine_tobacco": "none"},
                    "symptoms": {"free_text": "Occasional fatigue", "structured": []}
                },
                "qualitative_encoding": {"rules_applied": [], "total_encoding_entries": 0}
            }
        }
