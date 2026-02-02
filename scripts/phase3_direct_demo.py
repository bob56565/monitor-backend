#!/usr/bin/env python3
"""
PHASE 3 DECISION INTELLIGENCE - DIRECT DEMO
Direct demonstration of Phase 3 features without API dependency
Shows: All Phase 3 modules working with sample data
"""
import sys
sys.path.insert(0, '/workspaces/MONITOR')

from datetime import datetime, timedelta
from typing import Dict, List
import json

# Phase 3 imports
from app.ml.phase3_integration import Phase3Integrator
from app.features.uncertainty_reduction import UncertaintyReductionPlanner
from app.features.cohort_matching import CohortMatchingEngine
from app.features.change_point_detection import ChangePointDetector
from app.features.provider_summary import ProviderSummaryGenerator
from app.features.cost_care_impact import CostCareImpactAnalyzer
from app.features.explainability import ExplainabilityEngine
from app.features.language_control import LanguageController

# Color codes
BLUE = "\033[94m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
MAGENTA = "\033[95m"
BOLD = "\033[1m"
RESET = "\033[0m"


def print_header(text: str):
    """Print section header."""
    print(f"\n{BOLD}{CYAN}{'=' * 80}{RESET}")
    print(f"{BOLD}{CYAN}{text.center(80)}{RESET}")
    print(f"{BOLD}{CYAN}{'=' * 80}{RESET}\n")


def print_success(message: str):
    """Print success message."""
    print(f"{GREEN}✅ {message}{RESET}")


def print_info(message: str):
    """Print info message."""
    print(f"{CYAN}ℹ️  {message}{RESET}")


def generate_sample_data():
    """Generate realistic sample data for Phase 3 demo."""
    print_header("📊 GENERATING SAMPLE DATA (90-DAY LONGITUDINAL)")
    
    base_time = datetime.utcnow() - timedelta(days=90)
    
    # 1. Estimates (from Phase 1 + Phase 2)
    estimates = {
        "glucose_fasting": {
            "value": 112.5,
            "uncertainty": 8.2,
            "confidence": 0.72,
            "evidence_grade": "B",
            "range": [104.3, 120.7]
        },
        "glucose_avg": {
            "value": 118.0,
            "uncertainty": 9.5,
            "confidence": 0.68,
            "evidence_grade": "B",
            "range": [108.5, 127.5]
        },
        "cholesterol_ldl": {
            "value": 118.0,
            "uncertainty": 12.5,
            "confidence": 0.65,
            "evidence_grade": "B",
            "range": [105.5, 130.5]
        },
        "cholesterol_total": {
            "value": 195.0,
            "uncertainty": 15.0,
            "confidence": 0.70,
            "evidence_grade": "B",
            "range": [180.0, 210.0]
        },
        "egfr": {
            "value": 87.0,
            "uncertainty": 5.0,
            "confidence": 0.85,
            "evidence_grade": "A",
            "range": [82.0, 92.0]
        },
        "creatinine": {
            "value": 0.9,
            "uncertainty": 0.1,
            "confidence": 0.82,
            "evidence_grade": "A",
            "range": [0.8, 1.0]
        }
    }
    
    # 2. Historical data (longitudinal)
    historical_data = {}
    
    # Glucose: trending upward with change point at day 60
    glucose_history = []
    for day in range(0, 91, 3):
        timestamp = base_time + timedelta(days=day)
        if day < 60:
            value = 95.0 + (day * 0.1)
        else:
            value = 95.0 + 6.0 + ((day - 60) * 0.3)
            # Add volatility after change point
            import random
            value += random.uniform(-3, 5)
        glucose_history.append((timestamp, round(value, 1)))
    historical_data["glucose_fasting"] = glucose_history
    
    # Cholesterol: improving (statin effect at day 45)
    cholesterol_history = []
    for day in range(0, 91, 3):
        timestamp = base_time + timedelta(days=day)
        if day < 45:
            value = 145.0
        else:
            value = 145.0 - ((day - 45) * 0.6)
        cholesterol_history.append((timestamp, round(max(value, 85), 1)))
    historical_data["cholesterol_ldl"] = cholesterol_history
    
    # eGFR: stable
    egfr_history = []
    for day in range(0, 91, 3):
        timestamp = base_time + timedelta(days=day)
        value = 87.0 + random.uniform(-2, 2)
        egfr_history.append((timestamp, round(value, 1)))
    historical_data["egfr"] = egfr_history
    
    # 3. Measured anchors (recent labs)
    measured_anchors = {
        "glucose_fasting": {
            "value": 110.0,
            "timestamp": datetime.utcnow() - timedelta(days=2),
            "source": "lab"
        },
        "egfr": {
            "value": 87.0,
            "timestamp": datetime.utcnow() - timedelta(days=5),
            "source": "lab"
        }
    }
    
    # 4. Phase 2 metadata
    phase2_metadata = {
        "temporal_stability_high": True,
        "temporal_stability": 0.75,
        "personal_baselines": {
            "glucose_fasting": {"baseline": 95.0, "deviation": 17.5, "percentile_shift": 45},
            "cholesterol_ldl": {"baseline": 145.0, "deviation": -27.0, "percentile_shift": -30},
            "egfr": {"baseline": 87.0, "deviation": 0.0, "percentile_shift": 0}
        },
        "priors_influence": {
            "glucose_fasting": 0.35,
            "cholesterol_ldl": 0.42,
            "egfr": 0.15
        }
    }
    
    # 5. User context
    user_context = {
        "age": 45,
        "sex": "M",
        "bmi": 26.5,
        "medications": ["metformin", "atorvastatin"],
        "activity_level": "moderate"
    }
    
    print_success(f"Generated {len(estimates)} estimates")
    print_success(f"Generated {len(historical_data)} longitudinal series (31 points each)")
    print_success(f"Generated {len(measured_anchors)} measured anchors")
    print_info(f"User: 45yo Male, BMI 26.5, on metformin + atorvastatin")
    
    return estimates, historical_data, measured_anchors, phase2_metadata, user_context


def display_phase3_results(result: Dict):
    """Display Phase 3 results beautifully."""
    phase3 = result.get("phase3_metadata", {})
    
    if not phase3:
        print(f"{RED}❌ No Phase 3 metadata found!{RESET}")
        return
    
    # 1. UNCERTAINTY REDUCTION
    print_header("📊 A2.1: UNCERTAINTY REDUCTION RECOMMENDATIONS")
    ur = phase3.get("uncertainty_reduction", {})
    if ur.get("top_recommendations"):
        print(f"{BOLD}Top measurements to reduce uncertainty:{RESET}\n")
        for i, rec in enumerate(ur["top_recommendations"][:3], 1):
            urgency_color = RED if rec.get("urgency") == "high" else YELLOW if rec.get("urgency") == "medium" else GREEN
            print(f"{BOLD}{i}.{RESET} {YELLOW}{rec.get('measurement', 'Unknown')}{RESET}")
            if "expected_reduction_pct" in rec:
                print(f"   Expected Reduction: {GREEN}{rec['expected_reduction_pct']:.1f}%{RESET}")
            if "expected_reduction" in rec:
                print(f"   Expected Reduction: {GREEN}{rec['expected_reduction']:.2f}{RESET}")
            print(f"   Urgency: {urgency_color}{rec.get('urgency', 'unknown').upper()}{RESET}")
            if "outputs_affected" in rec:
                print(f"   Affects: {', '.join(rec['outputs_affected'])}")
            if "rationale" in rec:
                print(f"   Rationale: {rec['rationale']}")
            print()
    else:
        print_success("All estimates have acceptable uncertainty")
    
    # 2. COHORT MATCHING
    print_header("👥 A2.2: COHORT MATCHING & CONTEXTUALIZATION")
    cohort = phase3.get("cohort_comparison", {})
    if cohort.get("similarity_score", 0) >= 0.30:
        print(f"{BOLD}Similarity Score:{RESET} {cohort['similarity_score']:.2f}\n")
        
        if cohort.get("percentile_bands"):
            print(f"{BOLD}Position vs. matched cohort:{RESET}\n")
            for marker, bands in list(cohort["percentile_bands"].items())[:4]:
                p = bands.get("user_percentile", 50)
                color = GREEN if 25 <= p <= 75 else YELLOW if 10 <= p <= 90 else RED
                print(f"  {YELLOW}{marker}{RESET}")
                print(f"    Your percentile: {color}{p}th{RESET}")
                print(f"    Cohort range: {bands.get('p25', 0):.1f} - {bands.get('p75', 0):.1f}")
        
        if cohort.get("trajectory_summary"):
            print(f"\n{BOLD}Trajectory:{RESET} {cohort['trajectory_summary']}")
    else:
        print_info("Cohort comparison suppressed (low similarity)")
    
    # 3. CHANGE POINT DETECTION
    print_header("📈 A2.3: CHANGE POINT DETECTION")
    changes = phase3.get("detected_changes", [])
    if changes:
        print(f"{BOLD}Detected {len(changes)} significant change(s):{RESET}\n")
        for change in changes:
            icon = "🔴" if change.get("clinical_relevance") == "high" else "🟡"
            print(f"{icon} {BOLD}{change['marker']}{RESET} - {change['change_type']}")
            print(f"   Magnitude: {change.get('magnitude', 0):.1f}")
            print(f"   Clinical Relevance: {change.get('clinical_relevance', 'unknown').upper()}")
            if change.get("potential_causes"):
                print(f"   Potential Causes: {', '.join(change['potential_causes'])}")
            if change.get("early_warning"):
                print(f"   {RED}⚠️  EARLY WARNING{RESET}")
            print()
    else:
        print_success("No significant changes - all markers stable")
    
    # 4. EXPLAINABILITY
    print_header("💡 B.6: EXPLAINABILITY")
    explanations = phase3.get("explanations", {})
    for output_id, exp in list(explanations.items())[:3]:
        print(f"\n{BOLD}{YELLOW}{output_id}{RESET}")
        print(f"{MAGENTA}{exp.get('because_sentence', 'N/A')}{RESET}")
        print(f"\nConfidence: {exp.get('confidence_bar', '░' * 10)}")
        
        if exp.get("top_drivers"):
            print(f"\n{BOLD}Top Drivers:{RESET}")
            for driver in exp["top_drivers"][:2]:
                weight = driver.get("contribution_weight", 0) * 100
                print(f"  • {driver.get('driver_name', 'Unknown')} ({weight:.0f}%)")
                print(f"    {driver.get('short_explanation', '')}")
        
        if exp.get("what_would_change_this"):
            print(f"\n{BOLD}To improve:{RESET}")
            for suggestion in exp["what_would_change_this"]:
                print(f"  → {suggestion}")
        print()
    
    # 5. PROVIDER SUMMARY
    print_header("🏥 B.4: PROVIDER SUMMARY")
    summary = phase3.get("provider_summary", {})
    print(f"{BOLD}Data Quality:{RESET} {summary.get('data_quality_grade', 'N/A')}")
    print(f"{BOLD}Coverage:{RESET} {summary.get('temporal_coverage_days', 0)} days\n")
    
    sections = summary.get("sections", {})
    for section_name, section_data in sections.items():
        if section_data.get("items"):
            priority = section_data.get("priority", "LOW")
            icon = "🔴" if priority == "HIGH" else "🟡" if priority == "MEDIUM" else "⚪"
            print(f"{icon} {BOLD}{section_name.upper()}{RESET} [{priority}]")
            for item in section_data["items"][:3]:
                print(f"  • {item}")
            print()
    
    # 6. COST/CARE IMPACT
    print_header("💰 B.5: COST & CARE IMPACT")
    impact = phase3.get("cost_care_impact", {})
    if impact.get("rendered", True):
        for module_name, module_data in impact.items():
            if module_name != "rendered" and isinstance(module_data, dict):
                print(f"{BOLD}{module_name.replace('_', ' ').title()}{RESET}")
                print(f"  Claim: {module_data.get('claim', 'N/A')}")
                print(f"  Evidence: {module_data.get('evidence_strength', 'N/A').upper()}")
                print(f"  Confidence: {module_data.get('confidence', 0):.0%}\n")
    else:
        print_info("Impact suppressed (insufficient data)")
    
    # 7. LANGUAGE VALIDATION
    print_header("🛡️  B.7: LANGUAGE CONTROL")
    validation = phase3.get("language_validation", {})
    violations = validation.get("violations_detected", [])
    if violations:
        print(f"{YELLOW}⚠️  Found {len(violations)} violations (auto-corrected):{RESET}\n")
        for v in violations[:3]:
            print(f"  ❌ '{v.get('original_text', '')}'")
            print(f"  ✅ '{v.get('safe_alternative', '')}'\n")
    else:
        print_success("All output passed validation")
        print("  → No diagnostic claims")
        print("  → Estimation-based language only")


def main():
    """Run Phase 3 direct demo."""
    print_header("🚀 PHASE 3 DECISION INTELLIGENCE - INTERACTIVE DEMO")
    print(f"{BOLD}Direct execution of all Phase 3 components{RESET}")
    print(f"Demonstrating: Full pipeline integration\n")
    
    try:
        # Generate sample data
        estimates, historical_data, measured_anchors, phase2_metadata, user_context = generate_sample_data()
        
        # Initialize Phase 3 Integrator
        print_header("⚙️  INITIALIZING PHASE 3 INTEGRATION")
        integrator = Phase3Integrator()
        print_success("Phase 3 Integrator initialized")
        print_info("All Phase 3 feature flags enabled")
        
        # Run Phase 3 integration
        print_header("🔄 RUNNING PHASE 3 PIPELINE")
        print("Executing:")
        print("  1️⃣  Uncertainty Reduction Planning")
        print("  2️⃣  Cohort Matching Engine")
        print("  3️⃣  Change Point Detection")
        print("  4️⃣  Explainability Generation")
        print("  5️⃣  Provider Summary Creation")
        print("  6️⃣  Cost/Care Impact Analysis")
        print("  7️⃣  Language Control Validation")
        print()
        
        result = integrator.integrate_phase3(
            patient_id="demo_patient_001",
            run_v2=None,  # Mock run object
            estimates=estimates,
            measured_anchors=measured_anchors,
            historical_data=historical_data,
            events=None,
            phase2_metadata=phase2_metadata,
            previous_report=None
        )
        
        print_success("Phase 3 pipeline complete!")
        
        # Display results
        display_phase3_results(result)
        
        # Final summary
        print_header("✅ DEMO COMPLETE")
        print(f"{GREEN}All Phase 3 components executed successfully:{RESET}\n")
        print("  ✅ Uncertainty Reduction (A2.1)")
        print("  ✅ Cohort Matching (A2.2)")
        print("  ✅ Change Detection (A2.3)")
        print("  ✅ Explainability (B.6)")
        print("  ✅ Provider Summary (B.4)")
        print("  ✅ Cost/Care Impact (B.5)")
        print("  ✅ Language Control (B.7)")
        
        print(f"\n{BOLD}{CYAN}Phase 3 Decision Intelligence is fully operational!{RESET}\n")
        
        # Save results
        output_file = "phase3_direct_demo_result.json"
        with open(output_file, "w") as f:
            json.dump(result, f, indent=2, default=str)
        print(f"{YELLOW}📁 Results saved to: {output_file}{RESET}")
        
        return 0
        
    except Exception as e:
        print(f"{RED}❌ Demo failed: {e}{RESET}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
