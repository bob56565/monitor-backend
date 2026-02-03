/**
 * MONITOR HEALTH - CONSTRAINT ENGINE v1.0
 * Cross-panel physiological consistency validation
 */

// Physiological bounds - impossible values
const PHYSIOLOGICAL_BOUNDS = {
  // Vital ranges (hard bounds)
  age: { min: 0, max: 120 },
  bmi: { min: 10, max: 80 },
  weight_kg: { min: 20, max: 500 },
  height_cm: { min: 50, max: 250 },
  
  // Lab ranges (extreme bounds, not reference ranges)
  total_cholesterol: { min: 50, max: 500 },
  hdl: { min: 5, max: 150 },
  ldl: { min: 10, max: 400 },
  triglycerides: { min: 20, max: 5000 },
  fasting_glucose: { min: 20, max: 600 },
  fasting_insulin: { min: 0.5, max: 300 },
  creatinine: { min: 0.1, max: 20 },
  egfr: { min: 0, max: 150 },
  hemoglobin: { min: 3, max: 22 },
  hematocrit: { min: 10, max: 70 },
  wbc: { min: 0.5, max: 100 },
  platelets: { min: 10, max: 1500 },
  tsh: { min: 0.01, max: 100 },
  ft4: { min: 0.1, max: 10 },
  sodium: { min: 100, max: 180 },
  potassium: { min: 1.5, max: 9 },
  calcium: { min: 4, max: 16 },
  albumin: { min: 1, max: 6 },
  bilirubin: { min: 0.1, max: 30 },
  ast: { min: 5, max: 2000 },
  alt: { min: 5, max: 2000 },
  hscrp: { min: 0, max: 50 },
  ferritin: { min: 1, max: 5000 },
  vitamin_d: { min: 4, max: 200 },
  b12: { min: 50, max: 2000 },
  hba1c: { min: 3, max: 18 },
};

// Directional relationship rules
const DIRECTIONAL_RULES = [
  {
    id: "lipid_triad",
    desc: "High TG + Low HDL typically correlates with high LDL/VLDL",
    check: (v) => {
      if (v.triglycerides > 200 && v.hdl < 40 && v.ldl < 70) {
        return { flag: "unexpected", note: "Low LDL unusual with high TG/low HDL pattern" };
      }
      return null;
    }
  },
  {
    id: "insulin_resistance_consistency",
    desc: "HOMA-IR and TyG should trend together",
    check: (v) => {
      if (v.homa_ir > 4 && v.tyg_index < 8.2) {
        return { flag: "inconsistent", note: "HOMA-IR elevated but TyG normal - verify inputs" };
      }
      if (v.homa_ir < 1.5 && v.tyg_index > 9.5) {
        return { flag: "inconsistent", note: "TyG elevated but HOMA-IR optimal - verify inputs" };
      }
      return null;
    }
  },
  {
    id: "inflammatory_consistency",
    desc: "Inflammatory markers should correlate",
    check: (v) => {
      if (v.hscrp > 5 && v.nlr < 2 && v.plr < 100) {
        return { flag: "review", note: "CRP elevated but cell ratios normal - check timing" };
      }
      return null;
    }
  },
  {
    id: "kidney_egfr_creatinine",
    desc: "eGFR and creatinine inversely related",
    check: (v) => {
      if (v.egfr > 90 && v.creatinine > 1.5) {
        return { flag: "calculation_error", note: "High eGFR impossible with elevated creatinine" };
      }
      return null;
    }
  },
  {
    id: "anemia_consistency",
    desc: "Hemoglobin and hematocrit should correlate",
    check: (v) => {
      if (v.hemoglobin && v.hematocrit) {
        const expected_hct = v.hemoglobin * 3;
        if (Math.abs(v.hematocrit - expected_hct) > 5) {
          return { flag: "review", note: "Hgb/Hct ratio unusual - verify values" };
        }
      }
      return null;
    }
  },
  {
    id: "thyroid_pattern",
    desc: "TSH and FT4 inversely related (usually)",
    check: (v) => {
      if (v.tsh > 10 && v.ft4 > 1.8) {
        return { flag: "unusual", note: "Both TSH and FT4 elevated - rare pattern" };
      }
      if (v.tsh < 0.1 && v.ft4 < 0.8) {
        return { flag: "unusual", note: "Both TSH and FT4 low - central hypothyroid?" };
      }
      return null;
    }
  },
  {
    id: "liver_pattern",
    desc: "Liver enzymes pattern validation",
    check: (v) => {
      if (v.ast > 10 * v.alt && v.ast > 200) {
        return { flag: "alert", note: "AST >> ALT pattern suggests alcohol or ischemic injury" };
      }
      return null;
    }
  },
  {
    id: "diabetes_glucose_hba1c",
    desc: "Fasting glucose and HbA1c should correlate",
    check: (v) => {
      if (v.hba1c > 9 && v.fasting_glucose < 100) {
        return { flag: "inconsistent", note: "High HbA1c but normal fasting glucose - verify" };
      }
      if (v.hba1c < 5.5 && v.fasting_glucose > 140) {
        return { flag: "inconsistent", note: "Normal HbA1c but elevated glucose - acute?" };
      }
      return null;
    }
  }
];

// Mutual exclusions - can't have both
const MUTUAL_EXCLUSIONS = [
  {
    id: "thyroid_state",
    states: ["hyperthyroid_pattern", "hypothyroid_pattern"],
    check: (v) => {
      const hyper = v.tsh < 0.4 && v.ft4 > 1.5;
      const hypo = v.tsh > 4.5 && v.ft4 < 0.8;
      if (hyper && hypo) return { flag: "impossible", note: "Contradictory thyroid patterns" };
      return null;
    }
  },
  {
    id: "kidney_function",
    check: (v) => {
      if (v.egfr > 100 && v.ckd_stage && v.ckd_stage >= 3) {
        return { flag: "impossible", note: "High eGFR incompatible with CKD stage 3+" };
      }
      return null;
    }
  }
];

// Formula validity conditions
const FORMULA_VALIDITY = {
  friedewald: {
    condition: (v) => v.triglycerides < 400,
    invalidMessage: "Friedewald LDL invalid when TG ≥ 400"
  },
  homa_ir: {
    condition: (v) => v.fasting_glucose > 0 && v.fasting_insulin > 0,
    invalidMessage: "HOMA-IR requires positive glucose and insulin"
  },
  ckd_epi: {
    condition: (v) => v.age >= 18,
    invalidMessage: "CKD-EPI designed for adults ≥ 18"
  },
  framingham: {
    condition: (v) => v.age >= 30 && v.age <= 74,
    invalidMessage: "Framingham validated for ages 30-74"
  },
  meld: {
    condition: (v) => v.creatinine > 0 && v.bilirubin > 0 && v.inr > 0,
    invalidMessage: "MELD requires creatinine, bilirubin, and INR"
  }
};

/**
 * Validate input bounds
 */
function validateInputBounds(inputs) {
  const violations = [];
  
  for (const [key, value] of Object.entries(inputs)) {
    const bounds = PHYSIOLOGICAL_BOUNDS[key];
    if (bounds && typeof value === 'number') {
      if (value < bounds.min) {
        violations.push({
          field: key,
          value: value,
          issue: "below_minimum",
          bound: bounds.min,
          severity: "error"
        });
      } else if (value > bounds.max) {
        violations.push({
          field: key,
          value: value,
          issue: "above_maximum", 
          bound: bounds.max,
          severity: "error"
        });
      }
    }
  }
  
  return violations;
}

/**
 * Check directional consistency
 */
function checkDirectionalConsistency(values) {
  const flags = [];
  
  for (const rule of DIRECTIONAL_RULES) {
    const result = rule.check(values);
    if (result) {
      flags.push({
        rule_id: rule.id,
        description: rule.desc,
        ...result
      });
    }
  }
  
  return flags;
}

/**
 * Check mutual exclusions
 */
function checkMutualExclusions(values) {
  const flags = [];
  
  for (const rule of MUTUAL_EXCLUSIONS) {
    const result = rule.check(values);
    if (result) {
      flags.push({
        rule_id: rule.id,
        ...result
      });
    }
  }
  
  return flags;
}

/**
 * Check formula validity
 */
function checkFormulaValidity(formula, values) {
  const validity = FORMULA_VALIDITY[formula];
  if (!validity) return { valid: true };
  
  if (!validity.condition(values)) {
    return {
      valid: false,
      formula: formula,
      message: validity.invalidMessage
    };
  }
  
  return { valid: true };
}

/**
 * Run full constraint validation
 */
function runConstraintValidation(inputs, calculated) {
  const allValues = { ...inputs, ...calculated };
  
  return {
    input_violations: validateInputBounds(inputs),
    directional_flags: checkDirectionalConsistency(allValues),
    exclusion_flags: checkMutualExclusions(allValues),
    timestamp: new Date().toISOString()
  };
}

/**
 * Get constraint summary
 */
function getConstraintSummary(validation) {
  const errors = validation.input_violations.filter(v => v.severity === 'error').length;
  const warnings = validation.directional_flags.filter(f => f.flag === 'review' || f.flag === 'unusual').length;
  const inconsistencies = validation.directional_flags.filter(f => f.flag === 'inconsistent').length;
  const impossibles = validation.exclusion_flags.filter(f => f.flag === 'impossible').length;
  
  let status = 'valid';
  if (impossibles > 0 || errors > 0) status = 'invalid';
  else if (inconsistencies > 0) status = 'inconsistent';
  else if (warnings > 0) status = 'review_recommended';
  
  return {
    status,
    error_count: errors,
    warning_count: warnings,
    inconsistency_count: inconsistencies,
    impossible_count: impossibles
  };
}

module.exports = {
  PHYSIOLOGICAL_BOUNDS,
  DIRECTIONAL_RULES,
  MUTUAL_EXCLUSIONS,
  FORMULA_VALIDITY,
  validateInputBounds,
  checkDirectionalConsistency,
  checkMutualExclusions,
  checkFormulaValidity,
  runConstraintValidation,
  getConstraintSummary
};
