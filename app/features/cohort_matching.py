"""
Cohort Matching Engine (Phase 3 A2.2)

Matches users to nearest physiological neighbors to contextualize trajectories,
stability, and risk patterns. Provides percentile positioning and expected
trajectory bands based on similar cohorts.

Key Features:
- Multi-dimensional similarity matching (age, sex, BMI, key markers, trends)
- Nearest neighbor cohort identification
- Percentile position computation
- Expected trajectory band estimation
- Anonymized reference dataset usage

Design Principles:
- Descriptive, not prescriptive comparisons
- Suppress cohort claims when similarity is low
- Widen uncertainty when cohort mismatch exists
- Respect privacy (anonymized data only)
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple
import math
from collections import defaultdict


class CohortDimension(str, Enum):
    """Dimensions used for cohort matching."""
    AGE = "age"
    SEX = "sex"
    BMI = "bmi"
    KEY_MARKERS = "key_markers"
    LONGITUDINAL_TRENDS = "longitudinal_trends"
    ACTIVITY_LEVEL = "activity_level"
    MEDICATION_BURDEN = "medication_burden"


class SimilarityLevel(str, Enum):
    """Level of similarity to matched cohort."""
    VERY_HIGH = "very_high"  # >0.85
    HIGH = "high"  # 0.70-0.85
    MODERATE = "moderate"  # 0.50-0.70
    LOW = "low"  # 0.30-0.50
    VERY_LOW = "very_low"  # <0.30


@dataclass
class CohortMatchingProfile:
    """User profile for cohort matching."""
    # Demographics
    age: Optional[float]
    sex: Optional[str]
    bmi: Optional[float]
    
    # Key physiological markers
    glucose_mean: Optional[float]
    a1c: Optional[float]
    cholesterol_total: Optional[float]
    hdl: Optional[float]
    creatinine: Optional[float]
    
    # Longitudinal trend features
    glucose_trend_slope: Optional[float]  # mg/dL per month
    weight_trend_slope: Optional[float]  # kg per month
    activity_level: Optional[float]  # steps/day average
    
    # Medication burden
    medication_count: Optional[int]
    takes_metformin: bool
    takes_statins: bool


@dataclass
class CohortReference:
    """Reference cohort for comparison."""
    cohort_id: str
    cohort_name: str
    
    # Cohort characteristics (centroid)
    age_range: Tuple[float, float]
    sex: str
    bmi_range: Tuple[float, float]
    
    # Key marker ranges (10th-90th percentiles)
    glucose_percentiles: Tuple[float, float]
    a1c_percentiles: Tuple[float, float]
    cholesterol_percentiles: Tuple[float, float]
    
    # Expected trajectories
    glucose_trajectory_slope_mean: float
    glucose_trajectory_slope_std: float
    
    # Cohort size
    n_members: int
    
    # Risk profiles
    diabetes_prevalence: float
    cvd_prevalence: float


@dataclass
class CohortMatchResult:
    """Result of cohort matching."""
    # Matched cohort
    matched_cohort_id: str
    matched_cohort_name: str
    
    # Similarity
    overall_similarity_score: float  # 0.0 to 1.0
    similarity_level: SimilarityLevel
    dimension_scores: Dict[str, float]  # dimension -> score
    
    # Percentile positions
    glucose_percentile: Optional[float]
    a1c_percentile: Optional[float]
    bmi_percentile: Optional[float]
    
    # Expected trajectory
    expected_glucose_trajectory: Optional[Tuple[float, float]]  # (mean, std)
    trajectory_deviation: Optional[float]  # user's trajectory vs expected
    
    # Risk context
    cohort_diabetes_prevalence: float
    cohort_cvd_prevalence: float
    
    # Confidence
    match_confidence: float  # 0.0 to 1.0
    suppress_cohort_claims: bool  # True if similarity too low
    
    # Explanation
    why_this_cohort: str
    key_similarities: List[str]
    key_differences: List[str]


@dataclass
class TrajectoryBand:
    """Expected trajectory band for a marker."""
    marker_id: str
    
    # Current position
    current_value: float
    cohort_percentile: float
    
    # Expected trajectory (next 3, 6, 12 months)
    trajectory_3mo: Tuple[float, float, float]  # (low, mid, high)
    trajectory_6mo: Tuple[float, float, float]
    trajectory_12mo: Tuple[float, float, float]
    
    # Confidence
    trajectory_confidence: float
    
    # Explanation
    trajectory_interpretation: str  # "stable", "improving", "worsening"


class CohortMatchingEngine:
    """
    Engine that matches users to physiological neighbors for contextualization.
    
    Algorithm:
    1. Extract user profile from current data
    2. Compute similarity to all reference cohorts
    3. Select nearest neighbor cohort
    4. Compute percentile positions
    5. Estimate expected trajectory bands
    6. Assess match confidence and decide whether to suppress
    """
    
    def __init__(self):
        # Reference cohorts (anonymized synthetic data)
        self.reference_cohorts = self._load_reference_cohorts()
        
        # Dimension weights for similarity scoring
        self.dimension_weights = {
            CohortDimension.AGE: 0.20,
            CohortDimension.SEX: 0.15,
            CohortDimension.BMI: 0.15,
            CohortDimension.KEY_MARKERS: 0.30,
            CohortDimension.LONGITUDINAL_TRENDS: 0.15,
            CohortDimension.MEDICATION_BURDEN: 0.03,
            CohortDimension.ACTIVITY_LEVEL: 0.02
        }
        
        # Similarity threshold for suppression
        self.suppression_threshold = 0.30
    
    def match_cohort(
        self,
        current_estimates: Dict[str, Dict],
        measured_anchors: Dict[str, any],
        historical_data: Dict[str, List[Dict]],
        user_metadata: Dict[str, any]
    ) -> CohortMatchResult:
        """
        Main matching method: find nearest neighbor cohort.
        
        Returns CohortMatchResult with matched cohort, similarity scores,
        percentile positions, and trajectory expectations.
        """
        # 1. Extract user profile
        user_profile = self._extract_user_profile(
            current_estimates, measured_anchors, historical_data, user_metadata
        )
        
        # 2. Compute similarity to all cohorts
        similarities = []
        for cohort in self.reference_cohorts:
            score, dimension_scores = self._compute_similarity(user_profile, cohort)
            similarities.append((cohort, score, dimension_scores))
        
        # 3. Select best match
        best_match = max(similarities, key=lambda x: x[1])
        matched_cohort, overall_score, dim_scores = best_match
        
        # 4. Determine similarity level
        sim_level = self._classify_similarity(overall_score)
        
        # 5. Suppress if similarity too low
        suppress = overall_score < self.suppression_threshold
        
        # 6. Compute percentile positions
        glucose_pct = self._compute_percentile(
            user_profile.glucose_mean, matched_cohort.glucose_percentiles
        )
        a1c_pct = self._compute_percentile(
            user_profile.a1c, matched_cohort.a1c_percentiles
        )
        bmi_pct = self._compute_percentile(
            user_profile.bmi, matched_cohort.bmi_range
        )
        
        # 7. Estimate trajectory
        expected_traj = (
            matched_cohort.glucose_trajectory_slope_mean,
            matched_cohort.glucose_trajectory_slope_std
        )
        
        traj_deviation = None
        if user_profile.glucose_trend_slope is not None:
            traj_deviation = (
                user_profile.glucose_trend_slope - matched_cohort.glucose_trajectory_slope_mean
            ) / max(matched_cohort.glucose_trajectory_slope_std, 0.1)
        
        # 8. Generate explanation
        why = self._explain_cohort_match(user_profile, matched_cohort, dim_scores)
        similarities_list = self._list_key_similarities(user_profile, matched_cohort)
        differences_list = self._list_key_differences(user_profile, matched_cohort)
        
        # 9. Compute match confidence
        match_conf = self._compute_match_confidence(overall_score, dim_scores)
        
        return CohortMatchResult(
            matched_cohort_id=matched_cohort.cohort_id,
            matched_cohort_name=matched_cohort.cohort_name,
            overall_similarity_score=overall_score,
            similarity_level=sim_level,
            dimension_scores=dim_scores,
            glucose_percentile=glucose_pct,
            a1c_percentile=a1c_pct,
            bmi_percentile=bmi_pct,
            expected_glucose_trajectory=expected_traj if not suppress else None,
            trajectory_deviation=traj_deviation,
            cohort_diabetes_prevalence=matched_cohort.diabetes_prevalence,
            cohort_cvd_prevalence=matched_cohort.cvd_prevalence,
            match_confidence=match_conf,
            suppress_cohort_claims=suppress,
            why_this_cohort=why,
            key_similarities=similarities_list,
            key_differences=differences_list
        )
    
    def estimate_trajectory_bands(
        self,
        user_profile: CohortMatchingProfile,
        cohort_match: CohortMatchResult,
        marker_id: str
    ) -> Optional[TrajectoryBand]:
        """Estimate trajectory bands for a specific marker."""
        if cohort_match.suppress_cohort_claims:
            return None
        
        # Get current value
        current = getattr(user_profile, f"{marker_id}_mean", None)
        if current is None:
            return None
        
        # Get cohort trajectory
        if cohort_match.expected_glucose_trajectory is None:
            return None
        
        mean_slope, std_slope = cohort_match.expected_glucose_trajectory
        
        # Project forward
        traj_3mo = self._project_trajectory(current, mean_slope, std_slope, months=3)
        traj_6mo = self._project_trajectory(current, mean_slope, std_slope, months=6)
        traj_12mo = self._project_trajectory(current, mean_slope, std_slope, months=12)
        
        # Interpret trajectory
        interpretation = self._interpret_trajectory(mean_slope)
        
        return TrajectoryBand(
            marker_id=marker_id,
            current_value=current,
            cohort_percentile=cohort_match.glucose_percentile or 50.0,
            trajectory_3mo=traj_3mo,
            trajectory_6mo=traj_6mo,
            trajectory_12mo=traj_12mo,
            trajectory_confidence=cohort_match.match_confidence,
            trajectory_interpretation=interpretation
        )
    
    # ===== Core Algorithm Methods =====
    
    def _extract_user_profile(
        self,
        estimates: Dict[str, Dict],
        anchors: Dict[str, any],
        history: Dict[str, List[Dict]],
        metadata: Dict[str, any]
    ) -> CohortMatchingProfile:
        """Extract user profile for cohort matching."""
        # Demographics
        age = metadata.get("age")
        sex = metadata.get("sex")
        bmi = self._compute_bmi(metadata, estimates)
        
        # Key markers (prefer measured, fallback to estimated)
        glucose_mean = self._get_marker_mean("glucose", anchors, estimates, history)
        a1c = anchors.get("a1c") or estimates.get("a1c", {}).get("estimated_value")
        cholesterol = anchors.get("total_cholesterol") or estimates.get("total_cholesterol", {}).get("estimated_value")
        hdl = anchors.get("hdl") or estimates.get("hdl", {}).get("estimated_value")
        creatinine = anchors.get("creatinine") or estimates.get("creatinine", {}).get("estimated_value")
        
        # Longitudinal trends
        glucose_trend = self._compute_trend_slope("glucose", history)
        weight_trend = self._compute_trend_slope("weight", history)
        activity_level = self._compute_activity_level(history)
        
        # Medication burden
        meds = metadata.get("medications", [])
        med_count = len(meds) if meds else 0
        takes_metformin = any("metformin" in m.lower() for m in meds) if meds else False
        takes_statins = any("statin" in m.lower() or "atorvastatin" in m.lower() for m in meds) if meds else False
        
        return CohortMatchingProfile(
            age=age,
            sex=sex,
            bmi=bmi,
            glucose_mean=glucose_mean,
            a1c=a1c,
            cholesterol_total=cholesterol,
            hdl=hdl,
            creatinine=creatinine,
            glucose_trend_slope=glucose_trend,
            weight_trend_slope=weight_trend,
            activity_level=activity_level,
            medication_count=med_count,
            takes_metformin=takes_metformin,
            takes_statins=takes_statins
        )
    
    def _compute_similarity(
        self,
        user: CohortMatchingProfile,
        cohort: CohortReference
    ) -> Tuple[float, Dict[str, float]]:
        """Compute similarity score between user and cohort."""
        dimension_scores = {}
        
        # Age similarity
        if user.age is not None:
            age_score = self._age_similarity(user.age, cohort.age_range)
        else:
            age_score = 0.0
        dimension_scores[CohortDimension.AGE.value] = age_score
        
        # Sex match
        if user.sex is not None:
            sex_score = 1.0 if user.sex == cohort.sex else 0.0
        else:
            sex_score = 0.5  # neutral
        dimension_scores[CohortDimension.SEX.value] = sex_score
        
        # BMI similarity
        if user.bmi is not None:
            bmi_score = self._range_similarity(user.bmi, cohort.bmi_range)
        else:
            bmi_score = 0.0
        dimension_scores[CohortDimension.BMI.value] = bmi_score
        
        # Key markers similarity
        marker_scores = []
        if user.glucose_mean is not None:
            marker_scores.append(self._range_similarity(user.glucose_mean, cohort.glucose_percentiles))
        if user.a1c is not None:
            marker_scores.append(self._range_similarity(user.a1c, cohort.a1c_percentiles))
        if user.cholesterol_total is not None:
            marker_scores.append(self._range_similarity(user.cholesterol_total, cohort.cholesterol_percentiles))
        
        markers_score = sum(marker_scores) / len(marker_scores) if marker_scores else 0.0
        dimension_scores[CohortDimension.KEY_MARKERS.value] = markers_score
        
        # Longitudinal trends similarity
        if user.glucose_trend_slope is not None:
            trend_score = self._trend_similarity(
                user.glucose_trend_slope,
                cohort.glucose_trajectory_slope_mean,
                cohort.glucose_trajectory_slope_std
            )
        else:
            trend_score = 0.0
        dimension_scores[CohortDimension.LONGITUDINAL_TRENDS.value] = trend_score
        
        # Medication burden (simple match)
        med_score = 0.5  # neutral for now
        dimension_scores[CohortDimension.MEDICATION_BURDEN.value] = med_score
        
        # Activity level (neutral for now - not used in current cohort matching)
        activity_score = 0.5  # neutral
        dimension_scores[CohortDimension.ACTIVITY_LEVEL.value] = activity_score
        
        # Weighted average
        overall_score = sum(
            dimension_scores[dim.value] * self.dimension_weights[dim]
            for dim in CohortDimension
        )
        
        return overall_score, dimension_scores
    
    def _age_similarity(self, user_age: float, cohort_age_range: Tuple[float, float]) -> float:
        """Compute age similarity (1.0 if within range, decay with distance)."""
        low, high = cohort_age_range
        if low <= user_age <= high:
            return 1.0
        
        # Decay with distance
        if user_age < low:
            distance = low - user_age
        else:
            distance = user_age - high
        
        # Exponential decay: e^(-distance/10)
        return math.exp(-distance / 10.0)
    
    def _range_similarity(self, value: float, cohort_range: Tuple[float, float]) -> float:
        """Compute similarity based on range overlap."""
        low, high = cohort_range
        if low <= value <= high:
            return 1.0
        
        # Distance from range
        if value < low:
            distance = low - value
            range_width = high - low
        else:
            distance = value - high
            range_width = high - low
        
        # Normalize distance
        normalized_distance = distance / max(range_width, 1.0)
        
        # Exponential decay
        return math.exp(-normalized_distance)
    
    def _trend_similarity(self, user_slope: float, cohort_mean: float, cohort_std: float) -> float:
        """Compute trend similarity using z-score."""
        z_score = abs(user_slope - cohort_mean) / max(cohort_std, 0.1)
        
        # Convert z-score to similarity (closer to 0 = higher similarity)
        # z=0 -> 1.0, z=1 -> 0.6, z=2 -> 0.14, z=3 -> 0.01
        return math.exp(-0.5 * z_score ** 2)
    
    def _classify_similarity(self, score: float) -> SimilarityLevel:
        """Classify overall similarity score."""
        if score >= 0.85:
            return SimilarityLevel.VERY_HIGH
        elif score >= 0.70:
            return SimilarityLevel.HIGH
        elif score >= 0.50:
            return SimilarityLevel.MODERATE
        elif score >= 0.30:
            return SimilarityLevel.LOW
        else:
            return SimilarityLevel.VERY_LOW
    
    def _compute_percentile(self, value: Optional[float], cohort_range: Tuple[float, float]) -> Optional[float]:
        """Estimate percentile position within cohort range."""
        if value is None:
            return None
        
        low, high = cohort_range
        if value <= low:
            return 10.0
        elif value >= high:
            return 90.0
        else:
            # Linear interpolation
            return 10.0 + 80.0 * (value - low) / (high - low)
    
    def _project_trajectory(
        self,
        current: float,
        mean_slope: float,
        std_slope: float,
        months: int
    ) -> Tuple[float, float, float]:
        """Project trajectory forward with confidence band."""
        expected = current + mean_slope * months
        lower = current + (mean_slope - std_slope) * months
        upper = current + (mean_slope + std_slope) * months
        
        return (lower, expected, upper)
    
    def _interpret_trajectory(self, slope: float) -> str:
        """Interpret trajectory slope."""
        if abs(slope) < 0.5:
            return "stable"
        elif slope > 0:
            return "worsening"
        else:
            return "improving"
    
    def _explain_cohort_match(
        self,
        user: CohortMatchingProfile,
        cohort: CohortReference,
        scores: Dict[str, float]
    ) -> str:
        """Generate explanation for cohort match."""
        # Find strongest matching dimensions
        top_dims = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:2]
        
        parts = [f"Matched based on"]
        for dim, score in top_dims:
            if score > 0.7:
                parts.append(dim.replace("_", " "))
        
        return " ".join(parts) + f" similarity to {cohort.cohort_name}."
    
    def _list_key_similarities(
        self,
        user: CohortMatchingProfile,
        cohort: CohortReference
    ) -> List[str]:
        """List key similarities."""
        similarities = []
        
        if user.age and cohort.age_range[0] <= user.age <= cohort.age_range[1]:
            similarities.append(f"Age within cohort range")
        
        if user.sex == cohort.sex:
            similarities.append(f"Same sex")
        
        if user.glucose_mean and cohort.glucose_percentiles[0] <= user.glucose_mean <= cohort.glucose_percentiles[1]:
            similarities.append(f"Glucose within typical range")
        
        return similarities[:3]
    
    def _list_key_differences(
        self,
        user: CohortMatchingProfile,
        cohort: CohortReference
    ) -> List[str]:
        """List key differences."""
        differences = []
        
        if user.age and not (cohort.age_range[0] <= user.age <= cohort.age_range[1]):
            differences.append(f"Age outside typical range")
        
        if user.glucose_mean and not (cohort.glucose_percentiles[0] <= user.glucose_mean <= cohort.glucose_percentiles[1]):
            if user.glucose_mean > cohort.glucose_percentiles[1]:
                differences.append(f"Glucose higher than cohort")
            else:
                differences.append(f"Glucose lower than cohort")
        
        return differences[:2]
    
    def _compute_match_confidence(
        self,
        overall_score: float,
        dim_scores: Dict[str, float]
    ) -> float:
        """Compute confidence in cohort match."""
        # Confidence based on overall score and consistency
        consistency = 1.0 - (max(dim_scores.values()) - min(dim_scores.values()))
        
        return (overall_score * 0.7 + consistency * 0.3)
    
    # ===== Helper Methods =====
    
    def _compute_bmi(self, metadata: Dict, estimates: Dict) -> Optional[float]:
        """Compute BMI from available data."""
        weight_kg = metadata.get("weight_kg") or estimates.get("weight", {}).get("estimated_value")
        height_m = metadata.get("height_m") or estimates.get("height", {}).get("estimated_value")
        
        if weight_kg and height_m and height_m > 0:
            return weight_kg / (height_m ** 2)
        
        return None
    
    def _get_marker_mean(
        self,
        marker: str,
        anchors: Dict,
        estimates: Dict,
        history: Dict
    ) -> Optional[float]:
        """Get marker mean from anchors or history."""
        # Prefer anchor
        if marker in anchors and anchors[marker] is not None:
            return float(anchors[marker])
        
        # Fallback to estimate
        if marker in estimates:
            return estimates[marker].get("estimated_value")
        
        # Compute from history
        if marker in history and history[marker]:
            values = [p.get("value") for p in history[marker] if p.get("value") is not None]
            if values:
                return sum(values) / len(values)
        
        return None
    
    def _compute_trend_slope(self, marker: str, history: Dict) -> Optional[float]:
        """Compute linear trend slope from history."""
        if marker not in history or len(history[marker]) < 2:
            return None
        
        points = history[marker]
        # Simple linear regression
        # For now, return None (would need full implementation)
        return None
    
    def _compute_activity_level(self, history: Dict) -> Optional[float]:
        """Compute average activity level."""
        if "steps" not in history or not history["steps"]:
            return None
        
        steps = [p.get("value") for p in history["steps"] if p.get("value") is not None]
        if steps:
            return sum(steps) / len(steps)
        
        return None
    
    def _load_reference_cohorts(self) -> List[CohortReference]:
        """Load reference cohorts (synthetic data for now)."""
        return [
            CohortReference(
                cohort_id="healthy_young_adult",
                cohort_name="Healthy Young Adult",
                age_range=(18, 35),
                sex="mixed",
                bmi_range=(18.5, 25.0),
                glucose_percentiles=(70, 100),
                a1c_percentiles=(4.5, 5.6),
                cholesterol_percentiles=(150, 200),
                glucose_trajectory_slope_mean=0.1,
                glucose_trajectory_slope_std=0.5,
                n_members=1000,
                diabetes_prevalence=0.02,
                cvd_prevalence=0.01
            ),
            CohortReference(
                cohort_id="prediabetic_middle_age",
                cohort_name="Prediabetic Middle Age",
                age_range=(35, 55),
                sex="mixed",
                bmi_range=(25.0, 30.0),
                glucose_percentiles=(100, 125),
                a1c_percentiles=(5.7, 6.4),
                cholesterol_percentiles=(180, 240),
                glucose_trajectory_slope_mean=0.5,
                glucose_trajectory_slope_std=1.0,
                n_members=500,
                diabetes_prevalence=0.30,
                cvd_prevalence=0.15
            ),
            CohortReference(
                cohort_id="type2_diabetes_older",
                cohort_name="Type 2 Diabetes Older Adult",
                age_range=(55, 75),
                sex="mixed",
                bmi_range=(28.0, 35.0),
                glucose_percentiles=(126, 180),
                a1c_percentiles=(6.5, 8.0),
                cholesterol_percentiles=(200, 260),
                glucose_trajectory_slope_mean=1.0,
                glucose_trajectory_slope_std=2.0,
                n_members=300,
                diabetes_prevalence=1.0,
                cvd_prevalence=0.40
            ),
            CohortReference(
                cohort_id="athletic_fitness",
                cohort_name="Athletic/High Fitness",
                age_range=(25, 45),
                sex="mixed",
                bmi_range=(20.0, 26.0),
                glucose_percentiles=(65, 95),
                a1c_percentiles=(4.2, 5.4),
                cholesterol_percentiles=(140, 190),
                glucose_trajectory_slope_mean=-0.2,
                glucose_trajectory_slope_std=0.3,
                n_members=200,
                diabetes_prevalence=0.01,
                cvd_prevalence=0.005
            )
        ]


# ===== Singleton =====

_cohort_engine_instance = None

def get_cohort_matching_engine() -> CohortMatchingEngine:
    """Get singleton instance of cohort matching engine."""
    global _cohort_engine_instance
    if _cohort_engine_instance is None:
        _cohort_engine_instance = CohortMatchingEngine()
    return _cohort_engine_instance
