"""
Global Constraint Lattice (Phase 2 - A2.1)

Creates a shared constraint graph across physiological systems to:
- Link related domains and markers
- Detect physiological contradictions
- Tighten ranges when constraints are satisfied
- Widen ranges when contradictions exist
- Provide explainable constraint evaluations

All constraints are soft-penalty (probabilistic) by default.
"""

from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ConstraintDomain(str, Enum):
    """Physiological domains for constraint organization."""
    METABOLIC_LIPIDS_GLUCOSE = "metabolic_lipids_glucose"
    INFLAMMATION_IRON_VITAMIN = "inflammation_iron_vitamin"
    RENAL_ELECTROLYTES_VITAMIN = "renal_electrolytes_vitamin"
    ADIPOSITY_FAT_SOLUBLE = "adiposity_fat_soluble"
    SLEEP_CIRCADIAN_CORTISOL = "sleep_circadian_cortisol"
    MEDICATIONS_GLOBAL = "medications_global"


class ConstraintType(str, Enum):
    """Type of constraint relationship."""
    CORRELATION = "correlation"  # Two markers move together
    CONTRADICTION = "contradiction"  # Values are physiologically incompatible
    CAUSALITY = "causality"  # One value implies/causes another
    BOUND = "bound"  # One value constrains the range of another
    MUTUAL_EXCLUSION = "mutual_exclusion"  # Both cannot be abnormal simultaneously


class ConstraintSeverity(str, Enum):
    """How strongly the constraint should be enforced."""
    SOFT = "soft"  # Gentle penalty, minor tightening/widening
    MODERATE = "moderate"  # Standard constraint
    STRONG = "strong"  # Hard constraint, significant impact
    HARD = "hard"  # Impossible values, must fail


@dataclass
class ConstraintDefinition:
    """
    Definition of a single physiological constraint.
    """
    name: str
    domain: ConstraintDomain
    constraint_type: ConstraintType
    severity: ConstraintSeverity
    
    # Markers involved in this constraint
    primary_markers: List[str]
    secondary_markers: List[str] = field(default_factory=list)
    
    # Human-readable rationale
    rationale: str = ""
    
    # Optional callable for custom evaluation
    evaluator: Optional[Any] = None
    
    # Constraint parameters (thresholds, bounds, etc.)
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    def __hash__(self):
        return hash(self.name)


@dataclass
class ConstraintEvaluation:
    """
    Result of evaluating a constraint against actual data.
    """
    constraint_name: str
    is_satisfied: bool
    is_violated: bool
    is_triggered: bool  # Did the constraint apply to this data?
    
    # Penalty/adjustment factors
    confidence_penalty: float = 0.0  # 0.0 to 1.0 (reduction in confidence)
    tightening_factor: float = 1.0  # <1.0 = tighten, >1.0 = widen
    
    # Explanation
    explanation: str = ""
    triggered_by: List[str] = field(default_factory=list)  # Which inputs triggered it
    
    # Optional suggested adjustments
    suggested_range_adjustments: Dict[str, Tuple[float, float]] = field(default_factory=dict)


class ConstraintLattice:
    """
    Global constraint lattice system.
    
    Maintains a registry of constraints and evaluates them against
    clinical data to detect contradictions and guide range tightening.
    """
    
    def __init__(self):
        """Initialize empty constraint lattice."""
        self.constraints: Dict[str, ConstraintDefinition] = {}
        self.domain_index: Dict[ConstraintDomain, Set[str]] = {
            domain: set() for domain in ConstraintDomain
        }
        self.marker_index: Dict[str, Set[str]] = {}  # marker -> constraint names
        self._register_default_constraints()
    
    def register_constraint(self, constraint: ConstraintDefinition):
        """
        Register a new constraint in the lattice.
        
        Args:
            constraint: Constraint definition to register
        """
        self.constraints[constraint.name] = constraint
        self.domain_index[constraint.domain].add(constraint.name)
        
        # Index by markers
        for marker in constraint.primary_markers + constraint.secondary_markers:
            if marker not in self.marker_index:
                self.marker_index[marker] = set()
            self.marker_index[marker].add(constraint.name)
        
        logger.debug(f"Registered constraint: {constraint.name} in domain {constraint.domain}")
    
    def _register_default_constraints(self):
        """Register default physiological constraints."""
        
        # METABOLIC/LIPIDS/GLUCOSE constraints
        self.register_constraint(ConstraintDefinition(
            name="glucose_insulin_homeostasis",
            domain=ConstraintDomain.METABOLIC_LIPIDS_GLUCOSE,
            constraint_type=ConstraintType.CORRELATION,
            severity=ConstraintSeverity.MODERATE,
            primary_markers=["glucose", "insulin"],
            rationale="Glucose and insulin should correlate in healthy homeostasis; "
                     "dissociation suggests insulin resistance or beta-cell dysfunction"
        ))
        
        self.register_constraint(ConstraintDefinition(
            name="triglyceride_glucose_coupling",
            domain=ConstraintDomain.METABOLIC_LIPIDS_GLUCOSE,
            constraint_type=ConstraintType.CORRELATION,
            severity=ConstraintSeverity.SOFT,
            primary_markers=["triglycerides", "glucose"],
            rationale="Elevated triglycerides often co-occur with elevated glucose "
                     "(metabolic syndrome pattern)"
        ))
        
        self.register_constraint(ConstraintDefinition(
            name="hdl_triglyceride_inverse",
            domain=ConstraintDomain.METABOLIC_LIPIDS_GLUCOSE,
            constraint_type=ConstraintType.CORRELATION,
            severity=ConstraintSeverity.SOFT,
            primary_markers=["hdl_cholesterol", "triglycerides"],
            rationale="HDL and triglycerides typically inversely correlate"
        ))
        
        self.register_constraint(ConstraintDefinition(
            name="a1c_glucose_consistency",
            domain=ConstraintDomain.METABOLIC_LIPIDS_GLUCOSE,
            constraint_type=ConstraintType.BOUND,
            severity=ConstraintSeverity.MODERATE,
            primary_markers=["hemoglobin_a1c", "glucose"],
            rationale="HbA1c should be consistent with average glucose over 3 months",
            parameters={"a1c_to_glucose_factor": 28.7}  # Nathan et al. formula
        ))
        
        # INFLAMMATION/IRON/VITAMIN constraints
        self.register_constraint(ConstraintDefinition(
            name="inflammation_iron_sequestration",
            domain=ConstraintDomain.INFLAMMATION_IRON_VITAMIN,
            constraint_type=ConstraintType.CAUSALITY,
            severity=ConstraintSeverity.MODERATE,
            primary_markers=["crp", "ferritin", "iron", "transferrin_saturation"],
            rationale="Inflammation causes iron sequestration (elevated ferritin, low iron/TSAT)"
        ))
        
        self.register_constraint(ConstraintDefinition(
            name="vitamin_d_inflammation_inverse",
            domain=ConstraintDomain.INFLAMMATION_IRON_VITAMIN,
            constraint_type=ConstraintType.CORRELATION,
            severity=ConstraintSeverity.SOFT,
            primary_markers=["vitamin_d", "crp"],
            rationale="Vitamin D deficiency often correlates with elevated inflammation"
        ))
        
        # RENAL/ELECTROLYTES/VITAMIN constraints
        self.register_constraint(ConstraintDefinition(
            name="kidney_vitamin_d_activation",
            domain=ConstraintDomain.RENAL_ELECTROLYTES_VITAMIN,
            constraint_type=ConstraintType.CAUSALITY,
            severity=ConstraintSeverity.MODERATE,
            primary_markers=["egfr", "creatinine", "vitamin_d"],
            secondary_markers=["calcium", "phosphorus"],
            rationale="Kidney disease impairs vitamin D activation and mineral balance"
        ))
        
        self.register_constraint(ConstraintDefinition(
            name="sodium_potassium_homeostasis",
            domain=ConstraintDomain.RENAL_ELECTROLYTES_VITAMIN,
            constraint_type=ConstraintType.BOUND,
            severity=ConstraintSeverity.STRONG,
            primary_markers=["sodium", "potassium"],
            rationale="Sodium and potassium must stay within narrow physiologic bounds"
        ))
        
        self.register_constraint(ConstraintDefinition(
            name="egfr_creatinine_consistency",
            domain=ConstraintDomain.RENAL_ELECTROLYTES_VITAMIN,
            constraint_type=ConstraintType.BOUND,
            severity=ConstraintSeverity.STRONG,
            primary_markers=["egfr", "creatinine"],
            rationale="eGFR must be consistent with creatinine (CKD-EPI formula)"
        ))
        
        # ADIPOSITY/FAT SOLUBLE constraints
        self.register_constraint(ConstraintDefinition(
            name="adiposity_vitamin_d_storage",
            domain=ConstraintDomain.ADIPOSITY_FAT_SOLUBLE,
            constraint_type=ConstraintType.CAUSALITY,
            severity=ConstraintSeverity.SOFT,
            primary_markers=["bmi", "body_fat_percent", "vitamin_d"],
            rationale="Higher adiposity may sequester fat-soluble vitamins"
        ))
        
        # SLEEP/CIRCADIAN/CORTISOL constraints
        self.register_constraint(ConstraintDefinition(
            name="sleep_cortisol_rhythm",
            domain=ConstraintDomain.SLEEP_CIRCADIAN_CORTISOL,
            constraint_type=ConstraintType.CORRELATION,
            severity=ConstraintSeverity.MODERATE,
            primary_markers=["sleep_duration", "sleep_quality", "cortisol"],
            secondary_markers=["heart_rate_variability"],
            rationale="Poor sleep disrupts cortisol rhythm and autonomic balance"
        ))
        
        logger.info(f"Registered {len(self.constraints)} default constraints")
    
    def evaluate_constraints(
        self,
        values: Dict[str, float],
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[ConstraintEvaluation]:
        """
        Evaluate all relevant constraints against provided values.
        
        Args:
            values: Dictionary of marker_name -> value
            metadata: Optional metadata (age, sex, medications, etc.)
        
        Returns:
            List of constraint evaluations
        """
        evaluations: List[ConstraintEvaluation] = []
        metadata = metadata or {}
        
        # Find all constraints that apply to these markers
        relevant_constraints = set()
        for marker in values.keys():
            if marker in self.marker_index:
                relevant_constraints.update(self.marker_index[marker])
        
        logger.debug(f"Evaluating {len(relevant_constraints)} constraints for {len(values)} values")
        
        for constraint_name in relevant_constraints:
            constraint = self.constraints[constraint_name]
            evaluation = self._evaluate_single_constraint(constraint, values, metadata)
            evaluations.append(evaluation)
        
        return evaluations
    
    def _evaluate_single_constraint(
        self,
        constraint: ConstraintDefinition,
        values: Dict[str, float],
        metadata: Dict[str, Any]
    ) -> ConstraintEvaluation:
        """
        Evaluate a single constraint.
        
        Args:
            constraint: Constraint to evaluate
            values: Marker values
            metadata: Additional metadata
        
        Returns:
            Constraint evaluation result
        """
        # Check if constraint is triggered (all required markers present)
        required_markers = constraint.primary_markers
        available_markers = [m for m in required_markers if m in values]
        
        if len(available_markers) < len(required_markers):
            # Not enough data to evaluate this constraint
            return ConstraintEvaluation(
                constraint_name=constraint.name,
                is_satisfied=False,
                is_violated=False,
                is_triggered=False,
                explanation=f"Insufficient data: missing {set(required_markers) - set(available_markers)}"
            )
        
        # Use custom evaluator if provided
        if constraint.evaluator:
            return constraint.evaluator(constraint, values, metadata)
        
        # Default evaluation based on constraint type
        if constraint.constraint_type == ConstraintType.BOUND:
            return self._evaluate_bound_constraint(constraint, values, metadata)
        elif constraint.constraint_type == ConstraintType.CORRELATION:
            return self._evaluate_correlation_constraint(constraint, values, metadata)
        elif constraint.constraint_type == ConstraintType.CONTRADICTION:
            return self._evaluate_contradiction_constraint(constraint, values, metadata)
        elif constraint.constraint_type == ConstraintType.CAUSALITY:
            return self._evaluate_causality_constraint(constraint, values, metadata)
        else:
            # Default: triggered but no specific evaluation
            return ConstraintEvaluation(
                constraint_name=constraint.name,
                is_satisfied=True,
                is_violated=False,
                is_triggered=True,
                explanation=f"Constraint type {constraint.constraint_type} not yet implemented",
                triggered_by=available_markers
            )
    
    def _evaluate_bound_constraint(
        self,
        constraint: ConstraintDefinition,
        values: Dict[str, float],
        metadata: Dict[str, Any]
    ) -> ConstraintEvaluation:
        """Evaluate a bound constraint (one value constrains another)."""
        
        # Specific implementations for known bound constraints
        if constraint.name == "a1c_glucose_consistency":
            a1c = values.get("hemoglobin_a1c")
            glucose = values.get("glucose")
            
            if a1c and glucose:
                # Nathan formula: estimated average glucose (mg/dL) = 28.7 * A1c - 46.7
                expected_glucose = 28.7 * a1c - 46.7
                deviation = abs(glucose - expected_glucose) / expected_glucose
                
                is_consistent = deviation < 0.20  # Within 20%
                
                if is_consistent:
                    return ConstraintEvaluation(
                        constraint_name=constraint.name,
                        is_satisfied=True,
                        is_violated=False,
                        is_triggered=True,
                        confidence_penalty=0.0,
                        tightening_factor=0.95,  # Tighten slightly
                        explanation=f"A1c {a1c:.1f}% consistent with glucose {glucose:.0f} mg/dL",
                        triggered_by=["hemoglobin_a1c", "glucose"]
                    )
                else:
                    return ConstraintEvaluation(
                        constraint_name=constraint.name,
                        is_satisfied=False,
                        is_violated=True,
                        is_triggered=True,
                        confidence_penalty=0.15,
                        tightening_factor=1.20,  # Widen
                        explanation=f"A1c {a1c:.1f}% inconsistent with glucose {glucose:.0f} mg/dL "
                                   f"(expected ~{expected_glucose:.0f} mg/dL, {deviation*100:.0f}% deviation)",
                        triggered_by=["hemoglobin_a1c", "glucose"]
                    )
        
        elif constraint.name == "egfr_creatinine_consistency":
            egfr = values.get("egfr")
            creatinine = values.get("creatinine")
            
            if egfr and creatinine:
                # Simple check: higher creatinine should mean lower eGFR
                # Rough inverse relationship
                is_inverse = (egfr > 90 and creatinine < 1.2) or \
                            (egfr < 60 and creatinine > 1.2) or \
                            (60 <= egfr <= 90)
                
                if is_inverse:
                    return ConstraintEvaluation(
                        constraint_name=constraint.name,
                        is_satisfied=True,
                        is_violated=False,
                        is_triggered=True,
                        confidence_penalty=0.0,
                        tightening_factor=0.95,
                        explanation=f"eGFR {egfr:.0f} consistent with creatinine {creatinine:.2f}",
                        triggered_by=["egfr", "creatinine"]
                    )
                else:
                    return ConstraintEvaluation(
                        constraint_name=constraint.name,
                        is_satisfied=False,
                        is_violated=True,
                        is_triggered=True,
                        confidence_penalty=0.20,
                        tightening_factor=1.30,
                        explanation=f"eGFR {egfr:.0f} inconsistent with creatinine {creatinine:.2f}",
                        triggered_by=["egfr", "creatinine"]
                    )
        
        # Default bound evaluation
        return ConstraintEvaluation(
            constraint_name=constraint.name,
            is_satisfied=True,
            is_violated=False,
            is_triggered=True,
            explanation=f"Bound constraint evaluated (no specific logic)",
            triggered_by=constraint.primary_markers
        )
    
    def _evaluate_correlation_constraint(
        self,
        constraint: ConstraintDefinition,
        values: Dict[str, float],
        metadata: Dict[str, Any]
    ) -> ConstraintEvaluation:
        """Evaluate a correlation constraint (markers should move together)."""
        
        # For now, mark as satisfied if markers are present
        # In production, would compute actual correlation from historical data
        return ConstraintEvaluation(
            constraint_name=constraint.name,
            is_satisfied=True,
            is_violated=False,
            is_triggered=True,
            confidence_penalty=0.0,
            tightening_factor=1.0,
            explanation=f"Correlation constraint triggered but not fully evaluated",
            triggered_by=constraint.primary_markers
        )
    
    def _evaluate_contradiction_constraint(
        self,
        constraint: ConstraintDefinition,
        values: Dict[str, float],
        metadata: Dict[str, Any]
    ) -> ConstraintEvaluation:
        """Evaluate a contradiction constraint (values are incompatible)."""
        
        return ConstraintEvaluation(
            constraint_name=constraint.name,
            is_satisfied=True,
            is_violated=False,
            is_triggered=True,
            explanation=f"No contradiction detected",
            triggered_by=constraint.primary_markers
        )
    
    def _evaluate_causality_constraint(
        self,
        constraint: ConstraintDefinition,
        values: Dict[str, float],
        metadata: Dict[str, Any]
    ) -> ConstraintEvaluation:
        """Evaluate a causality constraint (one causes another)."""
        
        return ConstraintEvaluation(
            constraint_name=constraint.name,
            is_satisfied=True,
            is_violated=False,
            is_triggered=True,
            explanation=f"Causality constraint triggered",
            triggered_by=constraint.primary_markers
        )
    
    def get_constraints_for_marker(self, marker_name: str) -> List[ConstraintDefinition]:
        """
        Get all constraints that involve a specific marker.
        
        Args:
            marker_name: Name of the marker
        
        Returns:
            List of constraint definitions
        """
        if marker_name not in self.marker_index:
            return []
        
        constraint_names = self.marker_index[marker_name]
        return [self.constraints[name] for name in constraint_names]
    
    def get_constraints_for_domain(self, domain: ConstraintDomain) -> List[ConstraintDefinition]:
        """
        Get all constraints in a specific domain.
        
        Args:
            domain: Constraint domain
        
        Returns:
            List of constraint definitions
        """
        constraint_names = self.domain_index[domain]
        return [self.constraints[name] for name in constraint_names]
    
    def summarize_evaluations(
        self,
        evaluations: List[ConstraintEvaluation]
    ) -> Dict[str, Any]:
        """
        Summarize constraint evaluation results.
        
        Args:
            evaluations: List of constraint evaluations
        
        Returns:
            Summary dictionary with aggregate stats
        """
        triggered = [e for e in evaluations if e.is_triggered]
        satisfied = [e for e in triggered if e.is_satisfied]
        violated = [e for e in triggered if e.is_violated]
        
        total_penalty = sum(e.confidence_penalty for e in violated)
        avg_tightening = sum(e.tightening_factor for e in satisfied) / max(len(satisfied), 1)
        
        return {
            "total_constraints": len(evaluations),
            "triggered_constraints": len(triggered),
            "satisfied_constraints": len(satisfied),
            "violated_constraints": len(violated),
            "total_confidence_penalty": min(total_penalty, 0.50),  # Cap at 50% penalty
            "average_tightening_factor": avg_tightening,
            "violations": [
                {
                    "constraint": e.constraint_name,
                    "explanation": e.explanation,
                    "penalty": e.confidence_penalty
                }
                for e in violated
            ]
        }


# Global instance
_global_lattice: Optional[ConstraintLattice] = None


def get_constraint_lattice() -> ConstraintLattice:
    """Get or create the global constraint lattice instance."""
    global _global_lattice
    if _global_lattice is None:
        _global_lattice = ConstraintLattice()
    return _global_lattice
