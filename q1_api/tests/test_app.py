"""Module 1 tests.

Required by Q1.3:
- a CSV with dirty rows (accepted/rejected counts + per-row reasons)
- the happy-path lifecycle: upload -> stage 1 review -> stage 2 review
- at least three invalid transitions -> 409
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app, batches_db, cases_db
import os
import sys

client = TestClient(app)

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))  #absolute path 



@pytest.fixture(autouse=True)
def clear_db():
 
    batches_db.clear()
    cases_db.clear()


# 1. testing CSV with wrong data
def test_import_csv_with_dirty_rows():
    csv_content = (
        "case_ref,applicant_name,id_number,dob,issue_date,image_ref\n"
        "C001,John Doe,ID12345,2000-01-01,2020-01-01,img1.png\n"  
        "C002,Jane Doe,ID12346,invalid-dob,2020-01-01,img2.png\n"  # wrong date
        "C003,,ID12347,2000-01-01,2020-01-01,img3.png\n"  # missing required field
        "C001,Duplicate Case,ID12348,2000-01-01,2020-01-01,img4.png\n"  # duplicate case_ref
    )

    response = client.post(
        "/api/batches",
        files={"file": ("applications.csv", csv_content, "text/csv")}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["accepted_count"] == 1
    assert data["rejected_count"] == 3


    rejected_details = data["rejected_details"]
    assert len(rejected_details) == 3
    assert rejected_details[0]["row"] == 3 
    assert "Invalid date format" in rejected_details[0]["reason"]
    assert rejected_details[1]["row"] == 4
    assert "Missing required fields" in rejected_details[1]["reason"]
    assert rejected_details[2]["row"] == 5
    assert "Duplicate case_ref" in rejected_details[2]["reason"]


# 2. 測試 Happy-path 生命周期 (Upload -> Review Stage 1 -> Review Stage 2)
def test_happy_path_lifecycle():
    # 上傳合法 CSV
    csv_content = (
        "case_ref,applicant_name,id_number,dob,issue_date,image_ref\n"
        "C_HAPPY,Alice,ID99999,1995-05-20,2018-10-10,alice.jpg\n"
    )
    res_upload = client.post(
        "/api/batches",
        files={"file": ("happy.csv", csv_content, "text/csv")}
    )
    assert res_upload.status_code == 200

    # 手動將狀態推進至 ocr_done (模擬 Module 2 OCR 順利完成)
    cases_db["C_HAPPY"]["status"] = "ocr_done"

    # Stage 1 審核通過
    res_s1 = client.post(
        "/api/cases/C_HAPPY/review",
        json={"stage": 1, "decision": "approve"}
    )
    assert res_s1.status_code == 200
    assert res_s1.json()["status"] == "stage1_approved"

    # Stage 2 審核通過
    res_s2 = client.post(
        "/api/cases/C_HAPPY/review",
        json={"stage": 2, "decision": "approve"}
    )
    assert res_s2.status_code == 200
    assert res_s2.json()["status"] == "stage2_approved"


# 3. 測試至少三個違規轉移觸發 HTTP 409
def test_invalid_state_transitions_return_409():
    # 建立一個處於 pending 狀態的測試 Case
    cases_db["C_TEST"] = {
        "id": "C_TEST",
        "case_ref": "C_TEST",
        "status": "pending"
    }

    # 違規 1：在 pending 狀態（未完成 OCR）直接執行 Stage 1 審核 -> 應回 409
    res1 = client.post(
        "/api/cases/C_TEST/review",
        json={"stage": 1, "decision": "approve"}
    )
    assert res1.status_code == 409

    # 違規 2：在 pending 狀態跳過 Stage 1 直接執行 Stage 2 審核 -> 應回 409
    res2 = client.post(
        "/api/cases/C_TEST/review",
        json={"stage": 2, "decision": "approve"}
    )
    assert res2.status_code == 409

    # 將狀態調整至 stage1_approved
    cases_db["C_TEST"]["status"] = "stage1_approved"

    # 違規 3：對已完成 Stage 1 審核的個案，再次重複提交 Stage 1 審核 -> 應回 409
    res3 = client.post(
        "/api/cases/C_TEST/review",
        json={"stage": 1, "decision": "approve"}
    )
    assert res3.status_code == 409

    # 違規 4：對 stage1_approved 個案，嘗試做非法的 Stage 2 動作（如錯誤的變數值）-> 應回 409
    res4 = client.post(
        "/api/cases/C_TEST/review",
        json={"stage": 2, "decision": "unknown_decision"}
    )
    assert res4.status_code == 409