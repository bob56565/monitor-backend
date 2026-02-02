"""
Confidence Calibration System (Phase 2 - B.7)

Calibrates confidence so it corresponds to real-world reliability.
Decomposes confidence into interpretable components and provides explanations.

Confidence components:
- Data adequacy
- Anchor strength
- Solver agreement
- Temporal stability
- Constraint consistency
- Input conflict penalty

External confidence respects Phase 1 evidence grade caps.
"""

from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import logging

from app.models.inference_pack_v2 import EvidenceGrade, EVIDENCE_GRADE_CAPS

logger = logging.getLogger(__name__)


@dataclass
class ConfidenceComponents:
    """
    Internal confidence components.
    """
    data_adequacy: float = 0.5  # 0-1
    anchor_strength: float = 0.5  # 0-1
    solver_agreement: float = 0.5  # 0-1
    temporal_stability: float = 0.5  # 0-1
    constraint_consistency: float = 0.5  # 0-1
    input_conflict_penalty: float = 0.0  # 0-1 (penalty, not component)
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary."""
        return {
            "data_adequacy": self.data_adequacy,
            "anchor_strength": self.anchor_strength,
            "solver_agreement": self.solver_agreement,
            "temporal_stability": self.temporal_stability,
            "constraint_consistency": self.constraint_consistency,
            "input_conflict_penalty": self.input_conflict_penalty
        }


@dataclass
class CalibratedConfidence:
    """
    Calibrated confidence with explanation.
    """
    marker_name: str
    
    # Final confidence
    confidence: float  # 0-1, respecting evidence grade cap
    
    # Evidence grade and cap
    evidence_grade: EvidenceGrade
    grade_cap: float
    
    # Internal components
    components: ConfidenceComponents
    
    # Explanation
    top_drivers: List[Tuple[str, float]]  # [(component_name, value), ...]
    top_uncertainties: List[Tuple[str, float]]  # [(component_name, value), ...]
    
    # Metadata
    is_capped: bool = False  # Whether confidence was capped by evidence grade
    pre_calibration_confidence: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "marker": self.marker_name,
            "confidence": self.confidence,
            "evidence_grade": self.evidence_grade.value,
            "grade_cap": self.grade_cap,
            "is_capped": self.is_capped,
            "components": self.components.to_dict(),
            "top_confidence_drivers": [
                {"component": name, "value": value}
                for name, value in self.top_drivers
            ],
            "top_uncertainty_drivers": [
                {"component": name, "value": value}
                for name, value in self.top_uncertainties
            ]
        }


class ConfidenceCalibrator:
    """
    Calibrates confidence based on multiple factors.
    """
    
    # Component weights (how much each component contributes)
    DEFAULT_WEIGHTS = {
        "data_adequacy": 0.25,
        "anchor_strength": 0.25,
        "solver_agreement": 0.20,
        "temporal_stability": 0.15,
        "constraint_consistency": 0.15
    }
    
    def __init__(self):
        """Initialize confidence calibrator."""
        self.weights = self.DEFAULT_WEIGHTS.copy()
        self.calibration_curves: Dict[str, Any] = {}  # Placeholder for learned curves
    
    def set_weight(self, component: str, weight: float):
        """Set custom weight for a component."""
        if component in self.weights:
            self.weights[component] = weight
    
    def calibrate_confidence(
        self,
        marker_name: str,
        components: ConfidenceComponents,
        evidence_grade: EvidenceGrade,
        pre_calibration_confidence: Optional[float] = None
    ) -> CalibratedConfidence:
        """
        Calibrate confidence from components.
        
        Args:
            marker_name: Name of marker
            components: Confidence components
            evidence_grade: Evidence grade (determines cap)
            pre_calibration_confidence: Optional pre-calibrated confidence
        
        Returns:
            CalibratedConfidence with final confidence and explanation
        """
        # Compute base confidence from weighted components
        base_confidence = (
            self.weights["data_adequacy"] * components.data_adequacy +
            self.weights["anchor_strength"] * components.anchor_strength +
            self.weights["solver_agreement"] * components.solver_agreement +
            self.weights["temporal_stability"] * components.temporal_stability +
            self.weights["constraint_consistency"] * components.constraint_consistency
        )
        
        # Apply conflict penalty
        base_confidence *= (1.0 - components.input_conflict_penalty)
        
        # Ensure monotonicity: better components cannot reduce confidence
        # (unless penalty is applied)
        base_confidence = max(0.0, min(1.0, base_confidence))
        
        # Apply calibration curve if available
        # (For now, skip calibration curve - would be learned from validation data)
        calibrated_confidence = base_confidence
        
        # Apply evidence grade cap
        grade_cap = EVIDENCE_GRADE_CAPS[evidence_grade]
        final_confidence = min(calibrated_confidence, grade_cap)
        is_capped = final_confidence < calibrated_confidence
        
        # Identify top drivers and uncertainties
        component_values = {
            "data_adequacy": components.data_adequacy,
            "anchor_strength": components.anchor_strength,
            "solver_agreement": components.solver_agreement,
            "temporal_stability": components.temporal_stability,
            "constraint_consistency": components.constraint_consistency
        }
        
        # Top 3 drivers (highest values)
        sorted_components = sorted(
            component_values.items(),
            key=lambda x: x[1],
            reverse=True
        )
        top_drivers = sorted_components[:3]
        
        # Top 2 uncertainties (lowest values)
        sorted_uncertainties = sorted(
            component_values.items(),
            key=lambda x: x[1]
        )
        top_uncertainties = sorted_uncertainties[:2]
        
        # Add conflict penalty if significant
        if components.input_conflict_penalty > 0.10:
            top_uncertainties.append(
                ("input_conflict_penalty", components.input_conflict_penalty)
            )
        
        return CalibratedConfidence(
            marker_name=marker_name,
            confidence=final_confidence,
            evidence_grade=evidence_grade,
            grade_cap=grade_cap,
            components=components,
            top_drivers=top_drivers,
            top_uncertainties=top_uncertainties,
            is_capped=is_capped,
            pre_calibration_confidence=pre_calibration_confidence
        )
    
    def calibrate_batch(
        self,
        estimates: Dict[str, Dict[str, Any]],
        components_map: Dict[str, ConfidenceComponents],
        evidence_grades: Dict[str, EvidenceGrade]
    ) -> Dict[str, CalibratedConfidence]:
        """
        Calibrate confidence for multiple markers.
        
        Args:
            estimates: Dictionary of marker -> estimate
            components_map: Dictionary of marker -> ConfidenceComponents
            evidence_grades: Dictionary of marker -> EvidenceGrade
        
        Returns:
            Dictionary of marker -> CalibratedConfidence
        """
        calibrated = {}
        
        for marker, estimate in estimates.items():
            if marker not in components_map or marker not in evidence_grades:
                continue
            
            components = components_map[marker]
            evidence_grade = evidence_grades[marker]
            pre_conf = estimate.get("confidence")
            
            calibrated[marker] = self.calibrate_confidence(
                marker_name=marker,
                components=components,
                evidence_grade=evidence_grade,
                pre_calibration_confidence=pre_conf
            )
        
        return calibrated
    
    def compute_components_from_metadata(
        self,
        marker_name: str,
        metadata: Dict[str, Any]
    ) -> ConfidenceComponents:
        """
        Compute confidence components from available metadata.
        
        Args:
            marker_name: Name of marker
            metadata: Dictionary with component information
        
        Returns:
            ConfidenceComponents
        """
        # Extract component values from metadata
        data_adequacy = metadata.get("data_adequacy", 0.5)
        anchor_strength = metadata.get("anchor_strength", 0.5)
        solver_agreement = metadata.get("solver_agreement", 0.5)
        temporal_stability = metadata.get("temporal_stability", 0.5)
        constraint_consistency = metadata.get("constraint_consistency", 0.5)
        input_conflict_penalty = metadata.get("input_conflict_penalty", 0.0)
        
        return ConfidenceComponents(
            data_adequacy=data_adequacy,
            anchor_strength=anchor_strength,
            solver_agreement=solver_agreement,
            temporal_stability=temporal_stability,
            constraint_consistency=constraint_consistency,
            input_conflict_penalty=input_conflict_penalty
        )
    
    def explain_confidence(
        self,
        calibrated: CalibratedConfidence
    ) -> str:
        """
        Generate human-readable explanation of confidence.
        
        Args:
            calibrated: Calibrated confidence
        
        Returns:
            Explanation string
        """
        explanation_parts = []
        
        # Overall confidence
        conf_pct = calibrated.confidence * 100
        explanation_parts.append(
            f"Confidence: {conf_pct:.0f}% (Evidence Grade {calibrated.evidence_grade.value})"
        )
        
        # Top drivers
        if calibrated.top_drivers:
            driver_strs = [
                f"{name.replace('_', ' ')}: {value*100:.0f}%"
                for name, value in calibrated.top_drivers
            ]
            explanation_parts.append(
                f"Main confidence drivers: {', '.join(driver_strs)}"
            )
        
        # Top uncertainties
        if calibrated.top_uncertainties:
            uncertainty_strs = [
                f"{name.replace('_', ' ')}: {value*100:.0f}%"
                for name, value in calibrated.top_uncertainties
            ]
            explanation_parts.append(
                f"Main uncertainty sources: {', '.join(uncertainty_strs)}"
            )
        
        # Capping notice
        if calibrated.is_capped:
            explanation_parts.append(
                f"Confidence capped at {calibrated.grade_cap*100:.0f}% by evidence grade"
            )
        
        return ". ".join(explanation_parts)
    
    def apply_calibrated_confidence(
        self,
        estimates: Dict[str, Dict[str, Any]],
        calibrated_map: Dict[str, CalibratedConfidence]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Apply calibrated confidence to estimates.
        
        Args:
            estimates: Original estimates
            calibrated_map: Map of marker -> CalibratedConfidence
        
        Returns:
            Estimates with updated confidence
        """
        updated = {}
        
        for marker, estimate in estimates.items():
            updated_estimate = estimate.copy()
            
            if marker in calibrated_map:
                calibrated = calibrated_map[marker]
                
                # Update confidence
                updated_estimate["confidence"] = calibrated.confidence
                
                # Add calibration metadata
                updated_estimate["confidence_calibration"] = calibrated.to_dict()
                updated_estimate["confidence_explanation"] = self.explain_confidence(calibrated)
            
            updated[marker] = updated_estimate
        
        return updated


# Global instance
_global_confidence_calibrator: Optional[ConfidenceCalibrator] = None


def get_confidence_calibrator() -> ConfidenceCalibrator:
    """Get or create the global confidence calibrator instance."""
    global _global_confidence_calibrator
    if _global_confidence_calibrator is None:
        _global_confidence_calibrator = ConfidenceCalibrator()
    return _global_confidence_calibrator
