# ROADMAP — AI Voice HR Representative Agent

> **Checkpoint:** Phase 1 complete · 2026-06-28
> **Test suite:** 69/69 passing

---

## Phase 1: Security Integration ✅ COMPLETE

**Files:** `.planning/phases/01-security-integration/`

| Task | Status |
|------|--------|
| DB schema: `security_logs` table | ✅ |
| `core/security.py` library | ✅ |
| State machine integration (Tier 2 & 3) | ✅ |
| Webhook transfer whitelisting (Tier 1) | ✅ |
| Security tests (`tests/test_security.py`) | ✅ 55 tests |
| Phase summary | ✅ |

---

## Phase 2: Notification & Scheduler Service ⏳ NEXT

**Dependencies:** `apscheduler` (in requirements.txt, unused), `scheduled_callbacks` table (exists), SendGrid (in `.env.example`, unused)

**What needs to be built:**
- [ ] Background scheduler in `main.py` using `apscheduler` to process `scheduled_callbacks`
- [ ] Email notification service (SendGrid) for callback reminders
- [ ] SMS notification fallback (Twilio SMS)
- [ ] Dashboard notification indicators (bell/badge for upcoming callbacks)
- [ ] Tests for scheduler and notification service

**Files to create:** `core/scheduler.py`, `core/notifications.py`
**Files to modify:** `main.py`, `static/index.html`, `static/app.js`

---

## Phase 3: Production Hardening ⏳ DEFERRED

- [ ] Database migration tool (Alembic or manual migration scripts)
- [ ] Streaming TTS optimization (WebSocket streaming for lower latency)
- [ ] Input validation hardening (Pydantic v2 migration, file upload sanitization)
- [ ] Rate limiting & DoS protection
- [ ] HTTPS/TLS enforcement
- [ ] Logging aggregation & monitoring

---

## Phase 4: Enhanced Features ⏳ DEFERRED

- [ ] Multi-candidate support (dashboard switching)
- [ ] Resume parsing with actual LLM calls (stub in `core/pdf_parser.py`)
- [ ] LinkedIn/Naukri scraper with Playwright fallback
- [ ] Call recording download & playback in dashboard
- [ ] Analytics dashboard (call duration trends, success rates)
- [ ] Webhook retry with exponential backoff (carrier failover)

---

## Phase 5: Production Deployment ⏳ DEFERRED

- [ ] Docker containerization
- [ ] CI/CD pipeline (GitHub Actions)
- [ ] Cloud deployment (AWS/GCP/Azure)
- [ ] Domain & SSL setup
- [ ] Environment-specific config (dev/staging/prod)
- [ ] Load testing & performance tuning

---

## Known Technical Debt

| Issue | Location | Severity |
|-------|----------|----------|
| Stub LLM call in PDF parser | `core/pdf_parser.py:39` | MEDIUM |
| Raw SQL instead of ORM | `db.py` | LOW |
| Pydantic V1 validators deprecated | `main.py:62,77` | LOW |
| `on_event` startup deprecated | `main.py:149` | LOW |
| `apscheduler` unused | `requirements.txt` | LOW |
| No `.env` loading in production | `config.yaml` | MEDIUM |
| Regex-based JD parser fragile | `core/scraper.py` | MEDIUM |
