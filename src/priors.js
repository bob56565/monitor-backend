/**
 * MONITOR HEALTH - POPULATION PRIORS v1.0
 * Age/sex stratified reference ranges and Bayesian adjustments
 */

// Population reference ranges stratified by age and sex
const POPULATION_PRIORS = {
  // LIPID PANEL
  total_cholesterol: {
    general: { mean: 200, sd: 40, optimal: [150, 200], borderline: [200, 240], high: [240, 999] },
    by_age: {
      "20-29": { mean: 180, sd: 35 },
      "30-39": { mean: 195, sd: 38 },
      "40-49": { mean: 210, sd: 40 },
      "50-59": { mean: 220, sd: 42 },
      "60+": { mean: 215, sd: 45 }
    }
  },
  hdl: {
    male: { mean: 45, sd: 12, optimal: [60, 999], normal: [40, 60], low: [0, 40] },
    female: { mean: 55, sd: 14, optimal: [60, 999], normal: [50, 60], low: [0, 50] }
  },
  ldl: {
    general: { mean: 120, sd: 35, optimal: [0, 100], near_optimal: [100, 130], borderline: [130, 160], high: [160, 190], very_high: [190, 999] }
  },
  triglycerides: {
    general: { mean: 130, sd: 70, optimal: [0, 100], normal: [100, 150], borderline: [150, 200], high: [200, 500], very_high: [500, 9999] }
  },

  // GLYCEMIC
  fasting_glucose: {
    general: { mean: 95, sd: 15, normal: [70, 100], prediabetes: [100, 126], diabetes: [126, 999] }
  },
  fasting_insulin: {
    general: { mean: 8, sd: 5, optimal: [2, 6], normal: [6, 12], elevated: [12, 25], high: [25, 999] }
  },
  hba1c: {
    general: { mean: 5.4, sd: 0.5, normal: [4, 5.7], prediabetes: [5.7, 6.5], diabetes: [6.5, 99] }
  },
  homa_ir: {
    general: { mean: 1.5, sd: 1.2, optimal: [0, 1], normal: [1, 2], elevated: [2, 3], high: [3, 999] }
  },

  // KIDNEY
  creatinine: {
    male: { mean: 1.0, sd: 0.2, normal: [0.7, 1.3], elevated: [1.3, 2], high: [2, 999] },
    female: { mean: 0.8, sd: 0.15, normal: [0.5, 1.1], elevated: [1.1, 1.8], high: [1.8, 999] }
  },
  egfr: {
    by_age: {
      "20-29": { mean: 115, sd: 15 },
      "30-39": { mean: 107, sd: 15 },
      "40-49": { mean: 99, sd: 15 },
      "50-59": { mean: 93, sd: 15 },
      "60-69": { mean: 85, sd: 15 },
      "70+": { mean: 75, sd: 18 }
    },
    stages: { G1: [90, 999], G2: [60, 90], G3a: [45, 60], G3b: [30, 45], G4: [15, 30], G5: [0, 15] }
  },

  // LIVER
  alt: {
    male: { mean: 30, sd: 15, normal: [7, 40], mild: [40, 80], moderate: [80, 200], severe: [200, 9999] },
    female: { mean: 22, sd: 12, normal: [7, 33], mild: [33, 66], moderate: [66, 150], severe: [150, 9999] }
  },
  ast: {
    male: { mean: 28, sd: 12, normal: [10, 40], mild: [40, 80], moderate: [80, 200], severe: [200, 9999] },
    female: { mean: 24, sd: 10, normal: [10, 35], mild: [35, 70], moderate: [70, 150], severe: [150, 9999] }
  },

  // INFLAMMATORY
  hscrp: {
    general: { mean: 1.5, sd: 2, low_risk: [0, 1], moderate_risk: [1, 3], high_risk: [3, 10], acute: [10, 999] }
  },
  ferritin: {
    male: { mean: 150, sd: 100, low: [0, 30], normal: [30, 300], elevated: [300, 500], high: [500, 9999] },
    female: { mean: 70, sd: 50, low: [0, 15], normal: [15, 150], elevated: [150, 300], high: [300, 9999] }
  },

  // THYROID
  tsh: {
    general: { mean: 2.0, sd: 1.2, low: [0, 0.4], normal: [0.4, 4.5], subclinical_hypo: [4.5, 10], overt_hypo: [10, 999] }
  },

  // VITALS
  sbp: {
    by_age: {
      "20-29": { mean: 115, sd: 10 },
      "30-39": { mean: 118, sd: 11 },
      "40-49": { mean: 122, sd: 12 },
      "50-59": { mean: 128, sd: 14 },
      "60-69": { mean: 133, sd: 16 },
      "70+": { mean: 138, sd: 18 }
    },
    categories: { optimal: [0, 120], normal: [120, 130], stage1: [130, 140], stage2: [140, 180], crisis: [180, 999] }
  },

  // BODY COMPOSITION
  bmi: {
    general: { mean: 26, sd: 5, underweight: [0, 18.5], normal: [18.5, 25], overweight: [25, 30], obese1: [30, 35], obese2: [35, 40], obese3: [40, 999] }
  }
};

/**
 * Get age bracket
 */
function getAgeBracket(age) {
  if (age < 30) return "20-29";
  if (age < 40) return "30-39";
  if (age < 50) return "40-49";
  if (age < 60) return "50-59";
  if (age < 70) return "60-69";
  return "70+";
}

/**
 * Get population prior for a biomarker
 */
function getPrior(biomarker, age, isFemale) {
  const prior = POPULATION_PRIORS[biomarker];
  if (!prior) return null;

  let result = { ...prior.general };

  // Age-specific adjustments
  if (prior.by_age && age) {
    const bracket = getAgeBracket(age);
    if (prior.by_age[bracket]) {
      result = { ...result, ...prior.by_age[bracket] };
    }
  }

  // Sex-specific adjustments
  if (isFemale !== undefined) {
    const sexKey = isFemale ? 'female' : 'male';
    if (prior[sexKey]) {
      result = { ...result, ...prior[sexKey] };
    }
  }

  return result;
}

/**
 * Calculate z-score (how many SDs from population mean)
 */
function calculateZScore(value, prior) {
  if (!prior || !prior.mean || !prior.sd) return null;
  return (value - prior.mean) / prior.sd;
}

/**
 * Get percentile from z-score (approximate)
 */
function zToPercentile(z) {
  // Approximation using error function
  const t = 1 / (1 + 0.2316419 * Math.abs(z));
  const d = 0.3989423 * Math.exp(-z * z / 2);
  const p = d * t * (0.3193815 + t * (-0.3565638 + t * (1.781478 + t * (-1.821256 + t * 1.330274))));
  return z > 0 ? (1 - p) * 100 : p * 100;
}

/**
 * Classify value against reference ranges
 */
function classifyValue(value, prior) {
  if (!prior) return { category: "unknown", percentile: null };

  const categories = ['optimal', 'normal', 'low_risk', 'near_optimal', 'borderline', 'moderate_risk', 'elevated', 'high_risk', 'high', 'very_high', 'severe', 'acute'];
  
  for (const cat of categories) {
    if (prior[cat]) {
      const [min, max] = prior[cat];
      if (value >= min && value < max) {
        return { category: cat, range: prior[cat] };
      }
    }
  }

  // Also check special categories
  const specialCats = Object.keys(prior).filter(k => Array.isArray(prior[k]));
  for (const cat of specialCats) {
    const [min, max] = prior[cat];
    if (value >= min && value < max) {
      return { category: cat, range: prior[cat] };
    }
  }

  return { category: "out_of_range" };
}

/**
 * Apply Bayesian-like adjustment to confidence based on prior plausibility
 */
function adjustConfidenceWithPrior(baseConfidence, value, prior) {
  if (!prior || !prior.mean || !prior.sd) return baseConfidence;

  const z = calculateZScore(value, prior);
  const absZ = Math.abs(z);

  // Penalize extreme values (unlikely without special circumstances)
  let adjustment = 1.0;
  if (absZ > 3) adjustment = 0.7;      // Very unusual
  else if (absZ > 2.5) adjustment = 0.8;
  else if (absZ > 2) adjustment = 0.9;
  else if (absZ < 1) adjustment = 1.05; // Boost for typical values

  return Math.min(1, baseConfidence * adjustment);
}

/**
 * Generate prior-based insights
 */
function generatePriorInsights(biomarker, value, age, isFemale) {
  const prior = getPrior(biomarker, age, isFemale);
  if (!prior) return null;

  const z = calculateZScore(value, prior);
  const percentile = z !== null ? zToPercentile(z) : null;
  const classification = classifyValue(value, prior);

  let populationContext = "";
  if (percentile !== null) {
    if (percentile < 5) populationContext = "Lower than ~95% of similar individuals";
    else if (percentile < 25) populationContext = "Lower than typical";
    else if (percentile < 75) populationContext = "Within typical range";
    else if (percentile < 95) populationContext = "Higher than typical";
    else populationContext = "Higher than ~95% of similar individuals";
  }

  return {
    biomarker,
    value,
    population_mean: prior.mean,
    population_sd: prior.sd,
    z_score: z ? Math.round(z * 100) / 100 : null,
    percentile: percentile ? Math.round(percentile) : null,
    classification: classification.category,
    population_context: populationContext,
    reference_range: classification.range || null
  };
}

module.exports = {
  POPULATION_PRIORS,
  getPrior,
  calculateZScore,
  zToPercentile,
  classifyValue,
  adjustConfidenceWithPrior,
  generatePriorInsights,
  getAgeBracket
};
