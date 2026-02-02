"""
Confidence Scoring Engine

Computes confidence scores for inferred/measured outputs based on:
- Data completeness
- Anchor availability (uploaded labs)
- Data recency
- Sensor quality flags
- Signal stability
- Modality alignment

All confidence scores are bounded 0-100% with explicit caps for
measured (95%) vs inferred outputs (85% tight, 70% wide, 55% no anchor).
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from enum import Enum
import math

from app.services.priors import priors_service


class OutputType(str, Enum):
    """Type of output for confidence calculation."""
    MEASURED = "measured"  # Direct upload (lab, vital)
    INFERRED_TIGHT = "inferred_tight"  # Inferred with strong anchors
    INFERRED_WIDE = "inferred_wide"  # Inferred with weak anchors
    INFERRED_NO_ANCHOR = "inferred_no_anchor"  # Inferred without anchors


class ConfidenceEngine:
    """
    Engine for computing standardized confidence scores.
    
    Singleton pattern for consistency across the platform.
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        # Load confidence parameters from priors service
        self.params = priors_service.get_confidence_parameters()
        self._initialized = True
    
    def compute_confidence(
        self,
        output_type: OutputType,
        completeness_score: float,
        anchor_quality: float,
        recency_days: Optional[float],
        signal_quality: Optional[float] = None,
        signal_stability: Optional[float] = None,
        modality_alignment: Optional[float] = None,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Compute confidence score for an output.
        
        Args:
            output_type: Type of output (measured/inferred)
            completeness_score: Data completeness (0-1)
            anchor_quality: Quality of anchoring data (0-1, 1=recent lab upload)
            recency_days: Days since most recent relevant data
            signal_quality: Sensor quality score (0-1)
            signal_stability: Signal stability score (0-1)
            modality_alignment: Cross-modality agreement score (0-1)
            metadata: Additional context for driver explanations
        
        Returns:
            Dict with:
                - confidence_percent: Final confidence (0-100)
                - top_3_drivers: List of (driver, impact) tuples
                - what_increases_confidence: List of actionable recommendations
                - confidence_inputs: Structured inputs for provenance
        """
        # Get max confidence based on output type
        max_confidence = self._get_max_confidence(output_type)
        
        # Compute component scores
        components = {}
        
        # Completeness contribution (0-1)
        components['completeness'] = self._score_completeness(completeness_score)
        
        # Anchor contribution (0-1)
        components['anchor'] = self._score_anchor(anchor_quality, output_type)
        
        # Recency contribution (0-1)
        if recency_days is not None:
            components['recency'] = self._score_recency(recency_days)
        else:
            components['recency'] = 0.5  # Neutral if unknown
        
        # Signal quality contribution (0-1)
        if signal_quality is not None:
            components['signal_quality'] = max(signal_quality, self.params['signal_quality_floor'])
        else:
            components['signal_quality'] = 0.7  # Default decent quality
        
        # Signal stability contribution (0-1)
        if signal_stability is not None:
            components['stability'] = signal_stability
        else:
            components['stability'] = 0.7  # Default decent stability
        
        # Modality alignment bonus (0-0.1)
        if modality_alignment is not None:
            components['alignment_bonus'] = modality_alignment * self.params['modality_alignment_bonus']
        else:
            components['alignment_bonus'] = 0.0
        
        # Weighted combination
        base_score = (
            components['completeness'] * 0.30 +
            components['anchor'] * 0.30 +
            components['recency'] * 0.15 +
            components['signal_quality'] * 0.15 +
            components['stability'] * 0.10
        )
        
        # Add alignment bonus
        final_score = min(base_score + components['alignment_bonus'], 1.0)
        
        # Scale to percentage and cap
        confidence_percent = min(final_score * 100, max_confidence)
        
        # Identify top drivers
        top_drivers = self._identify_top_drivers(components, metadata)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            components, output_type, confidence_percent, metadata
        )
        
        return {
            'confidence_percent': round(confidence_percent, 1),
            'top_3_drivers': top_drivers[:3],
            'what_increases_confidence': recommendations,
            'confidence_inputs': {
                'output_type': output_type,
                'max_confidence': max_confidence,
                'components': components,
                'final_score': round(final_score, 3),
                'metadata': metadata or {}
            }
        }
    
    def _get_max_confidence(self, output_type: OutputType) -> float:
        """Get maximum allowed confidence for output type."""
        if output_type == OutputType.MEASURED:
            return self.params['max_confidence_measured']
        elif output_type == OutputType.INFERRED_TIGHT:
            return self.params['max_confidence_inferred_tight']
        elif output_type == OutputType.INFERRED_WIDE:
            return self.params['max_confidence_inferred_wide']
        else:  # INFERRED_NO_ANCHOR
            return self.params['max_confidence_no_anchor']
    
    def _score_completeness(self, completeness: float) -> float:
        """Score data completeness (0-1)."""
        # Sigmoid-like curve: penalize low completeness more heavily
        return 1 / (1 + math.exp(-8 * (completeness - 0.5)))
    
    def _score_anchor(self, anchor_quality: float, output_type: OutputType) -> float:
        """Score anchor data quality (0-1)."""
        if output_type == OutputType.MEASURED:
            # Measured data is self-anchoring
            return 1.0
        else:
            # Inferred data depends on anchor quality
            return anchor_quality
    
    def _score_recency(self, days: float) -> float:
        """Score data recency using exponential decay (0-1)."""
        halflife = self.params['recency_decay_halflife_days']
        return math.exp(-math.log(2) * days / halflife)
    
    def _identify_top_drivers(
        self,
        components: Dict[str, float],
        metadata: Optional[Dict]
    ) -> List[Tuple[str, str]]:
        """
        Identify top 3 confidence drivers.
        
        Returns:
            List of (driver_name, impact_description) tuples
        """
        # Convert components to interpretable drivers
        driver_scores = []
        
        if components['completeness'] >= 0.8:
            driver_scores.append(('completeness', components['completeness'], 'high', 'Comprehensive data uploaded'))
        elif components['completeness'] >= 0.6:
            driver_scores.append(('completeness', components['completeness'], 'medium', 'Good data coverage'))
        else:
            driver_scores.append(('completeness', components['completeness'], 'low', 'Limited data available'))
        
        if components['anchor'] >= 0.8:
            driver_scores.append(('anchor', components['anchor'], 'high', 'Recent lab results anchor estimate'))
        elif components['anchor'] >= 0.5:
            driver_scores.append(('anchor', components['anchor'], 'medium', 'Some lab data available'))
        else:
            driver_scores.append(('anchor', components['anchor'], 'low', 'No recent lab anchors'))
        
        if components['recency'] >= 0.8:
            driver_scores.append(('recency', components['recency'], 'high', 'Very recent data'))
        elif components['recency'] >= 0.6:
            driver_scores.append(('recency', components['recency'], 'medium', 'Reasonably recent data'))
        else:
            driver_scores.append(('recency', components['recency'], 'low', 'Older data'))
        
        if components['signal_quality'] >= 0.8:
            driver_scores.append(('signal_quality', components['signal_quality'], 'high', 'High sensor quality'))
        elif components['signal_quality'] >= 0.6:
            driver_scores.append(('signal_quality', components['signal_quality'], 'medium', 'Adequate sensor quality'))
        else:
            driver_scores.append(('signal_quality', components['signal_quality'], 'low', 'Lower sensor quality'))
        
        if components['stability'] >= 0.8:
            driver_scores.append(('stability', components['stability'], 'high', 'Stable signal patterns'))
        
        if components.get('alignment_bonus', 0) > 0.05:
            driver_scores.append(('alignment', 0.9, 'high', 'Multiple modalities agree'))
        
        # Sort by score and take top 3
        driver_scores.sort(key=lambda x: x[1], reverse=True)
        return [(d[3], d[2]) for d in driver_scores[:3]]
    
    def _generate_recommendations(
        self,
        components: Dict[str, float],
        output_type: OutputType,
        current_confidence: float,
        metadata: Optional[Dict]
    ) -> List[str]:
        """
        Generate actionable recommendations to increase confidence.
        
        Returns:
            List of recommendation strings
        """
        recommendations = []
        
        # Completeness recommendations
        if components['completeness'] < 0.7:
            missing_items = metadata.get('missing_items', []) if metadata else []
            if missing_items:
                recommendations.append(f"Upload missing data: {', '.join(missing_items[:3])}")
            else:
                recommendations.append("Upload additional specimen data (blood, urine, saliva)")
        
        # Anchor recommendations
        if components['anchor'] < 0.7 and output_type != OutputType.MEASURED:
            anchor_type = metadata.get('anchor_type', 'lab') if metadata else 'lab'
            recommendations.append(f"Upload recent {anchor_type} results to improve accuracy")
        
        # Recency recommendations
        if components['recency'] < 0.6:
            recommendations.append("Add more recent data to improve timeliness")
        
        # Signal quality recommendations
        if components['signal_quality'] < 0.7:
            recommendations.append("Ensure ISF monitor has good contact and is properly calibrated")
        
        # Time window recommendations
        if metadata and metadata.get('days_of_data', 0) < 14:
            recommendations.append("Collect more days of continuous monitoring (14+ days recommended)")
        
        # Cap at 3-4 most actionable
        return recommendations[:4]
    
    def compute_data_completeness(
        self,
        has_specimen_uploads: bool = False,
        specimen_count: int = 0,
        has_isf_monitor: bool = False,
        isf_days: int = 0,
        has_vitals: bool = False,
        vitals_count: int = 0,
        has_soap_profile: bool = False,
        soap_completeness: float = 0.0
    ) -> Dict:
        """
        Compute overall data completeness score.
        
        Args:
            has_specimen_uploads: Whether user has uploaded any specimens
            specimen_count: Number of specimen uploads
            has_isf_monitor: Whether user has ISF monitor data
            isf_days: Number of days of ISF data
            has_vitals: Whether user has vitals data
            vitals_count: Number of vitals records
            has_soap_profile: Whether user has SOAP profile
            soap_completeness: SOAP profile completeness (0-1)
        
        Returns:
            Dict with:
                - completeness_score: Overall score (0-1)
                - component_scores: Breakdown by component
                - missing_critical: List of missing critical items
        """
        weights = self.params['completeness_weights']
        
        # Score each component
        specimen_score = min(specimen_count / 3.0, 1.0) if has_specimen_uploads else 0.0
        isf_score = min(isf_days / 30.0, 1.0) if has_isf_monitor else 0.0
        vitals_score = min(vitals_count / 10.0, 1.0) if has_vitals else 0.0
        soap_score = soap_completeness if has_soap_profile else 0.0
        
        # Weighted average
        completeness_score = (
            specimen_score * weights['specimen_uploads'] +
            isf_score * weights['isf_monitor_data'] +
            vitals_score * weights['vitals_data'] +
            soap_score * weights['soap_profile']
        )
        
        # Identify missing critical items
        missing_critical = []
        if not has_specimen_uploads:
            missing_critical.append("Blood panel (CMP, CBC, or lipid)")
        if not has_isf_monitor or isf_days < 7:
            missing_critical.append("7+ days of ISF monitor data")
        if not has_vitals:
            missing_critical.append("Vital signs (BP, HR)")
        if not has_soap_profile or soap_completeness < 0.5:
            missing_critical.append("Complete SOAP profile (demographics, medical history)")
        
        return {
            'completeness_score': round(completeness_score, 3),
            'component_scores': {
                'specimens': round(specimen_score, 3),
                'isf_monitor': round(isf_score, 3),
                'vitals': round(vitals_score, 3),
                'soap_profile': round(soap_score, 3),
            },
            'missing_critical': missing_critical
        }


# Singleton instance
confidence_engine = ConfidenceEngine()
