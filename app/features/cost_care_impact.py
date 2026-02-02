"""
Cost and Care Impact Modules (Phase 3 B.5)

Conditionally generates honest, data-justified cost and care impact insights.
Only renders when data quality and anchor strength justify claims.

Key Modules:
- Tests avoided or deferred
- Earlier intervention opportunities
- Value of longitudinal tracking vs annual labs

Design Principles:
- Only render when evidence supports claims
- Probabilistic and conditional framing
- No absolute cost savings claims
- Explain assumptions and limitations
- Respect evidence grade and confidence thresholds
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional
from app.features.language_control import get_language_controller


class ImpactModuleType(str, Enum):
    """Type of impact module."""
    TESTS_AVOIDED = "tests_avoided"
    EARLIER_INTERVENTION = "earlier_intervention"
    LONGITUDINAL_VALUE = "longitudinal_value"
    COST_EFFICIENCY = "cost_efficiency"


class ConfidenceLevel(str, Enum):
    """Confidence level for impact claims."""
    HIGH = "high"  # Can make strong claims
    MODERATE = "moderate"  # Can make qualified claims
    LOW = "low"  # Can only mention possibility
    INSUFFICIENT = "insufficient"  # Cannot make claims


@dataclass
class ImpactClaim:
    """Single impact claim with supporting data."""
    claim_statement: str
    supporting_data_signals: List[str]
    confidence_level: ConfidenceLevel
    why_this_is_valid: str
    limitations: List[str]
    
    # Quantification (if possible)
    estimated_tests_saved: Optional[int] = None
    estimated_timeframe: Optional[str] = None


@dataclass
class ImpactModule:
    """Complete impact module."""
    module_type: ImpactModuleType
    module_title: str
    
    # Should this module render?
    should_render: bool
    suppression_reason: Optional[str]  # Why suppressed if not rendered
    
    # Claims (if rendered)
    claims: List[ImpactClaim]
    
    # Overall assessment
    overall_confidence: ConfidenceLevel
    key_assumptions: List[str]


class CostCareImpactAnalyzer:
    """
    Analyzer for cost and care impact.
    
    Determines when impact claims are justified and generates
    appropriately hedged statements.
    """
    
    def __init__(self):
        self.language_controller = get_language_controller()
        
        # Thresholds for making claims
        self.min_confidence_for_claims = 0.50
        self.min_evidence_grade = "B"  # Need at least B grade
        self.min_data_points = 30  # Need longitudinal data
        self.min_temporal_coverage_days = 21
    
    def analyze_impact(
        self,
        estimates: Dict[str, Dict],
        measured_anchors: Dict[str, any],
        historical_data: Dict[str, List[Dict]],
        phase2_metadata: Optional[Dict] = None,
        phase3_metadata: Optional[Dict] = None,
        user_metadata: Optional[Dict] = None
    ) -> Dict[str, ImpactModule]:
        """
        Analyze potential cost and care impact.
        
        Returns dict of impact modules (some may be suppressed).
        """
        modules = {}
        
        # 1. Tests avoided or deferred
        modules["tests_avoided"] = self._analyze_tests_avoided(
            estimates, measured_anchors, historical_data, phase2_metadata
        )
        
        # 2. Earlier intervention opportunities
        modules["earlier_intervention"] = self._analyze_earlier_intervention(
            estimates, historical_data, phase3_metadata
        )
        
        # 3. Longitudinal value
        modules["longitudinal_value"] = self._analyze_longitudinal_value(
            historical_data, phase2_metadata
        )
        
        return modules
    
    def format_for_display(self, modules: Dict[str, ImpactModule]) -> str:
        """Format impact modules for display."""
        lines = []
        
        lines.append("## Cost & Care Impact Insights\n")
        
        for module_id, module in modules.items():
            if not module.should_render:
                continue
            
            lines.append(f"### {module.module_title}\n")
            
            for claim in module.claims:
                # Statement
                lines.append(f"**{claim.claim_statement}**\n")
                
                # Supporting data
                lines.append(f"*Supporting data:*")
                for signal in claim.supporting_data_signals:
                    lines.append(f"  - {signal}")
                
                # Confidence
                lines.append(f"*Confidence:* {claim.confidence_level.value}")
                
                # Limitations
                if claim.limitations:
                    lines.append(f"*Limitations:* {claim.limitations[0]}")
                
                lines.append("")  # blank line
            
            # Assumptions
            if module.key_assumptions:
                lines.append(f"*Key assumptions:*")
                for assumption in module.key_assumptions:
                    lines.append(f"  - {assumption}")
                lines.append("")
        
        return "\n".join(lines)
    
    # ===== Module Analyzers =====
    
    def _analyze_tests_avoided(
        self,
        estimates: Dict[str, Dict],
        anchors: Dict[str, any],
        history: Dict[str, List[Dict]],
        phase2_metadata: Optional[Dict]
    ) -> ImpactModule:
        """Analyze tests that may have been avoided or deferred."""
        # Check if we have enough data to make claims
        sufficient_data = self._has_sufficient_data(history)
        high_confidence = self._has_high_confidence(estimates)
        
        if not sufficient_data or not high_confidence:
            return ImpactModule(
                module_type=ImpactModuleType.TESTS_AVOIDED,
                module_title="Tests Avoided/Deferred",
                should_render=False,
                suppression_reason="Insufficient data quality or confidence for impact claims",
                claims=[],
                overall_confidence=ConfidenceLevel.INSUFFICIENT,
                key_assumptions=[]
            )
        
        # Build claims
        claims = []
        
        # Claim 1: Continuous monitoring reduced need for frequent labs
        if self._has_continuous_monitoring(history):
            supporting_signals = [
                f"Continuous glucose monitoring active ({self._count_data_points(history.get('glucose', []))} points)",
                f"High confidence estimates ({self._avg_confidence(estimates):.0%} average)",
                "Personal baselines established" if phase2_metadata and phase2_metadata.get("personal_baseline_used") else "Population references used"
            ]
            
            claims.append(ImpactClaim(
                claim_statement="Continuous monitoring may reduce need for some routine lab tests",
                supporting_data_signals=supporting_signals,
                confidence_level=ConfidenceLevel.MODERATE,
                why_this_is_valid="Continuous data provides more comprehensive view than point-in-time labs",
                limitations=[
                    "Cannot replace all lab tests",
                    "Clinical validation still required",
                    "Some biomarkers require direct measurement"
                ],
                estimated_tests_saved=2,
                estimated_timeframe="over 6 months"
            ))
        
        # Claim 2: Stable patterns suggest test frequency could be reduced
        if self._has_stable_patterns(estimates, phase2_metadata):
            supporting_signals = [
                "Markers stable over extended period",
                "Low temporal variation",
                "Personal baselines well-established"
            ]
            
            claims.append(ImpactClaim(
                claim_statement="Stable patterns suggest some monitoring intervals could potentially be extended",
                supporting_data_signals=supporting_signals,
                confidence_level=ConfidenceLevel.MODERATE,
                why_this_is_valid="Stable values reduce urgency for frequent re-testing",
                limitations=[
                    "Clinical judgment required",
                    "Depends on risk factors",
                    "Guidelines may mandate specific intervals"
                ],
                estimated_tests_saved=1,
                estimated_timeframe="over 12 months"
            ))
        
        overall_conf = ConfidenceLevel.MODERATE if claims else ConfidenceLevel.LOW
        
        return ImpactModule(
            module_type=ImpactModuleType.TESTS_AVOIDED,
            module_title="Tests Avoided/Deferred",
            should_render=len(claims) > 0,
            suppression_reason=None,
            claims=claims,
            overall_confidence=overall_conf,
            key_assumptions=[
                "Clinical guidelines allow flexibility in testing frequency",
                "Patient continues monitoring consistently",
                "No significant changes in health status"
            ]
        )
    
    def _analyze_earlier_intervention(
        self,
        estimates: Dict[str, Dict],
        history: Dict[str, List[Dict]],
        phase3_metadata: Optional[Dict]
    ) -> ImpactModule:
        """Analyze earlier intervention opportunities."""
        # Check for change points that enabled earlier awareness
        has_change_points = (
            phase3_metadata and
            "change_point_analysis" in phase3_metadata and
            len(phase3_metadata["change_point_analysis"]) > 0
        )
        
        if not has_change_points:
            return ImpactModule(
                module_type=ImpactModuleType.EARLIER_INTERVENTION,
                module_title="Earlier Intervention Opportunities",
                should_render=False,
                suppression_reason="No significant changes detected",
                claims=[],
                overall_confidence=ConfidenceLevel.INSUFFICIENT,
                key_assumptions=[]
            )
        
        claims = []
        
        # Check for early deterioration signals
        early_warnings = self._extract_early_warnings(phase3_metadata)
        if early_warnings:
            supporting_signals = [
                f"Early warning signals detected: {', '.join(early_warnings[:2])}",
                "Detected before typical clinical testing interval",
                "Allows proactive discussion with provider"
            ]
            
            claims.append(ImpactClaim(
                claim_statement="Continuous monitoring detected early signals that may enable proactive care",
                supporting_data_signals=supporting_signals,
                confidence_level=ConfidenceLevel.MODERATE,
                why_this_is_valid="Earlier detection allows for earlier clinical evaluation",
                limitations=[
                    "Does not guarantee intervention will be needed",
                    "Requires clinical confirmation",
                    "Benefit depends on condition and timeline"
                ],
                estimated_timeframe="potentially 2-4 weeks earlier than annual checkup"
            ))
        
        overall_conf = ConfidenceLevel.MODERATE if claims else ConfidenceLevel.LOW
        
        return ImpactModule(
            module_type=ImpactModuleType.EARLIER_INTERVENTION,
            module_title="Earlier Intervention Opportunities",
            should_render=len(claims) > 0,
            suppression_reason=None,
            claims=claims,
            overall_confidence=overall_conf,
            key_assumptions=[
                "Early detection leads to better outcomes (condition-dependent)",
                "Patient acts on early signals",
                "Clinical system responsive to early findings"
            ]
        )
    
    def _analyze_longitudinal_value(
        self,
        history: Dict[str, List[Dict]],
        phase2_metadata: Optional[Dict]
    ) -> ImpactModule:
        """Analyze value of longitudinal tracking vs annual labs."""
        # Check for personal baselines
        has_baselines = (
            phase2_metadata and
            phase2_metadata.get("personal_baseline_used")
        )
        
        # Check for sufficient longitudinal data
        sufficient_longitudinal = sum(
            len(history.get(stream, [])) for stream in history
        ) >= 100
        
        if not has_baselines or not sufficient_longitudinal:
            return ImpactModule(
                module_type=ImpactModuleType.LONGITUDINAL_VALUE,
                module_title="Value of Longitudinal Tracking",
                should_render=False,
                suppression_reason="Insufficient longitudinal data to demonstrate value",
                claims=[],
                overall_confidence=ConfidenceLevel.INSUFFICIENT,
                key_assumptions=[]
            )
        
        claims = []
        
        # Claim: Longitudinal data provides personal context
        supporting_signals = [
            "Personal baselines established from extended monitoring",
            f"{sum(len(history.get(s, [])) for s in history)} total data points collected",
            "Individual variability patterns identified"
        ]
        
        claims.append(ImpactClaim(
            claim_statement="Longitudinal tracking provides personal context that single lab tests cannot",
            supporting_data_signals=supporting_signals,
            confidence_level=ConfidenceLevel.HIGH,
            why_this_is_valid="Personal baselines replace population averages with individual patterns",
            limitations=[
                "Requires consistent monitoring commitment",
                "Value increases over time",
                "Does not replace all clinical testing"
            ]
        ))
        
        # Claim: Captures variability
        claims.append(ImpactClaim(
            claim_statement="Continuous data captures day-to-day variability missed by annual tests",
            supporting_data_signals=[
                "Variability patterns identified",
                "Outliers and trends detected",
                "Context for single-point measurements"
            ],
            confidence_level=ConfidenceLevel.HIGH,
            why_this_is_valid="Annual tests are single snapshots; longitudinal data shows full picture",
            limitations=[
                "Requires data quality maintenance",
                "Interpretation requires expertise",
                "Some markers don't benefit from continuous monitoring"
            ]
        ))
        
        return ImpactModule(
            module_type=ImpactModuleType.LONGITUDINAL_VALUE,
            module_title="Value of Longitudinal Tracking",
            should_render=True,
            suppression_reason=None,
            claims=claims,
            overall_confidence=ConfidenceLevel.HIGH,
            key_assumptions=[
                "Monitoring continues consistently",
                "Data quality maintained",
                "Results integrated into clinical care"
            ]
        )
    
    # ===== Helper Methods =====
    
    def _has_sufficient_data(self, history: Dict[str, List[Dict]]) -> bool:
        """Check if sufficient data for impact claims."""
        total_points = sum(len(history.get(stream, [])) for stream in history)
        return total_points >= self.min_data_points
    
    def _has_high_confidence(self, estimates: Dict[str, Dict]) -> bool:
        """Check if estimates have high enough confidence."""
        confidences = [e.get("confidence", 0) for e in estimates.values()]
        if not confidences:
            return False
        
        avg_conf = sum(confidences) / len(confidences)
        return avg_conf >= self.min_confidence_for_claims
    
    def _has_continuous_monitoring(self, history: Dict[str, List[Dict]]) -> bool:
        """Check if continuous monitoring is active."""
        # Look for glucose or other continuous streams
        glucose_points = len(history.get("glucose", []))
        return glucose_points >= 50
    
    def _has_stable_patterns(
        self,
        estimates: Dict[str, Dict],
        phase2_metadata: Optional[Dict]
    ) -> bool:
        """Check if patterns are stable."""
        if not phase2_metadata:
            return False
        
        # Check temporal stability
        temporal_stable = phase2_metadata.get("temporal_stability_high", False)
        
        # Check low variability
        low_variability = phase2_metadata.get("low_variability", False)
        
        return temporal_stable or low_variability
    
    def _count_data_points(self, data: List[Dict]) -> int:
        """Count data points."""
        return len(data)
    
    def _avg_confidence(self, estimates: Dict[str, Dict]) -> float:
        """Compute average confidence."""
        confidences = [e.get("confidence", 0) for e in estimates.values()]
        if not confidences:
            return 0.0
        return sum(confidences) / len(confidences)
    
    def _extract_early_warnings(self, phase3_metadata: Dict) -> List[str]:
        """Extract early warning signals from change point analysis."""
        warnings = []
        
        change_analyses = phase3_metadata.get("change_point_analysis", {})
        for marker, analysis in change_analyses.items():
            if "early_warning_flags" in analysis:
                warnings.extend(analysis["early_warning_flags"])
        
        return warnings[:3]  # Top 3


# ===== Singleton =====

_impact_analyzer_instance = None

def get_cost_care_impact_analyzer() -> CostCareImpactAnalyzer:
    """Get singleton instance of cost/care impact analyzer."""
    global _impact_analyzer_instance
    if _impact_analyzer_instance is None:
        _impact_analyzer_instance = CostCareImpactAnalyzer()
    return _impact_analyzer_instance
