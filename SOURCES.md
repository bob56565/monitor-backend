# Data Sources Documentation

## Overview
This document catalogs all external data sources used in the MONITOR platform's priors pack. All data is vendored into the repository and loaded locally at runtime (no external HTTP calls).

---

## Source 1: CDC NHANES (National Health and Nutrition Examination Survey)

### What We Used
**Dataset**: NHANES 2017-2020 Pre-Pandemic Cycle  
**Components Extracted**:
- Examination data (vitals: blood pressure, heart rate, anthropometry)
- Laboratory data (biochemistry panels: CMP, CBC, lipids, endocrine, vitamins, inflammation markers)

### Why We Chose This Source
- **Public Domain**: All NHANES data is U.S. Government work and not subject to copyright
- **Credible**: Gold standard for U.S. population health statistics, managed by CDC/NCHS
- **Representative**: Nationally representative sample of non-institutionalized U.S. population
- **Comprehensive**: Covers demographics, vitals, labs, and health conditions we need for priors
- **Well-Documented**: Extensive codebooks, quality control procedures, and statistical guidance

### What We Extracted and Transformed

#### Artifact 1: `nhanes_vitals_percentiles.csv`
**Source Files**: 
- Examination files (P_BMX.XPT, P_BPXO.XPT for 2017-2020)
- Demographics (P_DEMO.XPT)

**Extraction Process**:
1. Downloaded examination data files from NHANES 2017-2020 cycle
2. Filtered to adults (18+) with complete data for each metric
3. Stratified by age groups (18-29, 30-39, 40-49, 50-59, 60-69, 70+) and sex (M/F)
4. Computed 5th, 10th, 25th, 50th, 75th, 90th, 95th percentiles for each stratum
5. Metrics included:
   - Resting heart rate (bpm)
   - Systolic and diastolic blood pressure (mmHg)
   - BMI (kg/m²)
   - Waist circumference (cm)
   - HRV proxy (RMSSD in ms - derived from heart rate variability studies, not direct NHANES measurement)

**Transformations**: Aggregated raw individual records into percentile tables; no individual-level data retained.

**Where Used in MONITOR**:
- Priors service: `get_percentiles()` for population context
- Confidence engine: To assess how far a user's values deviate from population norms
- Part B outputs: To provide percentile rankings (e.g., "Your resting HR is at the 75th percentile for your age/sex")

---

#### Artifact 2: `nhanes_lab_reference_intervals.csv`
**Source Files**:
- Laboratory files for 2017-2020 (P_BIOPRO.XPT, P_CBC.XPT, P_TCHOL.XPT, P_TRIGLY.XPT, P_GHB.XPT, P_INS.XPT, P_FERTIN.XPT, P_FOLATE.XPT, P_VID.XPT, etc.)
- Demographics (P_DEMO.XPT)

**Extraction Process**:
1. Downloaded laboratory data files covering CMP, CBC, lipids, endocrine, vitamins, inflammation markers
2. Filtered to healthy reference population (exclusion criteria: known diabetes, CVD, renal disease, pregnancy, certain medications)
3. Stratified by age and sex where physiologically relevant (e.g., creatinine, HDL, hemoglobin)
4. Computed 2.5th and 97.5th percentiles as reference interval bounds (standard clinical practice)
5. Added critical thresholds from clinical literature (e.g., severe hypoglycemia <40 mg/dL)

**Transformations**: Aggregated raw lab values into reference intervals; no individual-level data retained.

**Where Used in MONITOR**:
- Priors service: `get_reference_interval()` to validate uploaded lab values
- Quality gating: To flag values outside critical thresholds
- Part A parsers: Fallback reference ranges when lab doesn't provide them
- Confidence engine: Anchor validation (is the uploaded lab value plausible?)

---

## Source 2: Clinical Guidelines Compilation

### What We Used
**Dataset**: Calibration constants and gating thresholds derived from published clinical guidelines  
**Sources**:
- American Diabetes Association (ADA) Standards of Care
- American Heart Association / American College of Cardiology (AHA/ACC) Guidelines
- European Society of Cardiology (ESC) Guidelines
- American College of Sports Medicine (ACSM) Exercise Testing and Prescription

### Why We Chose These Sources
- **Authoritative**: Professional society guidelines represent consensus expert opinion
- **Factual**: Specific numeric thresholds (e.g., A1c <5.7% = normal) are non-copyrightable facts
- **Clinically Validated**: Used worldwide in clinical practice and research

### What We Extracted and Transformed

#### Artifact 3: `calibration_constants.json`
**Content**:
- Minimum data windows for various inference types (e.g., 30 days for A1c estimate)
- Signal quality thresholds for tight vs wide range outputs
- Anchor requirements (e.g., tight A1c estimate requires recent A1c lab within 90 days)
- Confidence cap parameters (95% for measured, 85% for tight inferred, 70% for wide)
- Typical variability bounds (e.g., glucose CV <36% is normal)
- Time windows for recency decay (90-day half-life for lab relevance)

**Transformations**: Manual curation from guidelines; extracted specific numeric thresholds and compiled into structured JSON.

**Where Used in MONITOR**:
- Confidence engine: Loads confidence parameters to compute bounded confidence scores
- Gating engine: Loads gating thresholds to enforce minimum data requirements
- Part B inference: Uses variability bounds to classify glucose stability, BP control, etc.

---

## Data Retrieval and Versioning

### NHANES Data
**Official Portal**: https://wwwn.cdc.gov/nchs/nhanes/continuousnhanes/default.aspx?Cycle=2017-2020  
**Retrieval Date**: 2026-01-29  
**Version/Release**: 2017-2020 Pre-Pandemic Cycle (released 2021-09)  
**File Format**: SAS Transport (.XPT) → converted to CSV for priors tables  
**Checksums**: See `manifest.json` for SHA-256 checksums of vendored CSV files

### Clinical Guidelines
**Retrieval Date**: 2026-01-29  
**Versions**:
- ADA Standards of Care in Diabetes—2024
- 2017 ACC/AHA Guideline for High Blood Pressure in Adults
- ESC Guidelines on Cardiovascular Disease Prevention (2021)
- ACSM's Guidelines for Exercise Testing and Prescription, 11th Edition (2021)

---

## Reproducibility

The priors pack can be fully rebuilt using the script:
```bash
python scripts/build_priors_pack.py
```

This script:
1. Downloads exact versions of NHANES data files (pinned to 2017-2020 cycle)
2. Applies documented filters and transformations
3. Computes percentiles and reference intervals
4. Validates against expected checksums
5. Writes output CSV files to `data/priors_pack/`

**Note**: The script requires ~500MB download space and takes ~10 minutes to run. The repository ships with pre-built priors tables to avoid requiring maintainers to rebuild unless updating sources.

---

## Data Minimization and Privacy

- **No Individual-Level Data**: All vendored files contain only aggregated statistics (percentiles, reference intervals)
- **No PHI**: NHANES data is already de-identified; our priors pack contains no identifiable information
- **Minimal Extraction**: We extract only the subset needed for priors; full NHANES datasets are not included

---

## Usage in MONITOR Platform

| Priors Artifact | Loaded By | Used By | Purpose |
|-----------------|-----------|---------|---------|
| `nhanes_vitals_percentiles.csv` | `app/services/priors.py` | Confidence engine, Part B outputs | Population context, percentile rankings |
| `nhanes_lab_reference_intervals.csv` | `app/services/priors.py` | Part A parsers, Quality gating, Confidence engine | Validate uploads, fallback reference ranges |
| `calibration_constants.json` | Confidence engine, Gating engine | Part B inference modules | Thresholds, caps, time windows |

---

## Future Updates

To update priors pack to a newer NHANES cycle:
1. Update `scripts/build_priors_pack.py` with new cycle year (e.g., 2021-2023)
2. Run the builder script
3. Update `manifest.json` with new version and checksums
4. Update this `SOURCES.md` with new retrieval date and version
5. Commit vendored files with clear commit message indicating version bump

---

## Contact

For questions about data sources or to report issues with priors pack:
- Check `manifest.json` for artifact metadata
- Review `DATA_LICENSES.md` for licensing details
- See `scripts/build_priors_pack.py` for technical implementation
