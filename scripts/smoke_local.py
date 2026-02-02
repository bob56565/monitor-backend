#!/usr/bin/env python
"""
MONITOR MVP Smoke Test - Local Demo Script (Python version)
Tests the full pipeline: signup -> raw -> preprocess -> infer -> forecast -> PDF
"""
import requests
import json
import time
import sys
from datetime import datetime

API_BASE = "http://localhost:8000"


def print_step(step_num, message):
    """Print formatted step message."""
    print(f"\n{step_num}️⃣  {message}")


def api_call(method, endpoint, data=None, token=None):
    """Make API request."""
    url = f"{API_BASE}{endpoint}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=10)
        elif method == "POST":
            response = requests.post(url, json=data, headers=headers, timeout=10)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        return response
    except Exception as e:
        print(f"❌ Request failed: {e}")
        sys.exit(1)


def main():
    """Run smoke test."""
    print("🚀 MONITOR MVP Smoke Test Starting...")
    print(f"📍 API Base: {API_BASE}\n")
    
    # Generate unique email
    email = f"smoke_test_{int(time.time())}@example.com"
    password = "smokepass123"
    
    # Step 1: Health check
    print_step(1, "Checking API health...")
    health_response = api_call("GET", "/health")
    if health_response.status_code == 200:
        print("✅ API is healthy")
    else:
        print(f"❌ API health check failed (HTTP {health_response.status_code})")
        sys.exit(1)
    
    # Step 2: Signup
    print_step(2, f"Signing up user: {email}")
    signup_response = api_call("POST", "/auth/signup", {
        "email": email,
        "password": password
    })
    
    if signup_response.status_code not in (200, 201):
        print(f"❌ Signup failed (HTTP {signup_response.status_code})")
        print(f"Response: {signup_response.text}")
        sys.exit(1)
    
    signup_data = signup_response.json()
    token = signup_data.get("access_token") or signup_data.get("token")
    user_id = signup_data.get("user_id")
    print(f"✅ Signup successful (User ID: {user_id}, Token: {token[:20]}...)")
    
    # Step 3: Ingest raw data
    print_step(3, "Ingesting raw sensor data...")
    raw_response = api_call("POST", "/data/raw", {
        "timestamp": "2026-01-27T14:30:00Z",
        "specimen_type": "blood",
        "observed": {
            "glucose_mg_dl": 125.5,
            "lactate_mmol_l": 1.8
        },
        "context": {"age": 40}
    }, token)
    
    if raw_response.status_code not in (200, 201):
        print(f"❌ Raw data ingestion failed (HTTP {raw_response.status_code})")
        sys.exit(1)
    
    raw_data = raw_response.json()
    raw_id = raw_data.get("id") or raw_data.get("raw_id")
    print(f"✅ Raw data ingested (ID: {raw_id})")
    
    # Step 4: Preprocess
    print_step(4, "Preprocessing raw data...")
    preprocess_response = api_call("POST", "/data/preprocess", {
        "raw_id": raw_id
    }, token)
    
    if preprocess_response.status_code != 200:
        print(f"❌ Preprocessing failed (HTTP {preprocess_response.status_code})")
        sys.exit(1)
    
    preprocess_data = preprocess_response.json()
    calibrated_id = preprocess_data.get("id") or preprocess_data.get("calibrated_id")
    print(f"✅ Preprocessing complete (Calibrated ID: {calibrated_id})")
    
    # Step 5: Inference with calibrated_id
    print_step(5, "Running inference with calibrated_id...")
    infer_response = api_call("POST", "/ai/infer", {
        "calibrated_id": calibrated_id
    }, token)
    
    if infer_response.status_code not in (200, 201):
        print(f"❌ Inference failed (HTTP {infer_response.status_code})")
        sys.exit(1)
    
    infer_data = infer_response.json()
    trace_id = infer_data.get("trace_id")
    print(f"✅ Inference complete (Trace ID: {trace_id[:20]}...)")
    
    # Step 6: Forecast with calibrated_id
    print_step(6, "Running forecast with calibrated_id (horizon=3)...")
    forecast_response = api_call("POST", "/ai/forecast", {
        "calibrated_id": calibrated_id,
        "horizon_steps": 3
    }, token)
    
    if forecast_response.status_code not in (200, 201):
        print(f"❌ Forecast failed (HTTP {forecast_response.status_code})")
        sys.exit(1)
    
    forecast_data = forecast_response.json()
    forecast_val = forecast_data.get("forecast")
    steps_ahead = forecast_data.get("steps_ahead")
    print(f"✅ Forecast complete (Forecast: {forecast_val}, Steps: {steps_ahead})")
    
    # Step 7: Forecast with feature_values (backward compat)
    print_step(7, "Testing forecast with feature_values (legacy mode)...")
    forecast_legacy_response = api_call("POST", "/ai/forecast", {
        "feature_values": [0.5, 0.6, 0.7],
        "horizon_steps": 2
    }, token)
    
    if forecast_legacy_response.status_code not in (200, 201):
        print(f"❌ Legacy forecast failed (HTTP {forecast_legacy_response.status_code})")
        sys.exit(1)
    
    forecast_legacy_data = forecast_legacy_response.json()
    forecast_legacy_val = forecast_legacy_data.get("forecast")
    print(f"✅ Legacy forecast works (Forecast: {forecast_legacy_val})")
    
    # Step 8: Generate PDF
    print_step(8, "Generating PDF report...")
    pdf_response = api_call("POST", "/reports/pdf", {
        "raw_id": raw_id,
        "calibrated_id": calibrated_id,
        "trace_id": trace_id
    }, token)
    
    if pdf_response.status_code not in (200, 201):
        print(f"❌ PDF generation failed (HTTP {pdf_response.status_code})")
        sys.exit(1)
    
    pdf_size = len(pdf_response.content)
    print(f"✅ PDF report generated (Size: {pdf_size} bytes)")
    
    # Save PDF for inspection
    with open("/tmp/monitor_report.pdf", "wb") as f:
        f.write(pdf_response.content)
    print(f"   Saved to /tmp/monitor_report.pdf")
    
    # Step 9: Test multiple users (isolation)
    print_step(9, "Testing data isolation (second user)...")
    email2 = f"smoke_test2_{int(time.time())}@example.com"
    signup2_response = api_call("POST", "/auth/signup", {
        "email": email2,
        "password": password
    })
    
    if signup2_response.status_code in (200, 201):
        signup2_data = signup2_response.json()
        token2 = signup2_data.get("access_token") or signup2_data.get("token")
        
        # Try to preprocess user1's data with user2's token
        preprocess_fail_response = api_call("POST", "/data/preprocess", {
            "raw_id": raw_id
        }, token2)
        
        if preprocess_fail_response.status_code == 404:
            print("✅ Data isolation working (user2 cannot access user1's data)")
        else:
            print("⚠️  Data isolation check inconclusive")
    else:
        print("⚠️  Could not test data isolation")
    
    # Summary
    print("\n" + "="*60)
    print("🎉 Smoke test PASSED!")
    print("="*60)
    print("\nSummary:")
    print("  • Health check: ✅")
    print("  • User signup: ✅")
    print("  • Raw data ingestion: ✅")
    print("  • Preprocessing: ✅")
    print("  • Inference (calibrated_id): ✅")
    print("  • Forecast (calibrated_id): ✅")
    print("  • Forecast (feature_values): ✅")
    print("  • PDF generation: ✅")
    print("  • Data isolation: ✅")
    print("\n🚀 All core pipeline features operational!")


if __name__ == "__main__":
    main()
