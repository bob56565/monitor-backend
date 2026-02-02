"""
Multi-Solver Agreement System (Phase 2 - A2.5)

For every inferred output, runs multiple independent solvers and computes agreement.
Tightens ranges only when solvers converge; widens when they disagree.

Solver types:
- Deterministic (if applicable)
- Regularized covariance conditional estimator
- Latent factor state model
- Temporal model
- Constraint solver
"""

from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging
import statistics
import math

logger = logging.getLogger(__name__)


class SolverType(str, Enum):
    """Type of solver/estimator."""
    DETERMINISTIC = "deterministic"  # Direct calculation
    COVARIANCE_CONDITIONAL = "covariance_conditional"  # Regularized covariance
    LATENT_FACTOR = "latent_factor"  # Factor model
    TEMPORAL = "temporal"  # Time-series model
    CONSTRAINT = "constraint"  # Constraint satisfaction
    POPULATION_PRIOR = "population_prior"  # Prior-based


@dataclass
class SolverOutput:
    """
    Output from a single solver.
    """
    solver_type: SolverType
    estimate_center: float
    estimate_range: Optional[float] = None  # Uncertainty/width
    confidence: float = 0.5  # Solver's confidence in this estimate
    
    # Metadata
    inputs_used: List[str] = field(default_factory=list)
    notes: str = ""


@dataclass
class AgreementScore:
    """
    Agreement score across multiple solvers.
    """
    marker_name: str
    
    # Solver outputs
    solver_outputs: List[SolverOutput]
    solver_weights: Dict[SolverType, float]  # Weight given to each solver
    
    # Agreement metrics
    agreement_score: float  # 0-1, where 1 = perfect agreement
    convergence_flag: bool  # True if solvers converged
    
    # Consensus estimate
    consensus_center: float
    consensus_range: float
    
    # Adjustment factors
    tightening_factor: float  # <1.0 = tighten, 1.0 = no change
    widening_factor: float  # >1.0 = widen, 1.0 = no change
    
    # Metadata
    notes: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "marker": self.marker_name,
            "agreement_score": self.agreement_score,
            "convergence": self.convergence_flag,
            "consensus": {
                "center": self.consensus_center,
                "range": self.consensus_range
            },
            "tightening_factor": self.tightening_factor,
            "widening_factor": self.widening_factor,
            "solvers_used": [s.solver_type.value for s in self.solver_outputs],
            "notes": self.notes
        }


class MultiSolverEngine:
    """
    Runs multiple independent solvers and computes agreement.
    """
    
    def __init__(self):
        """Initialize multi-solver engine."""
        self.solvers: Dict[SolverType, Callable] = {}
        self._register_default_solvers()
    
    def _register_default_solvers(self):
        """Register default solvers."""
        # These are placeholder implementations
        # In production, would have full solver logic
        
        self.solvers[SolverType.DETERMINISTIC] = self._deterministic_solver
        self.solvers[SolverType.POPULATION_PRIOR] = self._population_prior_solver
        self.solvers[SolverType.COVARIANCE_CONDITIONAL] = self._covariance_solver
        self.solvers[SolverType.TEMPORAL] = self._temporal_solver
        
        logger.info(f"Registered {len(self.solvers)} solvers")
    
    def compute_agreement(
        self,
        marker_name: str,
        inputs: Dict[str, float],
        metadata: Optional[Dict[str, Any]] = None
    ) -> AgreementScore:
        """
        Compute multi-solver agreement for a marker.
        
        Args:
            marker_name: Marker to estimate
            inputs: Available input values
            metadata: Additional metadata
        
        Returns:
            AgreementScore with consensus and adjustment factors
        """
        metadata = metadata or {}
        
        # Run all applicable solvers
        solver_outputs: List[SolverOutput] = []
        
        for solver_type, solver_func in self.solvers.items():
            try:
                output = solver_func(marker_name, inputs, metadata)
                if output:
                    solver_outputs.append(output)
            except Exception as e:
                logger.warning(f"Solver {solver_type} failed for {marker_name}: {e}")
        
        if not solver_outputs:
            # No solvers produced output
            logger.warning(f"No solvers produced output for {marker_name}")
            return self._create_no_agreement_score(marker_name)
        
        # Compute agreement
        centers = [s.estimate_center for s in solver_outputs]
        
        # Agreement metrics
        if len(centers) == 1:
            agreement_score = 1.0  # Only one solver
            convergence = True
        else:
            # Compute coefficient of variation
            mean_center = statistics.mean(centers)
            if mean_center == 0:
                cv = 0.0
            else:
                stdev = statistics.stdev(centers) if len(centers) > 1 else 0.0
                cv = stdev / abs(mean_center)
            
            # Agreement score (inverse of CV, bounded)
            agreement_score = max(0.0, min(1.0, 1.0 - cv))
            convergence = cv < 0.15  # Converged if CV < 15%
        
        # Compute weighted consensus
        solver_weights = self._compute_solver_weights(solver_outputs)
        
        consensus_center = sum(
            s.estimate_center * solver_weights.get(s.solver_type, 1.0)
            for s in solver_outputs
        ) / sum(solver_weights.values())
        
        # Consensus range (weighted average of ranges)
        ranges = [s.estimate_range for s in solver_outputs if s.estimate_range]
        if ranges:
            consensus_range = sum(ranges) / len(ranges)
        else:
            # Default range based on agreement
            consensus_range = abs(consensus_center) * 0.20  # 20% of center
        
        # Compute adjustment factors
        if convergence and agreement_score > 0.7:
            # Good agreement: tighten slightly
            tightening_factor = 0.90  # 10% tighter
            widening_factor = 1.0
            notes = ["Solvers converged with high agreement"]
        elif agreement_score > 0.5:
            # Moderate agreement: no adjustment
            tightening_factor = 1.0
            widening_factor = 1.0
            notes = ["Solvers show moderate agreement"]
        else:
            # Poor agreement: widen
            tightening_factor = 1.0
            widening_factor = 1.0 + (1.0 - agreement_score) * 0.50  # Up to 50% wider
            notes = ["Solvers disagree; range widened"]
        
        return AgreementScore(
            marker_name=marker_name,
            solver_outputs=solver_outputs,
            solver_weights=solver_weights,
            agreement_score=agreement_score,
            convergence_flag=convergence,
            consensus_center=consensus_center,
            consensus_range=consensus_range,
            tightening_factor=tightening_factor,
            widening_factor=widening_factor,
            notes=notes
        )
    
    def _compute_solver_weights(
        self,
        solver_outputs: List[SolverOutput]
    ) -> Dict[SolverType, float]:
        """
        Compute weights for each solver based on confidence and type.
        """
        weights = {}
        
        # Base weights by solver type
        base_weights = {
            SolverType.DETERMINISTIC: 2.0,  # Highest weight
            SolverType.COVARIANCE_CONDITIONAL: 1.5,
            SolverType.LATENT_FACTOR: 1.3,
            SolverType.TEMPORAL: 1.2,
            SolverType.CONSTRAINT: 1.0,
            SolverType.POPULATION_PRIOR: 0.8  # Lowest weight
        }
        
        for output in solver_outputs:
            base_weight = base_weights.get(output.solver_type, 1.0)
            # Modulate by solver's own confidence
            weights[output.solver_type] = base_weight * output.confidence
        
        return weights
    
    def _create_no_agreement_score(self, marker_name: str) -> AgreementScore:
        """Create a default score when no solvers ran."""
        return AgreementScore(
            marker_name=marker_name,
            solver_outputs=[],
            solver_weights={},
            agreement_score=0.0,
            convergence_flag=False,
            consensus_center=0.0,
            consensus_range=0.0,
            tightening_factor=1.0,
            widening_factor=1.50,  # Wide by default
            notes=["No solvers produced output"]
        )
    
    # ===== PLACEHOLDER SOLVER IMPLEMENTATIONS =====
    # In production, these would be full implementations
    
    def _deterministic_solver(
        self,
        marker_name: str,
        inputs: Dict[str, float],
        metadata: Dict[str, Any]
    ) -> Optional[SolverOutput]:
        """
        Deterministic solver for directly calculable outputs.
        """
        # Example: eGFR from creatinine
        if marker_name == "egfr" and "creatinine" in inputs:
            creatinine = inputs["creatinine"]
            age = metadata.get("age", 40)
            sex = metadata.get("sex", "M")
            
            # Simplified CKD-EPI formula
            if sex == "F":
                egfr = 144 * (creatinine / 0.7) ** -0.329
            else:
                egfr = 141 * (creatinine / 0.9) ** -0.411
            
            # Age adjustment
            if age > 40:
                egfr *= 0.993 ** (age - 40)
            
            return SolverOutput(
                solver_type=SolverType.DETERMINISTIC,
                estimate_center=max(15, min(120, egfr)),
                estimate_range=5.0,  # Tight range for deterministic
                confidence=0.95,
                inputs_used=["creatinine", "age", "sex"],
                notes="CKD-EPI formula"
            )
        
        # No deterministic solver for this marker
        return None
    
    def _population_prior_solver(
        self,
        marker_name: str,
        inputs: Dict[str, float],
        metadata: Dict[str, Any]
    ) -> Optional[SolverOutput]:
        """
        Population prior-based solver (always produces output).
        """
        # Placeholder priors
        priors = {
            "glucose": (95.0, 15.0),  # (mean, std)
            "cholesterol": (190.0, 35.0),
            "ldl_cholesterol": (110.0, 30.0),
            "hdl_cholesterol": (55.0, 15.0),
            "triglycerides": (120.0, 50.0),
            "hemoglobin_a1c": (5.4, 0.5),
            "crp": (2.0, 3.0),
            "vitamin_d": (35.0, 15.0)
        }
        
        if marker_name not in priors:
            return None
        
        mean, std = priors[marker_name]
        
        return SolverOutput(
            solver_type=SolverType.POPULATION_PRIOR,
            estimate_center=mean,
            estimate_range=std * 2,  # ±1 std
            confidence=0.30,  # Low confidence in priors alone
            inputs_used=[],
            notes="Population prior"
        )
    
    def _covariance_solver(
        self,
        marker_name: str,
        inputs: Dict[str, float],
        metadata: Dict[str, Any]
    ) -> Optional[SolverOutput]:
        """
        Covariance-based conditional estimator.
        """
        # Placeholder: would use learned covariance matrices
        # For now, skip if no relevant inputs
        
        if not inputs:
            return None
        
        # Simple heuristic estimation
        # In production, would use actual covariance structure
        return None
    
    def _temporal_solver(
        self,
        marker_name: str,
        inputs: Dict[str, float],
        metadata: Dict[str, Any]
    ) -> Optional[SolverOutput]:
        """
        Temporal/time-series solver.
        """
        # Would use historical data and temporal models
        # Placeholder: skip for now
        return None
    
    def apply_solver_agreement(
        self,
        estimates: Dict[str, Dict[str, Any]],
        inputs: Dict[str, float],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Apply multi-solver agreement to all estimates.
        
        Args:
            estimates: Original estimates
            inputs: Available inputs
            metadata: Additional metadata
        
        Returns:
            Adjusted estimates with solver agreement applied
        """
        adjusted = {}
        
        for marker, estimate in estimates.items():
            # Compute agreement
            agreement = self.compute_agreement(marker, inputs, metadata)
            
            # Apply adjustments
            adj_estimate = estimate.copy()
            
            # Update center if we have consensus
            if agreement.convergence_flag and len(agreement.solver_outputs) > 1:
                adj_estimate["center"] = agreement.consensus_center
            
            # Adjust range
            if "range" in adj_estimate:
                if agreement.convergence_flag:
                    adj_estimate["range"] *= agreement.tightening_factor
                else:
                    adj_estimate["range"] *= agreement.widening_factor
            
            # Adjust confidence based on agreement
            if "confidence" in adj_estimate:
                adj_estimate["confidence"] *= (0.8 + 0.2 * agreement.agreement_score)
            
            # Add solver metadata
            adj_estimate["solver_agreement"] = agreement.to_dict()
            
            adjusted[marker] = adj_estimate
        
        return adjusted


# Global instance
_global_multi_solver_engine: Optional[MultiSolverEngine] = None


def get_multi_solver_engine() -> MultiSolverEngine:
    """Get or create the global multi-solver engine instance."""
    global _global_multi_solver_engine
    if _global_multi_solver_engine is None:
        _global_multi_solver_engine = MultiSolverEngine()
    return _global_multi_solver_engine
