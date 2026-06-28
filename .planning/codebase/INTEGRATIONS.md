# External Integrations

**Analysis Date:** 2026-06-28

## APIs & External Services

**LLM Services:**
- **OpenRouter** (Primary LLM Adapter):
  - Model: `meta-llama/llama-3-70b-instruct` (configurable)
  - SDK/Client: REST API via `httpx` (async)
  - Auth: API Key (`openrouter_api_key` in `config.yaml`)
  - File: `adapters/llm.py` (`OpenRouterAdapter` class)
- **OpenAI / Anthropic / Gemini / Kimi** (Alternative LLM Adapters):
  - SDK/Client: REST APIs via `httpx` (async)
  - Auth: API Keys (`openai_api_key`, `anthropic_api_key`, `credentials.gemini` placeholder, moonshot API Key for Kimi)
  - Files: `adapters/llm.py` (`OpenAIAdapter`, `AnthropicAdapter`, `GeminiAdapter`, `KimiAdapter` classes)

**Speech-to-Text (STT):**
- **Deepgram** (Primary STT):
  - Model: `nova-2`
  - Client: REST API via `httpx` (async)
  - Auth: API Key (`deepgram_api_key` in `config.yaml`)
  - File: `adapters/voice.py` (`DeepgramSTT` class)
- **Whisper API** (Fallback STT):
  - Client: OpenAI Whisper API via `httpx` (async)
  - Auth: API Key (`openai_api_key` in `config.yaml`)
  - File: `adapters/voice.py` (`WhisperLocalSTT` class)

**Text-to-Speech (TTS):**
- **ElevenLabs** (Primary TTS):
  - Model: `eleven_monolingual_v1`
  - Client: REST API via `httpx` (async)
  - Auth: API Key (`elevenlabs_api_key` in `config.yaml`)
  - File: `adapters/voice.py` (`ElevenLabsTTS` class)
- **PlayHT** (Alternative TTS):
  - Client: REST API via `httpx` (async)
  - Auth: API Key and User ID (`playht_api_key` in `config.yaml`)
  - File: `adapters/voice.py` (`PlayHTTTS` class)
- **EdgeTTS** (Local TTS Fallback):
  - Client: Local synthesis via `edge-tts` python package
  - Auth: None (free/open service)
  - File: `adapters/voice.py` (`EdgeTTS` class)

**Telephony:**
- **Vapi** (Primary Telephony):
  - Client: Outbound call REST API via `httpx` (async)
  - Auth: API Key (`vapi_api_key` in `config.yaml`)
  - File: `adapters/telephony.py` (`VapiTelephony` class)
- **Twilio** (Alternative Telephony):
  - Client: REST API via `httpx` (async)
  - Auth: Account SID and Auth Token (`twilio_account_sid`, `twilio_auth_token` in `config.yaml`)
  - File: `adapters/telephony.py` (`TwilioTelephony` class)

## Data Storage

**Databases:**
- **SQLite** (Local Database):
  - Connection: Local file (defaults to `database.db` via `app.db_path` in `config.yaml`)
  - Client: `sqlite3` python module (with `sqlite3.Row` factory)
  - Migrations: Handled procedurally on start via `init_db()` in `db.py`
  - File: `db.py`

## Environment Configuration

**Configuration File:**
- Location: `config.yaml`
- Secret storage: Keys and credentials kept inline in `config.yaml` (needs to be excluded from public tracking if real keys are used).
- Mock Mode: When `app.mock_mode: true` is set, the application uses mock adapters (`MockLLMAdapter`, `MockVoiceAdapter`, `MockTelephony`) to run offline without charging paid API endpoints.

## Webhooks & Callbacks

**Incoming:**
- **FastAPI Endpoint Hooks**:
  - `main.py` defines endpoints for callback events from telephony providers to stream transcripts or update call logs.

---

*Integration audit: 2026-06-28*
*Update when adding/removing external services*
