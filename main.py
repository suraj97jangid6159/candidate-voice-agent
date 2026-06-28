from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Form, HTTPException, Request, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, List, Dict
import uvicorn
import yaml
import os
import uuid
import json
import asyncio
import traceback
import logging
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import components
import db
from core.pdf_parser import parse_resume_pdf
from core.scraper import scrape_job_description, analyze_resume_jd_fit
from core.state_machine import CallStateMachine
from core.security import (
    scan_input_injection, scan_output_agreement, scan_sensitive_data,
    sanitize_text, validate_transfer_request, is_valid_phone_format
)
from core.scheduler import CallbackScheduler
from core.notifications import NotificationService
from adapters import (
    load_config,
    get_llm_adapter,
    get_stt_adapter,
    get_tts_adapter,
    get_telephony_adapter
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(UPLOADS_DIR, exist_ok=True)

# Keep track of active WebSocket connections for call updates
active_connections: Dict[str, List[WebSocket]] = {}

# Scheduler instance (initialized on startup)
callback_scheduler: Optional[CallbackScheduler] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    notifier = NotificationService()
    global callback_scheduler
    callback_scheduler = CallbackScheduler(notifier)
    callback_scheduler.start()
    logger.info("Candidate Voice Agent started successfully with scheduler")
    yield
    if callback_scheduler:
        callback_scheduler.stop()
    logger.info("Candidate Voice Agent stopped")


app = FastAPI(title="Candidate Voice Agent", version="2.1.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Pydantic Models for Validation
class CandidateCreate(BaseModel):
    name: str
    phone: str
    current_ctc: Optional[str] = None
    expected_ctc: Optional[str] = None
    notice_period: Optional[str] = None
    skills: Optional[str] = None
    
    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v):
        if not is_valid_phone_format(v):
            raise ValueError('Invalid phone number format')
        return v

class JobCreate(BaseModel):
    candidate_id: str
    company_name: str
    job_title: str
    jd_text: str
    jd_url: Optional[str] = None
    hr_phone: Optional[str] = None
    hr_email: Optional[str] = None
    
    @field_validator('hr_phone')
    @classmethod
    def validate_hr_phone(cls, v):
        if v and not is_valid_phone_format(v):
            raise ValueError('Invalid HR phone number format')
        return v

# Helper Functions
async def broadcast_call_update(call_id: str, message: dict):
    """Broadcast updates to all WebSocket listeners for a call."""
    if call_id in active_connections:
        dead_ws = []
        for ws in active_connections[call_id]:
            try:
                await ws.send_json(message)
            except Exception:
                dead_ws.append(ws)
        # Clean up dead connections
        for ws in dead_ws:
            active_connections[call_id].remove(ws)

async def log_security_event(call_id: str, violation_type: str, flagged_text: str, action_taken: str, severity: str = "MEDIUM"):
    """Log security events to database."""
    try:
        db.save_security_log(call_id, violation_type, flagged_text, action_taken, severity)
        logger.warning(f"Security Event [{severity}] Call {call_id}: {violation_type} - {action_taken}")
    except Exception as e:
        logger.error(f"Failed to log security event: {e}")

async def process_message_with_security(call_id: str, message: str, history: list, candidate_info: dict, job_info: dict, llm_adapter, current_state: str):
    """
    Process a message through the security pipeline before LLM processing.
    Returns: (next_state, response, action, was_blocked)
    """
    config = load_config()
    security_config = config.get("security", {})
    
    # 1. Sanitize input
    clean_message = sanitize_text(message)
    
    # 2. Scan for prompt injection
    is_injection, reason, severity = scan_input_injection(clean_message)
    if is_injection and security_config.get("scan_inputs", True):
        await log_security_event(call_id, "PROMPT_INJECTION", clean_message[:200], f"Blocked: {reason}", severity)
        if severity in ["HIGH", "CRITICAL"]:
            return "COMPLETED", "I apologize, but I'm unable to process that request. Let's stick to discussing the candidate's professional qualifications.", "hangup", True
        # For medium/low, sanitize but continue
        clean_message = "[Content filtered for security]"
    
    # 3. Scan for sensitive data
    has_sensitive, sensitive_types = scan_sensitive_data(clean_message)
    if has_sensitive:
        await log_security_event(call_id, "SENSITIVE_DATA_DETECTED", str(sensitive_types), "Logged but allowed for review", "LOW")
    
    # 4. Process through state machine
    state_machine = CallStateMachine(candidate_info, job_info, llm_adapter)
    next_state, response, action = await state_machine.process_turn(current_state, clean_message, history)
    
    # 5. Scan LLM output for unauthorized agreements
    is_agreement, pattern, agreement_severity = scan_output_agreement(response)
    if is_agreement and security_config.get("block_agreements", True):
        await log_security_event(call_id, "UNAUTHORIZED_AGREEMENT", response[:200], f"Blocked pattern: {pattern}", agreement_severity)
        # Replace with safe response
        safe_response = (
            f"I appreciate your interest. However, I'm only authorized to share the candidate's profile "
            f"and qualifications. Any formal commitments or terms would need to be discussed directly with "
            f"{candidate_info.get('name', 'the candidate')}. Would you like me to arrange that?"
        )
        return next_state, safe_response, action, True
    
    return next_state, response, action, False

# Serve static dashboard
@app.get("/")
async def read_index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))

# Health Check Endpoint
@app.get("/health")
async def health_check():
    config = load_config()
    mock_mode = config.get("app", {}).get("mock_mode", True)
    
    health_status = {
        "status": "healthy",
        "version": "2.0.0",
        "mock_mode": mock_mode,
        "timestamp": datetime.utcnow().isoformat(),
        "services": {}
    }
    
    # Check database connectivity
    try:
        conn = db.get_db_connection()
        conn.execute("SELECT 1")
        conn.close()
        health_status["services"]["database"] = "connected"
    except Exception as e:
        health_status["services"]["database"] = f"error: {str(e)}"
        health_status["status"] = "degraded"
    
    return health_status

# API: Upload Resume & Candidate Profile
@app.post("/api/candidate")
async def create_candidate(
    name: str = Form(...),
    phone: str = Form(...),
    current_ctc: Optional[str] = Form(None),
    expected_ctc: Optional[str] = Form(None),
    notice_period: Optional[str] = Form(None),
    skills: Optional[str] = Form(None),
    resume: UploadFile = File(...)
):
    # Validate phone
    if not is_valid_phone_format(phone):
        return JSONResponse(status_code=400, content={"error": "Invalid phone number format. Use E.164 format (e.g., +15551234567)"})
    
    candidate_id = str(uuid.uuid4())
    
    # Save the file
    file_path = os.path.join(UPLOADS_DIR, f"{candidate_id}_{resume.filename}")
    with open(file_path, "wb") as f:
        f.write(await resume.read())
        
    try:
        # Load config and parse resume PDF
        config = load_config()
        llm = get_llm_adapter(config)
        parsed_data = await parse_resume_pdf(file_path, llm)
        
        if not parsed_data:
            return JSONResponse(status_code=400, content={"error": "Failed to read or parse PDF resume."})
            
        # Overwrite parsed values with explicit form entries if provided
        final_name = name or parsed_data.get("name", "Unknown Candidate")
        final_phone = phone or parsed_data.get("phone", "")
        final_current_ctc = current_ctc or parsed_data.get("current_ctc", "")
        final_expected_ctc = expected_ctc or parsed_data.get("expected_ctc", "")
        final_notice_period = notice_period or parsed_data.get("notice_period", "")
        
        # Skills conversion to comma-separated string
        parsed_skills = parsed_data.get("skills", [])
        if isinstance(parsed_skills, list):
            parsed_skills = ", ".join(parsed_skills)
        final_skills = skills or parsed_skills or ""
        
        # Save to DB
        db.save_candidate(
            candidate_id, 
            final_name, 
            final_phone, 
            final_current_ctc, 
            final_expected_ctc, 
            final_notice_period, 
            final_skills, 
            parsed_data.get("resume_text", "")
        )
        
        logger.info(f"Candidate created: {final_name} ({candidate_id})")
        
        return {
            "success": True,
            "id": candidate_id,
            "name": final_name,
            "phone": final_phone,
            "current_ctc": final_current_ctc,
            "expected_ctc": final_expected_ctc,
            "notice_period": final_notice_period,
            "skills": final_skills,
            "parsed_from_pdf": parsed_data.get("name") is not None
        }
    except Exception as e:
        logger.error(f"Error creating candidate: {e}")
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": f"Internal Server Error: {str(e)}"})

# API: Create / Scrape Job Posting
@app.post("/api/job")
async def create_job(
    candidate_id: str = Form(...),
    company_name: Optional[str] = Form(None),
    job_title: Optional[str] = Form(None),
    jd_url: Optional[str] = Form(None),
    jd_text: Optional[str] = Form(None),
    hr_phone: Optional[str] = Form(None),
    hr_email: Optional[str] = Form(None)
):
    job_id = str(uuid.uuid4())
    
    # Retrieve Candidate details
    cand = db.get_candidate(candidate_id)
    if not cand:
        return JSONResponse(status_code=404, content={"error": "Candidate not found."})
    
    # Validate HR phone if provided
    if hr_phone and not is_valid_phone_format(hr_phone):
        return JSONResponse(status_code=400, content={"error": "Invalid HR phone number format."})
        
    final_company = company_name or "Unknown Company"
    final_title = job_title or "Job Role"
    final_jd = jd_text or ""
    final_phone = hr_phone or ""
    final_email = hr_email or ""
    
    # Scrape description if URL is present
    if jd_url:
        try:
            scraped = await scrape_job_description(jd_url)
            if scraped.get("jd_text"):
                final_jd = scraped["jd_text"]
            if scraped.get("company_name") and not company_name:
                final_company = scraped["company_name"]
            if scraped.get("job_title") and not job_title:
                final_title = scraped["job_title"]
            if scraped.get("hr_phone") and not hr_phone:
                final_phone = scraped["hr_phone"]
            if scraped.get("hr_email") and not hr_email:
                final_email = scraped["hr_email"]
        except Exception as e:
            logger.warning(f"Scraping failed for {jd_url}: {e}")
            # Continue with manual entry if scraping fails

    # Calculate candidate-JD alignment fit score
    fit_score = analyze_resume_jd_fit(cand.get("skills", ""), final_jd)
    
    db.save_job(
        job_id, 
        candidate_id, 
        final_company, 
        final_title, 
        jd_url, 
        final_jd, 
        final_phone, 
        final_email, 
        fit_score
    )
    
    logger.info(f"Job created: {final_company} - {final_title} ({job_id}), Fit Score: {fit_score}")
    
    return {
        "success": True,
        "id": job_id,
        "company_name": final_company,
        "job_title": final_title,
        "jd_url": jd_url,
        "hr_phone": final_phone,
        "hr_email": final_email,
        "fit_score": fit_score
    }

# API: Dial Outbound Agent Call
@app.post("/api/call")
async def initiate_call(request: Request, job_id: str = Form(...), hr_phone: str = Form(...)):
    # Validate inputs
    job = db.get_job(job_id)
    if not job:
        return JSONResponse(status_code=404, content={"error": "Job posting details not found."})
        
    cand = db.get_candidate(job["candidate_id"])
    if not cand:
        return JSONResponse(status_code=404, content={"error": "Candidate profile not found."})
    
    if not is_valid_phone_format(hr_phone):
        return JSONResponse(status_code=400, content={"error": "Invalid HR phone number format."})

    call_id = str(uuid.uuid4())
    db.save_call(call_id, job_id, "DIALING", "")
    
    config = load_config()
    mock_mode = config.get("app", {}).get("mock_mode", False)
    
    if mock_mode or config.get("adapters", {}).get("telephony", {}).get("primary") == "mock":
        logger.info(f"Mock call initiated: {call_id} to {hr_phone}")
        return {
            "success": True,
            "call_id": call_id,
            "status": "MOCK_DIALING",
            "message": "Call initiated in mock mode. Connect via websocket for interactive simulation."
        }
        
    # Real outbound call via Twilio/Vapi
    telephony = get_telephony_adapter(config)
    webhook_base = str(request.base_url).rstrip("/")
    
    try:
        if config.get("adapters", {}).get("telephony", {}).get("primary") == "twilio":
            webhook_url = f"{webhook_base}/webhook/twilio/voice?call_id={call_id}"
            call_sid = await telephony.make_call(hr_phone, config.get("credentials", {}).get("twilio_phone_number"), webhook_url)
            db.save_call(call_sid, job_id, "DIALING", "")
            logger.info(f"Twilio call placed: {call_sid} to {hr_phone}")
            return {"success": True, "call_id": call_sid, "status": "DIALING", "message": "Twilio call placed."}
        else: # Vapi
            webhook_url = f"{webhook_base}/webhook/vapi?call_id={call_id}"
            vapi_call_id = await telephony.make_call(hr_phone, config.get("credentials", {}).get("vapi_phone_number_id"), webhook_url)
            db.save_call(vapi_call_id, job_id, "DIALING", "")
            logger.info(f"Vapi call placed: {vapi_call_id} to {hr_phone}")
            return {"success": True, "call_id": vapi_call_id, "status": "DIALING", "message": "Vapi call placed."}
            
    except Exception as e:
        db.update_call_status(call_id, "FAILED")
        logger.error(f"Telephony failure: {e}")
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": f"Telephony provider failure: {str(e)}"})

# API: Retrieve logs and transcripts
@app.get("/api/calls")
async def get_calls():
    return db.get_all_calls_with_details()

# API: Get security logs
@app.get("/api/security/logs")
async def get_security_logs(limit: int = 100):
    return db.get_all_security_logs(limit)

# API: Scheduler status
@app.get("/api/scheduler/status")
async def scheduler_status():
    if not callback_scheduler:
        return {"status": "not_initialized"}
    return {
        "status": "running" if callback_scheduler.is_running else "stopped",
        "jobs": callback_scheduler.get_jobs(),
    }

# API: Get pending callbacks
@app.get("/api/scheduler/callbacks")
async def get_pending_callbacks():
    return db.get_pending_callbacks()

# API: Get transcript for specific call
@app.get("/api/calls/{call_id}/transcript")
async def get_transcript(call_id: str):
    call = db.get_call(call_id)
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    return {
        "call_id": call_id,
        "transcript": call.get("transcript", ""),
        "status": call.get("status", "UNKNOWN"),
        "security_logs": db.get_security_logs_for_call(call_id)
    }

# Twilio Voice Call Webhook handler
@app.post("/webhook/twilio/voice")
async def twilio_voice(request: Request, call_id: str):
    # Retrieve job information linked to this call
    call = db.get_call(call_id)
    if not call:
        form_data = await request.form()
        call_sid = form_data.get("CallSid")
        call = db.get_call(call_sid)
        if call:
            call_id = call_sid
            
    if not call:
        return XMLResponse("<Response><Say>System error. Call details not found.</Say><Hangup/></Response>")

    job = db.get_job(call["job_id"])
    cand = db.get_candidate(job["candidate_id"])
    
    config = load_config()
    llm = get_llm_adapter(config, cand, job)
    
    # Process opening turn with security
    next_state, response, action, _ = await process_message_with_security(
        call_id, "START", [], cand, job, llm, "START"
    )
    
    transcript = f"Agent: {response}\n"
    db.save_call(call_id, call["job_id"], next_state, transcript)
    
    await broadcast_call_update(call_id, {"role": "agent", "content": response, "state": next_state})
    
    twiml = (
        f'<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<Response>\n'
        f'    <Say voice="Polly.Kimberly">{response}</Say>\n'
        f'    <Gather input="speech" action="/webhook/twilio/gather?call_id={call_id}&amp;state={next_state}" timeout="3" speechTimeout="auto" />\n'
        f'    <Redirect>/webhook/twilio/gather?call_id={call_id}&amp;state={next_state}</Redirect>\n'
        f'</Response>'
    )
    return XMLResponse(twiml)

# Twilio Dialog Gather callback
@app.post("/webhook/twilio/gather")
async def twilio_gather(request: Request, call_id: str, state: str):
    form_data = await request.form()
    speech_result = sanitize_text(form_data.get("SpeechResult", "").strip())
    
    call = db.get_call(call_id)
    if not call or not speech_result:
        twiml = (
            f'<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<Response>\n'
            f'    <Say voice="Polly.Kimberly">I did not catch that. Please speak clearly.</Say>\n'
            f'    <Gather input="speech" action="/webhook/twilio/gather?call_id={call_id}&amp;state={state}" timeout="3" speechTimeout="auto" />\n'
            f'</Response>'
        )
        return XMLResponse(twiml)
        
    job = db.get_job(call["job_id"])
    cand = db.get_candidate(job["candidate_id"])
    
    config = load_config()
    llm = get_llm_adapter(config, cand, job)
    
    # Rebuild history from DB transcript
    history = []
    lines = call["transcript"].split("\n")
    for line in lines:
        if line.startswith("Agent: "):
            history.append({"role": "assistant", "content": line[7:]})
        elif line.startswith("HR: "):
            history.append({"role": "user", "content": line[4:]})
    
    # Process turn with security
    next_state, response, action, was_blocked = await process_message_with_security(
        call_id, speech_result, history, cand, job, llm, state
    )
    
    new_transcript = call["transcript"] + f"HR: {speech_result}\nAgent: {response}\n"
    db.save_call(call_id, call["job_id"], next_state, new_transcript)
    
    await broadcast_call_update(call_id, {"role": "hr", "content": speech_result})
    await broadcast_call_update(call_id, {"role": "agent", "content": response, "state": next_state})
    
    # Check actions with security validation for transfers
    if action == "transfer":
        candidate_num = cand["phone"]
        can_transfer, denial_reason = validate_transfer_request(candidate_num, candidate_num, config)
        
        if not can_transfer:
            await log_security_event(call_id, "TRANSFER_BLOCKED", candidate_num, denial_reason, "HIGH")
            twiml = (
                f'<?xml version="1.0" encoding="UTF-8"?>\n'
                f'<Response>\n'
                f'    <Say voice="Polly.Kimberly">I apologize, but I am unable to transfer this call at this time. Let me schedule a callback instead.</Say>\n'
                f'    <Hangup/>\n'
                f'</Response>'
            )
            db.update_call_status(call_id, "COMPLETED")
            return XMLResponse(twiml)
        
        await broadcast_call_update(call_id, {"role": "system", "content": f"Warm-transferring call to candidate: {candidate_num}"})
        twiml = (
            f'<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<Response>\n'
            f'    <Say voice="Polly.Kimberly">{response}</Say>\n'
            f'    <Dial>{candidate_num}</Dial>\n'
            f'</Response>'
        )
        db.update_call_status(call_id, "TRANSFERRED")
        return XMLResponse(twiml)
        
    elif action and action.startswith("schedule:"):
        callback_time = action.split(":", 1)[1]
        db.save_scheduled_callback(call_id, callback_time)
        db.update_call_status(call_id, "COMPLETED", scheduled_callback=callback_time)
        twiml = (
            f'<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<Response>\n'
            f'    <Say voice="Polly.Kimberly">{response}</Say>\n'
            f'    <Hangup/>\n'
            f'</Response>'
        )
        return XMLResponse(twiml)
        
    elif action == "hangup" or next_state == "COMPLETED":
        twiml = (
            f'<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<Response>\n'
            f'    <Say voice="Polly.Kimberly">{response}</Say>\n'
            f'    <Hangup/>\n'
            f'</Response>'
        )
        db.update_call_status(call_id, "COMPLETED")
        return XMLResponse(twiml)
        
    # Regular dialogue loop
    twiml = (
        f'<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<Response>\n'
        f'    <Say voice="Polly.Kimberly">{response}</Say>\n'
        f'    <Gather input="speech" action="/webhook/twilio/gather?call_id={call_id}&amp;state={next_state}" timeout="3" speechTimeout="auto" />\n'
        f'    <Redirect>/webhook/twilio/gather?call_id={call_id}&amp;state={next_state}</Redirect>\n'
        f'</Response>'
    )
    return XMLResponse(twiml)

# Vapi Dialog handler
@app.post("/webhook/vapi")
async def vapi_webhook(request: Request, call_id: str):
    body = await request.json()
    message = body.get("message", {})
    message_type = message.get("type")
    
    call = db.get_call(call_id)
    if not call:
        return JSONResponse(status_code=404, content={"error": "Call details not found."})
        
    job = db.get_job(call["job_id"])
    cand = db.get_candidate(job["candidate_id"])
    
    config = load_config()
    llm = get_llm_adapter(config, cand, job)
    
    if message_type == "assistant-request":
        hr_speech = ""
        transcript_history = message.get("transcriptHistory", [])
        if transcript_history:
            for msg_item in reversed(transcript_history):
                if msg_item.get("role") == "user":
                    hr_speech = sanitize_text(msg_item.get("content", ""))
                    break
        
        history = []
        for msg_item in transcript_history:
            if msg_item.get("role") in ["user", "assistant"]:
                history.append({"role": msg_item.get("role"), "content": msg_item.get("content")})
                
        current_state = call["status"]
        if current_state == "DIALING":
            current_state = "START"
        
        # Process with security
        next_state, response, action, was_blocked = await process_message_with_security(
            call_id, hr_speech or "START", history, cand, job, llm, current_state
        )
        
        updated_transcript = call["transcript"] + f"HR: {hr_speech}\nAgent: {response}\n"
        db.save_call(call_id, call["job_id"], next_state, updated_transcript)
        
        if hr_speech:
            await broadcast_call_update(call_id, {"role": "hr", "content": hr_speech})
        await broadcast_call_update(call_id, {"role": "agent", "content": response, "state": next_state})
        
        vapi_res = {"response": {"assistant": {"firstMessage": response}}}
        
        if action == "transfer":
            candidate_num = cand["phone"]
            can_transfer, denial_reason = validate_transfer_request(candidate_num, candidate_num, config)
            
            if not can_transfer:
                await log_security_event(call_id, "TRANSFER_BLOCKED", candidate_num, denial_reason, "HIGH")
                vapi_res["response"]["assistant"]["shouldEndCall"] = True
                vapi_res["response"]["assistant"]["firstMessage"] = "I apologize, but I am unable to transfer this call at this time. The candidate will follow up with you directly."
                db.update_call_status(call_id, "COMPLETED")
            else:
                db.update_call_status(call_id, "TRANSFERRED")
                vapi_res["response"]["assistant"]["tools"] = [
                    {
                        "type": "transferCall",
                        "destinations": [{"type": "number", "number": candidate_num}]
                    }
                ]
        elif action and action.startswith("schedule:"):
            callback_time = action.split(":", 1)[1]
            db.save_scheduled_callback(call_id, callback_time)
            db.update_call_status(call_id, "COMPLETED", scheduled_callback=callback_time)
            vapi_res["response"]["assistant"]["shouldEndCall"] = True
        elif action == "hangup" or next_state == "COMPLETED":
            db.update_call_status(call_id, "COMPLETED")
            vapi_res["response"]["assistant"]["shouldEndCall"] = True
            
        return vapi_res
        
    return {"status": "ok"}

# Interactive Mock WebSocket endpoint
@app.websocket("/ws/call/{call_id}")
async def call_websocket(websocket: WebSocket, call_id: str):
    await websocket.accept()
    
    if call_id not in active_connections:
        active_connections[call_id] = []
    active_connections[call_id].append(websocket)
    
    try:
        call = db.get_call(call_id)
        if not call:
            await websocket.send_json({"role": "system", "content": "Error: Call not found in DB."})
            return
            
        job = db.get_job(call["job_id"])
        cand = db.get_candidate(job["candidate_id"])
        
        config = load_config()
        llm = get_llm_adapter(config, cand, job)
        
        # Start dialogue with security
        next_state, response, action, _ = await process_message_with_security(
            call_id, "START", [], cand, job, llm, "START"
        )
        
        transcript = f"Agent: {response}\n"
        db.save_call(call_id, call["job_id"], next_state, transcript)
        
        await websocket.send_json({"role": "agent", "content": response, "state": next_state})
        
        while True:
            data = await websocket.receive_text()
            event = json.loads(data)
            hr_speech = sanitize_text(event.get("content", "").strip())
            
            call = db.get_call(call_id)
            current_state = call["status"]
            
            history = []
            lines = call["transcript"].split("\n")
            for line in lines:
                if line.startswith("Agent: "):
                    history.append({"role": "assistant", "content": line[7:]})
                elif line.startswith("HR: "):
                    history.append({"role": "user", "content": line[4:]})
            
            # Process with security
            next_state, response, action, was_blocked = await process_message_with_security(
                call_id, hr_speech, history, cand, job, llm, current_state
            )
            
            new_transcript = call["transcript"] + f"HR: {hr_speech}\nAgent: {response}\n"
            db.save_call(call_id, call["job_id"], next_state, new_transcript)
            
            await broadcast_call_update(call_id, {"role": "hr", "content": hr_speech})
            await broadcast_call_update(call_id, {"role": "agent", "content": response, "state": next_state})
            
            if was_blocked:
                await broadcast_call_update(call_id, {"role": "system", "content": "Security filter triggered. Response sanitized."})
            
            if action == "transfer":
                candidate_num = cand["phone"]
                can_transfer, denial_reason = validate_transfer_request(candidate_num, candidate_num, config)
                
                if not can_transfer:
                    await log_security_event(call_id, "TRANSFER_BLOCKED", candidate_num, denial_reason, "HIGH")
                    await broadcast_call_update(call_id, {
                        "role": "system", 
                        "content": f"Transfer blocked: {denial_reason}"
                    })
                else:
                    db.update_call_status(call_id, "TRANSFERRED")
                    await broadcast_call_update(call_id, {
                        "role": "system", 
                        "content": f"System: Call successfully warm-transferred to candidate at phone: {candidate_num}."
                    })
                break
            elif action and action.startswith("schedule:"):
                callback_time = action.split(":", 1)[1]
                db.save_scheduled_callback(call_id, callback_time)
                db.update_call_status(call_id, "COMPLETED", scheduled_callback=callback_time)
                await broadcast_call_update(call_id, {
                    "role": "system", 
                    "content": f"System: Call finished. Callback scheduled for: {callback_time}."
                })
                break
            elif action == "hangup" or next_state == "COMPLETED":
                db.update_call_status(call_id, "COMPLETED")
                await broadcast_call_update(call_id, {"role": "system", "content": "System: Call completed."})
                break
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for call: {call_id}")
    except Exception as e:
        logger.error(f"WebSocket error for call {call_id}: {e}")
        traceback.print_exc()
        try:
            await websocket.send_json({"role": "system", "content": f"Internal Error: {str(e)}"})
        except Exception:
            pass
    finally:
        if call_id in active_connections:
            if websocket in active_connections[call_id]:
                active_connections[call_id].remove(websocket)
            if not active_connections[call_id]:
                del active_connections[call_id]

# Helper XML response class
class XMLResponse(JSONResponse):
    media_type = "application/xml"
    def render(self, content: str) -> bytes:
        return content.encode("utf-8")

if __name__ == "__main__":
    config = load_config()
    host = config.get("app", {}).get("host", "127.0.0.1")
    port = config.get("app", {}).get("port", 8000)
    uvicorn.run("main:app", host=host, port=port, reload=True)
