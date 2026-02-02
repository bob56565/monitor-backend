"""
Lightweight API endpoint for MONITOR inference.
Can be deployed as Cloudflare Worker or standalone FastAPI.
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
import json

app = FastAPI(title="MONITOR API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load reference data
REFERENCE_RANGES = {
    "glucose": {"unit": "mg/dL", "ref_low": 70, "ref_high": 100, "prediabetes": 100, "diabetes": 126},
    "hemoglobin_a1c": {"unit": "%", "ref_low": 4.0, "ref_high": 5.6, "prediabetes": 5.7, "diabetes": 6.5},
    "total_cholesterol": {"unit": "mg/dL", "ref_low": 125, "ref_high": 200, "borderline": 200, "high": 240},
    "ldl_cholesterol": {"unit": "mg/dL", "ref_low": 50, "ref_high": 100, "borderline": 130, "high": 160},
    "hdl_cholesterol": {"unit": "mg/dL", "ref_low": 40, "ref_high": 60, "low_risk": 60},
    "triglycerides": {"unit": "mg/dL", "ref_low": 50, "ref_high": 150, "borderline": 150, "high": 200},
    "sodium": {"unit": "mmol/L", "ref_low": 136, "ref_high": 145},
    "potassium": {"unit": "mmol/L", "ref_low": 3.5, "ref_high": 5.0},
    "creatinine": {"unit": "mg/dL", "ref_low": 0.7, "ref_high": 1.3},
    "bun": {"unit": "mg/dL", "ref_low": 7, "ref_high": 20},
}


class LabInput(BaseModel):
    glucose: Optional[float] = None
    hemoglobin_a1c: Optional[float] = None
    total_cholesterol: Optional[float] = None
    ldl_cholesterol: Optional[float] = None
    hdl_cholesterol: Optional[float] = None
    triglycerides: Optional[float] = None
    sodium: Optional[float] = None
    potassium: Optional[float] = None
    creatinine: Optional[float] = None
    bun: Optional[float] = None
    age: Optional[int] = None
    sex: Optional[str] = None


class InferenceOutput(BaseModel):
    key: str
    title: str
    risk_level: str
    confidence: float
    explanation: str
    contributing_factors: List[str]
    recommendations: List[str]


class InferenceResponse(BaseModel):
    status: str
    inferences: List[InferenceOutput]
    raw_assessments: Dict[str, Any]
    metadata: Dict[str, Any]


def assess_glycemic_status(glucose: Optional[float], a1c: Optional[float]) -> Optional[InferenceOutput]:
    """Assess diabetes/prediabetes risk based on ADA criteria."""
    if glucose is None and a1c is None:
        return None
    
    factors = []
    risk = "LOW"
    confidence = 0.75
    
    # ADA criteria
    if glucose is not None:
        if glucose >= 126:
            risk = "HIGH"
            factors.append(f"Fasting glucose {glucose} mg/dL (≥126 = diabetes)")
            confidence = 0.92
        elif glucose >= 100:
            risk = "MODERATE" if risk != "HIGH" else risk
            factors.append(f"Fasting glucose {glucose} mg/dL (100-125 = prediabetes)")
            confidence = max(confidence, 0.85)
    
    if a1c is not None:
        if a1c >= 6.5:
            risk = "HIGH"
            factors.append(f"HbA1c {a1c}% (≥6.5 = diabetes)")
            confidence = 0.94
        elif a1c >= 5.7:
            risk = "MODERATE" if risk != "HIGH" else risk
            factors.append(f"HbA1c {a1c}% (5.7-6.4 = prediabetes)")
            confidence = max(confidence, 0.87)
    
    if not factors:
        factors.append("Blood sugar markers within normal range")
    
    recommendations = []
    if risk == "HIGH":
        recommendations = [
            "Consult healthcare provider for diabetes management",
            "Consider medication evaluation",
            "Monitor blood glucose regularly"
        ]
    elif risk == "MODERATE":
        recommendations = [
            "Lifestyle modifications recommended",
            "Increase physical activity",
            "Reduce refined carbohydrate intake",
            "Retest in 3-6 months"
        ]
    else:
        recommendations = ["Maintain healthy lifestyle", "Annual screening recommended"]
    
    return InferenceOutput(
        key="glycemic_status",
        title="Glycemic Status Assessment",
        risk_level=risk,
        confidence=confidence,
        explanation=f"Based on ADA diagnostic criteria. {'; '.join(factors)}",
        contributing_factors=factors,
        recommendations=recommendations
    )


def assess_cardiovascular_risk(
    cholesterol: Optional[float],
    ldl: Optional[float],
    hdl: Optional[float],
    triglycerides: Optional[float]
) -> Optional[InferenceOutput]:
    """Assess cardiovascular risk based on AHA guidelines."""
    if all(v is None for v in [cholesterol, ldl, hdl, triglycerides]):
        return None
    
    factors = []
    risk = "LOW"
    confidence = 0.70
    risk_points = 0
    
    if cholesterol is not None:
        if cholesterol >= 240:
            risk_points += 2
            factors.append(f"Total cholesterol {cholesterol} mg/dL (high ≥240)")
        elif cholesterol >= 200:
            risk_points += 1
            factors.append(f"Total cholesterol {cholesterol} mg/dL (borderline 200-239)")
    
    if ldl is not None:
        if ldl >= 160:
            risk_points += 2
            factors.append(f"LDL {ldl} mg/dL (high ≥160)")
        elif ldl >= 130:
            risk_points += 1
            factors.append(f"LDL {ldl} mg/dL (borderline 130-159)")
    
    if hdl is not None:
        if hdl < 40:
            risk_points += 2
            factors.append(f"HDL {hdl} mg/dL (low <40, independent risk factor)")
        elif hdl >= 60:
            risk_points -= 1
            factors.append(f"HDL {hdl} mg/dL (protective ≥60)")
    
    if triglycerides is not None:
        if triglycerides >= 200:
            risk_points += 1
            factors.append(f"Triglycerides {triglycerides} mg/dL (high ≥200)")
        elif triglycerides >= 150:
            factors.append(f"Triglycerides {triglycerides} mg/dL (borderline 150-199)")
    
    if risk_points >= 3:
        risk = "HIGH"
        confidence = 0.88
    elif risk_points >= 1:
        risk = "MODERATE"
        confidence = 0.82
    
    if not factors:
        factors.append("Lipid panel within desirable ranges")
    
    recommendations = []
    if risk == "HIGH":
        recommendations = [
            "Consult cardiologist",
            "Consider statin therapy evaluation",
            "Mediterranean or DASH diet recommended",
            "Regular cardiovascular exercise"
        ]
    elif risk == "MODERATE":
        recommendations = [
            "Dietary modifications recommended",
            "Increase omega-3 fatty acids",
            "Regular aerobic exercise",
            "Retest in 6 months"
        ]
    else:
        recommendations = ["Maintain heart-healthy lifestyle", "Annual lipid panel"]
    
    return InferenceOutput(
        key="cardiovascular_risk",
        title="Cardiovascular Risk Assessment",
        risk_level=risk,
        confidence=confidence,
        explanation=f"Based on AHA lipid guidelines. {'; '.join(factors) if factors else 'All markers optimal.'}",
        contributing_factors=factors,
        recommendations=recommendations
    )


def assess_metabolic_syndrome(
    glucose: Optional[float],
    triglycerides: Optional[float],
    hdl: Optional[float]
) -> Optional[InferenceOutput]:
    """Assess metabolic syndrome markers (partial - needs BP and waist)."""
    if all(v is None for v in [glucose, triglycerides, hdl]):
        return None
    
    criteria_met = 0
    factors = []
    
    if glucose is not None and glucose >= 100:
        criteria_met += 1
        factors.append(f"Elevated fasting glucose ({glucose} mg/dL ≥100)")
    
    if triglycerides is not None and triglycerides >= 150:
        criteria_met += 1
        factors.append(f"Elevated triglycerides ({triglycerides} mg/dL ≥150)")
    
    if hdl is not None and hdl < 40:
        criteria_met += 1
        factors.append(f"Low HDL ({hdl} mg/dL <40)")
    
    risk = "LOW"
    confidence = 0.65  # Lower confidence due to incomplete criteria
    
    if criteria_met >= 2:
        risk = "HIGH"
        confidence = 0.78
    elif criteria_met == 1:
        risk = "MODERATE"
        confidence = 0.72
    
    explanation = f"{criteria_met} of 3 measured criteria present"
    if criteria_met > 0:
        explanation += f": {', '.join(factors)}"
    explanation += ". Note: Complete assessment requires blood pressure and waist circumference."
    
    recommendations = []
    if risk == "HIGH":
        recommendations = [
            "Comprehensive metabolic evaluation recommended",
            "Weight management if applicable",
            "Regular physical activity",
            "Blood pressure monitoring"
        ]
    elif risk == "MODERATE":
        recommendations = [
            "Lifestyle modifications",
            "Monitor additional markers",
            "Consider comprehensive metabolic panel"
        ]
    else:
        recommendations = ["Continue healthy habits", "Regular monitoring"]
    
    return InferenceOutput(
        key="metabolic_syndrome",
        title="Metabolic Syndrome Markers",
        risk_level=risk,
        confidence=confidence,
        explanation=explanation,
        contributing_factors=factors if factors else ["No metabolic syndrome markers detected"],
        recommendations=recommendations
    )


def assess_kidney_function(
    creatinine: Optional[float],
    bun: Optional[float],
    age: Optional[int] = None,
    sex: Optional[str] = None
) -> Optional[InferenceOutput]:
    """Assess kidney function using available markers."""
    if creatinine is None and bun is None:
        return None
    
    factors = []
    risk = "LOW"
    confidence = 0.70
    
    # Simple assessment (full eGFR would need CKD-EPI formula)
    if creatinine is not None:
        if creatinine > 1.3:
            risk = "MODERATE"
            factors.append(f"Elevated creatinine ({creatinine} mg/dL)")
            confidence = 0.75
        if creatinine > 2.0:
            risk = "HIGH"
            factors.append(f"Significantly elevated creatinine ({creatinine} mg/dL)")
            confidence = 0.85
    
    if bun is not None:
        if bun > 20:
            if risk != "HIGH":
                risk = "MODERATE"
            factors.append(f"Elevated BUN ({bun} mg/dL)")
    
    if not factors:
        factors.append("Kidney function markers within normal range")
    
    return InferenceOutput(
        key="kidney_function",
        title="Kidney Function Assessment",
        risk_level=risk,
        confidence=confidence,
        explanation=f"Based on serum markers. {'; '.join(factors)}",
        contributing_factors=factors,
        recommendations=[
            "Consult nephrologist" if risk == "HIGH" else "Regular monitoring",
            "Stay hydrated",
            "Monitor blood pressure"
        ] if risk != "LOW" else ["Maintain hydration", "Annual screening"]
    )


@app.get("/")
def root():
    return {
        "service": "MONITOR Health Intelligence API",
        "version": "1.0.0",
        "status": "operational",
        "endpoints": {
            "/infer": "POST - Run health inference on lab values",
            "/reference": "GET - Get reference ranges",
            "/health": "GET - Health check"
        }
    }


@app.get("/health")
def health():
    return {"status": "healthy", "service": "monitor-api"}


@app.get("/reference")
def get_reference_ranges():
    return {"reference_ranges": REFERENCE_RANGES}


@app.post("/infer", response_model=InferenceResponse)
def run_inference(labs: LabInput):
    """Run clinical inference on provided lab values."""
    inferences = []
    raw = {}
    
    # Glycemic assessment
    glycemic = assess_glycemic_status(labs.glucose, labs.hemoglobin_a1c)
    if glycemic:
        inferences.append(glycemic)
        raw["glycemic"] = {"glucose": labs.glucose, "a1c": labs.hemoglobin_a1c}
    
    # Cardiovascular assessment
    cardio = assess_cardiovascular_risk(
        labs.total_cholesterol,
        labs.ldl_cholesterol,
        labs.hdl_cholesterol,
        labs.triglycerides
    )
    if cardio:
        inferences.append(cardio)
        raw["lipids"] = {
            "total": labs.total_cholesterol,
            "ldl": labs.ldl_cholesterol,
            "hdl": labs.hdl_cholesterol,
            "trig": labs.triglycerides
        }
    
    # Metabolic syndrome
    metsyn = assess_metabolic_syndrome(
        labs.glucose,
        labs.triglycerides,
        labs.hdl_cholesterol
    )
    if metsyn:
        inferences.append(metsyn)
    
    # Kidney function
    kidney = assess_kidney_function(
        labs.creatinine,
        labs.bun,
        labs.age,
        labs.sex
    )
    if kidney:
        inferences.append(kidney)
        raw["kidney"] = {"creatinine": labs.creatinine, "bun": labs.bun}
    
    return InferenceResponse(
        status="success",
        inferences=inferences,
        raw_assessments=raw,
        metadata={
            "input_count": sum(1 for v in labs.dict().values() if v is not None),
            "inference_count": len(inferences),
            "api_version": "1.0.0"
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
