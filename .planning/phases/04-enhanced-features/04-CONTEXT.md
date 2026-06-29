# Phase 4: Enhanced Features - Context

**Gathered:** 2026-06-28
**Status:** Planning

<domain>
## Phase Boundary

Implement enhanced features to upgrade the voice agent from single-candidate MVP to a multi-candidate, production-ready platform with rich analytics and robust parsing.

**Scope:**
1. Multi-candidate dashboard switching
2. LLM-based resume parsing (replace regex fallback)
3. Playwright-based JD scraper (LinkedIn/Naukri)
4. Call recording download & playback
5. Analytics dashboard (call trends, success rates)
6. Webhook retry with exponential backoff

**Exclusions:**
- Production deployment (Docker, CI/CD, SSL) — deferred to Phase 5
- Third-party carrier integrations beyond current Twilio/Vapi
</domain>

<decisions>
## Design Decisions

### Multi-Candidate (D-01)
- Dashboard sidebar lists all candidates with active/archived status
- Selecting a candidate loads their jobs and call history
- API: `GET /api/candidates` + `GET /api/candidates/{id}` with nested jobs

### LLM Resume Parsing (D-02)
- `core/pdf_parser.py` parse_resume_text_with_llm already has the prompt — wire it to actually call the LLM adapter
- Fallback to regex if LLM fails or returns invalid JSON
- Use `MockLLMAdapter` for deterministic test results

### Playwright Scraper (D-03)
- New optional dependency: `playwright`
- If playwright not installed, fall back to existing BeautifulSoup scraper
- Scraper detects LinkedIn/Naukri URLs and switches to Playwright automatically

### Call Recording (D-04)
- Twilio provides recording URLs via webhook callbacks
- Store `recording_url` in calls table (column exists)
- Dashboard shows play button when recording URL is available

### Analytics (D-05)
- New endpoint: `GET /api/analytics/summary` — aggregates call data
- Frontend chart using Chart.js (CDN) for call duration trends and success rates

### Webhook Retry (D-06)
- Add retry wrapper in `adapters/utils.py` with exponential backoff
- Apply to telephony webhook handlers in `main.py`
</decisions>

<canonical_refs>
## Key Files

- `core/pdf_parser.py` — Resume parsing (LLM + fallback)
- `core/scraper.py` — JD scraping (BeautifulSoup → Playwright)
- `static/index.html` — Dashboard layout
- `static/app.js` — Frontend logic
- `db.py` — Schema additions for analytics
- `main.py` — New API endpoints
</canonical_refs>
