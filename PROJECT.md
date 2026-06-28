# AI Voice HR Representative Agent

An AI-powered voice agent that calls HR managers on behalf of a job candidate, pitches their profile, answers screening questions, and warm-transfers interested HR to the candidate.

---

## Quick Start

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # fill in API keys
python3 -m pytest tests/  # 69 tests should pass
python3 main.py  # starts on http://127.0.0.1:8000
```

## Project Manifest

| File | Purpose |
|------|---------|
| `main.py` | FastAPI server (routes, webhooks, WebSocket) |
| `db.py` | SQLite database (5 tables, CRUD, migrations) |
| `config.yaml` | Adapter config, security rules, app settings |
| `adapters/base.py` | Abstract interfaces (LLM, STT, TTS, Telephony) |
| `adapters/llm.py` | 5 LLMs: OpenRouter, OpenAI, Anthropic, Gemini, Kimi + Mock + Fallback |
| `adapters/voice.py` | 2 STT (Deepgram, Whisper) + 3 TTS (ElevenLabs, PlayHT, EdgeTTS) + Mock + Fallback |
| `adapters/telephony.py` | 2 providers (Vapi, Twilio) + Mock + Fallback |
| `adapters/__init__.py` | Factory methods, config loading |
| `adapters/utils.py` | API key validation, retry utilities |
| `core/state_machine.py` | Call state machine (6 states: OPENING→PITCH→QA→TRANSFER→COMPLETED) |
| `core/security.py` | Injection scanner, agreement scanner, phone whitelisting |
| `core/pdf_parser.py` | Resume PDF parsing (LLM stub + regex fallback) |
| `core/scraper.py` | JD scraping + resume-JD fit analysis |
| `static/index.html` | Glassmorphic dashboard UI |
| `static/app.js` | Frontend logic (forms, WebSocket, live terminal) |
| `static/style.css` | Dark theme, responsive layout |
| `tests/test_security.py` | 55 security tests |
| `tests/test_adapters.py` | Unit tests (DB, state machine, fit analysis) |
| `tests/test_integration.py` | Integration tests (full API flow) |
| `tests/test_adapter_hardening.py` | Adapter validation & fallback tests |

## Architecture

```
API/UI Layer  →  Core Orchestration  →  Adapter Layer  →  External APIs
                                      →  SQLite Storage
```

Adapter Pattern: primary → fallback → mock chains for LLM, STT, TTS, Telephony.

## Current State — Phase 1 Complete

- ✅ Security integration (injection guards, agreement scanners, phone whitelisting, audit logging)
- ✅ Mock mode for offline testing (no API keys needed)
- ✅ All 5 LLM adapters functioning
- ✅ Call state machine with 6 states
- ✅ Resume PDF parsing + JD scraping + fit analysis
- ✅ Full dashboard with WebSocket live terminal
- ✅ 69 unit/integration tests passing
- ✅ `.gitignore` created

## Next Up — Phase 2: Notification & Scheduler

See `ROADMAP.md` for details. The `scheduled_callbacks` table and `apscheduler` dependency are ready but not wired up.

## Handoff Instructions

If you are a new agent picking up this project:

1. **Read this file** — understand the project structure and state
2. **Read `ROADMAP.md`** — see what phase to work on next
3. **Read `core/security.py`** — the most recently completed module
4. **Read `.planning/codebase/`** — 7 architecture/design docs
5. **Run `python3 -m pytest tests/ -v`** — verify current test state
6. **Check `git log --oneline -5`** — see recent commits
7. **Check `git status`** — see uncommitted changes

The `.planning/phases/` directory contains detailed plan and summary for each phase.
