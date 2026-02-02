# MONITOR API Documentation

**Version:** 1.1.0  
**Base URL:** `https://api.monitor.health` (production - coming soon)  
**Status:** Beta

---

## Overview

MONITOR provides clinical-grade health inference from biomarker data. Our API analyzes lab values and returns confidence-scored health insights based on established clinical guidelines.

## Authentication

Currently in beta - no authentication required for demo endpoints.

Production will use API keys:
```
Authorization: Bearer your_api_key
```

---

## Endpoints

### Health Check

```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "monitor-api",
  "version": "1.1.0"
}
```

### Get Reference Ranges

```http
GET /reference
```

Returns all clinical reference ranges with sources.

**Response:**
```json
{
  "references": {
    "glucose": {
      "unit": "mg/dL",
      "normal": {"low": 70, "high": 99},
      "prediabetes": {"low": 100, "high": 125},
      "diabetes": {"low": 126, "high": null},
      "source": "ADA Standards of Medical Care 2024"
    }
    // ... more biomarkers
  }
}
```

### Run Health Inference

```http
POST /infer
Content-Type: application/json
```

**Request Body:**
```json
{
  "glucose": 108,
  "hemoglobin_a1c": 5.9,
  "total_cholesterol": 215,
  "ldl_cholesterol": 135,
  "hdl_cholesterol": 42,
  "triglycerides": 178,
  "age": 45,
  "sex": "M"
}
```

**All fields are optional.** Include only the biomarkers you have.

**Response:**
```json
{
  "status": "success",
  "inferences": [
    {
      "key": "glycemic_status",
      "title": "Glycemic Status Assessment",
      "risk_level": "MODERATE",
      "confidence": 0.87,
      "explanation": "Based on ADA diagnostic criteria. Fasting glucose 108 mg/dL (100-125 = prediabetes); HbA1c 5.9% (5.7-6.4 = prediabetes)",
      "contributing_factors": [
        "Fasting glucose 108 mg/dL (100-125 = prediabetes)",
        "HbA1c 5.9% (5.7-6.4 = prediabetes)"
      ],
      "recommendations": [
        "Lifestyle modifications recommended",
        "Increase physical activity",
        "Reduce refined carbohydrate intake",
        "Retest in 3-6 months"
      ]
    },
    {
      "key": "cardiovascular_risk",
      "title": "Cardiovascular Risk Assessment",
      "risk_level": "MODERATE",
      "confidence": 0.82,
      "explanation": "Based on AHA lipid guidelines...",
      "contributing_factors": [...],
      "recommendations": [...]
    }
  ],
  "metadata": {
    "input_count": 6,
    "inference_count": 3,
    "api_version": "1.1.0"
  }
}
```

---

## Supported Biomarkers

### Metabolic
| Biomarker | Field Name | Unit | Normal Range |
|-----------|------------|------|--------------|
| Fasting Glucose | `glucose` | mg/dL | 70-99 |
| HbA1c | `hemoglobin_a1c` | % | 4.0-5.6 |
| Fasting Insulin | `insulin` | µIU/mL | 2.6-24.9 |

### Lipids
| Biomarker | Field Name | Unit | Optimal |
|-----------|------------|------|---------|
| Total Cholesterol | `total_cholesterol` | mg/dL | <200 |
| LDL Cholesterol | `ldl_cholesterol` | mg/dL | <100 |
| HDL Cholesterol | `hdl_cholesterol` | mg/dL | >60 |
| Triglycerides | `triglycerides` | mg/dL | <150 |

### Kidney Function
| Biomarker | Field Name | Unit | Normal Range |
|-----------|------------|------|--------------|
| Creatinine | `creatinine` | mg/dL | 0.7-1.3 (M), 0.6-1.1 (F) |
| BUN | `bun` | mg/dL | 7-20 |
| eGFR | `egfr` | mL/min/1.73m² | >90 |

### Thyroid
| Biomarker | Field Name | Unit | Normal Range |
|-----------|------------|------|--------------|
| TSH | `tsh` | mIU/L | 0.4-4.0 |

### Vitamins
| Biomarker | Field Name | Unit | Optimal |
|-----------|------------|------|---------|
| Vitamin D | `vitamin_d` | ng/mL | 30-100 |
| Vitamin B12 | `vitamin_b12` | pg/mL | 200-900 |

### Liver
| Biomarker | Field Name | Unit | Normal |
|-----------|------------|------|--------|
| ALT | `alt` | U/L | 7-56 |
| AST | `ast` | U/L | 10-40 |

### Inflammation
| Biomarker | Field Name | Unit | Low Risk |
|-----------|------------|------|----------|
| hs-CRP | `crp` | mg/L | <1.0 |

### Demographics (Optional)
| Field | Type | Description |
|-------|------|-------------|
| `age` | integer | Age in years |
| `sex` | string | "M" or "F" |

---

## Risk Levels

| Level | Meaning | Confidence Threshold |
|-------|---------|---------------------|
| `LOW` | Within normal parameters | ≥0.70 |
| `MODERATE` | Borderline/requires attention | ≥0.75 |
| `HIGH` | Significant concern/action needed | ≥0.80 |

---

## Clinical Sources

All inferences are based on established clinical guidelines:

- **ADA** - American Diabetes Association Standards of Medical Care
- **AHA/ACC** - American Heart Association / American College of Cardiology Lipid Guidelines
- **KDIGO** - Kidney Disease: Improving Global Outcomes Guidelines
- **ATA** - American Thyroid Association Guidelines
- **Endocrine Society** - Clinical Practice Guidelines

---

## Rate Limits

| Plan | Requests/Month | Requests/Second |
|------|----------------|-----------------|
| Free | 1,000 | 1 |
| Pro | 50,000 | 10 |
| Enterprise | Unlimited | 100 |

---

## Errors

| Code | Meaning |
|------|---------|
| 400 | Bad Request - Invalid input |
| 401 | Unauthorized - Invalid API key |
| 429 | Rate limit exceeded |
| 500 | Server error |

**Error Response:**
```json
{
  "error": "Invalid input",
  "message": "glucose must be a number",
  "code": 400
}
```

---

## SDKs

Coming soon:
- Python SDK
- JavaScript/TypeScript SDK
- REST API client

---

## Example: Python

```python
import requests

response = requests.post(
    "https://api.monitor.health/infer",
    json={
        "glucose": 108,
        "hemoglobin_a1c": 5.9,
        "total_cholesterol": 215,
        "ldl_cholesterol": 135,
        "hdl_cholesterol": 42,
        "triglycerides": 178
    }
)

data = response.json()
for inference in data["inferences"]:
    print(f"{inference['title']}: {inference['risk_level']} ({inference['confidence']*100:.0f}% confidence)")
```

---

## Example: JavaScript

```javascript
const response = await fetch('https://api.monitor.health/infer', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    glucose: 108,
    hemoglobin_a1c: 5.9,
    total_cholesterol: 215,
    ldl_cholesterol: 135,
    hdl_cholesterol: 42,
    triglycerides: 178
  })
});

const { inferences } = await response.json();
inferences.forEach(i => {
  console.log(`${i.title}: ${i.risk_level}`);
});
```

---

## Changelog

### v1.1.0 (2026-02-02)
- Added 20+ biomarker support
- Added thyroid, vitamin, liver assessments
- Enhanced confidence scoring
- Source citations in responses

### v1.0.0 (2026-02-01)
- Initial release
- Basic metabolic and lipid assessments

---

## Support

- **Email:** api@monitor.health
- **Documentation:** https://docs.monitor.health
- **Status:** https://status.monitor.health

---

*MONITOR is for informational purposes only and does not constitute medical advice. Always consult a healthcare professional for medical decisions.*
