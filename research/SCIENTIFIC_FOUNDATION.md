# MONITOR Scientific Foundation

## Critical Gap Analysis

### What We Have (Scaffolding)
- Reference ranges from clinical guidelines
- Basic rule-based logic
- Placeholder code for ML models
- 184 tests (but testing placeholder logic)

### What We NEED (Real Product)

---

## SECTION 1: INPUTS

### 1.1 Biomarker Inputs - Scientific Validation Required

| Biomarker | Unit | Normal Range | Source | Physiological Basis | Proxy Potential |
|-----------|------|--------------|--------|---------------------|-----------------|
| Fasting Glucose | mg/dL | 70-99 | ADA 2024 | Direct measurement of blood sugar | CGM avg, PPG |
| HbA1c | % | 4.0-5.6 | ADA 2024 | 3-month glycemic average | GMI from CGM |
| Total Cholesterol | mg/dL | <200 | AHA/ACC | Lipid transport | Calculated panels |
| LDL-C | mg/dL | <100 | AHA/ACC | Atherogenic particles | Friedewald calc |
| HDL-C | mg/dL | >40M/>50F | AHA/ACC | Reverse cholesterol transport | Direct measure |
| Triglycerides | mg/dL | <150 | AHA/ACC | Fat transport | Fasting required |
| Creatinine | mg/dL | 0.7-1.3M/0.6-1.1F | KDIGO | Muscle metabolism/kidney | Cystatin-C |
| eGFR | mL/min/1.73m² | >90 | CKD-EPI 2021 | Kidney filtration rate | DERIVED |
| TSH | mIU/L | 0.4-4.0 | ATA | Thyroid function | T3/T4 correlation |
| Vitamin D | ng/mL | 30-100 | Endocrine Soc | Bone/immune health | UV exposure proxy |
| Vitamin B12 | pg/mL | 200-900 | Clinical | Nerve/blood health | MMA, homocysteine |
| hs-CRP | mg/L | <1.0 | AHA | Systemic inflammation | - |
| Fasting Insulin | μIU/mL | 2-25 | Clinical | Metabolic status | HOMA-IR |
| ALT | U/L | 7-56 | Clinical | Liver function | AST ratio |
| AST | U/L | 10-40 | Clinical | Liver/muscle | ALT ratio |

### 1.2 Derived/Calculated Inputs

| Metric | Formula | Clinical Significance |
|--------|---------|----------------------|
| BMI | weight(kg) / height(m)² | Adiposity proxy |
| HOMA-IR | (glucose × insulin) / 405 | Insulin resistance |
| eGFR | CKD-EPI 2021 equation | Kidney function |
| Non-HDL-C | TC - HDL | Atherogenic lipids |
| TC/HDL Ratio | TC / HDL | CV risk ratio |
| TG/HDL Ratio | TG / HDL | Insulin resistance proxy |
| LDL/HDL Ratio | LDL / HDL | Atherogenic ratio |
| MAP | (SBP + 2×DBP) / 3 | Mean arterial pressure |
| Pulse Pressure | SBP - DBP | Arterial stiffness |
| GMI | 3.31 + (0.02392 × mean_glucose) | A1c estimate from CGM |
| TIR | % time 70-180 mg/dL | Glycemic control |
| CV% | (SD/mean) × 100 | Glycemic variability |

### 1.3 Input Validation Rules

```python
VALIDATION_RULES = {
    "glucose": {
        "physiologic_min": 20,  # Below = death
        "physiologic_max": 600,  # Above = severe crisis
        "plausible_min": 40,
        "plausible_max": 400,
        "normal_min": 70,
        "normal_max": 99,
        "fasting_required": True,
        "unit_conversions": {"mmol/L": 18.0182}
    },
    # ... for each biomarker
}
```

---

## SECTION 2: PROCESSING (The "Juicy Middle")

### 2.1 Statistical Methods Required

| Method | Purpose | Implementation |
|--------|---------|----------------|
| **Percentile Ranking** | Population context | NHANES percentiles |
| **Z-Score** | Standard deviation from mean | (value - mean) / SD |
| **Bayesian Updating** | Incorporate new evidence | Prior × Likelihood / Evidence |
| **Time Series Analysis** | Trend detection | Linear regression, ARIMA |
| **Change Point Detection** | Identify shifts | CUSUM, PELT algorithm |
| **Correlation Analysis** | Multi-biomarker relationships | Pearson, Spearman |

### 2.2 ML Models to Train

| Model | Target | Features | Training Data |
|-------|--------|----------|---------------|
| **Prediabetes Risk** | Binary | Glucose, A1c, BMI, age, family hx | NHANES + literature |
| **CVD Risk** | 10-year % | Lipids, BP, age, smoking, diabetes | Framingham validated |
| **Metabolic Syndrome** | Binary | ATP-III criteria | NHANES |
| **CKD Progression** | Stage change | eGFR, proteinuria, BP | KDIGO data |
| **Glycemic Control** | A1c category | CGM features, meds, diet | Published CGM studies |

### 2.3 Ensemble Architecture

```python
class MonitorEnsemble:
    """Production ensemble for health inference."""
    
    def __init__(self):
        self.models = {
            "rule_based": ClinicalRulesEngine(),
            "random_forest": RandomForestClassifier(),
            "gradient_boost": XGBClassifier(),
            "bayesian": BayesianInference()
        }
        
        # Weights determined by validation accuracy
        self.weights = {
            "rule_based": 0.30,  # Clinically grounded
            "random_forest": 0.25,
            "gradient_boost": 0.30,
            "bayesian": 0.15
        }
    
    def predict(self, features):
        predictions = {}
        for name, model in self.models.items():
            predictions[name] = model.predict_proba(features)
        
        # Weighted ensemble
        ensemble = sum(
            self.weights[name] * pred 
            for name, pred in predictions.items()
        )
        
        # Disagreement = lower confidence
        disagreement = np.std([p for p in predictions.values()])
        confidence_penalty = disagreement * 0.5
        
        return {
            "prediction": ensemble,
            "confidence": min(0.95, max(0.50, ensemble - confidence_penalty)),
            "model_agreement": 1 - disagreement
        }
```

### 2.4 LLM Integration for Explanations

```python
class ExplanationGenerator:
    """Use LLM to generate human-readable explanations."""
    
    def __init__(self, model="gpt-4"):
        self.client = OpenAI()
    
    def generate(self, inference_result, user_context):
        prompt = f"""
        Generate a clear, empathetic health explanation for a patient.
        
        Clinical findings:
        {json.dumps(inference_result, indent=2)}
        
        Patient context:
        - Age: {user_context['age']}
        - Sex: {user_context['sex']}
        - Known conditions: {user_context.get('conditions', 'None')}
        
        Requirements:
        1. Use plain language (8th grade reading level)
        2. Explain what the numbers mean
        3. Provide actionable recommendations
        4. Be encouraging but honest
        5. Mention when to see a doctor
        
        Do NOT provide medical diagnosis. Frame as health insights.
        """
        
        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )
        
        return response.choices[0].message.content
```

---

## SECTION 3: OUTPUTS

### 3.1 Output Categories

| Category | Assessments | Confidence Required |
|----------|-------------|---------------------|
| **Metabolic** | Glycemic status, Insulin resistance, Metabolic syndrome | >0.70 |
| **Cardiovascular** | Lipid status, BP status, CVD risk | >0.75 |
| **Renal** | Kidney function, Electrolyte balance | >0.80 |
| **Endocrine** | Thyroid function, Hormone balance | >0.75 |
| **Nutritional** | Vitamin status, Mineral status | >0.65 |
| **Inflammatory** | Systemic inflammation, Immune markers | >0.70 |

### 3.2 Risk Level Definitions

| Level | Numerical | Clinical Meaning | Action Required |
|-------|-----------|------------------|-----------------|
| **LOW** | 0-30% | Within normal limits | Routine monitoring |
| **MODERATE** | 31-60% | Borderline/early changes | Lifestyle modification |
| **HIGH** | 61-85% | Significant abnormality | Medical consultation |
| **CRITICAL** | 86-100% | Urgent/dangerous | Immediate medical care |

### 3.3 Confidence Score Components

```python
def calculate_confidence(result):
    components = {
        "data_completeness": len(inputs) / len(required) * 0.25,
        "data_quality": quality_score * 0.20,
        "data_recency": recency_decay(hours_old) * 0.15,
        "model_agreement": agreement_score * 0.20,
        "evidence_strength": evidence_level * 0.20
    }
    
    return sum(components.values())
```

---

## SECTION 4: VALIDATION FRAMEWORK (SANDBOX)

### 4.1 Test Cases Required

| Test Type | Purpose | Pass Criteria |
|-----------|---------|---------------|
| **Unit Tests** | Individual function correctness | 100% pass |
| **Integration Tests** | Pipeline end-to-end | 100% pass |
| **Clinical Validation** | Match published studies | >90% concordance |
| **Edge Cases** | Boundary conditions | Handle gracefully |
| **Stress Tests** | High volume, missing data | Maintain accuracy |

### 4.2 Clinical Concordance Testing

```python
VALIDATION_CASES = [
    {
        "name": "Classic Prediabetes",
        "inputs": {"glucose": 110, "a1c": 5.9, "bmi": 28},
        "expected": {"glycemic_status": "MODERATE", "confidence": ">0.80"}
    },
    {
        "name": "Well-Controlled Diabetes",
        "inputs": {"glucose": 95, "a1c": 6.8},
        "expected": {"glycemic_status": "MODERATE", "note": "On treatment"}
    },
    # ... 50+ validation cases
]
```

### 4.3 Proxy Validation

For each proxy relationship, validate against gold standard:

| Proxy | Gold Standard | Correlation Required | Citation |
|-------|---------------|---------------------|----------|
| GMI → A1c | Lab A1c | r > 0.90 | Bergenstal 2018 |
| CGM TIR → A1c | Lab A1c | r > 0.85 | Beck 2019 |
| TG/HDL → HOMA-IR | Clamp study | r > 0.70 | McLaughlin 2003 |
| Friedewald LDL → Direct LDL | Direct measurement | r > 0.95 | Friedewald 1972 |

---

## SECTION 5: CITATIONS & EVIDENCE BASE

### Primary Sources
1. ADA Standards of Medical Care in Diabetes—2024
2. AHA/ACC Guideline on Blood Cholesterol Management—2018
3. AHA/ACC Guideline for High Blood Pressure—2017
4. KDIGO Clinical Practice Guideline for CKD—2012
5. ATP III Guidelines on Metabolic Syndrome—2001
6. Endocrine Society Vitamin D Guidelines—2011

### Key Validation Studies
1. Bergenstal RM et al. Glucose Management Indicator (GMI). Diabetes Care 2018
2. Beck RW et al. CGM Time in Range. Diabetes Care 2019
3. Framingham Heart Study Risk Calculator Validation
4. CKD-EPI 2021 Creatinine Equation Validation

---

## IMPLEMENTATION PRIORITY

### EOW MUST-HAVE
1. ✅ Validated input ranges with citations
2. ✅ Working rule-based inference with proper thresholds
3. ✅ Real ML model (at least Random Forest) trained on NHANES
4. ✅ Confidence scoring that makes sense
5. ✅ Demo that actually computes real results
6. ✅ 50+ validated test cases passing

### NEXT WEEK
- LLM explanation generation
- Full ensemble with XGBoost
- Trend analysis
- More biomarkers

---

*This document is the scientific foundation for MONITOR. All claims must be traceable to citations.*
