"""
MONITOR API - Cloudflare Workers compatible version
Uses simple HTTP without FastAPI for minimal dependencies
"""

import json
from app.ml.real_inference_engine import run_full_inference, CLINICAL_THRESHOLDS

def handle_request(request):
    """Handle incoming HTTP request."""
    path = request.get("path", "/")
    method = request.get("method", "GET")
    body = request.get("body", {})
    
    # Route handling
    if path == "/" or path == "":
        return {
            "status": 200,
            "body": json.dumps({
                "service": "MONITOR Health Intelligence API",
                "version": "2.0.0",
                "status": "operational"
            })
        }
    
    elif path == "/health":
        return {
            "status": 200,
            "body": json.dumps({"status": "healthy", "service": "monitor-api"})
        }
    
    elif path == "/reference":
        return {
            "status": 200,
            "body": json.dumps({"references": CLINICAL_THRESHOLDS})
        }
    
    elif path == "/infer" and method == "POST":
        try:
            results = run_full_inference(body)
            return {
                "status": 200,
                "body": json.dumps(results)
            }
        except Exception as e:
            return {
                "status": 500,
                "body": json.dumps({"error": str(e)})
            }
    
    else:
        return {
            "status": 404,
            "body": json.dumps({"error": "Not found"})
        }
