/**
 * MONITOR HEALTH - UNCERTAINTY PROPAGATION v1.0
 * Input reliability → Output confidence
 */

// Input reliability classes
const RELIABILITY_CLASSES = {
  // Lab values - high reliability
  lab_certified: { class: "A", variance: 0.02, description: "Certified lab, standardized assay" },
  lab_standard: { class: "A", variance: 0.05, description: "Standard clinical lab" },
  lab_point_of_care: { class: "B", variance: 0.10, description: "Point of care testing" },
  
  // Device measurements
  device_medical: { class: "A", variance: 0.03, description: "FDA-cleared medical device" },
  device_consumer: { class: "B", variance: 0.08, description: "Consumer wearable" },
  device_research: { class: "B", variance: 0.06, description: "Research-grade device" },
  
  // Self-reported
  self_measured: { class: "C", variance: 0.15, description: "Self-measured (e.g., weight)" },
  self_estimated: { class: "D", variance: 0.25, description: "Self-estimated value" },
  self_recalled: { class: "D", variance: 0.30, description: "Recalled from memory" },
  
  // Derived/calculated
  derived_direct: { class: "B", variance: 0.08, description: "Direct formula from inputs" },
  derived_cascade: { class: "C", variance: 0.15, description: "Multi-step cascade derivation" },
  derived_proxy: { class: "D", variance: 0.25, description: "Proxy/surrogate inference" },
  
  // Default
  unknown: { class: "C", variance: 0.20, description: "Unknown source" }
};

// Default input sources (can be overridden)
const DEFAULT_INPUT_SOURCES = {
  // Lab biomarkers default to standard lab
  total_cholesterol: "lab_standard",
  hdl: "lab_standard",
  ldl: "lab_standard",
  triglycerides: "lab_standard",
  fasting_glucose: "lab_standard",
  fasting_insulin: "lab_standard",
  creatinine: "lab_standard",
  hemoglobin: "lab_standard",
  hematocrit: "lab_standard",
  wbc: "lab_standard",
  platelets: "lab_standard",
  tsh: "lab_standard",
  ft4: "lab_standard",
  sodium: "lab_standard",
  potassium: "lab_standard",
  calcium: "lab_standard",
  albumin: "lab_standard",
  bilirubin: "lab_standard",
  ast: "lab_standard",
  alt: "lab_standard",
  hscrp: "lab_standard",
  ferritin: "lab_standard",
  vitamin_d: "lab_standard",
  b12: "lab_standard",
  hba1c: "lab_standard",
  
  // Physical measurements
  weight_kg: "self_measured",
  height_cm: "self_measured",
  waist_cm: "self_measured",
  hip_cm: "self_measured",
  sbp: "device_consumer",
  dbp: "device_consumer",
  
  // Demographics (exact)
  age: "lab_certified",
  is_female: "lab_certified",
};

/**
 * Get reliability for an input
 */
function getInputReliability(inputName, source = null) {
  const sourceType = source || DEFAULT_INPUT_SOURCES[inputName] || "unknown";
  return RELIABILITY_CLASSES[sourceType] || RELIABILITY_CLASSES.unknown;
}

/**
 * Propagate uncertainty through a formula
 * Uses simplified error propagation (sum of variances for independent inputs)
 */
function propagateUncertainty(requiredInputs, inputSources = {}) {
  let totalVariance = 0;
  let minClass = "A";
  const classOrder = { "A": 1, "B": 2, "C": 3, "D": 4 };
  
  for (const input of requiredInputs) {
    const reliability = getInputReliability(input, inputSources[input]);
    totalVariance += Math.pow(reliability.variance, 2);
    
    if (classOrder[reliability.class] > classOrder[minClass]) {
      minClass = reliability.class;
    }
  }
  
  // Combined standard deviation
  const combinedVariance = Math.sqrt(totalVariance);
  
  // Additional penalty for cascade depth
  const cascadeMultiplier = requiredInputs.length > 3 ? 1.2 : 1.0;
  
  return {
    combined_variance: combinedVariance * cascadeMultiplier,
    reliability_class: minClass,
    input_count: requiredInputs.length,
    confidence_factor: Math.max(0, 1 - combinedVariance * cascadeMultiplier)
  };
}

/**
 * Calculate sensitivity - how fragile is output to input changes
 */
function calculateSensitivity(formulaType, inputValues) {
  // Formulas with division are more sensitive near zero
  const divisionFormulas = ['ratio', 'homa_ir', 'quicki', 'castelli_1', 'castelli_2', 'tg_hdl'];
  const logFormulas = ['aip', 'tyg', 'meld'];
  
  if (divisionFormulas.includes(formulaType)) {
    // Check for small denominators
    const denominators = Object.values(inputValues).filter(v => typeof v === 'number' && v > 0 && v < 10);
    if (denominators.length > 0) {
      return "fragile";
    }
  }
  
  if (logFormulas.includes(formulaType)) {
    // Log functions sensitive near 1
    const nearOne = Object.values(inputValues).filter(v => typeof v === 'number' && v > 0.5 && v < 2);
    if (nearOne.length > 0) {
      return "moderate";
    }
  }
  
  return "stable";
}

/**
 * Build structured confidence object
 */
function buildConfidenceObject(params) {
  const {
    baseConfidence,      // Original formula confidence (0-1)
    formula,             // Formula name
    requiredInputs,      // List of required input names
    providedInputs,      // What was actually provided
    inputSources = {},   // Source types for inputs
    citations,           // PMID/citation info
    constraintStatus,    // From constraint engine
    iteration = 1        // Cascade iteration depth
  } = params;
  
  // Evidence grade
  let evidenceGrade = "derived";
  if (citations && citations.pmid) {
    evidenceGrade = "peer_reviewed";
  } else if (iteration === 1) {
    evidenceGrade = "direct_calculation";
  } else if (iteration > 2) {
    evidenceGrade = "cascade_inference";
  }
  
  // Input completeness
  const provided = requiredInputs.filter(i => providedInputs.includes(i)).length;
  const inputCompleteness = provided / requiredInputs.length;
  
  // Assumption load (how many inputs were derived vs direct)
  const derivedInputs = requiredInputs.filter(i => !DEFAULT_INPUT_SOURCES[i]);
  const assumptionLoad = derivedInputs.length;
  
  // Uncertainty propagation
  const uncertainty = propagateUncertainty(requiredInputs, inputSources);
  
  // Sensitivity
  const sensitivity = calculateSensitivity(formula, providedInputs);
  
  // Cross-panel consistency
  let crossPanelConsistency = "consistent";
  if (constraintStatus) {
    if (constraintStatus.impossible_count > 0) crossPanelConsistency = "invalid";
    else if (constraintStatus.inconsistency_count > 0) crossPanelConsistency = "inconsistent";
    else if (constraintStatus.warning_count > 0) crossPanelConsistency = "flagged";
  }
  
  // Final confidence score (composite)
  let finalConfidence = baseConfidence;
  finalConfidence *= inputCompleteness;
  finalConfidence *= uncertainty.confidence_factor;
  finalConfidence *= (1 - assumptionLoad * 0.05);
  if (sensitivity === "fragile") finalConfidence *= 0.85;
  else if (sensitivity === "moderate") finalConfidence *= 0.95;
  if (crossPanelConsistency === "inconsistent") finalConfidence *= 0.7;
  else if (crossPanelConsistency === "flagged") finalConfidence *= 0.9;
  
  return {
    // Core metrics
    score: Math.round(finalConfidence * 100) / 100,
    
    // Structured components
    evidence_grade: evidenceGrade,
    input_completeness: Math.round(inputCompleteness * 100) / 100,
    assumption_load: assumptionLoad,
    sensitivity: sensitivity,
    cross_panel_consistency: crossPanelConsistency,
    
    // Reliability
    reliability_class: uncertainty.reliability_class,
    combined_variance: Math.round(uncertainty.combined_variance * 1000) / 1000,
    
    // Metadata
    cascade_depth: iteration,
    required_inputs: requiredInputs.length,
    citation_backed: !!(citations && citations.pmid)
  };
}

/**
 * Get human-readable confidence explanation
 */
function explainConfidence(confidenceObj) {
  const explanations = [];
  
  // Evidence
  const evidenceMap = {
    "peer_reviewed": "Based on peer-reviewed formula",
    "direct_calculation": "Direct calculation from inputs",
    "derived": "Derived from other calculations",
    "cascade_inference": "Multiple inference steps"
  };
  explanations.push(evidenceMap[confidenceObj.evidence_grade] || "Unknown evidence basis");
  
  // Completeness
  if (confidenceObj.input_completeness < 1) {
    explanations.push(`${Math.round(confidenceObj.input_completeness * 100)}% of required inputs provided`);
  }
  
  // Assumptions
  if (confidenceObj.assumption_load > 0) {
    explanations.push(`${confidenceObj.assumption_load} derived input(s) used`);
  }
  
  // Sensitivity
  if (confidenceObj.sensitivity === "fragile") {
    explanations.push("Result sensitive to small input changes");
  }
  
  // Consistency
  if (confidenceObj.cross_panel_consistency !== "consistent") {
    explanations.push("Some cross-panel inconsistencies detected");
  }
  
  return {
    summary: `Confidence: ${Math.round(confidenceObj.score * 100)}%`,
    reliability: `Class ${confidenceObj.reliability_class}`,
    factors: explanations
  };
}

module.exports = {
  RELIABILITY_CLASSES,
  DEFAULT_INPUT_SOURCES,
  getInputReliability,
  propagateUncertainty,
  calculateSensitivity,
  buildConfidenceObject,
  explainConfidence
};
