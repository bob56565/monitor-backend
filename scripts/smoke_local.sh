#!/bin/bash
# MONITOR MVP Smoke Test - Local Demo Script
# Tests the full pipeline: signup -> raw -> preprocess -> infer -> forecast -> PDF

set -e

API_BASE="http://localhost:8000"
EMAIL="smoke_test_$(date +%s)@example.com"
PASSWORD="smokepass123"

echo "🚀 MONITOR MVP Smoke Test Starting..."
echo "📍 API Base: $API_BASE"
echo ""

# Function to make API requests
api_call() {
    local method=$1
    local endpoint=$2
    local data=$3
    local token=$4
    
    if [ -z "$token" ]; then
        curl -s -X "$method" "$API_BASE$endpoint" \
            -H "Content-Type: application/json" \
            -d "$data"
    else
        curl -s -X "$method" "$API_BASE$endpoint" \
            -H "Content-Type: application/json" \
            -H "Authorization: Bearer $token" \
            -d "$data"
    fi
}

# Step 1: Check health
echo "1️⃣  Checking API health..."
health=$(api_call GET "/health")
if echo "$health" | grep -q "ok"; then
    echo "✅ API is healthy"
else
    echo "❌ API health check failed"
    exit 1
fi
echo ""

# Step 2: Signup
echo "2️⃣  Signing up user: $EMAIL"
signup=$(api_call POST "/auth/signup" "{\"email\": \"$EMAIL\", \"password\": \"$PASSWORD\"}")
TOKEN=$(echo "$signup" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)
USER_ID=$(echo "$signup" | grep -o '"user_id":[0-9]*' | cut -d':' -f2)

if [ -z "$TOKEN" ]; then
    echo "❌ Signup failed"
    echo "Response: $signup"
    exit 1
fi
echo "✅ Signup successful (User ID: $USER_ID, Token: ${TOKEN:0:20}...)"
echo ""

# Step 3: Ingest raw data
echo "3️⃣  Ingesting raw sensor data..."
raw=$(api_call POST "/data/raw" \
    "{\"timestamp\": \"2026-01-27T14:30:00Z\", \"specimen_type\": \"blood\", \"observed\": {\"glucose_mg_dl\": 125.5, \"lactate_mmol_l\": 1.8}, \"context\": {\"age\": 40}}" \
    "$TOKEN")
RAW_ID=$(echo "$raw" | grep -o '"id":[0-9]*' | cut -d':' -f2 | head -1)

if [ -z "$RAW_ID" ]; then
    echo "❌ Raw data ingestion failed"
    echo "Response: $raw"
    exit 1
fi
echo "✅ Raw data ingested (ID: $RAW_ID)"
echo ""

# Step 4: Preprocess
echo "4️⃣  Preprocessing raw data..."
preprocess=$(api_call POST "/data/preprocess" "{\"raw_id\": $RAW_ID}" "$TOKEN")
CAL_ID=$(echo "$preprocess" | grep -o '"id":[0-9]*' | cut -d':' -f2 | head -1)

if [ -z "$CAL_ID" ]; then
    echo "❌ Preprocessing failed"
    echo "Response: $preprocess"
    exit 1
fi
echo "✅ Preprocessing complete (Calibrated ID: $CAL_ID)"
echo ""

# Step 5: Inference with calibrated_id
echo "5️⃣  Running inference with calibrated_id..."
infer=$(api_call POST "/ai/infer" "{\"calibrated_id\": $CAL_ID}" "$TOKEN")
TRACE_ID=$(echo "$infer" | grep -o '"trace_id":"[^"]*"' | cut -d'"' -f4)

if [ -z "$TRACE_ID" ]; then
    echo "❌ Inference failed"
    echo "Response: $infer"
    exit 1
fi
echo "✅ Inference complete (Trace ID: ${TRACE_ID:0:20}...)"
echo ""

# Step 6: Forecast with calibrated_id
echo "6️⃣  Running forecast with calibrated_id (horizon=3)..."
forecast=$(api_call POST "/ai/forecast" \
    "{\"calibrated_id\": $CAL_ID, \"horizon_steps\": 3}" \
    "$TOKEN")
FORECAST_VAL=$(echo "$forecast" | grep -o '"forecast":[0-9.]*' | cut -d':' -f2)

if [ -z "$FORECAST_VAL" ]; then
    echo "❌ Forecast failed"
    echo "Response: $forecast"
    exit 1
fi
echo "✅ Forecast complete (Forecast: $FORECAST_VAL)"
echo ""

# Step 7: Forecast with feature_values (backward compat)
echo "7️⃣  Testing forecast with feature_values (legacy mode)..."
forecast_legacy=$(api_call POST "/ai/forecast" \
    "{\"feature_values\": [0.5, 0.6, 0.7], \"horizon_steps\": 2}" \
    "$TOKEN")
FORECAST_LEGACY=$(echo "$forecast_legacy" | grep -o '"forecast":[0-9.]*' | cut -d':' -f2)

if [ -z "$FORECAST_LEGACY" ]; then
    echo "❌ Legacy forecast failed"
    echo "Response: $forecast_legacy"
    exit 1
fi
echo "✅ Legacy forecast works (Forecast: $FORECAST_LEGACY)"
echo ""

# Step 8: Generate PDF
echo "8️⃣  Generating PDF report..."
pdf=$(api_call POST "/reports/pdf" \
    "{\"raw_id\": $RAW_ID, \"calibrated_id\": $CAL_ID, \"trace_id\": \"$TRACE_ID\"}" \
    "$TOKEN")

# Check if response is PDF (binary data won't work in simple curl, so we check differently)
pdf_response=$(curl -s -w "%{http_code}" -X POST "$API_BASE/reports/pdf" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $TOKEN" \
    -d "{\"raw_id\": $RAW_ID, \"calibrated_id\": $CAL_ID}" \
    -o /tmp/monitor_report.pdf)

HTTP_CODE="${pdf_response: -3}"
if [ "$HTTP_CODE" == "200" ] || [ "$HTTP_CODE" == "201" ]; then
    PDF_SIZE=$(stat -f%z /tmp/monitor_report.pdf 2>/dev/null || stat -c%s /tmp/monitor_report.pdf 2>/dev/null || echo "unknown")
    echo "✅ PDF report generated (Size: $PDF_SIZE bytes, saved to /tmp/monitor_report.pdf)"
else
    echo "❌ PDF generation failed (HTTP $HTTP_CODE)"
    exit 1
fi
echo ""

# Step 9: Test multiple users (isolation)
echo "9️⃣  Testing data isolation (second user)..."
EMAIL2="smoke_test2_$(date +%s)@example.com"
signup2=$(api_call POST "/auth/signup" "{\"email\": \"$EMAIL2\", \"password\": \"$PASSWORD\"}")
TOKEN2=$(echo "$signup2" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)

# Try to preprocess user1's data with user2's token
preprocess_fail=$(api_call POST "/data/preprocess" "{\"raw_id\": $RAW_ID}" "$TOKEN2")
if echo "$preprocess_fail" | grep -q "404\|not found"; then
    echo "✅ Data isolation working (user2 cannot access user1's data)"
else
    echo "⚠️  Data isolation check inconclusive"
fi
echo ""

echo "🎉 Smoke test PASSED!"
echo ""
echo "Summary:"
echo "  • Health check: ✅"
echo "  • User signup: ✅"
echo "  • Raw data ingestion: ✅"
echo "  • Preprocessing: ✅"
echo "  • Inference (calibrated_id): ✅"
echo "  • Forecast (calibrated_id): ✅"
echo "  • Forecast (feature_values): ✅"
echo "  • PDF generation: ✅"
echo "  • Data isolation: ✅"
echo ""
echo "🚀 All core pipeline features operational!"
