"""
Priors Service

Provides access to vendored population priors and reference intervals
for use in confidence scoring, quality gating, and inference outputs.

All data is loaded locally from data/priors_pack/ - no runtime HTTP calls.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from functools import lru_cache

import pandas as pd

# Path to vendored priors pack
PRIORS_DIR = Path(__file__).parent.parent.parent / "data" / "priors_pack"


class PriorsService:
    """
    Service for querying population priors and reference intervals.
    
    Singleton pattern with lazy loading and caching.
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._vitals_percentiles: Optional[pd.DataFrame] = None
        self._lab_reference_intervals: Optional[pd.DataFrame] = None
        self._calibration_constants: Optional[Dict] = None
        self._initialized = True
    
    def _load_vitals_percentiles(self) -> pd.DataFrame:
        """Load vitals percentiles table (lazy loading with caching)."""
        if self._vitals_percentiles is None:
            path = PRIORS_DIR / "nhanes_vitals_percentiles.csv"
            if not path.exists():
                raise FileNotFoundError(
                    f"Vitals percentiles file not found: {path}. "
                    f"Run scripts/build_priors_pack.py to generate."
                )
            self._vitals_percentiles = pd.read_csv(path)
        return self._vitals_percentiles
    
    def _load_lab_reference_intervals(self) -> pd.DataFrame:
        """Load lab reference intervals table (lazy loading with caching)."""
        if self._lab_reference_intervals is None:
            path = PRIORS_DIR / "nhanes_lab_reference_intervals.csv"
            if not path.exists():
                raise FileNotFoundError(
                    f"Lab reference intervals file not found: {path}. "
                    f"Run scripts/build_priors_pack.py to generate."
                )
            self._lab_reference_intervals = pd.read_csv(path)
        return self._lab_reference_intervals
    
    def _load_calibration_constants(self) -> Dict:
        """Load calibration constants (lazy loading with caching)."""
        if self._calibration_constants is None:
            path = PRIORS_DIR / "calibration_constants.json"
            if not path.exists():
                raise FileNotFoundError(
                    f"Calibration constants file not found: {path}. "
                    f"Run scripts/build_priors_pack.py to generate."
                )
            with open(path, 'r') as f:
                self._calibration_constants = json.load(f)
        return self._calibration_constants
    
    def get_percentiles(
        self,
        metric: str,
        age: int,
        sex: str,
        bmi: Optional[float] = None
    ) -> Optional[Dict[str, float]]:
        """
        Get population percentiles for a given metric.
        
        Args:
            metric: Metric name (e.g., 'resting_hr_bpm', 'systolic_bp_mmhg')
            age: Age in years (18-120)
            sex: 'M' or 'F'
            bmi: BMI value (optional, for BMI-stratified priors if available)
        
        Returns:
            Dict with keys: p5, p10, p25, p50, p75, p90, p95
            or None if no matching prior found
        """
        df = self._load_vitals_percentiles()
        
        # Normalize sex
        sex = sex.upper()
        if sex not in ('M', 'F'):
            return None
        
        # Find matching stratum
        matching = df[
            (df['metric'] == metric) &
            (df['sex'] == sex) &
            (df['age_min'] <= age) &
            (df['age_max'] >= age)
        ]
        
        if matching.empty:
            return None
        
        # Return first match (should be unique by design)
        row = matching.iloc[0]
        return {
            'p5': float(row['p5']),
            'p10': float(row['p10']),
            'p25': float(row['p25']),
            'p50': float(row['p50']),
            'p75': float(row['p75']),
            'p90': float(row['p90']),
            'p95': float(row['p95']),
        }
    
    def get_percentile_rank(
        self,
        metric: str,
        value: float,
        age: int,
        sex: str
    ) -> Optional[float]:
        """
        Get the approximate percentile rank of a value within population.
        
        Args:
            metric: Metric name
            value: Observed value
            age: Age in years
            sex: 'M' or 'F'
        
        Returns:
            Percentile rank (0-100) or None if no prior available
        """
        percentiles = self.get_percentiles(metric, age, sex)
        if not percentiles:
            return None
        
        # Linear interpolation between percentile points
        pcts = [5, 10, 25, 50, 75, 90, 95]
        vals = [percentiles[f'p{p}'] for p in pcts]
        
        if value <= vals[0]:
            return 5.0
        if value >= vals[-1]:
            return 95.0
        
        # Find surrounding percentile points
        for i in range(len(vals) - 1):
            if vals[i] <= value <= vals[i + 1]:
                # Linear interpolation
                lower_pct, upper_pct = pcts[i], pcts[i + 1]
                lower_val, upper_val = vals[i], vals[i + 1]
                
                if upper_val == lower_val:
                    return float(lower_pct)
                
                fraction = (value - lower_val) / (upper_val - lower_val)
                return lower_pct + fraction * (upper_pct - lower_pct)
        
        return None
    
    def get_reference_interval(
        self,
        analyte: str,
        age: int,
        sex: str,
        units: Optional[str] = None
    ) -> Optional[Dict[str, float]]:
        """
        Get reference interval for a lab analyte.
        
        Args:
            analyte: Analyte name (e.g., 'glucose', 'creatinine', 'hemoglobin')
            age: Age in years
            sex: 'M', 'F', or 'ALL'
            units: Expected units (optional, for validation)
        
        Returns:
            Dict with keys: ref_low, ref_high, critical_low, critical_high, units
            or None if no matching reference interval found
        """
        df = self._load_lab_reference_intervals()
        
        # Normalize analyte name (lowercase, underscores)
        analyte = analyte.lower().replace(' ', '_').replace('-', '_')
        
        # Normalize sex
        sex = sex.upper()
        
        # Try exact sex match first, then fall back to 'ALL'
        for sex_query in [sex, 'ALL']:
            matching = df[
                (df['analyte'] == analyte) &
                (df['sex'] == sex_query) &
                (df['age_min'] <= age) &
                (df['age_max'] >= age)
            ]
            
            if not matching.empty:
                row = matching.iloc[0]
                result = {
                    'ref_low': float(row['ref_low']),
                    'ref_high': float(row['ref_high']),
                    'critical_low': float(row['critical_low']),
                    'critical_high': float(row['critical_high']),
                    'units': str(row['units']),
                }
                
                # Validate units if provided
                if units and str(row['units']).lower() != units.lower():
                    # Return interval but flag unit mismatch
                    result['units_match'] = False
                else:
                    result['units_match'] = True
                
                return result
        
        return None
    
    def validate_units_and_ranges(
        self,
        analyte: str,
        value: float,
        units: str,
        age: int,
        sex: str
    ) -> Dict[str, any]:
        """
        Validate a lab value against reference intervals.
        
        Args:
            analyte: Analyte name
            value: Measured value
            units: Units of measurement
            age: Patient age
            sex: Patient sex
        
        Returns:
            Dict with keys:
                - valid: bool (within reference or critical range)
                - status: str ('normal', 'abnormal', 'critical', 'unknown')
                - ref_interval: dict or None
                - message: str (human-readable)
        """
        ref = self.get_reference_interval(analyte, age, sex, units)
        
        if not ref:
            return {
                'valid': True,  # Unknown, so assume valid
                'status': 'unknown',
                'ref_interval': None,
                'message': f"No reference interval available for {analyte}"
            }
        
        # Check units match
        if not ref.get('units_match', True):
            return {
                'valid': False,
                'status': 'unit_mismatch',
                'ref_interval': ref,
                'message': f"Unit mismatch: expected {ref['units']}, got {units}"
            }
        
        # Check critical range
        if value < ref['critical_low'] or value > ref['critical_high']:
            return {
                'valid': False,
                'status': 'critical',
                'ref_interval': ref,
                'message': f"Value {value} {units} is outside critical range [{ref['critical_low']}, {ref['critical_high']}]"
            }
        
        # Check reference range
        if ref['ref_low'] <= value <= ref['ref_high']:
            return {
                'valid': True,
                'status': 'normal',
                'ref_interval': ref,
                'message': f"Value {value} {units} is within normal range [{ref['ref_low']}, {ref['ref_high']}]"
            }
        else:
            return {
                'valid': True,  # Abnormal but not critical
                'status': 'abnormal',
                'ref_interval': ref,
                'message': f"Value {value} {units} is outside normal range [{ref['ref_low']}, {ref['ref_high']}] but not critical"
            }
    
    def get_population_prior(
        self,
        metric: str,
        strata: Dict[str, any]
    ) -> Optional[Dict]:
        """
        Generic method to get population prior (percentiles or reference interval).
        
        Args:
            metric: Metric or analyte name
            strata: Dict with keys like 'age', 'sex', 'bmi'
        
        Returns:
            Population prior data or None
        """
        age = strata.get('age', 40)  # Default to 40 if not provided
        sex = strata.get('sex', 'ALL')
        bmi = strata.get('bmi')
        
        # Try vitals percentiles first
        percentiles = self.get_percentiles(metric, age, sex, bmi)
        if percentiles:
            return {'type': 'percentiles', 'data': percentiles}
        
        # Try lab reference intervals
        ref_interval = self.get_reference_interval(metric, age, sex)
        if ref_interval:
            return {'type': 'reference_interval', 'data': ref_interval}
        
        return None
    
    def get_calibration_constant(self, key_path: str, default=None):
        """
        Get a calibration constant by JSON path.
        
        Args:
            key_path: Dot-separated path (e.g., 'gating_thresholds.minimum_data_windows_days.a1c_estimate')
            default: Default value if key not found
        
        Returns:
            Value from calibration constants or default
        """
        constants = self._load_calibration_constants()
        
        keys = key_path.split('.')
        value = constants
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value
    
    def get_gating_thresholds(self) -> Dict:
        """Get all gating thresholds."""
        constants = self._load_calibration_constants()
        return constants.get('gating_thresholds', {})
    
    def get_confidence_parameters(self) -> Dict:
        """Get all confidence parameters."""
        constants = self._load_calibration_constants()
        return constants.get('confidence_parameters', {})


# Singleton instance
priors_service = PriorsService()
