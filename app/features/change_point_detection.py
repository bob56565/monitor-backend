"""
Change Point Detection (Phase 3 A2.3)

Detects meaningful inflection points, early deterioration, and recovery signals
in longitudinal physiological data. Respects temporal inertia constraints and
marker-specific kinetics.

Key Features:
- Statistical change point detection (Bayesian, PELT, segmentation)
- Direction and magnitude quantification
- Clinical relevance flagging
- Marker-specific sensitivity (fast vs slow systems)
- False positive penalty via confidence reduction

Design Principles:
- Respect temporal inertia constraints
- Explainable events (what changed, when, why)
- Marker-specific detection (glucose vs A1c vs creatinine)
- Conservative detection to minimize false positives
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple
import math
from collections import defaultdict


class ChangePointType(str, Enum):
    """Type of change point detected."""
    STEP_UP = "step_up"  # Sudden increase
    STEP_DOWN = "step_down"  # Sudden decrease
    TREND_ACCELERATION = "trend_acceleration"  # Slope increases
    TREND_DECELERATION = "trend_deceleration"  # Slope decreases
    VOLATILITY_INCREASE = "volatility_increase"  # Variance increases
    VOLATILITY_DECREASE = "volatility_decrease"  # Variance decreases
    REGIME_CHANGE = "regime_change"  # Complete pattern shift


class ChangeDirection(str, Enum):
    """Direction of change."""
    IMPROVING = "improving"
    WORSENING = "worsening"
    NEUTRAL = "neutral"


class ClinicalRelevance(str, Enum):
    """Clinical relevance of change."""
    HIGH = "high"  # Clinically significant
    MODERATE = "moderate"  # Noteworthy
    LOW = "low"  # Statistical only
    UNCERTAIN = "uncertain"  # Unclear significance


@dataclass
class ChangePointEvent:
    """Detected change point event."""
    # Event identification
    event_id: str
    marker_id: str
    
    # Timing
    change_point_timestamp: datetime
    detection_timestamp: datetime
    days_ago: float
    
    # Change characteristics
    change_type: ChangePointType
    direction: ChangeDirection
    magnitude: float  # Change in marker units
    magnitude_percent: float  # Percent change
    
    # Statistical confidence
    statistical_confidence: float  # 0.0 to 1.0
    p_value: Optional[float]
    
    # Clinical relevance
    clinical_relevance: ClinicalRelevance
    crosses_threshold: bool  # Did it cross a clinical threshold?
    
    # Context
    before_value_mean: float
    after_value_mean: float
    before_variability: float
    after_variability: float
    
    # Explanation
    likely_cause: Optional[str]
    clinical_interpretation: str
    
    # Related events
    related_marker_changes: List[str]  # Other markers that changed around same time


@dataclass
class ChangePointAnalysis:
    """Complete change point analysis for a marker."""
    marker_id: str
    
    # Detected events
    events: List[ChangePointEvent]
    recent_events: List[ChangePointEvent]  # Last 90 days
    
    # Current state
    current_phase: str  # "stable", "improving", "deteriorating", "volatile"
    phase_confidence: float
    
    # Trajectory summary
    overall_trend: str  # "stable", "increasing", "decreasing"
    trend_strength: float  # 0.0 to 1.0
    
    # Early warning signals
    early_warning_flags: List[str]
    
    # Recovery signals
    recovery_signals: List[str]


@dataclass
class MultiMarkerChangeAnalysis:
    """Cross-marker change point analysis."""
    # Synchronized events (multiple markers changing together)
    synchronized_events: List[Dict[str, any]]
    
    # Leading indicators (marker A changes before marker B)
    leading_indicators: List[Dict[str, any]]
    
    # Systemic changes (broad pattern across markers)
    systemic_changes: List[Dict[str, any]]


class ChangePointDetector:
    """
    Detector for meaningful inflection points in longitudinal data.
    
    Algorithm:
    1. Segment time series into phases (Bayesian change point detection)
    2. Characterize each change (type, magnitude, direction)
    3. Assess clinical relevance
    4. Filter false positives using temporal inertia
    5. Identify likely causes
    6. Cross-reference related markers
    """
    
    def __init__(self):
        # Marker-specific sensitivity thresholds
        self.sensitivity_thresholds = self._initialize_sensitivity_thresholds()
        
        # Clinical thresholds for relevance assessment
        self.clinical_thresholds = self._initialize_clinical_thresholds()
        
        # Minimum data requirements
        self.min_points_before = 10
        self.min_points_after = 5
        self.min_days_coverage = 14
    
    def detect_change_points(
        self,
        marker_id: str,
        historical_data: List[Dict],
        marker_kinetics: Optional[Dict] = None
    ) -> ChangePointAnalysis:
        """
        Detect change points for a single marker.
        
        Args:
            marker_id: Marker identifier
            historical_data: Time series data points
            marker_kinetics: Optional kinetics info from temporal inertia
        
        Returns:
            ChangePointAnalysis with detected events and summary
        """
        # 1. Validate data sufficiency
        if not self._has_sufficient_data(historical_data):
            return self._empty_analysis(marker_id)
        
        # 2. Preprocess and sort data
        clean_data = self._preprocess_data(historical_data)
        
        # 3. Detect change points using statistical methods
        candidate_points = self._bayesian_change_point_detection(clean_data, marker_id)
        
        # 4. Characterize each change point
        events = []
        for cp in candidate_points:
            event = self._characterize_change_point(cp, clean_data, marker_id, marker_kinetics)
            if event:
                events.append(event)
        
        # 5. Filter false positives using temporal inertia
        filtered_events = self._filter_false_positives(events, marker_id, marker_kinetics)
        
        # 6. Identify recent events (last 90 days)
        recent = [e for e in filtered_events if e.days_ago <= 90]
        
        # 7. Assess current phase
        current_phase, phase_conf = self._assess_current_phase(clean_data, filtered_events)
        
        # 8. Compute overall trend
        overall_trend, trend_strength = self._compute_overall_trend(clean_data)
        
        # 9. Detect early warning signals
        early_warnings = self._detect_early_warnings(clean_data, filtered_events, marker_id)
        
        # 10. Detect recovery signals
        recovery_signals = self._detect_recovery_signals(clean_data, filtered_events, marker_id)
        
        return ChangePointAnalysis(
            marker_id=marker_id,
            events=filtered_events,
            recent_events=recent,
            current_phase=current_phase,
            phase_confidence=phase_conf,
            overall_trend=overall_trend,
            trend_strength=trend_strength,
            early_warning_flags=early_warnings,
            recovery_signals=recovery_signals
        )
    
    def detect_multi_marker_changes(
        self,
        marker_analyses: Dict[str, ChangePointAnalysis],
        historical_data: Dict[str, List[Dict]]
    ) -> MultiMarkerChangeAnalysis:
        """Detect synchronized and systemic changes across markers."""
        # 1. Find synchronized events (changes within 7 days of each other)
        synchronized = self._find_synchronized_events(marker_analyses)
        
        # 2. Find leading indicators (A changes before B consistently)
        leading = self._find_leading_indicators(marker_analyses)
        
        # 3. Detect systemic changes (many markers changing)
        systemic = self._detect_systemic_changes(marker_analyses)
        
        return MultiMarkerChangeAnalysis(
            synchronized_events=synchronized,
            leading_indicators=leading,
            systemic_changes=systemic
        )
    
    # ===== Core Algorithm Methods =====
    
    def _bayesian_change_point_detection(
        self,
        data: List[Dict],
        marker_id: str
    ) -> List[Dict]:
        """
        Bayesian change point detection (simplified implementation).
        
        Returns list of candidate change points with:
        - timestamp
        - index
        - probability
        """
        if len(data) < 20:
            return []
        
        candidates = []
        
        # Sliding window approach (simplified)
        window_size = 10
        
        for i in range(window_size, len(data) - window_size):
            # Compute statistics before and after
            before = [p["value"] for p in data[i-window_size:i]]
            after = [p["value"] for p in data[i:i+window_size]]
            
            mean_before = sum(before) / len(before)
            mean_after = sum(after) / len(after)
            
            std_before = self._std(before)
            std_after = self._std(after)
            
            # Test for mean shift
            mean_shift = abs(mean_after - mean_before)
            pooled_std = math.sqrt((std_before**2 + std_after**2) / 2)
            
            if pooled_std > 0:
                t_statistic = mean_shift / (pooled_std * math.sqrt(2 / window_size))
            else:
                t_statistic = 0
            
            # Convert to probability (heuristic)
            probability = min(1.0, t_statistic / 3.0)
            
            # Threshold: require prob > 0.7
            if probability > 0.7:
                candidates.append({
                    "timestamp": data[i]["timestamp"],
                    "index": i,
                    "probability": probability,
                    "mean_before": mean_before,
                    "mean_after": mean_after,
                    "std_before": std_before,
                    "std_after": std_after
                })
        
        # Deduplicate nearby candidates (keep strongest within 7 days)
        deduplicated = self._deduplicate_change_points(candidates, days_threshold=7)
        
        return deduplicated
    
    def _characterize_change_point(
        self,
        candidate: Dict,
        data: List[Dict],
        marker_id: str,
        kinetics: Optional[Dict]
    ) -> Optional[ChangePointEvent]:
        """Characterize a candidate change point."""
        idx = candidate["index"]
        timestamp = candidate["timestamp"]
        probability = candidate["probability"]
        
        mean_before = candidate["mean_before"]
        mean_after = candidate["mean_after"]
        std_before = candidate["std_before"]
        std_after = candidate["std_after"]
        
        # Compute magnitude
        magnitude = mean_after - mean_before
        magnitude_pct = (magnitude / mean_before * 100) if mean_before != 0 else 0
        
        # Determine change type
        change_type = self._classify_change_type(
            mean_before, mean_after, std_before, std_after
        )
        
        # Determine direction
        direction = self._determine_direction(magnitude, marker_id)
        
        # Assess clinical relevance
        relevance = self._assess_clinical_relevance(
            marker_id, magnitude, magnitude_pct, mean_before, mean_after
        )
        
        # Check threshold crossing
        crosses_threshold = self._crosses_clinical_threshold(
            marker_id, mean_before, mean_after
        )
        
        # Generate interpretation
        interpretation = self._generate_clinical_interpretation(
            marker_id, change_type, direction, magnitude, relevance
        )
        
        # Attempt to identify likely cause
        likely_cause = self._identify_likely_cause(
            marker_id, change_type, direction, timestamp, data
        )
        
        # Find related marker changes (placeholder for now)
        related = []
        
        # Compute days ago
        days_ago = (datetime.now() - timestamp).total_seconds() / 86400
        
        event_id = f"{marker_id}_{timestamp.strftime('%Y%m%d')}"
        
        return ChangePointEvent(
            event_id=event_id,
            marker_id=marker_id,
            change_point_timestamp=timestamp,
            detection_timestamp=datetime.now(),
            days_ago=days_ago,
            change_type=change_type,
            direction=direction,
            magnitude=magnitude,
            magnitude_percent=magnitude_pct,
            statistical_confidence=probability,
            p_value=None,
            clinical_relevance=relevance,
            crosses_threshold=crosses_threshold,
            before_value_mean=mean_before,
            after_value_mean=mean_after,
            before_variability=std_before,
            after_variability=std_after,
            likely_cause=likely_cause,
            clinical_interpretation=interpretation,
            related_marker_changes=related
        )
    
    def _filter_false_positives(
        self,
        events: List[ChangePointEvent],
        marker_id: str,
        kinetics: Optional[Dict]
    ) -> List[ChangePointEvent]:
        """Filter false positives using temporal inertia constraints."""
        if not kinetics:
            # No filtering without kinetics
            return events
        
        filtered = []
        
        for event in events:
            # Check if change respects temporal inertia
            daily_limit = kinetics.get("daily_drift_ceiling_percent", 100.0)
            
            # Compute implied daily rate
            # (Simplified: assume change happened over 1 day)
            implied_daily_rate = abs(event.magnitude_percent)
            
            if implied_daily_rate <= daily_limit * 3:  # Allow 3x for true change points
                filtered.append(event)
            else:
                # Too extreme, likely false positive
                pass
        
        return filtered
    
    def _classify_change_type(
        self,
        mean_before: float,
        mean_after: float,
        std_before: float,
        std_after: float
    ) -> ChangePointType:
        """Classify type of change."""
        mean_change = abs(mean_after - mean_before)
        mean_avg = (mean_before + mean_after) / 2
        
        # Mean change relative to average
        mean_change_ratio = mean_change / mean_avg if mean_avg > 0 else 0
        
        # Volatility change
        vol_change_ratio = (std_after - std_before) / std_before if std_before > 0 else 0
        
        # Classify
        if mean_change_ratio > 0.15:  # 15% mean shift
            if mean_after > mean_before:
                return ChangePointType.STEP_UP
            else:
                return ChangePointType.STEP_DOWN
        elif abs(vol_change_ratio) > 0.5:  # 50% volatility change
            if vol_change_ratio > 0:
                return ChangePointType.VOLATILITY_INCREASE
            else:
                return ChangePointType.VOLATILITY_DECREASE
        else:
            return ChangePointType.REGIME_CHANGE
    
    def _determine_direction(self, magnitude: float, marker_id: str) -> ChangeDirection:
        """Determine if change is improving or worsening."""
        # For most markers, lower is better (glucose, cholesterol, etc.)
        # Exceptions: HDL (higher better), some vitamins
        
        better_when_lower = [
            "glucose", "a1c", "ldl", "triglycerides", "creatinine",
            "blood_pressure_systolic", "blood_pressure_diastolic"
        ]
        
        better_when_higher = [
            "hdl", "vitamin_d", "hemoglobin", "egfr"
        ]
        
        if magnitude > 0:  # Increased
            if marker_id in better_when_lower:
                return ChangeDirection.WORSENING
            elif marker_id in better_when_higher:
                return ChangeDirection.IMPROVING
            else:
                return ChangeDirection.NEUTRAL
        elif magnitude < 0:  # Decreased
            if marker_id in better_when_lower:
                return ChangeDirection.IMPROVING
            elif marker_id in better_when_higher:
                return ChangeDirection.WORSENING
            else:
                return ChangeDirection.NEUTRAL
        else:
            return ChangeDirection.NEUTRAL
    
    def _assess_clinical_relevance(
        self,
        marker_id: str,
        magnitude: float,
        magnitude_pct: float,
        before: float,
        after: float
    ) -> ClinicalRelevance:
        """Assess clinical relevance of change."""
        # Get clinical thresholds
        thresholds = self.clinical_thresholds.get(marker_id, {})
        
        minimal_change = thresholds.get("minimal", float('inf'))
        moderate_change = thresholds.get("moderate", float('inf'))
        large_change = thresholds.get("large", float('inf'))
        
        abs_magnitude = abs(magnitude)
        
        if abs_magnitude >= large_change:
            return ClinicalRelevance.HIGH
        elif abs_magnitude >= moderate_change:
            return ClinicalRelevance.MODERATE
        elif abs_magnitude >= minimal_change:
            return ClinicalRelevance.LOW
        else:
            return ClinicalRelevance.UNCERTAIN
    
    def _crosses_clinical_threshold(
        self,
        marker_id: str,
        before: float,
        after: float
    ) -> bool:
        """Check if change crosses a clinical threshold."""
        thresholds = {
            "glucose": [100, 126],  # Prediabetes, diabetes
            "a1c": [5.7, 6.5],
            "ldl": [100, 130, 160],
            "triglycerides": [150, 200],
            "blood_pressure_systolic": [120, 130, 140]
        }
        
        if marker_id not in thresholds:
            return False
        
        for threshold in thresholds[marker_id]:
            # Check if crossed
            if (before < threshold <= after) or (after < threshold <= before):
                return True
        
        return False
    
    def _generate_clinical_interpretation(
        self,
        marker_id: str,
        change_type: ChangePointType,
        direction: ChangeDirection,
        magnitude: float,
        relevance: ClinicalRelevance
    ) -> str:
        """Generate human-readable clinical interpretation."""
        parts = []
        
        # Magnitude descriptor
        if abs(magnitude) > 20:
            parts.append("Large")
        elif abs(magnitude) > 10:
            parts.append("Moderate")
        else:
            parts.append("Small")
        
        # Direction
        if magnitude > 0:
            parts.append("increase")
        else:
            parts.append("decrease")
        
        # Marker
        parts.append(f"in {marker_id}")
        
        # Clinical context
        if direction == ChangeDirection.IMPROVING:
            parts.append("(favorable trend)")
        elif direction == ChangeDirection.WORSENING:
            parts.append("(concerning trend)")
        
        return " ".join(parts) + "."
    
    def _identify_likely_cause(
        self,
        marker_id: str,
        change_type: ChangePointType,
        direction: ChangeDirection,
        timestamp: datetime,
        data: List[Dict]
    ) -> Optional[str]:
        """Attempt to identify likely cause of change."""
        # Placeholder: would check for:
        # - Medication changes
        # - Lifestyle events
        # - Illness markers
        # - Seasonal patterns
        
        # For now, return generic causes
        if change_type == ChangePointType.STEP_UP:
            return "Possible medication change, lifestyle shift, or illness"
        elif change_type == ChangePointType.STEP_DOWN:
            return "Possible intervention effect or recovery"
        elif change_type == ChangePointType.VOLATILITY_INCREASE:
            return "Increased instability or measurement variability"
        else:
            return None
    
    def _assess_current_phase(
        self,
        data: List[Dict],
        events: List[ChangePointEvent]
    ) -> Tuple[str, float]:
        """Assess current phase based on recent data and events."""
        if len(data) < 10:
            return "insufficient_data", 0.0
        
        # Look at last 30 days
        recent = data[-30:] if len(data) >= 30 else data
        
        # Compute recent variability
        values = [p["value"] for p in recent]
        std = self._std(values)
        mean_val = sum(values) / len(values)
        cv = std / mean_val if mean_val > 0 else 0
        
        # Check for recent events
        recent_events = [e for e in events if e.days_ago <= 30]
        
        if cv > 0.2:
            return "volatile", 0.7
        elif recent_events:
            latest = recent_events[0]
            if latest.direction == ChangeDirection.IMPROVING:
                return "improving", 0.6
            elif latest.direction == ChangeDirection.WORSENING:
                return "deteriorating", 0.6
        
        # Otherwise stable
        return "stable", 0.8
    
    def _compute_overall_trend(self, data: List[Dict]) -> Tuple[str, float]:
        """Compute overall trend using linear regression."""
        if len(data) < 10:
            return "insufficient_data", 0.0
        
        # Simple linear regression
        n = len(data)
        x = list(range(n))
        y = [p["value"] for p in data]
        
        x_mean = sum(x) / n
        y_mean = sum(y) / n
        
        numerator = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            return "stable", 0.0
        
        slope = numerator / denominator
        
        # Normalize slope to [-1, 1]
        slope_normalized = slope / max(abs(slope), 0.01)
        
        if slope_normalized > 0.1:
            return "increasing", min(abs(slope_normalized), 1.0)
        elif slope_normalized < -0.1:
            return "decreasing", min(abs(slope_normalized), 1.0)
        else:
            return "stable", 1.0 - abs(slope_normalized)
    
    def _detect_early_warnings(
        self,
        data: List[Dict],
        events: List[ChangePointEvent],
        marker_id: str
    ) -> List[str]:
        """Detect early warning signals."""
        warnings = []
        
        if len(data) < 20:
            return warnings
        
        # Check recent volatility increase
        recent = data[-14:] if len(data) >= 14 else data
        early = data[-28:-14] if len(data) >= 28 else []
        
        if early:
            recent_std = self._std([p["value"] for p in recent])
            early_std = self._std([p["value"] for p in early])
            
            if recent_std > early_std * 1.5:
                warnings.append("Increased variability (early instability signal)")
        
        # Check for small upward drift
        recent_values = [p["value"] for p in recent]
        if len(recent_values) >= 7:
            first_half = sum(recent_values[:7]) / 7
            second_half = sum(recent_values[-7:]) / 7
            
            if second_half > first_half * 1.05:
                warnings.append("Gradual upward drift detected")
        
        return warnings
    
    def _detect_recovery_signals(
        self,
        data: List[Dict],
        events: List[ChangePointEvent],
        marker_id: str
    ) -> List[str]:
        """Detect recovery signals."""
        signals = []
        
        # Check for recent favorable change events
        recent_events = [e for e in events if e.days_ago <= 60]
        improving_events = [e for e in recent_events if e.direction == ChangeDirection.IMPROVING]
        
        if improving_events:
            signals.append("Recent favorable trend detected")
        
        # Check for stabilization after volatility
        if len(data) >= 30:
            recent = data[-14:]
            earlier = data[-30:-14]
            
            recent_std = self._std([p["value"] for p in recent])
            earlier_std = self._std([p["value"] for p in earlier])
            
            if earlier_std > recent_std * 1.3:
                signals.append("Stabilization after volatility")
        
        return signals
    
    def _find_synchronized_events(
        self,
        marker_analyses: Dict[str, ChangePointAnalysis]
    ) -> List[Dict[str, any]]:
        """Find synchronized events across markers."""
        synchronized = []
        
        # Collect all events with timestamps
        all_events = []
        for marker_id, analysis in marker_analyses.items():
            for event in analysis.events:
                all_events.append((marker_id, event))
        
        # Group events within 7 days
        time_window = timedelta(days=7)
        
        for i, (marker1, event1) in enumerate(all_events):
            related = [(marker1, event1)]
            
            for j, (marker2, event2) in enumerate(all_events):
                if i != j:
                    time_diff = abs(event1.change_point_timestamp - event2.change_point_timestamp)
                    if time_diff <= time_window:
                        related.append((marker2, event2))
            
            if len(related) >= 2:  # At least 2 markers changing together
                synchronized.append({
                    "timestamp": event1.change_point_timestamp,
                    "markers": [m for m, e in related],
                    "count": len(related)
                })
        
        # Deduplicate
        seen = set()
        unique = []
        for s in synchronized:
            key = (s["timestamp"], tuple(sorted(s["markers"])))
            if key not in seen:
                seen.add(key)
                unique.append(s)
        
        return unique
    
    def _find_leading_indicators(
        self,
        marker_analyses: Dict[str, ChangePointAnalysis]
    ) -> List[Dict[str, any]]:
        """Find leading indicators (A changes before B)."""
        # Placeholder for now
        return []
    
    def _detect_systemic_changes(
        self,
        marker_analyses: Dict[str, ChangePointAnalysis]
    ) -> List[Dict[str, any]]:
        """Detect systemic changes across many markers."""
        # Count markers in each phase
        phase_counts = defaultdict(int)
        
        for analysis in marker_analyses.values():
            phase_counts[analysis.current_phase] += 1
        
        systemic = []
        
        # If many markers deteriorating
        if phase_counts.get("deteriorating", 0) >= 3:
            systemic.append({
                "type": "broad_deterioration",
                "markers_affected": phase_counts["deteriorating"],
                "interpretation": "Multiple physiological systems showing concerning trends"
            })
        
        # If many markers improving
        if phase_counts.get("improving", 0) >= 3:
            systemic.append({
                "type": "broad_improvement",
                "markers_affected": phase_counts["improving"],
                "interpretation": "Multiple physiological systems showing favorable trends"
            })
        
        return systemic
    
    # ===== Helper Methods =====
    
    def _has_sufficient_data(self, data: List[Dict]) -> bool:
        """Check if data is sufficient for analysis."""
        if not data or len(data) < 20:
            return False
        
        # Check time coverage
        if len(data) >= 2:
            first = data[0]["timestamp"]
            last = data[-1]["timestamp"]
            days = (last - first).total_seconds() / 86400
            if days < self.min_days_coverage:
                return False
        
        return True
    
    def _preprocess_data(self, data: List[Dict]) -> List[Dict]:
        """Preprocess and clean data."""
        # Remove nulls
        clean = [p for p in data if p.get("value") is not None]
        
        # Sort by timestamp
        clean.sort(key=lambda p: p["timestamp"])
        
        # Remove outliers (simple IQR method)
        if len(clean) >= 10:
            values = [p["value"] for p in clean]
            q1 = self._percentile(values, 25)
            q3 = self._percentile(values, 75)
            iqr = q3 - q1
            lower = q1 - 3 * iqr
            upper = q3 + 3 * iqr
            
            clean = [p for p in clean if lower <= p["value"] <= upper]
        
        return clean
    
    def _empty_analysis(self, marker_id: str) -> ChangePointAnalysis:
        """Return empty analysis when data insufficient."""
        return ChangePointAnalysis(
            marker_id=marker_id,
            events=[],
            recent_events=[],
            current_phase="insufficient_data",
            phase_confidence=0.0,
            overall_trend="insufficient_data",
            trend_strength=0.0,
            early_warning_flags=[],
            recovery_signals=[]
        )
    
    def _deduplicate_change_points(
        self,
        candidates: List[Dict],
        days_threshold: int
    ) -> List[Dict]:
        """Deduplicate nearby change points."""
        if not candidates:
            return []
        
        # Sort by probability
        sorted_candidates = sorted(candidates, key=lambda c: c["probability"], reverse=True)
        
        deduplicated = []
        
        for candidate in sorted_candidates:
            # Check if too close to existing
            too_close = False
            for existing in deduplicated:
                time_diff = abs(candidate["timestamp"] - existing["timestamp"])
                if time_diff.days <= days_threshold:
                    too_close = True
                    break
            
            if not too_close:
                deduplicated.append(candidate)
        
        return deduplicated
    
    def _std(self, values: List[float]) -> float:
        """Compute standard deviation."""
        if len(values) < 2:
            return 0.0
        
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
        return math.sqrt(variance)
    
    def _percentile(self, values: List[float], p: float) -> float:
        """Compute percentile."""
        sorted_values = sorted(values)
        k = (len(sorted_values) - 1) * (p / 100.0)
        f = math.floor(k)
        c = math.ceil(k)
        
        if f == c:
            return sorted_values[int(k)]
        
        d0 = sorted_values[int(f)] * (c - k)
        d1 = sorted_values[int(c)] * (k - f)
        return d0 + d1
    
    def _initialize_sensitivity_thresholds(self) -> Dict[str, Dict]:
        """Initialize marker-specific sensitivity thresholds."""
        return {
            "glucose": {"minimal": 5, "moderate": 15, "large": 30},
            "a1c": {"minimal": 0.2, "moderate": 0.5, "large": 1.0},
            "ldl": {"minimal": 10, "moderate": 20, "large": 40},
            "triglycerides": {"minimal": 20, "moderate": 50, "large": 100},
            "blood_pressure_systolic": {"minimal": 5, "moderate": 10, "large": 20},
            "creatinine": {"minimal": 0.1, "moderate": 0.2, "large": 0.5}
        }
    
    def _initialize_clinical_thresholds(self) -> Dict[str, Dict]:
        """Initialize clinical thresholds for relevance."""
        return self._initialize_sensitivity_thresholds()


# ===== Singleton =====

_detector_instance = None

def get_change_point_detector() -> ChangePointDetector:
    """Get singleton instance of change point detector."""
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = ChangePointDetector()
    return _detector_instance
