"""
Part 2: Build-Time Validators

Validates that all Part B outputs meet clinical communication standards.
"""

from typing import List, Tuple
from app.part_b.clinical_mental_model import METRIC_REGISTRY, validate_all_metrics_present
from app.part_b.schemas.output_schemas import OutputLineItem, PartBReport
from app.part_b.explanation_generator import (
    check_forbidden_phrases,
    validate_explanation_quality,
    generate_lab_analog_explanation
)


class ValidationError(Exception):
    """Raised when validation fails."""
    pass


def validate_metric_count() -> None:
    """
    Validate that exactly 35 metrics are defined.
    This is a build-time assertion.
    """
    if len(METRIC_REGISTRY) != 35:
        raise ValidationError(
            f"CRITICAL: METRIC_REGISTRY must have exactly 35 metrics, found {len(METRIC_REGISTRY)}"
        )


def validate_no_null_values(output: OutputLineItem) -> List[str]:
    """
    Validate that output has no NULL/empty primary values when confidence > 0.
    Returns list of issues (empty if valid).
    """
    issues = []
    
    if output.confidence_percent > 0:
        has_value = any([
            output.value_score is not None,
            output.value_range_low is not None,
            output.value_range_high is not None,
            output.value_class is not None
        ])
        
        if not has_value:
            issues.append(
                f"Metric {output.metric_name} has confidence {output.confidence_percent}% "
                f"but no primary value. NULL not allowed when confidence > 0."
            )
    
    return issues


def validate_all_metrics_in_report(report: PartBReport) -> Tuple[bool, List[str]]:
    """
    Validate that report contains all 35 metrics.
    Returns (is_valid, missing_metrics).
    """
    all_outputs = []
    for panel in [
        report.metabolic_regulation,
        report.lipid_cardiometabolic,
        report.micronutrient_vitamin,
        report.inflammatory_immune,
        report.endocrine_neurohormonal,
        report.renal_hydration,
        report.comprehensive_integrated
    ]:
        all_outputs.extend([output.metric_name for output in panel.outputs])
    
    is_complete, missing = validate_all_metrics_present(all_outputs)
    return is_complete, missing


def validate_report_quality(report: PartBReport) -> List[str]:
    """
    Run comprehensive quality validation on a Part B report.
    Returns list of all issues found.
    """
    all_issues = []
    
    # Check metric count
    try:
        validate_metric_count()
    except ValidationError as e:
        all_issues.append(str(e))
    
    # Check all 35 metrics present
    is_complete, missing = validate_all_metrics_in_report(report)
    if not is_complete:
        all_issues.append(
            f"Report missing {len(missing)} metrics: {', '.join(missing)}"
        )
    
    # Check each output
    for panel in [
        report.metabolic_regulation,
        report.lipid_cardiometabolic,
        report.micronutrient_vitamin,
        report.inflammatory_immune,
        report.endocrine_neurohormonal,
        report.renal_hydration,
        report.comprehensive_integrated
    ]:
        for output in panel.outputs:
            # Check no NULL values
            null_issues = validate_no_null_values(output)
            all_issues.extend(null_issues)
            
            # Generate and validate explanation
            try:
                explanation = generate_lab_analog_explanation(
                    output.metric_name,
                    output,
                    output.confidence_percent
                )
                explanation_issues = validate_explanation_quality(explanation)
                if explanation_issues:
                    all_issues.append(
                        f"Metric {output.metric_name}: {', '.join(explanation_issues)}"
                    )
            except Exception as e:
                all_issues.append(
                    f"Metric {output.metric_name}: Failed to generate explanation: {str(e)}"
                )
    
    return all_issues


def run_build_time_validation() -> None:
    """
    Run all build-time validations.
    Raises ValidationError if any check fails.
    """
    print("Running Part 2 build-time validations...")
    
    # Validate metric count
    validate_metric_count()
    print(f"✅ Metric count: {len(METRIC_REGISTRY)} (expected 35)")
    
    # Validate all metrics have definitions
    for metric_id in METRIC_REGISTRY.keys():
        metric_def = METRIC_REGISTRY[metric_id]
        if not metric_def.lab_analog:
            raise ValidationError(f"Metric {metric_id} missing lab_analog")
        if not metric_def.where_seen:
            raise ValidationError(f"Metric {metric_id} missing where_seen")
        if not metric_def.stands_in_for:
            raise ValidationError(f"Metric {metric_id} missing stands_in_for")
    
    print("✅ All 35 metrics have complete definitions")
    
    # Validate domain coverage
    domains = {m.domain for m in METRIC_REGISTRY.values()}
    expected_domains = {
        "Metabolic Regulation",
        "Lipid + Cardiometabolic",
        "Micronutrient + Vitamin",
        "Inflammatory + Immune",
        "Endocrine + Neurohormonal",
        "Renal + Hydration",
        "Comprehensive + Integrated"
    }
    if domains != expected_domains:
        raise ValidationError(f"Domain coverage mismatch: {domains} != {expected_domains}")
    
    print("✅ All 7 domains covered")
    
    print("\n🎉 All Part 2 build-time validations PASSED")


if __name__ == "__main__":
    run_build_time_validation()
