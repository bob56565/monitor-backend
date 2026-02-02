"""
Phase 2 Integration Module

Coordinates all Phase 2 A2 Processing and B Inference enhancements:
- Constraint lattice evaluation (A2.1)
- Cross-domain reconciliation (A2.2)
- Temporal inertia enforcement (A2.3)
- Personal baseline modeling (A2.4)
- Multi-solver agreement (A2.5)
- Priors and decay logic (B.6)
- Confidence calibration (B.7)
- Anchor strength gating (B.8)

All operations are additive, backward-compatible, and feature-flagged.
"""

from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
import logging

from app.models.run_v2 import RunV2
from app.models.inference_pack_v2 import EvidenceGrade

# Phase 2 modules
from app.features.constraint_lattice import get_constraint_lattice
from app.features.reconciliation import get_reconciliation_engine
from app.features.temporal_inertia import get_temporal_inertia_engine, TemporalEvent
from app.features.personal_baselines import get_personal_baseline_engine
from app.features.multi_solver import get_multi_solver_engine
from app.features.priors_decay import get_priors_decay_engine
from app.features.confidence_calibration import (
    get_confidence_calibrator, ConfidenceComponents
)
from app.features.anchor_gating import get_anchor_strength_gate

logger = logging.getLogger(__name__)


class Phase2Integrator:
    """
    Coordinates Phase 2 enhancements.
    All operations are backward-compatible and can be toggled via feature flags.
    """
    
    # Feature flags (can be controlled via config or environment)
    FEATURE_FLAGS = {
        "enable_phase2_constraints": True,
        "enable_phase2_reconciliation": True,
        "enable_phase2_temporal_inertia": True,
        "enable_phase2_personal_baselines": True,
        "enable_phase2_multi_solver": True,
        "enable_phase2_priors_decay": True,
        "enable_phase2_confidence_calibration": True,
        "enable_phase2_anchor_gating": True
    }
    
    def __init__(self):
        """Initialize Phase 2 integrator."""
        # Initialize all engines
        self.lattice = get_constraint_lattice()
        self.reconciliation = get_reconciliation_engine()
        self.temporal = get_temporal_inertia_engine()
        self.baselines = get_personal_baseline_engine()
        self.multi_solver = get_multi_solver_engine()
        self.priors = get_priors_decay_engine()
        self.calibrator = get_confidence_calibrator()
        self.anchor_gate = get_anchor_strength_gate()
    
    @classmethod
    def set_feature_flag(cls, flag_name: str, enabled: bool):
        """Enable or disable a feature flag."""
        if flag_name in cls.FEATURE_FLAGS:
            cls.FEATURE_FLAGS[flag_name] = enabled
            logger.info(f"Feature flag {flag_name} set to {enabled}")
    
    def integrate_phase2(
        self,
        run_v2: RunV2,
        estimates: Dict[str, Dict[str, Any]],
        measured_anchors: Optional[Dict[str, float]] = None,
        historical_data: Optional[Dict[str, List[Tuple[datetime, float]]]] = None,
        events: Optional[List[TemporalEvent]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Apply all Phase 2 enhancements to estimates.
        
        Args:
            run_v2: Multi-specimen run
            estimates: Initial estimates from Phase 1 or solvers
            measured_anchors: Measured values (immutable)
            historical_data: Historical measurements for temporal/baseline analysis
            events: List of events (illness, meds changes, etc.)
            metadata: Additional metadata (age, sex, medications, etc.)
        
        Returns:
            Enhanced estimates with Phase 2 adjustments
        """
        measured_anchors = measured_anchors or {}
        historical_data = historical_data or {}
        events = events or []
        metadata = metadata or {}
        
        logger.info("=" * 60)
        logger.info("PHASE 2 INTEGRATION START")
        logger.info("=" * 60)
        
        # Start with estimates
        enhanced = estimates.copy()
        phase2_metadata = {}
        
        # ===== A2.1: Constraint Lattice Evaluation =====
        if self.FEATURE_FLAGS["enable_phase2_constraints"]:
            logger.info("Applying constraint lattice evaluation...")
            
            # Extract values for constraint checking
            all_values = {**measured_anchors}
            for marker, est in enhanced.items():
                if "center" in est:
                    all_values[marker] = est["center"]
                elif "value" in est:
                    all_values[marker] = est["value"]
            
            constraint_evals = self.lattice.evaluate_constraints(all_values, metadata)
            constraint_summary = self.lattice.summarize_evaluations(constraint_evals)
            
            phase2_metadata["constraint_evaluations"] = constraint_summary
            logger.info(f"Constraints: {constraint_summary['violated_constraints']} violations")
        
        # ===== A2.2: Cross-Domain Reconciliation =====
        if self.FEATURE_FLAGS["enable_phase2_reconciliation"]:
            logger.info("Applying cross-domain reconciliation...")
            
            reconciliation_result = self.reconciliation.reconcile_with_anchor_priority(
                estimates=enhanced,
                measured_anchors=measured_anchors,
                metadata=metadata
            )
            
            enhanced = reconciliation_result.reconciled_estimates
            phase2_metadata["reconciliation"] = reconciliation_result.to_dict()
            logger.info(
                f"Reconciliation: {reconciliation_result.range_adjustments_applied} adjustments"
            )
        
        # ===== A2.3: Temporal Inertia Enforcement =====
        if self.FEATURE_FLAGS["enable_phase2_temporal_inertia"] and historical_data:
            logger.info("Applying temporal inertia enforcement...")
            
            temporal_assessment = self.temporal.assess_temporal_coherence(
                current_estimates=enhanced,
                historical_values=historical_data,
                events=events
            )
            
            enhanced = self.temporal.apply_temporal_adjustments(
                estimates=enhanced,
                assessment=temporal_assessment
            )
            
            phase2_metadata["temporal_inertia"] = temporal_assessment.to_dict()
            logger.info(
                f"Temporal: {len(temporal_assessment.violations)} violations detected"
            )
        
        # ===== A2.4: Personal Baseline Modeling =====
        if self.FEATURE_FLAGS["enable_phase2_personal_baselines"] and historical_data:
            logger.info("Computing personal baselines...")
            
            baselines = self.baselines.compute_baselines_batch(
                historical_data=historical_data
            )
            
            # Compare current estimates to baselines
            baseline_comparisons = {}
            for marker, baseline in baselines.items():
                if marker in enhanced:
                    current_value = enhanced[marker].get("center") or enhanced[marker].get("value")
                    if current_value is not None:
                        comparison = self.baselines.compare_to_baseline(baseline, current_value)
                        baseline_comparisons[marker] = comparison
                        
                        # Add baseline metadata to estimate
                        enhanced[marker]["personal_baseline"] = baseline.to_dict()
                        enhanced[marker]["baseline_deviation"] = comparison["deviation"]
            
            phase2_metadata["personal_baselines"] = {
                "computed": len(baselines),
                "comparisons": baseline_comparisons
            }
            logger.info(f"Personal baselines: {len(baselines)} computed")
        
        # ===== A2.5: Multi-Solver Agreement =====
        if self.FEATURE_FLAGS["enable_phase2_multi_solver"]:
            logger.info("Computing multi-solver agreement...")
            
            # Extract available inputs
            inputs = {**measured_anchors}
            for marker, est in enhanced.items():
                if "center" in est:
                    inputs[marker] = est["center"]
            
            enhanced = self.multi_solver.apply_solver_agreement(
                estimates=enhanced,
                inputs=inputs,
                metadata=metadata
            )
            
            logger.info("Multi-solver agreement applied")
        
        # ===== B.6: Priors and Decay Logic =====
        if self.FEATURE_FLAGS["enable_phase2_priors_decay"]:
            logger.info("Applying priors and decay logic...")
            
            # Update posteriors with any new measurements
            for marker, value in measured_anchors.items():
                # Assume measurement uncertainty of 5% by default
                uncertainty = abs(value) * 0.05
                self.priors.update_posterior(
                    marker_name=marker,
                    measurement_value=value,
                    measurement_uncertainty=uncertainty
                )
            
            # Get prior status for all markers
            priors_status = self.priors.get_all_priors_status()
            phase2_metadata["priors_status"] = priors_status
            
            # For markers without direct measurements, incorporate priors
            for marker, est in enhanced.items():
                if marker not in measured_anchors:
                    prior = self.priors.get_prior(marker, apply_decay=True)
                    if prior:
                        # Blend estimate with decayed prior
                        # (More sophisticated blending could be done here)
                        est["prior_mean"] = prior.mean
                        est["prior_std"] = prior.std
                        est["prior_strength"] = prior.get_current_strength()
            
            logger.info(f"Priors: {len(priors_status)} priors available")
        
        # ===== B.7: Confidence Calibration =====
        if self.FEATURE_FLAGS["enable_phase2_confidence_calibration"]:
            logger.info("Calibrating confidence...")
            
            # Build confidence components for each estimate
            components_map = {}
            evidence_grades = {}
            
            for marker, est in enhanced.items():
                # Extract component values from Phase 2 metadata
                data_adequacy = 0.7  # Default, would compute from coverage
                anchor_strength_score = 0.5  # Default
                solver_agreement_score = 0.5  # Default
                temporal_stability_score = 0.5  # Default
                constraint_consistency_score = 0.5  # Default
                conflict_penalty = 0.0
                
                # Extract from metadata if available
                if "solver_agreement" in est:
                    solver_agreement_score = est["solver_agreement"].get("agreement_score", 0.5)
                
                if "temporal_inertia" in phase2_metadata:
                    stab_scores = phase2_metadata["temporal_inertia"].get("stability_scores", {})
                    if marker in stab_scores:
                        temporal_stability_score = stab_scores[marker]
                
                if "constraint_evaluations" in phase2_metadata:
                    violations = phase2_metadata["constraint_evaluations"].get("violated_constraints", 0)
                    constraint_consistency_score = max(0.3, 1.0 - (violations * 0.1))
                
                components = ConfidenceComponents(
                    data_adequacy=data_adequacy,
                    anchor_strength=anchor_strength_score,
                    solver_agreement=solver_agreement_score,
                    temporal_stability=temporal_stability_score,
                    constraint_consistency=constraint_consistency_score,
                    input_conflict_penalty=conflict_penalty
                )
                
                components_map[marker] = components
                
                # Determine evidence grade (default to B for inferred)
                evidence_grade = est.get("evidence_grade", EvidenceGrade.B)
                if isinstance(evidence_grade, str):
                    evidence_grade = EvidenceGrade(evidence_grade)
                evidence_grades[marker] = evidence_grade
            
            # Calibrate
            calibrated = self.calibrator.calibrate_batch(
                estimates=enhanced,
                components_map=components_map,
                evidence_grades=evidence_grades
            )
            
            enhanced = self.calibrator.apply_calibrated_confidence(
                estimates=enhanced,
                calibrated_map=calibrated
            )
            
            logger.info(f"Confidence calibrated for {len(calibrated)} estimates")
        
        # ===== B.8: Anchor Strength Gating =====
        if self.FEATURE_FLAGS["enable_phase2_anchor_gating"]:
            logger.info("Applying anchor strength gating...")
            
            # Build coverage and temporal info
            coverage_info = {}
            temporal_info = {}
            
            # Extract from historical data
            for marker, history in historical_data.items():
                if history:
                    # Simple coverage score based on data density
                    days_covered = len(set(t.date() for t, _ in history))
                    coverage_info[marker] = min(1.0, days_covered / 30.0)  # 30 days = full coverage
            
            # Get temporal stability from phase 2 metadata
            if "temporal_inertia" in phase2_metadata:
                temporal_info = phase2_metadata["temporal_inertia"].get("stability_scores", {})
            
            # Assess anchor strength for all markers
            markers_to_assess = list(enhanced.keys())
            assessments = self.anchor_gate.assess_batch(
                markers=markers_to_assess,
                available_data={**measured_anchors, **{k: v.get("center", 0) for k, v in enhanced.items()}},
                coverage_info=coverage_info,
                temporal_info=temporal_info
            )
            
            # Apply gating
            enhanced = self.anchor_gate.apply_anchor_gating(
                estimates=enhanced,
                assessments=assessments
            )
            
            phase2_metadata["anchor_gating"] = {
                marker: assessment.to_dict()
                for marker, assessment in assessments.items()
            }
            
            logger.info(f"Anchor gating: {len(enhanced)} outputs passed")
        
        logger.info("=" * 60)
        logger.info("PHASE 2 INTEGRATION COMPLETE")
        logger.info("=" * 60)
        
        return {
            "estimates": enhanced,
            "phase2_metadata": phase2_metadata
        }
    
    def get_phase2_summary(self, integration_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a summary of Phase 2 enhancements.
        
        Args:
            integration_result: Result from integrate_phase2
        
        Returns:
            Summary dictionary
        """
        metadata = integration_result.get("phase2_metadata", {})
        estimates = integration_result.get("estimates", {})
        
        summary = {
            "total_outputs": len(estimates),
            "constraint_violations": metadata.get("constraint_evaluations", {}).get("violated_constraints", 0),
            "reconciliation_adjustments": metadata.get("reconciliation", {}).get("range_adjustments_applied", 0),
            "temporal_violations": len(metadata.get("temporal_inertia", {}).get("violations", [])),
            "personal_baselines_computed": metadata.get("personal_baselines", {}).get("computed", 0),
            "priors_available": len(metadata.get("priors_status", {})),
            "anchor_gating_passed": len(metadata.get("anchor_gating", {}))
        }
        
        return summary


# Global instance
_global_phase2_integrator: Optional[Phase2Integrator] = None


def get_phase2_integrator() -> Phase2Integrator:
    """Get or create the global Phase 2 integrator instance."""
    global _global_phase2_integrator
    if _global_phase2_integrator is None:
        _global_phase2_integrator = Phase2Integrator()
    return _global_phase2_integrator
