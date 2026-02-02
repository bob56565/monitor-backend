"""
Provider-Ready Summary Generator (Phase 3 B.4)

Generates concise, clinician-facing, one-page summaries designed for quick review.
Structured for clinical workflow integration.

Key Sections:
- What Changed Since Last Report
- What Matters Now
- What Is Stable
- Key Risk Patterns
- Suggested Next Measurements (if any)

Design Principles:
- Clinician-oriented language (non-diagnostic but technical)
- Quick-scan format (bulleted, not paragraphs)
- Suppress sections if no meaningful content
- Reference confidence and anchor strength implicitly
- Actionable insights, not just data dumps
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from app.features.language_control import get_language_controller, enforce_safe_language


@dataclass
class ProviderSummarySection:
    """Single section of provider summary."""
    section_title: str
    should_render: bool
    suppression_reason: Optional[str]
    content_items: List[str]  # Bulleted list items
    priority_level: str  # "HIGH", "MEDIUM", "LOW"


@dataclass
class ProviderSummary:
    """Complete provider-ready summary."""
    # Meta
    patient_id: str
    report_date: datetime
    data_quality_grade: str  # Overall data quality
    
    # Sections
    what_changed: ProviderSummarySection
    what_matters_now: ProviderSummarySection
    what_is_stable: ProviderSummarySection
    risk_patterns: ProviderSummarySection
    suggested_measurements: ProviderSummarySection
    
    # Footer
    key_limitations: List[str]
    data_summary: str  # e.g., "Based on 87 days of monitoring, 234 glucose points, 12 lab results"


class ProviderSummaryGenerator:
    """
    Generator for provider-ready one-page summaries.
    
    Designed for quick clinical review during patient visits.
    """
    
    def __init__(self):
        self.language_controller = get_language_controller()
    
    @enforce_safe_language
    def generate_summary(
        self,
        patient_id: str,
        estimates: Dict[str, Dict],
        measured_anchors: Dict[str, any],
        historical_data: Dict[str, List[Dict]],
        phase2_metadata: Optional[Dict] = None,
        phase3_metadata: Optional[Dict] = None,
        previous_report: Optional[Dict] = None
    ) -> ProviderSummary:
        """
        Generate provider-ready summary.
        
        Args:
            patient_id: Patient identifier
            estimates: Current estimates
            measured_anchors: Measured values
            historical_data: Longitudinal data
            phase2_metadata: Phase 2 metadata
            phase3_metadata: Phase 3 metadata (change points, etc.)
            previous_report: Previous report for comparison
        
        Returns:
            Complete provider summary
        """
        report_date = datetime.now()
        
        # 1. Assess overall data quality
        data_quality = self._assess_data_quality(estimates, historical_data)
        
        # 2. Generate sections
        what_changed = self._generate_what_changed(
            estimates, previous_report, phase3_metadata
        )
        
        what_matters = self._generate_what_matters_now(
            estimates, phase2_metadata, phase3_metadata
        )
        
        what_stable = self._generate_what_is_stable(
            estimates, phase2_metadata, phase3_metadata
        )
        
        risk_patterns = self._generate_risk_patterns(
            estimates, phase3_metadata
        )
        
        suggested_meas = self._generate_suggested_measurements(
            estimates, phase3_metadata
        )
        
        # 3. Generate limitations and data summary
        limitations = self._generate_limitations(estimates, historical_data)
        data_summary = self._generate_data_summary(historical_data, measured_anchors)
        
        return ProviderSummary(
            patient_id=patient_id,
            report_date=report_date,
            data_quality_grade=data_quality,
            what_changed=what_changed,
            what_matters_now=what_matters,
            what_is_stable=what_stable,
            risk_patterns=risk_patterns,
            suggested_measurements=suggested_meas,
            key_limitations=limitations,
            data_summary=data_summary
        )
    
    def format_for_display(self, summary: ProviderSummary) -> str:
        """Format summary as one-page text."""
        lines = []
        
        # Header
        lines.append("=" * 70)
        lines.append("PROVIDER SUMMARY REPORT")
        lines.append("=" * 70)
        lines.append(f"Patient ID: {summary.patient_id}")
        lines.append(f"Report Date: {summary.report_date.strftime('%Y-%m-%d %H:%M')}")
        lines.append(f"Data Quality: {summary.data_quality_grade}")
        lines.append(f"Data Summary: {summary.data_summary}")
        lines.append("=" * 70)
        lines.append("")
        
        # Sections
        sections = [
            summary.what_changed,
            summary.what_matters_now,
            summary.what_is_stable,
            summary.risk_patterns,
            summary.suggested_measurements
        ]
        
        for section in sections:
            if not section.should_render:
                continue
            
            lines.append(f"## {section.section_title}")
            
            if section.priority_level != "LOW":
                lines.append(f"   [Priority: {section.priority_level}]")
            
            lines.append("")
            
            for item in section.content_items:
                lines.append(f"  • {item}")
            
            lines.append("")
        
        # Footer
        if summary.key_limitations:
            lines.append("## Key Limitations")
            lines.append("")
            for limitation in summary.key_limitations:
                lines.append(f"  • {limitation}")
            lines.append("")
        
        lines.append("=" * 70)
        lines.append("END OF SUMMARY")
        lines.append("=" * 70)
        
        return "\n".join(lines)
    
    # ===== Section Generators =====
    
    def _generate_what_changed(
        self,
        estimates: Dict[str, Dict],
        previous_report: Optional[Dict],
        phase3_metadata: Optional[Dict]
    ) -> ProviderSummarySection:
        """Generate 'What Changed Since Last Report' section."""
        items = []
        
        # Check for change points
        if phase3_metadata and "change_point_analysis" in phase3_metadata:
            analyses = phase3_metadata["change_point_analysis"]
            
            for marker, analysis in analyses.items():
                recent_events = analysis.get("recent_events", [])
                
                for event in recent_events[:2]:  # Top 2 recent
                    if event.get("clinical_relevance") in ["HIGH", "MODERATE"]:
                        direction = event.get("direction", "changed")
                        magnitude = event.get("magnitude", 0)
                        days_ago = event.get("days_ago", 0)
                        
                        items.append(
                            f"{marker.upper()}: {direction} by {magnitude:.1f} "
                            f"({int(days_ago)} days ago) - {event.get('clinical_relevance', 'MODERATE')} relevance"
                        )
        
        # Compare to previous report if available
        if previous_report:
            for marker, current_est in estimates.items():
                if marker in previous_report:
                    prev_value = previous_report[marker].get("estimated_value")
                    curr_value = current_est.get("estimated_value")
                    
                    if prev_value and curr_value:
                        change_pct = ((curr_value - prev_value) / prev_value) * 100
                        
                        if abs(change_pct) > 10:  # >10% change
                            items.append(
                                f"{marker}: {change_pct:+.1f}% change since last report "
                                f"({prev_value:.1f} → {curr_value:.1f})"
                            )
        
        # Determine priority
        priority = "HIGH" if any("HIGH" in item for item in items) else "MEDIUM"
        
        # Determine if should render
        should_render = len(items) > 0
        suppression = None if should_render else "No significant changes detected"
        
        return ProviderSummarySection(
            section_title="What Changed Since Last Report",
            should_render=should_render,
            suppression_reason=suppression,
            content_items=items[:5],  # Top 5
            priority_level=priority
        )
    
    def _generate_what_matters_now(
        self,
        estimates: Dict[str, Dict],
        phase2_metadata: Optional[Dict],
        phase3_metadata: Optional[Dict]
    ) -> ProviderSummarySection:
        """Generate 'What Matters Now' section."""
        items = []
        
        # Check for high-confidence concerning patterns
        for marker, estimate in estimates.items():
            confidence = estimate.get("confidence", 0)
            value = estimate.get("estimated_value")
            
            if confidence >= 0.6 and value:
                # Check if in concerning range
                if self._is_concerning_value(marker, value):
                    items.append(
                        f"{marker}: Elevated at {value:.1f} (confidence: {confidence:.0%}) - "
                        f"Consider clinical evaluation"
                    )
        
        # Check for early warning signals
        if phase3_metadata and "change_point_analysis" in phase3_metadata:
            for marker, analysis in phase3_metadata["change_point_analysis"].items():
                warnings = analysis.get("early_warning_flags", [])
                if warnings:
                    items.append(
                        f"{marker}: Early warning - {warnings[0]}"
                    )
        
        # Check for constraint conflicts
        if phase2_metadata and phase2_metadata.get("constraint_conflicts", 0) > 0:
            conflicts = phase2_metadata.get("constraint_conflicts_detail", [])
            if conflicts:
                items.append(
                    f"Physiological inconsistency detected: {conflicts[0]}"
                )
        
        # Determine priority
        priority = "HIGH" if items else "LOW"
        
        # Determine if should render
        should_render = len(items) > 0
        suppression = None if should_render else "No urgent concerns identified"
        
        return ProviderSummarySection(
            section_title="What Matters Now",
            should_render=should_render,
            suppression_reason=suppression,
            content_items=items[:5],
            priority_level=priority
        )
    
    def _generate_what_is_stable(
        self,
        estimates: Dict[str, Dict],
        phase2_metadata: Optional[Dict],
        phase3_metadata: Optional[Dict]
    ) -> ProviderSummarySection:
        """Generate 'What Is Stable' section."""
        items = []
        
        # Check change point analysis for stable markers
        if phase3_metadata and "change_point_analysis" in phase3_metadata:
            for marker, analysis in phase3_metadata["change_point_analysis"].items():
                if analysis.get("current_phase") == "stable":
                    confidence = analysis.get("phase_confidence", 0)
                    if confidence >= 0.7:
                        items.append(
                            f"{marker}: Stable over monitoring period (confidence: {confidence:.0%})"
                        )
        
        # Check for high-confidence, in-range values
        for marker, estimate in estimates.items():
            confidence = estimate.get("confidence", 0)
            value = estimate.get("estimated_value")
            
            if confidence >= 0.7 and value:
                if self._is_normal_range(marker, value):
                    items.append(
                        f"{marker}: Within normal range at {value:.1f} (confidence: {confidence:.0%})"
                    )
        
        # Determine priority
        priority = "LOW"  # Stable is good but low priority
        
        # Determine if should render
        should_render = len(items) > 0
        suppression = None if should_render else "Insufficient data to assess stability"
        
        return ProviderSummarySection(
            section_title="What Is Stable",
            should_render=should_render,
            suppression_reason=suppression,
            content_items=items[:5],
            priority_level=priority
        )
    
    def _generate_risk_patterns(
        self,
        estimates: Dict[str, Dict],
        phase3_metadata: Optional[Dict]
    ) -> ProviderSummarySection:
        """Generate 'Key Risk Patterns' section."""
        items = []
        
        # Check cohort context
        if phase3_metadata and "cohort_match" in phase3_metadata:
            cohort = phase3_metadata["cohort_match"]
            if not cohort.get("suppress_cohort_claims"):
                diabetes_prev = cohort.get("cohort_diabetes_prevalence", 0)
                cvd_prev = cohort.get("cohort_cvd_prevalence", 0)
                
                if diabetes_prev > 0.3:
                    items.append(
                        f"Matched cohort shows {diabetes_prev:.0%} diabetes prevalence "
                        f"(similarity: {cohort.get('overall_similarity_score', 0):.0%})"
                    )
                
                if cvd_prev > 0.2:
                    items.append(
                        f"Matched cohort shows {cvd_prev:.0%} CVD prevalence"
                    )
        
        # Check for multiple markers in concerning ranges
        concerning_count = sum(
            1 for marker, est in estimates.items()
            if self._is_concerning_value(marker, est.get("estimated_value"))
        )
        
        if concerning_count >= 3:
            items.append(
                f"Multiple markers ({concerning_count}) in concerning ranges - "
                f"consider comprehensive metabolic evaluation"
            )
        
        # Check for deteriorating trends
        if phase3_metadata and "change_point_analysis" in phase3_metadata:
            deteriorating = [
                marker for marker, analysis in phase3_metadata["change_point_analysis"].items()
                if analysis.get("current_phase") == "deteriorating"
            ]
            
            if len(deteriorating) >= 2:
                items.append(
                    f"Multiple deteriorating trends: {', '.join(deteriorating[:3])}"
                )
        
        # Determine priority
        priority = "HIGH" if items else "LOW"
        
        # Determine if should render
        should_render = len(items) > 0
        suppression = None if should_render else "No significant risk patterns identified"
        
        return ProviderSummarySection(
            section_title="Key Risk Patterns",
            should_render=should_render,
            suppression_reason=suppression,
            content_items=items[:5],
            priority_level=priority
        )
    
    def _generate_suggested_measurements(
        self,
        estimates: Dict[str, Dict],
        phase3_metadata: Optional[Dict]
    ) -> ProviderSummarySection:
        """Generate 'Suggested Next Measurements' section."""
        items = []
        
        # Get uncertainty reduction recommendations
        if phase3_metadata and "top_recommendations" in phase3_metadata:
            recs = phase3_metadata["top_recommendations"]
            
            for rec in recs[:3]:  # Top 3
                measurement = rec.get("measurement")
                reduction = rec.get("expected_reduction_percent", 0)
                reason = rec.get("reason", "")
                urgency = rec.get("urgency", "LOW")
                
                items.append(
                    f"{measurement}: {reduction:.0f}% uncertainty reduction expected "
                    f"[{urgency} urgency] - {reason}"
                )
        
        # Add any missing key anchors
        weak_confidence = [
            marker for marker, est in estimates.items()
            if est.get("confidence", 0) < 0.4 and est.get("anchor_strength") == "NONE"
        ]
        
        if weak_confidence:
            items.append(
                f"Direct measurement of {', '.join(weak_confidence[:2])} would strengthen estimates"
            )
        
        # Determine priority
        priority = "MEDIUM" if items else "LOW"
        
        # Determine if should render
        should_render = len(items) > 0
        suppression = None if should_render else "Current data sufficient; no urgent measurements needed"
        
        return ProviderSummarySection(
            section_title="Suggested Next Measurements",
            should_render=should_render,
            suppression_reason=suppression,
            content_items=items[:5],
            priority_level=priority
        )
    
    # ===== Helper Methods =====
    
    def _assess_data_quality(
        self,
        estimates: Dict[str, Dict],
        history: Dict[str, List[Dict]]
    ) -> str:
        """Assess overall data quality."""
        # Compute average confidence
        confidences = [e.get("confidence", 0) for e in estimates.values()]
        avg_conf = sum(confidences) / len(confidences) if confidences else 0
        
        # Count data points
        total_points = sum(len(history.get(s, [])) for s in history)
        
        # Grade
        if avg_conf >= 0.7 and total_points >= 100:
            return "A (Excellent)"
        elif avg_conf >= 0.5 and total_points >= 50:
            return "B (Good)"
        elif avg_conf >= 0.3 and total_points >= 20:
            return "C (Fair)"
        else:
            return "D (Limited)"
    
    def _generate_limitations(
        self,
        estimates: Dict[str, Dict],
        history: Dict[str, List[Dict]]
    ) -> List[str]:
        """Generate key limitations."""
        limitations = []
        
        # Check for weak anchors
        weak_anchors = [
            m for m, e in estimates.items()
            if e.get("anchor_strength") in ["NONE", "WEAK"]
        ]
        
        if len(weak_anchors) >= 3:
            limitations.append(
                f"{len(weak_anchors)} outputs lack direct measurements (population-based estimates)"
            )
        
        # Check for temporal gaps
        has_gaps = any(
            len(history.get(s, [])) < 10 for s in ["glucose", "weight", "heart_rate"]
        )
        
        if has_gaps:
            limitations.append("Limited continuous monitoring data for some streams")
        
        # General disclaimer
        limitations.append("Estimates are probabilistic, not diagnostic")
        limitations.append("Clinical judgment and validation required")
        
        return limitations[:4]
    
    def _generate_data_summary(
        self,
        history: Dict[str, List[Dict]],
        anchors: Dict[str, any]
    ) -> str:
        """Generate data summary string."""
        # Count data points
        total_points = sum(len(history.get(s, [])) for s in history)
        
        # Count days of monitoring
        all_timestamps = []
        for stream_data in history.values():
            for point in stream_data:
                if "timestamp" in point:
                    all_timestamps.append(point["timestamp"])
        
        if all_timestamps:
            days = (max(all_timestamps) - min(all_timestamps)).days
        else:
            days = 0
        
        # Count lab results
        lab_count = len([a for a in anchors.values() if a is not None])
        
        return f"{days} days monitoring, {total_points} data points, {lab_count} lab measurements"
    
    def _is_concerning_value(self, marker: str, value: Optional[float]) -> bool:
        """Check if value is in concerning range."""
        if value is None:
            return False
        
        thresholds = {
            "glucose": 126,  # Diabetes threshold
            "a1c": 6.5,
            "ldl": 160,  # High
            "triglycerides": 200,  # High
            "blood_pressure_systolic": 140  # Stage 2 hypertension
        }
        
        return value >= thresholds.get(marker, float('inf'))
    
    def _is_normal_range(self, marker: str, value: Optional[float]) -> bool:
        """Check if value is in normal range."""
        if value is None:
            return False
        
        normal_ranges = {
            "glucose": (70, 100),
            "a1c": (4.0, 5.6),
            "ldl": (0, 100),
            "hdl": (40, float('inf')),
            "triglycerides": (0, 150)
        }
        
        if marker not in normal_ranges:
            return False
        
        low, high = normal_ranges[marker]
        return low <= value <= high


# ===== Singleton =====

_summary_generator_instance = None

def get_provider_summary_generator() -> ProviderSummaryGenerator:
    """Get singleton instance of provider summary generator."""
    global _summary_generator_instance
    if _summary_generator_instance is None:
        _summary_generator_instance = ProviderSummaryGenerator()
    return _summary_generator_instance
