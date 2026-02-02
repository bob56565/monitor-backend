"""
Deterministic Derived Feature Engine.

Implements Requirement A2.3: Deterministic, non-ML derived clinical features.
- Always compute deterministic clinical calculations
- No ML allowed in this module
- Calculators gracefully skip if inputs missing
- Results are additive and don't replace existing outputs
"""

from typing import Dict, Optional, List, Any
from pydantic import BaseModel, Field
from enum import Enum
import math
import logging

logger = logging.getLogger(__name__)


class DerivedFeatureType(str, Enum):
    """Types of derived features."""
    RENAL = "renal"
    ELECTROLYTE = "electrolyte"
    LIPID = "lipid"
    BLOOD_PRESSURE = "blood_pressure"
    GLUCOSE = "glucose"
    HEMATOLOGY = "hematology"


class DerivedFeature(BaseModel):
    """A single derived feature result."""
    feature_name: str
    feature_type: DerivedFeatureType
    value: Optional[float] = None
    unit: Optional[str] = None
    formula_used: str
    inputs_used: Dict[str, Any] = Field(default_factory=dict)
    interpretation: Optional[str] = None
    reference_range: Optional[Dict[str, float]] = None
    is_within_normal: Optional[bool] = None
    clinical_significance: Optional[str] = None
    computation_timestamp: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "feature_name": "eGFR_CKD_EPI",
                "feature_type": "renal",
                "value": 92.5,
                "unit": "mL/min/1.73m²",
                "formula_used": "CKD-EPI_2021",
                "inputs_used": {"creatinine": 1.0, "age": 45, "sex": "F"},
                "is_within_normal": True
            }
        }


class DerivedFeaturePack(BaseModel):
    """Collection of all derived features for a run."""
    run_id: str
    schema_version: str = "derived_features_v1.0"
    
    # Derived features by type
    renal_features: List[DerivedFeature] = Field(default_factory=list)
    electrolyte_features: List[DerivedFeature] = Field(default_factory=list)
    lipid_features: List[DerivedFeature] = Field(default_factory=list)
    blood_pressure_features: List[DerivedFeature] = Field(default_factory=list)
    glucose_features: List[DerivedFeature] = Field(default_factory=list)
    hematology_features: List[DerivedFeature] = Field(default_factory=list)
    
    # Metadata
    features_computed: int = 0
    features_skipped: int = 0
    skipped_reasons: List[str] = Field(default_factory=list)


# ============================================================================
# RENAL CALCULATORS
# ============================================================================

def calculate_egfr_ckd_epi(
    creatinine_mg_dl: float,
    age: int,
    sex: str,
    race: Optional[str] = None
) -> Optional[DerivedFeature]:
    """
    Calculate eGFR using CKD-EPI equation (2021 version without race).
    
    Formula:
    eGFR = 142 × min(Scr/κ, 1)^α × max(Scr/κ, 1)^-1.200 × 0.9938^Age × (1.012 if female)
    
    Where:
    - κ = 0.7 (females) or 0.9 (males)
    - α = -0.241 (females) or -0.302 (males)
    """
    try:
        if sex.upper() == "F":
            kappa = 0.7
            alpha = -0.241
            sex_factor = 1.012
        else:
            kappa = 0.9
            alpha = -0.302
            sex_factor = 1.0
        
        scr_kappa = creatinine_mg_dl / kappa
        min_term = min(scr_kappa, 1.0) ** alpha
        max_term = max(scr_kappa, 1.0) ** -1.200
        age_factor = 0.9938 ** age
        
        egfr = 142 * min_term * max_term * age_factor * sex_factor
        
        # Interpret
        if egfr >= 90:
            interpretation = "Normal or high (Stage 1)"
            is_normal = True
        elif egfr >= 60:
            interpretation = "Mildly decreased (Stage 2)"
            is_normal = True
        elif egfr >= 45:
            interpretation = "Mildly to moderately decreased (Stage 3a)"
            is_normal = False
        elif egfr >= 30:
            interpretation = "Moderately to severely decreased (Stage 3b)"
            is_normal = False
        elif egfr >= 15:
            interpretation = "Severely decreased (Stage 4)"
            is_normal = False
        else:
            interpretation = "Kidney failure (Stage 5)"
            is_normal = False
        
        from datetime import datetime
        
        return DerivedFeature(
            feature_name="eGFR_CKD_EPI",
            feature_type=DerivedFeatureType.RENAL,
            value=round(egfr, 1),
            unit="mL/min/1.73m²",
            formula_used="CKD-EPI_2021",
            inputs_used={"creatinine_mg_dl": creatinine_mg_dl, "age": age, "sex": sex},
            interpretation=interpretation,
            reference_range={"low": 90, "high": 999},
            is_within_normal=is_normal,
            computation_timestamp=datetime.utcnow().isoformat(),
        )
    except Exception as e:
        logger.error(f"Error calculating eGFR: {e}")
        return None


def calculate_bun_creatinine_ratio(
    bun_mg_dl: float,
    creatinine_mg_dl: float
) -> Optional[DerivedFeature]:
    """Calculate BUN/Creatinine ratio."""
    try:
        ratio = bun_mg_dl / creatinine_mg_dl
        
        # Interpret
        if 10 <= ratio <= 20:
            interpretation = "Normal"
            is_normal = True
        elif ratio < 10:
            interpretation = "Low - possible overhydration or low protein intake"
            is_normal = False
        else:
            interpretation = "Elevated - possible dehydration, GI bleed, or renal hypoperfusion"
            is_normal = False
        
        from datetime import datetime
        
        return DerivedFeature(
            feature_name="BUN_Creatinine_Ratio",
            feature_type=DerivedFeatureType.RENAL,
            value=round(ratio, 1),
            unit="ratio",
            formula_used="BUN/Creatinine",
            inputs_used={"bun_mg_dl": bun_mg_dl, "creatinine_mg_dl": creatinine_mg_dl},
            interpretation=interpretation,
            reference_range={"low": 10, "high": 20},
            is_within_normal=is_normal,
            computation_timestamp=datetime.utcnow().isoformat(),
        )
    except Exception as e:
        logger.error(f"Error calculating BUN/Creatinine ratio: {e}")
        return None


# ============================================================================
# ELECTROLYTE CALCULATORS
# ============================================================================

def calculate_anion_gap(
    sodium: float,
    chloride: float,
    bicarbonate: float
) -> Optional[DerivedFeature]:
    """Calculate anion gap."""
    try:
        gap = sodium - (chloride + bicarbonate)
        
        # Interpret (normal: 8-12 for older method, 3-11 for albumin-corrected)
        if 8 <= gap <= 12:
            interpretation = "Normal"
            is_normal = True
        elif gap < 8:
            interpretation = "Low - possible hypoalbuminemia or lab error"
            is_normal = False
        elif gap <= 16:
            interpretation = "Mildly elevated"
            is_normal = False
        else:
            interpretation = "Elevated - possible metabolic acidosis"
            is_normal = False
        
        from datetime import datetime
        
        return DerivedFeature(
            feature_name="Anion_Gap",
            feature_type=DerivedFeatureType.ELECTROLYTE,
            value=round(gap, 1),
            unit="mmol/L",
            formula_used="Na - (Cl + HCO3)",
            inputs_used={"sodium": sodium, "chloride": chloride, "bicarbonate": bicarbonate},
            interpretation=interpretation,
            reference_range={"low": 8, "high": 12},
            is_within_normal=is_normal,
            computation_timestamp=datetime.utcnow().isoformat(),
        )
    except Exception as e:
        logger.error(f"Error calculating anion gap: {e}")
        return None


def calculate_albumin_corrected_anion_gap(
    anion_gap: float,
    albumin_g_dl: float,
    normal_albumin: float = 4.0
) -> Optional[DerivedFeature]:
    """Calculate albumin-corrected anion gap."""
    try:
        corrected_gap = anion_gap + 2.5 * (normal_albumin - albumin_g_dl)
        
        if 3 <= corrected_gap <= 11:
            interpretation = "Normal (albumin-corrected)"
            is_normal = True
        else:
            interpretation = "Abnormal (albumin-corrected)"
            is_normal = False
        
        from datetime import datetime
        
        return DerivedFeature(
            feature_name="Albumin_Corrected_Anion_Gap",
            feature_type=DerivedFeatureType.ELECTROLYTE,
            value=round(corrected_gap, 1),
            unit="mmol/L",
            formula_used="AG + 2.5*(4.0 - albumin)",
            inputs_used={"anion_gap": anion_gap, "albumin_g_dl": albumin_g_dl},
            interpretation=interpretation,
            reference_range={"low": 3, "high": 11},
            is_within_normal=is_normal,
            computation_timestamp=datetime.utcnow().isoformat(),
        )
    except Exception as e:
        logger.error(f"Error calculating albumin-corrected anion gap: {e}")
        return None


def calculate_estimated_osmolarity(
    sodium: float,
    glucose_mg_dl: float,
    bun_mg_dl: float
) -> Optional[DerivedFeature]:
    """Calculate estimated serum osmolarity."""
    try:
        osmolarity = 2 * sodium + glucose_mg_dl / 18 + bun_mg_dl / 2.8
        
        if 275 <= osmolarity <= 295:
            interpretation = "Normal"
            is_normal = True
        elif osmolarity < 275:
            interpretation = "Low - possible hyponatremia or overhydration"
            is_normal = False
        else:
            interpretation = "High - possible hypernatremia or dehydration"
            is_normal = False
        
        from datetime import datetime
        
        return DerivedFeature(
            feature_name="Estimated_Osmolarity",
            feature_type=DerivedFeatureType.ELECTROLYTE,
            value=round(osmolarity, 1),
            unit="mOsm/kg",
            formula_used="2*Na + Glucose/18 + BUN/2.8",
            inputs_used={"sodium": sodium, "glucose_mg_dl": glucose_mg_dl, "bun_mg_dl": bun_mg_dl},
            interpretation=interpretation,
            reference_range={"low": 275, "high": 295},
            is_within_normal=is_normal,
            computation_timestamp=datetime.utcnow().isoformat(),
        )
    except Exception as e:
        logger.error(f"Error calculating osmolarity: {e}")
        return None


# ============================================================================
# LIPID CALCULATORS
# ============================================================================

def calculate_non_hdl(
    total_cholesterol: float,
    hdl: float
) -> Optional[DerivedFeature]:
    """Calculate non-HDL cholesterol."""
    try:
        non_hdl = total_cholesterol - hdl
        
        if non_hdl < 130:
            interpretation = "Optimal"
            is_normal = True
        elif non_hdl < 160:
            interpretation = "Near optimal"
            is_normal = True
        elif non_hdl < 190:
            interpretation = "Borderline high"
            is_normal = False
        else:
            interpretation = "High"
            is_normal = False
        
        from datetime import datetime
        
        return DerivedFeature(
            feature_name="Non_HDL",
            feature_type=DerivedFeatureType.LIPID,
            value=round(non_hdl, 1),
            unit="mg/dL",
            formula_used="Total_Chol - HDL",
            inputs_used={"total_cholesterol": total_cholesterol, "hdl": hdl},
            interpretation=interpretation,
            reference_range={"low": 0, "high": 130},
            is_within_normal=is_normal,
            computation_timestamp=datetime.utcnow().isoformat(),
        )
    except Exception as e:
        logger.error(f"Error calculating non-HDL: {e}")
        return None


def calculate_triglyceride_hdl_ratio(
    triglycerides: float,
    hdl: float
) -> Optional[DerivedFeature]:
    """Calculate TG/HDL ratio (insulin resistance marker)."""
    try:
        ratio = triglycerides / hdl
        
        if ratio < 2.0:
            interpretation = "Low risk for insulin resistance"
            is_normal = True
        elif ratio < 4.0:
            interpretation = "Moderate risk for insulin resistance"
            is_normal = False
        else:
            interpretation = "High risk for insulin resistance"
            is_normal = False
        
        from datetime import datetime
        
        return DerivedFeature(
            feature_name="TG_HDL_Ratio",
            feature_type=DerivedFeatureType.LIPID,
            value=round(ratio, 2),
            unit="ratio",
            formula_used="TG/HDL",
            inputs_used={"triglycerides": triglycerides, "hdl": hdl},
            interpretation=interpretation,
            reference_range={"low": 0, "high": 2.0},
            is_within_normal=is_normal,
            clinical_significance="Marker of insulin resistance and CVD risk",
            computation_timestamp=datetime.utcnow().isoformat(),
        )
    except Exception as e:
        logger.error(f"Error calculating TG/HDL ratio: {e}")
        return None


def calculate_tc_hdl_ratio(
    total_cholesterol: float,
    hdl: float
) -> Optional[DerivedFeature]:
    """Calculate TC/HDL ratio (cardiac risk)."""
    try:
        ratio = total_cholesterol / hdl
        
        if ratio < 3.5:
            interpretation = "Optimal"
            is_normal = True
        elif ratio < 5.0:
            interpretation = "Normal"
            is_normal = True
        else:
            interpretation = "Elevated cardiac risk"
            is_normal = False
        
        from datetime import datetime
        
        return DerivedFeature(
            feature_name="TC_HDL_Ratio",
            feature_type=DerivedFeatureType.LIPID,
            value=round(ratio, 2),
            unit="ratio",
            formula_used="Total_Chol/HDL",
            inputs_used={"total_cholesterol": total_cholesterol, "hdl": hdl},
            interpretation=interpretation,
            reference_range={"low": 0, "high": 5.0},
            is_within_normal=is_normal,
            clinical_significance="Framingham cardiac risk marker",
            computation_timestamp=datetime.utcnow().isoformat(),
        )
    except Exception as e:
        logger.error(f"Error calculating TC/HDL ratio: {e}")
        return None


def calculate_remnant_cholesterol(
    total_cholesterol: float,
    ldl: float,
    hdl: float
) -> Optional[DerivedFeature]:
    """Calculate remnant cholesterol (VLDL + IDL)."""
    try:
        remnant = total_cholesterol - ldl - hdl
        
        if remnant < 30:
            interpretation = "Optimal"
            is_normal = True
        else:
            interpretation = "Elevated - increased CVD risk"
            is_normal = False
        
        from datetime import datetime
        
        return DerivedFeature(
            feature_name="Remnant_Cholesterol",
            feature_type=DerivedFeatureType.LIPID,
            value=round(remnant, 1),
            unit="mg/dL",
            formula_used="Total_Chol - LDL - HDL",
            inputs_used={"total_cholesterol": total_cholesterol, "ldl": ldl, "hdl": hdl},
            interpretation=interpretation,
            reference_range={"low": 0, "high": 30},
            is_within_normal=is_normal,
            clinical_significance="Marker of residual CVD risk",
            computation_timestamp=datetime.utcnow().isoformat(),
        )
    except Exception as e:
        logger.error(f"Error calculating remnant cholesterol: {e}")
        return None


# ============================================================================
# BLOOD PRESSURE CALCULATORS
# ============================================================================

def calculate_map(
    systolic: float,
    diastolic: float
) -> Optional[DerivedFeature]:
    """Calculate Mean Arterial Pressure."""
    try:
        map_value = diastolic + (systolic - diastolic) / 3
        
        if 70 <= map_value <= 100:
            interpretation = "Normal"
            is_normal = True
        elif map_value < 70:
            interpretation = "Low - possible hypoperfusion risk"
            is_normal = False
        else:
            interpretation = "Elevated"
            is_normal = False
        
        from datetime import datetime
        
        return DerivedFeature(
            feature_name="MAP",
            feature_type=DerivedFeatureType.BLOOD_PRESSURE,
            value=round(map_value, 1),
            unit="mmHg",
            formula_used="DBP + (SBP - DBP)/3",
            inputs_used={"systolic": systolic, "diastolic": diastolic},
            interpretation=interpretation,
            reference_range={"low": 70, "high": 100},
            is_within_normal=is_normal,
            computation_timestamp=datetime.utcnow().isoformat(),
        )
    except Exception as e:
        logger.error(f"Error calculating MAP: {e}")
        return None


def calculate_pulse_pressure(
    systolic: float,
    diastolic: float
) -> Optional[DerivedFeature]:
    """Calculate Pulse Pressure."""
    try:
        pp = systolic - diastolic
        
        if 40 <= pp <= 60:
            interpretation = "Normal"
            is_normal = True
        elif pp < 40:
            interpretation = "Low - possible reduced stroke volume"
            is_normal = False
        else:
            interpretation = "Wide - possible arterial stiffness"
            is_normal = False
        
        from datetime import datetime
        
        return DerivedFeature(
            feature_name="Pulse_Pressure",
            feature_type=DerivedFeatureType.BLOOD_PRESSURE,
            value=round(pp, 1),
            unit="mmHg",
            formula_used="SBP - DBP",
            inputs_used={"systolic": systolic, "diastolic": diastolic},
            interpretation=interpretation,
            reference_range={"low": 40, "high": 60},
            is_within_normal=is_normal,
            clinical_significance="Marker of arterial compliance",
            computation_timestamp=datetime.utcnow().isoformat(),
        )
    except Exception as e:
        logger.error(f"Error calculating pulse pressure: {e}")
        return None


# ============================================================================
# ORCHESTRATOR
# ============================================================================

def compute_derived_features(values: Dict[str, Any], patient_info: Optional[Dict[str, Any]] = None) -> DerivedFeaturePack:
    """
    Compute all applicable derived features from available values.
    
    Args:
        values: Dict of variable_name -> value
        patient_info: Optional dict with age, sex, etc.
    
    Returns:
        DerivedFeaturePack with all computed features
    """
    pack = DerivedFeaturePack(run_id=values.get("run_id", "unknown"))
    
    patient_age = patient_info.get("age") if patient_info else None
    patient_sex = patient_info.get("sex") if patient_info else None
    
    # Renal features
    if "creatinine" in values and patient_age and patient_sex:
        feature = calculate_egfr_ckd_epi(values["creatinine"], patient_age, patient_sex)
        if feature:
            pack.renal_features.append(feature)
            pack.features_computed += 1
    
    if "bun" in values and "creatinine" in values:
        feature = calculate_bun_creatinine_ratio(values["bun"], values["creatinine"])
        if feature:
            pack.renal_features.append(feature)
            pack.features_computed += 1
    
    # Electrolyte features
    if all(k in values for k in ["sodium_na", "chloride_cl", "co2_bicarb"]):
        feature = calculate_anion_gap(values["sodium_na"], values["chloride_cl"], values["co2_bicarb"])
        if feature:
            pack.electrolyte_features.append(feature)
            pack.features_computed += 1
            
            if "albumin" in values:
                corrected = calculate_albumin_corrected_anion_gap(feature.value, values["albumin"])
                if corrected:
                    pack.electrolyte_features.append(corrected)
                    pack.features_computed += 1
    
    if all(k in values for k in ["sodium_na", "glucose", "bun"]):
        feature = calculate_estimated_osmolarity(values["sodium_na"], values["glucose"], values["bun"])
        if feature:
            pack.electrolyte_features.append(feature)
            pack.features_computed += 1
    
    # Lipid features
    if "chol_total" in values and "hdl" in values:
        feature = calculate_non_hdl(values["chol_total"], values["hdl"])
        if feature:
            pack.lipid_features.append(feature)
            pack.features_computed += 1
        
        feature = calculate_tc_hdl_ratio(values["chol_total"], values["hdl"])
        if feature:
            pack.lipid_features.append(feature)
            pack.features_computed += 1
    
    if "triglycerides" in values and "hdl" in values:
        feature = calculate_triglyceride_hdl_ratio(values["triglycerides"], values["hdl"])
        if feature:
            pack.lipid_features.append(feature)
            pack.features_computed += 1
    
    if all(k in values for k in ["chol_total", "ldl", "hdl"]):
        feature = calculate_remnant_cholesterol(values["chol_total"], values["ldl"], values["hdl"])
        if feature:
            pack.lipid_features.append(feature)
            pack.features_computed += 1
    
    # Blood pressure features (if vitals available)
    if "blood_pressure_systolic" in values and "blood_pressure_diastolic" in values:
        feature = calculate_map(values["blood_pressure_systolic"], values["blood_pressure_diastolic"])
        if feature:
            pack.blood_pressure_features.append(feature)
            pack.features_computed += 1
        
        feature = calculate_pulse_pressure(values["blood_pressure_systolic"], values["blood_pressure_diastolic"])
        if feature:
            pack.blood_pressure_features.append(feature)
            pack.features_computed += 1
    
    return pack
