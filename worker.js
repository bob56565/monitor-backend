// Monitor Health API - Cloudflare Worker
// Cascade Inference Engine

const INFERENCE_RULES = {
  ldl: [{ req: ["total_cholesterol", "hdl", "triglycerides"], formula: "friedewald", conf: 0.90 }],
  vldl: [{ req: ["triglycerides"], formula: "tg_div_5", conf: 0.85 }],
  non_hdl: [{ req: ["total_cholesterol", "hdl"], formula: "tc_minus_hdl", conf: 0.95 }],
  egfr: [{ req: ["creatinine", "age"], formula: "ckd_epi", conf: 0.85 }],
  bmi: [{ req: ["weight_kg", "height_cm"], formula: "wt_ht", conf: 0.99 }],
  homa_ir: [{ req: ["fasting_glucose", "fasting_insulin"], formula: "homa_ir", conf: 0.90 }],
  tg_hdl_ratio: [{ req: ["triglycerides", "hdl"], formula: "ratio", conf: 0.95 }],
  tyg_index: [{ req: ["fasting_glucose", "triglycerides"], formula: "tyg", conf: 0.80 }],
  fib4: [{ req: ["age", "ast", "alt", "platelets"], formula: "fib4", conf: 0.85 }],
  remnant_cholesterol: [{ req: ["total_cholesterol", "ldl", "hdl"], formula: "remnant", conf: 0.95 }],
  castelli_1: [{ req: ["total_cholesterol", "hdl"], formula: "tc_hdl", conf: 0.90 }],
  castelli_2: [{ req: ["ldl", "hdl"], formula: "ldl_hdl", conf: 0.90 }],
  atherogenic_index: [{ req: ["triglycerides", "hdl"], formula: "aip", conf: 0.85 }],
  hba1c_estimated: [{ req: ["mean_glucose"], formula: "gmi", conf: 0.85 }],
  mean_glucose_estimated: [{ req: ["hba1c"], formula: "eag", conf: 0.88 }],
};

function calculate(formula, v) {
  try {
    switch (formula) {
      case "friedewald": return v.triglycerides < 400 ? v.total_cholesterol - v.hdl - v.triglycerides / 5 : null;
      case "tg_div_5": return v.triglycerides / 5;
      case "tc_minus_hdl": return v.total_cholesterol - v.hdl;
      case "ckd_epi": {
        const cr = v.creatinine, age = v.age, fem = v.is_female || false;
        const [k, a] = fem ? [0.7, cr <= 0.7 ? -0.241 : -1.2] : [0.9, cr <= 0.9 ? -0.302 : -1.2];
        return 142 * Math.pow(cr / k, a) * Math.pow(0.9938, age) * (fem ? 1.012 : 1.0);
      }
      case "wt_ht": return v.weight_kg / Math.pow(v.height_cm / 100, 2);
      case "homa_ir": return (v.fasting_glucose * v.fasting_insulin) / 405;
      case "ratio": return v.triglycerides / v.hdl;
      case "tyg": return Math.log(v.triglycerides * v.fasting_glucose / 2);
      case "fib4": return (v.age * v.ast) / (v.platelets * Math.sqrt(v.alt));
      case "remnant": return v.total_cholesterol - v.ldl - v.hdl;
      case "tc_hdl": return v.total_cholesterol / v.hdl;
      case "ldl_hdl": return v.ldl / v.hdl;
      case "aip": return Math.log10((v.triglycerides / 88.57) / (v.hdl / 38.67));
      case "gmi": return 3.31 + 0.02392 * v.mean_glucose;
      case "eag": return 28.7 * v.hba1c - 46.7;
    }
  } catch (e) {}
  return null;
}

function runCascade(inputs) {
  const values = { ...inputs };
  const calculated = [];
  
  for (let i = 0; i < 10; i++) {
    let found = false;
    for (const [target, rules] of Object.entries(INFERENCE_RULES)) {
      if (values[target] !== undefined) continue;
      for (const { req, formula, conf } of rules) {
        if (req.every(r => values[r] !== undefined)) {
          const val = calculate(formula, values);
          if (val !== null) {
            values[target] = val;
            calculated.push({ name: target, value: Math.round(val * 100) / 100, method: formula, confidence: conf });
            found = true;
            break;
          }
        }
      }
    }
    if (!found) break;
  }
  
  return { inputs: Object.keys(inputs).length, calculated: calculated.length, total: Object.keys(values).length, values, derived: calculated };
}

function getSuggestions(values) {
  const sugg = [];
  for (const [target, rules] of Object.entries(INFERENCE_RULES)) {
    if (values[target] !== undefined) continue;
    for (const { req, formula, conf } of rules) {
      const missing = req.filter(r => values[r] === undefined);
      if (missing.length === 1) {
        sugg.push({ target, missing: missing[0], confidence: conf });
      }
    }
  }
  return sugg.sort((a, b) => b.confidence - a.confidence).slice(0, 5);
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const cors = { "Access-Control-Allow-Origin": "*", "Access-Control-Allow-Methods": "GET,POST,OPTIONS", "Access-Control-Allow-Headers": "Content-Type", "Content-Type": "application/json" };
    
    if (request.method === "OPTIONS") return new Response(null, { headers: cors });
    
    if (url.pathname === "/" || url.pathname === "") {
      return new Response(JSON.stringify({
        name: "Monitor Health API",
        version: "1.0.0",
        differentiator: "CASCADE INFERENCE - We derive insights from whatever data you provide",
        endpoints: { "/analyze": "POST biomarkers", "/demo": "GET sample analysis" }
      }), { headers: cors });
    }
    
    if (url.pathname === "/demo") {
      const result = runCascade({ total_cholesterol: 220, hdl: 42, triglycerides: 185, fasting_glucose: 108, age: 45 });
      return new Response(JSON.stringify({ status: "success", ...result, suggestions: getSuggestions(result.values) }), { headers: cors });
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
