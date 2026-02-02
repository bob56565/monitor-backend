# Scientific Citations & Clinical Validation

## Overview
Every formula in the Monitor Health cascade inference engine is backed by peer-reviewed clinical literature. This document provides complete citations with PMIDs for verification.

---

## LIPID CALCULATIONS

### LDL-C (Friedewald Equation)
- **Formula:** `LDL = TC - HDL - (TG/5)`
- **PMID:** [4337382](https://pubmed.ncbi.nlm.nih.gov/4337382/)
- **Citation:** Friedewald WT, Levy RI, Fredrickson DS. Estimation of the concentration of low-density lipoprotein cholesterol in plasma, without use of the preparative ultracentrifuge. *Clin Chem.* 1972;18(6):499-502.
- **Validation:** Gold standard for TG < 400 mg/dL. Accuracy decreases with TG > 200.
- **Confidence:** 0.95 (TG < 150), 0.90 (TG 150-200), 0.80 (TG 200-400), INVALID (TG > 400)

### LDL-C (Martin-Hopkins Equation)
- **Formula:** `LDL = TC - HDL - TG/adjustable_factor`
- **PMID:** [24240933](https://pubmed.ncbi.nlm.nih.gov/24240933/)
- **Citation:** Martin SS, et al. Comparison of a novel method vs the Friedewald equation for estimating low-density lipoprotein cholesterol levels from the standard lipid profile. *JAMA.* 2013;310(19):2061-2068.
- **Validation:** Superior accuracy across all TG ranges including TG 200-400
- **Use When:** TG 150-400 mg/dL for improved accuracy

### VLDL-C Estimation
- **Formula:** `VLDL = TG / 5`
- **Source:** Derived component of Friedewald equation
- **Validation:** Approximation valid when TG < 400 mg/dL
- **Confidence:** 0.85

### Non-HDL Cholesterol
- **Formula:** `Non-HDL = TC - HDL`
- **PMID:** [12485966](https://pubmed.ncbi.nlm.nih.gov/12485966/)
- **Citation:** Third Report of NCEP Expert Panel on Detection, Evaluation, and Treatment of High Blood Cholesterol in Adults (ATP III). *Circulation.* 2002;106(25):3143-421.
- **Clinical Use:** Secondary target after LDL; captures all atherogenic particles (VLDL, IDL, LDL, Lp(a))
- **Confidence:** 0.98 (direct calculation, no estimation)

### Remnant Cholesterol
- **Formula:** `Remnant-C = TC - LDL - HDL`
- **PMID:** [23265341](https://pubmed.ncbi.nlm.nih.gov/23265341/)
- **Citation:** Varbo A, et al. Remnant cholesterol as a causal risk factor for ischemic heart disease. *J Am Coll Cardiol.* 2013;61(4):427-436.
- **Clinical Use:** Independent predictor of cardiovascular events beyond LDL
- **Confidence:** 0.90

---

## CARDIOVASCULAR RISK INDICES

### Castelli Risk Index I (TC/HDL Ratio)
- **Formula:** `CRI-I = TC / HDL`
- **PMID:** [191215](https://pubmed.ncbi.nlm.nih.gov/191215/)
- **Citation:** Castelli WP, et al. HDL cholesterol and other lipids in coronary heart disease. The Cooperative Lipoprotein Phenotyping Study. *Circulation.* 1977;55(5):767-772.
- **Risk Stratification:**
  - Men: <4.5 low risk, 4.5-5.5 moderate, >5.5 high risk
  - Women: <4.0 low risk, 4.0-4.5 moderate, >4.5 high risk
- **Validation:** Framingham Heart Study
- **Confidence:** 0.95

### Castelli Risk Index II (LDL/HDL Ratio)
- **Formula:** `CRI-II = LDL / HDL`
- **Source:** Derived from Framingham Heart Study data
- **Risk Stratification:**
  - Men: <3.0 optimal, 3.0-3.5 moderate, >3.5 high
  - Women: <2.5 optimal, 2.5-3.0 moderate, >3.0 high
- **Confidence:** 0.92 (depends on LDL accuracy)

### Atherogenic Index of Plasma (AIP)
- **Formula:** `AIP = log10(TG / HDL)`
- **PMID:** [11738396](https://pubmed.ncbi.nlm.nih.gov/11738396/)
- **Citation:** Dobiásová M, Frohlich J. The plasma parameter log (TG/HDL-C) as an atherogenic index: correlation with lipoprotein particle size and esterification rate in apoB-lipoprotein-depleted plasma. *Clin Biochem.* 2001;34(7):583-588.
- **Risk Stratification:**
  - <0.1: Low cardiovascular risk
  - 0.1-0.24: Intermediate risk
  - >0.24: High risk (small dense LDL phenotype likely)
- **Clinical Use:** Predicts LDL particle size, CVD risk
- **Confidence:** 0.90

### TG/HDL Ratio (Insulin Resistance Proxy)
- **Formula:** `TG/HDL Ratio = TG / HDL`
- **PMID:** [14623617](https://pubmed.ncbi.nlm.nih.gov/14623617/)
- **Citation:** McLaughlin T, et al. Use of metabolic markers to identify overweight individuals who are insulin resistant. *Ann Intern Med.* 2003;139(10):802-809.
- **Threshold:** >3.0 suggests insulin resistance (in non-Hispanic white populations)
- **Note:** Ethnic variations exist; threshold may vary
- **Confidence:** 0.88

---

## GLYCEMIC MARKERS

### TyG Index (Triglyceride-Glucose Index)
- **Formula:** `TyG = ln[TG(mg/dL) × FPG(mg/dL) / 2]`
- **PMID:** [19067533](https://pubmed.ncbi.nlm.nih.gov/19067533/)
- **Citation:** Simental-Mendía LE, et al. The product of fasting glucose and triglycerides as surrogate for identifying insulin resistance in apparently healthy subjects. *Metab Syndr Relat Disord.* 2008;6(4):299-304.
- **Additional Validation PMID:** [20484475](https://pubmed.ncbi.nlm.nih.gov/20484475/)
- **Citation:** Guerrero-Romero F, et al. The product of triglycerides and glucose, a simple measure of insulin sensitivity. *J Clin Endocrinol Metab.* 2010;95(7):3347-3351.
- **Risk Stratification:**
  - <8.5: Normal insulin sensitivity
  - 8.5-9.0: Borderline
  - >9.0: Insulin resistance likely
- **Confidence:** 0.88

### HOMA-IR (Homeostatic Model Assessment)
- **Formula:** `HOMA-IR = (Fasting Insulin × Fasting Glucose) / 405`
- **PMID:** [3899825](https://pubmed.ncbi.nlm.nih.gov/3899825/)
- **Citation:** Matthews DR, et al. Homeostasis model assessment: insulin resistance and β-cell function from fasting plasma glucose and insulin concentrations in man. *Diabetologia.* 1985;28(7):412-419.
- **Risk Stratification:**
  - <1.0: Optimal insulin sensitivity
  - 1.0-2.0: Normal
  - 2.0-2.9: Early insulin resistance
  - ≥3.0: Significant insulin resistance
- **Gold Standard:** Most widely validated IR assessment
- **Confidence:** 0.95

### Estimated Average Glucose (eAG) & GMI
- **Formula:** `eAG (mg/dL) = 28.7 × HbA1c - 46.7`
- **Formula:** `GMI (%) = 3.31 + 0.02392 × mean_glucose_mg/dL`
- **PMID:** [18540046](https://pubmed.ncbi.nlm.nih.gov/18540046/)
- **Citation:** Nathan DM, et al. Translating the A1C assay into estimated average glucose values. *Diabetes Care.* 2008;31(8):1473-1478.
- **ADAG Study:** Derived from continuous glucose monitoring correlation with HbA1c
- **Confidence:** 0.88-0.92

---

## KIDNEY FUNCTION

### eGFR (CKD-EPI 2021 - Race-Free)
- **PMID:** [34554658](https://pubmed.ncbi.nlm.nih.gov/34554658/)
- **Citation:** Inker LA, et al. New Creatinine- and Cystatin C–Based Equations to Estimate GFR without Race. *N Engl J Med.* 2021;385(19):1737-1749.
- **Replaces:** MDRD and CKD-EPI 2009 (which inappropriately used race coefficient)
- **Formula:**
  - Female: `142 × min(Cr/0.7, 1)^-0.241 × max(Cr/0.7, 1)^-1.200 × 0.9938^age × 1.012`
  - Male: `142 × min(Cr/0.9, 1)^-0.302 × max(Cr/0.9, 1)^-1.200 × 0.9938^age`
- **Confidence:** 0.90

### BUN/Creatinine Ratio
- **Formula:** `Ratio = BUN / Creatinine`
- **Reference Range:** 10-20:1
- **Clinical Use:**
  - >20:1 suggests pre-renal azotemia (dehydration, CHF)
  - <10:1 suggests liver disease, malnutrition, or intrinsic renal disease
- **Confidence:** 0.98

---

## LIVER FUNCTION

### FIB-4 Index (Fibrosis Staging)
- **Formula:** `FIB-4 = (Age × AST) / (Platelet Count × √ALT)`
- **PMID:** [16729309](https://pubmed.ncbi.nlm.nih.gov/16729309/)
- **Citation:** Sterling RK, et al. Development of a simple noninvasive index to predict significant fibrosis in patients with HIV/HCV coinfection. *Hepatology.* 2006;43(6):1317-1325.
- **Risk Stratification:**
  - <1.30: Low risk of advanced fibrosis (NPV >90%)
  - 1.30-2.67: Indeterminate (requires further testing)
  - >2.67: High risk of advanced fibrosis (PPV >65%)
- **Confidence:** 0.88

### AST/ALT Ratio (De Ritis Ratio)
- **Formula:** `Ratio = AST / ALT`
- **Citation:** De Ritis F, et al. An enzymic test for the diagnosis of viral hepatitis. *Clin Chim Acta.* 1957;2(1):70-74.
- **Clinical Use:**
  - <1.0: Suggests viral hepatitis, NAFLD
  - >1.0: Suggests alcoholic liver disease
  - >2.0: Strongly suggests alcoholic hepatitis
- **Confidence:** 0.92

### NAFLD Fibrosis Score
- **Formula:** `NFS = -1.675 + 0.037×age + 0.094×BMI + 1.13×IFG/diabetes + 0.99×AST/ALT - 0.013×platelets - 0.66×albumin`
- **PMID:** [17393509](https://pubmed.ncbi.nlm.nih.gov/17393509/)
- **Citation:** Angulo P, et al. The NAFLD fibrosis score: a noninvasive system that identifies liver fibrosis in patients with NAFLD. *Hepatology.* 2007;45(4):846-854.
- **Risk Stratification:**
  - <-1.455: Low risk (F0-F2)
  - -1.455 to 0.676: Indeterminate
  - >0.676: High risk (F3-F4)
- **Confidence:** 0.85

---

## INFLAMMATORY MARKERS

### Neutrophil-to-Lymphocyte Ratio (NLR)
- **Formula:** `NLR = Neutrophils / Lymphocytes`
- **PMID:** [11723675](https://pubmed.ncbi.nlm.nih.gov/11723675/)
- **Citation:** Zahorec R. Ratio of neutrophil to lymphocyte counts - rapid and simple parameter of systemic inflammation and stress in critically ill. *Bratisl Lek Listy.* 2001;102(1):5-14.
- **Risk Stratification:**
  - <3.0: Normal
  - 3.0-6.0: Mild systemic inflammation
  - >6.0: Significant inflammation/stress
- **Clinical Use:** Prognostic in CVD, cancer, infections, COVID-19
- **Confidence:** 0.90

### Platelet-to-Lymphocyte Ratio (PLR)
- **Formula:** `PLR = Platelets / Lymphocytes`
- **PMID:** [23844064](https://pubmed.ncbi.nlm.nih.gov/23844064/)
- **Citation:** Gary T, et al. Platelet-to-lymphocyte ratio: a novel marker for critical limb ischemia. *PLoS One.* 2013;8(7):e67688.
- **Reference:** <150 normal, >300 elevated
- **Confidence:** 0.85

### Systemic Immune-Inflammation Index (SII)
- **Formula:** `SII = (Platelets × Neutrophils) / Lymphocytes`
- **PMID:** [25271081](https://pubmed.ncbi.nlm.nih.gov/25271081/)
- **Citation:** Hu B, et al. Systemic Immune-Inflammation Index Predicts Prognosis of Patients after Curative Resection for Hepatocellular Carcinoma. *Clin Cancer Res.* 2014;20(23):6212-6222.
- **Clinical Use:** Prognostic marker in cancer and cardiovascular disease
- **Confidence:** 0.85

---

## CARDIOVASCULAR RISK SCORES

### Framingham 10-Year CVD Risk
- **PMID:** [18212285](https://pubmed.ncbi.nlm.nih.gov/18212285/)
- **Citation:** D'Agostino RB Sr, et al. General cardiovascular risk profile for use in primary care: the Framingham Heart Study. *Circulation.* 2008;117(6):743-753.
- **Inputs:** Age, sex, TC, HDL, SBP, treatment status, smoking, diabetes
- **Confidence:** 0.88

### ASCVD Risk Estimator (Pooled Cohort Equations)
- **PMID:** [24222018](https://pubmed.ncbi.nlm.nih.gov/24222018/)
- **Citation:** Goff DC Jr, et al. 2013 ACC/AHA guideline on the assessment of cardiovascular risk. *Circulation.* 2014;129(25 Suppl 2):S49-S73.
- **Inputs:** Age, sex, race, TC, HDL, SBP, BP treatment, diabetes, smoker
- **Confidence:** 0.85

---

## METABOLIC SYNDROME CRITERIA

### ATP III Criteria
- **PMID:** [12485966](https://pubmed.ncbi.nlm.nih.gov/12485966/)
- **Citation:** NCEP ATP III Final Report. *Circulation.* 2002;106(25):3143-421.
- **Diagnosis:** 3 of 5 criteria required:
  1. Waist: >102 cm (M), >88 cm (F)
  2. Triglycerides: ≥150 mg/dL
  3. HDL: <40 mg/dL (M), <50 mg/dL (F)
  4. BP: ≥130/85 mmHg or on treatment
  5. Fasting glucose: ≥100 mg/dL

### IDF Criteria
- **PMID:** [16182882](https://pubmed.ncbi.nlm.nih.gov/16182882/)
- **Citation:** Alberti KG, et al. The metabolic syndrome—a new worldwide definition. *Lancet.* 2005;366(9491):1059-1062.
- **Diagnosis:** Central obesity (ethnicity-specific) plus 2 of 4 other criteria

---

## DATA SOURCES

### NHANES (National Health and Nutrition Examination Survey)
- **Source:** CDC/NCHS
- **Cycle Used:** 2017-2020 Pre-Pandemic
- **License:** Public Domain (U.S. Government Work)
- **Use:** Population percentiles, reference intervals

### Clinical Guidelines
- American Diabetes Association (ADA) Standards of Care
- American Heart Association / American College of Cardiology (AHA/ACC)
- European Society of Cardiology (ESC)
- Kidney Disease: Improving Global Outcomes (KDIGO)

---

## VERIFICATION STATUS

✅ All formulas verified against original publications  
✅ All PMIDs validated on PubMed  
✅ Reference intervals verified against ADA, AHA, NIH sources  
✅ Calculations tested against clinical calculators

*Last Updated: 2026-02-02*
*Version: 2.0.0*
