"""
Anchor Strength Gating (Phase 2 - B.8)

Tracks anchor strength (none/weak/moderate/strong) per output and uses it to:
- Control language and phrasing
- Adjust range width
- Set confidence ceilings
- Determine output eligibility

Anchor strength is computed from:
- Coverage (data density)
- Direct biomarkers present
- Surrogate relevance
- Temporal stability
"""

from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class AnchorStrength(str, Enum):
    """Strength of anchoring for an output."""
    NONE = "none"  # No anchors, purely population priors
    WEAK = "weak"  # Weak/indirect anchors (distant surrogates)
    MODERATE = "moderate"  # Moderate anchors (some direct biomarkers)
    STRONG = "strong"  # Strong anchors (direct measurements, good coverage)


@dataclass
class AnchorAssessment:
    """
    Assessment of anchor strength for a marker/output.
    """
    marker_name: str
    anchor_strength: AnchorStrength
    
    # Factors contributing to anchor strength
    coverage_score: float = 0.0  # 0-1
    direct_biomarker_score: float = 0.0  # 0-1
    surrogate_score: float = 0.0  # 0-1
    temporal_stability_score: float = 0.0  # 0-1
    
    # Overall anchor score
    overall_score: float = 0.0  # 0-1
    
    # Available anchors
    direct_anchors: List[str] = field(default_factory=list)
    indirect_anchors: List[str] = field(default_factory=list)
    
    # Gating decisions
    should_output: bool = True
    max_confidence: float = 1.0  # Maximum allowed confidence
    min_range_width: float = 0.0  # Minimum range width (fraction)
    
    # Language template
    language_template: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "marker": self.marker_name,
            "anchor_strength": self.anchor_strength.value,
            "scores": {
                "coverage": self.coverage_score,
                "direct_biomarkers": self.direct_biomarker_score,
                "surrogates": self.surrogate_score,
                "temporal_stability": self.temporal_stability_score,
                "overall": self.overall_score
            },
            "anchors": {
                "direct": self.direct_anchors,
                "indirect": self.indirect_anchors
            },
            "gating": {
                "should_output": self.should_output,
                "max_confidence": self.max_confidence,
                "min_range_width": self.min_range_width,
                "language_template": self.language_template
            }
        }


class AnchorStrengthGate:
    """
    Assesses anchor strength and applies gating logic.
    """
    
    # Anchor mappings: output -> required/optional anchors
    ANCHOR_MAPPINGS = {
        "glucose": {
            "direct": ["glucose_isf", "glucose_serum", "glucose_blood"],
            "indirect": ["hemoglobin_a1c", "insulin", "c_peptide"]
        },
        "hemoglobin_a1c": {
            "direct": ["hemoglobin_a1c"],
            "indirect": ["glucose_isf", "glucose_serum"]
        },
        "cholesterol": {
            "direct": ["total_cholesterol", "ldl_cholesterol", "hdl_cholesterol"],
            "indirect": ["triglycerides", "apob", "apoa1"]
        },
        "vitamin_d": {
            "direct": ["vitamin_d_25oh"],
            "indirect": ["calcium", "phosphorus", "pth"]
        },
        "iron_status": {
            "direct": ["iron", "ferritin", "transferrin_saturation"],
            "indirect": ["hemoglobin", "mcv", "crp"]
        },
        "kidney_function": {
            "direct": ["creatinine", "egfr", "bun"],
            "indirect": ["sodium", "potassium", "bicarbonate"]
        }
    }
    
    def __init__(self):
        """Initialize anchor strength gate."""
        pass
    
    def assess_anchor_strength(
        self,
        marker_name: str,
        available_data: Dict[str, Any],
        coverage_info: Optional[Dict[str, float]] = None,
        temporal_info: Optional[Dict[str, float]] = None
    ) -> AnchorAssessment:
        """
        Assess anchor strength for a marker.
        
        Args:
            marker_name: Name of marker/output
            available_data: Available data (marker -> value or info)
            coverage_info: Coverage scores (marker -> score)
            temporal_info: Temporal stability scores (marker -> score)
        
        Returns:
            AnchorAssessment
        """
        coverage_info = coverage_info or {}
        temporal_info = temporal_info or {}
        
        # Get anchor mappings
        anchors = self.ANCHOR_MAPPINGS.get(marker_name, {"direct": [], "indirect": []})
        
        # Identify available anchors
        direct_anchors = [a for a in anchors["direct"] if a in available_data]
        indirect_anchors = [a for a in anchors["indirect"] if a in available_data]
        
        # Compute scores
        
        # 1. Direct biomarker score
        if anchors["direct"]:
            direct_biomarker_score = len(direct_anchors) / len(anchors["direct"])
        else:
            direct_biomarker_score = 0.0
        
        # 2. Surrogate score
        if anchors["indirect"]:
            surrogate_score = min(1.0, len(indirect_anchors) / max(len(anchors["indirect"]), 1))
        else:
            surrogate_score = 0.0
        
        # 3. Coverage score (average coverage of available anchors)
        anchor_coverages = []
        for anchor in direct_anchors + indirect_anchors:
            if anchor in coverage_info:
                anchor_coverages.append(coverage_info[anchor])
        
        coverage_score = sum(anchor_coverages) / len(anchor_coverages) if anchor_coverages else 0.0
        
        # 4. Temporal stability score
        anchor_stabilities = []
        for anchor in direct_anchors:
            if anchor in temporal_info:
                anchor_stabilities.append(temporal_info[anchor])
        
        temporal_stability_score = sum(anchor_stabilities) / len(anchor_stabilities) if anchor_stabilities else 0.5
        
        # Compute overall score (weighted combination)
        overall_score = (
            0.40 * direct_biomarker_score +
            0.25 * coverage_score +
            0.20 * surrogate_score +
            0.15 * temporal_stability_score
        )
        
        # Determine anchor strength
        if overall_score >= 0.70 and direct_anchors:
            anchor_strength = AnchorStrength.STRONG
        elif overall_score >= 0.40 and (direct_anchors or len(indirect_anchors) >= 2):
            anchor_strength = AnchorStrength.MODERATE
        elif overall_score >= 0.15 or indirect_anchors:
            anchor_strength = AnchorStrength.WEAK
        else:
            anchor_strength = AnchorStrength.NONE
        
        # Apply gating rules
        gating_rules = self._get_gating_rules(anchor_strength)
        
        return AnchorAssessment(
            marker_name=marker_name,
            anchor_strength=anchor_strength,
            coverage_score=coverage_score,
            direct_biomarker_score=direct_biomarker_score,
            surrogate_score=surrogate_score,
            temporal_stability_score=temporal_stability_score,
            overall_score=overall_score,
            direct_anchors=direct_anchors,
            indirect_anchors=indirect_anchors,
            should_output=gating_rules["should_output"],
            max_confidence=gating_rules["max_confidence"],
            min_range_width=gating_rules["min_range_width"],
            language_template=gating_rules["language_template"]
        )
    
    def _get_gating_rules(self, anchor_strength: AnchorStrength) -> Dict[str, Any]:
        """
        Get gating rules for an anchor strength level.
        """
        rules = {
            AnchorStrength.STRONG: {
                "should_output": True,
                "max_confidence": 0.90,  # Can reach high confidence
                "min_range_width": 0.05,  # Can be tight (5% of center)
                "language_template": "Based on direct measurements"
            },
            AnchorStrength.MODERATE: {
                "should_output": True,
                "max_confidence": 0.70,  # Moderate confidence cap
                "min_range_width": 0.15,  # Moderate width (15% of center)
                "language_template": "Inferred from available biomarkers"
            },
            AnchorStrength.WEAK: {
                "should_output": True,
                "max_confidence": 0.45,  # Low confidence cap
                "min_range_width": 0.30,  # Wide range (30% of center)
                "language_template": "Exploratory estimate based on indirect markers"
            },
            AnchorStrength.NONE: {
                "should_output": False,  # Don't output by default
                "max_confidence": 0.25,  # Very low confidence if forced to output
                "min_range_width": 0.50,  # Very wide range (50% of center)
                "language_template": "Population-based estimate (insufficient personal data)"
            }
        }
        
        return rules.get(anchor_strength, rules[AnchorStrength.NONE])
    
    def apply_anchor_gating(
        self,
        estimates: Dict[str, Dict[str, Any]],
        assessments: Dict[str, AnchorAssessment]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Apply anchor strength gating to estimates.
        
        Args:
            estimates: Original estimates
            assessments: Anchor strength assessments
        
        Returns:
            Gated estimates (filtered and adjusted)
        """
        gated = {}
        
        for marker, estimate in estimates.items():
            if marker not in assessments:
                # No assessment, keep as-is
                gated[marker] = estimate.copy()
                continue
            
            assessment = assessments[marker]
            
            # Check if should output
            if not assessment.should_output:
                # Skip this output
                logger.debug(f"Filtered out {marker} due to insufficient anchor strength")
                continue
            
            # Apply gating adjustments
            gated_estimate = estimate.copy()
            
            # Cap confidence
            if "confidence" in gated_estimate:
                gated_estimate["confidence"] = min(
                    gated_estimate["confidence"],
                    assessment.max_confidence
                )
            
            # Enforce minimum range width
            if "range" in gated_estimate and "center" in gated_estimate:
                center = abs(gated_estimate["center"])
                min_range = center * assessment.min_range_width
                if gated_estimate["range"] < min_range:
                    gated_estimate["range"] = min_range
            
            # Add anchor metadata
            gated_estimate["anchor_assessment"] = assessment.to_dict()
            gated_estimate["anchor_strength"] = assessment.anchor_strength.value
            
            gated[marker] = gated_estimate
        
        logger.info(
            f"Anchor gating: {len(gated)} outputs passed from {len(estimates)} inputs"
        )
        
        return gated
    
    def assess_batch(
        self,
        markers: List[str],
        available_data: Dict[str, Any],
        coverage_info: Optional[Dict[str, float]] = None,
        temporal_info: Optional[Dict[str, float]] = None
    ) -> Dict[str, AnchorAssessment]:
        """
        Assess anchor strength for multiple markers.
        
        Args:
            markers: List of markers to assess
            available_data: Available data
            coverage_info: Coverage scores
            temporal_info: Temporal stability scores
        
        Returns:
            Dictionary of marker -> AnchorAssessment
        """
        assessments = {}
        
        for marker in markers:
            assessment = self.assess_anchor_strength(
                marker_name=marker,
                available_data=available_data,
                coverage_info=coverage_info,
                temporal_info=temporal_info
            )
            assessments[marker] = assessment
        
        return assessments
    
    def get_language_for_strength(
        self,
        anchor_strength: AnchorStrength,
        marker_name: str
    ) -> str:
        """
        Get appropriate language/phrasing for anchor strength.
        
        Args:
            anchor_strength: Anchor strength level
            marker_name: Name of marker
        
        Returns:
            Language template/phrase
        """
        templates = {
            AnchorStrength.STRONG: f"{marker_name} is directly measured and well-characterized",
            AnchorStrength.MODERATE: f"{marker_name} is inferred from available biomarkers with moderate confidence",
            AnchorStrength.WEAK: f"{marker_name} is an exploratory estimate based on indirect markers",
            AnchorStrength.NONE: f"{marker_name} is a population-based estimate (insufficient personal data)"
        }
        
        return templates.get(anchor_strength, templates[AnchorStrength.NONE])


# Global instance
_global_anchor_gate: Optional[AnchorStrengthGate] = None


def get_anchor_strength_gate() -> AnchorStrengthGate:
    """Get or create the global anchor strength gate instance."""
    global _global_anchor_gate
    if _global_anchor_gate is None:
        _global_anchor_gate = AnchorStrengthGate()
    return _global_anchor_gate
