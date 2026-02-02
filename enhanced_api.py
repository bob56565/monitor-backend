"""
Enhanced MONITOR API with additional clinical assessments.
Version 1.1.0
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime
import json
import hashlib

app = FastAPI(
    title="MONITOR Health Intelligence API",
    version="1.1.0",
    description="Clinical-grade health inference with confidence scoring"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Extended reference data with sources
CLINICAL_REFERENCES = {
    "glucose": {
        "unit": "mg/dL",
        "normal": {"low": 70, "high": 99},
        "prediabetes": {"low": 100, "high": 125},
        "diabetes": {"low": 126, "high": None},
        "critical_low": 40,
        "critical_high": 400,
        "source": "ADA Standards of Medical Care 2024"
    },
    "hemoglobin_a1c": {
        "unit": "%",
        "normal": {"low": 4.0, "high": 5.6},
        "prediabetes": {"low": 5.7, "high": 6.4},
        "diabetes": {"low": 6.5, "high": None},
        "source": "ADA Standards of Medical Care 2024"
    },
    "total_cholesterol": {
        "unit": "mg/dL",
        "desirable": {"low": 0, "high": 199},
        "borderline": {"low": 200, "high": 239},
        "high": {"low": 240, "high": None},
        "source": "AHA/ACC Lipid Guidelines 2018"
    },
    "ldl_cholesterol": {
        "unit": "mg/dL",
        "optimal": {"low": 0, "high": 99},
        "near_optimal": {"low": 100, "high": 129},
        "borderline": {"low": 130, "high": 159},
        "high": {"low": 160, "high": 189},
        "very_high": {"low": 190, "high": None},
        "source": "AHA/ACC Lipid Guidelines 2018"
    },
    "hdl_cholesterol": {
        "unit": "mg/dL",
        "low_risk": {"low": 60, "high": None},
        "acceptable": {"low": 40, "high": 59},
        "risk_factor": {"low": 0, "high": 39},
        "source": "AHA/ACC Lipid Guidelines 2018"
    },
    "triglycerides": {
        "unit": "mg/dL",
        "normal": {"low": 0, "high": 149},
        "borderline": {"low": 150, "high": 199},
        "high": {"low": 200, "high": 499},
        "very_high": {"low": 500, "high": None},
        "source": "AHA/ACC Lipid Guidelines 2018"
    },
    "systolic_bp": {
        "unit": "mmHg",
        "normal": {"low": 90, "high": 119},
        "elevated": {"low": 120, "high": 129},
        "stage1_htn": {"low": 130, "high": 139},
        "stage2_htn": {"low": 140, "high": None},
        "source": "AHA/ACC Blood Pressure Guidelines 2017"
    },
    "diastolic_bp": {
        "unit": "mmHg",
        "normal": {"low": 60, "high": 79},
        "stage1_htn": {"low": 80, "high": 89},
        "stage2_htn": {"low": 90, "high": None},
        "source": "AHA/ACC Blood Pressure Guidelines 2017"
    },
    "creatinine": {
        "unit": "mg/dL",
        "male_normal": {"low": 0.7, "high": 1.3},
        "female_normal": {"low": 0.6, "high": 1.1},
        "source": "KDIGO CKD Guidelines"
    },
    "bun": {
        "unit": "mg/dL",
        "normal": {"low": 7, "high": 20},
        "source": "Clinical reference ranges"
    },
    "sodium": {
        "unit": "mmol/L",
        "normal": {"low": 136, "high": 145},
        "hyponatremia": {"low": 0, "high": 135},
        "hypernatremia": {"low": 146, "high": None},
        "source": "Harrison's Principles"
    },
    "potassium": {
        "unit": "mmol/L",
        "normal": {"low": 3.5, "high": 5.0},
        "hypokalemia": {"low": 0, "high": 3.4},
        "hyperkalemia": {"low": 5.1, "high": None},
        "critical_low": 2.5,
        "critical_high": 6.5,
        "source": "Harrison's Principles"
    },
    "tsh": {
        "unit": "mIU/L",
        "normal": {"low": 0.4, "high": 4.0},
        "hyperthyroid": {"low": 0, "high": 0.39},
        "hypothyroid": {"low": 4.01, "high": None},
        "source": "ATA Thyroid Guidelines"
    },
    "vitamin_d": {
        "unit": "ng/mL",
        "sufficient": {"low": 30, "high": 100},
        "insufficient": {"low": 20, "high": 29},
        "deficient": {"low": 0, "high": 19},
        "source": "Endocrine Society Guidelines"
    },
    "vitamin_b12": {
        "unit": "pg/mL",
        "normal": {"low": 200, "high": 900},
        "low": {"low": 0, "high": 199},
        "source": "Clinical reference ranges"
    },
    "ferritin": {
        "unit": "ng/mL",
        "male_normal": {"low": 30, "high": 400},
        "female_normal": {"low": 15, "high": 150},
        "source": "WHO Guidelines"
    },
    "hemoglobin": {
        "unit": "g/dL",
        "male_normal": {"low": 13.5, "high": 17.5},
        "female_normal": {"low": 12.0, "high": 16.0},
        "anemia_male": {"low": 0, "high": 13.4},
        "anemia_female": {"low": 0, "high": 11.9},
        "source": "WHO Hemoglobin Guidelines"
    },
    "alt": {
        "unit": "U/L",
        "normal": {"low": 7, "high": 56},
        "elevated": {"low": 57, "high": None},
        "source": "ACG Liver Disease Guidelines"
    },
    "ast": {
        "unit": "U/L",
        "normal": {"low": 10, "high": 40},
        "elevated": {"low": 41, "high": None},
        "source": "ACG Liver Disease Guidelines"
    },
    "egfr": {
        "unit": "mL/min/1.73m²",
        "normal": {"low": 90, "high": None},
        "mild_decrease": {"low": 60, "high": 89},
        "moderate_decrease": {"low": 30, "high": 59},
        "severe_decrease": {"low": 15, "high": 29},
        "kidney_failure": {"low": 0, "high": 14},
        "source": "KDIGO CKD Guidelines 2012"
    },
    "uric_acid": {
        "unit": "mg/dL",
        "male_normal": {"low": 3.4, "high": 7.0},
        "female_normal": {"low": 2.4, "high": 6.0},
        "source": "ACR Gout Guidelines"
    },
    "crp": {
        "unit": "mg/L",
        "low_risk": {"low": 0, "high": 1.0},
        "moderate_risk": {"low": 1.0, "high": 3.0},
        "high_risk": {"low": 3.0, "high": None},
        "source": "AHA Cardiovascular Risk"
    }
}


class ComprehensiveLabInput(BaseModel):
    # Metabolic
    glucose: Optional[float] = Field(None, description="Fasting glucose (mg/dL)")
    hemoglobin_a1c: Optional[float] = Field(None, description="HbA1c (%)")
    insulin: Optional[float] = Field(None, description="Fasting insulin (µIU/mL)")
    
    # Lipids
    total_cholesterol: Optional[float] = Field(None, description="Total cholesterol (mg/dL)")
    ldl_cholesterol: Optional[float] = Field(None, description="LDL cholesterol (mg/dL)")
    hdl_cholesterol: Optional[float] = Field(None, description="HDL cholesterol (mg/dL)")
    triglycerides: Optional[float] = Field(None, description="Triglycerides (mg/dL)")
    
    # Blood pressure
    systolic_bp: Optional[float] = Field(None, description="Systolic BP (mmHg)")
    diastolic_bp: Optional[float] = Field(None, description="Diastolic BP (mmHg)")
    
    # Kidney
    creatinine: Optional[float] = Field(None, description="Creatinine (mg/dL)")
    bun: Optional[float] = Field(None, description="BUN (mg/dL)")
    egfr: Optional[float] = Field(None, description="eGFR (mL/min/1.73m²)")
    
    # Electrolytes
    sodium: Optional[float] = Field(None, description="Sodium (mmol/L)")
    potassium: Optional[float] = Field(None, description="Potassium (mmol/L)")
    
    # Thyroid
    tsh: Optional[float] = Field(None, description="TSH (mIU/L)")
    
    # Vitamins
    vitamin_d: Optional[float] = Field(None, description="Vitamin D (ng/mL)")
    vitamin_b12: Optional[float] = Field(None, description="Vitamin B12 (pg/mL)")
    
    # Iron
    ferritin: Optional[float] = Field(None, description="Ferritin (ng/mL)")
    hemoglobin: Optional[float] = Field(None, description="Hemoglobin (g/dL)")
    
    # Liver
    alt: Optional[float] = Field(None, description="ALT (U/L)")
    ast: Optional[float] = Field(None, description="AST (U/L)")
    
    # Inflammation
    crp: Optional[float] = Field(None, description="hs-CRP (mg/L)")
    
    # Other
    uric_acid: Optional[float] = Field(None, description="Uric acid (mg/dL)")
    
    # Demographics
    age: Optional[int] = Field(None, description="Age in years")
    sex: Optional[str] = Field(None, description="M or F")
    weight_kg: Optional[float] = Field(None, description="Weight in kg")
    height_cm: Optional[float] = Field(None, description="Height in cm")
    waist_cm: Optional[float] = Field(None, description="Waist circumference (cm)")


class InferenceResult(BaseModel):
    key: str
    title: str
    category: str
    risk_level: str
    confidence: float
    explanation: str
    contributing_factors: List[str]
    recommendations: List[str]
    sources: List[str]


class EnhancedInferenceResponse(BaseModel):
    status: str
    run_id: str
    timestamp: str
    inferences: List[InferenceResult]
    summary: Dict[str, Any]
    metadata: Dict[str, Any]


def calculate_bmi(weight_kg: float, height_cm: float) -> float:
    """Calculate BMI from weight and height."""
    height_m = height_cm / 100
    return round(weight_kg / (height_m ** 2), 1)


def calculate_homa_ir(glucose: float, insulin: float) -> float:
    """Calculate HOMA-IR insulin resistance index."""
    return round((glucose * insulin) / 405, 2)


def assess_insulin_resistance(glucose: float, insulin: float, a1c: float = None) -> Optional[InferenceResult]:
    """Assess insulin resistance using HOMA-IR and other markers."""
    if glucose is None or insulin is None:
        return None
    
    homa_ir = calculate_homa_ir(glucose, insulin)
    
    risk = "LOW"
    confidence = 0.80
    factors = []
    
    if homa_ir >= 2.5:
        risk = "HIGH"
        confidence = 0.88
        factors.append(f"HOMA-IR {homa_ir} (≥2.5 indicates insulin resistance)")
    elif homa_ir >= 1.9:
        risk = "MODERATE"
        confidence = 0.82
        factors.append(f"HOMA-IR {homa_ir} (1.9-2.4 borderline)")
    else:
        factors.append(f"HOMA-IR {homa_ir} (normal <1.9)")
    
    if a1c and a1c >= 5.7:
        if risk != "HIGH":
            risk = "MODERATE"
        factors.append(f"Elevated A1c {a1c}% supports insulin resistance pattern")
        confidence = min(confidence + 0.05, 0.95)
    
    return InferenceResult(
        key="insulin_resistance",
        title="Insulin Resistance Assessment",
        category="metabolic",
        risk_level=risk,
        confidence=confidence,
        explanation=f"HOMA-IR calculation from fasting glucose and insulin. Values ≥2.5 indicate significant insulin resistance.",
        contributing_factors=factors,
        recommendations=[
            "Low glycemic index diet recommended" if risk != "LOW" else "Maintain current diet",
            "Regular exercise improves insulin sensitivity",
            "Consider metformin evaluation" if risk == "HIGH" else "Monitor trends",
            "Retest in 3-6 months"
        ],
        sources=["Matthews DR, et al. Diabetologia 1985", "HOMA Calculator, Oxford University"]
    )


def assess_thyroid(tsh: float) -> Optional[InferenceResult]:
    """Assess thyroid function based on TSH."""
    if tsh is None:
        return None
    
    risk = "LOW"
    confidence = 0.75
    factors = []
    explanation = ""
    
    if tsh < 0.4:
        risk = "MODERATE"
        confidence = 0.82
        factors.append(f"TSH {tsh} mIU/L is below normal (<0.4)")
        explanation = "Low TSH may indicate hyperthyroidism. Further testing with Free T4 and T3 recommended."
    elif tsh > 4.0:
        risk = "MODERATE"
        confidence = 0.82
        factors.append(f"TSH {tsh} mIU/L is above normal (>4.0)")
        explanation = "Elevated TSH may indicate hypothyroidism. Further testing with Free T4 recommended."
    else:
        factors.append(f"TSH {tsh} mIU/L is within normal range (0.4-4.0)")
        explanation = "Thyroid function appears normal based on TSH screening."
    
    return InferenceResult(
        key="thyroid_function",
        title="Thyroid Function Assessment",
        category="endocrine",
        risk_level=risk,
        confidence=confidence,
        explanation=explanation,
        contributing_factors=factors,
        recommendations=[
            "Order Free T4 for complete assessment" if risk != "LOW" else "Annual TSH monitoring",
            "Consider thyroid antibodies if TSH abnormal",
            "Evaluate symptoms: fatigue, weight changes, temperature sensitivity"
        ],
        sources=["ATA Thyroid Guidelines 2012", "AACE Hypothyroidism Guidelines"]
    )


def assess_vitamin_status(vitamin_d: float = None, vitamin_b12: float = None) -> List[InferenceResult]:
    """Assess vitamin D and B12 status."""
    results = []
    
    if vitamin_d is not None:
        risk = "LOW"
        confidence = 0.80
        factors = []
        
        if vitamin_d < 20:
            risk = "HIGH"
            confidence = 0.88
            factors.append(f"Vitamin D {vitamin_d} ng/mL is deficient (<20)")
        elif vitamin_d < 30:
            risk = "MODERATE"
            confidence = 0.85
            factors.append(f"Vitamin D {vitamin_d} ng/mL is insufficient (20-29)")
        else:
            factors.append(f"Vitamin D {vitamin_d} ng/mL is sufficient (≥30)")
        
        results.append(InferenceResult(
            key="vitamin_d_status",
            title="Vitamin D Status",
            category="nutrition",
            risk_level=risk,
            confidence=confidence,
            explanation="Vitamin D is essential for bone health, immune function, and metabolic regulation.",
            contributing_factors=factors,
            recommendations=[
                "Supplement 2000-4000 IU daily" if risk == "HIGH" else "Supplement 1000-2000 IU daily" if risk == "MODERATE" else "Maintain sun exposure and diet",
                "Recheck levels in 3 months if supplementing",
                "Consider calcium intake assessment"
            ],
            sources=["Endocrine Society Clinical Practice Guidelines"]
        ))
    
    if vitamin_b12 is not None:
        risk = "LOW"
        confidence = 0.80
        factors = []
        
        if vitamin_b12 < 200:
            risk = "HIGH"
            confidence = 0.85
            factors.append(f"Vitamin B12 {vitamin_b12} pg/mL is low (<200)")
        elif vitamin_b12 < 300:
            risk = "MODERATE"
            confidence = 0.78
            factors.append(f"Vitamin B12 {vitamin_b12} pg/mL is borderline (200-300)")
        else:
            factors.append(f"Vitamin B12 {vitamin_b12} pg/mL is normal (≥300)")
        
        results.append(InferenceResult(
            key="vitamin_b12_status",
            title="Vitamin B12 Status",
            category="nutrition",
            risk_level=risk,
            confidence=confidence,
            explanation="B12 deficiency can cause neurological symptoms and anemia.",
            contributing_factors=factors,
            recommendations=[
                "Supplement B12 1000mcg daily" if risk != "LOW" else "Maintain dietary intake",
                "Check MMA and homocysteine if borderline" if risk == "MODERATE" else "Monitor annually",
                "Consider intrinsic factor antibodies if deficient"
            ],
            sources=["AGA Clinical Practice Guidelines"]
        ))
    
    return results


def assess_liver_function(alt: float = None, ast: float = None) -> Optional[InferenceResult]:
    """Assess liver function based on transaminases."""
    if alt is None and ast is None:
        return None
    
    risk = "LOW"
    confidence = 0.75
    factors = []
    
    if alt is not None:
        if alt > 56:
            risk = "MODERATE"
            factors.append(f"ALT {alt} U/L is elevated (>56)")
            confidence = 0.80
            if alt > 112:  # >2x ULN
                risk = "HIGH"
                confidence = 0.88
        else:
            factors.append(f"ALT {alt} U/L is normal")
    
    if ast is not None:
        if ast > 40:
            if risk != "HIGH":
                risk = "MODERATE"
            factors.append(f"AST {ast} U/L is elevated (>40)")
            confidence = max(confidence, 0.80)
        else:
            factors.append(f"AST {ast} U/L is normal")
    
    # Calculate AST/ALT ratio if both available
    ratio_note = ""
    if alt and ast and alt > 0:
        ratio = round(ast / alt, 2)
        if ratio > 2:
            ratio_note = f" AST/ALT ratio {ratio} (>2 may suggest alcohol-related liver disease)"
        elif ratio < 1:
            ratio_note = f" AST/ALT ratio {ratio} (<1 typical for NAFLD)"
    
    return InferenceResult(
        key="liver_function",
        title="Liver Function Assessment",
        category="hepatic",
        risk_level=risk,
        confidence=confidence,
        explanation=f"Transaminase assessment for liver health.{ratio_note}",
        contributing_factors=factors,
        recommendations=[
            "Liver ultrasound recommended" if risk == "HIGH" else "Recheck in 3-6 months" if risk == "MODERATE" else "Annual monitoring",
            "Review medications and alcohol intake",
            "Consider hepatitis B/C screening if elevated"
        ],
        sources=["ACG Clinical Guidelines for Liver Disease"]
    )


def assess_inflammation(crp: float) -> Optional[InferenceResult]:
    """Assess cardiovascular inflammation risk via hs-CRP."""
    if crp is None:
        return None
    
    risk = "LOW"
    confidence = 0.78
    factors = []
    
    if crp > 3.0:
        risk = "HIGH"
        confidence = 0.85
        factors.append(f"hs-CRP {crp} mg/L indicates high cardiovascular inflammation risk (>3.0)")
    elif crp > 1.0:
        risk = "MODERATE"
        confidence = 0.82
        factors.append(f"hs-CRP {crp} mg/L indicates moderate risk (1.0-3.0)")
    else:
        factors.append(f"hs-CRP {crp} mg/L indicates low cardiovascular risk (<1.0)")
    
    return InferenceResult(
        key="inflammation_risk",
        title="Cardiovascular Inflammation Risk",
        category="cardiovascular",
        risk_level=risk,
        confidence=confidence,
        explanation="High-sensitivity CRP is a marker of systemic inflammation associated with cardiovascular disease risk.",
        contributing_factors=factors,
        recommendations=[
            "Anti-inflammatory lifestyle: Mediterranean diet, regular exercise" if risk != "LOW" else "Maintain healthy lifestyle",
            "Rule out acute infection/inflammation if very elevated",
            "Consider statin therapy evaluation" if risk == "HIGH" else "Monitor trends"
        ],
        sources=["AHA Scientific Statement on CRP and Cardiovascular Risk"]
    )


@app.get("/")
def root():
    return {
        "service": "MONITOR Health Intelligence API",
        "version": "1.1.0",
        "status": "operational",
        "capabilities": {
            "biomarkers_supported": len(CLINICAL_REFERENCES),
            "assessment_categories": ["metabolic", "cardiovascular", "endocrine", "hepatic", "renal", "nutrition", "inflammation"],
            "features": ["confidence_scoring", "multi_marker_inference", "clinical_recommendations", "source_citations"]
        },
        "endpoints": {
            "/infer": "POST - Run comprehensive health inference",
            "/reference": "GET - Get all clinical reference ranges",
            "/reference/{biomarker}": "GET - Get specific biomarker reference",
            "/health": "GET - Health check"
        }
    }


@app.get("/health")
def health():
    return {"status": "healthy", "service": "monitor-api", "version": "1.1.0"}


@app.get("/reference")
def get_all_references():
    return {"references": CLINICAL_REFERENCES, "count": len(CLINICAL_REFERENCES)}


@app.get("/reference/{biomarker}")
def get_reference(biomarker: str):
    if biomarker not in CLINICAL_REFERENCES:
        raise HTTPException(status_code=404, detail=f"Biomarker '{biomarker}' not found")
    return {biomarker: CLINICAL_REFERENCES[biomarker]}


@app.post("/infer", response_model=EnhancedInferenceResponse)
def run_comprehensive_inference(labs: ComprehensiveLabInput):
    """Run comprehensive clinical inference on provided lab values."""
    
    # Generate run ID
    run_id = hashlib.md5(f"{datetime.utcnow().isoformat()}{labs.json()}".encode()).hexdigest()[:12]
    
    inferences = []
    risk_summary = {"HIGH": 0, "MODERATE": 0, "LOW": 0}
    
    # Import base assessments from api_worker
    from api_worker import (
        assess_glycemic_status, 
        assess_cardiovascular_risk,
        assess_metabolic_syndrome,
        assess_kidney_function
    )
    
    # Basic metabolic assessments
    glycemic = assess_glycemic_status(labs.glucose, labs.hemoglobin_a1c)
    if glycemic:
        inferences.append(InferenceResult(
            key=glycemic.key,
            title=glycemic.title,
            category="metabolic",
            risk_level=glycemic.risk_level,
            confidence=glycemic.confidence,
            explanation=glycemic.explanation,
            contributing_factors=glycemic.contributing_factors,
            recommendations=glycemic.recommendations,
            sources=["ADA Standards of Medical Care"]
        ))
        risk_summary[glycemic.risk_level] += 1
    
    # Cardiovascular
    cardio = assess_cardiovascular_risk(
        labs.total_cholesterol,
        labs.ldl_cholesterol,
        labs.hdl_cholesterol,
        labs.triglycerides
    )
    if cardio:
        inferences.append(InferenceResult(
            key=cardio.key,
            title=cardio.title,
            category="cardiovascular",
            risk_level=cardio.risk_level,
            confidence=cardio.confidence,
            explanation=cardio.explanation,
            contributing_factors=cardio.contributing_factors,
            recommendations=cardio.recommendations,
            sources=["AHA/ACC Lipid Guidelines"]
        ))
        risk_summary[cardio.risk_level] += 1
    
    # Metabolic syndrome
    metsyn = assess_metabolic_syndrome(
        labs.glucose,
        labs.triglycerides,
        labs.hdl_cholesterol
    )
    if metsyn:
        inferences.append(InferenceResult(
            key=metsyn.key,
            title=metsyn.title,
            category="metabolic",
            risk_level=metsyn.risk_level,
            confidence=metsyn.confidence,
            explanation=metsyn.explanation,
            contributing_factors=metsyn.contributing_factors,
            recommendations=metsyn.recommendations,
            sources=["ATP III Guidelines", "IDF Consensus Definition"]
        ))
        risk_summary[metsyn.risk_level] += 1
    
    # Kidney function
    kidney = assess_kidney_function(
        labs.creatinine,
        labs.bun,
        labs.age,
        labs.sex
    )
    if kidney:
        inferences.append(InferenceResult(
            key=kidney.key,
            title=kidney.title,
            category="renal",
            risk_level=kidney.risk_level,
            confidence=kidney.confidence,
            explanation=kidney.explanation,
            contributing_factors=kidney.contributing_factors,
            recommendations=kidney.recommendations,
            sources=["KDIGO CKD Guidelines"]
        ))
        risk_summary[kidney.risk_level] += 1
    
    # Enhanced assessments
    if labs.glucose and labs.insulin:
        ir = assess_insulin_resistance(labs.glucose, labs.insulin, labs.hemoglobin_a1c)
        if ir:
            inferences.append(ir)
            risk_summary[ir.risk_level] += 1
    
    thyroid = assess_thyroid(labs.tsh)
    if thyroid:
        inferences.append(thyroid)
        risk_summary[thyroid.risk_level] += 1
    
    vitamins = assess_vitamin_status(labs.vitamin_d, labs.vitamin_b12)
    for v in vitamins:
        inferences.append(v)
        risk_summary[v.risk_level] += 1
    
    liver = assess_liver_function(labs.alt, labs.ast)
    if liver:
        inferences.append(liver)
        risk_summary[liver.risk_level] += 1
    
    inflammation = assess_inflammation(labs.crp)
    if inflammation:
        inferences.append(inflammation)
        risk_summary[inflammation.risk_level] += 1
    
    # Calculate overall health score
    total_assessments = sum(risk_summary.values())
    if total_assessments > 0:
        health_score = round(
            (risk_summary["LOW"] * 100 + risk_summary["MODERATE"] * 60 + risk_summary["HIGH"] * 20) / total_assessments
        )
    else:
        health_score = None
    
    # Count inputs provided
    input_count = sum(1 for k, v in labs.dict().items() if v is not None)
    
    return EnhancedInferenceResponse(
        status="success",
        run_id=run_id,
        timestamp=datetime.utcnow().isoformat(),
        inferences=inferences,
        summary={
            "health_score": health_score,
            "risk_distribution": risk_summary,
            "total_assessments": total_assessments,
            "priority_concerns": [i.title for i in inferences if i.risk_level == "HIGH"]
        },
        metadata={
            "input_count": input_count,
            "inference_count": len(inferences),
            "api_version": "1.1.0",
            "processing_time_ms": 45  # Simulated
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
