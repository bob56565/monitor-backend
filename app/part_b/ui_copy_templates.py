"""
Part 3: UI Copy Templates

Exact copy templates for each metric category.
Templates are populated with metric-specific data at render time.

CRITICAL: All templates must pass diagnostic language filter.
"""

from typing import Dict, List, Optional
from enum import Enum


class TemplateCategory(str, Enum):
    """Template categories matching metric types."""
    LAB_RANGE_PROXY = "CATEGORY_A_LAB_RANGE_PROXY"
    PROBABILITY_ABNORMAL = "CATEGORY_B_PROBABILITY"
    PHYSIOLOGIC_PHENOTYPE = "CATEGORY_C_PHYSIOLOGIC_PHENOTYPE"
    COMPOSITE_INDEX = "CATEGORY_D_COMPOSITE_INDEX"


# ============================================================================
# TEMPLATE DEFINITIONS
# ============================================================================

UI_COPY_TEMPLATES = {
    TemplateCategory.LAB_RANGE_PROXY: {
        "headline": "Estimated {metric_name}: {range_low}–{range_high} {unit}",
        "subheadline": "Clinical reference: {ref_low}–{ref_high} {unit} ({lab_panel})",
        "what_this_represents": (
            "This is an AI-derived estimate of your {lab_test_name} based on "
            "continuous physiologic signals, validated population patterns, and "
            "internal consistency checks."
        ),
        "how_to_interpret": (
            "If a blood test were drawn today, it would most likely fall within "
            "this estimated range."
        ),
        "why_we_believe_this": (
            "This estimate integrates {top_drivers_list} using physiologic "
            "constraints, longitudinal consistency, and population priors."
        ),
        "what_would_increase_certainty": (
            "A direct {lab_test_name} measurement would narrow this range further."
        ),
        "clinical_context": (
            "Clinicians order {lab_panel} to assess {clinical_question}. "
            "This estimate provides similar insight without a blood draw."
        ),
        "safety_language": (
            "This is not a diagnostic result. For clinical decisions, "
            "consult your healthcare provider and consider confirmatory testing."
        )
    },
    
    TemplateCategory.PROBABILITY_ABNORMAL: {
        "headline": "Estimated probability of abnormal {lab_test_name}: {prob_low}–{prob_high}%",
        "subheadline": "Abnormal = outside {ref_low}–{ref_high} {unit}",
        "what_this_represents": (
            "This represents the likelihood that your {lab_test_name} would fall "
            "outside the typical lab reference range if measured today."
        ),
        "how_to_interpret": (
            "Higher probabilities indicate closer alignment with profiles commonly "
            "associated with out-of-range results."
        ),
        "why_we_believe_this": (
            "This probability is supported by {top_drivers_list} and constrained "
            "by physiologic plausibility checks."
        ),
        "what_would_increase_certainty": (
            "A direct {lab_test_name} test would confirm the exact value."
        ),
        "clinical_context": (
            "This probability helps prioritize which labs to order next. "
            "It does not replace actual lab testing."
        ),
        "safety_language": (
            "Probabilities are estimates, not diagnoses. Clinical context and "
            "symptoms should guide testing decisions with your provider."
        )
    },
    
    TemplateCategory.PHYSIOLOGIC_PHENOTYPE: {
        "headline": "Detected pattern: {pattern_label}",
        "subheadline": "System: {system_name}",
        "what_this_represents": (
            "This pattern reflects how your body is regulating {system_name}, "
            "inferred from multiple measured and derived signals."
        ),
        "how_to_interpret": (
            "Clinicians often infer this pattern using labs such as "
            "{lab_analogs_used_by_clinicians}."
        ),
        "why_we_believe_this": (
            "Pattern detection is based on {top_drivers_list} showing "
            "{pattern_characteristics}."
        ),
        "what_this_does_not_mean": (
            "This is not a diagnosis and does not replace clinical evaluation."
        ),
        "clinical_context": (
            "Understanding your physiologic patterns helps guide lifestyle "
            "optimization and identify which labs to prioritize."
        ),
        "safety_language": (
            "Patterns are descriptive, not diagnostic. Discuss findings with "
            "your healthcare provider for clinical interpretation."
        )
    },
    
    TemplateCategory.COMPOSITE_INDEX: {
        "headline": "{metric_name}: {index_score}/100 ({index_band})",
        "subheadline": "Multi-system summary score",
        "what_this_summarizes": (
            "This index summarizes signals across {domains_list} into one "
            "interpretable score."
        ),
        "how_to_interpret": (
            "Higher scores reflect greater physiologic strain. Best interpreted "
            "longitudinally over weeks to months."
        ),
        "why_this_matters": (
            "Composite indices help track overall physiologic trajectory and "
            "identify which specific domains need attention."
        ),
        "best_use": (
            "Most valuable for trend tracking over time, not single-point decisions."
        ),
        "clinical_context": (
            "Similar to how clinicians use metabolic syndrome criteria or "
            "cardiovascular risk scores to integrate multiple factors."
        ),
        "safety_language": (
            "Composite scores are for monitoring trends, not diagnosis. "
            "Clinical decisions require full evaluation by your provider."
        )
    }
}


# ============================================================================
# TEMPLATE POPULATION
# ============================================================================

def populate_template(
    category: TemplateCategory,
    context: Dict
) -> Dict[str, str]:
    """
    Populate template with metric-specific context.
    
    Args:
        category: Template category
        context: Dict with substitution values
        
    Returns:
        Dict of populated template sections
    """
    template = UI_COPY_TEMPLATES[category]
    populated = {}
    
    for key, template_str in template.items():
        try:
            populated[key] = template_str.format(**context)
        except KeyError as e:
            # Missing context key - use placeholder
            populated[key] = template_str.replace(f"{{{e.args[0]}}}", f"[{e.args[0]}]")
    
    return populated


def build_template_context(metric_data: Dict) -> Dict:
    """
    Build context dict for template population from metric data.
    
    Args:
        metric_data: Rendered metric data
        
    Returns:
        Context dict with all template variables
    """
    # Extract core fields
    context = {
        'metric_name': metric_data.get('display_name', 'Unknown Metric'),
        'range_low': format_value(metric_data.get('range_low')),
        'range_high': format_value(metric_data.get('range_high')),
        'unit': metric_data.get('unit', ''),
        'index_score': format_value(metric_data.get('value_center')),
        'prob_low': format_value(metric_data.get('confidence_range', (0, 0))[0]),
        'prob_high': format_value(metric_data.get('confidence_range', (0, 0))[1]),
        'pattern_label': metric_data.get('display_name', 'Pattern'),
        'index_band': get_index_band(metric_data.get('value_center', 50))
    }
    
    # Add reference interval if present
    ref_interval = metric_data.get('reference_interval', {})
    context.update({
        'ref_low': format_value(ref_interval.get('low')),
        'ref_high': format_value(ref_interval.get('high')),
        'lab_panel': ref_interval.get('source', 'Standard Lab Panel')
    })
    
    # Add lab analog info
    lab_analog = metric_data.get('lab_analog', {})
    context.update({
        'lab_test_name': ', '.join(lab_analog.get('test_names', ['this test'])),
        'lab_analogs_used_by_clinicians': ', '.join(lab_analog.get('test_names', ['lab tests']))
    })
    
    # Add driver list
    drivers = metric_data.get('drivers', [])
    driver_names = [d.get('name', 'signal') if isinstance(d, dict) else d[0] for d in drivers[:3]]
    context['top_drivers_list'] = ', '.join(driver_names) if driver_names else 'multiple signals'
    
    # Add system/domain info
    context.update({
        'system_name': infer_system_name(metric_data.get('metric_id', '')),
        'domains_list': infer_domains(metric_data.get('metric_id', '')),
        'clinical_question': infer_clinical_question(metric_data.get('metric_id', '')),
        'pattern_characteristics': infer_pattern_characteristics(metric_data)
    })
    
    return context


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def format_value(value: Optional[float]) -> str:
    """Format numeric value for display."""
    if value is None:
        return "—"
    if isinstance(value, (int, float)):
        return f"{value:.1f}" if value != int(value) else str(int(value))
    return str(value)


def get_index_band(score: float) -> str:
    """Get qualitative band for index score."""
    if score >= 80:
        return "High"
    elif score >= 60:
        return "Moderate-High"
    elif score >= 40:
        return "Moderate"
    elif score >= 20:
        return "Low-Moderate"
    else:
        return "Low"


def infer_system_name(metric_id: str) -> str:
    """Infer physiologic system from metric ID."""
    if 'metabol' in metric_id or 'glucose' in metric_id or 'insulin' in metric_id:
        return "glucose and energy metabolism"
    elif 'lipid' in metric_id or 'ldl' in metric_id or 'hdl' in metric_id or 'cholesterol' in metric_id:
        return "lipid metabolism and cardiovascular health"
    elif 'inflam' in metric_id or 'immune' in metric_id:
        return "inflammation and immune response"
    elif 'cortisol' in metric_id or 'stress' in metric_id or 'autonomic' in metric_id:
        return "stress response and autonomic regulation"
    elif 'renal' in metric_id or 'kidney' in metric_id or 'egfr' in metric_id:
        return "kidney function and fluid balance"
    elif 'thyroid' in metric_id:
        return "thyroid function and metabolic rate"
    else:
        return "physiologic regulation"


def infer_domains(metric_id: str) -> str:
    """Infer domains for composite index."""
    # Most composite indices span multiple domains
    return "metabolic, cardiovascular, inflammatory, and stress domains"


def infer_clinical_question(metric_id: str) -> str:
    """Infer clinical question addressed by metric."""
    if 'hba1c' in metric_id or 'glucose' in metric_id:
        return "glucose control and diabetes risk"
    elif 'ldl' in metric_id or 'lipid' in metric_id:
        return "cardiovascular disease risk"
    elif 'vitamin_d' in metric_id:
        return "vitamin D adequacy and bone health"
    elif 'inflammation' in metric_id:
        return "systemic inflammation burden"
    else:
        return "overall physiologic health"


def infer_pattern_characteristics(metric_data: Dict) -> str:
    """Infer pattern characteristics from metric data."""
    # Simplified - in production, derive from actual pattern analysis
    return "consistent patterns across multiple timepoints"


# ============================================================================
# VALIDATION
# ============================================================================

def validate_templates() -> None:
    """Validate all templates are properly defined."""
    print("Running Part 3 template validation...")
    
    # Check all categories have templates
    for category in TemplateCategory:
        assert category in UI_COPY_TEMPLATES, f"Missing template for {category}"
        template = UI_COPY_TEMPLATES[category]
        
        # Check required sections (flexible - different categories have different sections)
        required_sections = ['headline', 'safety_language']
        for section in required_sections:
            assert section in template, f"{category} missing {section}"
        
        # Check at least one content section
        content_sections = ['what_this_represents', 'what_this_summarizes', 'what_this_does_not_mean']
        has_content = any(s in template for s in content_sections)
        assert has_content, f"{category} missing content sections"
    
    print(f"✅ All {len(UI_COPY_TEMPLATES)} template categories validated")
    print("✅ All required sections present")
    print("✅ Template validation PASSED")


if __name__ == "__main__":
    validate_templates()
