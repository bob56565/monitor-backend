# Data Licenses and Legal Compliance

## Overview
This document provides licensing information for all external data sources vendored into the MONITOR platform. All sources have been verified for permissive licensing that allows bundling and redistribution.

---

## License 1: CDC NHANES Data - Public Domain

### Applicable Artifacts
- `data/priors_pack/nhanes_vitals_percentiles.csv`
- `data/priors_pack/nhanes_lab_reference_intervals.csv`

### License Type
**Public Domain (U.S. Government Work)**

### Legal Basis
All NHANES data is produced by the U.S. Centers for Disease Control and Prevention (CDC), an agency of the U.S. Government. Under U.S. copyright law (17 USC § 105), works created by federal government employees as part of their official duties are not subject to copyright protection within the United States.

### Official CDC Statement
From CDC website (https://www.cdc.gov/other/agencymaterials.html):
> "Most material on the CDC website is not copyrighted and may be used freely by the public. Visitors may use, copy, or distribute any CDC content, though we do ask that you cite CDC as the source."

### Permissions Granted
✅ **Use**: Permitted  
✅ **Modification**: Permitted  
✅ **Distribution**: Permitted  
✅ **Commercial Use**: Permitted  
✅ **Bundling in Software**: Permitted  

### Attribution Requirement
While not legally required for public domain works, CDC requests citation. We provide:

**Citation**:
> Centers for Disease Control and Prevention (CDC). National Center for Health Statistics (NCHS). National Health and Nutrition Examination Survey Data. Hyattsville, MD: U.S. Department of Health and Human Services, Centers for Disease Control and Prevention, 2017-2020. Available from: https://wwwn.cdc.gov/nchs/nhanes/

### Data Use Restrictions (Ethical, Not Legal)
- NHANES data should not be used to attempt re-identification of survey participants
- Analysis should follow NHANES Analytic Guidelines for proper statistical handling
- We comply by using only aggregated statistics (no individual-level data retained)

---

## License 2: Clinical Guidelines - Derived Facts

### Applicable Artifacts
- `data/priors_pack/calibration_constants.json`

### License Type
**Derived Facts (Non-Copyrightable)**

### Legal Basis
The calibration constants file contains numeric thresholds and factual medical criteria extracted from published clinical guidelines. Under U.S. copyright law, facts are not copyrightable (Feist Publications, Inc. v. Rural Telephone Service Co., 499 U.S. 340 (1991)).

**Examples of non-copyrightable facts used**:
- "A1c <5.7% is considered normal" (ADA guideline)
- "Blood pressure <120/80 mmHg is optimal" (AHA/ACC guideline)
- "Glucose coefficient of variation <36% indicates stable glycemic control" (clinical consensus)

### Source Guidelines
Our calibration constants are derived from:

1. **American Diabetes Association (ADA)**
   - Standards of Care in Diabetes—2024
   - Copyright: ADA holds copyright on the full guideline text and specific phrasing
   - Our Use: We extract only numeric thresholds (facts), not copyrighted text or algorithms
   - Compliance: Facts like "A1c 5.7-6.4% = prediabetes" are not copyrightable

2. **American Heart Association / American College of Cardiology (AHA/ACC)**
   - 2017 Guideline for High Blood Pressure in Adults
   - Copyright: AHA/ACC hold copyright on full guideline document
   - Our Use: We extract only BP classification thresholds (facts)
   - Compliance: Categories like "Stage 1 hypertension = 130-139/80-89" are factual classifications

3. **European Society of Cardiology (ESC)**
   - Guidelines on Cardiovascular Disease Prevention (2021)
   - Copyright: ESC holds copyright on guideline text
   - Our Use: We use only factual risk thresholds
   - Compliance: Numeric cutoffs are non-copyrightable facts

4. **American College of Sports Medicine (ACSM)**
   - Guidelines for Exercise Testing and Prescription, 11th Ed (2021)
   - Copyright: ACSM/Wolters Kluwer hold copyright on full textbook
   - Our Use: We reference only established physiological norms (e.g., HRV ranges)
   - Compliance: Physiological reference values are scientific facts

### Permissions Granted
✅ **Use of Facts**: Permitted (cannot be copyrighted)  
✅ **Modification**: Permitted (we organize facts into JSON structure)  
✅ **Distribution**: Permitted (facts are public domain)  
✅ **Commercial Use**: Permitted (facts cannot be restricted)  

### Attribution Requirement
While facts cannot be copyrighted, we provide citations for scientific integrity:

**Citations Included in Code Comments and Documentation**:
- See `SOURCES.md` for full citation list
- See `calibration_constants.json` inline comments for specific threshold sources

### What We Do NOT Include
❌ **Copyrighted Text**: We do not reproduce paragraphs or explanatory text from guidelines  
❌ **Proprietary Algorithms**: We do not use patented or proprietary risk calculators  
❌ **Full Guidelines**: We do not bundle entire guideline PDFs  

---

## License 3: HRV Reference Data - Academic Commons

### Applicable Artifacts
- HRV (RMSSD) percentiles in `nhanes_vitals_percentiles.csv`

### License Type
**Derived from Published Scientific Literature (Fair Use)**

### Legal Basis
HRV reference values are compiled from multiple published peer-reviewed studies. We use only summary statistics (means, SDs, percentile ranges) which are facts. Short excerpts of factual data from scientific papers for transformative use (building a clinical decision support system) fall under fair use.

### Source Studies
Primary references:
- Nunan D, et al. "A quantitative systematic review of normal values for short-term heart rate variability in healthy adults." *Pacing Clin Electrophysiol.* 2010;33(11):1407-17.
- Tegegne BS, et al. "Determinants of heart rate variability in the general population." *Heart Rhythm.* 2018;15(10):1552-1558.

### Our Use
- We extract only age- and sex-stratified summary statistics (percentile ranges)
- We do not reproduce copyrighted figures, tables, or textual analysis
- Use is transformative (creating population priors for a different purpose than original research)

### Compliance
✅ Minimal extraction of factual data  
✅ Transformative use (clinical application, not competing research publication)  
✅ Full citation provided  
✅ Does not harm market for original works  

---

## Licensing Compliance Checklist

| Requirement | Status | Evidence |
|-------------|--------|----------|
| All data sources have permissive licenses | ✅ Yes | NHANES (public domain), guidelines (facts), HRV (fair use) |
| Redistribution rights confirmed | ✅ Yes | Public domain and facts allow unrestricted distribution |
| Attributions provided | ✅ Yes | See SOURCES.md and manifest.json |
| No proprietary/paid data included | ✅ Yes | All sources are freely accessible |
| No copyright infringement | ✅ Yes | Only facts/aggregates, no copyrighted text |
| Commercial use permitted | ✅ Yes | Public domain and facts have no restrictions |
| Version/release pinned | ✅ Yes | NHANES 2017-2020 cycle; guideline years documented |
| Checksums recorded | ✅ Yes | See manifest.json |

---

## Third-Party License Requirements (None)

The MONITOR platform does not incorporate any third-party datasets with restrictive licenses such as:
- ❌ CC BY-NC (Non-Commercial) — would prohibit commercial deployment
- ❌ CC BY-SA (Share-Alike) — would require open-sourcing entire platform
- ❌ Proprietary/Paid APIs — would require runtime licensing fees
- ❌ Academic-Use-Only datasets — would prohibit clinical deployment

All data is either public domain or non-copyrightable facts.

---

## Downstream License Implications

**MONITOR Platform License**: The priors pack data does not impose any licensing restrictions on the MONITOR platform itself. The platform may be licensed under any license chosen by the copyright holders (e.g., MIT, Apache 2.0, proprietary).

**User Obligations**: Users of the MONITOR platform do not need to comply with any data licensing terms, as all priors are public domain or facts. However, for scientific integrity, users should cite MONITOR and underlying sources when publishing research using the platform.

---

## Annual Review Process

**Responsible Party**: Platform maintainers  
**Frequency**: Annually, or when updating to new NHANES cycle  
**Checklist**:
1. Verify CDC NHANES data remains public domain (check CDC website policy)
2. Check for updates to clinical guidelines (ADA/AHA/ESC release new versions)
3. Confirm no changes to copyright law affecting fair use of medical facts
4. Update SOURCES.md and this file with new versions and retrieval dates
5. Re-run `scripts/build_priors_pack.py` if sources updated

---

## Disclaimer

This document represents our good-faith legal analysis and compliance efforts. It is not legal advice. Organizations deploying MONITOR should consult their own legal counsel, especially for:
- International deployment (non-U.S. copyright laws may differ)
- Use in regulated environments (FDA, EMA, etc.)
- Integration with other proprietary systems

---

## Contact

Legal questions about data licensing: [Contact platform legal team or maintainers]  
Technical questions about data sources: See SOURCES.md  
Report licensing concerns: [Open GitHub issue or contact maintainers]

---

**Last Updated**: 2026-01-29  
**Next Review Due**: 2027-01-29
