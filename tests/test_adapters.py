import pytest
import os
import sys

# Append parent dir to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import db
from core.state_machine import CallStateMachine
from core.scraper import analyze_resume_jd_fit
from adapters.llm import MockLLMAdapter

@pytest.fixture(autouse=True)
def setup_test_db():
    # Make sure we initialize database
    db.init_db()

def test_db_operations():
    # Test candidate save and retrieval
    cand_id = "test_cand"
    db.save_candidate(cand_id, "Test Name", "+12345", "10 LPA", "12 LPA", "30 days", "Python, SQL", "This is resume text.")
    
    cand = db.get_candidate(cand_id)
    assert cand is not None
    assert cand["name"] == "Test Name"
    assert cand["skills"] == "Python, SQL"

    # Test job save
    job_id = "test_job"
    db.save_job(job_id, cand_id, "Test Company", "Developer", "http://test.com", "JD description here", "+12345", "hr@test.com", 8.5)
    
    job = db.get_job(job_id)
    assert job is not None
    assert job["company_name"] == "Test Company"
    assert job["fit_score"] == 8.5

def test_resume_jd_fit():
    skills = "Python, FastAPI, AWS"
    jd_text = "We are looking for a FastAPI backend developer with strong Python skills who is familiar with AWS cloud systems."
    score = analyze_resume_jd_fit(skills, jd_text)
    # 3 out of 3 matched -> 10.0 score
    assert score == 10.0

@pytest.mark.asyncio
async def test_state_machine_flow():
    candidate_info = {
        "name": "Alex Mercer",
        "skills": "Python, FastAPI",
        "current_ctc": "$90,000",
        "expected_ctc": "$110,000",
        "notice_period": "30 days",
        "resume_text": "Experienced Python and FastAPI backend engineer."
    }
    job_info = {
        "job_title": "Backend Engineer",
        "company_name": "Tech Corp",
        "jd_text": "Required skills: Python, FastAPI."
    }
    
    llm = MockLLMAdapter(candidate_info, job_info)
    state_machine = CallStateMachine(candidate_info, job_info, llm)
    
    # Phase 0: Dial/Start
    state, response, action = await state_machine.process_turn("START", "")
    assert state == "OPENING"
    assert "Alex Mercer" in response
    assert action is None
    
    # Phase 1: OPENING -> PITCH
    state, response, action = await state_machine.process_turn("OPENING", "Sure, I have 2 minutes. Go ahead.")
    assert state == "PITCH"
    assert action is None
    
    # Phase 2: PITCH -> QA_SCREENING (Ask CTC)
    state, response, action = await state_machine.process_turn("PITCH", "What is their current CTC and notice period?")
    assert state == "QA_SCREENING"
    assert "$90,000" in response or "30 days" in response
