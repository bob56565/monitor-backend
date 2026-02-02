# MONITOR Platform - Quick Start Guide

## 🚀 One-Command Demo Launch

\`\`\`bash
# Ensure services are running
docker-compose up -d postgres && uvicorn app.main:app --host 0.0.0.0 --port 8000
\`\`\`

## 🌐 Access URLs

- **Complete 0→5 Demo:** http://localhost:8000/
- **API Documentation:** http://localhost:8000/docs
- **Phase 3 Only Demo:** http://localhost:8000/phase3-only

## ⚡ Quick Verification

\`\`\`bash
# Check server health
curl http://localhost:8000/health

# Run Phase 3 tests
pytest tests/test_phase3.py -v

# Run all core tests (Phase 1+2+3 + A2 backbone)
pytest tests/test_phase{1,2,3}.py tests/test_a2_backbone.py -v
\`\`\`

## 📊 Test Results

- Phase 1: 19/19 ✅
- Phase 2: 21/21 ✅
- Phase 3: 23/23 ✅
- A2 Backbone: 35/35 ✅
- **Total:** 98/98 passing

## 🔄 Demo Journey (0→5)

1. **0️⃣ Auth:** Signup/Login → JWT token
2. **1️⃣ Part A:** Multi-specimen data ingestion (RunV2)
3. **2️⃣ A2 Processing:** Phase 1 → Phase 2 → Phase 3 (all 7 modules)
4. **3️⃣ Part B:** Output generation (6 streams)
5. **4️⃣ Visualization:** Collapsible results panels
6. **5️⃣ Takeaways:** Answer 5 key questions

## ⚠️ Troubleshooting

**Seeing old UI?**
- Press \`Ctrl+Shift+R\` (hard refresh)
- Or open in incognito: \`Ctrl+Shift+N\`

**Server not responding?**
\`\`\`bash
pkill -f uvicorn
uvicorn app.main:app --host 0.0.0.0 --port 8000
\`\`\`

**Database issues?**
\`\`\`bash
docker-compose restart postgres
\`\`\`

## 📝 Phase 3 Features

All 7 decision intelligence modules implemented:

- **A2.1:** Uncertainty Reduction Planner (info gain)
- **A2.2:** Cohort Matching Engine (percentiles)
- **A2.3:** Change Point Detection (Bayesian)
- **B.4:** Provider Summary Generator (clinician text)
- **B.5:** Cost/Care Impact (evidence grades)
- **B.6:** Explainability ("because" sentences)
- **B.7:** Language Control (non-diagnostic)

## 🔗 Documentation

- Full diagnostic: \`DIAGNOSTIC_EVIDENCE_PACKAGE.md\`
- Phase 3 summary: \`PHASE3_IMPLEMENTATION_SUMMARY.md\`
- API reference: http://localhost:8000/docs
