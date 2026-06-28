# Task: Build AI Voice HR Agent with Adapter Pattern & Call State Machine

Build a complete AI Voice HR Agent that calls HR on behalf of a candidate, pitches them, handles questions, and warm-transfers interested HR calls. Implement in Python (FastAPI) and Vanilla HTML/CSS/JS.

---

## 1. System Configuration (config.yaml)
```yaml
app:
  port: 8000
  host: "0.0.0.0"
  db_path: "database.db"

adapters:
  llm:
    primary: "openrouter" # openrouter | anthropic | openai | kimi
    model: "meta-llama/llama-3-70b-instruct"
    fallback: "gemini"
  stt:
    primary: "deepgram" # deepgram | whisper-local
    fallback: "whisper-local"
  tts:
    primary: "elevenlabs" # elevenlabs | playht
    fallback: "playht"
  telephony:
    primary: "vapi" # vapi | twilio | telnyx
    fallback: "twilio"

credentials:
  openrouter_api_key: "YOUR_OPENROUTER_KEY"
  openai_api_key: "YOUR_OPENAI_KEY"
  anthropic_api_key: "YOUR_ANTHROPIC_KEY"
  deepgram_api_key: "YOUR_DEEPGRAM_KEY"
  elevenlabs_api_key: "YOUR_ELEVENLABS_KEY"
  playht_api_key: "YOUR_PLAYHT_KEY"
  vapi_api_key: "YOUR_VAPI_KEY"
  twilio_account_sid: "YOUR_TWILIO_SID"
  twilio_auth_token: "YOUR_TWILIO_TOKEN"
  twilio_phone_number: "+1XXXXXXXXXX"
  telnyx_api_key: "YOUR_TELNYX_KEY"
```

---

## 2. Database Schema (SQLite)
```sql
CREATE TABLE candidates (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    phone TEXT NOT NULL,
    current_ctc TEXT,
    expected_ctc TEXT,
    notice_period TEXT,
    skills TEXT, -- Comma-separated or JSON
    resume_text TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE jobs (
    id TEXT PRIMARY KEY,
    candidate_id TEXT,
    company_name TEXT NOT NULL,
    job_title TEXT NOT NULL,
    jd_url TEXT,
    jd_text TEXT NOT NULL,
    hr_phone TEXT,
    hr_email TEXT,
    fit_score REAL,
    status TEXT DEFAULT 'PENDING', -- PENDING, MATCHED, DIALING, COMPLETED
    FOREIGN KEY(candidate_id) REFERENCES candidates(id)
);

CREATE TABLE calls (
    id TEXT PRIMARY KEY,
    job_id TEXT,
    status TEXT NOT NULL, -- BUSY, PITCHED, TRANSFERRED, COMPLETED
    transcript TEXT,
    recording_url TEXT,
    scheduled_callback TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(job_id) REFERENCES jobs(id)
);
```

---

## 3. Interfaces & Core Adapters (`adapters/`)

Create base contracts and swappable sub-classes:

### LLM Adapter (`adapters/llm.py`)
```python
from abc import ABC, abstractmethod

class LLMAdapter(ABC):
    @abstractmethod
    async def generate_response(self, system_prompt: str, user_message: str, history: list) -> str:
        pass
```
Implement subclass wrappers: `OpenRouterAdapter`, `AnthropicAdapter`, `KimiAdapter`, `GeminiAdapter`. Implement auto-fallback mechanism when HTTP status is not 200.

### Voice Adapter (`adapters/voice.py`)
```python
from abc import ABC, abstractmethod

class STTAdapter(ABC):
    @abstractmethod
    async def speech_to_text(self, audio_data: bytes) -> str:
        pass

class TTSAdapter(ABC):
    @abstractmethod
    async def text_to_speech(self, text: str) -> bytes:
        pass
```
Implement subclasses: `DeepgramSTT`, `WhisperLocalSTT`, `ElevenLabsTTS`, `PlayHTTTS`, `EdgeTTS` (using `edge-tts` python package as a free fallback).

### Telephony Adapter (`adapters/telephony.py`)
```python
from abc import ABC, abstractmethod

class TelephonyAdapter(ABC):
    @abstractmethod
    async def make_call(self, to_number: str, from_number: str, webhook_url: str) -> str:
        """Returns call_sid or session_id"""
        pass
        
    @abstractmethod
    async def transfer_call(self, session_id: str, target_number: str) -> bool:
        """Performs warm SIP or PSTN transfer"""
        pass
```
Implement subclasses:
- `VapiTelephony`: Utilizes Vapi API to instantiate inbound/outbound calls with tools.
- `TwilioTelephony`: Uses Twilio REST API to place outbound call and returns TwiML webhooks.

---

## 4. Webhook and Dialog Logic (`core/state_machine.py`)
Implement the following dialogue states in the webhook orchestrator:

1. **State: OPENING**
   - *"Hello, I'm calling on behalf of [Candidate]. I'm reaching out about the [Job Title] role. Is this a good time to speak?"*
2. **State: BUSY_SCHEDULING**
   - Triggered if HR says "no", "busy", or "call back later".
   - Ask for date/time. Parse output using LLM function calling to store `scheduled_callback` in DB and send a notification to the candidate.
3. **State: PITCH**
   - Triggered if HR says "yes" or "go ahead".
   - Deliver summary: Experience, key skills matched to the specific JD, and CTC alignment.
4. **State: QA_SCREENING**
   - Handle HR questions using resume data.
   - For basic HR questions (CTC, notice period, reasons for leaving): answer directly.
   - For complex technical tests or if HR is very interested: proceed to state `TRANSFER_PROPOSAL`.
5. **State: TRANSFER_PROPOSAL**
   - *"I'd love to connect you directly with [Candidate] right now. Can I transfer this call?"*
   - If YES -> trigger `telephony.transfer_call` to Candidate's verified number.
   - If NO -> trigger `BUSY_SCHEDULING` for a future time slot.
6. **State: LOGGING**
   - Save full transcript, final status, recording link, and push email/SMS notification to the candidate.

---

## 5. Parser & Scraper (`core/scraper.py`, `core/pdf_parser.py`)
- **Scraper**: Use `requests` and `beautifulsoup4` to scrape job requirements, company name, and search contacts. Integrate Apify API search for HR contacts if API key is present.
- **PDF Parser**: Use `pdfplumber` or `fitz` (PyMuPDF) to read the candidate's PDF resume and structure it as JSON using a simple LLM parsing prompt.

---

## 6. Frontend Dashboard (`static/`)
- Single-page layout with Glassmorphic CSS.
- Forms: Candidate Profile (Name, Phone, CTC, Resume PDF upload).
- Forms: Job Discovery (Job Link paste / manual entry, HR number).
- Real-time logging console (using WebSockets or long-polling to fetch call statuses and live transcripts).

---

## Step-by-Step Implementation Workflow for LLM (OpenCode)
1. **Setup Env & Core DB**: Create SQLite schema and configurations reading `config.yaml`.
2. **Implement Parser & Scraper**: Write BeautifulSoup parser and PDF text extractor.
3. **Write Base Adapters**: Implement LLM/Voice/Telephony subclasses with fallback logging.
4. **Build State Machine Routing**: Create the FastAPI webhook handler (`/webhook/vapi` and `/webhook/twilio`) parsing speech/transcripts and returning the correct voice instruction action.
5. **Add Live Call Transfer endpoint**: Wrap Twilio Dial / Vapi Transfer tools.
6. **Build UI Dashboard**: Write HTML/CSS/JS frontend to tie database records together.
