# MONITOR Scientific Data Sources

## Active Database Integrations

### 1. PubMed/NCBI (Implemented)
- **API:** https://eutils.ncbi.nlm.nih.gov/entrez/eutils/
- **Auth:** None required
- **Data:** Research papers, abstracts, citations
- **Use:** Validating biomarker correlations, evidence base

### 2. NIH Clinical Tables (Implemented)
- **API:** https://clinicaltables.nlm.nih.gov/api/
- **Auth:** None required
- **Data:** Clinical conditions, symptoms, treatments
- **Use:** Condition mapping, symptom correlations

### 3. OpenFDA (To Implement)
- **API:** https://api.fda.gov/
- **Auth:** None required
- **Data:** Drug interactions, adverse events
- **Use:** Medication context for interpretations

### 4. ClinicalTrials.gov (To Implement)
- **API:** https://clinicaltrials.gov/api/
- **Auth:** None required
- **Data:** Trial outcomes, intervention data
- **Use:** Treatment efficacy data

### 5. OpenEvidence (Requires Browser Login)
- **URL:** https://www.openevidence.com
- **Auth:** abedelhamdan@gmail.com / Hamdan56!
- **Data:** NEJM, JAMA, NCCN guidelines
- **Use:** Current clinical guidelines

## Pending Integrations

### LOINC (Lab Codes)
- Standard lab test identifiers
- Mapping consumer device outputs to clinical terms

### SNOMED CT
- Clinical terminology
- Standardized condition coding

### RxNorm
- Medication normalization
- Drug interaction checking

## Research Paper Sources

### Key Search Terms
1. "biomarker multi-analyte prediction"
2. "glucose HbA1c correlation"
3. "CGM glucose variability outcomes"
4. "lipid panel cardiovascular risk"
5. "metabolic syndrome criteria validation"

### Retrieved Paper IDs (PubMed)
- Glucose-A1c: 41619945, 41619054, 41607455, 41603531, 41601819
- Multi-biomarker: 41424613, 41359082, 41243077, 39615253, 39288894

## Data Quality Requirements

1. **Peer-reviewed sources only**
2. **Publication date < 5 years preferred**
3. **Sample size > 1000 for population data**
4. **Multiple validation studies required**

## Citation Format

All data sources must be cited in outputs:
```
Source: [Author] et al., [Journal], [Year]. PMID: [ID]
```
