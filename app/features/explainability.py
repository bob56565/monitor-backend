"""
Tight Explainability Engine (Phase 3 B.6)

Provides clear, minimal, high-signal explanations for every output.
No essays, no redundancy - just essential drivers and actionable insights.

Key Features:
- Top 2-4 ranked drivers per output
- Single "because" sentence per output
- Confidence bar with visual representation
- "What would change this" actionable suggestions

Design Principles:
- Maximum signal, minimum noise
- Drivers must map to actual inputs and constraints
- Consistent with evidence grade and anchor strength
- Actionable, not just descriptive
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple
from app.features.language_control import get_language_controller


class DriverType(str, Enum):
    """Type of explanatory driver."""
    MEASURED_ANCHOR = "measured_anchor"
    STRONG_CORRELATION = "strong_correlation"
    TEMPORAL_PATTERN = "temporal_pattern"
    CONSTRAINT_INFERENCE = "constraint_inference"
    POPULATION_PRIOR = "population_prior"
    SOLVER_AGREEMENT = "solver_agreement"
    PERSONAL_BASELINE = "personal_baseline"


@dataclass
class ExplanationDriver:
    """Single driver for an estimate."""
    driver_type: DriverType
    driver_name: str  # Human-readable name
    contribution_weight: float  # 0.0 to 1.0
    
    # Specific details
    source_input: Optional[str]  # Which input/anchor drove this
    correlation_strength: Optional[float]  # If correlation-based
    temporal_consistency: Optional[float]  # If temporal-based
    
    # Human-readable explanation
    short_explanation: str  # One sentence max


@dataclass
class OutputExplanation:
    """Complete explanation for a single output."""
    output_id: str
    estimated_value: Optional[float]
    estimated_range: Optional[Tuple[float, float]]
    confidence: float
    evidence_grade: str
    
    # Top drivers (ranked by importance)
    top_drivers: List[ExplanationDriver]  # 2-4 drivers
    
    # Single "because" sentence
    because_sentence: str
    
    # Confidence visualization
    confidence_bar: str  # Visual bar (e.g., "████░░░░░░ 40%")
    confidence_interpretation: str  # "Low confidence", "Moderate confidence", etc.
    
    # What would improve this
    what_would_change_this: List[str]  # 1-3 actionable suggestions
    
    # Uncertainty sources
    primary_uncertainty: str
    secondary_uncertainties: List[str]


class ExplainabilityEngine:
    """
    Engine for generating tight, high-signal explanations.
    
    Avoids:
    - Long paragraphs
    - Redundant information
    - Vague statements
    - Technical jargon (unless provider-facing)
    
    Provides:
    - Ranked drivers with weights
    - One-sentence "because" statement
    - Visual confidence
    - Actionable improvement suggestions
    """
    
    def __init__(self):
        self.language_controller = get_language_controller()
        
        # Driver weight thresholds
        self.min_driver_weight = 0.15  # Only show drivers contributing ≥15%
        
        # Max drivers to show
        self.max_drivers = 4
    
    def explain_output(
        self,
        output_id: str,
        estimate: Dict[str, any],
        phase2_metadata: Optional[Dict] = None,
        phase3_metadata: Optional[Dict] = None
    ) -> OutputExplanation:
        """
        Generate tight explanation for a single output.
        
        Args:
            output_id: Output identifier
            estimate: Estimate dict from inference
            phase2_metadata: Optional Phase 2 metadata
            phase3_metadata: Optional Phase 3 metadata
        
        Returns:
            Complete explanation with drivers, because-sentence, and suggestions
        """
        # Extract key fields
        value = estimate.get("estimated_value")
        value_low = estimate.get("estimated_value_low")
        value_high = estimate.get("estimated_value_high")
        confidence = estimate.get("confidence", 0.5)
        evidence_grade = estimate.get("evidence_grade", "C")
        
        # 1. Identify top drivers
        drivers = self._identify_top_drivers(
            output_id, estimate, phase2_metadata, phase3_metadata
        )
        
        # 2. Generate "because" sentence
        because = self._generate_because_sentence(output_id, drivers, confidence)
        
        # 3. Generate confidence bar
        conf_bar = self._generate_confidence_bar(confidence)
        conf_interp = self._interpret_confidence(confidence)
        
        # 4. Generate "what would change this"
        suggestions = self._generate_improvement_suggestions(
            output_id, drivers, confidence, evidence_grade, phase3_metadata
        )
        
        # 5. Identify uncertainty sources
        primary_unc, secondary_uncs = self._identify_uncertainty_sources(
            estimate, phase2_metadata
        )
        
        return OutputExplanation(
            output_id=output_id,
            estimated_value=value,
            estimated_range=(value_low, value_high) if value_low and value_high else None,
            confidence=confidence,
            evidence_grade=evidence_grade,
            top_drivers=drivers[:self.max_drivers],
            because_sentence=because,
            confidence_bar=conf_bar,
            confidence_interpretation=conf_interp,
            what_would_change_this=suggestions,
            primary_uncertainty=primary_unc,
            secondary_uncertainties=secondary_uncs
        )
    
    def explain_batch(
        self,
        estimates: Dict[str, Dict],
        phase2_metadata: Optional[Dict] = None,
        phase3_metadata: Optional[Dict] = None
    ) -> Dict[str, OutputExplanation]:
        """Generate explanations for all outputs."""
        explanations = {}
        
        for output_id, estimate in estimates.items():
            explanations[output_id] = self.explain_output(
                output_id, estimate, phase2_metadata, phase3_metadata
            )
        
        return explanations
    
    def format_for_display(
        self,
        explanation: OutputExplanation,
        target_audience: str = "patient"  # "patient" or "provider"
    ) -> str:
        """
        Format explanation for display.
        
        Returns compact, readable text block.
        """
        lines = []
        
        # Header
        if explanation.estimated_value is not None:
            lines.append(f"**{explanation.output_id}**: {explanation.estimated_value:.1f}")
        else:
            lines.append(f"**{explanation.output_id}**")
        
        # Range
        if explanation.estimated_range:
            low, high = explanation.estimated_range
            lines.append(f"  Range: {low:.1f} - {high:.1f}")
        
        # Confidence
        lines.append(f"  Confidence: {explanation.confidence_bar} ({explanation.confidence_interpretation})")
        
        # Because
        lines.append(f"  **Because**: {explanation.because_sentence}")
        
        # Top drivers
        lines.append(f"  **Key drivers**:")
        for i, driver in enumerate(explanation.top_drivers[:3], 1):
            weight_pct = int(driver.contribution_weight * 100)
            lines.append(f"    {i}. {driver.driver_name} ({weight_pct}%): {driver.short_explanation}")
        
        # What would change this
        if explanation.what_would_change_this:
            lines.append(f"  **To improve**: {explanation.what_would_change_this[0]}")
        
        return "\n".join(lines)
    
    # ===== Core Methods =====
    
    def _identify_top_drivers(
        self,
        output_id: str,
        estimate: Dict,
        phase2_metadata: Optional[Dict],
        phase3_metadata: Optional[Dict]
    ) -> List[ExplanationDriver]:
        """Identify and rank drivers for an output."""
        drivers = []
        
        # 1. Check for measured anchors
        anchor_strength = estimate.get("anchor_strength", "NONE")
        if anchor_strength in ["STRONG", "MODERATE"]:
            drivers.append(ExplanationDriver(
                driver_type=DriverType.MEASURED_ANCHOR,
                driver_name="Direct measurement",
                contribution_weight=0.6 if anchor_strength == "STRONG" else 0.4,
                source_input=estimate.get("primary_anchor"),
                correlation_strength=None,
                temporal_consistency=None,
                short_explanation=f"Based on recent {estimate.get('primary_anchor', 'measurement')}"
            ))
        
        # 2. Check for personal baseline contribution
        if phase2_metadata and phase2_metadata.get("personal_baseline_used"):
            drivers.append(ExplanationDriver(
                driver_type=DriverType.PERSONAL_BASELINE,
                driver_name="Personal baseline",
                contribution_weight=0.3,
                source_input="historical_pattern",
                correlation_strength=None,
                temporal_consistency=phase2_metadata.get("baseline_confidence", 0.5),
                short_explanation="Consistent with your personal historical range"
            ))
        
        # 3. Check for solver agreement
        if phase2_metadata and phase2_metadata.get("solver_agreement"):
            agreement = phase2_metadata["solver_agreement"]
            if agreement.get("converged"):
                drivers.append(ExplanationDriver(
                    driver_type=DriverType.SOLVER_AGREEMENT,
                    driver_name="Multiple methods agree",
                    contribution_weight=0.25,
                    source_input="multi_solver",
                    correlation_strength=agreement.get("agreement_score", 0.7),
                    temporal_consistency=None,
                    short_explanation="Independent estimation methods converged"
                ))
        
        # 4. Check for strong correlations
        correlations = estimate.get("correlations", {})
        if correlations:
            strongest = max(correlations.items(), key=lambda x: abs(x[1]))
            corr_marker, corr_strength = strongest
            if abs(corr_strength) > 0.6:
                drivers.append(ExplanationDriver(
                    driver_type=DriverType.STRONG_CORRELATION,
                    driver_name=f"Correlation with {corr_marker}",
                    contribution_weight=min(abs(corr_strength), 0.4),
                    source_input=corr_marker,
                    correlation_strength=corr_strength,
                    temporal_consistency=None,
                    short_explanation=f"Strongly correlated with your {corr_marker} levels"
                ))
        
        # 5. Check for temporal patterns
        if phase2_metadata and phase2_metadata.get("temporal_stability_high"):
            drivers.append(ExplanationDriver(
                driver_type=DriverType.TEMPORAL_PATTERN,
                driver_name="Stable temporal pattern",
                contribution_weight=0.2,
                source_input="history",
                correlation_strength=None,
                temporal_consistency=phase2_metadata.get("temporal_stability", 0.7),
                short_explanation="Values have been stable over time"
            ))
        
        # 6. Fallback to population prior
        if not drivers or sum(d.contribution_weight for d in drivers) < 0.5:
            drivers.append(ExplanationDriver(
                driver_type=DriverType.POPULATION_PRIOR,
                driver_name="Population reference",
                contribution_weight=0.3,
                source_input="population_data",
                correlation_strength=None,
                temporal_consistency=None,
                short_explanation="Based on population reference ranges"
            ))
        
        # Sort by weight
        drivers.sort(key=lambda d: d.contribution_weight, reverse=True)
        
        # Filter by minimum weight
        drivers = [d for d in drivers if d.contribution_weight >= self.min_driver_weight]
        
        return drivers
    
    def _generate_because_sentence(
        self,
        output_id: str,
        drivers: List[ExplanationDriver],
        confidence: float
    ) -> str:
        """Generate concise 'because' sentence."""
        if not drivers:
            return f"Estimated from available data (low confidence)."
        
        # Take top 2 drivers
        top_2 = drivers[:2]
        
        # Build sentence
        parts = []
        
        for driver in top_2:
            if driver.driver_type == DriverType.MEASURED_ANCHOR:
                parts.append("recent direct measurements")
            elif driver.driver_type == DriverType.PERSONAL_BASELINE:
                parts.append("your historical patterns")
            elif driver.driver_type == DriverType.SOLVER_AGREEMENT:
                parts.append("multiple independent methods")
            elif driver.driver_type == DriverType.STRONG_CORRELATION:
                parts.append(f"correlation with {driver.source_input}")
            elif driver.driver_type == DriverType.TEMPORAL_PATTERN:
                parts.append("stable temporal trends")
            else:
                parts.append("population references")
        
        if len(parts) == 1:
            return f"Estimated primarily from {parts[0]}."
        else:
            return f"Estimated from {parts[0]} and {parts[1]}."
    
    def _generate_confidence_bar(self, confidence: float) -> str:
        """Generate visual confidence bar."""
        filled = int(confidence * 10)
        empty = 10 - filled
        
        bar = "█" * filled + "░" * empty
        pct = int(confidence * 100)
        
        return f"{bar} {pct}%"
    
    def _interpret_confidence(self, confidence: float) -> str:
        """Interpret confidence level."""
        if confidence >= 0.85:
            return "Very high confidence"
        elif confidence >= 0.70:
            return "High confidence"
        elif confidence >= 0.50:
            return "Moderate confidence"
        elif confidence >= 0.30:
            return "Low confidence"
        else:
            return "Very low confidence"
    
    def _generate_improvement_suggestions(
        self,
        output_id: str,
        drivers: List[ExplanationDriver],
        confidence: float,
        evidence_grade: str,
        phase3_metadata: Optional[Dict]
    ) -> List[str]:
        """Generate actionable suggestions to improve estimate."""
        suggestions = []
        
        # 1. If no measured anchor, suggest measurement
        has_measured = any(d.driver_type == DriverType.MEASURED_ANCHOR for d in drivers)
        if not has_measured:
            suggestions.append(f"Get a direct {output_id} measurement")
        
        # 2. If confidence low, suggest more data
        if confidence < 0.5:
            suggestions.append("Collect more longitudinal data (continuous monitoring)")
        
        # 3. Check uncertainty reduction recommendations
        if phase3_metadata and "top_recommendations" in phase3_metadata:
            recs = phase3_metadata["top_recommendations"]
            if recs and len(suggestions) < 2:
                top_rec = recs[0]
                if output_id in top_rec.get("outputs_affected", []):
                    suggestions.append(f"Measure {top_rec['measurement']}")
        
        # 4. If relying heavily on priors, suggest anchors
        prior_heavy = any(
            d.driver_type == DriverType.POPULATION_PRIOR and d.contribution_weight > 0.4
            for d in drivers
        )
        if prior_heavy and len(suggestions) < 2:
            suggestions.append("Establish personal baseline with consistent monitoring")
        
        # 5. Ensure at least one suggestion (even for high confidence)
        if not suggestions:
            if confidence >= 0.7:
                suggestions.append("Maintain current monitoring frequency")
            else:
                suggestions.append(f"Consider measuring related markers to refine {output_id} estimate")
        
        # Limit to 3
        return suggestions[:3]
    
    def _identify_uncertainty_sources(
        self,
        estimate: Dict,
        phase2_metadata: Optional[Dict]
    ) -> Tuple[str, List[str]]:
        """Identify primary and secondary uncertainty sources."""
        sources = []
        
        confidence = estimate.get("confidence", 0.5)
        anchor_strength = estimate.get("anchor_strength", "NONE")
        
        # Check various sources
        if anchor_strength in ["NONE", "WEAK"]:
            sources.append("No direct measurements")
        
        if confidence < 0.4:
            sources.append("Insufficient data")
        
        if phase2_metadata:
            if phase2_metadata.get("solver_disagreement"):
                sources.append("Methods disagree")
            
            if phase2_metadata.get("constraint_conflicts", 0) > 0:
                sources.append("Physiological inconsistencies")
            
            if phase2_metadata.get("temporal_gap"):
                sources.append("Stale data")
        
        # Separate primary and secondary
        primary = sources[0] if sources else "General uncertainty"
        secondary = sources[1:] if len(sources) > 1 else []
        
        return primary, secondary


# ===== Singleton =====

_explainability_engine_instance = None

def get_explainability_engine() -> ExplainabilityEngine:
    """Get singleton instance of explainability engine."""
    global _explainability_engine_instance
    if _explainability_engine_instance is None:
        _explainability_engine_instance = ExplainabilityEngine()
    return _explainability_engine_instance
