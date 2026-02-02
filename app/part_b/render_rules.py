"""
Part 3: Rendering Rules Engine (Backend Support)

Deterministically renders Part B outputs into clinically believable UI cards.
Handles confidence processing, category caps, language mapping, and bounded uncertainty.

CRITICAL: This is frontend-support only. Does NOT modify backend inference logic.
"""

from typing import Dict, List, Optional, Tuple, Literal
from pydantic import BaseModel, Field
from enum import Enum
import math


class MetricCategory(str, Enum):
    """Metric categories with different rendering rules."""
    LAB_RANGE_PROXY = "LAB_RANGE_PROXY"
    PROBABILITY_ABNORMAL = "PROBABILITY_ABNORMAL"
    PHYSIOLOGIC_PHENOTYPE = "PHYSIOLOGIC_PHENOTYPE"
    COMPOSITE_INDEX = "COMPOSITE_INDEX"


class AnchorStrength(str, Enum):
    """Anchor data quality levels."""
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"


class ConfidenceBand(BaseModel):
    """Confidence band with label and range."""
    min_confidence: float = Field(..., ge=0.0, le=1.0)
    max_confidence: float = Field(..., ge=0.0, le=1.0)
    label: str
    usage_rule: str


# ============================================================================
# CONFIDENCE PROCESSING
# ============================================================================

# Category-specific confidence caps (prevents overconfidence)
CATEGORY_CONFIDENCE_CAPS: Dict[MetricCategory, float] = {
    MetricCategory.LAB_RANGE_PROXY: 0.85,
    MetricCategory.PROBABILITY_ABNORMAL: 0.80,
    MetricCategory.PHYSIOLOGIC_PHENOTYPE: 0.75,
    MetricCategory.COMPOSITE_INDEX: 0.70
}

# Confidence language mapping (clinical phrasing by confidence level)
CONFIDENCE_LANGUAGE_MAP: List[ConfidenceBand] = [
    ConfidenceBand(
        min_confidence=0.85,
        max_confidence=0.90,
        label="Highly consistent with",
        usage_rule="anchor_strength == strong AND data_adequacy >= 0.8"
    ),
    ConfidenceBand(
        min_confidence=0.75,
        max_confidence=0.849999,
        label="Strongly suggests",
        usage_rule="data_adequacy >= 0.6"
    ),
    ConfidenceBand(
        min_confidence=0.65,
        max_confidence=0.749999,
        label="Moderately consistent with",
        usage_rule="default"
    ),
    ConfidenceBand(
        min_confidence=0.55,
        max_confidence=0.649999,
        label="Suggestive of",
        usage_rule="weak or partial anchors"
    ),
    ConfidenceBand(
        min_confidence=0.0,
        max_confidence=0.549999,
        label="Exploratory signal only",
        usage_rule="must include what_to_measure_next"
    )
]

# Disallowed diagnostic phrases (NEVER in UI)
DISALLOWED_PHRASES = [
    "you have",
    "diagnosed",
    "confirms",
    "definitive",
    "indicates disease",
    "treatment",
    "prescribe",
    "start medication",
    "stop medication"
]


def compute_confidence_score(
    model_certainty: float,
    data_adequacy: float,
    anchor_strength: AnchorStrength
) -> float:
    """
    Compute raw confidence score using multiplicative formula.
    
    Args:
        model_certainty: Model's internal certainty (0-1)
        data_adequacy: Data quality score (0-1)
        anchor_strength: Anchor quality (weak/moderate/strong)
        
    Returns:
        Raw confidence score (0-1)
    """
    # Convert anchor strength to numeric
    anchor_multiplier = {
        AnchorStrength.WEAK: 0.6,
        AnchorStrength.MODERATE: 0.8,
        AnchorStrength.STRONG: 1.0
    }[anchor_strength]
    
    # Multiplicative formula
    confidence_raw = model_certainty * data_adequacy * anchor_multiplier
    
    return max(0.0, min(1.0, confidence_raw))


def apply_category_cap(confidence_raw: float, category: MetricCategory) -> float:
    """Apply category-specific confidence cap."""
    cap = CATEGORY_CONFIDENCE_CAPS[category]
    return min(confidence_raw, cap)


def snap_to_band(confidence: float, band_width: float = 0.10) -> float:
    """
    Snap confidence to nearest band (e.g., 10% bands: 0.70, 0.80, 0.90).
    
    Args:
        confidence: Raw confidence (0-1)
        band_width: Band width (default 0.10 = 10%)
        
    Returns:
        Snapped confidence
    """
    return round(confidence / band_width) * band_width


def process_confidence(
    model_certainty: float,
    data_adequacy: float,
    anchor_strength: AnchorStrength,
    category: MetricCategory
) -> Tuple[float, int, str]:
    """
    Full confidence processing pipeline.
    
    Returns:
        (confidence_final, confidence_percent, confidence_label)
    """
    # Step 1: Compute raw confidence
    conf_raw = compute_confidence_score(model_certainty, data_adequacy, anchor_strength)
    
    # Step 2: Apply category cap
    conf_capped = apply_category_cap(conf_raw, category)
    
    # Step 3: Snap to 10% band
    conf_snapped = snap_to_band(conf_capped, 0.10)
    
    # Step 4: Round to integer percent
    conf_percent = int(round(conf_snapped * 100))
    
    # Step 5: Get confidence label
    conf_label = get_confidence_label(conf_snapped, anchor_strength)
    
    return conf_snapped, conf_percent, conf_label


def get_confidence_label(confidence: float, anchor_strength: AnchorStrength) -> str:
    """
    Get clinical confidence label based on confidence level and anchor strength.
    """
    for band in CONFIDENCE_LANGUAGE_MAP:
        if band.min_confidence <= confidence <= band.max_confidence:
            # Apply usage rule
            if "strong" in band.usage_rule and anchor_strength != AnchorStrength.STRONG:
                continue
            return band.label
    
    # Default fallback
    return "Moderately consistent with"


# ============================================================================
# RENDERING UTILITIES
# ============================================================================

def infer_category(metric_name: str) -> MetricCategory:
    """
    Infer metric category from metric name.
    Used when category not explicitly provided in backend payload.
    """
    # Lab range proxies (direct lab analogs)
    lab_proxies = [
        'estimated_hba1c_range',
        'ldl_pattern_risk_proxy',
        'hdl_functional_likelihood',
        'vitamin_d_sufficiency_likelihood',
        'chronic_inflammation_index',
        'egfr_trajectory_class'
    ]
    
    # Probability metrics
    probabilities = [
        'insulin_resistance_probability',
        'triglyceride_elevation_probability',
        'dehydration_driven_creatinine_elevation_risk'
    ]
    
    # Composite indices
    composites = [
        'cardiometabolic_risk_score',
        'metabolic_flexibility_score',
        'recovery_capacity_score',
        'allostatic_load_proxy',
        'homeostatic_resilience_score'
    ]
    
    if metric_name in lab_proxies:
        return MetricCategory.LAB_RANGE_PROXY
    elif metric_name in probabilities:
        return MetricCategory.PROBABILITY_ABNORMAL
    elif metric_name in composites:
        return MetricCategory.COMPOSITE_INDEX
    else:
        return MetricCategory.PHYSIOLOGIC_PHENOTYPE


def compute_confidence_range(
    confidence: float,
    value_center: Optional[float] = None,
    max_width_percent: float = 10.0
) -> Tuple[int, int]:
    """
    Compute confidence range bounds as percentages.
    
    Args:
        confidence: Confidence level (0-1)
        value_center: Center value (optional)
        max_width_percent: Max width in percentage points
        
    Returns:
        (low_pct, high_pct) - e.g., (70, 80) for 70-80% confidence
    """
    conf_pct = confidence * 100
    half_width = min(max_width_percent / 2, 5.0)  # Cap at ±5%
    
    low_pct = int(max(0, conf_pct - half_width))
    high_pct = int(min(100, conf_pct + half_width))
    
    return low_pct, high_pct


def validate_no_diagnostic_language(text: str) -> List[str]:
    """
    Check text for disallowed diagnostic phrases.
    Returns list of violations (empty if clean).
    """
    text_lower = text.lower()
    violations = []
    
    for phrase in DISALLOWED_PHRASES:
        if phrase in text_lower:
            violations.append(phrase)
    
    return violations


# ============================================================================
# RENDER PIPELINE
# ============================================================================

def normalize_inputs(raw_output: Dict) -> Dict:
    """Step 1: Normalize input data structure."""
    return {
        'metric_id': raw_output.get('metric_name') or raw_output.get('metric_id'),
        'metric_name': raw_output.get('metric_name'),
        'value_center': raw_output.get('value_score'),
        'range_low': raw_output.get('value_range_low'),
        'range_high': raw_output.get('value_range_high'),
        'unit': raw_output.get('units'),
        'confidence': raw_output.get('confidence_percent', 0) / 100.0,
        'category': raw_output.get('category'),
        'anchor_strength': raw_output.get('anchor_strength', 'moderate'),
        'drivers': raw_output.get('confidence_top_3_drivers', []),
        'measured_vs_inferred': raw_output.get('measured_vs_inferred', 'inferred')
    }


def derive_display_fields(normalized: Dict) -> Dict:
    """Step 2: Derive display-specific fields."""
    # Infer category if missing
    if not normalized.get('category'):
        normalized['category'] = infer_category(normalized['metric_id']).value
    
    # Format metric name for display
    display_name = normalized['metric_name'].replace('_', ' ').title()
    normalized['display_name'] = display_name
    
    return normalized


def compute_render_confidence(normalized: Dict) -> Dict:
    """Step 3: Compute confidence range and label."""
    category = MetricCategory(normalized['category'])
    anchor_strength = AnchorStrength(normalized.get('anchor_strength', 'moderate'))
    
    confidence_raw = normalized['confidence']
    
    # Apply category cap
    confidence_capped = apply_category_cap(confidence_raw, category)
    
    # Snap to band
    confidence_final = snap_to_band(confidence_capped, 0.10)
    
    # Get label
    confidence_label = get_confidence_label(confidence_final, anchor_strength)
    
    # Compute range
    conf_low, conf_high = compute_confidence_range(confidence_final)
    
    normalized['confidence_final'] = confidence_final
    normalized['confidence_percent'] = int(confidence_final * 100)
    normalized['confidence_label'] = confidence_label
    normalized['confidence_range'] = (conf_low, conf_high)
    
    return normalized


def render_output_card(raw_output: Dict) -> Dict:
    """
    Main render pipeline: transform raw backend output into UI card data.
    
    Args:
        raw_output: Raw output from Part B inference
        
    Returns:
        Rendered card data structure ready for UI
    """
    # Step 1: Normalize
    normalized = normalize_inputs(raw_output)
    
    # Step 2: Derive display fields
    display_ready = derive_display_fields(normalized)
    
    # Step 3: Compute confidence
    with_confidence = compute_render_confidence(display_ready)
    
    return with_confidence


# ============================================================================
# VALIDATION
# ============================================================================

def validate_render_rules() -> None:
    """Run validation checks on render rules configuration."""
    print("Running Part 3 render rules validation...")
    
    # Check confidence caps
    assert all(0 < cap <= 1.0 for cap in CATEGORY_CONFIDENCE_CAPS.values()), \
        "All confidence caps must be in (0, 1]"
    
    # Check confidence bands
    assert len(CONFIDENCE_LANGUAGE_MAP) > 0, "Must have confidence language mappings"
    
    # Check bands cover full range
    min_covered = min(band.min_confidence for band in CONFIDENCE_LANGUAGE_MAP)
    max_covered = max(band.max_confidence for band in CONFIDENCE_LANGUAGE_MAP)
    assert min_covered == 0.0 and max_covered >= 0.90, \
        "Confidence bands must cover [0.0, 0.90+]"
    
    print("✅ Confidence caps validated")
    print("✅ Confidence language mappings validated")
    print("✅ All render rules PASSED")


if __name__ == "__main__":
    validate_render_rules()
