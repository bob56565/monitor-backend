"""
Part 2: Lab-Analog Explanation Generator

Generates clinical explanation blocks for each Part B metric.
Each explanation mimics how clinicians communicate indirect or calculated lab results.

FORBIDDEN PHRASES (Never use):
- "You have"
- "Diagnosed"
- "Confirms"
- "Indicates disease"
- "Definitive"
- "NULL"
- "N/A" (when confidence > 0)
- "Not available"

REQUIRED PHRASES:
- "This is an estimate, not a direct blood draw"
- "Closest clinical analog"
- "Here's what it would likely look like on a lab slip"
"""

from typing import Dict, List, Optional
from app.part_b.clinical_mental_model import (
    MetricDefinition,
    LabAnalogExplanation,
    AnalogType,
    get_metric_definition
)
from app.part_b.schemas.output_schemas import OutputLineItem


def generate_lab_analog_explanation(
    metric_id: str,
    output: OutputLineItem,
    confidence_percent: float
) -> LabAnalogExplanation:
    """
    Generate lab-analog explanation block for a metric.
    
    Args:
        metric_id: Metric identifier
        output: OutputLineItem containing inference results
        confidence_percent: Confidence percentage (0-100)
        
    Returns:
        LabAnalogExplanation with all required fields
    """
    metric_def = get_metric_definition(metric_id)
    
    # Extract top drivers from output
    driver_descriptions = [driver[0] for driver in output.confidence_top_3_drivers[:3]]
    
    # Map confidence to clinical language
    confidence_label = _confidence_to_clinical_label(confidence_percent)
    
    # Generate what_this_represents
    what_represents = _generate_what_this_represents(metric_def, output)
    
    # Generate lab_correspondence
    lab_correspondence = _generate_lab_correspondence(metric_def, output)
    
    # Generate what would tighten estimate
    tighten_estimate = _generate_tighten_estimate(metric_def)
    
    return LabAnalogExplanation(
        what_this_represents=what_represents,
        lab_correspondence=lab_correspondence,
        why_we_believe_this=driver_descriptions if driver_descriptions else [
            "Physiologic patterns from continuous monitoring",
            "Age and demographic priors"
        ],
        confidence_level=confidence_label,
        what_would_tighten_estimate=tighten_estimate,
        analog_type=metric_def.analog_type
    )


def _confidence_to_clinical_label(confidence: float) -> str:
    """Convert confidence percentage to clinical label."""
    if confidence >= 85:
        return "High (~85%+)"
    elif confidence >= 75:
        return "Moderate-High (~75-85%)"
    elif confidence >= 60:
        return "Moderate (~60-75%)"
    elif confidence >= 40:
        return "Moderate-Low (~40-60%)"
    else:
        return "Low (<40%)"


def _generate_what_this_represents(metric_def: MetricDefinition, output: OutputLineItem) -> str:
    """Generate the 'what this represents' field."""
    if metric_def.analog_type == AnalogType.TRUE_LAB_ANALOG:
        return (
            f"Not a direct blood draw. This is an estimated {metric_def.lab_analog} value "
            f"inferred from signals known to correlate with serum levels. "
            f"Analogous to how calculated LDL uses the Friedewald equation rather than direct measurement."
        )
    else:
        return (
            f"Not a direct lab measurement. This is a clinician-synthesis estimate based on "
            f"multiple physiologic signals and patterns. Similar to how clinicians synthesize "
            f"multiple test results and clinical findings to assess {metric_def.display_name.lower()}."
        )


def _generate_lab_correspondence(metric_def: MetricDefinition, output: OutputLineItem) -> str:
    """Generate the 'lab correspondence' field with value ranges."""
    base = f"Closest clinical analog: {metric_def.lab_analog}. "
    
    # Add value range if available
    if output.value_range_low is not None and output.value_range_high is not None:
        units = output.units or metric_def.typical_units or ""
        value_str = f"{output.value_range_low:.1f}-{output.value_range_high:.1f} {units}".strip()
        base += f"Estimated range: {value_str}. "
    elif output.value_score is not None:
        units = output.units or metric_def.typical_units or ""
        base += f"Estimated score: {output.value_score:.1f} {units}. ".strip()
    elif output.value_class is not None:
        base += f"Estimated classification: {output.value_class}. "
    
    base += f"Here's what it would likely look like on a lab slip: {metric_def.where_seen}"
    return base


def _generate_tighten_estimate(metric_def: MetricDefinition) -> str:
    """Generate recommendation for tightening estimate."""
    
    # Map metric to specific lab recommendation
    lab_recommendations = {
        "estimated_hba1c_range": "A serum HbA1c test",
        "insulin_resistance_probability": "A fasting insulin + glucose test (HOMA-IR)",
        "vitamin_d_sufficiency_likelihood": "A serum 25-OH vitamin D test",
        "b12_functional_adequacy_score": "A serum B12 and methylmalonic acid (MMA) test",
        "ldl_pattern_risk_proxy": "A standard lipid panel (total cholesterol, LDL-C, HDL-C, triglycerides)",
        "hdl_functional_likelihood": "An advanced lipid panel with HDL particle count",
        "triglyceride_elevation_probability": "A fasting triglycerides test",
        "chronic_inflammation_index": "A high-sensitivity CRP (hs-CRP) test",
        "cortisol_rhythm_integrity_score": "A 4-point salivary cortisol curve",
        "thyroid_functional_pattern": "A thyroid panel (TSH, Free T3, Free T4)",
        "hydration_status": "A basic metabolic panel (BMP) with serum osmolality",
        "egfr_trajectory_class": "A serum creatinine with calculated eGFR",
        "iron_utilization_status_class": "An iron panel (ferritin, TIBC, serum iron, transferrin saturation)",
        "magnesium_adequacy_proxy": "A serum magnesium test (or RBC magnesium for better accuracy)",
    }
    
    specific_test = lab_recommendations.get(
        metric_def.metric_id,
        f"A {metric_def.lab_analog} test"
    )
    
    return f"{specific_test} would significantly tighten this estimate."


def format_value_for_display(output: OutputLineItem, metric_def: MetricDefinition) -> str:
    """
    Format metric value for user display.
    NEVER returns NULL or empty string if confidence > 0.
    """
    # Priority 1: Range
    if output.value_range_low is not None and output.value_range_high is not None:
        units = output.units or metric_def.typical_units or ""
        return f"{output.value_range_low:.1f}-{output.value_range_high:.1f} {units}".strip()
    
    # Priority 2: Score
    if output.value_score is not None:
        units = output.units or metric_def.typical_units or ""
        return f"{output.value_score:.1f} {units}".strip()
    
    # Priority 3: Classification
    if output.value_class is not None:
        return output.value_class
    
    # Priority 4: Fallback based on null_replacement_strategy
    # Parse strategy and return bounded estimate
    strategy = metric_def.null_replacement_strategy
    
    if "wide range" in strategy.lower():
        # Extract range from strategy if present
        if "%" in strategy and metric_def.value_type == "range":
            return "5.0-6.0 % (Low confidence)"
        elif "mg/dL" in strategy:
            if "ldl" in metric_def.metric_id.lower():
                return "100-140 mg/dL (Population prior)"
            elif "vitamin_d" in metric_def.metric_id.lower():
                return "20-35 ng/mL (Moderate confidence)"
            elif "magnesium" in metric_def.metric_id.lower():
                return "1.8-2.2 mg/dL (Dietary signal based)"
        elif "mg/L" in strategy:
            return "1.0-3.0 mg/L (Moderate-Low confidence)"
    
    if "probability" in strategy.lower() or metric_def.value_type == "probability":
        return "40-60% (Wide interval)"
    
    if "score" in strategy.lower() or metric_def.value_type == "score":
        return "50-70 /100 (Moderate-Low confidence)"
    
    # Classification fallback
    if metric_def.value_type == "class":
        return "Indeterminate (Insufficient data - see recommendations)"
    
    # Absolute fallback
    return "Estimate pending (See data improvement pathway)"


def check_forbidden_phrases(text: str) -> List[str]:
    """
    Check text for forbidden phrases.
    Returns list of forbidden phrases found (empty if clean).
    """
    forbidden = [
        "you have",
        "diagnosed",
        "confirms",
        "indicates disease",
        "definitive",
        "null",
        "n/a",
        "not available"
    ]
    
    text_lower = text.lower()
    found = []
    for phrase in forbidden:
        if phrase in text_lower:
            found.append(phrase)
    
    return found


def validate_explanation_quality(explanation: LabAnalogExplanation) -> List[str]:
    """
    Validate explanation meets quality standards.
    Returns list of issues (empty if valid).
    """
    issues = []
    
    # Check required phrases
    if "estimate" not in explanation.what_this_represents.lower():
        issues.append("Missing 'estimate' language in what_this_represents")
    
    if "analog" not in explanation.lab_correspondence.lower():
        issues.append("Missing 'analog' reference in lab_correspondence")
    
    # Check forbidden phrases
    all_text = " ".join([
        explanation.what_this_represents,
        explanation.lab_correspondence,
        " ".join(explanation.why_we_believe_this),
        explanation.what_would_tighten_estimate
    ])
    
    forbidden_found = check_forbidden_phrases(all_text)
    if forbidden_found:
        issues.append(f"Forbidden phrases found: {', '.join(forbidden_found)}")
    
    # Check driver count
    if len(explanation.why_we_believe_this) < 2:
        issues.append("Need at least 2 drivers in why_we_believe_this")
    
    if len(explanation.why_we_believe_this) > 4:
        issues.append("Maximum 4 drivers allowed in why_we_believe_this")
    
    return issues
