"""
Strict Language Control System (Phase 3 B.7)

Enforces non-diagnostic, estimation-based language across all outputs.
Provides centralized templates and validation to ensure clinical safety
and regulatory compliance.

Key Features:
- Centralized language templates
- Evidence-grade-aware phrasing
- Confidence-level-aware qualifiers
- Forbidden phrase detection and blocking
- Safe alternative suggestions

Design Principles:
- Never diagnostic (no "you have", "diagnosis", "disease")
- Always estimation-based ("estimated", "probable", "consistent with")
- Appropriate hedging based on evidence grade and confidence
- Clinician consultation prompts when appropriate
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Set
import re


class LanguageViolationType(str, Enum):
    """Type of language violation."""
    DIAGNOSTIC_CLAIM = "diagnostic_claim"
    DEFINITIVE_STATEMENT = "definitive_statement"
    MEDICAL_ADVICE = "medical_advice"
    CAUSAL_CLAIM = "causal_claim"
    PREDICTIVE_CERTAINTY = "predictive_certainty"


@dataclass
class LanguageViolation:
    """Detected language violation."""
    violation_type: LanguageViolationType
    violating_phrase: str
    context: str
    suggested_replacement: str
    severity: str  # "ERROR", "WARNING"


@dataclass
class SafePhrasing:
    """Safe alternative phrasing."""
    template: str
    example: str
    confidence_threshold: Optional[float] = None
    evidence_grade_required: Optional[str] = None


class LanguageController:
    """
    Centralized language control system.
    
    Validates all output text against safety rules and provides
    safe alternatives.
    """
    
    def __init__(self):
        # Forbidden phrases (regex patterns)
        self.forbidden_patterns = self._initialize_forbidden_patterns()
        
        # Safe templates by category
        self.safe_templates = self._initialize_safe_templates()
        
        # Qualifier words by confidence level
        self.confidence_qualifiers = self._initialize_confidence_qualifiers()
        
        # Evidence grade hedges
        self.evidence_hedges = self._initialize_evidence_hedges()
    
    def validate_text(self, text: str) -> List[LanguageViolation]:
        """
        Validate text against language rules.
        
        Returns list of violations (empty if clean).
        """
        violations = []
        
        for pattern_type, patterns in self.forbidden_patterns.items():
            for pattern, replacement_template in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    violations.append(LanguageViolation(
                        violation_type=pattern_type,
                        violating_phrase=match.group(0),
                        context=text[max(0, match.start()-20):min(len(text), match.end()+20)],
                        suggested_replacement=replacement_template,
                        severity="ERROR" if pattern_type in [
                            LanguageViolationType.DIAGNOSTIC_CLAIM,
                            LanguageViolationType.MEDICAL_ADVICE
                        ] else "WARNING"
                    ))
        
        return violations
    
    def safe_phrase(
        self,
        category: str,
        value: Optional[float] = None,
        confidence: Optional[float] = None,
        evidence_grade: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Generate safe phrasing for a category.
        
        Args:
            category: Template category (e.g., "range_statement", "trend_statement")
            value: Optional value to insert
            confidence: Confidence level (0-1)
            evidence_grade: Evidence grade (A, B, C, D)
            **kwargs: Additional template variables
        
        Returns:
            Safe formatted string
        """
        templates = self.safe_templates.get(category, [])
        
        if not templates:
            return ""
        
        # Select appropriate template based on confidence/evidence
        selected = templates[0]  # default
        
        for template in templates:
            if confidence is not None and template.confidence_threshold is not None:
                if confidence >= template.confidence_threshold:
                    selected = template
                    break
            
            if evidence_grade is not None and template.evidence_grade_required is not None:
                if evidence_grade >= template.evidence_grade_required:
                    selected = template
                    break
        
        # Add qualifiers based on confidence
        qualifier = self._select_qualifier(confidence)
        
        # Add hedge based on evidence grade
        hedge = self._select_hedge(evidence_grade)
        
        # Format template
        try:
            formatted = selected.template.format(
                value=value,
                qualifier=qualifier,
                hedge=hedge,
                **kwargs
            )
            return formatted
        except Exception:
            return selected.example
    
    def add_clinician_prompt(self, text: str, confidence: float, evidence_grade: str) -> str:
        """Add appropriate clinician consultation prompt."""
        prompts = {
            "low_confidence": "Consider discussing these patterns with your healthcare provider.",
            "moderate_confidence": "These estimates may warrant clinical review.",
            "high_confidence": "Discuss these findings with your clinician for personalized guidance."
        }
        
        if confidence < 0.4:
            prompt = prompts["low_confidence"]
        elif confidence < 0.7:
            prompt = prompts["moderate_confidence"]
        else:
            prompt = prompts["high_confidence"]
        
        return f"{text} {prompt}"
    
    def sanitize_for_provider(self, text: str) -> str:
        """
        Sanitize text for provider-facing output.
        
        Providers can handle more technical language but still
        need estimation framing.
        """
        # Check for violations
        violations = self.validate_text(text)
        
        # Replace violating phrases
        sanitized = text
        for violation in violations:
            if violation.severity == "ERROR":
                sanitized = sanitized.replace(
                    violation.violating_phrase,
                    violation.suggested_replacement
                )
        
        return sanitized
    
    def sanitize_for_patient(self, text: str) -> str:
        """
        Sanitize text for patient-facing output.
        
        Requires more conservative language and clearer hedging.
        """
        sanitized = self.sanitize_for_provider(text)
        
        # Add additional hedging for patients
        # (Simplified for now)
        
        return sanitized
    
    # ===== Template Initialization =====
    
    def _initialize_forbidden_patterns(self) -> Dict[LanguageViolationType, List[tuple]]:
        """Initialize forbidden phrase patterns."""
        return {
            LanguageViolationType.DIAGNOSTIC_CLAIM: [
                (r'\byou have\b', "pattern consistent with"),
                (r'\bdiagnosed with\b', "estimated to be consistent with"),
                (r'\byou are diabetic\b', "glucose patterns suggest prediabetes/diabetes range"),
                (r'\bconfirms\b', "suggests"),
                (r'\bindicates disease\b', "pattern consistent with"),
                (r'\bdiagnosis of\b', "estimated physiological state consistent with"),
            ],
            LanguageViolationType.DEFINITIVE_STATEMENT: [
                (r'\bdefinitely\b', "likely"),
                (r'\bcertainly\b', "probably"),
                (r'\bis\b', "appears to be"),
                (r'\bwill\b', "may"),
            ],
            LanguageViolationType.MEDICAL_ADVICE: [
                (r'\byou should take\b', "consider discussing with your clinician"),
                (r'\bstop taking\b', "consult your healthcare provider before changing"),
                (r'\bstart medication\b', "medication options may be discussed with your clinician"),
                (r'\btreatment is\b', "treatment options include (discuss with clinician)"),
            ],
            LanguageViolationType.CAUSAL_CLAIM: [
                (r'\bcauses your\b', "may be associated with"),
                (r'\bdue to\b', "potentially related to"),
                (r'\bresults from\b', "consistent with"),
            ],
            LanguageViolationType.PREDICTIVE_CERTAINTY: [
                (r'\bwill develop\b', "may be at increased risk for"),
                (r'\bgoing to\b', "trajectory suggests possible"),
                (r'\bpredicts\b', "pattern suggests"),
            ],
        }
    
    def _initialize_safe_templates(self) -> Dict[str, List[SafePhrasing]]:
        """Initialize safe phrase templates."""
        return {
            "range_statement": [
                SafePhrasing(
                    template="Estimated {marker} range: {low}-{high} {units} ({qualifier}confidence)",
                    example="Estimated glucose range: 95-105 mg/dL (moderate confidence)",
                    confidence_threshold=0.5
                ),
                SafePhrasing(
                    template="Probable {marker} range: {low}-{high} {units} ({qualifier}confidence)",
                    example="Probable glucose range: 95-105 mg/dL (low confidence)",
                    confidence_threshold=0.0
                ),
            ],
            "pattern_statement": [
                SafePhrasing(
                    template="Pattern {qualifier}consistent with {pattern_description}",
                    example="Pattern moderately consistent with prediabetic glucose levels",
                    confidence_threshold=0.5
                ),
                SafePhrasing(
                    template="Data {qualifier}suggests {pattern_description}",
                    example="Data suggests elevated glucose patterns",
                    confidence_threshold=0.3
                ),
            ],
            "trend_statement": [
                SafePhrasing(
                    template="{Marker} {qualifier}trending {direction} ({hedge})",
                    example="Glucose moderately trending upward (based on limited data)",
                    confidence_threshold=0.4
                ),
                SafePhrasing(
                    template="{Marker} appears to be {direction} ({hedge})",
                    example="Glucose appears to be increasing (preliminary estimate)",
                    confidence_threshold=0.3
                ),
            ],
            "recommendation_statement": [
                SafePhrasing(
                    template="Consider discussing {suggestion} with your healthcare provider",
                    example="Consider discussing glucose monitoring with your healthcare provider",
                    confidence_threshold=0.0
                ),
                SafePhrasing(
                    template="{suggestion} may be worth clinical review",
                    example="Recent glucose elevation may be worth clinical review",
                    confidence_threshold=0.4
                ),
            ],
            "risk_statement": [
                SafePhrasing(
                    template="Patterns {qualifier}suggest {risk_level} probability of {condition}",
                    example="Patterns moderately suggest elevated probability of prediabetes",
                    confidence_threshold=0.5
                ),
                SafePhrasing(
                    template="Estimated {risk_level} risk for {condition} ({hedge})",
                    example="Estimated moderate risk for prediabetes (based on current data)",
                    confidence_threshold=0.4
                ),
            ],
            "threshold_crossing": [
                SafePhrasing(
                    template="{Marker} {qualifier}in range associated with {clinical_category}",
                    example="Glucose moderately in range associated with prediabetes",
                    confidence_threshold=0.5
                ),
                SafePhrasing(
                    template="{Marker} approaching threshold for {clinical_category}",
                    example="Glucose approaching threshold for prediabetes",
                    confidence_threshold=0.3
                ),
            ],
            "change_detected": [
                SafePhrasing(
                    template="{Marker} {hedge}changed by {magnitude} ({direction})",
                    example="Glucose appears to have changed by 15 mg/dL (increase)",
                    confidence_threshold=0.5
                ),
                SafePhrasing(
                    template="Possible {direction} in {marker} detected ({hedge})",
                    example="Possible increase in glucose detected (requires confirmation)",
                    confidence_threshold=0.3
                ),
            ],
            "measurement_recommendation": [
                SafePhrasing(
                    template="{Measurement} could help refine estimates for {outputs}",
                    example="HbA1c test could help refine estimates for diabetes risk",
                    confidence_threshold=0.0
                ),
                SafePhrasing(
                    template="Additional {measurement} data would strengthen confidence in {outputs}",
                    example="Additional glucose monitoring would strengthen confidence in metabolic estimates",
                    confidence_threshold=0.3
                ),
            ],
        }
    
    def _initialize_confidence_qualifiers(self) -> Dict[str, str]:
        """Initialize confidence-based qualifiers."""
        return {
            "very_high": "",  # 0.85+: No qualifier needed
            "high": "likely ",  # 0.70-0.85
            "moderate": "moderately ",  # 0.50-0.70
            "low": "possibly ",  # 0.30-0.50
            "very_low": "tentatively ",  # <0.30
        }
    
    def _initialize_evidence_hedges(self) -> Dict[str, str]:
        """Initialize evidence-grade-based hedges."""
        return {
            "A": "based on strong data",
            "B": "based on good data",
            "C": "based on limited data",
            "D": "preliminary estimate",
            "F": "insufficient data quality"
        }
    
    def _select_qualifier(self, confidence: Optional[float]) -> str:
        """Select appropriate qualifier for confidence level."""
        if confidence is None:
            return "moderately "
        
        if confidence >= 0.85:
            return self.confidence_qualifiers["very_high"]
        elif confidence >= 0.70:
            return self.confidence_qualifiers["high"]
        elif confidence >= 0.50:
            return self.confidence_qualifiers["moderate"]
        elif confidence >= 0.30:
            return self.confidence_qualifiers["low"]
        else:
            return self.confidence_qualifiers["very_low"]
    
    def _select_hedge(self, evidence_grade: Optional[str]) -> str:
        """Select appropriate hedge for evidence grade."""
        if evidence_grade is None:
            return "based on available data"
        
        return self.evidence_hedges.get(evidence_grade, "based on available data")


# ===== Singleton =====

_language_controller_instance = None

def get_language_controller() -> LanguageController:
    """Get singleton instance of language controller."""
    global _language_controller_instance
    if _language_controller_instance is None:
        _language_controller_instance = LanguageController()
    return _language_controller_instance


# ===== Validation Decorator =====

def enforce_safe_language(func):
    """
    Decorator to enforce safe language on function outputs.
    
    Usage:
        @enforce_safe_language
        def generate_report(...) -> str:
            ...
    """
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        
        if isinstance(result, str):
            controller = get_language_controller()
            violations = controller.validate_text(result)
            
            if violations:
                # Log violations (in production)
                print(f"WARNING: Language violations detected in {func.__name__}")
                for v in violations:
                    print(f"  - {v.violation_type.value}: {v.violating_phrase}")
                
                # Auto-sanitize
                sanitized = controller.sanitize_for_patient(result)
                return sanitized
        
        return result
    
    return wrapper
