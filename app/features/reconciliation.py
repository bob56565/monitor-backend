"""
Cross-Domain Reconciliation Engine (Phase 2 - A2.2)

Reconciles outputs across physiological domains after all estimators run.
Detects contradictions, adjusts ranges, and generates explanations.

This is a POST_SOLVER_PRE_REPORT step that ensures physiological coherence.
"""

from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime
import logging

from app.features.constraint_lattice import (
    get_constraint_lattice, ConstraintEvaluation
)

logger = logging.getLogger(__name__)


@dataclass
class ReconciliationNote:
    """
    A note explaining a reconciliation adjustment.
    """
    marker_name: str
    note_type: str  # "range_widened", "center_shifted", "confidence_reduced"
    reason: str
    before_value: Optional[Tuple[float, float]] = None  # (center, range) or (min, max)
    after_value: Optional[Tuple[float, float]] = None
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class ReconciliationResult:
    """
    Result of cross-domain reconciliation.
    """
    reconciled_estimates: Dict[str, Any]  # marker -> updated estimate
    reconciliation_notes: List[ReconciliationNote]
    contradiction_flags: List[str]  # List of detected contradictions
    range_adjustments_applied: int
    total_confidence_penalty: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "reconciled_estimates": self.reconciled_estimates,
            "reconciliation_notes": [
                {
                    "marker": note.marker_name,
                    "type": note.note_type,
                    "reason": note.reason,
                    "before": note.before_value,
                    "after": note.after_value,
                    "timestamp": note.timestamp
                }
                for note in self.reconciliation_notes
            ],
            "contradiction_flags": self.contradiction_flags,
            "range_adjustments_applied": self.range_adjustments_applied,
            "total_confidence_penalty": self.total_confidence_penalty
        }


class ReconciliationEngine:
    """
    Cross-domain reconciliation engine.
    
    Ensures physiological coherence across all inferred outputs by:
    1. Detecting contradictions using constraint lattice
    2. Adjusting ranges when contradictions exist
    3. Shifting centers if needed
    4. Generating automatic explanations
    """
    
    def __init__(self):
        """Initialize reconciliation engine."""
        self.lattice = get_constraint_lattice()
    
    def reconcile(
        self,
        estimates: Dict[str, Dict[str, Any]],
        measured_anchors: Optional[Dict[str, float]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ReconciliationResult:
        """
        Reconcile estimates across domains.
        
        Args:
            estimates: Dictionary of marker_name -> estimate dict
                      Each estimate should have: {center, range, confidence, ...}
            measured_anchors: Dictionary of measured values (cannot be altered)
            metadata: Additional metadata (age, sex, medications, etc.)
        
        Returns:
            ReconciliationResult with adjusted estimates and explanations
        """
        measured_anchors = measured_anchors or {}
        metadata = metadata or {}
        
        logger.info(f"Reconciling {len(estimates)} estimates with {len(measured_anchors)} anchors")
        
        # Extract values for constraint evaluation
        all_values = {}
        for marker, estimate in estimates.items():
            if "center" in estimate:
                all_values[marker] = estimate["center"]
            elif "value" in estimate:
                all_values[marker] = estimate["value"]
        
        # Add measured anchors
        all_values.update(measured_anchors)
        
        # Evaluate constraints
        constraint_evals = self.lattice.evaluate_constraints(all_values, metadata)
        
        # Process evaluations and adjust estimates
        reconciled = {}
        notes = []
        contradictions = []
        adjustments = 0
        total_penalty = 0.0
        
        for marker, estimate in estimates.items():
            if marker in measured_anchors:
                # Never alter measured values
                reconciled[marker] = estimate.copy()
                continue
            
            # Find relevant constraint violations
            relevant_violations = [
                e for e in constraint_evals 
                if e.is_violated and marker in e.triggered_by
            ]
            
            if not relevant_violations:
                # No violations, keep estimate as-is
                reconciled[marker] = estimate.copy()
                continue
            
            # Apply reconciliation
            adjusted_estimate = estimate.copy()
            
            for violation in relevant_violations:
                # Record contradiction
                contradictions.append(
                    f"{violation.constraint_name}: {violation.explanation}"
                )
                
                # Adjust range based on tightening_factor
                if "range" in adjusted_estimate:
                    before_range = adjusted_estimate["range"]
                    adjusted_estimate["range"] = before_range * violation.tightening_factor
                    
                    if violation.tightening_factor > 1.0:
                        # Range widened
                        notes.append(ReconciliationNote(
                            marker_name=marker,
                            note_type="range_widened",
                            reason=violation.explanation,
                            before_value=(adjusted_estimate.get("center", 0), before_range),
                            after_value=(adjusted_estimate.get("center", 0), adjusted_estimate["range"])
                        ))
                        adjustments += 1
                
                # Apply confidence penalty
                if "confidence" in adjusted_estimate:
                    before_conf = adjusted_estimate["confidence"]
                    penalty = violation.confidence_penalty
                    adjusted_estimate["confidence"] = max(0.0, before_conf - penalty)
                    total_penalty += penalty
                    
                    if penalty > 0:
                        notes.append(ReconciliationNote(
                            marker_name=marker,
                            note_type="confidence_reduced",
                            reason=f"Constraint violation penalty: {violation.explanation}",
                            before_value=(before_conf, 0),
                            after_value=(adjusted_estimate["confidence"], 0)
                        ))
            
            reconciled[marker] = adjusted_estimate
        
        logger.info(
            f"Reconciliation complete: {len(contradictions)} contradictions, "
            f"{adjustments} adjustments, {total_penalty:.2f} total penalty"
        )
        
        return ReconciliationResult(
            reconciled_estimates=reconciled,
            reconciliation_notes=notes,
            contradiction_flags=contradictions,
            range_adjustments_applied=adjustments,
            total_confidence_penalty=min(total_penalty, 0.50)  # Cap at 50%
        )
    
    def reconcile_with_anchor_priority(
        self,
        estimates: Dict[str, Dict[str, Any]],
        measured_anchors: Dict[str, float],
        metadata: Optional[Dict[str, Any]] = None
    ) -> ReconciliationResult:
        """
        Reconcile with strict anchor priority.
        
        If an inferred estimate conflicts with a measured anchor, the
        estimate is penalized and widened, but the anchor is never changed.
        
        Args:
            estimates: Inferred estimates
            measured_anchors: Measured values (immutable)
            metadata: Additional metadata
        
        Returns:
            ReconciliationResult
        """
        metadata = metadata or {}
        
        # First, check for direct conflicts between estimates and anchors
        conflicts = []
        
        for marker, anchor_value in measured_anchors.items():
            if marker in estimates:
                estimate = estimates[marker]
                
                # Check if anchor is outside estimated range
                if "center" in estimate and "range" in estimate:
                    center = estimate["center"]
                    range_width = estimate["range"]
                    min_val = center - range_width / 2
                    max_val = center + range_width / 2
                    
                    if not (min_val <= anchor_value <= max_val):
                        conflicts.append({
                            "marker": marker,
                            "anchor_value": anchor_value,
                            "estimated_range": (min_val, max_val),
                            "estimated_center": center
                        })
        
        # Standard reconciliation
        result = self.reconcile(estimates, measured_anchors, metadata)
        
        # Apply additional penalties for direct anchor conflicts
        for conflict in conflicts:
            marker = conflict["marker"]
            
            if marker in result.reconciled_estimates:
                est = result.reconciled_estimates[marker]
                
                # Widen range significantly
                if "range" in est:
                    est["range"] *= 1.50  # 50% wider
                
                # Reduce confidence
                if "confidence" in est:
                    est["confidence"] *= 0.70  # 30% penalty
                
                # Add note
                result.reconciliation_notes.append(ReconciliationNote(
                    marker_name=marker,
                    note_type="range_widened",
                    reason=f"Inferred estimate conflicts with measured anchor value {conflict['anchor_value']:.1f}",
                    before_value=(conflict["estimated_center"], conflict["estimated_range"]),
                    after_value=(est.get("center"), est.get("range"))
                ))
                
                result.contradiction_flags.append(
                    f"Anchor conflict: {marker} measured={conflict['anchor_value']:.1f} "
                    f"vs estimated={conflict['estimated_center']:.1f}"
                )
                result.range_adjustments_applied += 1
        
        return result
    
    def detect_cross_domain_contradictions(
        self,
        estimates: Dict[str, Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """
        Detect contradictions between estimates across domains.
        
        Args:
            estimates: Dictionary of estimates
            metadata: Additional metadata
        
        Returns:
            List of contradiction descriptions
        """
        # Extract values
        values = {}
        for marker, estimate in estimates.items():
            if "center" in estimate:
                values[marker] = estimate["center"]
            elif "value" in estimate:
                values[marker] = estimate["value"]
        
        # Evaluate constraints
        evals = self.lattice.evaluate_constraints(values, metadata or {})
        
        # Collect violations
        contradictions = [
            f"{e.constraint_name}: {e.explanation}"
            for e in evals
            if e.is_violated
        ]
        
        return contradictions


# Global instance
_global_reconciliation_engine: Optional[ReconciliationEngine] = None


def get_reconciliation_engine() -> ReconciliationEngine:
    """Get or create the global reconciliation engine instance."""
    global _global_reconciliation_engine
    if _global_reconciliation_engine is None:
        _global_reconciliation_engine = ReconciliationEngine()
    return _global_reconciliation_engine
