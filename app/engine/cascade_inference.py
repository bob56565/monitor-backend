"""
CASCADE INFERENCE ENGINE - CORE DIFFERENTIATOR
If user missing data, we FIGURE IT OUT. Outputs cascade into MORE outputs.
"""
import math
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

class DataSource(str, Enum):
    USER_INPUT = "user_input"
    CALCULATED = "calculated"
    ESTIMATED = "estimated"

@dataclass
class InferredValue:
    name: str
    value: float
    unit: str
    source: DataSource
    confidence: float
    method: str
    inputs_used: List[str] = field(default_factory=list)

INFERENCE_RULES = {
    "ldl": [(["total_cholesterol", "hdl", "triglycerides"], "friedewald", 0.90)],
    "vldl": [(["triglycerides"], "tg_div_5", 0.85)],
    "non_hdl": [(["total_cholesterol", "hdl"], "tc_minus_hdl", 0.95)],
    "hba1c_estimated": [(["mean_glucose"], "gmi", 0.85), (["fasting_glucose"], "fg_proxy", 0.60)],
    "mean_glucose_estimated": [(["hba1c"], "eag", 0.88)],
    "egfr": [(["creatinine", "age", "is_female"], "ckd_epi", 0.95), (["creatinine"], "ckd_epi_avg", 0.70)],
    "bmi": [(["weight_kg", "height_cm"], "wt_ht", 0.99)],
    "insulin_resistance_score": [(["fasting_glucose", "fasting_insulin"], "homa_ir", 0.90), (["triglycerides", "hdl"], "tg_hdl", 0.75), (["fasting_glucose", "triglycerides"], "tyg", 0.80)],
    "liver_fibrosis_score": [(["age", "ast", "alt", "platelets"], "fib4", 0.85)],
    "remnant_cholesterol": [(["total_cholesterol", "ldl", "hdl"], "direct", 0.95), (["triglycerides"], "tg_approx", 0.70)],
    "apob_estimated": [(["ldl"], "ldl_regression", 0.75)],
    "castelli_1": [(["total_cholesterol", "hdl"], "tc_hdl", 0.90)],
    "castelli_2": [(["ldl", "hdl"], "ldl_hdl", 0.90)],
    "tg_hdl_ratio": [(["triglycerides", "hdl"], "ratio", 0.95)],
    "atherogenic_index": [(["triglycerides", "hdl"], "aip", 0.85)],
}

UNITS = {"ldl":"mg/dL","hdl":"mg/dL","vldl":"mg/dL","non_hdl":"mg/dL","total_cholesterol":"mg/dL","triglycerides":"mg/dL","fasting_glucose":"mg/dL","fasting_insulin":"µIU/mL","hba1c":"%","hba1c_estimated":"%","mean_glucose":"mg/dL","mean_glucose_estimated":"mg/dL","creatinine":"mg/dL","egfr":"mL/min/1.73m²","bmi":"kg/m²","ast":"U/L","alt":"U/L","platelets":"10⁹/L","insulin_resistance_score":"index","liver_fibrosis_score":"index","remnant_cholesterol":"mg/dL","apob_estimated":"mg/dL","castelli_1":"ratio","castelli_2":"ratio","tg_hdl_ratio":"ratio","atherogenic_index":"index"}

class CascadeInferenceEngine:
    def __init__(self):
        self.values: Dict[str, InferredValue] = {}
        self.chains = []
    
    def load_inputs(self, inputs: Dict[str, float]):
        for k, v in inputs.items():
            self.values[k] = InferredValue(k, v, UNITS.get(k,""), DataSource.USER_INPUT, 1.0, "user")
    
    def run_cascade(self, max_iter=10):
        for _ in range(max_iter):
            found = False
            for target, rules in INFERENCE_RULES.items():
                if target in self.values: continue
                for req, formula, conf in rules:
                    if all(r in self.values for r in req):
                        val = self._calc(formula, {r: self.values[r].value for r in req})
                        if val is not None:
                            prop_conf = conf * min(self.values[r].confidence for r in req)
                            self.values[target] = InferredValue(target, val, UNITS.get(target,""), DataSource.CALCULATED if conf>=0.8 else DataSource.ESTIMATED, prop_conf, formula, req)
                            self.chains.append({"output":target,"method":formula,"confidence":prop_conf})
                            found = True
                            break
            if not found: break
        return self.values
    
    def _calc(self, f, v):
        try:
            if f=="friedewald": return v["total_cholesterol"]-v["hdl"]-(v["triglycerides"]/5) if v["triglycerides"]<400 else None
            if f=="tg_div_5": return v["triglycerides"]/5
            if f=="tc_minus_hdl": return v["total_cholesterol"]-v["hdl"]
            if f=="gmi": return 3.31+0.02392*v["mean_glucose"]
            if f=="fg_proxy": return 2.0+(v["fasting_glucose"]/35)
            if f=="eag": return 28.7*v["hba1c"]-46.7
            if f=="ckd_epi":
                cr,age,fem = v["creatinine"],v["age"],v.get("is_female",False)
                k,a = (0.7,-0.241 if cr<=0.7 else -1.2) if fem else (0.9,-0.302 if cr<=0.9 else -1.2)
                return 142*((cr/k)**a)*(0.9938**age)*(1.012 if fem else 1.0)
            if f=="ckd_epi_avg": return 142*((v["creatinine"]/0.8)**-0.8)*(0.9938**50)
            if f=="wt_ht": return v["weight_kg"]/((v["height_cm"]/100)**2)
            if f=="homa_ir": return (v["fasting_glucose"]*v["fasting_insulin"])/405
            if f=="tg_hdl": return min(10,v["triglycerides"]/v["hdl"]/0.4)
            if f=="tyg": return math.log(v["triglycerides"]*v["fasting_glucose"]/2)
            if f=="fib4": return (v["age"]*v["ast"])/(v["platelets"]*math.sqrt(v["alt"]))
            if f=="direct": return v["total_cholesterol"]-v["ldl"]-v["hdl"]
            if f=="tg_approx": return v["triglycerides"]/5
            if f=="ldl_regression": return v["ldl"]*0.9
            if f=="tc_hdl": return v["total_cholesterol"]/v["hdl"]
            if f=="ldl_hdl": return v["ldl"]/v["hdl"]
            if f=="ratio": return v["triglycerides"]/v["hdl"]
            if f=="aip": return math.log10((v["triglycerides"]/88.57)/(v["hdl"]/38.67))
        except: pass
        return None
    
    def get_suggestions(self):
        sugg = []
        avail = set(self.values.keys())
        for target, rules in INFERENCE_RULES.items():
            if target in avail: continue
            for req, formula, conf in rules:
                missing = [r for r in req if r not in avail]
                if len(missing)==1:
                    sugg.append({"target":target,"missing":missing[0],"confidence":conf,"priority":"high" if conf>0.8 else "medium"})
        return sorted(sugg, key=lambda x: -x["confidence"])[:10]
    
    def report(self):
        user = [v for v in self.values.values() if v.source==DataSource.USER_INPUT]
        calc = [v for v in self.values.values() if v.source==DataSource.CALCULATED]
        est = [v for v in self.values.values() if v.source==DataSource.ESTIMATED]
        return {"summary":{"user_inputs":len(user),"calculated":len(calc),"estimated":len(est),"total":len(self.values)},"user":[{"name":v.name,"value":v.value,"unit":v.unit} for v in user],"calculated":[{"name":v.name,"value":round(v.value,2),"unit":v.unit,"method":v.method,"confidence":round(v.confidence,2)} for v in calc],"estimated":[{"name":v.name,"value":round(v.value,2),"unit":v.unit,"method":v.method,"confidence":round(v.confidence,2)} for v in est],"chains":self.chains}

def analyze_with_cascade(inputs: Dict[str, float]) -> Dict[str, Any]:
    e = CascadeInferenceEngine()
    e.load_inputs(inputs)
    e.run_cascade()
    return {"analysis":e.report(),"suggestions":e.get_suggestions(),"all_values":{k:{"value":round(v.value,2),"unit":v.unit,"source":v.source.value,"confidence":round(v.confidence,2)} for k,v in e.values.items()}}
