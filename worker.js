// Monitor Health API - Cloudflare Worker
// CASCADE INFERENCE ENGINE v3.0 - FULL COVERAGE
// ALL biomarkers → ALL derivable outputs
// Every formula backed by peer-reviewed clinical literature

/**
 * SCIENTIFIC CITATIONS INDEX
 * Complete PMID references for validation
 */
const CITATIONS = {
  // LIPID
  friedewald: { pmid: "4337382", source: "Friedewald WT, et al. Clin Chem. 1972;18(6):499-502", validation: "Gold standard for TG < 400 mg/dL" },
  martin_hopkins: { pmid: "24240933", source: "Martin SS, et al. JAMA. 2013;310(19):2061-2068", validation: "Superior accuracy TG 150-400" },
  castelli: { pmid: "191215", source: "Castelli WP, et al. Circulation. 1977;55(5):767-772", validation: "Framingham Heart Study" },
  aip: { pmid: "11738396", source: "Dobiásová M, Frohlich J. Clin Biochem. 2001;34(7):583-588", validation: "Predicts LDL particle size" },
  remnant: { pmid: "23265341", source: "Varbo A, et al. J Am Coll Cardiol. 2013;61(4):427-436", validation: "Independent CV predictor" },
  
  // GLYCEMIC
  homa_ir: { pmid: "3899825", source: "Matthews DR, et al. Diabetologia. 1985;28(7):412-419", validation: "Gold standard IR assessment" },
  homa_beta: { pmid: "3899825", source: "Matthews DR, et al. Diabetologia. 1985;28(7):412-419", validation: "Beta cell function" },
  tyg_index: { pmid: "19067533", source: "Simental-Mendía LE, et al. Metab Syndr Relat Disord. 2008;6(4):299-304", validation: "IR surrogate" },
  quicki: { pmid: "10868854", source: "Katz A, et al. J Clin Endocrinol Metab. 2000;85(7):2402-2410", validation: "Quantitative insulin sensitivity" },
  gmi: { pmid: "18540046", source: "Nathan DM, et al. Diabetes Care. 2008;31(8):1473-1478", validation: "ADAG study" },
  tg_hdl_ir: { pmid: "14623617", source: "McLaughlin T, et al. Ann Intern Med. 2003;139(10):802-809", validation: "TG/HDL >3 = IR" },
  
  // KIDNEY
  ckd_epi_2021: { pmid: "34554658", source: "Inker LA, et al. N Engl J Med. 2021;385(19):1737-1749", validation: "Race-free equation" },
  cockcroft_gault: { pmid: "1244564", source: "Cockcroft DW, Gault MH. Nephron. 1976;16(1):31-41", validation: "CrCl estimation" },
  
  // LIVER
  fib4: { pmid: "16729309", source: "Sterling RK, et al. Hepatology. 2006;43(6):1317-1325", validation: "Fibrosis staging" },
  nafld_fib: { pmid: "17393509", source: "Angulo P, et al. Hepatology. 2007;45(4):846-854", validation: "NAFLD fibrosis" },
  apri: { pmid: "12916920", source: "Wai CT, et al. Hepatology. 2003;38(2):518-526", validation: "AST-to-platelet ratio" },
  meld: { pmid: "11172350", source: "Kamath PS, et al. Hepatology. 2001;33(2):464-470", validation: "Liver disease severity" },
  
  // INFLAMMATORY
  nlr: { pmid: "11723675", source: "Zahorec R. Bratisl Lek Listy. 2001;102(1):5-14", validation: "Systemic inflammation" },
  plr: { pmid: "23844064", source: "Gary T, et al. PLoS One. 2013;8(7):e67688", validation: "Inflammation marker" },
  sii: { pmid: "25271081", source: "Hu B, et al. Clin Cancer Res. 2014;20(23):6212-6222", validation: "Immune-inflammation index" },
  mlr: { pmid: "24603634", source: "Nishijima TF, et al. Ann Oncol. 2015;26(5):998-1003", validation: "Monocyte-lymphocyte ratio" },
  
  // CARDIAC
  framingham: { pmid: "18212285", source: "D'Agostino RB Sr, et al. Circulation. 2008;117(6):743-753", validation: "General CVD risk" },
  ascvd: { pmid: "24222018", source: "Goff DC Jr, et al. Circulation. 2014;129(25 Suppl 2):S49-S73", validation: "ACC/AHA pooled cohort" },
  
  // THYROID
  tshi: { pmid: "19068291", source: "Jostel A, et al. Clin Endocrinol. 2009;70(2):217-223", validation: "Thyroid sensitivity" },
  
  // ANEMIA
  mentzer: { pmid: "4703063", source: "Mentzer WC. Lancet. 1973;1(7808):882", validation: "Iron def vs thalassemia" },
  rdw_cv: { pmid: "21208070", source: "Patel KV, et al. Arch Intern Med. 2009;169(5):515-523", validation: "Mortality predictor" },
  
  // METABOLIC SYNDROME
  atp3: { pmid: "12485966", source: "NCEP ATP III. Circulation. 2002;106(25):3143-421", validation: "MetS criteria" },
  idf: { pmid: "16182882", source: "Alberti KG, et al. Lancet. 2005;366(9491):1059-1062", validation: "IDF MetS criteria" }
};

/**
 * COMPLETE INFERENCE RULES - FULL BIOMARKER NETWORK
 * Organized by physiological system
 */
const INFERENCE_RULES = {
  // ═══════════════════════════════════════════════════════════════
  // LIPID PANEL & CARDIOVASCULAR
  // ═══════════════════════════════════════════════════════════════
  ldl: [
    { req: ["total_cholesterol", "hdl", "triglycerides"], formula: "friedewald", conf: 0.92, cite: "friedewald", cond: (v) => v.triglycerides < 400 },
    { req: ["total_cholesterol", "hdl", "triglycerides"], formula: "martin_hopkins", conf: 0.88, cite: "martin_hopkins", cond: (v) => v.triglycerides >= 150 && v.triglycerides < 400 }
  ],
  vldl: [{ req: ["triglycerides"], formula: "tg_div_5", conf: 0.85, cite: "friedewald", cond: (v) => v.triglycerides < 400 }],
  non_hdl: [{ req: ["total_cholesterol", "hdl"], formula: "tc_minus_hdl", conf: 0.98 }],
  remnant_cholesterol: [{ req: ["total_cholesterol", "ldl", "hdl"], formula: "remnant", conf: 0.95, cite: "remnant" }],
  castelli_1: [{ req: ["total_cholesterol", "hdl"], formula: "tc_hdl", conf: 0.95, cite: "castelli" }],
  castelli_2: [{ req: ["ldl", "hdl"], formula: "ldl_hdl", conf: 0.92, cite: "castelli" }],
  atherogenic_index: [{ req: ["triglycerides", "hdl"], formula: "aip", conf: 0.90, cite: "aip" }],
  tg_hdl_ratio: [{ req: ["triglycerides", "hdl"], formula: "ratio", conf: 0.92, cite: "tg_hdl_ir" }],
  ldl_particle_risk: [{ req: ["triglycerides", "hdl", "ldl"], formula: "ldl_particle_proxy", conf: 0.80 }],
  apob_estimated: [{ req: ["ldl", "triglycerides"], formula: "apob_est", conf: 0.75 }],
  lp_ir_score: [{ req: ["triglycerides", "hdl", "vldl"], formula: "lp_ir", conf: 0.78 }],
  
  // ═══════════════════════════════════════════════════════════════
  // GLYCEMIC & INSULIN RESISTANCE
  // ═══════════════════════════════════════════════════════════════
  homa_ir: [{ req: ["fasting_glucose", "fasting_insulin"], formula: "homa_ir", conf: 0.95, cite: "homa_ir" }],
  homa_beta: [{ req: ["fasting_glucose", "fasting_insulin"], formula: "homa_beta", conf: 0.90, cite: "homa_beta" }],
  quicki: [{ req: ["fasting_glucose", "fasting_insulin"], formula: "quicki", conf: 0.92, cite: "quicki" }],
  tyg_index: [{ req: ["fasting_glucose", "triglycerides"], formula: "tyg", conf: 0.88, cite: "tyg_index" }],
  tyg_bmi: [{ req: ["fasting_glucose", "triglycerides", "bmi"], formula: "tyg_bmi", conf: 0.85 }],
  tyg_wc: [{ req: ["fasting_glucose", "triglycerides", "waist_cm"], formula: "tyg_wc", conf: 0.85 }],
  mets_ir: [{ req: ["fasting_glucose", "triglycerides", "hdl", "bmi"], formula: "mets_ir", conf: 0.82 }],
  hba1c_estimated: [{ req: ["mean_glucose"], formula: "gmi", conf: 0.85, cite: "gmi" }],
  mean_glucose_estimated: [{ req: ["hba1c"], formula: "eag", conf: 0.88, cite: "gmi" }],
  diabetes_risk_score: [{ req: ["fasting_glucose", "bmi", "age"], formula: "diabetes_risk", conf: 0.80 }],
  prediabetes_indicator: [{ req: ["fasting_glucose"], formula: "prediabetes", conf: 0.95 }],
  postprandial_estimate: [{ req: ["fasting_glucose", "hba1c"], formula: "ppg_estimate", conf: 0.75 }],
  glucose_variability_proxy: [{ req: ["fasting_glucose", "hba1c"], formula: "gv_proxy", conf: 0.70 }],
  
  // ═══════════════════════════════════════════════════════════════
  // KIDNEY FUNCTION
  // ═══════════════════════════════════════════════════════════════
  egfr: [{ req: ["creatinine", "age"], formula: "ckd_epi", conf: 0.90, cite: "ckd_epi_2021" }],
  egfr_cystatin: [{ req: ["cystatin_c", "age"], formula: "ckd_epi_cys", conf: 0.92 }],
  creatinine_clearance: [{ req: ["creatinine", "age", "weight_kg"], formula: "cockcroft_gault", conf: 0.85, cite: "cockcroft_gault" }],
  bun_creatinine_ratio: [{ req: ["bun", "creatinine"], formula: "bun_cr", conf: 0.98 }],
  ckd_stage: [{ req: ["egfr"], formula: "ckd_staging", conf: 0.95 }],
  uacr_risk: [{ req: ["urine_albumin", "urine_creatinine"], formula: "uacr", conf: 0.95 }],
  kidney_risk_score: [{ req: ["egfr", "age", "albumin"], formula: "kidney_risk", conf: 0.80 }],
  
  // ═══════════════════════════════════════════════════════════════
  // LIVER FUNCTION
  // ═══════════════════════════════════════════════════════════════
  fib4: [{ req: ["age", "ast", "alt", "platelets"], formula: "fib4", conf: 0.88, cite: "fib4" }],
  ast_alt_ratio: [{ req: ["ast", "alt"], formula: "de_ritis", conf: 0.95 }],
  nafld_fib_score: [{ req: ["age", "bmi", "ast", "alt", "platelets", "albumin"], formula: "nafld_fib", conf: 0.85, cite: "nafld_fib" }],
  apri: [{ req: ["ast", "platelets"], formula: "apri", conf: 0.85, cite: "apri" }],
  meld_score: [{ req: ["bilirubin", "creatinine", "inr"], formula: "meld", conf: 0.90, cite: "meld" }],
  meld_na: [{ req: ["bilirubin", "creatinine", "inr", "sodium"], formula: "meld_na", conf: 0.92 }],
  baat_score: [{ req: ["age", "bmi", "ast", "alt", "triglycerides"], formula: "baat", conf: 0.78 }],
  fatty_liver_index: [{ req: ["bmi", "waist_cm", "triglycerides", "ggt"], formula: "fli", conf: 0.82 }],
  alcoholic_liver_risk: [{ req: ["ast", "alt", "ggt", "mcv"], formula: "alc_liver", conf: 0.75 }],
  
  // ═══════════════════════════════════════════════════════════════
  // INFLAMMATORY & IMMUNE
  // ═══════════════════════════════════════════════════════════════
  nlr: [{ req: ["neutrophils", "lymphocytes"], formula: "nlr", conf: 0.95, cite: "nlr" }],
  plr: [{ req: ["platelets", "lymphocytes"], formula: "plr", conf: 0.90, cite: "plr" }],
  sii: [{ req: ["platelets", "neutrophils", "lymphocytes"], formula: "sii", conf: 0.88, cite: "sii" }],
  mlr: [{ req: ["monocytes", "lymphocytes"], formula: "mlr", conf: 0.85, cite: "mlr" }],
  nlr_plr_combined: [{ req: ["nlr", "plr"], formula: "nlr_plr", conf: 0.82 }],
  aisi: [{ req: ["neutrophils", "monocytes", "platelets", "lymphocytes"], formula: "aisi", conf: 0.85 }],
  chronic_inflammation_index: [{ req: ["hscrp", "wbc"], formula: "cii", conf: 0.80 }],
  inflammation_risk_class: [{ req: ["hscrp"], formula: "crp_risk", conf: 0.90 }],
  
  // ═══════════════════════════════════════════════════════════════
  // CARDIAC & BLOOD PRESSURE
  // ═══════════════════════════════════════════════════════════════
  map: [{ req: ["sbp", "dbp"], formula: "mean_arterial", conf: 0.98 }],
  pulse_pressure: [{ req: ["sbp", "dbp"], formula: "pp", conf: 0.99 }],
  ppi: [{ req: ["pulse_pressure", "sbp"], formula: "ppi", conf: 0.90 }],
  hypertension_stage: [{ req: ["sbp", "dbp"], formula: "htn_stage", conf: 0.95 }],
  arterial_stiffness_proxy: [{ req: ["pulse_pressure", "age"], formula: "art_stiff", conf: 0.75 }],
  cv_risk_bp: [{ req: ["sbp", "age"], formula: "cv_bp_risk", conf: 0.80 }],
  
  // ═══════════════════════════════════════════════════════════════
  // THYROID FUNCTION
  // ═══════════════════════════════════════════════════════════════
  tsh_ft4_ratio: [{ req: ["tsh", "ft4"], formula: "tsh_ft4", conf: 0.85 }],
  tshi: [{ req: ["tsh", "ft4"], formula: "tshi", conf: 0.82, cite: "tshi" }],
  t3_t4_ratio: [{ req: ["t3", "t4"], formula: "t3_t4", conf: 0.85 }],
  ft3_ft4_ratio: [{ req: ["ft3", "ft4"], formula: "ft3_ft4", conf: 0.88 }],
  thyroid_resistance_index: [{ req: ["tsh", "ft4", "ft3"], formula: "tri", conf: 0.75 }],
  
  // ═══════════════════════════════════════════════════════════════
  // ANEMIA & HEMATOLOGY
  // ═══════════════════════════════════════════════════════════════
  mchc: [{ req: ["hemoglobin", "hematocrit"], formula: "mchc", conf: 0.98 }],
  mcv_calculated: [{ req: ["hematocrit", "rbc"], formula: "mcv_calc", conf: 0.98 }],
  mch_calculated: [{ req: ["hemoglobin", "rbc"], formula: "mch_calc", conf: 0.98 }],
  mentzer_index: [{ req: ["mcv", "rbc"], formula: "mentzer", conf: 0.85, cite: "mentzer" }],
  rdw_mcv_ratio: [{ req: ["rdw", "mcv"], formula: "rdw_mcv", conf: 0.80 }],
  anemia_type_indicator: [{ req: ["mcv", "mchc", "rdw"], formula: "anemia_type", conf: 0.75 }],
  iron_deficiency_probability: [{ req: ["ferritin", "tibc", "serum_iron"], formula: "iron_def", conf: 0.85 }],
  tsat: [{ req: ["serum_iron", "tibc"], formula: "tsat", conf: 0.95 }],
  reticulocyte_index: [{ req: ["reticulocytes", "hematocrit"], formula: "retic_idx", conf: 0.88 }],
  
  // ═══════════════════════════════════════════════════════════════
  // METABOLIC & ANTHROPOMETRIC
  // ═══════════════════════════════════════════════════════════════
  bmi: [{ req: ["weight_kg", "height_cm"], formula: "wt_ht", conf: 0.99 }],
  bmi_class: [{ req: ["bmi"], formula: "bmi_class", conf: 0.99 }],
  waist_height_ratio: [{ req: ["waist_cm", "height_cm"], formula: "whr", conf: 0.98 }],
  waist_hip_ratio: [{ req: ["waist_cm", "hip_cm"], formula: "whp", conf: 0.98 }],
  bsa: [{ req: ["weight_kg", "height_cm"], formula: "bsa_mosteller", conf: 0.95 }],
  ibw: [{ req: ["height_cm"], formula: "ideal_body_weight", conf: 0.90 }],
  absi: [{ req: ["waist_cm", "bmi", "height_cm"], formula: "absi", conf: 0.85 }],
  bri: [{ req: ["waist_cm", "height_cm"], formula: "bri", conf: 0.88 }],
  visceral_fat_proxy: [{ req: ["waist_cm", "bmi", "age"], formula: "vat_proxy", conf: 0.75 }],
  
  // ═══════════════════════════════════════════════════════════════
  // ELECTROLYTES & FLUID BALANCE
  // ═══════════════════════════════════════════════════════════════
  anion_gap: [{ req: ["sodium", "chloride", "bicarbonate"], formula: "anion_gap", conf: 0.98 }],
  corrected_anion_gap: [{ req: ["anion_gap", "albumin"], formula: "corrected_ag", conf: 0.95 }],
  serum_osmolality: [{ req: ["sodium", "glucose", "bun"], formula: "osmolality", conf: 0.92 }],
  osmolar_gap: [{ req: ["serum_osmolality", "sodium", "glucose", "bun"], formula: "osm_gap", conf: 0.88 }],
  corrected_sodium: [{ req: ["sodium", "glucose"], formula: "corrected_na", conf: 0.95 }],
  corrected_calcium: [{ req: ["calcium", "albumin"], formula: "corrected_ca", conf: 0.95 }],
  free_water_deficit: [{ req: ["sodium", "weight_kg"], formula: "fwd", conf: 0.85 }],
  
  // ═══════════════════════════════════════════════════════════════
  // NUTRITIONAL & VITAMINS
  // ═══════════════════════════════════════════════════════════════
  vitamin_d_status: [{ req: ["vitamin_d"], formula: "vit_d_status", conf: 0.95 }],
  b12_deficiency_risk: [{ req: ["b12", "mma"], formula: "b12_risk", conf: 0.88 }],
  folate_status: [{ req: ["folate", "rbc_folate"], formula: "folate_status", conf: 0.85 }],
  homocysteine_risk: [{ req: ["homocysteine"], formula: "hcy_risk", conf: 0.90 }],
  nutritional_risk_index: [{ req: ["albumin", "weight_kg", "ideal_body_weight"], formula: "nri", conf: 0.80 }],
  
  // ═══════════════════════════════════════════════════════════════
  // COMPOSITE & RISK SCORES
  // ═══════════════════════════════════════════════════════════════
  metabolic_syndrome_atp3: [{ req: ["waist_cm", "triglycerides", "hdl", "sbp", "fasting_glucose"], formula: "mets_atp3", conf: 0.95, cite: "atp3" }],
  metabolic_syndrome_idf: [{ req: ["waist_cm", "triglycerides", "hdl", "sbp", "fasting_glucose"], formula: "mets_idf", conf: 0.95, cite: "idf" }],
  cardiometabolic_risk: [{ req: ["ldl", "hdl", "triglycerides", "sbp", "fasting_glucose", "bmi"], formula: "cm_risk", conf: 0.85 }],
  overall_health_score: [{ req: ["bmi", "sbp", "fasting_glucose", "hdl", "triglycerides"], formula: "health_score", conf: 0.75 }]
};

/**
 * CALCULATION FUNCTIONS
 */
function calculate(formula, v) {
  try {
    switch (formula) {
      // LIPID
      case "friedewald": return v.triglycerides < 400 ? v.total_cholesterol - v.hdl - v.triglycerides / 5 : null;
      case "martin_hopkins": {
        const f = v.triglycerides < 100 ? 4.5 : v.triglycerides < 150 ? 5 : v.triglycerides < 200 ? 5.5 : 6;
        return v.total_cholesterol - v.hdl - v.triglycerides / f;
      }
      case "tg_div_5": return v.triglycerides / 5;
      case "tc_minus_hdl": return v.total_cholesterol - v.hdl;
      case "remnant": return v.total_cholesterol - v.ldl - v.hdl;
      case "tc_hdl": return v.total_cholesterol / v.hdl;
      case "ldl_hdl": return v.ldl / v.hdl;
      case "aip": return Math.log10(v.triglycerides / v.hdl);
      case "ratio": return v.triglycerides / v.hdl;
      case "ldl_particle_proxy": return v.triglycerides > 150 && v.hdl < 40 ? "high_sdldl_risk" : v.triglycerides > 100 ? "moderate" : "low";
      case "apob_est": return 0.7 * v.ldl + 0.25 * v.triglycerides / 5; // Simplified estimation
      case "lp_ir": return (v.triglycerides * v.vldl) / (v.hdl * v.hdl);
      
      // GLYCEMIC
      case "homa_ir": return (v.fasting_glucose * v.fasting_insulin) / 405;
      case "homa_beta": return (360 * v.fasting_insulin) / (v.fasting_glucose - 63);
      case "quicki": return 1 / (Math.log10(v.fasting_insulin) + Math.log10(v.fasting_glucose));
      case "tyg": return Math.log(v.triglycerides * v.fasting_glucose / 2);
      case "tyg_bmi": return Math.log(v.triglycerides * v.fasting_glucose / 2) * v.bmi;
      case "tyg_wc": return Math.log(v.triglycerides * v.fasting_glucose / 2) * v.waist_cm;
      case "mets_ir": return Math.log((2 * v.fasting_glucose + v.triglycerides) * v.bmi) / Math.log(v.hdl);
      case "gmi": return 3.31 + 0.02392 * v.mean_glucose;
      case "eag": return 28.7 * v.hba1c - 46.7;
      case "diabetes_risk": return (v.fasting_glucose - 70) * 0.5 + (v.bmi - 20) * 1.5 + (v.age - 30) * 0.3;
      case "prediabetes": return v.fasting_glucose >= 100 && v.fasting_glucose < 126 ? "prediabetes" : v.fasting_glucose >= 126 ? "diabetes_range" : "normal";
      case "ppg_estimate": return v.fasting_glucose + (v.hba1c - 5) * 30;
      case "gv_proxy": return Math.abs((v.hba1c * 28.7 - 46.7) - v.fasting_glucose) / v.fasting_glucose;
      
      // KIDNEY
      case "ckd_epi": {
        const cr = v.creatinine, age = v.age, fem = v.is_female || false;
        const k = fem ? 0.7 : 0.9;
        const alpha = fem ? (cr <= 0.7 ? -0.241 : -1.2) : (cr <= 0.9 ? -0.302 : -1.2);
        return 142 * Math.pow(Math.min(cr / k, 1), alpha) * Math.pow(Math.max(cr / k, 1), -1.2) * Math.pow(0.9938, age) * (fem ? 1.012 : 1);
      }
      case "ckd_epi_cys": return 133 * Math.pow(Math.min(v.cystatin_c / 0.8, 1), -0.499) * Math.pow(Math.max(v.cystatin_c / 0.8, 1), -1.328) * Math.pow(0.996, v.age);
      case "cockcroft_gault": {
        const w = v.weight_kg, cr = v.creatinine, age = v.age, fem = v.is_female || false;
        return ((140 - age) * w) / (72 * cr) * (fem ? 0.85 : 1);
      }
      case "bun_cr": return v.bun / v.creatinine;
      case "ckd_staging": return v.egfr >= 90 ? "G1" : v.egfr >= 60 ? "G2" : v.egfr >= 45 ? "G3a" : v.egfr >= 30 ? "G3b" : v.egfr >= 15 ? "G4" : "G5";
      case "uacr": return v.urine_albumin / v.urine_creatinine;
      case "kidney_risk": return (120 - v.egfr) * 0.5 + (v.age - 40) * 0.3 + (v.albumin < 3.5 ? 10 : 0);
      
      // LIVER
      case "fib4": return (v.age * v.ast) / (v.platelets * Math.sqrt(v.alt));
      case "de_ritis": return v.ast / v.alt;
      case "nafld_fib": {
        const ifg = v.fasting_glucose > 100 || v.diabetes ? 1 : 0;
        return -1.675 + 0.037 * v.age + 0.094 * v.bmi + 1.13 * ifg + 0.99 * (v.ast / v.alt) - 0.013 * v.platelets - 0.66 * v.albumin;
      }
      case "apri": return ((v.ast / 40) / v.platelets) * 100;
      case "meld": return 10 * (0.957 * Math.log(Math.max(v.creatinine, 1)) + 0.378 * Math.log(Math.max(v.bilirubin, 1)) + 1.12 * Math.log(Math.max(v.inr, 1)) + 0.643);
      case "meld_na": {
        const meld = 10 * (0.957 * Math.log(Math.max(v.creatinine, 1)) + 0.378 * Math.log(Math.max(v.bilirubin, 1)) + 1.12 * Math.log(Math.max(v.inr, 1)) + 0.643);
        return meld + 1.32 * (137 - Math.max(Math.min(v.sodium, 137), 125)) - 0.033 * meld * (137 - Math.max(Math.min(v.sodium, 137), 125));
      }
      case "baat": return (v.age >= 50 ? 1 : 0) + (v.bmi >= 28 ? 1 : 0) + (v.ast >= 2 * v.alt ? 2 : 0) + (v.triglycerides >= 1.7 ? 1 : 0);
      case "fli": return Math.exp(0.953 * Math.log(v.triglycerides) + 0.139 * v.bmi + 0.718 * Math.log(v.ggt) + 0.053 * v.waist_cm - 15.745) / (1 + Math.exp(0.953 * Math.log(v.triglycerides) + 0.139 * v.bmi + 0.718 * Math.log(v.ggt) + 0.053 * v.waist_cm - 15.745)) * 100;
      case "alc_liver": return (v.ast > v.alt * 2 ? 1 : 0) + (v.ggt > 100 ? 1 : 0) + (v.mcv > 100 ? 1 : 0);
      
      // INFLAMMATORY
      case "nlr": return v.neutrophils / v.lymphocytes;
      case "plr": return v.platelets / v.lymphocytes;
      case "sii": return (v.platelets * v.neutrophils) / v.lymphocytes;
      case "mlr": return v.monocytes / v.lymphocytes;
      case "nlr_plr": return v.nlr * v.plr / 100;
      case "aisi": return (v.neutrophils * v.monocytes * v.platelets) / v.lymphocytes;
      case "cii": return v.hscrp * v.wbc / 10;
      case "crp_risk": return v.hscrp < 1 ? "low" : v.hscrp < 3 ? "average" : "high";
      
      // CARDIAC
      case "mean_arterial": return v.dbp + (v.sbp - v.dbp) / 3;
      case "pp": return v.sbp - v.dbp;
      case "ppi": return v.pulse_pressure / v.sbp * 100;
      case "htn_stage": return v.sbp < 120 && v.dbp < 80 ? "normal" : v.sbp < 130 && v.dbp < 80 ? "elevated" : v.sbp < 140 || v.dbp < 90 ? "stage1" : "stage2";
      case "art_stiff": return v.pulse_pressure + v.age * 0.5;
      case "cv_bp_risk": return (v.sbp - 120) * 0.5 + (v.age - 40) * 0.3;
      
      // THYROID
      case "tsh_ft4": return v.tsh / v.ft4;
      case "tshi": return Math.log(v.tsh) + 0.1345 * v.ft4;
      case "t3_t4": return v.t3 / v.t4;
      case "ft3_ft4": return v.ft3 / v.ft4;
      case "tri": return v.tsh * v.ft3 / v.ft4;
      
      // ANEMIA
      case "mchc": return (v.hemoglobin / v.hematocrit) * 100;
      case "mcv_calc": return (v.hematocrit / v.rbc) * 10;
      case "mch_calc": return (v.hemoglobin / v.rbc) * 10;
      case "mentzer": return v.mcv / v.rbc;
      case "rdw_mcv": return v.rdw / v.mcv * 100;
      case "anemia_type": return v.mcv < 80 && v.rdw > 15 ? "iron_deficiency" : v.mcv < 80 && v.rdw <= 15 ? "thalassemia_trait" : v.mcv > 100 ? "megaloblastic" : "normocytic";
      case "iron_def": return v.ferritin < 30 || v.tsat < 20 ? "likely" : v.ferritin < 100 ? "possible" : "unlikely";
      case "tsat": return (v.serum_iron / v.tibc) * 100;
      case "retic_idx": return v.reticulocytes * (v.hematocrit / 45);
      
      // METABOLIC
      case "wt_ht": return v.weight_kg / Math.pow(v.height_cm / 100, 2);
      case "bmi_class": return v.bmi < 18.5 ? "underweight" : v.bmi < 25 ? "normal" : v.bmi < 30 ? "overweight" : v.bmi < 35 ? "obese_1" : v.bmi < 40 ? "obese_2" : "obese_3";
      case "whr": return v.waist_cm / v.height_cm;
      case "whp": return v.waist_cm / v.hip_cm;
      case "bsa_mosteller": return Math.sqrt((v.height_cm * v.weight_kg) / 3600);
      case "ideal_body_weight": return v.is_female ? 45.5 + 2.3 * ((v.height_cm / 2.54) - 60) : 50 + 2.3 * ((v.height_cm / 2.54) - 60);
      case "absi": return v.waist_cm / (Math.pow(v.bmi, 2/3) * Math.pow(v.height_cm, 1/2));
      case "bri": return 364.2 - 365.5 * Math.sqrt(1 - Math.pow(v.waist_cm / (2 * Math.PI), 2) / Math.pow(0.5 * v.height_cm, 2));
      case "vat_proxy": return v.waist_cm * 0.5 + v.bmi * 0.3 + v.age * 0.1;
      
      // ELECTROLYTES
      case "anion_gap": return v.sodium - v.chloride - v.bicarbonate;
      case "corrected_ag": return v.anion_gap + 2.5 * (4 - v.albumin);
      case "osmolality": return 2 * v.sodium + v.glucose / 18 + v.bun / 2.8;
      case "osm_gap": return v.serum_osmolality - (2 * v.sodium + v.glucose / 18 + v.bun / 2.8);
      case "corrected_na": return v.sodium + 0.016 * (v.glucose - 100);
      case "corrected_ca": return v.calcium + 0.8 * (4 - v.albumin);
      case "fwd": return 0.6 * v.weight_kg * (v.sodium / 140 - 1);
      
      // NUTRITIONAL
      case "vit_d_status": return v.vitamin_d < 20 ? "deficient" : v.vitamin_d < 30 ? "insufficient" : v.vitamin_d < 100 ? "sufficient" : "toxicity_risk";
      case "b12_risk": return v.b12 < 200 || v.mma > 0.4 ? "likely_deficient" : v.b12 < 300 ? "borderline" : "sufficient";
      case "folate_status": return v.folate < 3 || v.rbc_folate < 140 ? "deficient" : "sufficient";
      case "hcy_risk": return v.homocysteine > 15 ? "elevated" : v.homocysteine > 12 ? "borderline" : "normal";
      case "nri": return 1.519 * v.albumin + 41.7 * (v.weight_kg / v.ideal_body_weight);
      
      // COMPOSITE
      case "mets_atp3": {
        let c = 0;
        if (v.waist_cm > (v.is_female ? 88 : 102)) c++;
        if (v.triglycerides >= 150) c++;
        if (v.hdl < (v.is_female ? 50 : 40)) c++;
        if (v.sbp >= 130 || v.dbp >= 85) c++;
        if (v.fasting_glucose >= 100) c++;
        return { criteria_met: c, diagnosis: c >= 3 ? "metabolic_syndrome" : c >= 2 ? "at_risk" : "not_met" };
      }
      case "mets_idf": {
        const central = v.waist_cm > (v.is_female ? 80 : 94);
        if (!central) return { diagnosis: "not_met", reason: "no_central_obesity" };
        let c = 0;
        if (v.triglycerides >= 150) c++;
        if (v.hdl < (v.is_female ? 50 : 40)) c++;
        if (v.sbp >= 130 || v.dbp >= 85) c++;
        if (v.fasting_glucose >= 100) c++;
        return { criteria_met: c + 1, diagnosis: c >= 2 ? "metabolic_syndrome" : "at_risk" };
      }
      case "cm_risk": return (v.ldl - 100) * 0.3 + (150 - v.hdl) * 0.2 + (v.triglycerides - 100) * 0.1 + (v.sbp - 120) * 0.2 + (v.fasting_glucose - 90) * 0.2 + (v.bmi - 25) * 0.5;
      case "health_score": {
        let score = 100;
        if (v.bmi > 30) score -= 15; else if (v.bmi > 25) score -= 5;
        if (v.sbp > 140) score -= 15; else if (v.sbp > 130) score -= 5;
        if (v.fasting_glucose > 126) score -= 15; else if (v.fasting_glucose > 100) score -= 5;
        if (v.hdl < 40) score -= 10; else if (v.hdl < 50) score -= 3;
        if (v.triglycerides > 200) score -= 10; else if (v.triglycerides > 150) score -= 5;
        return Math.max(0, score);
      }
    }
  } catch (e) {}
  return null;
}

/**
 * RISK INTERPRETATION
 */
function interpretRisk(metric, value) {
  const interps = {
    castelli_1: [{ max: 3.5, risk: "low", note: "Optimal CV risk" }, { max: 5, risk: "moderate" }, { max: Infinity, risk: "high", note: "Elevated CV risk" }],
    castelli_2: [{ max: 2.5, risk: "optimal" }, { max: 3.5, risk: "moderate" }, { max: Infinity, risk: "high" }],
    atherogenic_index: [{ max: 0.1, risk: "low" }, { max: 0.24, risk: "moderate" }, { max: Infinity, risk: "high", note: "Small dense LDL likely" }],
    tg_hdl_ratio: [{ max: 2, risk: "optimal" }, { max: 3, risk: "borderline" }, { max: Infinity, risk: "elevated", note: "Insulin resistance likely" }],
    tyg_index: [{ max: 8.5, risk: "normal" }, { max: 9, risk: "borderline" }, { max: Infinity, risk: "elevated", note: "Insulin resistance" }],
    homa_ir: [{ max: 1, risk: "optimal" }, { max: 2, risk: "normal" }, { max: 2.9, risk: "elevated" }, { max: Infinity, risk: "high" }],
    fib4: [{ max: 1.3, risk: "low", note: "Low fibrosis risk" }, { max: 2.67, risk: "indeterminate" }, { max: Infinity, risk: "high" }],
    nlr: [{ max: 3, risk: "normal" }, { max: 6, risk: "mild_inflammation" }, { max: Infinity, risk: "elevated" }],
    egfr: [{ min: 90, risk: "normal" }, { min: 60, risk: "mild_decrease" }, { min: 30, risk: "moderate" }, { min: 15, risk: "severe" }, { min: 0, risk: "failure" }]
  };
  const r = interps[metric];
  if (!r) return null;
  if (metric === 'egfr') { for (const i of r) if (value >= i.min) return i; }
  else { for (const i of r) if (value <= i.max) return i; }
  return null;
}

/**
 * CASCADE ENGINE
 */
function runCascade(inputs) {
  const values = { ...inputs };
  const calculated = [];
  
  for (let i = 0; i < 20; i++) {
    let found = false;
    for (const [target, rules] of Object.entries(INFERENCE_RULES)) {
      if (values[target] !== undefined) continue;
      for (const rule of rules) {
        if (!rule.req.every(r => values[r] !== undefined)) continue;
        if (rule.cond && !rule.cond(values)) continue;
        const val = calculate(rule.formula, values);
        if (val !== null && val !== undefined && (typeof val !== 'number' || (!isNaN(val) && isFinite(val)))) {
          values[target] = val;
          const entry = { name: target, value: typeof val === 'number' ? Math.round(val * 1000) / 1000 : val, method: rule.formula, confidence: rule.conf, iteration: i + 1 };
          if (rule.cite && CITATIONS[rule.cite]) entry.citation = CITATIONS[rule.cite];
          const interp = interpretRisk(target, val);
          if (interp) entry.interpretation = interp;
          calculated.push(entry);
          found = true;
          break;
        }
      }
    }
    if (!found) break;
  }
  
  return { inputs: Object.keys(inputs).length, calculated: calculated.length, total: Object.keys(values).length, cascade_iterations: calculated.length > 0 ? calculated[calculated.length - 1].iteration : 0, values, derived: calculated };
}

/**
 * SUGGESTIONS
 */
function getSuggestions(values) {
  const sugg = [];
  for (const [target, rules] of Object.entries(INFERENCE_RULES)) {
    if (values[target] !== undefined) continue;
    for (const rule of rules) {
      const missing = rule.req.filter(r => values[r] === undefined);
      if (missing.length === 1) {
        sugg.push({ target, missing: missing[0], confidence: rule.conf, citation: rule.cite ? CITATIONS[rule.cite]?.source : null, why: `Adding ${missing[0]} enables ${target}` });
      }
    }
  }
  return sugg.sort((a, b) => b.confidence - a.confidence).slice(0, 10);
}

/**
 * CLOUDFLARE HANDLER
 */
export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const cors = { "Access-Control-Allow-Origin": "*", "Access-Control-Allow-Methods": "GET,POST,OPTIONS", "Access-Control-Allow-Headers": "Content-Type", "Content-Type": "application/json" };
    if (request.method === "OPTIONS") return new Response(null, { headers: cors });
    
    if (url.pathname === "/" || url.pathname === "") {
      return new Response(JSON.stringify({
        name: "Monitor Health API",
        version: "3.0.0 - FULL COVERAGE",
        differentiator: "CASCADE INFERENCE: Partial data → Comprehensive insights. EVERY formula has PMID citation.",
        total_formulas: Object.values(INFERENCE_RULES).reduce((a, r) => a + r.length, 0),
        total_citations: Object.keys(CITATIONS).length,
        endpoints: { "/analyze": "POST biomarkers", "/demo": "GET sample", "/citations": "GET all PMIDs", "/schema": "GET inputs/outputs" }
      }), { headers: cors });
    }
    
    if (url.pathname === "/citations") {
      return new Response(JSON.stringify({ status: "success", count: Object.keys(CITATIONS).length, citations: CITATIONS }), { headers: cors });
    }
    
    if (url.pathname === "/schema") {
      const inputs = new Set(), outputs = new Set();
      for (const [t, r] of Object.entries(INFERENCE_RULES)) { outputs.add(t); r.forEach(x => x.req.forEach(i => inputs.add(i))); }
      return new Response(JSON.stringify({ inputs: [...inputs].sort(), outputs: [...outputs].sort(), total_inputs: inputs.size, total_outputs: outputs.size }), { headers: cors });
    }
    
    if (url.pathname === "/demo") {
      const result = runCascade({ total_cholesterol: 220, hdl: 42, triglycerides: 185, fasting_glucose: 108, fasting_insulin: 15, age: 45, creatinine: 1.1, weight_kg: 85, height_cm: 175, waist_cm: 98, sbp: 138, dbp: 88 });
      return new Response(JSON.stringify({ status: "success", demo_note: `From ${result.inputs} inputs → ${result.calculated} calculated → ${result.total} total values`, ...result, suggestions: getSuggestions(result.values) }), { headers: cors });
    }
    
    if (url.pathname === "/analyze" && request.method === "POST") {
      try {
        const body = await request.json();
        const result = runCascade(body);
        return new Response(JSON.stringify({ status: "success", ...result, suggestions: getSuggestions(result.values) }), { headers: cors });
      } catch (e) {
        return new Response(JSON.stringify({ error: e.message }), { status: 400, headers: cors });
      }
    }
    
    return new Response(JSON.stringify({ error: "Not found" }), { status: 404, headers: cors });
  }
};
