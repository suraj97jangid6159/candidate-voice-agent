# Codebase Structure

**Analysis Date:** 2026-06-28

## Directory Layout

```
ai_voice_agent_proejct/
├── adapters/            # Third-party service integration adapters (Adapter Pattern)
│   ├── __init__.py      # Adapter instantiation utilities and fallback logic
│   ├── base.py          # Abstract interfaces for LLM, STT, TTS, and Telephony
│   ├── llm.py           # Implementations for OpenRouter, OpenAI, Gemini, etc.
│   ├── telephony.py     # Telephony integrations for Twilio and Vapi
│   └── voice.py         # Voice client integrations for ElevenLabs, EdgeTTS, etc.
├── core/                # Core processing and state orchestration
│   ├── pdf_parser.py    # Resume text parsing and structured entity extraction
│   ├── scraper.py       # JD web scraping, contact extraction, and skill fit analysis
│   └── state_machine.py # Turn-by-turn conversational state machine and dialog logic
├── static/              # Web application dashboard frontend code
│   ├── app.js           # Dashboard UI event handlers and API request functions
│   ├── index.html       # Dashboard HTML layout
│   └── style.css        # Dashboard CSS styling and layout formatting
├── tests/               # Automated validation tests
│   ├── test_adapters.py # Unit tests verifying mock and fallback adapters
│   └── test_integration.py # Integration testing for FastAPI and state machine workflows
├── config.yaml          # Application settings, provider config, and API credentials
├── database.db          # Local SQLite database file (generated at runtime)
├── db.py                # Database initialization, schema schema, and query wrapper functions
├── main.py              # Main FastAPI application server, API routes, and webhook entry points
└── requirements.txt     # Python packages and third-party dependencies manifest
```

---

## Directory Purposes

**adapters/**:
- **Purpose:** Decouple third-party external services (such as API-driven speech engines or messaging services) from core call logic.
- **Contains:** Abstract base classes and concrete classes for LLM, STT, TTS, and Telephony integrations.
- **Key files:** `adapters/base.py`, `adapters/llm.py`, `adapters/voice.py`, `adapters/telephony.py`.

**core/**:
- **Purpose:** Houses logic for parsing user input profiles, analyzing JDs, and driving the turn-based logic of phone conversations.
- **Contains:** Parsing functions, fit score matching, and conversational state structures.
- **Key files:** `core/state_machine.py`, `core/pdf_parser.py`, `core/scraper.py`.

**static/**:
- **Purpose:** Frontend files for the candidate dashboard.
- **Contains:** Vanilla JS, CSS, and HTML files. Served by FastAPI's static mounting route.

**tests/**:
- **Purpose:** Verify functionality of parsing, state transitions, and adapter endpoints.
- **Contains:** Pytest test cases.

---

## Key File Locations

**Entry Points:**
- `main.py` - Launches the FastAPI application server (Uvicorn starts here).
- `static/index.html` - Primary interface entry point for candidates.

**Configuration:**
- `config.yaml` - Primary application configuration, mock toggle, API keys, and endpoint paths.
- `requirements.txt` - Project dependencies.

**Core Logic:**
- `core/state_machine.py` - Dialogue management logic.
- `db.py` - Database helper routines.

---

## Naming Conventions

**Files:**
- snake_case for all backend Python modules (`pdf_parser.py`, `state_machine.py`).
- camelCase or standard names for frontend files (`app.js`, `style.css`).
- `test_*.py` for test files.

**Directories:**
- flat folders for modules (`adapters`, `core`, `static`, `tests`).

---

## Where to Add New Code

**Adding a New LLM/Voice/Telephony Provider:**
- Write the concrete adapter class in the corresponding file under `adapters/` (e.g., `adapters/llm.py` or `adapters/telephony.py`).
- Ensure it implements the appropriate base interface from `adapters/base.py`.
- Import and register it in `adapters/__init__.py` under the factory methods.

**Adding a New Call Stage/State:**
- Modify the state list and turn processing rules inside `core/state_machine.py`.

**Adding a New Backend REST Endpoint:**
- Define the FastAPI route handler in `main.py`.

---

## Special Directories

**uploads/**:
- **Purpose:** Temporary storage of uploaded resume PDFs.
- **Source:** Created dynamically on file upload.
- **Committed:** No (should be added to `.gitignore`).

---

*Structure analysis: 2026-06-28*
*Update when directory structure changes*
