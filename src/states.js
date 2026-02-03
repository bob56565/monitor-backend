/**
 * MONITOR HEALTH - PHYSIOLOGICAL STATE ENGINE v1.0
 * Signal → State → Action Framework
 * 
 * This is the core intelligence layer that transforms
 * isolated metrics into holistic physiological states.
 */

// Latent physiological states with contributing signals
const PHYSIOLOGICAL_STATES = {
  
  // ═══════════════════════════════════════════════════════════════
  // METABOLIC STATES
  // ═══════════════════════════════════════════════════════════════
  
  metabolic_health: {
    name: "Metabolic Health State",
    description: "Overall metabolic regulation and energy homeostasis",
    states: ["optimal", "stable", "stressed", "dysregulated"],
    signals: {
      required: ["homa_ir", "tg_hdl_ratio"],
      supporting: ["fasting_glucose", "bmi", "tyg_index", "fasting_insulin", "hba1c"],
      optional: ["waist_cm", "metabolic_syndrome_atp3"]
    },
    logic: (v) => {
      let score = 100;
      const factors = [];
      
      if (v.homa_ir > 3) { score -= 30; factors.push("Elevated insulin resistance (HOMA-IR)"); }
      else if (v.homa_ir > 2) { score -= 15; factors.push("Borderline insulin resistance"); }
      
      if (v.tg_hdl_ratio > 4) { score -= 25; factors.push("Elevated TG/HDL ratio"); }
      else if (v.tg_hdl_ratio > 3) { score -= 12; factors.push("Borderline TG/HDL ratio"); }
      
      if (v.fasting_glucose > 126) { score -= 25; factors.push("Diabetic-range glucose"); }
      else if (v.fasting_glucose > 100) { score -= 10; factors.push("Prediabetic glucose"); }
      
      if (v.bmi > 35) { score -= 15; factors.push("Class II+ obesity"); }
      else if (v.bmi > 30) { score -= 8; factors.push("Class I obesity"); }
      
      if (v.hba1c > 6.5) { score -= 20; factors.push("Elevated HbA1c"); }
      else if (v.hba1c > 5.7) { score -= 8; factors.push("Prediabetic HbA1c"); }
      
      const state = score > 80 ? "optimal" : score > 60 ? "stable" : score > 40 ? "stressed" : "dysregulated";
      return { state, score: Math.max(0, score), factors };
    },
    lab_anchors: {
      optimal: { "HOMA-IR": "<1.5", "HbA1c": "<5.7%", "Fasting Insulin": "<8 μIU/mL" },
      stressed: { "HOMA-IR": "2-3", "HbA1c": "5.7-6.4%", "Fasting Glucose": "100-125 mg/dL" },
      dysregulated: { "HOMA-IR": ">3", "HbA1c": ">6.5%", "Fasting Glucose": ">126 mg/dL" }
    },
    actions: {
      optimal: ["Maintain current lifestyle", "Annual monitoring sufficient"],
      stable: ["Consider lifestyle optimization", "Recheck in 6 months"],
      stressed: ["Dietary intervention recommended", "Consider CGM trial", "Recheck in 3 months"],
      dysregulated: ["Medical evaluation recommended", "Comprehensive metabolic panel", "Consider specialist referral"]
    }
  },

  // ═══════════════════════════════════════════════════════════════
  // INFLAMMATORY STATES
  // ═══════════════════════════════════════════════════════════════
  
  inflammatory_status: {
    name: "Inflammatory Status",
    description: "Systemic inflammation and immune activation level",
    states: ["quiescent", "low_grade", "moderate", "elevated"],
    signals: {
      required: ["hscrp"],
      supporting: ["nlr", "ferritin", "albumin", "plr"],
      optional: ["wbc", "fibrinogen", "esr"]
    },
    logic: (v) => {
      let score = 100;
      const factors = [];
      
      if (v.hscrp > 10) { score -= 50; factors.push("Acute-phase CRP elevation"); }
      else if (v.hscrp > 3) { score -= 30; factors.push("Elevated hs-CRP (high CV risk range)"); }
      else if (v.hscrp > 1) { score -= 15; factors.push("Moderate hs-CRP"); }
      
      if (v.nlr > 6) { score -= 25; factors.push("Elevated neutrophil-lymphocyte ratio"); }
      else if (v.nlr > 3) { score -= 10; factors.push("Borderline NLR"); }
      
      if (v.ferritin > 500) { score -= 20; factors.push("Elevated ferritin (inflammation marker)"); }
      else if (v.ferritin > 300) { score -= 8; factors.push("Upper-range ferritin"); }
      
      if (v.albumin < 3.5) { score -= 15; factors.push("Low albumin (negative acute phase)"); }
      
      const state = score > 85 ? "quiescent" : score > 65 ? "low_grade" : score > 45 ? "moderate" : "elevated";
      return { state, score: Math.max(0, score), factors };
    },
    lab_anchors: {
      quiescent: { "hs-CRP": "<1 mg/L", "NLR": "<2.5" },
      low_grade: { "hs-CRP": "1-3 mg/L", "NLR": "2.5-4" },
      elevated: { "hs-CRP": ">3 mg/L", "Ferritin": "May be elevated", "ESR": "May be elevated" }
    },
    actions: {
      quiescent: ["No intervention needed", "Routine monitoring"],
      low_grade: ["Assess lifestyle factors", "Consider anti-inflammatory diet", "Check omega-3 status"],
      moderate: ["Identify inflammation source", "Comprehensive workup recommended", "Consider specialist"],
      elevated: ["Urgent evaluation for inflammation source", "Rule out infection/autoimmune", "Specialist referral"]
    }
  },

  // ═══════════════════════════════════════════════════════════════
  // CARDIOVASCULAR STATES
  // ═══════════════════════════════════════════════════════════════
  
  cardiovascular_status: {
    name: "Cardiovascular Risk State",
    description: "Overall cardiovascular health and risk profile",
    states: ["optimal", "favorable", "moderate_risk", "elevated_risk"],
    signals: {
      required: ["ldl", "hdl"],
      supporting: ["sbp", "triglycerides", "hscrp", "pulse_pressure", "non_hdl"],
      optional: ["apob_estimated", "lp_ir_score", "castelli_1"]
    },
    logic: (v) => {
      let score = 100;
      const factors = [];
      
      if (v.ldl > 190) { score -= 35; factors.push("Very high LDL"); }
      else if (v.ldl > 160) { score -= 25; factors.push("High LDL"); }
      else if (v.ldl > 130) { score -= 15; factors.push("Borderline high LDL"); }
      else if (v.ldl < 100) { score += 5; factors.push("Optimal LDL"); }
      
      if (v.hdl < 40) { score -= 25; factors.push("Low HDL"); }
      else if (v.hdl > 60) { score += 5; factors.push("Protective HDL level"); }
      
      if (v.sbp > 160) { score -= 30; factors.push("Stage 2 hypertension"); }
      else if (v.sbp > 140) { score -= 20; factors.push("Stage 1 hypertension"); }
      else if (v.sbp > 130) { score -= 10; factors.push("Elevated blood pressure"); }
      
      if (v.triglycerides > 500) { score -= 25; factors.push("Very high triglycerides"); }
      else if (v.triglycerides > 200) { score -= 15; factors.push("High triglycerides"); }
      
      if (v.hscrp > 3) { score -= 15; factors.push("Inflammatory CV risk"); }
      
      if (v.pulse_pressure > 60) { score -= 10; factors.push("Elevated pulse pressure (arterial stiffness)"); }
      
      const state = score > 80 ? "optimal" : score > 60 ? "favorable" : score > 40 ? "moderate_risk" : "elevated_risk";
      return { state, score: Math.max(0, score), factors };
    },
    lab_anchors: {
      optimal: { "LDL": "<100 mg/dL", "HDL": ">60 mg/dL", "BP": "<120/80", "hs-CRP": "<1 mg/L" },
      moderate_risk: { "LDL": "130-160 mg/dL", "TG": "150-200 mg/dL", "BP": "130-140 systolic" },
      elevated_risk: { "LDL": ">160 mg/dL", "Lp(a)": "Should be checked", "ApoB": "Should be checked" }
    },
    actions: {
      optimal: ["Maintain lifestyle", "Continue current regimen"],
      favorable: ["Lifestyle optimization", "Annual lipid panel"],
      moderate_risk: ["Statin consideration per guidelines", "BP monitoring", "Lifestyle intervention"],
      elevated_risk: ["Cardiology consultation recommended", "Advanced lipid testing", "CAC score consideration"]
    }
  },

  // ═══════════════════════════════════════════════════════════════
  // LIVER HEALTH STATES
  // ═══════════════════════════════════════════════════════════════
  
  liver_status: {
    name: "Liver Health State",
    description: "Hepatic function and stress level",
    states: ["healthy", "mild_stress", "moderate_concern", "needs_evaluation"],
    signals: {
      required: ["alt"],
      supporting: ["ast", "ggt", "fib4", "albumin", "bilirubin"],
      optional: ["platelets", "nafld_fibrosis"]
    },
    logic: (v) => {
      let score = 100;
      const factors = [];
      
      if (v.alt > 80) { score -= 35; factors.push("Significantly elevated ALT"); }
      else if (v.alt > 40) { score -= 20; factors.push("Elevated ALT"); }
      
      if (v.ast > 80) { score -= 25; factors.push("Significantly elevated AST"); }
      else if (v.ast > 40) { score -= 12; factors.push("Elevated AST"); }
      
      if (v.fib4 > 2.67) { score -= 30; factors.push("High fibrosis risk (FIB-4)"); }
      else if (v.fib4 > 1.3) { score -= 15; factors.push("Indeterminate fibrosis risk"); }
      
      if (v.ggt > 60) { score -= 15; factors.push("Elevated GGT"); }
      
      if (v.albumin < 3.5) { score -= 15; factors.push("Low albumin (liver synthetic function)"); }
      
      const state = score > 80 ? "healthy" : score > 60 ? "mild_stress" : score > 40 ? "moderate_concern" : "needs_evaluation";
      return { state, score: Math.max(0, score), factors };
    },
    lab_anchors: {
      healthy: { "ALT": "<35 U/L", "AST": "<35 U/L", "FIB-4": "<1.3" },
      mild_stress: { "ALT": "35-60 U/L", "FIB-4": "1.3-2.0" },
      needs_evaluation: { "ALT": ">80 U/L", "FIB-4": ">2.67", "Consider": "FibroScan, ultrasound" }
    },
    actions: {
      healthy: ["Routine monitoring", "Maintain liver-healthy lifestyle"],
      mild_stress: ["Reduce alcohol", "Weight optimization if overweight", "Recheck in 3 months"],
      moderate_concern: ["Hepatology referral consideration", "Liver ultrasound", "Hepatitis screening"],
      needs_evaluation: ["Hepatology referral recommended", "FibroScan", "Comprehensive liver workup"]
    }
  },

  // ═══════════════════════════════════════════════════════════════
  // KIDNEY HEALTH STATES
  // ═══════════════════════════════════════════════════════════════
  
  kidney_status: {
    name: "Kidney Function State",
    description: "Renal function and filtration capacity",
    states: ["normal", "mildly_reduced", "moderately_reduced", "significantly_reduced"],
    signals: {
      required: ["egfr"],
      supporting: ["creatinine", "bun", "albumin"],
      optional: ["cystatin_c", "uacr"]
    },
    logic: (v) => {
      let score = 100;
      const factors = [];
      
      if (v.egfr < 30) { score -= 60; factors.push("Severely reduced GFR (CKD stage 4-5)"); }
      else if (v.egfr < 45) { score -= 40; factors.push("Moderately reduced GFR (CKD stage 3b)"); }
      else if (v.egfr < 60) { score -= 25; factors.push("Mildly-moderately reduced GFR (CKD stage 3a)"); }
      else if (v.egfr < 90) { score -= 10; factors.push("Mildly reduced GFR (CKD stage 2)"); }
      
      if (v.creatinine > 1.5) { score -= 15; factors.push("Elevated creatinine"); }
      
      const state = score > 85 ? "normal" : score > 60 ? "mildly_reduced" : score > 35 ? "moderately_reduced" : "significantly_reduced";
      return { state, score: Math.max(0, score), factors };
    },
    lab_anchors: {
      normal: { "eGFR": ">90 mL/min", "Creatinine": "Normal for age/sex" },
      mildly_reduced: { "eGFR": "60-89 mL/min", "Urine albumin": "Should be checked" },
      significantly_reduced: { "eGFR": "<45 mL/min", "PTH": "Should be checked", "Vitamin D": "Should be checked" }
    },
    actions: {
      normal: ["Routine monitoring", "Maintain kidney-healthy habits"],
      mildly_reduced: ["Annual monitoring", "BP optimization", "Check urine albumin"],
      moderately_reduced: ["Nephrology referral consideration", "Medication review", "Dietary protein guidance"],
      significantly_reduced: ["Nephrology referral recommended", "CKD management protocol", "Consider renal diet"]
    }
  },

  // ═══════════════════════════════════════════════════════════════
  // THYROID STATES
  // ═══════════════════════════════════════════════════════════════
  
  thyroid_status: {
    name: "Thyroid Function State",
    description: "Thyroid hormone regulation",
    states: ["euthyroid", "subclinical_variation", "dysfunction_pattern"],
    signals: {
      required: ["tsh"],
      supporting: ["ft4", "ft3"],
      optional: ["t3", "t4", "tpo_antibodies"]
    },
    logic: (v) => {
      let score = 100;
      const factors = [];
      
      if (v.tsh > 10) { score -= 50; factors.push("Significantly elevated TSH (overt hypothyroid range)"); }
      else if (v.tsh > 4.5) { score -= 25; factors.push("Elevated TSH (subclinical hypothyroid range)"); }
      else if (v.tsh < 0.1) { score -= 50; factors.push("Suppressed TSH (hyperthyroid range)"); }
      else if (v.tsh < 0.4) { score -= 25; factors.push("Low TSH (subclinical hyperthyroid range)"); }
      
      if (v.ft4 && (v.ft4 < 0.8 || v.ft4 > 1.8)) {
        score -= 20;
        factors.push(v.ft4 < 0.8 ? "Low free T4" : "Elevated free T4");
      }
      
      const state = score > 80 ? "euthyroid" : score > 50 ? "subclinical_variation" : "dysfunction_pattern";
      return { state, score: Math.max(0, score), factors };
    },
    lab_anchors: {
      euthyroid: { "TSH": "0.4-4.5 mIU/L", "Free T4": "0.8-1.8 ng/dL" },
      subclinical_variation: { "TSH": "Mildly abnormal", "Free T4": "Usually normal" },
      dysfunction_pattern: { "TSH": "Significantly abnormal", "Free T4": "May be abnormal", "Antibodies": "Should check TPO" }
    },
    actions: {
      euthyroid: ["No intervention needed", "Routine monitoring per age"],
      subclinical_variation: ["Repeat in 6-8 weeks", "Check TPO antibodies", "Assess symptoms"],
      dysfunction_pattern: ["Endocrinology referral", "Full thyroid panel", "Antibody testing"]
    }
  }
};

/**
 * Evaluate all applicable physiological states
 */
function evaluateStates(values) {
  const results = {};
  
  for (const [stateId, stateDef] of Object.entries(PHYSIOLOGICAL_STATES)) {
    // Check if required signals are present
    const hasRequired = stateDef.signals.required.every(s => values[s] !== undefined);
    if (!hasRequired) {
      results[stateId] = {
        name: stateDef.name,
        evaluated: false,
        missing: stateDef.signals.required.filter(s => values[s] === undefined)
      };
      continue;
    }
    
    // Count supporting signals
    const supportingPresent = stateDef.signals.supporting.filter(s => values[s] !== undefined).length;
    const supportingTotal = stateDef.signals.supporting.length;
    
    // Run logic
    const evaluation = stateDef.logic(values);
    
    results[stateId] = {
      name: stateDef.name,
      description: stateDef.description,
      evaluated: true,
      state: evaluation.state,
      score: evaluation.score,
      factors: evaluation.factors,
      signal_coverage: {
        required: "complete",
        supporting: `${supportingPresent}/${supportingTotal}`
      },
      lab_anchors: stateDef.lab_anchors[evaluation.state] || {},
      recommended_actions: stateDef.actions[evaluation.state] || [],
      confidence: calculateStateConfidence(evaluation, supportingPresent, supportingTotal)
    };
  }
  
  return results;
}

/**
 * Calculate confidence in state determination
 */
function calculateStateConfidence(evaluation, supportingPresent, supportingTotal) {
  let confidence = 0.7; // Base confidence with required signals
  
  // Boost for supporting signals
  const supportRatio = supportingPresent / Math.max(supportingTotal, 1);
  confidence += supportRatio * 0.2;
  
  // Boost for clear determination (high or low score)
  if (evaluation.score > 85 || evaluation.score < 25) {
    confidence += 0.08;
  }
  
  // Penalty for borderline scores
  if (evaluation.score > 45 && evaluation.score < 55) {
    confidence -= 0.1;
  }
  
  return Math.min(0.95, Math.max(0.5, Math.round(confidence * 100) / 100));
}

/**
 * Generate Signal → State → Action summary
 */
function generateStateSummary(states) {
  const evaluated = Object.entries(states).filter(([_, s]) => s.evaluated);
  const concerning = evaluated.filter(([_, s]) => s.score < 50);
  const attention = evaluated.filter(([_, s]) => s.score >= 50 && s.score < 70);
  
  return {
    total_states_evaluated: evaluated.length,
    states_of_concern: concerning.map(([id, s]) => ({
      state_id: id,
      name: s.name,
      current_state: s.state,
      score: s.score,
      top_factor: s.factors[0] || null,
      primary_action: s.recommended_actions[0] || null
    })),
    states_needing_attention: attention.map(([id, s]) => ({
      state_id: id,
      name: s.name,
      current_state: s.state
    })),
    overall_assessment: concerning.length === 0 ? 
      (attention.length === 0 ? "All evaluated systems appear stable" : "Some areas warrant attention") :
      `${concerning.length} area(s) of concern identified`
  };
}

module.exports = {
  PHYSIOLOGICAL_STATES,
  evaluateStates,
  calculateStateConfidence,
  generateStateSummary
};
