# MONITOR Inference Pipeline

## Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           MONITOR INFERENCE PIPELINE                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────┐  │
│  │   INPUTS     │ →  │  PROCESSING  │ →  │  INFERENCE   │ →  │ OUTPUTS  │  │
│  │              │    │              │    │              │    │          │  │
│  │ • CGM data   │    │ • Normalize  │    │ • Rules      │    │ • Risks  │  │
│  │ • Lab values │    │ • Aggregate  │    │ • ML models  │    │ • Scores │  │
│  │ • Vitals     │    │ • Correlate  │    │ • Bayesian   │    │ • Trends │  │
│  │ • User ctx   │    │ • Transform  │    │ • Ensemble   │    │ • Advice │  │
│  └──────────────┘    └──────────────┘    └──────────────┘    └──────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Stage 1: INPUT COLLECTION

### 1.1 Raw Data Sources
```python
INPUT_SOURCES = {
    "continuous": ["cgm", "wearable_hr", "activity"],
    "discrete": ["lab_values", "vitals", "test_strips"],
    "contextual": ["demographics", "pmh", "medications", "lifestyle"]
}
```

### 1.2 User Context Model
```python
UserContext = {
    # Demographics
    "age": int,
    "sex": "M" | "F",
    "ethnicity": str,
    "height_cm": float,
    "weight_kg": float,
    
    # Medical History
    "conditions": ["diabetes", "hypertension", ...],
    "family_history": {"diabetes": bool, "heart_disease": bool, ...},
    
    # Medications
    "current_meds": [{"name": str, "dose": str, "frequency": str}],
    "allergies": [str],
    
    # Lifestyle
    "smoking_status": "never" | "former" | "current",
    "alcohol_weekly_drinks": int,
    "exercise_minutes_weekly": int,
    "diet_type": "standard" | "low_carb" | "vegetarian" | ...,
    
    # Geographic/Environmental
    "location": {"lat": float, "lon": float},
    "altitude_m": float,
    "recent_travel": [{"destination": str, "dates": str}]
}
```

---

## Stage 2: DATA PROCESSING

### 2.1 Normalization
```python
def normalize_units(value, source_unit, target_unit):
    """Convert all values to standard units."""
    CONVERSIONS = {
        ("mmol/L", "mg/dL"): lambda x: x * 18.0182,  # glucose
        ("mg/dL", "mmol/L"): lambda x: x / 18.0182,
        ("lb", "kg"): lambda x: x * 0.453592,
        ("in", "cm"): lambda x: x * 2.54,
        # ... more conversions
    }
    return CONVERSIONS[(source_unit, target_unit)](value)
```

### 2.2 Quality Filtering
```python
def filter_quality(readings, device_type):
    """Remove artifacts and invalid readings."""
    QUALITY_RULES = {
        "cgm": {
            "min": 40, "max": 400,  # mg/dL
            "max_rate_of_change": 4,  # mg/dL/min
            "min_valid_interval": 300  # seconds
        },
        "bp": {
            "systolic": {"min": 70, "max": 250},
            "diastolic": {"min": 40, "max": 150}
        }
    }
    # Filter based on rules
```

### 2.3 Temporal Aggregation
```python
def aggregate_cgm(readings, window="24h"):
    """Calculate summary statistics from CGM data."""
    return {
        "mean_glucose": np.mean(readings),
        "std_glucose": np.std(readings),
        "cv_percent": np.std(readings) / np.mean(readings) * 100,
        "time_in_range_70_180": calculate_tir(readings, 70, 180),
        "time_below_70": calculate_tir(readings, 0, 70),
        "time_above_180": calculate_tir(readings, 180, 400),
        "gmi": 3.31 + (0.02392 * np.mean(readings)),  # Bergenstal formula
        "auc_above_140": calculate_auc(readings, threshold=140)
    }
```

### 2.4 Feature Extraction
```python
def extract_features(data):
    """Generate derived features for ML models."""
    features = {}
    
    # Metabolic features
    if "glucose" in data and "a1c" in data:
        features["glucose_a1c_discordance"] = calculate_discordance(
            data["glucose"], data["a1c"]
        )
    
    # Lipid ratios
    if all(k in data for k in ["total_chol", "hdl", "ldl", "trig"]):
        features["tc_hdl_ratio"] = data["total_chol"] / data["hdl"]
        features["ldl_hdl_ratio"] = data["ldl"] / data["hdl"]
        features["trig_hdl_ratio"] = data["trig"] / data["hdl"]
        features["non_hdl_chol"] = data["total_chol"] - data["hdl"]
    
    # Kidney function
    if "creatinine" in data and "age" in data and "sex" in data:
        features["egfr"] = calculate_egfr_ckdepi(
            data["creatinine"], data["age"], data["sex"]
        )
    
    # Body composition
    if "weight_kg" in data and "height_cm" in data:
        features["bmi"] = data["weight_kg"] / (data["height_cm"]/100)**2
    
    # Cardiovascular
    if "systolic" in data and "diastolic" in data:
        features["map"] = (data["systolic"] + 2*data["diastolic"]) / 3
        features["pulse_pressure"] = data["systolic"] - data["diastolic"]
    
    return features
```

---

## Stage 3: INFERENCE ENGINE

### 3.1 Rule-Based Inference
```python
CLINICAL_RULES = {
    "prediabetes_risk": {
        "conditions": [
            ("glucose >= 100 AND glucose < 126", 0.3),
            ("a1c >= 5.7 AND a1c < 6.5", 0.3),
            ("bmi >= 25", 0.15),
            ("family_history.diabetes == True", 0.15),
            ("age >= 45", 0.1)
        ],
        "threshold": 0.5,
        "sources": ["ADA Standards 2024", "PMID:34593612"]
    },
    
    "metabolic_syndrome": {
        "criteria": [
            "waist_cm > 102 (M) or > 88 (F)",
            "triglycerides >= 150",
            "hdl < 40 (M) or < 50 (F)",
            "bp >= 130/85",
            "fasting_glucose >= 100"
        ],
        "required": 3,  # Need 3 of 5
        "sources": ["NCEP ATP III", "IDF Consensus"]
    }
}
```

### 3.2 ML Model Inference
```python
class EnsembleInference:
    """Combine multiple models for robust predictions."""
    
    def __init__(self):
        self.models = {
            "random_forest": load_model("rf_metabolic_v1"),
            "gradient_boost": load_model("xgb_metabolic_v1"),
            "neural_net": load_model("nn_metabolic_v1")
        }
        self.weights = {"random_forest": 0.35, "gradient_boost": 0.4, "neural_net": 0.25}
    
    def predict(self, features):
        predictions = {}
        for name, model in self.models.items():
            pred = model.predict_proba(features)
            predictions[name] = pred
        
        # Weighted ensemble
        ensemble_pred = sum(
            self.weights[name] * pred 
            for name, pred in predictions.items()
        )
        
        return {
            "prediction": ensemble_pred,
            "model_agreement": self.calculate_agreement(predictions),
            "confidence": self.calculate_confidence(predictions, ensemble_pred)
        }
```

### 3.3 Bayesian Updating
```python
def bayesian_update(prior, likelihood, evidence):
    """Update probability with new evidence."""
    # P(A|B) = P(B|A) * P(A) / P(B)
    posterior = (likelihood * prior) / evidence
    return posterior

def update_risk_with_cgm(base_risk, cgm_features):
    """Incorporate CGM data into diabetes risk."""
    # Prior: risk from fasting glucose + A1c
    prior = base_risk
    
    # Likelihood based on CGM patterns
    if cgm_features["time_above_140"] > 0.3:  # >30% time elevated
        likelihood = 1.5  # Increases risk
    elif cgm_features["cv_percent"] > 36:  # High variability
        likelihood = 1.3
    else:
        likelihood = 0.8  # Good control reduces risk
    
    # Evidence normalization
    evidence = 1.0  # Simplified
    
    return bayesian_update(prior, likelihood, evidence)
```

### 3.4 Temporal Trend Analysis
```python
def analyze_trends(historical_data, metric, window_days=90):
    """Detect trends and predict trajectory."""
    values = [d[metric] for d in historical_data]
    timestamps = [d["timestamp"] for d in historical_data]
    
    # Linear regression for trend
    slope, intercept = np.polyfit(range(len(values)), values, 1)
    
    # Classify trend
    if slope > 0.01:
        trend = "increasing"
        rate = f"+{slope:.2f}/day"
    elif slope < -0.01:
        trend = "decreasing"
        rate = f"{slope:.2f}/day"
    else:
        trend = "stable"
        rate = "no significant change"
    
    # Project future value
    days_to_project = 30
    projected_value = values[-1] + (slope * days_to_project)
    
    return {
        "trend": trend,
        "rate": rate,
        "current": values[-1],
        "projected_30d": projected_value,
        "confidence_interval": calculate_ci(values, 0.95)
    }
```

---

## Stage 4: CONFIDENCE CALCULATION

### 4.1 Confidence Components
```python
def calculate_confidence(inference_result):
    """Multi-factor confidence scoring."""
    
    # Data completeness (0-0.3)
    completeness = len(available_inputs) / len(required_inputs) * 0.3
    
    # Data recency (0-0.2)
    hours_since_latest = (now - latest_timestamp).hours
    recency = max(0, 0.2 - (hours_since_latest / 168) * 0.2)  # Decay over 1 week
    
    # Model agreement (0-0.25)
    agreement = model_agreement_score * 0.25
    
    # Evidence strength (0-0.25)
    evidence_levels = {"RCT": 1.0, "cohort": 0.8, "expert": 0.6}
    evidence = np.mean([evidence_levels.get(s, 0.5) for s in sources]) * 0.25
    
    total_confidence = completeness + recency + agreement + evidence
    
    return {
        "overall": total_confidence,
        "components": {
            "data_completeness": completeness,
            "data_recency": recency,
            "model_agreement": agreement,
            "evidence_strength": evidence
        }
    }
```

---

## Stage 5: OUTPUT GENERATION

### 5.1 Output Schema
```python
InferenceOutput = {
    "assessment": {
        "key": "glycemic_status",
        "title": "Glycemic Status Assessment",
        "category": "metabolic",
        "risk_level": "LOW" | "MODERATE" | "HIGH" | "CRITICAL",
        "risk_score": float,  # 0-100
        "confidence": float,  # 0-1
        "trend": "improving" | "stable" | "worsening"
    },
    
    "explanation": {
        "summary": str,
        "contributing_factors": [
            {"factor": str, "impact": float, "direction": "+"|"-"}
        ],
        "evidence_base": [
            {"source": str, "pmid": str, "relevance": str}
        ]
    },
    
    "recommendations": {
        "immediate": [str],  # Do now
        "short_term": [str], # This week
        "long_term": [str],  # Ongoing
        "follow_up": {"test": str, "timeframe": str}
    },
    
    "metadata": {
        "inference_version": str,
        "models_used": [str],
        "data_sources": [str],
        "timestamp": str
    }
}
```

### 5.2 Human-Readable Explanation Generation
```python
def generate_explanation(inference_result, user_context):
    """Generate personalized, understandable explanation."""
    
    templates = {
        "prediabetes_moderate": """
        Your blood sugar markers suggest pre-diabetes risk. 
        
        Key findings:
        - Fasting glucose: {glucose} mg/dL (normal < 100)
        - HbA1c: {a1c}% (normal < 5.7%)
        
        This means your body is starting to have difficulty processing sugar efficiently.
        The good news: pre-diabetes can often be reversed with lifestyle changes.
        
        Based on your profile ({age} year old {sex}, BMI {bmi}), 
        we recommend:
        - 150 minutes/week of moderate exercise
        - Reducing refined carbohydrate intake
        - Monitoring with a CGM for personalized insights
        
        Follow up: Retest A1c in 3 months.
        """
    }
    
    return templates[inference_key].format(**user_context)
```

---

## Calculation Examples

### eGFR (CKD-EPI 2021)
```python
def calculate_egfr_ckdepi(creatinine, age, sex):
    """CKD-EPI 2021 equation (race-free)."""
    if sex == "F":
        if creatinine <= 0.7:
            egfr = 142 * (creatinine/0.7)**(-0.241) * (0.9938)**age
        else:
            egfr = 142 * (creatinine/0.7)**(-1.2) * (0.9938)**age
    else:  # Male
        if creatinine <= 0.9:
            egfr = 142 * (creatinine/0.9)**(-0.302) * (0.9938)**age
        else:
            egfr = 142 * (creatinine/0.9)**(-1.2) * (0.9938)**age
    return round(egfr, 1)
```

### GMI (Glucose Management Indicator)
```python
def calculate_gmi(mean_glucose_mg_dl):
    """Bergenstal et al. 2018 formula."""
    # GMI (%) = 3.31 + (0.02392 × mean glucose in mg/dL)
    return round(3.31 + (0.02392 * mean_glucose_mg_dl), 1)
```

### HOMA-IR
```python
def calculate_homa_ir(fasting_glucose_mg_dl, fasting_insulin_uIU_ml):
    """Homeostatic Model Assessment of Insulin Resistance."""
    # HOMA-IR = (glucose × insulin) / 405
    return round((fasting_glucose_mg_dl * fasting_insulin_uIU_ml) / 405, 2)
```

### Framingham Risk Score (Simplified)
```python
def calculate_framingham_10yr(age, total_chol, hdl, systolic, treated_bp, smoker, diabetic):
    """10-year cardiovascular risk (simplified)."""
    # This is a simplified version - full implementation uses lookup tables
    points = 0
    
    # Age points
    if age >= 70: points += 13
    elif age >= 65: points += 11
    elif age >= 60: points += 9
    # ... etc
    
    # Total cholesterol points
    if total_chol >= 280: points += 3
    elif total_chol >= 240: points += 2
    # ... etc
    
    # Convert points to probability
    risk_table = {0: 1, 5: 2, 10: 6, 15: 12, 20: 25}  # Simplified
    
    return interpolate_risk(points, risk_table)
```
