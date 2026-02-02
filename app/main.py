from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from app.api import auth, data, ai, reports, runs, part_a, data_quality, part_b, a2
from app.db.base import Base
from app.db.session import engine
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

app = FastAPI(
    title="MONITOR API",
    description="ISF/Specimen Inference MVP Backend",
    version="0.1.0",
    redirect_slashes=True,
)

# CRITICAL: Add CORS middleware FIRST (before any other middleware)
# This fixes CORS preflight issues in GitHub Codespaces
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods (GET, POST, OPTIONS, etc.)
    allow_headers=["*"],  # Allow all headers
    expose_headers=["*"],  # Expose all headers to the browser
)

# Add middleware to log all requests
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Request: {request.method} {request.url.path} from {request.client.host if request.client else 'unknown'}")
    response = await call_next(request)
    logger.info(f"Response: {response.status_code}")
    return response

# Create tables on app startup
@app.on_event("startup")
def startup_event():
    try:
        Base.metadata.create_all(bind=engine)
    except Exception:
        # Allow failures in test environments
        pass

# Health check
@app.get("/health")
def health_check():
    return {"status": "ok", "service": "MONITOR API"}

# Favicon handler to prevent 404 errors
@app.get("/favicon.ico")
async def favicon():
    from fastapi.responses import Response
    return Response(status_code=204)  # No Content

# Include routers
app.include_router(auth.router)
app.include_router(data.router)
app.include_router(ai.router)
app.include_router(reports.router)
app.include_router(runs.router)
app.include_router(part_a.router)
app.include_router(data_quality.router)
app.include_router(part_b.router)
app.include_router(a2.router)

# Serve frontend demo UI (does not interfere with existing API routes)
UI_DIR = Path(__file__).parent.parent / "ui" / "demo"

@app.get("/")
async def serve_demo_ui():
    """Serve the production platform UI as the canonical frontend at root path."""
    return FileResponse(UI_DIR / "production_platform.html")

@app.get("/demo")
async def serve_demo_ui_alt():
    """Alternative path for production platform UI."""
    return FileResponse(UI_DIR / "production_platform.html")

@app.get("/phase3-only")
async def serve_phase3_only():
    """Serve the Phase 3-only demo UI."""
    return FileResponse(UI_DIR / "phase3_live_demo.html")

@app.get("/test-harness")
async def serve_test_harness():
    """Serve the internal test harness UI (dev/QA only)."""
    return FileResponse(UI_DIR / "test_harness.html")

# Serve static demo result
@app.get("/demo/phase3_direct_demo_result.json")
async def serve_demo_result():
    """Serve the pre-generated Phase 3 demo result."""
    result_file = Path(__file__).parent.parent / "phase3_direct_demo_result.json"
    if result_file.exists():
        return FileResponse(result_file)
    return {"error": "Demo result not found. Run: python3 scripts/phase3_direct_demo.py"}

# API endpoint to run Phase 3 demo
@app.post("/demo/phase3/run")
async def run_phase3_demo_api():
    """Run Phase 3 demo and return results."""
    import subprocess
    import json
    
    try:
        # Run the Phase 3 demo script
        result = subprocess.run(
            ["python3", "scripts/phase3_direct_demo.py"],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=Path(__file__).parent.parent
        )
        
        # Load the result file
        result_file = Path(__file__).parent.parent / "phase3_direct_demo_result.json"
        if result_file.exists():
            with open(result_file) as f:
                return json.load(f)
        
        return {"error": "Demo execution succeeded but result file not found"}
    
    except subprocess.TimeoutExpired:
        return {"error": "Demo execution timed out"}
    except Exception as e:
        return {"error": f"Demo execution failed: {str(e)}"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
