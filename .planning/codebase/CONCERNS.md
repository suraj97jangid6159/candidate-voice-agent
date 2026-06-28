# Codebase Concerns

**Analysis Date:** 2026-06-28

## Tech Debt

**Raw SQL Queries without ORM:**
- Issue: `db.py` uses raw SQL strings instead of an ORM (like SQLAlchemy or tortoise-orm).
- Impact: Hinders schema evolution, does not support database migration frameworks, and limits backend swappability (e.g., migrating from SQLite to PostgreSQL).
- Fix approach: Refactor `db.py` to use an ORM (e.g., SQLAlchemy with Alembic migrations).

**Regex-Based Fallback Resume Parser:**
- Issue: `core/pdf_parser.py` implements a simplistic regex/heuristic fallback parser (`parse_resume_fallback`) to extract name, phone, and skills.
- Impact: Highly fragile; fails on modern resumes with multi-column formats, non-standard headings, or complex styling.
- Fix approach: Integrate a specialized python parser library (e.g., `pyresparser` or `spacy` entity recognizers) as the fallback.

**Fragile Job Title/Company Scraper Heuristics:**
- Issue: `core/scraper.py` parses job titles and companies by splitting the HTML `<title>` tag with keywords like `" at "` or `" hiring "`.
- Impact: Fails on job boards that use alternate formats (e.g., `"Jobs | Google"` or just `"Senior Backend Developer"`), leading to "Unknown Company" and incorrect title names.
- Fix approach: Implement site-specific scraper rules (JSON-LD metadata parse, selectors for LinkedIn/Indeed) or use LLM-based parsing of the scraped web text.

---

## Security Considerations

**Secrets Inline in config.yaml:**
- Issue: `config.yaml` prompts users to input API keys (OpenRouter, Deepgram, ElevenLabs, Vapi, Twilio) directly in the file.
- Impact: Risk of accidental commits of live production credentials to version control.
- Current mitigation: None (no `.gitignore` entries for `config.yaml`).
- Recommendations: Update configuration load to prioritize environment variables (using `os.environ`), seed `config.yaml` from `.env` files, and add `.env` to `.gitignore`.

**Unvalidated File Uploads:**
- Issue: `/api/candidate` accepts resume file uploads and saves/parses them.
- Risk: Path traversal or malicious file execution if non-PDF files are uploaded.
- Current mitigation: Basic FastAPI form parameter binding, but no file content-header/magic bytes validation.
- Recommendations: Use python-magic to verify mime-type and restrict upload file sizes to <= 5MB.

---

## Performance Bottlenecks

**Serial Call Webhooks Latency:**
- Issue: Dialog turn generation in `core/state_machine.py` awaits the LLM response (`generate_response`) before initiating TTS conversion, which in turn awaits ElevenLabs API payload bytes.
- Impact: Introduces round-trip network delays (often 2-4 seconds), creating unnatural pauses in voice calls.
- Improvement path: Implement streaming webhooks where LLM chunks are tokenized and sent to a streaming TTS API (like ElevenLabs WebSockets) to reduce time-to-first-byte (TTFB).

---

## Fragile Areas

**Call State Machine Turn Length Heuristics:**
- File: `core/state_machine.py` (lines 92-96)
- Why fragile: Dictates warm-transfer triggers based on simple string presence (`"connect"`, `"transfer"`, `"speak with him"`) or arbitrary turn limits (`len(history) > 6`).
- Common failures: HR saying *"I can transfer you to our manager"* might trigger the agent to initiate transfer to the *candidate* instead, or a long Q&A session might force a transfer proposal prematurely.
- Safe modification: Refactor state machine to use LLM function calling to classify call actions instead of raw keyword matches.

---

## Test Coverage Gaps

**Live Adapter API Integration Tests:**
- What's not tested: Integrations with real OpenRouter, Deepgram, Vapi, or Twilio endpoints.
- Risk: Changes in third-party API payloads (e.g. ElevenLabs API versioning) will break the integration silently.
- Priority: Medium
- Difficulty to test: Requires API key secrets and sandbox environments.
- Recommendations: Add mock-recorded integration tests (e.g., using `vcrpy` to replay HTTP requests).

---

*Concerns audit: 2026-06-28*
*Update as issues are fixed or new ones discovered*
