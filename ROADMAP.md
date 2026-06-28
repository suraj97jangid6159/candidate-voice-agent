# ROADMAP — Candidate Voice Agent

> **Checkpoint:** Phase 3 hardening (Pydantic V2, lifespan, dead code) · 2026-06-28
> **Test suite:** 77/77 passing, 0 deprecation warnings

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

## Phase 2: Notification & Scheduler Service ✅ COMPLETE

**Files:** `core/scheduler.py`, `core/notifications.py`

| Task | Status |
|------|--------|
| Background scheduler (`APScheduler`) polling pending callbacks every 60s | ✅ |
| Email notification service (SendGrid) with mock fallback | ✅ |
| `main.py` startup wiring + API endpoints (`/api/scheduler/status`, `/api/scheduler/callbacks`) | ✅ |
| Tests for scheduler and notification service (`tests/test_scheduler.py`) | ✅ 8 tests |
| Dashboard notification indicators | ⏳ deferred |
| SMS notification fallback (Twilio SMS) | ⏳ deferred |

---

## Phase 3: Production Hardening ✅ PARTIALLY COMPLETE

- [x] Input validation hardening (Pydantic V2 migration, file upload sanitization)
- [x] Migrate `on_event` startup to lifespan pattern
- [x] Remove dead code (`parse_resume_text_with_llm` stub)
- [ ] Database migration tool (Alembic or manual migration scripts)
- [ ] Streaming TTS optimization (WebSocket streaming for lower latency)
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
| Raw SQL instead of ORM | `db.py` | LOW |
| No `.env` loading in production | `config.yaml` | MEDIUM |
| Regex-based JD parser fragile | `core/scraper.py` | MEDIUM |
