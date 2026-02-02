"""
MONITOR Validation Test Cases
=============================
Scientifically validated test cases to ensure inference accuracy.
"""

import sys
sys.path.insert(0, '/root/clawd/monitor-backend')

from app.ml.real_inference_engine import (
    run_full_inference,
    assess_glycemic_status,
    assess_cardiovascular_risk,
    assess_kidney_function,
    assess_metabolic_syndrome,
    assess_thyroid_function,
    assess_vitamin_d_status,
    assess_inflammation,
    calculate_egfr_ckdepi_2021,
    calculate_homa_ir,
    calculate_bmi,
    RiskLevel
)

# =============================================================================
# VALIDATION TEST CASES
# =============================================================================

GLYCEMIC_TEST_CASES = [
    {
        "name": "Normal Glycemic Status",
        "inputs": {"glucose": 85, "a1c": 5.2, "age": 35, "bmi": 22},
        "expected_risk_level": RiskLevel.LOW,
        "expected_risk_range": (0, 35)
    },
    {
        "name": "Prediabetes - Glucose Only",
        "inputs": {"glucose": 110, "age": 50},
        "expected_risk_level": RiskLevel.MODERATE,
        # Note: Single high LDL without other factors may be LOW-MODERATE borderline
        "expected_risk_range": (40, 70)
    },
    {
        "name": "Prediabetes - A1c Only",
        "inputs": {"a1c": 6.0, "age": 45},
        "expected_risk_level": RiskLevel.MODERATE,
        # Note: Single high LDL without other factors may be LOW-MODERATE borderline
        "expected_risk_range": (40, 70)
    },
    {
        "name": "Diabetes Range - Both Elevated",
        "inputs": {"glucose": 140, "a1c": 7.2, "age": 55, "bmi": 32},
        "expected_risk_level": RiskLevel.HIGH,
        "expected_risk_range": (75, 100)
    },
    {
        "name": "Borderline with Risk Factors",
        "inputs": {"glucose": 100, "a1c": 5.7, "age": 52, "bmi": 29},
        "expected_risk_level": RiskLevel.MODERATE,
        # Note: Single high LDL without other factors may be LOW-MODERATE borderline
        "expected_risk_range": (40, 75)
    }
]

CARDIOVASCULAR_TEST_CASES = [
    {
        "name": "Optimal Lipids",
        "inputs": {"ldl": 80, "hdl": 65, "triglycerides": 90, "systolic_bp": 115},
        "expected_risk_level": RiskLevel.LOW,
        "expected_risk_range": (0, 30)
    },
    {
        "name": "High LDL Only",
        "inputs": {"ldl": 175, "hdl": 50, "triglycerides": 120},
        "expected_risk_level": RiskLevel.MODERATE,
        # Note: Single high LDL without other factors may be LOW-MODERATE borderline
        "expected_risk_range": (25, 60)
    },
    {
        "name": "Multiple Risk Factors",
        "inputs": {"ldl": 165, "hdl": 35, "triglycerides": 250, "systolic_bp": 145, "smoker": True},
        "expected_risk_level": RiskLevel.HIGH,
        "expected_risk_range": (70, 100)
    },
    {
        "name": "Low HDL with High TG",
        "inputs": {"ldl": 120, "hdl": 32, "triglycerides": 220},
        "expected_risk_level": RiskLevel.MODERATE,
        # Note: Single high LDL without other factors may be LOW-MODERATE borderline
        "expected_risk_range": (40, 70)
    }
]

KIDNEY_TEST_CASES = [
    {
        "name": "Normal Kidney Function - Young Male",
        "inputs": {"creatinine": 1.0, "age": 30, "sex": "M"},
        "expected_egfr_range": (95, 115),
        "expected_risk_level": RiskLevel.LOW
    },
    {
        "name": "Normal Kidney Function - Older Female",
        "inputs": {"creatinine": 0.8, "age": 65, "sex": "F"},
        "expected_egfr_range": (70, 90),
        "expected_risk_level": RiskLevel.LOW
    },
    {
        "name": "CKD Stage 3",
        "inputs": {"creatinine": 1.8, "age": 60, "sex": "M"},
        "expected_egfr_range": (35, 50),
        "expected_risk_level": RiskLevel.MODERATE
    },
    {
        "name": "CKD Stage 4",
        "inputs": {"creatinine": 3.5, "age": 70, "sex": "F"},
        "expected_egfr_range": (12, 20),
        "expected_risk_level": RiskLevel.HIGH
    }
]

CALCULATION_TEST_CASES = [
    # eGFR CKD-EPI 2021 validation
    {
        "name": "eGFR - Reference Male",
        "function": "calculate_egfr_ckdepi_2021",
        "inputs": {"creatinine": 1.0, "age": 50, "sex": "M"},
        "expected_range": (85, 95)
    },
    {
        "name": "eGFR - Reference Female",
        "function": "calculate_egfr_ckdepi_2021",
        "inputs": {"creatinine": 0.7, "age": 50, "sex": "F"},
        "expected_range": (95, 110)
    },
    # HOMA-IR validation
    {
        "name": "HOMA-IR - Normal",
        "function": "calculate_homa_ir",
        "inputs": {"glucose_mg_dl": 90, "insulin_uiu_ml": 8},
        "expected_range": (1.5, 2.0)
    },
    {
        "name": "HOMA-IR - Insulin Resistant",
        "function": "calculate_homa_ir",
        "inputs": {"glucose_mg_dl": 100, "insulin_uiu_ml": 20},
        "expected_range": (4.5, 5.5)
    },
    # BMI validation
    {
        "name": "BMI - Normal",
        "function": "calculate_bmi",
        "inputs": {"weight_kg": 70, "height_cm": 175},
        "expected_range": (22.5, 23.5)
    },
    {
        "name": "BMI - Obese",
        "function": "calculate_bmi",
        "inputs": {"weight_kg": 100, "height_cm": 170},
        "expected_range": (34, 35)
    }
]

def run_validation_tests():
    """Run all validation tests and report results."""
    passed = 0
    failed = 0
    results = []
    
    print("=" * 60)
    print("MONITOR VALIDATION TEST SUITE")
    print("=" * 60)
    
    # Test Glycemic Assessments
    print("\n--- Glycemic Status Tests ---")
    for case in GLYCEMIC_TEST_CASES:
        result = assess_glycemic_status(
            glucose=case["inputs"].get("glucose"),
            a1c=case["inputs"].get("a1c"),
            age=case["inputs"].get("age"),
            bmi=case["inputs"].get("bmi")
        )
        
        risk_level_match = result.risk_level == case["expected_risk_level"]
        risk_score_match = case["expected_risk_range"][0] <= result.risk_score <= case["expected_risk_range"][1]
        
        if risk_level_match and risk_score_match:
            print(f"  ✅ {case['name']}: {result.risk_level.value} ({result.risk_score}%)")
            passed += 1
        else:
            print(f"  ❌ {case['name']}: Expected {case['expected_risk_level'].value}, got {result.risk_level.value} ({result.risk_score}%)")
            failed += 1
    
    # Test Cardiovascular Assessments
    print("\n--- Cardiovascular Risk Tests ---")
    for case in CARDIOVASCULAR_TEST_CASES:
        result = assess_cardiovascular_risk(
            ldl=case["inputs"].get("ldl"),
            hdl=case["inputs"].get("hdl"),
            triglycerides=case["inputs"].get("triglycerides"),
            systolic_bp=case["inputs"].get("systolic_bp"),
            smoker=case["inputs"].get("smoker", False)
        )
        
        risk_level_match = result.risk_level == case["expected_risk_level"]
        risk_score_match = case["expected_risk_range"][0] <= result.risk_score <= case["expected_risk_range"][1]
        
        if risk_level_match and risk_score_match:
            print(f"  ✅ {case['name']}: {result.risk_level.value} ({result.risk_score}%)")
            passed += 1
        else:
            print(f"  ❌ {case['name']}: Expected {case['expected_risk_level'].value}, got {result.risk_level.value} ({result.risk_score}%)")
            failed += 1
    
    # Test Kidney Function
    print("\n--- Kidney Function Tests ---")
    for case in KIDNEY_TEST_CASES:
        egfr = calculate_egfr_ckdepi_2021(
            case["inputs"]["creatinine"],
            case["inputs"]["age"],
            case["inputs"]["sex"]
        )
        result = assess_kidney_function(
            creatinine=case["inputs"]["creatinine"],
            age=case["inputs"]["age"],
            sex=case["inputs"]["sex"]
        )
        
        egfr_match = case["expected_egfr_range"][0] <= egfr <= case["expected_egfr_range"][1]
        risk_level_match = result.risk_level == case["expected_risk_level"]
        
        if egfr_match and risk_level_match:
            print(f"  ✅ {case['name']}: eGFR={egfr}, {result.risk_level.value}")
            passed += 1
        else:
            print(f"  ❌ {case['name']}: eGFR={egfr} (expected {case['expected_egfr_range']}), {result.risk_level.value}")
            failed += 1
    
    # Test Calculations
    print("\n--- Calculation Validation Tests ---")
    for case in CALCULATION_TEST_CASES:
        if case["function"] == "calculate_egfr_ckdepi_2021":
            result = calculate_egfr_ckdepi_2021(**case["inputs"])
        elif case["function"] == "calculate_homa_ir":
            result = calculate_homa_ir(**case["inputs"])
        elif case["function"] == "calculate_bmi":
            result = calculate_bmi(**case["inputs"])
        else:
            continue
        
        if case["expected_range"][0] <= result <= case["expected_range"][1]:
            print(f"  ✅ {case['name']}: {result}")
            passed += 1
        else:
            print(f"  ❌ {case['name']}: {result} (expected {case['expected_range']})")
            failed += 1
    
    # Summary
    print("\n" + "=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print(f"SUCCESS RATE: {passed/(passed+failed)*100:.1f}%")
    print("=" * 60)
    
    return passed, failed

if __name__ == "__main__":
    run_validation_tests()
