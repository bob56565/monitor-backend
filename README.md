# MONITOR

**Multi-specimen health inference platform with clinic-grade outputs.**

## Overview

MONITOR transforms raw lab data, ISF readings, and other biomarkers into clinically meaningful health insights using rule-based inference with population priors.

### Key Features

- **40+ clinical outputs** with explicit eligibility gating
- **Confidence scoring** with component-level explanations  
- **Multi-specimen support**: Blood, saliva, sweat, urine, ISF
- **Full provenance tracking** for every inference
- **184 passing tests** with production-quality code

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Initialize database
alembic upgrade head

# Run API
uvicorn app.main:app --reload

# Run tests
pytest tests/ -v
```

## Architecture

```
Raw Data → Part A (Ingestion) → FeaturePackV2 → Part B (Inference) → InferencePackV2
```

### Components

| Component | Purpose |
|-----------|---------|
| `app/api/` | FastAPI endpoints |
| `app/ml/` | Inference engines (V1 legacy, V2 production) |
| `app/part_b/` | Clinical inference panels |
| `app/services/` | Confidence, gating, priors |
| `ingestion/` | Multi-format specimen parsers |
| `data/priors_pack/` | Population reference data (verified) |

## Clinical Methods

- **A1c estimation**: GMI formula (Bergenstal 2018)
- **eGFR calculation**: CKD-EPI 2021
- **Reference intervals**: Verified against ADA, AHA, NIH sources

See `PRIORS_VERIFICATION.md` for full verification report.

## Code Statistics

- **31,600 lines** of production Python
- **224 tests** across 14 test files
- **48 verified** reference range values

## License

Proprietary - All rights reserved.

## Contact

Abe Hamdan - abedelhamdan@gmail.com
