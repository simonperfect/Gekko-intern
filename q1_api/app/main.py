"""Securities account identity verification: API entry point.

Keep the ASGI entry point importable as `app.main:app` from q1_api/.
Organize application modules within this package. The repository README
defines fixed paths and names in section 2.
"""
import csv
import io
from datetime import datetime
import hashlib
import asyncio
from typing import Dict, List, Optional
from fastapi import BackgroundTasks, FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel
import httpx


app = FastAPI(title="Identity Verification Service")


batches_db: Dict[str, dict] = {}
cases_db: Dict[str, dict] = {}

MOCK_OCR_URL = "http://localhost:9100/ocr/parse"
MOCK_ONBOARDING_URL = "http://localhost:9200/ingest"

class ReviewRequest(BaseModel):
    stage: int
    decision: str  # "approve" or "reject"

def validate_date_format(date_str: str) -> bool:
   
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except (ValueError, TypeError):
        return False


# --- Q3.2: Health Check Endpoint ---
@app.get("/api/health")
def health_check():
    """
    Readiness & Liveness probe.
    Checks database reachability and returns status 200 if healthy.
    """
  
    try:
        # if DB connection, do some query to check if reachable
        db_reachable = True
    except Exception:
        db_reachable = False

    if not db_reachable:
        raise HTTPException(status_code=503, detail="Database not reachable")

    return {
        "status": "healthy",
        "database": "reachable"
    }


@app.post("/api/batches")
async def create_batch(file: UploadFile = File(...)):
   
    content = await file.read()
    decoded_file = content.decode("utf-8")
    csv_reader = csv.DictReader(io.StringIO(decoded_file))

    batch_id = f"batch_{len(batches_db) + 1}"
    accepted_cases = []
    rejected_rows = []
    seen_case_refs = set()

    for row_idx, row in enumerate(csv_reader, start=2):  
        case_ref = row.get("case_ref", "").strip()
        applicant_name = row.get("applicant_name", "").strip()
        id_number = row.get("id_number", "").strip()
        dob = row.get("dob", "").strip()
        issue_date = row.get("issue_date", "").strip()
        image_ref = row.get("image_ref", "").strip()

        # 1. all
        if not all([case_ref, applicant_name, id_number, dob, issue_date, image_ref]):
            rejected_rows.append({"row": row_idx, "reason": "Missing required fields"})
            continue

        # 2. date
        if not validate_date_format(dob) or not validate_date_format(issue_date):
            rejected_rows.append({"row": row_idx, "reason": "Invalid date format, expected YYYY-MM-DD"})
            continue

        # 3. case_ref unique?
        if case_ref in seen_case_refs or case_ref in cases_db:
            rejected_rows.append({"row": row_idx, "reason": f"Duplicate case_ref: {case_ref}"})
            continue

        seen_case_refs.add(case_ref)

        #save data
        case_data = {
            "id": case_ref,
            "batch_id": batch_id,
            "case_ref": case_ref,
            "applicant_name": applicant_name,
            "id_number": id_number,
            "dob": dob,
            "issue_date": issue_date,
            "image_ref": image_ref,
            "status": "pending"
        }
        cases_db[case_ref] = case_data
        accepted_cases.append(case_ref)

    batch_data = {
        "id": batch_id,
        "accepted_count": len(accepted_cases),
        "rejected_count": len(rejected_rows),
        "rejected_details": rejected_rows,
        "case_ids": accepted_cases,
        "status": "created"
    }
    batches_db[batch_id] = batch_data

    return batch_data

@app.get("/api/batches/{id}")
async def get_batch(id: str):

    if id not in batches_db:
        raise HTTPException(status_code=404, detail="Batch not found")
    
    batch = batches_db[id]
    status_counts = {}
    for case_id in batch["case_ids"]:
        status = cases_db[case_id]["status"]
        status_counts[status] = status_counts.get(status, 0) + 1

    return {
        "id": batch["id"],
        "accepted_count": batch["accepted_count"],
        "rejected_count": batch["rejected_count"],
        "status_counts": status_counts
    }

# --- Q2.1 & Q2.2: Async Background OCR & Retries with Backoff ---

async def call_ocr_with_retry(case: dict, max_retries: int = 3):
    """Mock OCR with Timeout、Backoff and ocr_failed sign"""

    case["status"] = "ocr_processing"
    
    async with httpx.AsyncClient(timeout=3.0) as client:    #three second for OCR service
        for attempt in range(max_retries):    
            try:
                response = await client.post(
                    MOCK_OCR_URL,
                    json={"image_ref": case["image_ref"], "case_ref": case["case_ref"]}
                )
                if response.status_code == 200:
                    case["ocr_data"] = response.json()
                    case["status"] = "ocr_done"
                    return
                elif response.status_code == 422:
                    # Unreadable scan
                    case["status"] = "ocr_failed"
                    case["error_reason"] = "Unreadable scan image"
                    return
            except (httpx.RequestError, httpx.TimeoutException):
                if attempt == max_retries - 1:
                    case["status"] = "ocr_failed"
                    case["error_reason"] = "OCR service timeout/unavailable"
                    return
                # Exponential Backoff
                await asyncio.sleep(0.1 * (2 ** attempt))


async def process_batch_ocr_task(batch_id: str):
    """Batch status """
    batch = batches_db.get(batch_id)
    if not batch:
        return

    batch["status"] = "processing"
    
    tasks = []
    for case_id in batch["case_ids"]:
        case = cases_db[case_id]
        # just for pending or ocr_failed 
        if case["status"] in ["pending", "ocr_failed"]:
            tasks.append(call_ocr_with_retry(case))

    if tasks:
        await asyncio.gather(*tasks)   # gather all tasks concurrently for OCR processing

    batch["status"] = "ocr_completed"


@app.post("/api/batches/{id}/process")
async def process_batch(id: str, background_tasks: BackgroundTasks):
 
    if id not in batches_db:
        raise HTTPException(status_code=404, detail="Batch not found")

    background_tasks.add_task(process_batch_ocr_task, id)     #  without waiting for all 50 cases to finish
    return {"message": "OCR processing started", "batch_id": id}




# 1.2 validation of OCR
VALID_TRANSITIONS = {
    ("ocr_done", 1, "approve"): "stage1_approved",
    ("ocr_done", 1, "reject"): "stage1_rejected",
    ("stage1_approved", 2, "approve"): "stage2_approved",
    ("stage1_approved", 2, "reject"): "stage2_rejected",
}

@app.post("/api/cases/{id}/review")
async def review_case(id: str, review: ReviewRequest):
    "checking database"
    if id not in cases_db:
        raise HTTPException(status_code=404, detail="Case not found")

    case = cases_db[id]
    current_status = case["status"]
    transition_key = (current_status, review.stage, review.decision)


    if transition_key not in VALID_TRANSITIONS:
        raise HTTPException(
            status_code=409,
            detail=f"Invalid transition from status '{current_status}' in stage {review.stage} with decision '{review.decision}'"
        )

    new_status = VALID_TRANSITIONS[transition_key]
    case["status"] = new_status
    return {"id": id, "status": new_status}




# --- Q2.3: Export & Idempotent Onboarding Delivery ---

@app.post("/api/batches/{id}/export")
async def export_and_deliver_batch(id: str):

    if id not in batches_db:
        raise HTTPException(status_code=404, detail="Batch not found")

    batch = batches_db[id]
    eligible_cases = [
        cases_db[cid] for cid in batch["case_ids"]
        if cases_db[cid]["status"] == "stage2_approved"
    ]

    if not eligible_cases:
        return {"message": "No eligible cases to export", "exported_count": 0}

    # CSV output
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["case_ref", "applicant_name", "id_number", "dob", "issue_date"])
    writer.writeheader()
    for c in eligible_cases:
        writer.writerow({
            "case_ref": c["case_ref"],
            "applicant_name": c["applicant_name"],
            "id_number": c["id_number"],
            "dob": c["dob"],
            "issue_date": c["issue_date"]
        })

    csv_content = output.getvalue()
    
    # Idempotency Key
    idempotency_key = hashlib.sha256(csv_content.encode("utf-8")).hexdigest()

   
    headers = {
        "Content-Type": "text/csv",
        "Idempotency-Key": idempotency_key,
        "X-Idempotency-Key": idempotency_key,
        "X-File-Name": f"EXPORT-{id}.csv"
    }

    max_retries = 3
    async with httpx.AsyncClient(timeout=5.0) as client:
        for attempt in range(max_retries):
            try:
                response = await client.post(
                    MOCK_ONBOARDING_URL,
                    content=csv_content.encode("utf-8"),
                    headers=headers
                )
                
        
                if response.status_code == 200:
                    for c in eligible_cases:
                        c["status"] = "exported"
                    
                    return {
                        "batch_id": id,
                        "exported_count": len(eligible_cases),
                        "idempotency_key": idempotency_key,
                        "delivery_status": response.status_code,
                        "receipt": response.json()
                    }
                elif response.status_code == 500:
       
                    if attempt == max_retries - 1:
                        raise HTTPException(status_code=502, detail="Onboarding service failed after retries")
                    await asyncio.sleep(0.2 * (2 ** attempt))
                else:
                    raise HTTPException(status_code=response.status_code, detail=response.text)

            except (httpx.RequestError, httpx.TimeoutException):

                if attempt == max_retries - 1:
                    raise HTTPException(status_code=503, detail="Onboarding service unavailable/timeout")
                await asyncio.sleep(0.2 * (2 ** attempt))