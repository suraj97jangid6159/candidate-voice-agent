# Technology Stack

**Analysis Date:** 2026-06-28

## Languages

**Primary:**
- Python 3.10+ - All application logic, database access, PDF parsing, web scraping, and API routing.

**Secondary:**
- HTML/JavaScript/CSS - Dashboard user interface and static frontend scripts.

## Runtime

**Environment:**
- Python 3.10+
- Browser runtime for the Candidate Web UI Dashboard.

**Package Manager:**
- pip (configured via `requirements.txt`)

## Frameworks

**Core:**
- FastAPI >= 0.100.0 - Web server and HTTP API routing.
- Uvicorn >= 0.22.0 - ASGI server implementation for running FastAPI.

**Testing:**
- pytest >= 7.3.0 - Unit and integration testing framework.
- pytest-asyncio >= 0.21.0 - Async support for pytest.

## Key Dependencies

**Critical:**
- pdfplumber >= 0.9.0 - PDF text extraction for resume parsing.
- edge-tts >= 6.1.0 - Local Text-to-Speech synthesis (fallback voice generation).
- httpx >= 0.24.0 - Asynchronous HTTP client for API communication (OpenRouter, Deepgram, ElevenLabs, Vapi, Twilio).
- beautifulsoup4 >= 4.12.0 - Web page parsing for Job Description and contact extraction.
- websockets >= 11.0.0 - WebSocket communication support.

**Infrastructure:**
- pyyaml >= 6.0 - YAML configuration file parsing.
- python-multipart >= 0.0.6 - Multipart form data parser (for resume file uploads).
- jinja2 >= 3.1.2 - HTML templating engine.
- sqlite3 (Standard Library) - Relational database interface.

## Configuration

**Environment & Setup:**
- Managed via `config.yaml` in the project root.
- Defines app port, host, database file path, mock mode toggle, adapter preferences, and credentials/API keys.

## Platform Requirements

**Development & Production:**
- Cross-platform (macOS, Linux, Windows) with Python 3.10+ installed.
- Local SQLite database file (defaults to `database.db`).

---

*Stack analysis: 2026-06-28*
*Update after major dependency changes*
