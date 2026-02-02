"""
Complete User Intake Data Models

Comprehensive Pydantic models for all user-provided health data:
- Demographics (age, sex, ethnicity - affects reference ranges)
- Anthropometrics (height, weight, body measurements)
- Medical History (PMH, surgeries, hospitalizations)
- Medications & Supplements (with interaction flags)
- Family History (genetic risk factors)
- Social/Lifestyle (smoking, alcohol, exercise, sleep)
- Symptoms/Complaints (structured symptom ontology)
- Allergies (drug, food, environmental)
- Dietary History (diet type, restrictions, patterns)
- Travel/Geographic (infectious disease risk)
- Psychological (stress, anxiety, depression indicators)

Created: 2026-02-02
Author: Helix 🧬
"""

from datetime import date, datetime
from typing import Optional, List, Dict, Any, Literal
from enum import Enum
from pydantic import BaseModel, Field, validator, root_validator
import re


# ============================================================================
# ENUMS
# ============================================================================

class BiologicalSex(str, Enum):
    MALE = "male"
    FEMALE = "female"
    INTERSEX = "intersex"


class GenderIdentity(str, Enum):
    MAN = "man"
    WOMAN = "woman"
    NON_BINARY = "non_binary"
    OTHER = "other"
    PREFER_NOT_TO_SAY = "prefer_not_to_say"


class Ethnicity(str, Enum):
    """Ethnicity categories - clinically relevant for reference ranges (e.g., eGFR)"""
    CAUCASIAN = "caucasian"
    AFRICAN_AMERICAN = "african_american"
    HISPANIC_LATINO = "hispanic_latino"
    ASIAN_EAST = "asian_east"
    ASIAN_SOUTH = "asian_south"
    ASIAN_SOUTHEAST = "asian_southeast"
    NATIVE_AMERICAN = "native_american"
    PACIFIC_ISLANDER = "pacific_islander"
    MIDDLE_EASTERN = "middle_eastern"
    MIXED = "mixed"
    OTHER = "other"
    PREFER_NOT_TO_SAY = "prefer_not_to_say"


class SmokingStatus(str, Enum):
    NEVER = "never"
    FORMER = "former"
    CURRENT_LIGHT = "current_light"  # <10 cigs/day
    CURRENT_MODERATE = "current_moderate"  # 10-20 cigs/day
    CURRENT_HEAVY = "current_heavy"  # >20 cigs/day
    VAPING_ONLY = "vaping_only"


class AlcoholFrequency(str, Enum):
    NEVER = "never"
    RARELY = "rarely"  # <1/month
    OCCASIONAL = "occasional"  # 1-4/month
    MODERATE = "moderate"  # 2-3/week
    FREQUENT = "frequent"  # 4-6/week
    DAILY = "daily"
    HEAVY = "heavy"  # >14 drinks/week men, >7 women


class ExerciseFrequency(str, Enum):
    SEDENTARY = "sedentary"  # <1x/week
    LIGHT = "light"  # 1-2x/week
    MODERATE = "moderate"  # 3-4x/week
    ACTIVE = "active"  # 5-6x/week
    VERY_ACTIVE = "very_active"  # daily
    ATHLETE = "athlete"  # 2x/day or professional


class SleepQuality(str, Enum):
    POOR = "poor"
    FAIR = "fair"
    GOOD = "good"
    EXCELLENT = "excellent"


class StressLevel(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    SEVERE = "severe"


class SymptomSeverity(str, Enum):
    NONE = "none"
    MILD = "mild"
    MODERATE = "moderate"
    SEVERE = "severe"
    CRITICAL = "critical"


class AllergyType(str, Enum):
    DRUG = "drug"
    FOOD = "food"
    ENVIRONMENTAL = "environmental"
    INSECT = "insect"
    LATEX = "latex"
    OTHER = "other"


class AllergyReaction(str, Enum):
    MILD = "mild"  # Rash, itching
    MODERATE = "moderate"  # Hives, swelling
    SEVERE = "severe"  # Breathing difficulty
    ANAPHYLAXIS = "anaphylaxis"  # Life-threatening


class DietType(str, Enum):
    OMNIVORE = "omnivore"
    VEGETARIAN = "vegetarian"
    VEGAN = "vegan"
    PESCATARIAN = "pescatarian"
    KETO = "keto"
    PALEO = "paleo"
    MEDITERRANEAN = "mediterranean"
    LOW_CARB = "low_carb"
    LOW_FAT = "low_fat"
    GLUTEN_FREE = "gluten_free"
    DAIRY_FREE = "dairy_free"
    OTHER = "other"


class MenstrualStatus(str, Enum):
    PREMENARCHE = "premenarche"
    REGULAR = "regular"
    IRREGULAR = "irregular"
    PERIMENOPAUSE = "perimenopause"
    POSTMENOPAUSE = "postmenopause"
    AMENORRHEA = "amenorrhea"
    NOT_APPLICABLE = "not_applicable"


class PregnancyStatus(str, Enum):
    NOT_PREGNANT = "not_pregnant"
    PREGNANT = "pregnant"
    POSTPARTUM = "postpartum"  # <6 weeks
    LACTATING = "lactating"
    NOT_APPLICABLE = "not_applicable"


# ============================================================================
# DEMOGRAPHICS
# ============================================================================

class Demographics(BaseModel):
    """Basic demographic information - critical for reference range interpretation"""
    
    date_of_birth: date = Field(..., description="Date of birth for age calculation")
    biological_sex: BiologicalSex = Field(..., description="Biological sex at birth - affects reference ranges")
    gender_identity: Optional[GenderIdentity] = Field(None, description="Gender identity")
    ethnicity: Optional[Ethnicity] = Field(None, description="Self-reported ethnicity - affects some reference ranges (e.g., eGFR)")
    country_of_birth: Optional[str] = Field(None, max_length=100)
    country_of_residence: Optional[str] = Field(None, max_length=100)
    
    @property
    def age_years(self) -> int:
        """Calculate current age in years"""
        today = date.today()
        age = today.year - self.date_of_birth.year
        if (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day):
            age -= 1
        return age
    
    @property
    def age_category(self) -> str:
        """Age category for reference range selection"""
        age = self.age_years
        if age < 1:
            return "infant"
        elif age < 3:
            return "toddler"
        elif age < 13:
            return "child"
        elif age < 18:
            return "adolescent"
        elif age < 40:
            return "young_adult"
        elif age < 65:
            return "adult"
        else:
            return "geriatric"


# ============================================================================
# ANTHROPOMETRICS
# ============================================================================

class Anthropometrics(BaseModel):
    """Body measurements - affects BMI, reference ranges, dosing"""
    
    height_cm: float = Field(..., gt=0, lt=300, description="Height in centimeters")
    weight_kg: float = Field(..., gt=0, lt=700, description="Weight in kilograms")
    waist_circumference_cm: Optional[float] = Field(None, gt=0, lt=300, description="Waist circumference (metabolic risk)")
    hip_circumference_cm: Optional[float] = Field(None, gt=0, lt=300, description="Hip circumference")
    body_fat_percent: Optional[float] = Field(None, ge=0, le=70, description="Body fat percentage if measured")
    measurement_date: Optional[date] = Field(None, description="Date of measurements")
    
    @property
    def bmi(self) -> float:
        """Calculate BMI"""
        height_m = self.height_cm / 100
        return round(self.weight_kg / (height_m ** 2), 1)
    
    @property
    def bmi_category(self) -> str:
        """WHO BMI classification"""
        bmi = self.bmi
        if bmi < 18.5:
            return "underweight"
        elif bmi < 25:
            return "normal"
        elif bmi < 30:
            return "overweight"
        elif bmi < 35:
            return "obese_class_1"
        elif bmi < 40:
            return "obese_class_2"
        else:
            return "obese_class_3"
    
    @property
    def waist_to_hip_ratio(self) -> Optional[float]:
        """Waist-to-hip ratio (cardiometabolic risk)"""
        if self.waist_circumference_cm and self.hip_circumference_cm:
            return round(self.waist_circumference_cm / self.hip_circumference_cm, 2)
        return None
    
    @property
    def bsa_m2(self) -> float:
        """Body surface area (Mosteller formula) - for drug dosing"""
        return round(((self.height_cm * self.weight_kg) / 3600) ** 0.5, 2)


# ============================================================================
# VITALS
# ============================================================================

class VitalSigns(BaseModel):
    """Current vital signs measurement"""
    
    measurement_datetime: datetime = Field(..., description="When vitals were measured")
    systolic_bp_mmhg: Optional[int] = Field(None, ge=50, le=300, description="Systolic blood pressure")
    diastolic_bp_mmhg: Optional[int] = Field(None, ge=30, le=200, description="Diastolic blood pressure")
    heart_rate_bpm: Optional[int] = Field(None, ge=20, le=300, description="Heart rate")
    respiratory_rate_brpm: Optional[int] = Field(None, ge=4, le=60, description="Respiratory rate")
    temperature_celsius: Optional[float] = Field(None, ge=30, le=45, description="Body temperature")
    spo2_percent: Optional[float] = Field(None, ge=50, le=100, description="Oxygen saturation")
    pain_scale_0_10: Optional[int] = Field(None, ge=0, le=10, description="Pain level")
    
    @property
    def mean_arterial_pressure(self) -> Optional[float]:
        """Calculate MAP if BP available"""
        if self.systolic_bp_mmhg and self.diastolic_bp_mmhg:
            return round(self.diastolic_bp_mmhg + (self.systolic_bp_mmhg - self.diastolic_bp_mmhg) / 3, 1)
        return None
    
    @property
    def pulse_pressure(self) -> Optional[int]:
        """Pulse pressure (SBP - DBP)"""
        if self.systolic_bp_mmhg and self.diastolic_bp_mmhg:
            return self.systolic_bp_mmhg - self.diastolic_bp_mmhg
        return None
    
    @property
    def bp_category(self) -> Optional[str]:
        """ACC/AHA blood pressure classification"""
        if not self.systolic_bp_mmhg or not self.diastolic_bp_mmhg:
            return None
        sbp, dbp = self.systolic_bp_mmhg, self.diastolic_bp_mmhg
        if sbp < 120 and dbp < 80:
            return "normal"
        elif sbp < 130 and dbp < 80:
            return "elevated"
        elif sbp < 140 or dbp < 90:
            return "stage_1_hypertension"
        elif sbp < 180 and dbp < 120:
            return "stage_2_hypertension"
        else:
            return "hypertensive_crisis"


# ============================================================================
# MEDICAL HISTORY
# ============================================================================

class Diagnosis(BaseModel):
    """A medical diagnosis"""
    
    condition_name: str = Field(..., max_length=500)
    icd10_code: Optional[str] = Field(None, regex=r"^[A-Z]\d{2}(\.\d{1,4})?$")
    diagnosis_date: Optional[date] = None
    resolution_date: Optional[date] = Field(None, description="If condition resolved")
    is_active: bool = True
    is_chronic: bool = False
    severity: Optional[SymptomSeverity] = None
    managed_by: Optional[str] = Field(None, description="Specialist/provider managing condition")
    notes: Optional[str] = Field(None, max_length=2000)


class Surgery(BaseModel):
    """Surgical history"""
    
    procedure_name: str = Field(..., max_length=500)
    cpt_code: Optional[str] = None
    surgery_date: Optional[date] = None
    hospital: Optional[str] = Field(None, max_length=200)
    surgeon: Optional[str] = Field(None, max_length=200)
    complications: Optional[List[str]] = None
    notes: Optional[str] = Field(None, max_length=2000)


class Hospitalization(BaseModel):
    """Hospitalization history"""
    
    reason: str = Field(..., max_length=500)
    admission_date: Optional[date] = None
    discharge_date: Optional[date] = None
    hospital: Optional[str] = Field(None, max_length=200)
    icu_stay: bool = False
    icu_days: Optional[int] = Field(None, ge=0)
    notes: Optional[str] = Field(None, max_length=2000)


class MedicalHistory(BaseModel):
    """Complete past medical history"""
    
    diagnoses: List[Diagnosis] = Field(default_factory=list)
    surgeries: List[Surgery] = Field(default_factory=list)
    hospitalizations: List[Hospitalization] = Field(default_factory=list)
    blood_transfusions: bool = False
    organ_transplant: bool = False
    transplant_details: Optional[str] = Field(None, max_length=500)
    cancer_history: bool = False
    cancer_details: Optional[List[str]] = None
    
    @property
    def active_conditions(self) -> List[Diagnosis]:
        return [d for d in self.diagnoses if d.is_active]
    
    @property
    def chronic_conditions(self) -> List[Diagnosis]:
        return [d for d in self.diagnoses if d.is_chronic]


# ============================================================================
# MEDICATIONS & SUPPLEMENTS
# ============================================================================

class Medication(BaseModel):
    """Current medication"""
    
    name: str = Field(..., max_length=300)
    generic_name: Optional[str] = Field(None, max_length=300)
    rxnorm_code: Optional[str] = None
    ndc_code: Optional[str] = None
    dose: Optional[str] = Field(None, max_length=100)  # e.g., "10mg"
    dose_value: Optional[float] = None
    dose_unit: Optional[str] = None
    frequency: Optional[str] = Field(None, max_length=100)  # e.g., "twice daily"
    route: Optional[str] = Field(None, max_length=50)  # oral, topical, injection, etc.
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_current: bool = True
    prescriber: Optional[str] = Field(None, max_length=200)
    indication: Optional[str] = Field(None, max_length=500)
    is_prn: bool = False  # As needed
    notes: Optional[str] = Field(None, max_length=1000)
    
    # Flags for analysis
    affects_glucose: bool = False
    affects_blood_pressure: bool = False
    affects_heart_rate: bool = False
    affects_lipids: bool = False
    affects_liver: bool = False
    affects_kidney: bool = False
    affects_electrolytes: bool = False
    affects_thyroid: bool = False
    affects_hormones: bool = False
    is_biotin_containing: bool = False  # Interferes with many lab tests


class Supplement(BaseModel):
    """Dietary supplement / vitamin / herbal"""
    
    name: str = Field(..., max_length=300)
    brand: Optional[str] = Field(None, max_length=200)
    dose: Optional[str] = Field(None, max_length=100)
    frequency: Optional[str] = Field(None, max_length=100)
    is_current: bool = True
    start_date: Optional[date] = None
    reason: Optional[str] = Field(None, max_length=500)
    
    # Flags for lab interference
    affects_lab_values: bool = False
    interfering_tests: Optional[List[str]] = None


class MedicationList(BaseModel):
    """Complete medication and supplement list"""
    
    medications: List[Medication] = Field(default_factory=list)
    supplements: List[Supplement] = Field(default_factory=list)
    takes_otc_nsaids: bool = False
    takes_otc_antacids: bool = False
    takes_otc_antihistamines: bool = False
    last_updated: Optional[datetime] = None
    
    @property
    def current_medications(self) -> List[Medication]:
        return [m for m in self.medications if m.is_current]
    
    @property
    def current_supplements(self) -> List[Supplement]:
        return [s for s in self.supplements if s.is_current]
    
    @property
    def biotin_exposure(self) -> bool:
        """Check for biotin in any supplement (common lab interferent)"""
        biotin_keywords = ["biotin", "b7", "hair skin nail", "beauty"]
        for s in self.current_supplements:
            if any(kw in s.name.lower() for kw in biotin_keywords):
                return True
        return any(m.is_biotin_containing for m in self.current_medications)


# ============================================================================
# FAMILY HISTORY
# ============================================================================

class FamilyMember(BaseModel):
    """Family member with health conditions"""
    
    relationship: str = Field(..., description="mother, father, sister, brother, maternal_grandmother, etc.")
    is_alive: Optional[bool] = None
    age_at_death: Optional[int] = Field(None, ge=0, le=150)
    cause_of_death: Optional[str] = Field(None, max_length=500)
    conditions: List[str] = Field(default_factory=list, description="List of diagnosed conditions")
    age_at_diagnosis: Optional[Dict[str, int]] = Field(None, description="Condition -> age at diagnosis")


class FamilyHistory(BaseModel):
    """Complete family medical history"""
    
    members: List[FamilyMember] = Field(default_factory=list)
    
    # Quick flags for common hereditary conditions
    heart_disease: bool = False
    heart_disease_early_onset: bool = False  # <55 male, <65 female
    stroke: bool = False
    type_2_diabetes: bool = False
    type_1_diabetes: bool = False
    hypertension: bool = False
    cancer: bool = False
    cancer_types: Optional[List[str]] = None
    breast_cancer: bool = False
    ovarian_cancer: bool = False
    colon_cancer: bool = False
    prostate_cancer: bool = False
    lung_cancer: bool = False
    alzheimers_dementia: bool = False
    parkinsons: bool = False
    autoimmune_disease: bool = False
    autoimmune_types: Optional[List[str]] = None
    mental_health_conditions: bool = False
    mental_health_types: Optional[List[str]] = None
    sudden_cardiac_death: bool = False
    blood_clots_dvt_pe: bool = False
    kidney_disease: bool = False
    liver_disease: bool = False
    
    notes: Optional[str] = Field(None, max_length=2000)


# ============================================================================
# SOCIAL HISTORY / LIFESTYLE
# ============================================================================

class SocialHistory(BaseModel):
    """Social determinants and lifestyle factors"""
    
    # Smoking
    smoking_status: SmokingStatus = SmokingStatus.NEVER
    pack_years: Optional[float] = Field(None, ge=0, description="Pack-years for smokers")
    quit_date: Optional[date] = Field(None, description="Date quit smoking if former")
    
    # Alcohol
    alcohol_frequency: AlcoholFrequency = AlcoholFrequency.NEVER
    drinks_per_week: Optional[int] = Field(None, ge=0)
    alcohol_type_preference: Optional[List[str]] = None  # beer, wine, spirits
    
    # Substances
    recreational_drug_use: bool = False
    drug_types: Optional[List[str]] = None
    cannabis_use: bool = False
    cannabis_frequency: Optional[str] = None
    
    # Caffeine
    caffeine_drinks_per_day: Optional[int] = Field(None, ge=0)
    caffeine_sources: Optional[List[str]] = None  # coffee, tea, energy drinks
    
    # Occupation
    occupation: Optional[str] = Field(None, max_length=200)
    occupation_category: Optional[str] = None  # sedentary, light, moderate, heavy labor
    work_hours_per_week: Optional[int] = Field(None, ge=0, le=168)
    night_shift_work: bool = False
    occupational_hazards: Optional[List[str]] = None
    
    # Living situation
    lives_alone: bool = False
    has_caregiver: bool = False
    housing_type: Optional[str] = None  # house, apartment, assisted_living, etc.
    
    # Stress
    perceived_stress_level: StressLevel = StressLevel.MODERATE
    major_life_stressors: Optional[List[str]] = None
    
    # Support
    social_support_level: Optional[str] = None  # strong, moderate, limited, none
    
    @property
    def smoking_risk_category(self) -> str:
        """Risk categorization for smoking"""
        if self.smoking_status == SmokingStatus.NEVER:
            return "no_risk"
        elif self.smoking_status == SmokingStatus.FORMER:
            if self.quit_date and (date.today() - self.quit_date).days > 3650:  # >10 years
                return "low_risk"
            return "moderate_risk"
        else:
            return "high_risk"


# ============================================================================
# EXERCISE & PHYSICAL ACTIVITY
# ============================================================================

class ExerciseHistory(BaseModel):
    """Physical activity and exercise patterns"""
    
    exercise_frequency: ExerciseFrequency = ExerciseFrequency.SEDENTARY
    minutes_per_week_cardio: Optional[int] = Field(None, ge=0)
    minutes_per_week_strength: Optional[int] = Field(None, ge=0)
    minutes_per_week_flexibility: Optional[int] = Field(None, ge=0)
    
    preferred_activities: Optional[List[str]] = None  # running, swimming, weights, yoga, etc.
    
    # Objective measures if available
    average_daily_steps: Optional[int] = Field(None, ge=0)
    vo2_max_ml_kg_min: Optional[float] = Field(None, ge=0)
    
    # Limitations
    exercise_limitations: Optional[List[str]] = None
    uses_mobility_aid: bool = False
    mobility_aid_type: Optional[str] = None
    
    @property
    def meets_who_guidelines(self) -> bool:
        """Check if meets WHO physical activity guidelines (150 min moderate or 75 min vigorous)"""
        total_minutes = (self.minutes_per_week_cardio or 0) + (self.minutes_per_week_strength or 0)
        return total_minutes >= 150


# ============================================================================
# SLEEP
# ============================================================================

class SleepHistory(BaseModel):
    """Sleep patterns and quality"""
    
    average_sleep_hours: float = Field(..., ge=0, le=24)
    typical_bedtime: Optional[str] = Field(None, regex=r"^\d{2}:\d{2}$")  # HH:MM
    typical_waketime: Optional[str] = Field(None, regex=r"^\d{2}:\d{2}$")
    sleep_quality: SleepQuality = SleepQuality.FAIR
    
    # Sleep issues
    difficulty_falling_asleep: bool = False
    difficulty_staying_asleep: bool = False
    early_morning_awakening: bool = False
    snoring: bool = False
    witnessed_apneas: bool = False
    restless_legs: bool = False
    daytime_sleepiness: bool = False
    uses_sleep_aids: bool = False
    sleep_aid_type: Optional[str] = None
    
    # Diagnosed conditions
    diagnosed_sleep_apnea: bool = False
    uses_cpap: bool = False
    cpap_compliance_percent: Optional[float] = Field(None, ge=0, le=100)
    diagnosed_insomnia: bool = False
    
    @property
    def sleep_adequacy(self) -> str:
        """Assess sleep duration adequacy (adult guidelines: 7-9 hours)"""
        if self.average_sleep_hours < 6:
            return "severely_insufficient"
        elif self.average_sleep_hours < 7:
            return "insufficient"
        elif self.average_sleep_hours <= 9:
            return "adequate"
        else:
            return "excessive"


# ============================================================================
# DIETARY HISTORY
# ============================================================================

class DietaryHistory(BaseModel):
    """Dietary patterns and nutrition"""
    
    diet_type: DietType = DietType.OMNIVORE
    diet_restrictions: Optional[List[str]] = None  # gluten-free, dairy-free, nut-free, etc.
    
    # Meal patterns
    meals_per_day: Optional[int] = Field(None, ge=0, le=10)
    snacks_per_day: Optional[int] = Field(None, ge=0, le=10)
    skips_breakfast: bool = False
    regular_meal_times: bool = True
    eats_late_night: bool = False
    
    # Specific intakes
    fruits_servings_daily: Optional[int] = Field(None, ge=0)
    vegetables_servings_daily: Optional[int] = Field(None, ge=0)
    water_liters_daily: Optional[float] = Field(None, ge=0)
    sugary_drinks_daily: Optional[int] = Field(None, ge=0)
    fast_food_times_weekly: Optional[int] = Field(None, ge=0)
    processed_food_frequency: Optional[str] = None  # rarely, sometimes, often, daily
    
    # Fasting
    practices_intermittent_fasting: bool = False
    fasting_protocol: Optional[str] = None  # 16:8, 18:6, OMAD, 5:2, etc.
    
    # Appetite
    recent_appetite_change: bool = False
    appetite_change_direction: Optional[str] = None  # increased, decreased
    recent_weight_change_kg: Optional[float] = None
    
    # Eating behaviors
    history_of_eating_disorder: bool = False
    eating_disorder_type: Optional[str] = None
    
    notes: Optional[str] = Field(None, max_length=2000)


# ============================================================================
# ALLERGIES
# ============================================================================

class Allergy(BaseModel):
    """Single allergy record"""
    
    allergen: str = Field(..., max_length=300)
    allergy_type: AllergyType = AllergyType.OTHER
    reaction_type: AllergyReaction = AllergyReaction.MILD
    reaction_description: Optional[str] = Field(None, max_length=500)
    confirmed_by_testing: bool = False
    date_first_reaction: Optional[date] = None
    carries_epipen: bool = False


class AllergyList(BaseModel):
    """Complete allergy list"""
    
    allergies: List[Allergy] = Field(default_factory=list)
    no_known_allergies: bool = False
    no_known_drug_allergies: bool = False
    
    @property
    def drug_allergies(self) -> List[Allergy]:
        return [a for a in self.allergies if a.allergy_type == AllergyType.DRUG]
    
    @property
    def food_allergies(self) -> List[Allergy]:
        return [a for a in self.allergies if a.allergy_type == AllergyType.FOOD]
    
    @property
    def has_anaphylaxis_risk(self) -> bool:
        return any(a.reaction_type == AllergyReaction.ANAPHYLAXIS for a in self.allergies)


# ============================================================================
# SYMPTOMS
# ============================================================================

class Symptom(BaseModel):
    """Individual symptom"""
    
    symptom_name: str = Field(..., max_length=300)
    snomed_code: Optional[str] = None
    severity: SymptomSeverity = SymptomSeverity.MILD
    onset_date: Optional[date] = None
    duration_description: Optional[str] = Field(None, max_length=200)  # e.g., "2 weeks", "chronic"
    frequency: Optional[str] = Field(None, max_length=100)  # constant, intermittent, episodic
    location: Optional[str] = Field(None, max_length=200)
    character: Optional[str] = Field(None, max_length=200)  # sharp, dull, burning, etc.
    triggers: Optional[List[str]] = None
    alleviating_factors: Optional[List[str]] = None
    aggravating_factors: Optional[List[str]] = None
    associated_symptoms: Optional[List[str]] = None
    impact_on_daily_life: Optional[str] = Field(None, max_length=500)
    notes: Optional[str] = Field(None, max_length=1000)


class SymptomHistory(BaseModel):
    """Current symptoms and chief complaints"""
    
    chief_complaint: Optional[str] = Field(None, max_length=500)
    symptoms: List[Symptom] = Field(default_factory=list)
    symptom_onset_date: Optional[date] = None
    is_asymptomatic: bool = False
    
    # Review of systems flags
    ros_constitutional: Optional[Dict[str, bool]] = None  # fever, chills, weight loss, fatigue
    ros_cardiovascular: Optional[Dict[str, bool]] = None  # chest pain, palpitations, edema
    ros_respiratory: Optional[Dict[str, bool]] = None  # cough, dyspnea, wheezing
    ros_gastrointestinal: Optional[Dict[str, bool]] = None  # nausea, vomiting, diarrhea, constipation
    ros_genitourinary: Optional[Dict[str, bool]] = None  # dysuria, frequency, hematuria
    ros_musculoskeletal: Optional[Dict[str, bool]] = None  # joint pain, muscle pain, weakness
    ros_neurological: Optional[Dict[str, bool]] = None  # headache, dizziness, numbness
    ros_psychiatric: Optional[Dict[str, bool]] = None  # anxiety, depression, insomnia
    ros_skin: Optional[Dict[str, bool]] = None  # rash, itching, lesions


# ============================================================================
# REPRODUCTIVE HEALTH
# ============================================================================

class ReproductiveHealth(BaseModel):
    """Reproductive health information"""
    
    # For all
    sexual_activity: Optional[bool] = None
    contraception_use: bool = False
    contraception_method: Optional[str] = Field(None, max_length=200)
    
    # Female-specific
    menstrual_status: MenstrualStatus = MenstrualStatus.NOT_APPLICABLE
    last_menstrual_period: Optional[date] = None
    cycle_length_days: Optional[int] = Field(None, ge=14, le=90)
    cycle_regularity: Optional[str] = None  # regular, irregular
    menstrual_symptoms: Optional[List[str]] = None  # cramps, heavy bleeding, PMS
    
    pregnancy_status: PregnancyStatus = PregnancyStatus.NOT_APPLICABLE
    due_date: Optional[date] = None
    gestational_weeks: Optional[int] = Field(None, ge=0, le=45)
    gravida: Optional[int] = Field(None, ge=0, description="Total pregnancies")
    para: Optional[int] = Field(None, ge=0, description="Live births")
    
    menopause_age: Optional[int] = Field(None, ge=30, le=70)
    on_hrt: bool = False
    hrt_type: Optional[str] = None
    
    # Fertility
    history_of_infertility: bool = False
    fertility_treatments: Optional[List[str]] = None
    
    # Male-specific
    erectile_dysfunction: Optional[bool] = None
    prostate_issues: Optional[bool] = None


# ============================================================================
# TRAVEL HISTORY
# ============================================================================

class TravelHistory(BaseModel):
    """Recent travel for infectious disease risk assessment"""
    
    recent_international_travel: bool = False
    countries_visited_6_months: Optional[List[str]] = None
    countries_visited_12_months: Optional[List[str]] = None
    tropical_travel: bool = False
    malaria_endemic_area: bool = False
    tick_exposure: bool = False
    animal_exposure: bool = False
    sick_contacts: bool = False
    healthcare_work: bool = False
    
    # Vaccinations
    up_to_date_on_vaccines: Optional[bool] = None
    recent_vaccines: Optional[List[str]] = None
    covid_vaccinated: Optional[bool] = None
    covid_vaccine_doses: Optional[int] = Field(None, ge=0)
    flu_vaccine_this_year: Optional[bool] = None


# ============================================================================
# PSYCHOLOGICAL
# ============================================================================

class PsychologicalHistory(BaseModel):
    """Mental health and psychological factors"""
    
    # Current mental health
    current_stress_level: StressLevel = StressLevel.MODERATE
    current_anxiety_level: SymptomSeverity = SymptomSeverity.NONE
    current_depression_level: SymptomSeverity = SymptomSeverity.NONE
    
    # Screening scores if available
    phq9_score: Optional[int] = Field(None, ge=0, le=27, description="PHQ-9 depression score")
    gad7_score: Optional[int] = Field(None, ge=0, le=21, description="GAD-7 anxiety score")
    pss_score: Optional[int] = Field(None, ge=0, le=40, description="Perceived Stress Scale")
    
    # History
    history_of_depression: bool = False
    history_of_anxiety: bool = False
    history_of_ptsd: bool = False
    history_of_other_mental_health: Optional[List[str]] = None
    
    # Treatment
    currently_in_therapy: bool = False
    therapy_type: Optional[str] = None  # CBT, psychodynamic, etc.
    on_psychiatric_medication: bool = False
    psychiatric_medications: Optional[List[str]] = None
    
    # Risk assessment
    history_of_suicidal_ideation: bool = False
    history_of_suicide_attempt: bool = False
    current_suicidal_ideation: bool = False
    
    notes: Optional[str] = Field(None, max_length=2000)


# ============================================================================
# COMPLETE INTAKE FORM
# ============================================================================

class CompleteUserIntake(BaseModel):
    """
    Complete user intake form combining all sections.
    This is the master schema for collecting comprehensive health data.
    """
    
    # Metadata
    intake_id: Optional[str] = None
    user_id: str = Field(..., description="User identifier")
    intake_datetime: datetime = Field(default_factory=datetime.utcnow)
    intake_version: str = "1.0.0"
    
    # All sections
    demographics: Demographics
    anthropometrics: Anthropometrics
    current_vitals: Optional[VitalSigns] = None
    medical_history: MedicalHistory = Field(default_factory=MedicalHistory)
    medications: MedicationList = Field(default_factory=MedicationList)
    family_history: FamilyHistory = Field(default_factory=FamilyHistory)
    social_history: SocialHistory = Field(default_factory=SocialHistory)
    exercise: ExerciseHistory = Field(default_factory=ExerciseHistory)
    sleep: SleepHistory = Field(default_factory=lambda: SleepHistory(average_sleep_hours=7))
    diet: DietaryHistory = Field(default_factory=DietaryHistory)
    allergies: AllergyList = Field(default_factory=AllergyList)
    symptoms: SymptomHistory = Field(default_factory=SymptomHistory)
    reproductive: ReproductiveHealth = Field(default_factory=ReproductiveHealth)
    travel: TravelHistory = Field(default_factory=TravelHistory)
    psychological: PsychologicalHistory = Field(default_factory=PsychologicalHistory)
    
    # Completeness tracking
    sections_completed: Optional[List[str]] = None
    completion_percent: Optional[float] = Field(None, ge=0, le=100)
    
    def calculate_completeness(self) -> float:
        """Calculate how complete the intake is"""
        required_sections = [
            self.demographics,
            self.anthropometrics,
            self.medical_history,
            self.medications,
            self.allergies
        ]
        optional_sections = [
            self.current_vitals,
            self.family_history.members,
            self.social_history,
            self.exercise,
            self.sleep,
            self.diet,
            self.symptoms.symptoms,
            self.reproductive,
            self.travel,
            self.psychological
        ]
        
        # Required sections weight 60%, optional 40%
        required_complete = sum(1 for s in required_sections if s) / len(required_sections)
        optional_complete = sum(1 for s in optional_sections if s) / len(optional_sections)
        
        return round(required_complete * 60 + optional_complete * 40, 1)
    
    @property
    def age_years(self) -> int:
        return self.demographics.age_years
    
    @property
    def bmi(self) -> float:
        return self.anthropometrics.bmi
    
    @property
    def is_high_risk_profile(self) -> bool:
        """Quick assessment of high-risk features"""
        risks = [
            self.demographics.age_years > 65,
            self.anthropometrics.bmi > 30,
            len(self.medical_history.chronic_conditions) > 2,
            self.family_history.heart_disease_early_onset,
            self.social_history.smoking_status not in [SmokingStatus.NEVER, SmokingStatus.FORMER],
            self.psychological.current_depression_level in [SymptomSeverity.MODERATE, SymptomSeverity.SEVERE]
        ]
        return sum(risks) >= 2


# ============================================================================
# EXPORT
# ============================================================================

__all__ = [
    # Enums
    "BiologicalSex", "GenderIdentity", "Ethnicity", "SmokingStatus", 
    "AlcoholFrequency", "ExerciseFrequency", "SleepQuality", "StressLevel",
    "SymptomSeverity", "AllergyType", "AllergyReaction", "DietType",
    "MenstrualStatus", "PregnancyStatus",
    # Models
    "Demographics", "Anthropometrics", "VitalSigns",
    "Diagnosis", "Surgery", "Hospitalization", "MedicalHistory",
    "Medication", "Supplement", "MedicationList",
    "FamilyMember", "FamilyHistory",
    "SocialHistory", "ExerciseHistory", "SleepHistory", "DietaryHistory",
    "Allergy", "AllergyList",
    "Symptom", "SymptomHistory",
    "ReproductiveHealth", "TravelHistory", "PsychologicalHistory",
    "CompleteUserIntake"
]
