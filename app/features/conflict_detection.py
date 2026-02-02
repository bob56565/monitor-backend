"""
Input Conflict Detection Module.

Implements Requirement A2.4: Detect physiologic contradictions before inference.
- Identifies impossible or conflicting values
- Never auto-averages or silently smooths conflicts
- Attaches conflict_note explaining why ranges will widen
- Conflicts propagate to confidence logic downstream
"""

from typing import Dict, List, Optional, Any, Tuple
from pydantic import BaseModel, Field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ConflictSeverity(str, Enum):
    """Severity of detected conflict."""
    INFO = "info"  # Notable but not problematic
    WARNING = "warning"  # Should be investigated
    CRITICAL = "critical"  # Likely data error or physiologic crisis


class ConflictType(str, Enum):
    """Types of conflicts."""
    PHYSIOLOGIC_IMPOSSIBLE = "physiologic_impossible"
    CROSS_SPECIMEN_DISAGREEMENT = "cross_specimen_disagreement"
    TEMPORAL_INCONSISTENCY = "temporal_inconsistency"
    RANGE_VIOLATION = "range_violation"
    ELECTROLYTE_IMBALANCE = "electrolyte_imbalance"
    MASS_BALANCE_VIOLATION = "mass_balance_violation"


class DetectedConflict(BaseModel):
    """A single detected conflict."""
    conflict_id: str
    conflict_type: ConflictType
    severity: ConflictSeverity
    
    # What's conflicting
    variables_involved: List[str]
    values_involved: Dict[str, Any]
    
    # Why it's a conflict
    conflict_description: str
    expected_range: Optional[Dict[str, float]] = None
    actual_value: Optional[float] = None
    
    # Impact on inference
    confidence_impact: str  # "widen_range", "reduce_confidence", "suppress_output"
    recommended_action: str
    
    # Metadata
    detected_at: Optional[str] = None
    resolution_status: str = "unresolved"  # "unresolved", "explained", "corrected"
    
    class Config:
        json_schema_extra = {
            "example": {
                "conflict_id": "conflict_001",
                "conflict_type": "cross_specimen_disagreement",
                "severity": "warning",
                "variables_involved": ["glucose_blood", "glucose_isf"],
                "conflict_description": "Blood glucose 250 mg/dL but ISF glucose 90 mg/dL - physiologically implausible",
                "confidence_impact": "widen_range"
            }
        }


class ConflictDetectionReport(BaseModel):
    """Complete conflict detection report for a run."""
    run_id: str
    schema_version: str = "conflict_detection_v1.0"
    
    conflicts_detected: List[DetectedConflict] = Field(default_factory=list)
    
    # Summary stats
    total_conflicts: int = 0
    critical_conflicts: int = 0
    warning_conflicts: int = 0
    info_conflicts: int = 0
    
    # Overall assessment
    data_quality_flag: str = "clean"  # "clean", "minor_issues", "major_issues", "unusable"
    overall_confidence_penalty: float = 0.0  # 0.0 to 1.0 multiplier
    
    processing_notes: List[str] = Field(default_factory=list)


# ============================================================================
# PHYSIOLOGIC RANGE CHECKS
# ============================================================================

PHYSIOLOGIC_ABSOLUTE_LIMITS = {
    "glucose": {"min": 10, "max": 1000, "unit": "mg/dL", "reason": "Below 10 incompatible with life, above 1000 extremely rare"},
    "creatinine": {"min": 0.1, "max": 30, "unit": "mg/dL", "reason": "Below 0.1 or above 30 likely measurement error"},
    "sodium_na": {"min": 110, "max": 170, "unit": "mmol/L", "reason": "Outside this range incompatible with consciousness"},
    "potassium_k": {"min": 1.5, "max": 9.0, "unit": "mmol/L", "reason": "Outside this range life-threatening"},
    "calcium": {"min": 5.0, "max": 15.0, "unit": "mg/dL", "reason": "Outside this range life-threatening"},
    "ph": {"min": 6.8, "max": 7.8, "unit": "pH", "reason": "Outside this range incompatible with life"},
    "heart_rate": {"min": 20, "max": 250, "unit": "bpm", "reason": "Outside this range likely measurement artifact"},
    "blood_pressure_systolic": {"min": 40, "max": 300, "unit": "mmHg", "reason": "Outside this range likely artifact or crisis"},
    "blood_pressure_diastolic": {"min": 20, "max": 200, "unit": "mmHg", "reason": "Outside this range likely artifact or crisis"},
}


def check_physiologic_ranges(values: Dict[str, float]) -> List[DetectedConflict]:
    """Check if values are within physiologically possible ranges."""
    conflicts = []
    
    for var_name, var_value in values.items():
        if var_name in PHYSIOLOGIC_ABSOLUTE_LIMITS:
            limits = PHYSIOLOGIC_ABSOLUTE_LIMITS[var_name]
            
            if var_value < limits["min"] or var_value > limits["max"]:
                from datetime import datetime
                
                conflict = DetectedConflict(
                    conflict_id=f"range_{var_name}",
                    conflict_type=ConflictType.PHYSIOLOGIC_IMPOSSIBLE,
                    severity=ConflictSeverity.CRITICAL,
                    variables_involved=[var_name],
                    values_involved={var_name: var_value},
                    conflict_description=f"{var_name} = {var_value} {limits['unit']} is outside physiologically possible range [{limits['min']}, {limits['max']}]. {limits['reason']}",
                    expected_range={"min": limits["min"], "max": limits["max"]},
                    actual_value=var_value,
                    confidence_impact="suppress_output",
                    recommended_action="Verify measurement, likely data entry error or sensor malfunction",
                    detected_at=datetime.utcnow().isoformat(),
                )
                conflicts.append(conflict)
    
    return conflicts


# ============================================================================
# CROSS-SPECIMEN CONFLICT DETECTION
# ============================================================================

def check_cross_specimen_consistency(
    specimens_data: List[Dict[str, Any]]
) -> List[DetectedConflict]:
    """
    Check for conflicts across specimens.
    For example: blood glucose 250 but ISF glucose 90 (physiologically implausible).
    """
    conflicts = []
    
    # Group by variable name
    variables_by_name: Dict[str, List[Tuple[str, float, Any]]] = {}
    
    for specimen in specimens_data:
        specimen_type = specimen.get("specimen_type", "unknown")
        values = specimen.get("values", {})
        
        for var_name, var_value in values.items():
            if var_value is not None:
                if var_name not in variables_by_name:
                    variables_by_name[var_name] = []
                variables_by_name[var_name].append((specimen_type, var_value, specimen))
    
    # Check for conflicts within same variable across specimens
    for var_name, measurements in variables_by_name.items():
        if len(measurements) >= 2:
            # Check glucose cross-specimen (blood vs ISF)
            if var_name == "glucose":
                blood_values = [v for st, v, _ in measurements if "BLOOD" in st.upper()]
                isf_values = [v for st, v, _ in measurements if st.upper() == "ISF"]
                
                if blood_values and isf_values:
                    blood_val = blood_values[0]
                    isf_val = isf_values[0]
                    
                    # ISF typically lags blood by 5-15 minutes
                    # Large disagreement (>50 mg/dL difference or >30% difference) is suspicious
                    diff = abs(blood_val - isf_val)
                    pct_diff = diff / max(blood_val, isf_val) * 100
                    
                    if diff > 50 and pct_diff > 30:
                        from datetime import datetime
                        
                        conflict = DetectedConflict(
                            conflict_id=f"cross_specimen_glucose",
                            conflict_type=ConflictType.CROSS_SPECIMEN_DISAGREEMENT,
                            severity=ConflictSeverity.WARNING,
                            variables_involved=["glucose_blood", "glucose_isf"],
                            values_involved={"glucose_blood": blood_val, "glucose_isf": isf_val},
                            conflict_description=f"Blood glucose ({blood_val} mg/dL) and ISF glucose ({isf_val} mg/dL) differ by {diff:.1f} mg/dL ({pct_diff:.1f}%). This exceeds expected physiologic lag.",
                            confidence_impact="widen_range",
                            recommended_action="Consider timing of measurements, recent meal, or sensor calibration issue",
                            detected_at=datetime.utcnow().isoformat(),
                        )
                        conflicts.append(conflict)
            
            # Check for extreme outliers within same variable
            values_only = [v for _, v, _ in measurements]
            if len(values_only) >= 2:
                import statistics
                mean_val = statistics.mean(values_only)
                if len(values_only) > 2:
                    stdev_val = statistics.stdev(values_only)
                    
                    # Flag values > 3 SD from mean
                    for specimen_type, val, _ in measurements:
                        if abs(val - mean_val) > 3 * stdev_val:
                            from datetime import datetime
                            
                            conflict = DetectedConflict(
                                conflict_id=f"outlier_{var_name}_{specimen_type}",
                                conflict_type=ConflictType.TEMPORAL_INCONSISTENCY,
                                severity=ConflictSeverity.WARNING,
                                variables_involved=[f"{var_name}_{specimen_type}"],
                                values_involved={f"{var_name}_{specimen_type}": val},
                                conflict_description=f"{var_name} from {specimen_type} ({val}) is >3 SD from mean of all measurements ({mean_val:.1f} ± {stdev_val:.1f})",
                                confidence_impact="widen_range",
                                recommended_action="Verify measurement, may indicate acute change or error",
                                detected_at=datetime.utcnow().isoformat(),
                            )
                            conflicts.append(conflict)
    
    return conflicts


# ============================================================================
# ELECTROLYTE BALANCE CHECKS
# ============================================================================

def check_electrolyte_balance(values: Dict[str, float]) -> List[DetectedConflict]:
    """Check for electrolyte imbalances that suggest measurement errors."""
    conflicts = []
    
    # Check anion gap plausibility
    if all(k in values for k in ["sodium_na", "chloride_cl", "co2_bicarb"]):
        ag = values["sodium_na"] - (values["chloride_cl"] + values["co2_bicarb"])
        
        if ag < 0:
            from datetime import datetime
            
            conflict = DetectedConflict(
                conflict_id="negative_anion_gap",
                conflict_type=ConflictType.ELECTROLYTE_IMBALANCE,
                severity=ConflictSeverity.CRITICAL,
                variables_involved=["sodium_na", "chloride_cl", "co2_bicarb"],
                values_involved={
                    "sodium_na": values["sodium_na"],
                    "chloride_cl": values["chloride_cl"],
                    "co2_bicarb": values["co2_bicarb"],
                    "anion_gap": ag
                },
                conflict_description=f"Calculated anion gap is negative ({ag:.1f}). This is physiologically impossible and indicates measurement error.",
                confidence_impact="suppress_output",
                recommended_action="Verify all electrolyte measurements, likely lab error",
                detected_at=datetime.utcnow().isoformat(),
            )
            conflicts.append(conflict)
        
        elif ag > 30:
            from datetime import datetime
            
            conflict = DetectedConflict(
                conflict_id="extreme_anion_gap",
                conflict_type=ConflictType.ELECTROLYTE_IMBALANCE,
                severity=ConflictSeverity.WARNING,
                variables_involved=["sodium_na", "chloride_cl", "co2_bicarb"],
                values_involved={
                    "sodium_na": values["sodium_na"],
                    "chloride_cl": values["chloride_cl"],
                    "co2_bicarb": values["co2_bicarb"],
                    "anion_gap": ag
                },
                conflict_description=f"Anion gap ({ag:.1f}) is extremely elevated. While possible in severe acidosis, verify measurements.",
                confidence_impact="reduce_confidence",
                recommended_action="Verify measurements, may indicate severe metabolic acidosis or error",
                detected_at=datetime.utcnow().isoformat(),
            )
            conflicts.append(conflict)
    
    # Check sodium-potassium relationship
    if "sodium_na" in values and "potassium_k" in values:
        # Typically Na is ~30-35x higher than K
        ratio = values["sodium_na"] / values["potassium_k"]
        
        if ratio < 20 or ratio > 50:
            from datetime import datetime
            
            conflict = DetectedConflict(
                conflict_id="na_k_ratio_abnormal",
                conflict_type=ConflictType.ELECTROLYTE_IMBALANCE,
                severity=ConflictSeverity.INFO,
                variables_involved=["sodium_na", "potassium_k"],
                values_involved={
                    "sodium_na": values["sodium_na"],
                    "potassium_k": values["potassium_k"],
                    "ratio": ratio
                },
                conflict_description=f"Na/K ratio ({ratio:.1f}) is outside typical range [20-50]. Verify measurements.",
                confidence_impact="reduce_confidence",
                recommended_action="Verify electrolyte measurements",
                detected_at=datetime.utcnow().isoformat(),
            )
            conflicts.append(conflict)
    
    return conflicts


# ============================================================================
# BLOOD PRESSURE CONSISTENCY
# ============================================================================

def check_blood_pressure_consistency(values: Dict[str, float]) -> List[DetectedConflict]:
    """Check blood pressure values for internal consistency."""
    conflicts = []
    
    if "blood_pressure_systolic" in values and "blood_pressure_diastolic" in values:
        sbp = values["blood_pressure_systolic"]
        dbp = values["blood_pressure_diastolic"]
        
        # Diastolic should always be less than systolic
        if dbp >= sbp:
            from datetime import datetime
            
            conflict = DetectedConflict(
                conflict_id="bp_inversion",
                conflict_type=ConflictType.PHYSIOLOGIC_IMPOSSIBLE,
                severity=ConflictSeverity.CRITICAL,
                variables_involved=["blood_pressure_systolic", "blood_pressure_diastolic"],
                values_involved={"systolic": sbp, "diastolic": dbp},
                conflict_description=f"Diastolic pressure ({dbp}) >= systolic pressure ({sbp}). This is physiologically impossible.",
                confidence_impact="suppress_output",
                recommended_action="Verify blood pressure measurement, likely cuff error or data entry error",
                detected_at=datetime.utcnow().isoformat(),
            )
            conflicts.append(conflict)
        
        # Pulse pressure should be reasonable (20-60 mmHg typical)
        pp = sbp - dbp
        if pp < 20:
            from datetime import datetime
            
            conflict = DetectedConflict(
                conflict_id="bp_narrow_pulse_pressure",
                conflict_type=ConflictType.RANGE_VIOLATION,
                severity=ConflictSeverity.WARNING,
                variables_involved=["blood_pressure_systolic", "blood_pressure_diastolic"],
                values_involved={"systolic": sbp, "diastolic": dbp, "pulse_pressure": pp},
                conflict_description=f"Pulse pressure ({pp} mmHg) is very narrow. May indicate reduced cardiac output or measurement error.",
                confidence_impact="reduce_confidence",
                recommended_action="Verify measurement, may be physiologic in some conditions",
                detected_at=datetime.utcnow().isoformat(),
            )
            conflicts.append(conflict)
        elif pp > 100:
            from datetime import datetime
            
            conflict = DetectedConflict(
                conflict_id="bp_wide_pulse_pressure",
                conflict_type=ConflictType.RANGE_VIOLATION,
                severity=ConflictSeverity.WARNING,
                variables_involved=["blood_pressure_systolic", "blood_pressure_diastolic"],
                values_involved={"systolic": sbp, "diastolic": dbp, "pulse_pressure": pp},
                conflict_description=f"Pulse pressure ({pp} mmHg) is very wide. May indicate arterial stiffness or measurement error.",
                confidence_impact="reduce_confidence",
                recommended_action="Verify measurement, may indicate aortic regurgitation or atherosclerosis",
                detected_at=datetime.utcnow().isoformat(),
            )
            conflicts.append(conflict)
    
    return conflicts


# ============================================================================
# ORCHESTRATOR
# ============================================================================

def detect_conflicts(
    values: Dict[str, float],
    specimens_data: Optional[List[Dict[str, Any]]] = None
) -> ConflictDetectionReport:
    """
    Comprehensive conflict detection across all data.
    
    Args:
        values: Flat dict of all values
        specimens_data: Optional list of specimen dicts for cross-specimen checks
    
    Returns:
        ConflictDetectionReport with all detected conflicts
    """
    from datetime import datetime
    
    all_conflicts: List[DetectedConflict] = []
    
    # Run all checks
    all_conflicts.extend(check_physiologic_ranges(values))
    all_conflicts.extend(check_electrolyte_balance(values))
    all_conflicts.extend(check_blood_pressure_consistency(values))
    
    if specimens_data:
        all_conflicts.extend(check_cross_specimen_consistency(specimens_data))
    
    # Calculate summary stats
    critical_count = sum(1 for c in all_conflicts if c.severity == ConflictSeverity.CRITICAL)
    warning_count = sum(1 for c in all_conflicts if c.severity == ConflictSeverity.WARNING)
    info_count = sum(1 for c in all_conflicts if c.severity == ConflictSeverity.INFO)
    
    # Determine overall data quality
    if critical_count > 0:
        data_quality = "major_issues"
        confidence_penalty = 0.5  # Reduce confidence by 50%
    elif warning_count > 3:
        data_quality = "major_issues"
        confidence_penalty = 0.7  # Reduce confidence by 30%
    elif warning_count > 0:
        data_quality = "minor_issues"
        confidence_penalty = 0.9  # Reduce confidence by 10%
    else:
        data_quality = "clean"
        confidence_penalty = 1.0  # No penalty
    
    processing_notes = [
        f"Detected {len(all_conflicts)} total conflicts",
        f"Critical: {critical_count}, Warning: {warning_count}, Info: {info_count}",
        f"Data quality assessment: {data_quality}",
        f"Confidence penalty factor: {confidence_penalty:.2f}"
    ]
    
    return ConflictDetectionReport(
        run_id=values.get("run_id", "unknown"),
        schema_version="conflict_detection_v1.0",
        conflicts_detected=all_conflicts,
        total_conflicts=len(all_conflicts),
        critical_conflicts=critical_count,
        warning_conflicts=warning_count,
        info_conflicts=info_count,
        data_quality_flag=data_quality,
        overall_confidence_penalty=confidence_penalty,
        processing_notes=processing_notes,
    )
