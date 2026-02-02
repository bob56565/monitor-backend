"""
Phase 3 Integration Orchestrator

Coordinates all Phase 3 enhancements:
- A2 Processing: uncertainty reduction, cohort matching, change point detection
- B Output: provider summaries, cost/care impact, explainability, language control

Design: Additive-only, backward-compatible, feature-flagged
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional
from app.features.uncertainty_reduction import get_uncertainty_reduction_planner
from app.features.cohort_matching import get_cohort_matching_engine
from app.features.change_point_detection import get_change_point_detector
from app.features.provider_summary import get_provider_summary_generator
from app.features.cost_care_impact import get_cost_care_impact_analyzer
from app.features.explainability import get_explainability_engine
from app.features.language_control import get_language_controller


@dataclass
class Phase3FeatureFlags:
    """Feature flags for Phase 3 components."""
    # A2 Processing
    enable_uncertainty_reduction_planner: bool = True
    enable_cohort_matching: bool = True
    enable_change_point_detection: bool = True
    
    # B Output
    enable_provider_summary: bool = True
    enable_cost_impact_modules: bool = True
    enable_tight_explainability: bool = True
    enable_language_control: bool = True  # Always enforce


class Phase3Integrator:
    """
    Orchestrator for all Phase 3 enhancements.
    
    Coordinates decision intelligence features:
    - Uncertainty reduction planning
    - Cohort contextualization
    - Change point detection
    - Provider-ready summaries
    - Cost/care impact analysis
    - Tight explainability
    - Strict language control
    """
    
    FEATURE_FLAGS = Phase3FeatureFlags()
    
    def __init__(self):
        # A2 Processing components
        self.uncertainty_planner = get_uncertainty_reduction_planner()
        self.cohort_engine = get_cohort_matching_engine()
        self.change_detector = get_change_point_detector()
        
        # B Output components
        self.summary_generator = get_provider_summary_generator()
        self.impact_analyzer = get_cost_care_impact_analyzer()
        self.explainability_engine = get_explainability_engine()
        self.language_controller = get_language_controller()
    
    def integrate_phase3(
        self,
        patient_id: str,
        run_v2: any,  # RunV2 object
        estimates: Dict[str, Dict],
        measured_anchors: Dict[str, any],
        historical_data: Dict[str, List[Dict]],
        events: Optional[List[Dict]],
        phase2_metadata: Optional[Dict],
        previous_report: Optional[Dict] = None
    ) -> Dict[str, any]:
        """
        Main Phase 3 integration method.
        
        Applies all Phase 3 enhancements and returns enhanced output with metadata.
        
        Args:
            patient_id: Patient identifier
            run_v2: RunV2 object
            estimates: Current estimates from Phase 2
            measured_anchors: Measured values
            historical_data: Longitudinal data
            events: Optional events (illness, medications, etc.)
            phase2_metadata: Metadata from Phase 2
            previous_report: Previous report for comparison
        
        Returns:
            {
                "estimates": {...},  # Unchanged estimates
                "phase3_metadata": {
                    "uncertainty_reduction": {...},
                    "cohort_match": {...},
                    "change_point_analysis": {...},
                    "explanations": {...},
                    "provider_summary": {...},
                    "cost_impact": {...}
                }
            }
        """
        phase3_metadata = {}
        
        # ===== A2 PROCESSING =====
        
        # 1. Uncertainty Reduction Planning
        if self.FEATURE_FLAGS.enable_uncertainty_reduction_planner:
            uncertainty_plan = self.uncertainty_planner.plan_uncertainty_reduction(
                current_estimates=estimates,
                measured_anchors=measured_anchors,
                historical_data=historical_data,
                metadata={"run_id": run_v2.run_id if hasattr(run_v2, 'run_id') else None}
            )
            phase3_metadata["uncertainty_reduction"] = uncertainty_plan
            phase3_metadata["top_recommendations"] = uncertainty_plan.get("top_recommendations", [])
        
        # 2. Cohort Matching
        if self.FEATURE_FLAGS.enable_cohort_matching:
            cohort_match = self.cohort_engine.match_cohort(
                current_estimates=estimates,
                measured_anchors=measured_anchors,
                historical_data=historical_data,
                user_metadata={"age": None, "sex": None, "medications": []}  # Would get from run_v2
            )
            phase3_metadata["cohort_match"] = {
                "matched_cohort_id": cohort_match.matched_cohort_id,
                "matched_cohort_name": cohort_match.matched_cohort_name,
                "overall_similarity_score": cohort_match.overall_similarity_score,
                "similarity_level": cohort_match.similarity_level.value,
                "suppress_cohort_claims": cohort_match.suppress_cohort_claims,
                "glucose_percentile": cohort_match.glucose_percentile,
                "cohort_diabetes_prevalence": cohort_match.cohort_diabetes_prevalence,
                "cohort_cvd_prevalence": cohort_match.cohort_cvd_prevalence
            }
        
        # 3. Change Point Detection (for key markers)
        if self.FEATURE_FLAGS.enable_change_point_detection:
            change_analyses = {}
            key_markers = ["glucose", "a1c", "ldl", "triglycerides", "blood_pressure_systolic"]
            
            for marker in key_markers:
                if marker in historical_data and historical_data[marker]:
                    analysis = self.change_detector.detect_change_points(
                        marker_id=marker,
                        historical_data=historical_data[marker],
                        marker_kinetics=phase2_metadata.get("temporal_kinetics", {}).get(marker) if phase2_metadata else None
                    )
                    
                    change_analyses[marker] = {
                        "events_count": len(analysis.events),
                        "recent_events": [
                            {
                                "timestamp": e.change_point_timestamp.isoformat(),
                                "change_type": e.change_type.value,
                                "direction": e.direction.value,
                                "magnitude": e.magnitude,
                                "clinical_relevance": e.clinical_relevance.value,
                                "days_ago": e.days_ago
                            }
                            for e in analysis.recent_events
                        ],
                        "current_phase": analysis.current_phase,
                        "phase_confidence": analysis.phase_confidence,
                        "overall_trend": analysis.overall_trend,
                        "early_warning_flags": analysis.early_warning_flags,
                        "recovery_signals": analysis.recovery_signals
                    }
            
            phase3_metadata["change_point_analysis"] = change_analyses
        
        # ===== B OUTPUT =====
        
        # 4. Tight Explainability
        if self.FEATURE_FLAGS.enable_tight_explainability:
            explanations = self.explainability_engine.explain_batch(
                estimates=estimates,
                phase2_metadata=phase2_metadata,
                phase3_metadata=phase3_metadata
            )
            
            phase3_metadata["explanations"] = {
                output_id: {
                    "confidence_bar": exp.confidence_bar,
                    "confidence_interpretation": exp.confidence_interpretation,
                    "because_sentence": exp.because_sentence,
                    "top_drivers": [
                        {
                            "name": d.driver_name,
                            "weight": d.contribution_weight,
                            "explanation": d.short_explanation
                        }
                        for d in exp.top_drivers
                    ],
                    "what_would_change_this": exp.what_would_change_this,
                    "primary_uncertainty": exp.primary_uncertainty
                }
                for output_id, exp in explanations.items()
            }
        
        # 5. Provider Summary
        if self.FEATURE_FLAGS.enable_provider_summary:
            provider_summary = self.summary_generator.generate_summary(
                patient_id=patient_id,
                estimates=estimates,
                measured_anchors=measured_anchors,
                historical_data=historical_data,
                phase2_metadata=phase2_metadata,
                phase3_metadata=phase3_metadata,
                previous_report=previous_report
            )
            
            phase3_metadata["provider_summary"] = {
                "report_date": provider_summary.report_date.isoformat(),
                "data_quality_grade": provider_summary.data_quality_grade,
                "what_changed": {
                    "should_render": provider_summary.what_changed.should_render,
                    "items": provider_summary.what_changed.content_items,
                    "priority": provider_summary.what_changed.priority_level
                },
                "what_matters_now": {
                    "should_render": provider_summary.what_matters_now.should_render,
                    "items": provider_summary.what_matters_now.content_items,
                    "priority": provider_summary.what_matters_now.priority_level
                },
                "what_is_stable": {
                    "should_render": provider_summary.what_is_stable.should_render,
                    "items": provider_summary.what_is_stable.content_items,
                    "priority": provider_summary.what_is_stable.priority_level
                },
                "risk_patterns": {
                    "should_render": provider_summary.risk_patterns.should_render,
                    "items": provider_summary.risk_patterns.content_items,
                    "priority": provider_summary.risk_patterns.priority_level
                },
                "suggested_measurements": {
                    "should_render": provider_summary.suggested_measurements.should_render,
                    "items": provider_summary.suggested_measurements.content_items,
                    "priority": provider_summary.suggested_measurements.priority_level
                },
                "formatted_text": self.summary_generator.format_for_display(provider_summary)
            }
        
        # 6. Cost & Care Impact Analysis
        if self.FEATURE_FLAGS.enable_cost_impact_modules:
            impact_modules = self.impact_analyzer.analyze_impact(
                estimates=estimates,
                measured_anchors=measured_anchors,
                historical_data=historical_data,
                phase2_metadata=phase2_metadata,
                phase3_metadata=phase3_metadata,
                user_metadata={}
            )
            
            phase3_metadata["cost_impact"] = {
                module_id: {
                    "should_render": module.should_render,
                    "suppression_reason": module.suppression_reason,
                    "claims": [
                        {
                            "statement": claim.claim_statement,
                            "confidence": claim.confidence_level.value,
                            "supporting_data": claim.supporting_data_signals,
                            "limitations": claim.limitations
                        }
                        for claim in module.claims
                    ],
                    "overall_confidence": module.overall_confidence.value
                }
                for module_id, module in impact_modules.items()
            }
        
        # 7. Language Control Validation
        if self.FEATURE_FLAGS.enable_language_control:
            # Validate provider summary text
            if "provider_summary" in phase3_metadata:
                summary_text = phase3_metadata["provider_summary"].get("formatted_text", "")
                violations = self.language_controller.validate_text(summary_text)
                
                if violations:
                    phase3_metadata["language_violations"] = [
                        {
                            "type": v.violation_type.value,
                            "phrase": v.violating_phrase,
                            "severity": v.severity
                        }
                        for v in violations
                    ]
        
        # Return enhanced output
        return {
            "estimates": estimates,  # Unchanged
            "phase3_metadata": phase3_metadata
        }


# ===== Singleton =====

_phase3_integrator_instance = None

def get_phase3_integrator() -> Phase3Integrator:
    """Get singleton instance of Phase 3 integrator."""
    global _phase3_integrator_instance
    if _phase3_integrator_instance is None:
        _phase3_integrator_instance = Phase3Integrator()
    return _phase3_integrator_instance


# ===== Convenience Function =====

def apply_phase3_enhancements(
    patient_id: str,
    run_v2: any,
    estimates: Dict[str, Dict],
    measured_anchors: Dict[str, any],
    historical_data: Dict[str, List[Dict]],
    events: Optional[List[Dict]] = None,
    phase2_metadata: Optional[Dict] = None,
    previous_report: Optional[Dict] = None,
    feature_flags: Optional[Phase3FeatureFlags] = None
) -> Dict[str, any]:
    """
    Convenience function to apply all Phase 3 enhancements.
    
    Usage:
        result = apply_phase3_enhancements(
            patient_id="user_123",
            run_v2=run,
            estimates=phase2_estimates,
            measured_anchors=anchors,
            historical_data=history,
            phase2_metadata=phase2_meta
        )
        
        provider_summary_text = result["phase3_metadata"]["provider_summary"]["formatted_text"]
    """
    integrator = get_phase3_integrator()
    
    # Apply custom feature flags if provided
    if feature_flags:
        integrator.FEATURE_FLAGS = feature_flags
    
    return integrator.integrate_phase3(
        patient_id=patient_id,
        run_v2=run_v2,
        estimates=estimates,
        measured_anchors=measured_anchors,
        historical_data=historical_data,
        events=events,
        phase2_metadata=phase2_metadata,
        previous_report=previous_report
    )
