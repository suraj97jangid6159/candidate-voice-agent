import pytest
from fastapi.testclient import TestClient
import unittest.mock as mock
import json
import os
import sys

# Append parent dir to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app
import db

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    db.init_db()

@mock.patch("main.parse_resume_pdf")
def test_full_flow(mock_parse):
    # Setup mock parser response
    mock_parse.return_value = {
        "name": "Jane Doe",
        "phone": "+19998887777",
        "current_ctc": "15 LPA",
        "expected_ctc": "18 LPA",
        "notice_period": "Immediate",
        "skills": ["Python", "FastAPI", "React"],
        "resume_text": "Jane Doe. Software engineer with experience in Python, FastAPI and React."
    }

    # 1. Create candidate via API
    # Create a dummy pdf file content
    dummy_pdf = b"%PDF-1.4 dummy pdf content"
    
    response = client.post(
        "/api/candidate",
        data={
            "name": "Jane Doe",
            "phone": "+19998887777",
            "current_ctc": "",
            "expected_ctc": "",
            "notice_period": "",
            "skills": ""
        },
        files={"resume": ("resume.pdf", dummy_pdf, "application/pdf")}
    )
    
    assert response.status_code == 200
    candidate_data = response.json()
    assert candidate_data["name"] == "Jane Doe"
    assert candidate_data["skills"] == "Python, FastAPI, React"
    candidate_id = candidate_data["id"]

    # 2. Create Job fit analysis via API
    response = client.post(
        "/api/job",
        data={
            "candidate_id": candidate_id,
            "company_name": "Initech Corp",
            "job_title": "Full Stack Dev",
            "jd_text": "We need a developer who knows Python and FastAPI.",
            "hr_phone": "+15551234567",
            "hr_email": "hr@initech.com"
        }
    )
    
    assert response.status_code == 200
    job_data = response.json()
    assert job_data["company_name"] == "Initech Corp"
    # Match skills: Python, FastAPI are matched out of 3 total -> score ~ 6.7
    assert job_data["fit_score"] > 0
    job_id = job_data["id"]

    # 3. Dial outbound call (mock mode) via API
    response = client.post(
        "/api/call",
        data={
            "job_id": job_id,
            "hr_phone": "+15551234567"
        }
    )
    
    assert response.status_code == 200
    call_data = response.json()
    assert call_data["status"] == "MOCK_DIALING"
    call_id = call_data["call_id"]

    # 4. Check calls logs list API
    response = client.get("/api/calls")
    assert response.status_code == 200
    calls_list = response.json()
    assert len(calls_list) > 0
    
    # Verify latest call logged matchesInitech Corp
    latest_call = calls_list[0]
    assert latest_call["company_name"] == "Initech Corp"
    assert latest_call["job_title"] == "Full Stack Dev"
