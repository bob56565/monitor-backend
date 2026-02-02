"""
Uncertainty Reduction Planner (Phase 3 A2.1)

Computes which next measurements would maximally reduce uncertainty across
the greatest number of outputs. Uses information gain estimation to prioritize
measurements based on their impact on downstream inference quality.

Key Features:
- Information gain estimation per candidate measurement
- Multi-output uncertainty reduction scoring
- Top-3 recommended measurements with explanations
- Conditional recommendations based on data quality and anchor strength
- Never requires action, only recommends

Design Principles:
- Maximum entropy reduction, not data volume
- Consider ALL downstream outputs affected
- Explainable recommendations (which outputs tighten and why)
- Respects current anchor strength and data quality
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple
import math
from collections import defaultdict


class MeasurementType(str, Enum):
    """Type of measurement that can be recommended."""
    LAB_PANEL = "lab_panel"
    SINGLE_BIOMARKER = "single_biomarker"
    WEARABLE_STREAM = "wearable_stream"
    VITAL_SIGN = "vital_sign"
    SPECIMEN = "specimen"


class UncertaintySource(str, Enum):
    """Source of uncertainty in current estimates."""
    INSUFFICIENT_DATA = "insufficient_data"
    WEAK_ANCHORS = "weak_anchors"
    SOLVER_DISAGREEMENT = "solver_disagreement"
    TEMPORAL_GAP = "temporal_gap"
    CONSTRAINT_CONFLICT = "constraint_conflict"
    MISSING_KEY_INPUT = "missing_key_input"


@dataclass
class MeasurementCandidate:
    """Candidate measurement that could reduce uncertainty."""
    measurement_id: str
    measurement_name: str
    measurement_type: MeasurementType
    
    # Direct biomarkers this measurement provides
    direct_biomarkers: List[str]
    
    # Indirect outputs affected via constraints/correlations
    indirect_outputs: List[str]
    
    # Current availability
    last_measured: Optional[datetime]
    days_since_last: Optional[float]
    
    # Cost/burden estimates (relative)
    relative_cost: float  # 0.0 (free/already streaming) to 1.0 (expensive panel)
    patient_burden: float  # 0.0 (no burden) to 1.0 (invasive)


@dataclass
class UncertaintyProfile:
    """Current uncertainty profile for an output."""
    output_id: str
    current_confidence: float
    current_range_width_percent: float
    
    # Uncertainty sources ranked by impact
    primary_uncertainty_source: UncertaintySource
    secondary_uncertainty_sources: List[UncertaintySource]
    
    # Anchor strength
    anchor_strength: str  # NONE, WEAK, MODERATE, STRONG
    
    # Missing key inputs
    missing_anchors: List[str]
    
    # Temporal staleness
    days_since_anchor: Optional[float]


@dataclass
class InformationGainEstimate:
    """Estimated information gain from a candidate measurement."""
    measurement_id: str
    measurement_name: str
    
    # Affected outputs
    directly_affected_outputs: List[str]
    indirectly_affected_outputs: List[str]
    total_outputs_affected: int
    
    # Uncertainty reduction estimates
    expected_confidence_increase: Dict[str, float]  # output_id -> delta_confidence
    expected_range_tightening: Dict[str, float]  # output_id -> percent_reduction
    
    # Aggregate scores
    aggregate_uncertainty_reduction: float  # 0.0 to 1.0
    weighted_impact_score: float  # considers importance + number of outputs
    
    # Cost-benefit
    relative_cost: float
    cost_adjusted_score: float  # impact / cost
    
    # Explanation
    why_this_helps: str
    which_outputs_improve_most: List[Tuple[str, float]]  # (output_id, reduction)


@dataclass
class UncertaintyReductionRecommendation:
    """Top recommendation for reducing uncertainty."""
    rank: int  # 1, 2, or 3
    measurement_id: str
    measurement_name: str
    measurement_type: MeasurementType
    
    # Impact summary
    outputs_affected: List[str]
    expected_uncertainty_reduction_percent: float
    
    # Explanation
    reason_for_recommendation: str
    affected_outputs_detail: List[Dict[str, any]]  # output + expected improvement
    
    # Timing
    urgency_level: str  # LOW, MODERATE, HIGH
    recommended_timeframe: str  # e.g., "within 1 week", "within 1 month"
    
    # Optional context
    last_measured: Optional[datetime]
    days_since_last: Optional[float]


class UncertaintyReductionPlanner:
    """
    Planner that recommends next measurements to maximally reduce uncertainty.
    
    Algorithm:
    1. Analyze current uncertainty profile for all outputs
    2. Generate candidate measurements
    3. Estimate information gain for each candidate
    4. Rank by cost-adjusted impact
    5. Return top 3 recommendations with explanations
    """
    
    def __init__(self):
        # Measurement impact graph: measurement -> outputs affected
        self.measurement_impact_graph = self._build_measurement_impact_graph()
        
        # Output importance weights
        self.output_importance = self._initialize_output_importance()
        
        # Constraint graph for indirect effects
        self.constraint_graph = self._build_constraint_dependencies()
    
    def plan_uncertainty_reduction(
        self,
        current_estimates: Dict[str, Dict],
        measured_anchors: Dict[str, any],
        historical_data: Dict[str, List[Dict]],
        metadata: Dict[str, any]
    ) -> Dict[str, any]:
        """
        Main planning method: analyze current state and recommend measurements.
        
        Returns:
        {
            "uncertainty_profiles": {...},
            "candidate_measurements": [...],
            "information_gain_estimates": [...],
            "top_recommendations": [...],
            "overall_uncertainty_score": float
        }
        """
        # 1. Build uncertainty profiles for all outputs
        uncertainty_profiles = self._analyze_uncertainty_profiles(
            current_estimates, measured_anchors, historical_data, metadata
        )
        
        # 2. Generate candidate measurements
        candidates = self._generate_measurement_candidates(
            uncertainty_profiles, measured_anchors, historical_data
        )
        
        # 3. Estimate information gain for each candidate
        info_gain_estimates = []
        for candidate in candidates:
            estimate = self._estimate_information_gain(
                candidate, uncertainty_profiles, current_estimates
            )
            info_gain_estimates.append(estimate)
        
        # 4. Rank and select top 3
        ranked = sorted(
            info_gain_estimates,
            key=lambda x: x.cost_adjusted_score,
            reverse=True
        )
        
        top_3 = self._format_top_recommendations(ranked[:3])
        
        # 5. Compute overall uncertainty score
        overall_score = self._compute_overall_uncertainty(uncertainty_profiles)
        
        return {
            "uncertainty_profiles": {
                p.output_id: {
                    "confidence": p.current_confidence,
                    "range_width_percent": p.current_range_width_percent,
                    "primary_source": p.primary_uncertainty_source.value,
                    "anchor_strength": p.anchor_strength,
                    "missing_anchors": p.missing_anchors
                }
                for p in uncertainty_profiles.values()
            },
            "candidate_measurements": [
                {
                    "measurement_id": c.measurement_id,
                    "measurement_name": c.measurement_name,
                    "type": c.measurement_type.value,
                    "direct_biomarkers": c.direct_biomarkers,
                    "days_since_last": c.days_since_last
                }
                for c in candidates
            ],
            "information_gain_estimates": [
                {
                    "measurement": e.measurement_name,
                    "outputs_affected": e.total_outputs_affected,
                    "uncertainty_reduction": e.aggregate_uncertainty_reduction,
                    "impact_score": e.weighted_impact_score,
                    "cost_adjusted_score": e.cost_adjusted_score
                }
                for e in ranked
            ],
            "top_recommendations": [
                {
                    "rank": r.rank,
                    "measurement": r.measurement_name,
                    "type": r.measurement_type.value,
                    "outputs_affected": r.outputs_affected,
                    "expected_reduction_percent": r.expected_uncertainty_reduction_percent,
                    "reason": r.reason_for_recommendation,
                    "urgency": r.urgency_level,
                    "timeframe": r.recommended_timeframe,
                    "days_since_last": r.days_since_last
                }
                for r in top_3
            ],
            "overall_uncertainty_score": overall_score
        }
    
    def _analyze_uncertainty_profiles(
        self,
        estimates: Dict[str, Dict],
        anchors: Dict[str, any],
        history: Dict[str, List[Dict]],
        metadata: Dict[str, any]
    ) -> Dict[str, UncertaintyProfile]:
        """Analyze current uncertainty for each output."""
        profiles = {}
        
        for output_id, estimate in estimates.items():
            confidence = estimate.get("confidence", 0.5)
            range_width = self._compute_range_width_percent(estimate)
            
            # Identify uncertainty sources
            sources = self._identify_uncertainty_sources(
                output_id, estimate, anchors, history, metadata
            )
            
            # Get anchor strength
            anchor_strength = estimate.get("anchor_strength", "NONE")
            
            # Find missing key anchors
            missing = self._find_missing_anchors(output_id, anchors)
            
            # Temporal staleness
            days_since = self._days_since_last_anchor(output_id, anchors, history)
            
            profiles[output_id] = UncertaintyProfile(
                output_id=output_id,
                current_confidence=confidence,
                current_range_width_percent=range_width,
                primary_uncertainty_source=sources[0] if sources else UncertaintySource.INSUFFICIENT_DATA,
                secondary_uncertainty_sources=sources[1:],
                anchor_strength=anchor_strength,
                missing_anchors=missing,
                days_since_anchor=days_since
            )
        
        return profiles
    
    def _generate_measurement_candidates(
        self,
        profiles: Dict[str, UncertaintyProfile],
        anchors: Dict[str, any],
        history: Dict[str, List[Dict]]
    ) -> List[MeasurementCandidate]:
        """Generate candidate measurements based on uncertainty profiles."""
        candidates = []
        
        # Standard lab panels
        candidates.append(MeasurementCandidate(
            measurement_id="lipid_panel",
            measurement_name="Lipid Panel",
            measurement_type=MeasurementType.LAB_PANEL,
            direct_biomarkers=["total_cholesterol", "hdl", "ldl", "triglycerides"],
            indirect_outputs=["cardiovascular_risk", "metabolic_health"],
            last_measured=self._get_last_measured("lipid_panel", history),
            days_since_last=self._days_since_last("lipid_panel", history),
            relative_cost=0.3,
            patient_burden=0.2
        ))
        
        candidates.append(MeasurementCandidate(
            measurement_id="metabolic_panel",
            measurement_name="Comprehensive Metabolic Panel",
            measurement_type=MeasurementType.LAB_PANEL,
            direct_biomarkers=["glucose", "a1c", "creatinine", "egfr", "electrolytes"],
            indirect_outputs=["kidney_function", "diabetes_risk", "metabolic_health"],
            last_measured=self._get_last_measured("metabolic_panel", history),
            days_since_last=self._days_since_last("metabolic_panel", history),
            relative_cost=0.4,
            patient_burden=0.2
        ))
        
        candidates.append(MeasurementCandidate(
            measurement_id="vitamin_d",
            measurement_name="Vitamin D (25-OH)",
            measurement_type=MeasurementType.SINGLE_BIOMARKER,
            direct_biomarkers=["vitamin_d_25oh"],
            indirect_outputs=["bone_health", "immune_function"],
            last_measured=self._get_last_measured("vitamin_d", history),
            days_since_last=self._days_since_last("vitamin_d", history),
            relative_cost=0.2,
            patient_burden=0.1
        ))
        
        candidates.append(MeasurementCandidate(
            measurement_id="iron_panel",
            measurement_name="Iron Panel",
            measurement_type=MeasurementType.LAB_PANEL,
            direct_biomarkers=["iron", "ferritin", "transferrin_saturation"],
            indirect_outputs=["anemia_risk", "inflammation"],
            last_measured=self._get_last_measured("iron_panel", history),
            days_since_last=self._days_since_last("iron_panel", history),
            relative_cost=0.3,
            patient_burden=0.2
        ))
        
        # Wearable streams (if not active)
        if not self._has_recent_data("glucose", history, days=7):
            candidates.append(MeasurementCandidate(
                measurement_id="cgm_stream",
                measurement_name="Continuous Glucose Monitor",
                measurement_type=MeasurementType.WEARABLE_STREAM,
                direct_biomarkers=["glucose_isf"],
                indirect_outputs=["diabetes_risk", "metabolic_health", "glucose_variability"],
                last_measured=self._get_last_measured("glucose", history),
                days_since_last=self._days_since_last("glucose", history),
                relative_cost=0.5,
                patient_burden=0.3
            ))
        
        return candidates
    
    def _estimate_information_gain(
        self,
        candidate: MeasurementCandidate,
        profiles: Dict[str, UncertaintyProfile],
        estimates: Dict[str, Dict]
    ) -> InformationGainEstimate:
        """Estimate information gain from a candidate measurement."""
        directly_affected = []
        indirectly_affected = []
        confidence_deltas = {}
        range_reductions = {}
        
        # Direct effects
        for biomarker in candidate.direct_biomarkers:
            if biomarker in profiles:
                directly_affected.append(biomarker)
                # Estimate confidence increase
                current_conf = profiles[biomarker].current_confidence
                delta_conf = self._estimate_confidence_delta(
                    profiles[biomarker], candidate
                )
                confidence_deltas[biomarker] = delta_conf
                
                # Estimate range tightening
                range_reduction = self._estimate_range_tightening(
                    profiles[biomarker], candidate
                )
                range_reductions[biomarker] = range_reduction
        
        # Indirect effects via constraints
        for output_id in candidate.indirect_outputs:
            if output_id in profiles:
                indirectly_affected.append(output_id)
                delta_conf = self._estimate_confidence_delta(
                    profiles[output_id], candidate, indirect=True
                )
                confidence_deltas[output_id] = delta_conf
                range_reductions[output_id] = delta_conf * 0.5  # indirect effect smaller
        
        # Aggregate scores
        total_affected = len(directly_affected) + len(indirectly_affected)
        avg_reduction = sum(range_reductions.values()) / max(len(range_reductions), 1)
        
        # Weight by output importance
        weighted_impact = sum(
            range_reductions.get(out, 0) * self.output_importance.get(out, 1.0)
            for out in range_reductions.keys()
        )
        
        # Cost-adjusted score
        cost_adjusted = weighted_impact / max(candidate.relative_cost, 0.1)
        
        # Explanation
        top_outputs = sorted(
            range_reductions.items(),
            key=lambda x: x[1],
            reverse=True
        )[:3]
        
        why = self._generate_recommendation_explanation(
            candidate, directly_affected, indirectly_affected, top_outputs
        )
        
        return InformationGainEstimate(
            measurement_id=candidate.measurement_id,
            measurement_name=candidate.measurement_name,
            directly_affected_outputs=directly_affected,
            indirectly_affected_outputs=indirectly_affected,
            total_outputs_affected=total_affected,
            expected_confidence_increase=confidence_deltas,
            expected_range_tightening=range_reductions,
            aggregate_uncertainty_reduction=avg_reduction,
            weighted_impact_score=weighted_impact,
            relative_cost=candidate.relative_cost,
            cost_adjusted_score=cost_adjusted,
            why_this_helps=why,
            which_outputs_improve_most=top_outputs
        )
    
    def _format_top_recommendations(
        self,
        top_estimates: List[InformationGainEstimate]
    ) -> List[UncertaintyReductionRecommendation]:
        """Format top 3 estimates as recommendations."""
        recommendations = []
        
        for rank, estimate in enumerate(top_estimates, 1):
            # Determine urgency based on uncertainty level
            urgency = self._determine_urgency(estimate)
            timeframe = self._recommend_timeframe(estimate)
            
            # Get measurement type (lookup from candidates)
            meas_type = MeasurementType.LAB_PANEL  # default
            
            # Format affected outputs detail
            affected_detail = [
                {
                    "output_id": output_id,
                    "expected_improvement_percent": reduction * 100
                }
                for output_id, reduction in estimate.which_outputs_improve_most
            ]
            
            recommendations.append(UncertaintyReductionRecommendation(
                rank=rank,
                measurement_id=estimate.measurement_id,
                measurement_name=estimate.measurement_name,
                measurement_type=meas_type,
                outputs_affected=estimate.directly_affected_outputs + estimate.indirectly_affected_outputs,
                expected_uncertainty_reduction_percent=estimate.aggregate_uncertainty_reduction * 100,
                reason_for_recommendation=estimate.why_this_helps,
                affected_outputs_detail=affected_detail,
                urgency_level=urgency,
                recommended_timeframe=timeframe,
                last_measured=None,
                days_since_last=None
            ))
        
        return recommendations
    
    # ===== Helper Methods =====
    
    def _build_measurement_impact_graph(self) -> Dict[str, List[str]]:
        """Build graph of measurements -> outputs affected."""
        return {
            "lipid_panel": ["total_cholesterol", "hdl", "ldl", "triglycerides", "cardiovascular_risk"],
            "metabolic_panel": ["glucose", "a1c", "creatinine", "egfr", "diabetes_risk", "kidney_function"],
            "vitamin_d": ["vitamin_d_25oh", "bone_health"],
            "iron_panel": ["iron", "ferritin", "anemia_risk"],
            "cgm_stream": ["glucose", "glucose_variability", "diabetes_risk"]
        }
    
    def _initialize_output_importance(self) -> Dict[str, float]:
        """Initialize importance weights for outputs."""
        return {
            "glucose": 1.5,
            "a1c": 1.5,
            "egfr": 1.5,
            "cardiovascular_risk": 1.3,
            "diabetes_risk": 1.3,
            "kidney_function": 1.3,
            "vitamin_d_25oh": 1.0,
            "iron": 1.0,
            "default": 1.0
        }
    
    def _build_constraint_dependencies(self) -> Dict[str, List[str]]:
        """Build constraint dependency graph."""
        return {
            "glucose": ["a1c", "diabetes_risk", "metabolic_health"],
            "a1c": ["glucose", "diabetes_risk"],
            "creatinine": ["egfr", "kidney_function"],
            "hdl": ["cardiovascular_risk", "metabolic_health"],
            "triglycerides": ["cardiovascular_risk", "metabolic_health"]
        }
    
    def _compute_range_width_percent(self, estimate: Dict) -> float:
        """Compute range width as percentage of midpoint."""
        low = estimate.get("estimated_value_low", 0)
        high = estimate.get("estimated_value_high", 100)
        midpoint = (low + high) / 2
        if midpoint == 0:
            return 100.0
        return ((high - low) / midpoint) * 100
    
    def _identify_uncertainty_sources(
        self,
        output_id: str,
        estimate: Dict,
        anchors: Dict,
        history: Dict,
        metadata: Dict
    ) -> List[UncertaintySource]:
        """Identify primary sources of uncertainty for an output."""
        sources = []
        
        confidence = estimate.get("confidence", 0.5)
        anchor_strength = estimate.get("anchor_strength", "NONE")
        
        # Check various sources
        if confidence < 0.4:
            sources.append(UncertaintySource.INSUFFICIENT_DATA)
        
        if anchor_strength in ["NONE", "WEAK"]:
            sources.append(UncertaintySource.WEAK_ANCHORS)
        
        if metadata.get("solver_agreement_low", False):
            sources.append(UncertaintySource.SOLVER_DISAGREEMENT)
        
        if self._has_temporal_gap(output_id, history):
            sources.append(UncertaintySource.TEMPORAL_GAP)
        
        if metadata.get("constraint_conflicts", 0) > 0:
            sources.append(UncertaintySource.CONSTRAINT_CONFLICT)
        
        return sources if sources else [UncertaintySource.INSUFFICIENT_DATA]
    
    def _find_missing_anchors(self, output_id: str, anchors: Dict) -> List[str]:
        """Find missing key anchors for an output."""
        # Mapping of outputs to their key anchors
        anchor_map = {
            "glucose": ["glucose_isf", "glucose_serum", "a1c"],
            "a1c": ["a1c", "glucose"],
            "vitamin_d_25oh": ["vitamin_d_25oh"],
            "iron": ["iron", "ferritin"],
            "egfr": ["creatinine", "egfr"]
        }
        
        required = anchor_map.get(output_id, [])
        missing = [a for a in required if a not in anchors or anchors[a] is None]
        return missing
    
    def _days_since_last_anchor(
        self,
        output_id: str,
        anchors: Dict,
        history: Dict
    ) -> Optional[float]:
        """Compute days since last anchor measurement."""
        # Simplified: return None if no history
        if output_id not in history or not history[output_id]:
            return None
        
        last_point = history[output_id][-1]
        if "timestamp" in last_point:
            ts = last_point["timestamp"]
            if isinstance(ts, datetime):
                delta = datetime.now() - ts
                return delta.total_seconds() / 86400
        
        return None
    
    def _get_last_measured(self, measurement_id: str, history: Dict) -> Optional[datetime]:
        """Get last measurement timestamp."""
        # Simplified lookup
        return None
    
    def _days_since_last(self, measurement_id: str, history: Dict) -> Optional[float]:
        """Compute days since last measurement."""
        return None
    
    def _has_recent_data(self, stream: str, history: Dict, days: int) -> bool:
        """Check if stream has recent data within N days."""
        if stream not in history or not history[stream]:
            return False
        
        last = history[stream][-1]
        if "timestamp" in last:
            ts = last["timestamp"]
            if isinstance(ts, datetime):
                delta = datetime.now() - ts
                return delta.days <= days
        
        return False
    
    def _estimate_confidence_delta(
        self,
        profile: UncertaintyProfile,
        candidate: MeasurementCandidate,
        indirect: bool = False
    ) -> float:
        """Estimate confidence increase from measurement."""
        current = profile.current_confidence
        
        # Direct measurement
        if not indirect:
            if profile.anchor_strength == "NONE":
                return min(0.4, 1.0 - current)  # Large gain
            elif profile.anchor_strength == "WEAK":
                return min(0.25, 1.0 - current)
            else:
                return min(0.15, 1.0 - current)
        else:
            # Indirect effect smaller
            return min(0.1, 1.0 - current)
    
    def _estimate_range_tightening(
        self,
        profile: UncertaintyProfile,
        candidate: MeasurementCandidate
    ) -> float:
        """Estimate range tightening percentage (0-1)."""
        current_width = profile.current_range_width_percent
        
        # Tightening depends on anchor strength
        if profile.anchor_strength == "NONE":
            return 0.5  # Can tighten by 50%
        elif profile.anchor_strength == "WEAK":
            return 0.3
        elif profile.anchor_strength == "MODERATE":
            return 0.2
        else:
            return 0.1  # Already tight
    
    def _has_temporal_gap(self, output_id: str, history: Dict) -> bool:
        """Check if there's a significant temporal gap."""
        if output_id not in history or len(history[output_id]) < 2:
            return True
        
        # Check last measurement recency
        last = history[output_id][-1]
        if "timestamp" in last:
            ts = last["timestamp"]
            if isinstance(ts, datetime):
                delta = datetime.now() - ts
                return delta.days > 30  # Gap > 30 days
        
        return False
    
    def _generate_recommendation_explanation(
        self,
        candidate: MeasurementCandidate,
        direct: List[str],
        indirect: List[str],
        top_outputs: List[Tuple[str, float]]
    ) -> str:
        """Generate human-readable explanation."""
        parts = []
        
        if direct:
            parts.append(f"Directly measures {', '.join(direct[:2])}")
        
        if indirect:
            parts.append(f"improves estimates for {', '.join(indirect[:2])}")
        
        if top_outputs:
            best = top_outputs[0]
            parts.append(f"(greatest impact on {best[0]})")
        
        return "; ".join(parts) + "."
    
    def _determine_urgency(self, estimate: InformationGainEstimate) -> str:
        """Determine urgency level."""
        if estimate.aggregate_uncertainty_reduction > 0.5:
            return "HIGH"
        elif estimate.aggregate_uncertainty_reduction > 0.3:
            return "MODERATE"
        else:
            return "LOW"
    
    def _recommend_timeframe(self, estimate: InformationGainEstimate) -> str:
        """Recommend timeframe for measurement."""
        if estimate.aggregate_uncertainty_reduction > 0.5:
            return "within 1-2 weeks"
        elif estimate.aggregate_uncertainty_reduction > 0.3:
            return "within 1 month"
        else:
            return "at next routine visit"
    
    def _compute_overall_uncertainty(
        self,
        profiles: Dict[str, UncertaintyProfile]
    ) -> float:
        """Compute overall uncertainty score (0-1, higher = more uncertain)."""
        if not profiles:
            return 1.0
        
        # Average of (1 - confidence) across all outputs
        uncertainties = [1.0 - p.current_confidence for p in profiles.values()]
        return sum(uncertainties) / len(uncertainties)


# ===== Singleton =====

_planner_instance = None

def get_uncertainty_reduction_planner() -> UncertaintyReductionPlanner:
    """Get singleton instance of uncertainty reduction planner."""
    global _planner_instance
    if _planner_instance is None:
        _planner_instance = UncertaintyReductionPlanner()
    return _planner_instance
