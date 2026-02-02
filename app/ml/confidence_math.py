"""
Confidence Math for Inference V2.

Computes confidence incorporating:
- Completeness (missingness inverse)
- Coherence scores
- Agreement (disagreement inverse)
- Stability (temporal)
- Signal quality
- Interference penalties
"""

from typing import Dict, Optional
from dataclasses import dataclass


@dataclass
class ConfidenceComponents:
    """Individual components of confidence computation."""
    completeness_score: float  # 0-1: 1 - normalized_missingness
    coherence_score: float  # 0-1: from feature_pack_v2
    agreement_score: float  # 0-1: 1 - disagreement_score
    stability_score: float  # 0-1: temporal consistency
    signal_quality_score: float  # 0-1: sensor/artifact quality
    interference_penalty: float  # 0-1: penalty from artifacts/meds


class ConfidenceMath:
    """
    Confidence formula combining multiple components.
    """
    
    # Default weights (must sum to ~1.0)
    DEFAULT_WEIGHTS = {
        "completeness": 0.22,
        "coherence": 0.22,
        "agreement": 0.20,
        "stability": 0.16,
        "signal_quality": 0.12,
    }
    
    @staticmethod
    def compute_confidence(
        components: ConfidenceComponents,
        weights: Optional[Dict[str, float]] = None,
        penalty_factor: float = 1.0,
    ) -> float:
        """
        Compute overall confidence from components.
        
        Formula:
            confidence = clamp(
                sum(w_i * component_i) - interference_penalty * penalty_factor,
                0, 1
            )
        
        Args:
            components: ConfidenceComponents with all scores 0-1
            weights: Custom weights (default: DEFAULT_WEIGHTS)
            penalty_factor: Multiplier for interference penalty (default: 1.0)
        
        Returns:
            confidence_0_1: Overall confidence score
        """
        if weights is None:
            weights = ConfidenceMath.DEFAULT_WEIGHTS
        
        # Weighted sum of components
        weighted_sum = (
            weights.get("completeness", 0.22) * components.completeness_score +
            weights.get("coherence", 0.22) * components.coherence_score +
            weights.get("agreement", 0.20) * components.agreement_score +
            weights.get("stability", 0.16) * components.stability_score +
            weights.get("signal_quality", 0.12) * components.signal_quality_score
        )
        
        # Apply interference penalty
        final_confidence = weighted_sum - (components.interference_penalty * penalty_factor)
        
        # Clamp to [0, 1]
        final_confidence = max(0.0, min(1.0, final_confidence))
        
        return final_confidence
    
    @staticmethod
    def compute_completeness_score(
        domain_missingness_score: float,
    ) -> float:
        """
        Completeness = 1 - normalized_missingness.
        
        Args:
            domain_missingness_score: 0-1, where 0=all present, 1=all missing
        
        Returns:
            0-1 completeness score
        """
        return 1.0 - domain_missingness_score
    
    @staticmethod
    def compute_agreement_score(
        disagreement_score: float,
    ) -> float:
        """
        Agreement = 1 - disagreement_score.
        
        Args:
            disagreement_score: 0-1 from multi-engine consensus
        
        Returns:
            0-1 agreement score
        """
        return 1.0 - disagreement_score
    
    @staticmethod
    def compute_stability_score(
        volatility_metric: float,
        regime_consistency: bool = True,
    ) -> float:
        """
        Stability from temporal features.
        
        Args:
            volatility_metric: 0-1, where 0=stable, 1=highly volatile
            regime_consistency: Whether regime is consistent
        
        Returns:
            0-1 stability score
        """
        stability = 1.0 - volatility_metric
        
        if not regime_consistency:
            stability *= 0.85  # Penalize for regime changes
        
        return max(0.0, min(1.0, stability))
    
    @staticmethod
    def should_widen_range(
        disagreement_score: float,
        coherence_score: float,
        completeness_score: float,
        threshold_disagreement: float = 0.45,
        threshold_coherence: float = 0.55,
        threshold_completeness: float = 0.40,
    ) -> tuple[bool, Optional[float]]:
        """
        Determine if confidence range should be widened.
        
        Returns:
            (should_widen: bool, widening_factor: float|None)
        """
        widening_factor = None
        
        # Disagreement widening
        if disagreement_score > threshold_disagreement:
            widening_factor = 1.25  # 25% wider
        
        # Coherence-driven widening
        if coherence_score < threshold_coherence:
            widening_factor = 1.40  # 40% wider
        
        # Completeness-driven suppression (severe)
        if completeness_score < threshold_completeness:
            return True, 1.40  # Widen significantly
        
        return (widening_factor is not None), widening_factor
    
    @staticmethod
    def compute_from_feature_pack_v2(
        feature_pack_v2: dict,
        domain: str = "metabolic",
    ) -> ConfidenceComponents:
        """
        Extract confidence components from feature_pack_v2.
        
        Args:
            feature_pack_v2: Dictionary with feature_pack_v2 data
            domain: Domain name for aggregation
        
        Returns:
            ConfidenceComponents with all scores
        """
        # Completeness from missingness
        domain_missingness = feature_pack_v2.get(
            "missingness_feature_vector", {}
        ).get("domain_missingness_scores", {}).get(domain, 0.5)
        completeness = ConfidenceMath.compute_completeness_score(domain_missingness)
        
        # Coherence from coherence_scores
        domain_coherence = feature_pack_v2.get(
            "coherence_scores", {}
        ).get("domain_coherence_map", {}).get(domain, 0.75)
        
        # Agreement from consensus (stub: assume 0.8 if not available)
        agreement = 0.8
        
        # Stability from temporal features (stub)
        stability = 0.80
        
        # Signal quality (stub)
        signal_quality = 0.85
        
        # Interference penalty (stub)
        interference = 0.05
        
        return ConfidenceComponents(
            completeness_score=completeness,
            coherence_score=domain_coherence,
            agreement_score=agreement,
            stability_score=stability,
            signal_quality_score=signal_quality,
            interference_penalty=interference,
        )
