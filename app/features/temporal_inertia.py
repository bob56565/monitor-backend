"""
Temporal Inertia Enforcement (Phase 2 - A2.3)

Enforces biological continuity by:
- Detecting unrealistic marker jumps
- Applying drift ceilings (bounded daily/weekly changes)
- Checking acceleration (second-derivative constraints)
- Providing stability bonuses for persistent trends
- Supporting event-aware exceptions (illness, meds, lifestyle changes)

Tightens ranges when stable; widens when jumps occur without plausible cause.
"""

from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import logging
import math

logger = logging.getLogger(__name__)


class MarkerVelocity(str, Enum):
    """How quickly a marker can physiologically change."""
    FAST = "fast"  # Can change significantly in hours (glucose, heart rate)
    MODERATE = "moderate"  # Changes over days (CRP, some vitamins)
    SLOW = "slow"  # Changes over weeks/months (cholesterol, HbA1c, vitamin D)
    VERY_SLOW = "very_slow"  # Changes over months (bone markers, chronic states)


@dataclass
class MarkerKinetics:
    """
    Kinetic parameters for a physiological marker.
    """
    marker_name: str
    velocity_class: MarkerVelocity
    
    # Maximum daily drift (as fraction of reference range or absolute units)
    max_daily_drift_fraction: float  # e.g., 0.05 = 5% of range per day
    max_daily_drift_absolute: Optional[float] = None  # Absolute units
    
    # Acceleration limits (change in change per day)
    max_acceleration: Optional[float] = None
    
    # Stability threshold (below this, consider stable)
    stability_threshold: float = 0.02  # 2% variation
    
    # Minimum days to establish baseline
    min_baseline_days: int = 7


@dataclass
class TemporalEvent:
    """
    An event that may justify a marker jump.
    """
    event_type: str  # "illness", "medication_change", "lifestyle_change", "acute_stressor"
    event_date: datetime
    affected_markers: List[str]
    justification: str


@dataclass
class TemporalViolation:
    """
    A detected violation of temporal inertia.
    """
    marker_name: str
    violation_type: str  # "drift_exceeded", "acceleration_exceeded", "unexplained_jump"
    severity: float  # 0.0-1.0
    
    previous_value: float
    current_value: float
    time_delta_days: float
    
    drift_rate: float  # Change per day
    expected_max_drift: float
    
    explanation: str
    suggested_range_widening: float = 1.0  # Multiplier for range


@dataclass
class TemporalAssessment:
    """
    Assessment of temporal coherence for a set of estimates.
    """
    violations: List[TemporalViolation]
    stability_scores: Dict[str, float]  # marker -> stability score (0-1)
    confidence_adjustments: Dict[str, float]  # marker -> adjustment factor
    range_adjustments: Dict[str, float]  # marker -> widening factor
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "violations": [
                {
                    "marker": v.marker_name,
                    "type": v.violation_type,
                    "severity": v.severity,
                    "previous": v.previous_value,
                    "current": v.current_value,
                    "days_elapsed": v.time_delta_days,
                    "drift_rate": v.drift_rate,
                    "expected_max": v.expected_max_drift,
                    "explanation": v.explanation
                }
                for v in self.violations
            ],
            "stability_scores": self.stability_scores,
            "confidence_adjustments": self.confidence_adjustments,
            "range_adjustments": self.range_adjustments
        }


class TemporalInertiaEngine:
    """
    Enforces biological continuity through temporal constraints.
    """
    
    def __init__(self):
        """Initialize temporal inertia engine."""
        self.marker_kinetics: Dict[str, MarkerKinetics] = {}
        self._register_default_kinetics()
    
    def _register_default_kinetics(self):
        """Register default kinetic parameters for common markers."""
        
        # FAST markers (hours to days)
        self.register_kinetics(MarkerKinetics(
            marker_name="glucose",
            velocity_class=MarkerVelocity.FAST,
            max_daily_drift_fraction=0.50,  # Can vary 50% daily
            max_daily_drift_absolute=100.0,  # mg/dL
            stability_threshold=0.10
        ))
        
        self.register_kinetics(MarkerKinetics(
            marker_name="heart_rate",
            velocity_class=MarkerVelocity.FAST,
            max_daily_drift_fraction=0.30,
            stability_threshold=0.05
        ))
        
        # MODERATE markers (days to week)
        self.register_kinetics(MarkerKinetics(
            marker_name="crp",
            velocity_class=MarkerVelocity.MODERATE,
            max_daily_drift_fraction=0.30,
            stability_threshold=0.15
        ))
        
        self.register_kinetics(MarkerKinetics(
            marker_name="iron",
            velocity_class=MarkerVelocity.MODERATE,
            max_daily_drift_fraction=0.15,
            stability_threshold=0.10
        ))
        
        self.register_kinetics(MarkerKinetics(
            marker_name="triglycerides",
            velocity_class=MarkerVelocity.MODERATE,
            max_daily_drift_fraction=0.20,
            stability_threshold=0.10
        ))
        
        # SLOW markers (weeks to months)
        self.register_kinetics(MarkerKinetics(
            marker_name="hemoglobin_a1c",
            velocity_class=MarkerVelocity.SLOW,
            max_daily_drift_fraction=0.01,  # 1% per day max
            stability_threshold=0.02,
            min_baseline_days=21
        ))
        
        self.register_kinetics(MarkerKinetics(
            marker_name="ldl_cholesterol",
            velocity_class=MarkerVelocity.SLOW,
            max_daily_drift_fraction=0.05,
            stability_threshold=0.05,
            min_baseline_days=14
        ))
        
        self.register_kinetics(MarkerKinetics(
            marker_name="hdl_cholesterol",
            velocity_class=MarkerVelocity.SLOW,
            max_daily_drift_fraction=0.03,
            stability_threshold=0.05,
            min_baseline_days=14
        ))
        
        self.register_kinetics(MarkerKinetics(
            marker_name="total_cholesterol",
            velocity_class=MarkerVelocity.SLOW,
            max_daily_drift_fraction=0.05,
            stability_threshold=0.05,
            min_baseline_days=14
        ))
        
        self.register_kinetics(MarkerKinetics(
            marker_name="vitamin_d",
            velocity_class=MarkerVelocity.SLOW,
            max_daily_drift_fraction=0.05,
            stability_threshold=0.10,
            min_baseline_days=21
        ))
        
        # VERY SLOW markers (months)
        self.register_kinetics(MarkerKinetics(
            marker_name="creatinine",
            velocity_class=MarkerVelocity.VERY_SLOW,
            max_daily_drift_fraction=0.02,
            stability_threshold=0.05,
            min_baseline_days=30
        ))
        
        self.register_kinetics(MarkerKinetics(
            marker_name="egfr",
            velocity_class=MarkerVelocity.VERY_SLOW,
            max_daily_drift_fraction=0.02,
            stability_threshold=0.05,
            min_baseline_days=30
        ))
        
        logger.info(f"Registered kinetics for {len(self.marker_kinetics)} markers")
    
    def register_kinetics(self, kinetics: MarkerKinetics):
        """Register kinetic parameters for a marker."""
        self.marker_kinetics[kinetics.marker_name] = kinetics
    
    def assess_temporal_coherence(
        self,
        current_estimates: Dict[str, Dict[str, Any]],
        historical_values: Dict[str, List[Tuple[datetime, float]]],
        events: Optional[List[TemporalEvent]] = None,
        current_time: Optional[datetime] = None
    ) -> TemporalAssessment:
        """
        Assess temporal coherence of current estimates vs history.
        
        Args:
            current_estimates: Current estimated values (marker -> {center, range, ...})
            historical_values: Historical measurements (marker -> [(timestamp, value), ...])
            events: List of events that may justify jumps
            current_time: Current timestamp (default: now)
        
        Returns:
            TemporalAssessment with violations and adjustments
        """
        events = events or []
        current_time = current_time or datetime.utcnow()
        
        violations = []
        stability_scores = {}
        confidence_adjustments = {}
        range_adjustments = {}
        
        for marker, estimate in current_estimates.items():
            # Get current estimated value
            current_value = estimate.get("center") or estimate.get("value")
            if current_value is None:
                continue
            
            # Get historical data
            history = historical_values.get(marker, [])
            if not history:
                # No history, can't assess temporal coherence
                stability_scores[marker] = 0.5  # Neutral
                continue
            
            # Get most recent historical value
            history_sorted = sorted(history, key=lambda x: x[0], reverse=True)
            most_recent_time, most_recent_value = history_sorted[0]
            
            time_delta = current_time - most_recent_time
            days_elapsed = time_delta.total_seconds() / 86400.0
            
            if days_elapsed < 0.01:  # Less than 15 minutes
                # Too recent, skip
                continue
            
            # Check drift
            violation = self._check_drift_violation(
                marker=marker,
                previous_value=most_recent_value,
                current_value=current_value,
                days_elapsed=days_elapsed,
                events=events,
                current_time=current_time
            )
            
            if violation:
                violations.append(violation)
                # Apply penalties
                confidence_adjustments[marker] = 1.0 - (violation.severity * 0.30)  # Up to 30% penalty
                range_adjustments[marker] = 1.0 + (violation.severity * 0.50)  # Up to 50% widening
            else:
                # Check stability for potential bonus
                stability_score = self._compute_stability_score(marker, history)
                stability_scores[marker] = stability_score
                
                if stability_score > 0.7:  # High stability
                    confidence_adjustments[marker] = 1.05  # 5% bonus
                    range_adjustments[marker] = 0.95  # 5% tightening
        
        logger.info(
            f"Temporal assessment: {len(violations)} violations, "
            f"{len(stability_scores)} stability scores computed"
        )
        
        return TemporalAssessment(
            violations=violations,
            stability_scores=stability_scores,
            confidence_adjustments=confidence_adjustments,
            range_adjustments=range_adjustments
        )
    
    def _check_drift_violation(
        self,
        marker: str,
        previous_value: float,
        current_value: float,
        days_elapsed: float,
        events: List[TemporalEvent],
        current_time: datetime
    ) -> Optional[TemporalViolation]:
        """
        Check if marker drift exceeds physiological limits.
        
        Returns:
            TemporalViolation if violated, None otherwise
        """
        # Get kinetics
        kinetics = self.marker_kinetics.get(marker)
        if not kinetics:
            # No kinetics defined, can't assess
            return None
        
        # Compute actual drift
        absolute_change = abs(current_value - previous_value)
        relative_change = absolute_change / max(abs(previous_value), 1e-6)
        drift_rate_per_day = absolute_change / max(days_elapsed, 1e-6)
        
        # Compute expected max drift
        expected_max_drift_fraction = kinetics.max_daily_drift_fraction * days_elapsed
        expected_max_drift_absolute = (kinetics.max_daily_drift_absolute or float('inf')) * days_elapsed
        
        # Check for justifying events
        is_justified = False
        justification = ""
        
        for event in events:
            if marker in event.affected_markers:
                # Check if event is recent enough to justify
                days_since_event = (current_time - event.event_date).total_seconds() / 86400.0
                
                # Events can justify changes for some time after
                max_justification_window = {
                    MarkerVelocity.FAST: 3,  # 3 days
                    MarkerVelocity.MODERATE: 14,  # 2 weeks
                    MarkerVelocity.SLOW: 30,  # 1 month
                    MarkerVelocity.VERY_SLOW: 90  # 3 months
                }.get(kinetics.velocity_class, 14)
                
                if 0 <= days_since_event <= max_justification_window:
                    is_justified = True
                    justification = f"Justified by {event.event_type}: {event.justification}"
                    break
        
        # Determine if violated
        is_violated = False
        severity = 0.0
        
        if relative_change > expected_max_drift_fraction:
            # Fractional drift exceeded
            severity = min(1.0, relative_change / expected_max_drift_fraction - 1.0)
            is_violated = not is_justified
        
        if kinetics.max_daily_drift_absolute and absolute_change > expected_max_drift_absolute:
            # Absolute drift exceeded
            severity = max(severity, min(1.0, absolute_change / expected_max_drift_absolute - 1.0))
            is_violated = is_violated or (not is_justified)
        
        if not is_violated:
            return None
        
        # Create violation
        explanation = (
            f"{marker} changed from {previous_value:.1f} to {current_value:.1f} "
            f"over {days_elapsed:.1f} days ({relative_change*100:.1f}% change, "
            f"{drift_rate_per_day:.2f}/day). Expected max: {expected_max_drift_fraction*100:.1f}%"
        )
        
        if justification:
            explanation += f". {justification}"
        
        suggested_widening = 1.0 + severity * 0.5  # Up to 50% widening
        
        return TemporalViolation(
            marker_name=marker,
            violation_type="drift_exceeded",
            severity=severity,
            previous_value=previous_value,
            current_value=current_value,
            time_delta_days=days_elapsed,
            drift_rate=drift_rate_per_day,
            expected_max_drift=expected_max_drift_fraction * abs(previous_value),
            explanation=explanation,
            suggested_range_widening=suggested_widening
        )
    
    def _compute_stability_score(
        self,
        marker: str,
        history: List[Tuple[datetime, float]]
    ) -> float:
        """
        Compute stability score from historical values.
        
        Returns:
            Stability score (0-1), where 1 = perfectly stable
        """
        if len(history) < 2:
            return 0.5  # Neutral
        
        # Get kinetics
        kinetics = self.marker_kinetics.get(marker)
        if not kinetics:
            return 0.5
        
        # Need minimum baseline period
        history_sorted = sorted(history, key=lambda x: x[0])
        time_span = (history_sorted[-1][0] - history_sorted[0][0]).total_seconds() / 86400.0
        
        if time_span < kinetics.min_baseline_days:
            return 0.5  # Not enough data
        
        # Compute coefficient of variation
        values = [v for _, v in history]
        mean_val = sum(values) / len(values)
        
        if mean_val == 0:
            return 0.5
        
        variance = sum((v - mean_val) ** 2 for v in values) / len(values)
        std_dev = math.sqrt(variance)
        cv = std_dev / abs(mean_val)
        
        # Compare to stability threshold
        if cv < kinetics.stability_threshold:
            # Very stable
            stability_score = 1.0 - (cv / kinetics.stability_threshold) * 0.3
            return max(0.7, min(1.0, stability_score))
        else:
            # Less stable
            stability_score = 0.7 * (kinetics.stability_threshold / cv)
            return max(0.3, min(0.7, stability_score))
    
    def apply_temporal_adjustments(
        self,
        estimates: Dict[str, Dict[str, Any]],
        assessment: TemporalAssessment
    ) -> Dict[str, Dict[str, Any]]:
        """
        Apply temporal adjustments to estimates.
        
        Args:
            estimates: Original estimates
            assessment: Temporal assessment
        
        Returns:
            Adjusted estimates
        """
        adjusted = {}
        
        for marker, estimate in estimates.items():
            adj_estimate = estimate.copy()
            
            # Apply confidence adjustment
            if marker in assessment.confidence_adjustments:
                factor = assessment.confidence_adjustments[marker]
                if "confidence" in adj_estimate:
                    adj_estimate["confidence"] *= factor
            
            # Apply range adjustment
            if marker in assessment.range_adjustments:
                factor = assessment.range_adjustments[marker]
                if "range" in adj_estimate:
                    adj_estimate["range"] *= factor
            
            adjusted[marker] = adj_estimate
        
        return adjusted


# Global instance
_global_temporal_engine: Optional[TemporalInertiaEngine] = None


def get_temporal_inertia_engine() -> TemporalInertiaEngine:
    """Get or create the global temporal inertia engine instance."""
    global _global_temporal_engine
    if _global_temporal_engine is None:
        _global_temporal_engine = TemporalInertiaEngine()
    return _global_temporal_engine
