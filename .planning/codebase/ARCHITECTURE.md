# Architecture

**Analysis Date:** 2026-06-28

## Pattern Overview

**Overall:** Modular Layered Web Application with Adapter Pattern

The project implements a virtual voice representative that calls HR, pitches a candidate, and handles warm-transfers. To prevent vendor lock-in and enable offline execution/cheap fallbacks, it heavily utilizes the **Adapter Pattern** to abstract away LLM, STT, TTS, and Telephony backends.

**Key Characteristics:**
- **Adapter-Driven Extensibility:** All AI and telephony interactions are decoupled from core business logic using base interfaces.
- **State Machine Dialogue Flow:** Conversational flows are managed using a deterministic state machine, ensuring predictable call progression.
- **Dual Mode Execution (Live vs Mock):** Uses a `mock_mode` configuration toggle in `config.yaml` to substitute live third-party services with local mock files and rule-based simulations.

---

## Layers

**API & UI Layer (`main.py`, `static/`):**
- **Purpose:** Serve the dashboard UI, receive user uploads (resumes), process JD pastes, trigger calls, and handle incoming webhooks from telephony platforms.
- **Contains:** FastAPI routes, Jinja2 templates, static CSS/JS, and webhook event-handlers.
- **Depends on:** Core Orchestration Layer, Adapter Layer, Storage Layer.

**Core Orchestration & Processing Layer (`core/`):**
- **Purpose:** Execute core business logic including PDF parsing, web scraping, and conversation management.
- **Contains:** `core/state_machine.py` (`CallStateMachine`), `core/pdf_parser.py` (PDF parsing), `core/scraper.py` (BeautifulSoup scraper and skill matching).
- **Depends on:** Adapter Layer interfaces (`adapters/base.py`).

**Adapter Layer (`adapters/`):**
- **Purpose:** Interface contracts and concrete client implementations for third-party systems.
- **Contains:** `adapters/base.py` (base interfaces), `adapters/llm.py` (LLM APIs), `adapters/voice.py` (STT and TTS APIs), `adapters/telephony.py` (call dial and bridge APIs).
- **Depends on:** External APIs (via `httpx`).

**Storage Layer (`db.py`):**
- **Purpose:** Persist Candidate Profiles, Job Information, and Call logs (including transcripts).
- **Contains:** SQLite schema initialization and raw SQL queries.
- **Depends on:** Standard library `sqlite3` only.

---

## Data Flow

### 1. Match & Fit Analysis Flow (Before Dialing)
1. Candidate uploads a PDF resume and submits a job description URL/text in the UI (`static/index.html`).
2. FastAPI (`main.py`) parses the PDF text using `core/pdf_parser.py` and scrapes the JD text using `core/scraper.py`.
3. Candidate skills are matched against the JD requirements to compute a `fit_score`.
4. Extracted profile info and job info are saved to `database.db` via `db.py`.

### 2. Live Outbound Call Flow
1. User clicks "Call" on the dashboard.
2. FastAPI triggers `TelephonyAdapter.make_call` (Vapi / Twilio) to place the outbound call.
3. Telephony system connects with the HR manager and triggers a webhook event or WebSocket streaming back to FastAPI.
4. For each spoken turn:
   - Voice audio is converted to text via `STTAdapter`.
   - Text transcript is fed into `CallStateMachine.process_turn` (`core/state_machine.py`).
   - The state machine transitions states (`OPENING` -> `PITCH` -> `QA_SCREENING` -> `TRANSFER_PROPOSAL` -> `COMPLETED`) and generates the text response via the `LLMAdapter`.
   - The text response is synthesized back to audio bytes via the `TTSAdapter` and streamed to the phone connection.
5. If the HR manager requests a direct discussion with the candidate, `CallStateMachine` returns a `transfer` action, which triggers `TelephonyAdapter.transfer_call` to bridge the call to the candidate's phone line.
6. Once the call terminates, the full transcript and call metrics are logged into SQLite via `db.py`.

---

## Key Abstractions

**Adapter Interfaces (`adapters/base.py`):**
- **`LLMAdapter`**: Abstract method `generate_response(...)`. Custom wrappers fall back from primary APIs (like OpenRouter) to local models or mocks.
- **`STTAdapter`**: Abstract method `speech_to_text(...)`. Decouples speech translation.
- **`TTSAdapter`**: Abstract method `text_to_speech(...)`. Decouples audio rendering.
- **`TelephonyAdapter`**: Abstract methods `make_call(...)` and `transfer_call(...)`. Decouples telephony dialing and call transfer bridges.

**Dialogue Manager (`core/state_machine.py`):**
- **`CallStateMachine`**: Implements turn processing and guides dialogue states sequentially. Emits voice responses and telephony instruction actions (`transfer`, `schedule`, `hangup`).

---

## Error Handling

- **Fallback Adapter Wrappers (`FallbackLLMAdapter`, `FallbackSTTAdapter`, `FallbackTTSAdapter`):** Decorate primary adapters with secondary backends (e.g., ElevenLabs falls back to local EdgeTTS, which falls back to silent Mock voice).
- **Offline / Mock Mode:** Toggled via `mock_mode` in `config.yaml` to bypass all external network exceptions and use pre-configured rule sheets for sandbox evaluation.

---

*Architecture analysis: 2026-06-28*
*Update when major patterns change*
