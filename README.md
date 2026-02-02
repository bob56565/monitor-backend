# MONITOR

**The Inference Layer for Preventive Health**

[![Demo](https://img.shields.io/badge/Demo-Live-green)](https://bob56565.github.io/monitor-demo/)
[![Pitch](https://img.shields.io/badge/Pitch-Deck-blue)](https://bob56565.github.io/monitor-pitch/)
[![Tests](https://img.shields.io/badge/Tests-184%20Passing-success)]()

MONITOR transforms raw biomarker data into confidence-scored health insights. We turn "glucose: 108 mg/dL" into "Pre-diabetes risk: MODERATE (87% confidence)."

## 🚀 Live Demo

**Try it now:** https://bob56565.github.io/monitor-demo/

Enter lab values and see real-time clinical inference with confidence scores.

## 📊 What We Do

| Input | Output |
|-------|--------|
| Glucose: 108 mg/dL | Glycemic Status: MODERATE |
| A1c: 5.9% | Confidence: 87% |
| HDL: 42 mg/dL | Contributing factors listed |
| Triglycerides: 178 mg/dL | Recommendations provided |

## ✨ Key Features

- **🎯 Confidence Scoring** - Explicit uncertainty (0-1) for every assessment
- **🧬 Multi-Specimen Fusion** - Blood, saliva, urine, sweat, ISF
- **📋 Clinically Verified** - All ranges verified against ADA, AHA, NIH
- **⚡ API-First** - Built for integration, not just consumers
- **📖 Explainable** - Every output traces to specific inputs and criteria

## 📦 Supported Biomarkers

### Metabolic
- Fasting Glucose
- Hemoglobin A1c
- Fasting Insulin

### Lipids
- Total Cholesterol
- LDL Cholesterol
- HDL Cholesterol
- Triglycerides

### Kidney Function
- Creatinine
- BUN
- eGFR

### Thyroid
- TSH

### Vitamins
- Vitamin D
- Vitamin B12

### Liver
- ALT
- AST

### Inflammation
- hs-CRP

## 🛠️ Quick Start

```bash
# Clone the repository
git clone https://github.com/bob56565/monitor-backend.git
cd monitor-backend

# Install dependencies
pip install -r requirements.txt

# Run the API
python -m uvicorn api_worker:app --reload

# Test it
curl http://localhost:8000/health
```

## 📡 API Usage

```bash
curl -X POST http://localhost:8000/infer \
  -H "Content-Type: application/json" \
  -d '{
    "glucose": 108,
    "hemoglobin_a1c": 5.9,
    "total_cholesterol": 215,
    "ldl_cholesterol": 135,
    "hdl_cholesterol": 42,
    "triglycerides": 178
  }'
```

Response:
```json
{
  "status": "success",
  "inferences": [
    {
      "key": "glycemic_status",
      "title": "Glycemic Status Assessment",
      "risk_level": "MODERATE",
      "confidence": 0.87,
      "explanation": "Based on ADA diagnostic criteria...",
      "recommendations": ["Lifestyle modifications recommended", ...]
    }
  ]
}
```

## 📁 Project Structure

```
monitor-backend/
├── app/                    # Main application
│   ├── api/               # FastAPI endpoints
│   ├── ml/                # Inference engines
│   ├── models/            # Data models
│   ├── part_b/            # Clinical inference panels
│   └── services/          # Core services
├── data/
│   └── priors_pack/       # Verified clinical reference data
├── docs/
│   └── CLINICAL_WHITEPAPER.md
├── ingestion/             # Specimen parsers
├── samples/               # Sample data for testing
├── tests/                 # Test suite (184 tests)
├── api_worker.py          # Lightweight API for demos
├── API_DOCUMENTATION.md   # Full API docs
├── CONTRIBUTING.md        # Contribution guidelines
├── PRIORS_VERIFICATION.md # Clinical data verification
└── ROADMAP.md             # Product roadmap
```

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [API Documentation](API_DOCUMENTATION.md) | Complete API reference |
| [Clinical Whitepaper](docs/CLINICAL_WHITEPAPER.md) | Methodology and clinical basis |
| [Priors Verification](PRIORS_VERIFICATION.md) | Reference data verification |
| [Roadmap](ROADMAP.md) | Product development plan |
| [Contributing](CONTRIBUTING.md) | How to contribute |

## 🔬 Clinical Methodology

All inferences are based on established clinical guidelines:

- **ADA** - American Diabetes Association Standards of Care
- **AHA/ACC** - Lipid and Blood Pressure Guidelines
- **KDIGO** - Kidney Disease Guidelines
- **Endocrine Society** - Vitamin and Thyroid Guidelines

See [CLINICAL_WHITEPAPER.md](docs/CLINICAL_WHITEPAPER.md) for full methodology.

## 📈 Code Statistics

| Metric | Value |
|--------|-------|
| Python Files | 126 |
| Lines of Code | 36,000+ |
| Tests | 184 passing |
| Biomarkers | 20+ |
| Clinical Outputs | 40+ |

## 🎯 Roadmap

- **Q1 2026**: Launch beta, first pilots
- **Q2 2026**: 50+ biomarkers, mobile apps
- **Q3 2026**: EHR integration, enterprise features
- **Q4 2026**: International expansion

See [ROADMAP.md](ROADMAP.md) for details.

## 💼 For Investors

- **Pitch Deck**: https://bob56565.github.io/monitor-pitch/
- **Live Demo**: https://bob56565.github.io/monitor-demo/
- **Raising**: $2M seed @ $10M pre-money

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📄 License

Proprietary - All rights reserved.

## 📧 Contact

**Abe Hamdan** - Founder & CEO
- Email: abedelhamdan@gmail.com
- GitHub: [@bob56565](https://github.com/bob56565)

---

**MONITOR** - Making health data actionable. 🧬
