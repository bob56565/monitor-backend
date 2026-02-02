"""
Quality Gating Engine

Enforces quality requirements for inference outputs:
- Minimum data windows (e.g., 14-30 days for A1c estimates)
- Minimum signal quality thresholds
- Anchor requirements for tight vs wide range outputs

Prevents overconfident outputs when data is insufficient.
"""

from typing import Dict, List, Optional
from enum import Enum
from datetime import datetime, timedelta

from app.services.priors import priors_service


class RangeWidth(str, Enum):
    """Recommended output range width based on data quality."""
    TIGHT = "tight"  # ±5-10% range for high-quality data
    WIDE = "wide"  # ±15-25% range for moderate data
    INSUFFICIENT = "insufficient"  # Not enough data for meaningful output


class GatingEngine:
    """
    Engine for quality gating decisions.
    
    Determines whether an inference output should be:
    - Allowed (tight range)
    - Allowed (wide range)
    - Blocked (insufficient data)
    
    Singleton pattern for consistency.
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
        
        # Load gating thresholds from priors service
        self.thresholds = priors_service.get_gating_thresholds()
        self._initialized = True
    
    def check_gate(
        self,
        output_name: str,
        days_of_data: int,
        signal_quality: Optional[float] = None,
        has_anchor: bool = False,
        anchor_recency_days: Optional[int] = None,
        additional_checks: Optional[Dict] = None
    ) -> Dict:
        """
        Check if output passes quality gates.
        
        Args:
            output_name: Name of output (e.g., 'a1c_estimate', 'bp_estimate')
            days_of_data: Number of days of data available
            signal_quality: Average signal quality (0-1)
            has_anchor: Whether recent anchor data (lab) is available
            anchor_recency_days: Days since anchor data
            additional_checks: Output-specific additional requirements
        
        Returns:
            Dict with:
                - allowed: bool (whether output is allowed at all)
                - recommended_range_width: RangeWidth enum
                - reasons: List of reasons for the decision
                - remediation: List of steps to improve quality
                - gating_details: Structured details for provenance
        """
        reasons = []
        remediation = []
        
        # Get minimum data window for this output
        min_days = self.thresholds['minimum_data_windows_days'].get(
            output_name,
            self.thresholds['minimum_data_windows_days']['default']
        )
        
        # Check data window
        has_sufficient_window = days_of_data >= min_days
        if not has_sufficient_window:
            reasons.append(f"Insufficient data: {days_of_data} days (need {min_days}+)")
            remediation.append(f"Collect at least {min_days} days of continuous data")
        
        # Check signal quality
        has_good_quality = True
        if signal_quality is not None:
            tight_threshold = self.thresholds['minimum_sensor_quality']['tight_range']
            wide_threshold = self.thresholds['minimum_sensor_quality']['wide_range']
            any_threshold = self.thresholds['minimum_sensor_quality']['any_output']
            
            if signal_quality < any_threshold:
                has_good_quality = False
                reasons.append(f"Signal quality too low: {signal_quality:.2f} (need {any_threshold}+)")
                remediation.append("Improve sensor contact and calibration")
        else:
            # Unknown quality, assume moderate
            signal_quality = 0.7
        
        # Check anchor requirements
        anchor_satisfied_tight = False
        anchor_satisfied_wide = False
        
        if has_anchor:
            # Check anchor recency
            if anchor_recency_days is not None and anchor_recency_days <= 90:
                anchor_satisfied_tight = True
                anchor_satisfied_wide = True
                reasons.append(f"Recent anchor data available ({anchor_recency_days} days old)")
            elif anchor_recency_days is not None and anchor_recency_days <= 180:
                anchor_satisfied_wide = True
                reasons.append(f"Moderately recent anchor data ({anchor_recency_days} days old)")
            else:
                reasons.append("Anchor data is stale (>180 days old)")
                remediation.append("Upload recent lab results")
        else:
            # Check if anchor is required
            tight_anchors = self.thresholds['anchor_requirements'].get(
                f"{output_name}_tight",
                self.thresholds['anchor_requirements'].get('default_tight', [])
            )
            if tight_anchors:
                reasons.append(f"No anchor data available (need: {', '.join(tight_anchors)})")
                remediation.append(f"Upload {tight_anchors[0]} for tight range")
        
        # Perform additional output-specific checks
        if additional_checks:
            for check_name, check_result in additional_checks.items():
                if not check_result['passed']:
                    reasons.append(f"{check_name}: {check_result['reason']}")
                    if 'remediation' in check_result:
                        remediation.append(check_result['remediation'])
        
        # Determine allowed status and range width
        allowed = has_sufficient_window and has_good_quality
        
        if not allowed:
            range_width = RangeWidth.INSUFFICIENT
        elif (signal_quality >= self.thresholds['minimum_sensor_quality']['tight_range'] and
              has_sufficient_window and
              (anchor_satisfied_tight or not tight_anchors)):
            range_width = RangeWidth.TIGHT
            reasons.append("High-quality data enables tight range estimate")
        elif signal_quality >= self.thresholds['minimum_sensor_quality']['wide_range']:
            range_width = RangeWidth.WIDE
            reasons.append("Moderate-quality data enables wide range estimate")
        else:
            range_width = RangeWidth.INSUFFICIENT
            allowed = False
        
        return {
            'allowed': allowed,
            'recommended_range_width': range_width,
            'reasons': reasons,
            'remediation': remediation if not allowed else [],
            'gating_details': {
                'output_name': output_name,
                'days_of_data': days_of_data,
                'min_days_required': min_days,
                'signal_quality': signal_quality,
                'has_anchor': has_anchor,
                'anchor_recency_days': anchor_recency_days,
                'anchor_satisfied_tight': anchor_satisfied_tight,
                'anchor_satisfied_wide': anchor_satisfied_wide,
                'additional_checks': additional_checks or {}
            }
        }
    
    def check_a1c_estimate_gate(
        self,
        days_of_glucose_data: int,
        signal_quality: float,
        has_recent_a1c_lab: bool = False,
        a1c_lab_days_old: Optional[int] = None,
        glucose_cv: Optional[float] = None
    ) -> Dict:
        """
        Specialized gate check for A1c estimate.
        
        Args:
            days_of_glucose_data: Days of continuous glucose data
            signal_quality: Average sensor quality
            has_recent_a1c_lab: Whether user has uploaded recent A1c lab
            a1c_lab_days_old: Days since A1c lab
            glucose_cv: Glucose coefficient of variation (optional stability check)
        
        Returns:
            Gating result dict
        """
        additional_checks = {}
        
        # Check glucose variability
        if glucose_cv is not None:
            if glucose_cv > 0.50:  # >50% CV indicates very unstable
                additional_checks['glucose_stability'] = {
                    'passed': False,
                    'reason': f"Glucose CV {glucose_cv:.2f} is very high (unstable)",
                    'remediation': "Improve glucose stability with diet/medication management"
                }
            else:
                additional_checks['glucose_stability'] = {
                    'passed': True,
                    'reason': f"Glucose CV {glucose_cv:.2f} is acceptable"
                }
        
        return self.check_gate(
            output_name='a1c_estimate',
            days_of_data=days_of_glucose_data,
            signal_quality=signal_quality,
            has_anchor=has_recent_a1c_lab,
            anchor_recency_days=a1c_lab_days_old,
            additional_checks=additional_checks
        )
    
    def check_bp_estimate_gate(
        self,
        days_of_bp_data: int,
        signal_quality: float,
        has_bp_readings: bool = False,
        bp_readings_count: int = 0,
        bp_variability: Optional[float] = None
    ) -> Dict:
        """
        Specialized gate check for BP estimate.
        
        Args:
            days_of_bp_data: Days of BP monitoring
            signal_quality: Average sensor quality
            has_bp_readings: Whether user has manual BP readings
            bp_readings_count: Number of BP readings
            bp_variability: BP standard deviation (optional)
        
        Returns:
            Gating result dict
        """
        additional_checks = {}
        
        # Require minimum number of readings
        if has_bp_readings and bp_readings_count < 3:
            additional_checks['reading_count'] = {
                'passed': False,
                'reason': f"Only {bp_readings_count} BP readings (need 3+ for reliability)",
                'remediation': "Take additional BP readings at different times of day"
            }
        elif has_bp_readings:
            additional_checks['reading_count'] = {
                'passed': True,
                'reason': f"{bp_readings_count} BP readings available"
            }
        
        # Check variability
        if bp_variability is not None and bp_variability > 20:
            additional_checks['bp_stability'] = {
                'passed': True,  # Don't block, but note
                'reason': f"BP variability is high ({bp_variability:.1f} mmHg SD)"
            }
        
        return self.check_gate(
            output_name='bp_estimate',
            days_of_data=days_of_bp_data,
            signal_quality=signal_quality,
            has_anchor=has_bp_readings,
            anchor_recency_days=7 if has_bp_readings else None,
            additional_checks=additional_checks
        )
    
    def check_lipid_trend_gate(
        self,
        days_of_monitoring: int,
        has_lipid_panel: bool = False,
        lipid_panel_days_old: Optional[int] = None,
        has_dietary_data: bool = False
    ) -> Dict:
        """
        Specialized gate check for lipid trend analysis.
        
        Args:
            days_of_monitoring: Days of monitoring
            has_lipid_panel: Whether user has uploaded lipid panel
            lipid_panel_days_old: Days since lipid panel
            has_dietary_data: Whether user has dietary intake data
        
        Returns:
            Gating result dict
        """
        additional_checks = {}
        
        # Lipid trends require longer window
        if days_of_monitoring < 90:
            additional_checks['trend_window'] = {
                'passed': False,
                'reason': "Lipid trends require 90+ days of data",
                'remediation': "Continue monitoring for at least 90 days"
            }
        
        # Dietary data improves accuracy
        if not has_dietary_data:
            additional_checks['dietary_context'] = {
                'passed': True,  # Don't block, but note
                'reason': "No dietary data (limits interpretation of trends)"
            }
        
        return self.check_gate(
            output_name='lipid_trend',
            days_of_data=days_of_monitoring,
            signal_quality=None,  # Not sensor-based
            has_anchor=has_lipid_panel,
            anchor_recency_days=lipid_panel_days_old,
            additional_checks=additional_checks
        )
    
    def get_minimum_window(self, output_name: str) -> int:
        """Get minimum data window (days) for an output type."""
        return self.thresholds['minimum_data_windows_days'].get(
            output_name,
            self.thresholds['minimum_data_windows_days']['default']
        )
    
    def get_quality_threshold(self, range_width: RangeWidth) -> float:
        """Get minimum signal quality for a range width."""
        if range_width == RangeWidth.TIGHT:
            return self.thresholds['minimum_sensor_quality']['tight_range']
        elif range_width == RangeWidth.WIDE:
            return self.thresholds['minimum_sensor_quality']['wide_range']
        else:
            return self.thresholds['minimum_sensor_quality']['any_output']


# Singleton instance
gating_engine = GatingEngine()
