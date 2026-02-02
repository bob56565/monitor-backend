"""
MONITOR Working API
===================
Production-ready API using real inference engine.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime
import json

# Import our REAL inference engine
import sys
sys.path.insert(0, '/root/clawd/monitor-backend')
from app.ml.real_inference_engine import (
    run_full_inference,
    CLINICAL_THRESHOLDS,
    calculate_egfr_ckdepi_2021,
    calculate_homa_ir,
    calculate_bmi
)

app = FastAPI(
    title="MONITOR Health Intelligence API",
    version="2.0.0",
    description="Real clinical inference with scientifically validated algorithms"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# Models
# =============================================================================

class HealthInput(BaseModel):
    """Input model for health inference."""
    # Glycemic
    glucose: Optional[float] = Field(None, description="Fasting glucose in mg/dL")
    hemoglobin_a1c: Optional[float] = Field(None, description="HbA1c in %")
    insulin: Optional[float] = Field(None, description="Fasting insulin in μIU/mL")
    
    # Lipids
    total_cholesterol: Optional[float] = Field(None, description="Total cholesterol in mg/dL")
    ldl_cholesterol: Optional[float] = Field(None, description="LDL cholesterol in mg/dL")
    hdl_cholesterol: Optional[float] = Field(None, description="HDL cholesterol in mg/dL")
    triglycerides: Optional[float] = Field(None, description="Triglycerides in mg/dL")
    
    # Kidney
    creatinine: Optional[float] = Field(None, description="Creatinine in mg/dL")
    bun: Optional[float] = Field(None, description="BUN in mg/dL")
    
    # Blood Pressure
    systolic_bp: Optional[float] = Field(None, description="Systolic BP in mmHg")
    diastolic_bp: Optional[float] = Field(None, description="Diastolic BP in mmHg")
    
    # Thyroid
    tsh: Optional[float] = Field(None, description="TSH in mIU/L")
    
    # Vitamins
    vitamin_d: Optional[float] = Field(None, description="25-OH Vitamin D in ng/mL")
    vitamin_b12: Optional[float] = Field(None, description="Vitamin B12 in pg/mL")
    
    # Liver
    alt: Optional[float] = Field(None, description="ALT in U/L")
    ast: Optional[float] = Field(None, description="AST in U/L")
    
    # Inflammation
    hscrp: Optional[float] = Field(None, description="hs-CRP in mg/L")
    
    # Demographics
    age: Optional[int] = Field(None, description="Age in years")
    sex: Optional[str] = Field(None, description="Sex (M/F)")
    weight_kg: Optional[float] = Field(None, description="Weight in kg")
    height_cm: Optional[float] = Field(None, description="Height in cm")
    
    # Risk factors
    smoker: bool = Field(False, description="Current smoker")
    diabetic: bool = Field(False, description="Known diabetes diagnosis")

class InferenceResponse(BaseModel):
    status: str
    timestamp: str
    inputs_received: List[str]
    inferences: List[Dict[str, Any]]
    derived_values: Dict[str, Any]
    overall_health_score: Optional[float]

# =============================================================================
# Endpoints
# =============================================================================

@app.get("/")
async def root():
    """API root - returns basic info."""
    return {
        "service": "MONITOR Health Intelligence API",
        "version": "2.0.0",
        "status": "operational",
        "endpoints": {
            "/infer": "POST - Run health inference",
            "/reference": "GET - Get clinical reference ranges",
            "/health": "GET - Health check",
            "/demo": "GET - Interactive demo page"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "monitor-api",
        "version": "2.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/reference")
async def get_references():
    """Return all clinical reference ranges with sources."""
    return {
        "status": "success",
        "references": CLINICAL_THRESHOLDS,
        "note": "All thresholds from validated clinical guidelines"
    }

@app.post("/infer", response_model=InferenceResponse)
async def run_inference(inputs: HealthInput):
    """
    Run health inference on provided biomarker data.
    
    This is the main endpoint. Provide any combination of biomarkers
    and receive risk assessments with confidence scores.
    """
    # Convert Pydantic model to dict, removing None values
    input_dict = {k: v for k, v in inputs.dict().items() if v is not None}
    
    if not input_dict:
        raise HTTPException(
            status_code=400,
            detail="No valid inputs provided. Please include at least one biomarker value."
        )
    
    # Run inference
    results = run_full_inference(input_dict)
    results["timestamp"] = datetime.utcnow().isoformat()
    
    return results

@app.get("/demo", response_class=HTMLResponse)
async def demo_page():
    """Interactive demo page."""
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MONITOR Health Intelligence Demo</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #fff;
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        h1 { 
            text-align: center; 
            margin-bottom: 10px;
            font-size: 2.5em;
            background: linear-gradient(90deg, #00d9ff, #00ff88);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .subtitle { text-align: center; color: #888; margin-bottom: 30px; }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 30px; }
        @media (max-width: 768px) { .grid { grid-template-columns: 1fr; } }
        .card {
            background: rgba(255,255,255,0.05);
            border-radius: 16px;
            padding: 24px;
            border: 1px solid rgba(255,255,255,0.1);
        }
        .card h2 { margin-bottom: 20px; font-size: 1.3em; color: #00d9ff; }
        .input-group { margin-bottom: 15px; }
        .input-group label { 
            display: block; 
            margin-bottom: 5px; 
            color: #aaa;
            font-size: 0.9em;
        }
        .input-group input {
            width: 100%;
            padding: 12px;
            border: 1px solid rgba(255,255,255,0.2);
            border-radius: 8px;
            background: rgba(0,0,0,0.3);
            color: #fff;
            font-size: 1em;
        }
        .input-group input:focus {
            outline: none;
            border-color: #00d9ff;
        }
        .input-row { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }
        button {
            width: 100%;
            padding: 15px;
            border: none;
            border-radius: 8px;
            background: linear-gradient(90deg, #00d9ff, #00ff88);
            color: #000;
            font-size: 1.1em;
            font-weight: bold;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
            margin-top: 20px;
        }
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 30px rgba(0,217,255,0.3);
        }
        .results { margin-top: 30px; }
        .result-card {
            background: rgba(255,255,255,0.03);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 15px;
            border-left: 4px solid #00d9ff;
        }
        .result-card.LOW { border-left-color: #00ff88; }
        .result-card.MODERATE { border-left-color: #ffaa00; }
        .result-card.HIGH { border-left-color: #ff4444; }
        .result-card.CRITICAL { border-left-color: #ff0000; }
        .result-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }
        .result-title { font-size: 1.1em; font-weight: bold; }
        .risk-badge {
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 0.8em;
            font-weight: bold;
        }
        .risk-badge.LOW { background: rgba(0,255,136,0.2); color: #00ff88; }
        .risk-badge.MODERATE { background: rgba(255,170,0,0.2); color: #ffaa00; }
        .risk-badge.HIGH { background: rgba(255,68,68,0.2); color: #ff4444; }
        .risk-badge.CRITICAL { background: rgba(255,0,0,0.3); color: #ff0000; }
        .explanation { color: #ccc; margin-bottom: 15px; line-height: 1.5; }
        .metrics { display: flex; gap: 20px; margin-bottom: 15px; }
        .metric { text-align: center; }
        .metric-value { font-size: 1.5em; font-weight: bold; color: #00d9ff; }
        .metric-label { font-size: 0.8em; color: #888; }
        .factors { margin-top: 15px; }
        .factor { 
            padding: 8px 12px; 
            background: rgba(0,0,0,0.3); 
            border-radius: 6px;
            margin-bottom: 5px;
            font-size: 0.9em;
        }
        .recommendations { margin-top: 15px; }
        .recommendations h4 { color: #00ff88; margin-bottom: 10px; }
        .recommendations ul { list-style: none; }
        .recommendations li { 
            padding: 8px 0;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }
        .recommendations li:before { content: "→ "; color: #00d9ff; }
        .health-score {
            text-align: center;
            padding: 30px;
            background: rgba(0,217,255,0.1);
            border-radius: 16px;
            margin-bottom: 20px;
        }
        .health-score-value {
            font-size: 4em;
            font-weight: bold;
            background: linear-gradient(90deg, #00d9ff, #00ff88);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .health-score-label { color: #888; margin-top: 10px; }
        .loading { text-align: center; padding: 40px; color: #888; }
        .error { background: rgba(255,0,0,0.1); padding: 20px; border-radius: 8px; color: #ff4444; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🧬 MONITOR</h1>
        <p class="subtitle">Health Intelligence with Confidence Scoring</p>
        
        <div class="grid">
            <div class="card">
                <h2>📊 Enter Your Lab Values</h2>
                <form id="labForm">
                    <div class="input-row">
                        <div class="input-group">
                            <label>Fasting Glucose (mg/dL)</label>
                            <input type="number" name="glucose" placeholder="e.g., 95" step="0.1">
                        </div>
                        <div class="input-group">
                            <label>HbA1c (%)</label>
                            <input type="number" name="hemoglobin_a1c" placeholder="e.g., 5.4" step="0.1">
                        </div>
                    </div>
                    
                    <div class="input-row">
                        <div class="input-group">
                            <label>Total Cholesterol (mg/dL)</label>
                            <input type="number" name="total_cholesterol" placeholder="e.g., 180">
                        </div>
                        <div class="input-group">
                            <label>LDL Cholesterol (mg/dL)</label>
                            <input type="number" name="ldl_cholesterol" placeholder="e.g., 100">
                        </div>
                    </div>
                    
                    <div class="input-row">
                        <div class="input-group">
                            <label>HDL Cholesterol (mg/dL)</label>
                            <input type="number" name="hdl_cholesterol" placeholder="e.g., 55">
                        </div>
                        <div class="input-group">
                            <label>Triglycerides (mg/dL)</label>
                            <input type="number" name="triglycerides" placeholder="e.g., 120">
                        </div>
                    </div>
                    
                    <div class="input-row">
                        <div class="input-group">
                            <label>Creatinine (mg/dL)</label>
                            <input type="number" name="creatinine" placeholder="e.g., 0.9" step="0.1">
                        </div>
                        <div class="input-group">
                            <label>Blood Pressure (sys/dia)</label>
                            <input type="text" id="bp" placeholder="e.g., 120/80">
                        </div>
                    </div>
                    
                    <div class="input-row">
                        <div class="input-group">
                            <label>Age</label>
                            <input type="number" name="age" placeholder="e.g., 35">
                        </div>
                        <div class="input-group">
                            <label>Sex</label>
                            <select name="sex" style="width:100%;padding:12px;border:1px solid rgba(255,255,255,0.2);border-radius:8px;background:rgba(0,0,0,0.3);color:#fff;">
                                <option value="">Select...</option>
                                <option value="M">Male</option>
                                <option value="F">Female</option>
                            </select>
                        </div>
                    </div>
                    
                    <button type="submit">🔬 Analyze My Health</button>
                </form>
            </div>
            
            <div class="card">
                <h2>📈 Your Health Analysis</h2>
                <div id="results">
                    <div class="loading">
                        Enter your lab values and click "Analyze" to see your personalized health insights.
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        document.getElementById('labForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const resultsDiv = document.getElementById('results');
            resultsDiv.innerHTML = '<div class="loading">Analyzing your data...</div>';
            
            const formData = new FormData(e.target);
            const data = {};
            
            formData.forEach((value, key) => {
                if (value && value !== '') {
                    data[key] = isNaN(value) ? value : parseFloat(value);
                }
            });
            
            // Parse blood pressure
            const bp = document.getElementById('bp').value;
            if (bp && bp.includes('/')) {
                const [sys, dia] = bp.split('/');
                data.systolic_bp = parseFloat(sys);
                data.diastolic_bp = parseFloat(dia);
            }
            
            try {
                const response = await fetch('/infer', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                
                if (!response.ok) {
                    throw new Error('Analysis failed');
                }
                
                const results = await response.json();
                displayResults(results);
            } catch (error) {
                resultsDiv.innerHTML = '<div class="error">Error: ' + error.message + '</div>';
            }
        });
        
        function displayResults(results) {
            const resultsDiv = document.getElementById('results');
            let html = '';
            
            if (results.overall_health_score !== null) {
                html += `
                    <div class="health-score">
                        <div class="health-score-value">${results.overall_health_score}</div>
                        <div class="health-score-label">Overall Health Score</div>
                    </div>
                `;
            }
            
            results.inferences.forEach(inf => {
                html += `
                    <div class="result-card ${inf.risk_level}">
                        <div class="result-header">
                            <span class="result-title">${inf.title}</span>
                            <span class="risk-badge ${inf.risk_level}">${inf.risk_level}</span>
                        </div>
                        <p class="explanation">${inf.explanation}</p>
                        <div class="metrics">
                            <div class="metric">
                                <div class="metric-value">${inf.risk_score}%</div>
                                <div class="metric-label">Risk Score</div>
                            </div>
                            <div class="metric">
                                <div class="metric-value">${Math.round(inf.confidence * 100)}%</div>
                                <div class="metric-label">Confidence</div>
                            </div>
                        </div>
                        <div class="factors">
                            ${inf.contributing_factors.map(f => `<div class="factor">${f.factor}</div>`).join('')}
                        </div>
                        <div class="recommendations">
                            <h4>Recommendations</h4>
                            <ul>
                                ${inf.recommendations.map(r => `<li>${r}</li>`).join('')}
                            </ul>
                        </div>
                    </div>
                `;
            });
            
            resultsDiv.innerHTML = html;
        }
    </script>
</body>
</html>
"""

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
