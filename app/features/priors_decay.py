"""
Population Priors and Decay Logic (Phase 2 - B.6)

Uses population priors + uploaded labs as priors that decay by marker half-life.
Re-strengthens when longitudinal stability confirms patterns.

Features:
- Prior distribution store per marker/state
- Half-life registry per marker/state  
- Prior decay engine (exponential decay)
- Stability reinforcement engine
- Posterior updates when new measurements arrive
"""

from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import logging
import math

logger = logging.getLogger(__name__)


@dataclass
class PriorDistribution:
    """
    Prior distribution for a marker or state.
    """
    marker_name: str
    
    # Distribution parameters
    mean: float
    std: float  # Standard deviation
    
    # Source of prior
    source: str  # "population", "lab_measurement", "inferred_stable"
    
    # Temporal metadata
    established_at: datetime
    last_measurement_date: Optional[datetime] = None
    
    # Decay parameters
    half_life_days: float = 90.0  # Default 90 days
    
    def get_current_strength(self, current_time: Optional[datetime] = None) -> float:
        """
        Get current strength of prior after decay.
        
        Returns:
            Strength (0-1), where 1 = full strength, 0 = completely decayed
        """
        current_time = current_time or datetime.utcnow()
        
        # Time since establishment
        if self.last_measurement_date:
            reference_time = self.last_measurement_date
        else:
            reference_time = self.established_at
        
        days_elapsed = (current_time - reference_time).total_seconds() / 86400.0
        
        if days_elapsed <= 0:
            return 1.0
        
        # Exponential decay based on half-life
        strength = math.exp(-math.log(2) * days_elapsed / self.half_life_days)
        return max(0.01, min(1.0, strength))  # Clamp to [0.01, 1.0]
    
    def get_decayed_distribution(
        self,
        current_time: Optional[datetime] = None
    ) -> Tuple[float, float]:
        """
        Get distribution parameters after decay.
        
        Returns:
            (mean, std) with decayed confidence (wider std as decay occurs)
        """
        strength = self.get_current_strength(current_time)
        
        # As prior weakens, increase uncertainty
        # std grows as strength decreases
        decayed_std = self.std / math.sqrt(strength) if strength > 0.01 else self.std * 10
        
        return (self.mean, decayed_std)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "marker": self.marker_name,
            "mean": self.mean,
            "std": self.std,
            "source": self.source,
            "established_at": self.established_at.isoformat(),
            "last_measurement": self.last_measurement_date.isoformat() if self.last_measurement_date else None,
            "half_life_days": self.half_life_days,
            "current_strength": self.get_current_strength()
        }


class HalfLifeRegistry:
    """
    Registry of half-lives for different markers and states.
    """
    
    # Default half-lives in days
    DEFAULT_HALF_LIVES = {
        # FAST markers (short half-life)
        "glucose": 0.1,  # Hours
        "insulin": 0.05,  # Very short
        "heart_rate": 0.5,
        
        # MODERATE markers (days to weeks)
        "crp": 14,
        "iron": 21,
        "ferritin": 30,
        "triglycerides": 7,
        
        # SLOW markers (weeks to months)
        "hemoglobin_a1c": 90,  # 3 months (RBC lifespan)
        "vitamin_d": 60,  # 2 months
        "vitamin_b12": 120,  # 4 months
        "ldl_cholesterol": 30,
        "hdl_cholesterol": 30,
        "total_cholesterol": 30,
        
        # VERY SLOW markers (months)
        "creatinine": 180,  # 6 months (kidney function changes slowly)
        "egfr": 180,
        "bone_markers": 90
    }
    
    def __init__(self):
        """Initialize half-life registry."""
        self.half_lives = self.DEFAULT_HALF_LIVES.copy()
    
    def get_half_life(self, marker_name: str) -> float:
        """
        Get half-life for a marker.
        
        Args:
            marker_name: Name of marker
        
        Returns:
            Half-life in days (default 90 if not found)
        """
        return self.half_lives.get(marker_name, 90.0)
    
    def set_half_life(self, marker_name: str, half_life_days: float):
        """Set custom half-life for a marker."""
        self.half_lives[marker_name] = half_life_days


class PriorsDecayEngine:
    """
    Manages population priors and their decay over time.
    Handles posterior updates when new measurements arrive.
    """
    
    def __init__(self):
        """Initialize priors decay engine."""
        self.half_life_registry = HalfLifeRegistry()
        self.priors: Dict[str, PriorDistribution] = {}
        self._initialize_population_priors()
    
    def _initialize_population_priors(self):
        """Initialize default population priors."""
        # These are placeholder values
        # In production, would load from NHANES/MIMIC data
        
        population_priors = {
            "glucose": (95.0, 15.0),
            "hemoglobin_a1c": (5.4, 0.5),
            "total_cholesterol": (190.0, 35.0),
            "ldl_cholesterol": (110.0, 30.0),
            "hdl_cholesterol": (55.0, 15.0),
            "triglycerides": (120.0, 50.0),
            "crp": (2.0, 3.0),
            "vitamin_d": (35.0, 15.0),
            "vitamin_b12": (500.0, 200.0),
            "iron": (80.0, 30.0),
            "ferritin": (100.0, 80.0),
            "creatinine": (1.0, 0.25),
            "egfr": (90.0, 20.0)
        }
        
        for marker, (mean, std) in population_priors.items():
            self.set_prior(
                marker_name=marker,
                mean=mean,
                std=std,
                source="population",
                half_life_days=self.half_life_registry.get_half_life(marker)
            )
        
        logger.info(f"Initialized {len(self.priors)} population priors")
    
    def set_prior(
        self,
        marker_name: str,
        mean: float,
        std: float,
        source: str = "population",
        established_at: Optional[datetime] = None,
        last_measurement_date: Optional[datetime] = None,
        half_life_days: Optional[float] = None
    ):
        """
        Set or update a prior for a marker.
        
        Args:
            marker_name: Name of marker
            mean: Prior mean
            std: Prior standard deviation
            source: Source of prior ("population", "lab_measurement", etc.)
            established_at: When prior was established
            last_measurement_date: Date of last measurement
            half_life_days: Custom half-life (optional)
        """
        established_at = established_at or datetime.utcnow()
        
        if half_life_days is None:
            half_life_days = self.half_life_registry.get_half_life(marker_name)
        
        prior = PriorDistribution(
            marker_name=marker_name,
            mean=mean,
            std=std,
            source=source,
            established_at=established_at,
            last_measurement_date=last_measurement_date,
            half_life_days=half_life_days
        )
        
        self.priors[marker_name] = prior
        logger.debug(f"Set prior for {marker_name}: mean={mean:.1f}, std={std:.1f}, source={source}")
    
    def get_prior(
        self,
        marker_name: str,
        apply_decay: bool = True,
        current_time: Optional[datetime] = None
    ) -> Optional[PriorDistribution]:
        """
        Get prior for a marker.
        
        Args:
            marker_name: Name of marker
            apply_decay: Whether to apply decay
            current_time: Current time (for decay calculation)
        
        Returns:
            PriorDistribution or None if not found
        """
        if marker_name not in self.priors:
            return None
        
        prior = self.priors[marker_name]
        
        if not apply_decay:
            return prior
        
        # Return a copy with decayed parameters
        decayed_mean, decayed_std = prior.get_decayed_distribution(current_time)
        
        return PriorDistribution(
            marker_name=marker_name,
            mean=decayed_mean,
            std=decayed_std,
            source=prior.source,
            established_at=prior.established_at,
            last_measurement_date=prior.last_measurement_date,
            half_life_days=prior.half_life_days
        )
    
    def update_posterior(
        self,
        marker_name: str,
        measurement_value: float,
        measurement_uncertainty: float,
        measurement_date: Optional[datetime] = None
    ) -> PriorDistribution:
        """
        Update prior with new measurement (Bayesian update).
        
        Args:
            marker_name: Name of marker
            measurement_value: Measured value
            measurement_uncertainty: Measurement uncertainty (std)
            measurement_date: Date of measurement
        
        Returns:
            Updated (posterior) prior distribution
        """
        measurement_date = measurement_date or datetime.utcnow()
        
        # Get current prior (with decay)
        prior = self.get_prior(marker_name, apply_decay=True, current_time=measurement_date)
        
        if prior is None:
            # No prior exists, create one from measurement
            self.set_prior(
                marker_name=marker_name,
                mean=measurement_value,
                std=measurement_uncertainty,
                source="lab_measurement",
                established_at=measurement_date,
                last_measurement_date=measurement_date
            )
            return self.priors[marker_name]
        
        # Bayesian update (Gaussian conjugate prior)
        # Posterior mean = weighted average of prior and measurement
        prior_precision = 1.0 / (prior.std ** 2)
        measurement_precision = 1.0 / (measurement_uncertainty ** 2)
        
        posterior_precision = prior_precision + measurement_precision
        posterior_variance = 1.0 / posterior_precision
        posterior_std = math.sqrt(posterior_variance)
        
        posterior_mean = (
            (prior_precision * prior.mean + measurement_precision * measurement_value) /
            posterior_precision
        )
        
        # Update prior with posterior
        self.set_prior(
            marker_name=marker_name,
            mean=posterior_mean,
            std=posterior_std,
            source="lab_measurement",
            established_at=measurement_date,
            last_measurement_date=measurement_date
        )
        
        logger.info(
            f"Updated posterior for {marker_name}: "
            f"prior=({prior.mean:.1f}±{prior.std:.1f}) + "
            f"measurement=({measurement_value:.1f}±{measurement_uncertainty:.1f}) → "
            f"posterior=({posterior_mean:.1f}±{posterior_std:.1f})"
        )
        
        return self.priors[marker_name]
    
    def reinforce_stability(
        self,
        marker_name: str,
        stable_values: List[Tuple[datetime, float]],
        reinforcement_factor: float = 0.5
    ):
        """
        Reinforce prior when longitudinal data shows stability.
        
        Args:
            marker_name: Name of marker
            stable_values: List of (timestamp, value) showing stability
            reinforcement_factor: How much to restore prior strength (0-1)
        """
        if marker_name not in self.priors:
            return
        
        if len(stable_values) < 3:
            return  # Need at least 3 points for stability
        
        prior = self.priors[marker_name]
        
        # Compute statistics from stable values
        values = [v for _, v in stable_values]
        mean_value = sum(values) / len(values)
        
        # Check if values are actually stable
        max_val = max(values)
        min_val = min(values)
        range_val = max_val - min_val
        relative_range = range_val / abs(mean_value) if mean_value != 0 else 0
        
        if relative_range > 0.20:  # More than 20% variation
            logger.debug(f"Values for {marker_name} not stable enough for reinforcement")
            return
        
        # Partially restore prior strength by "refreshing" the last measurement date
        # This reduces decay
        most_recent_time = max(t for t, _ in stable_values)
        
        # Interpolate between current date and most recent
        if prior.last_measurement_date:
            current_age_days = (datetime.utcnow() - prior.last_measurement_date).total_seconds() / 86400.0
            restored_age_days = current_age_days * (1.0 - reinforcement_factor)
            restored_date = datetime.utcnow() - timedelta(days=restored_age_days)
        else:
            restored_date = most_recent_time
        
        # Update prior with reinforced date
        self.priors[marker_name].last_measurement_date = restored_date
        
        logger.info(
            f"Reinforced prior for {marker_name} based on {len(stable_values)} stable measurements"
        )
    
    def get_all_priors_status(
        self,
        current_time: Optional[datetime] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get status of all priors.
        
        Returns:
            Dictionary of marker -> prior status
        """
        current_time = current_time or datetime.utcnow()
        
        status = {}
        for marker, prior in self.priors.items():
            strength = prior.get_current_strength(current_time)
            decayed_mean, decayed_std = prior.get_decayed_distribution(current_time)
            
            status[marker] = {
                "mean": prior.mean,
                "std": prior.std,
                "decayed_mean": decayed_mean,
                "decayed_std": decayed_std,
                "strength": strength,
                "source": prior.source,
                "half_life_days": prior.half_life_days,
                "established_at": prior.established_at.isoformat(),
                "last_measurement": prior.last_measurement_date.isoformat() if prior.last_measurement_date else None
            }
        
        return status


# Global instance
_global_priors_decay_engine: Optional[PriorsDecayEngine] = None


def get_priors_decay_engine() -> PriorsDecayEngine:
    """Get or create the global priors decay engine instance."""
    global _global_priors_decay_engine
    if _global_priors_decay_engine is None:
        _global_priors_decay_engine = PriorsDecayEngine()
    return _global_priors_decay_engine
