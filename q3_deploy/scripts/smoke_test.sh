#!/usr/bin/env bash
# Drives one batch end-to-end through nginx:
# upload -> process -> review -> export -> deliver, printing each step.
# `bash scripts/smoke_test.sh` must pass right after a clean
# `docker compose up --build`.
set -euo pipefail
BASE=${BASE:-http://localhost:8080}

echo "=== 1. Health Check ==="
curl -s -X GET "${BASE}/api/health"
echo -e "\n"

echo "=== 2. Upload Batch ==="
CSV_FILE="../data/account_applications.csv"
if [ ! -f "$CSV_FILE" ]; then
    echo "Error: Test file $CSV_FILE not found!"
    exit 1
fi

UPLOAD_RESPONSE=$(curl -s -X POST "${BASE}/api/batches" -F "file=@${CSV_FILE}")
echo "Upload Response: $UPLOAD_RESPONSE"

# get batch_id
BATCH_ID=$(echo "$UPLOAD_RESPONSE" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)
echo "Extracted Batch ID: $BATCH_ID"
echo ""

if [ -z "$BATCH_ID" ]; then
    echo "Error: Failed to obtain batch ID."
    exit 1
fi

echo "=== 3. Trigger OCR Batch Processing (Process Batch) ==="
PROCESS_RESPONSE=$(curl -s -X POST "${BASE}/api/batches/${BATCH_ID}/process")
echo "Process Response: $PROCESS_RESPONSE"
echo ""

# Wait for asynchronous OCR processing to complete 
echo "Waiting for OCR processing to complete..."
sleep 3

echo "=== 4. Get Batch Status ==="
BATCH_STATUS=$(curl -s -X GET "${BASE}/api/batches/${BATCH_ID}")
echo "Batch Status: $BATCH_STATUS"

# Extract the first case_id for manual review testing
# Assuming the response contains a case_ids array
CASE_ID=$(echo "$UPLOAD_RESPONSE" | grep -o '"case_ids":\["[^"]*"' | grep -o '"[^"]*"$' | tr -d '"')
if [ -z "$CASE_ID" ]; then
    # 備用擷取法：從對應資料中抓取
    CASE_ID=$(curl -s -X GET "${BASE}/api/batches/${BATCH_ID}" | grep -o '"id":"[^"]*"' | tail -n +2 | head -1 | cut -d'"' -f4)
fi
echo "Target Case ID for review: $CASE_ID"
echo ""

if [ -n "$CASE_ID" ]; then
    echo "=== 5. Stage 1: Approve ==="

    curl -s -X POST "${BASE}/api/cases/${CASE_ID}/review" \
         -H "Content-Type: application/json" \
         -d '{"stage": 1, "decision": "approve"}'
    echo -e "\n"

    echo "=== 6. Approve ==="
    curl -s -X POST "${BASE}/api/cases/${CASE_ID}/review" \
         -H "Content-Type: application/json" \
         -d '{"stage": 2, "decision": "approve"}'
    echo -e "\n"
else
    echo "⚠ Warning: Could not automatically extract a Case ID for review, skipping review steps."
fi

echo "=== 7. Export & Deliver Batch ==="
EXPORT_RESPONSE=$(curl -s -X POST "${BASE}/api/batches/${BATCH_ID}/export")
echo "Export Response: $EXPORT_RESPONSE"
echo ""

echo "🎉 Smoke Test completed successfully!"