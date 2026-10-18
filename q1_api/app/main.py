"""Securities account identity verification: API entry point.

Keep the ASGI entry point importable as `app.main:app` from q1_api/.
Organize application modules within this package. The repository README
defines fixed paths and names in section 2.
"""
import csv
import io
from datetime import datetime
from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel

app = FastAPI(title="Identity Verification Service")


batches_db: Dict[str, dict] = {}
cases_db: Dict[str, dict] = {}

class ReviewRequest(BaseModel):
    stage: int
    decision: str  # "approve" or "reject"

def validate_date_format(date_str: str) -> bool:
   
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except (ValueError, TypeError):
        return False

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


# validation of OCR
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