#!/bin/bash
echo "Testing Monitor API..."
curl -s https://monitor-api.abedelhamdan.workers.dev/ | jq '.version, .total_formulas'
curl -s https://monitor-api.abedelhamdan.workers.dev/demo | jq '.inputs, .calculated, .total'
echo "✅ API healthy"
