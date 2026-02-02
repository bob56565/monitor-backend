"""
Personal Baseline Modeling (Phase 2 - A2.4)

Replaces population variance with personal variance once adequate data exists.
Outputs deviation from personal baseline instead of just population norms.

Features:
- Per-stream minimum data requirements
- Personal baseline center and band computation
- Deviation scoring (z-like)
- Time-aware baselines (weekday/weekend, circadian)
- Graceful fallback to population priors
"""

from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import logging
import math
import statistics

logger = logging.getLogger(__name__)


class BaselineConfidence(str, Enum):
    """Confidence level in personal baseline."""
    INSUFFICIENT_DATA = "insufficient_data"
    LOW = "low"  # Minimum data met, but limited
    MODERATE = "moderate"  # Good data coverage
    HIGH = "high"  # Excellent data coverage


@dataclass
class PersonalBaseline:
    """
    Personal baseline for a marker or stream.
    """
    marker_name: str
    
    # Baseline statistics
    center: float  # Personal baseline center (median or mean)
    band_lower: float  # Lower bound of normal personal range
    band_upper: float  # Upper bound of normal personal range
    band_width: float  # Width of personal band
    
    # Confidence in baseline
    confidence: BaselineConfidence
    data_points_count: int
    data_span_days: float
    
    # Time-aware components (optional)
    weekday_baseline: Optional[float] = None
    weekend_baseline: Optional[float] = None
    circadian_pattern: Optional[Dict[int, float]] = None  # hour -> typical value
    
    # Metadata
    last_updated: datetime = field(default_factory=datetime.utcnow)
    
    def deviation_from_baseline(self, value: float) -> float:
        """
        Compute z-like deviation from personal baseline.
        
        Returns:
            Deviation in units of personal band width
            (0 = at center, ±1 = at band edges, >1 = outside normal range)
        """
        if self.band_width == 0:
            return 0.0
        
        deviation = (value - self.center) / (self.band_width / 2.0)
        return deviation
    
    def is_within_normal_range(self, value: float) -> bool:
        """Check if value is within personal normal range."""
        return self.band_lower <= value <= self.band_upper
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "marker": self.marker_name,
            "center": self.center,
            "band": (self.band_lower, self.band_upper),
            "band_width": self.band_width,
            "confidence": self.confidence.value,
            "data_points": self.data_points_count,
            "data_span_days": self.data_span_days,
            "weekday_baseline": self.weekday_baseline,
            "weekend_baseline": self.weekend_baseline,
            "last_updated": self.last_updated.isoformat()
        }


@dataclass
class BaselineRequirements:
    """
    Data requirements for establishing a personal baseline.
    """
    min_data_points: int
    min_days_covered: int
    min_span_days: int  # Total time span of data
    
    # Optional: require data from both weekday and weekend
    require_weekday_weekend_coverage: bool = False


class PersonalBaselineEngine:
    """
    Computes and maintains personal baselines for markers and streams.
    Falls back to population priors when insufficient data exists.
    """
    
    # Default requirements by stream type
    DEFAULT_REQUIREMENTS = {
        "glucose": BaselineRequirements(
            min_data_points=50,
            min_days_covered=14,
            min_span_days=21,
            require_weekday_weekend_coverage=True
        ),
        "vitals": BaselineRequirements(
            min_data_points=20,
            min_days_covered=7,
            min_span_days=14
        ),
        "sleep": BaselineRequirements(
            min_data_points=14,
            min_days_covered=7,
            min_span_days=14,
            require_weekday_weekend_coverage=True
        ),
        "pros": BaselineRequirements(
            min_data_points=14,
            min_days_covered=7,
            min_span_days=14
        ),
        "labs": BaselineRequirements(
            min_data_points=3,
            min_days_covered=30,
            min_span_days=90
        )
    }
    
    def __init__(self):
        """Initialize personal baseline engine."""
        self.requirements: Dict[str, BaselineRequirements] = self.DEFAULT_REQUIREMENTS.copy()
    
    def set_requirements(self, stream_or_marker: str, requirements: BaselineRequirements):
        """Set custom requirements for a stream or marker."""
        self.requirements[stream_or_marker] = requirements
    
    def compute_baseline(
        self,
        marker_name: str,
        historical_data: List[Tuple[datetime, float]],
        stream_type: Optional[str] = None
    ) -> Optional[PersonalBaseline]:
        """
        Compute personal baseline from historical data.
        
        Args:
            marker_name: Name of the marker
            historical_data: List of (timestamp, value) tuples
            stream_type: Stream type for requirements (glucose, vitals, sleep, labs)
        
        Returns:
            PersonalBaseline if sufficient data, None otherwise
        """
        if not historical_data:
            logger.debug(f"No historical data for {marker_name}")
            return None
        
        # Get requirements
        requirements = self._get_requirements(marker_name, stream_type)
        
        # Check data adequacy
        adequacy = self._check_data_adequacy(historical_data, requirements)
        
        if not adequacy["meets_requirements"]:
            logger.debug(
                f"Insufficient data for {marker_name}: {adequacy['reason']}"
            )
            return None
        
        # Compute baseline statistics
        values = [v for _, v in historical_data]
        timestamps = [t for t, _ in historical_data]
        
        # Central tendency
        center = statistics.median(values)
        
        # Personal band (using percentiles)
        sorted_values = sorted(values)
        n = len(sorted_values)
        
        # Use 10th and 90th percentiles for personal band
        p10_idx = max(0, int(n * 0.10))
        p90_idx = min(n - 1, int(n * 0.90))
        
        band_lower = sorted_values[p10_idx]
        band_upper = sorted_values[p90_idx]
        band_width = band_upper - band_lower
        
        # Determine confidence
        confidence = self._determine_confidence(
            adequacy["data_points"],
            adequacy["days_covered"],
            adequacy["span_days"],
            requirements
        )
        
        # Time-aware baselines (if enough data)
        weekday_baseline = None
        weekend_baseline = None
        
        if requirements.require_weekday_weekend_coverage and len(historical_data) >= 20:
            weekday_values = [v for t, v in historical_data if t.weekday() < 5]
            weekend_values = [v for t, v in historical_data if t.weekday() >= 5]
            
            if weekday_values and weekend_values:
                weekday_baseline = statistics.median(weekday_values)
                weekend_baseline = statistics.median(weekend_values)
        
        # Create baseline
        baseline = PersonalBaseline(
            marker_name=marker_name,
            center=center,
            band_lower=band_lower,
            band_upper=band_upper,
            band_width=band_width,
            confidence=confidence,
            data_points_count=len(values),
            data_span_days=adequacy["span_days"],
            weekday_baseline=weekday_baseline,
            weekend_baseline=weekend_baseline
        )
        
        logger.info(
            f"Computed personal baseline for {marker_name}: "
            f"center={center:.1f}, band=({band_lower:.1f}, {band_upper:.1f}), "
            f"confidence={confidence.value}"
        )
        
        return baseline
    
    def _get_requirements(
        self,
        marker_name: str,
        stream_type: Optional[str]
    ) -> BaselineRequirements:
        """Get requirements for marker or stream."""
        # Try marker-specific first
        if marker_name in self.requirements:
            return self.requirements[marker_name]
        
        # Try stream type
        if stream_type and stream_type in self.requirements:
            return self.requirements[stream_type]
        
        # Default to labs requirements
        return self.requirements.get("labs", BaselineRequirements(
            min_data_points=3,
            min_days_covered=30,
            min_span_days=90
        ))
    
    def _check_data_adequacy(
        self,
        historical_data: List[Tuple[datetime, float]],
        requirements: BaselineRequirements
    ) -> Dict[str, Any]:
        """
        Check if historical data meets requirements.
        
        Returns:
            Dictionary with adequacy info
        """
        if not historical_data:
            return {
                "meets_requirements": False,
                "reason": "No data",
                "data_points": 0,
                "days_covered": 0,
                "span_days": 0
            }
        
        # Count data points
        data_points = len(historical_data)
        
        # Compute days covered (unique days)
        dates = set(t.date() for t, _ in historical_data)
        days_covered = len(dates)
        
        # Compute span
        timestamps = [t for t, _ in historical_data]
        span_days = (max(timestamps) - min(timestamps)).total_seconds() / 86400.0
        
        # Check requirements
        reasons = []
        
        if data_points < requirements.min_data_points:
            reasons.append(
                f"Only {data_points} data points (need {requirements.min_data_points})"
            )
        
        if days_covered < requirements.min_days_covered:
            reasons.append(
                f"Only {days_covered} days covered (need {requirements.min_days_covered})"
            )
        
        if span_days < requirements.min_span_days:
            reasons.append(
                f"Only {span_days:.0f} day span (need {requirements.min_span_days})"
            )
        
        # Check weekday/weekend coverage if required
        if requirements.require_weekday_weekend_coverage:
            weekday_dates = set(t.date() for t, _ in historical_data if t.weekday() < 5)
            weekend_dates = set(t.date() for t, _ in historical_data if t.weekday() >= 5)
            
            if not weekday_dates or not weekend_dates:
                reasons.append("Missing weekday or weekend data")
        
        meets_requirements = len(reasons) == 0
        
        return {
            "meets_requirements": meets_requirements,
            "reason": "; ".join(reasons) if reasons else "All requirements met",
            "data_points": data_points,
            "days_covered": days_covered,
            "span_days": span_days
        }
    
    def _determine_confidence(
        self,
        data_points: int,
        days_covered: int,
        span_days: float,
        requirements: BaselineRequirements
    ) -> BaselineConfidence:
        """Determine confidence level in baseline."""
        
        # Score each dimension
        points_score = min(1.0, data_points / (requirements.min_data_points * 2))
        days_score = min(1.0, days_covered / (requirements.min_days_covered * 2))
        span_score = min(1.0, span_days / (requirements.min_span_days * 1.5))
        
        overall_score = (points_score + days_score + span_score) / 3.0
        
        if overall_score >= 0.8:
            return BaselineConfidence.HIGH
        elif overall_score >= 0.5:
            return BaselineConfidence.MODERATE
        else:
            return BaselineConfidence.LOW
    
    def compute_baselines_batch(
        self,
        historical_data: Dict[str, List[Tuple[datetime, float]]],
        stream_types: Optional[Dict[str, str]] = None
    ) -> Dict[str, PersonalBaseline]:
        """
        Compute baselines for multiple markers.
        
        Args:
            historical_data: Dictionary of marker_name -> [(timestamp, value), ...]
            stream_types: Optional mapping of marker_name -> stream_type
        
        Returns:
            Dictionary of marker_name -> PersonalBaseline (only for those with sufficient data)
        """
        stream_types = stream_types or {}
        baselines = {}
        
        for marker, data in historical_data.items():
            stream_type = stream_types.get(marker)
            baseline = self.compute_baseline(marker, data, stream_type)
            
            if baseline:
                baselines[marker] = baseline
        
        logger.info(
            f"Computed {len(baselines)} personal baselines from {len(historical_data)} markers"
        )
        
        return baselines
    
    def compare_to_baseline(
        self,
        baseline: PersonalBaseline,
        current_value: float
    ) -> Dict[str, Any]:
        """
        Compare current value to personal baseline.
        
        Returns:
            Comparison result with deviation, interpretation, etc.
        """
        deviation = baseline.deviation_from_baseline(current_value)
        is_normal = baseline.is_within_normal_range(current_value)
        
        # Interpret deviation
        if abs(deviation) < 0.5:
            interpretation = "at personal baseline"
        elif abs(deviation) < 1.0:
            interpretation = "slightly elevated" if deviation > 0 else "slightly depressed"
        elif abs(deviation) < 1.5:
            interpretation = "moderately elevated" if deviation > 0 else "moderately depressed"
        else:
            interpretation = "significantly elevated" if deviation > 0 else "significantly depressed"
        
        return {
            "current_value": current_value,
            "personal_baseline": baseline.center,
            "personal_range": (baseline.band_lower, baseline.band_upper),
            "deviation": deviation,
            "deviation_interpretation": interpretation,
            "is_within_normal_range": is_normal,
            "baseline_confidence": baseline.confidence.value
        }


# Global instance
_global_baseline_engine: Optional[PersonalBaselineEngine] = None


def get_personal_baseline_engine() -> PersonalBaselineEngine:
    """Get or create the global personal baseline engine instance."""
    global _global_baseline_engine
    if _global_baseline_engine is None:
        _global_baseline_engine = PersonalBaselineEngine()
    return _global_baseline_engine
