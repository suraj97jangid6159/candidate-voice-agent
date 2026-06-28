# Phase 1: Security Integration - Context

**Gathered:** 2026-06-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Implement a three-tiered security system to protect the outbound voice agent from prompt injection, data leaks, phone system abuse (toll fraud), and unauthorized binding commitments/agreements.
- Scope: Twilio and Vapi webhook endpoints, core state machine dialog flows, and database auditing.
- Exclusions: General telephony firewall rules, third-party platform API credential rotations.
</domain>

<decisions>
## Implementation Decisions

### Whitelisting & Scope Guards (Tier 1)
- **D-01:** The telephony adapter and webhook server must only dial or transfer calls to numbers matching the candidate's verified number stored in the database.
- **D-02:** Clean both proposed target and candidate numbers by stripping non-digit characters (except leading `+`) before checking match compatibility.
- **D-03:** Reject dialing/transfer targets starting with premium number prefixes: `900`, `1900`, `+1900`.

### Input/Output Guardrails (Tier 2)
- **D-04:** Check incoming STT text transcripts against prompt injection keywords (e.g., "ignore previous instructions", "system prompt", "developer mode"). If a violation is caught, bypass the LLM and output the neutral message: *"I am only authorized to discuss the candidate's professional profile. Let's return to the role details."*
- **D-05:** Scan generated LLM output before TTS synthesis using regex to identify binding agreements or commitments. If matched, bypass the LLM response and replace it with: *"I am only authorized to share the candidate's preferred profile details and qualifications. I will note down those terms, and the candidate can discuss them with you directly."*

### Defensive System Prompt (Tier 3)
- **D-06:** Harden the state machine system prompt with boundary rules: represent candidate professional fit only; do not discuss non-professional topics or personal keys; politely refuse terms negotiation.

### Security Logging & Auditing
- **D-07:** Create a database table `security_logs` to log security violations with columns: `id`, `call_id`, `violation_type` ("INPUT_INJECTION", "OUTPUT_AGREEMENT", "INVALID_TRANSFER_NUMBER"), `flagged_text`, `action_taken`, and `created_at`.
- **D-08:** Save logs to the table whenever a Tier 2 scanner flags an injection or an agreement violation, or when a Tier 1 whitelisting verification fails.
</decisions>

<specifics>
## Specific Ideas
- Input keywords to match: `"ignore previous"`, `"system prompt"`, `"developer mode"`, `"new instructions"`, `"disregard instructions"`, `"bypass instructions"`, `"you are now a"`, `"system override"`, `"ignore rules"`, `"forget everything"`, `"new role"`.
- Output regex patterns to catch: `r"i\s+agree\s+to"`, `r"i\s+accept\s+on\s+behalf"`, `r"i\s+promise"`, `r"we\s+agree\s+on\s+behalf"`, `r"on\s+behalf\s+of\s+.*,\s*i\s+(?:agree|accept|promise)"`, `r"i\s+can\s+guarantee\s+that\s+.*will\s+accept"`, `r"we\s+have\s+a\s+deal"`, `r"i\s+confirm\s+the\s+agreement"`, `r"i\s+accept\s+those\s+terms"`.
</specifics>

<canonical_refs>
## Canonical References

### Call Flow & State Machine
- `core/state_machine.py` — Integrates dialog states, prompts, and actions.
- `main.py` §webhook — Integrates Twilio and Vapi callbacks and connects transfer endpoints.

### Database Operations
- `db.py` — Implements SQLite schema and database interactions.
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `db.get_candidate(candidate_id)` — Fetches the candidate profile (and verified phone number).
- `db.save_call(...)` — Model for storing call metadata.

### Integration Points
- `core/state_machine.py:CallStateMachine.process_turn(...)` — Where Tier 2 & 3 checks run.
- `main.py:twilio_gather(...)` and `main.py:vapi_webhook(...)` — Where transfer targets must be whitelisted.
</code_context>

<deferred>
## Deferred Ideas
- Automatic phone carrier verification lookup (e.g. Twilio Lookup API) — Deferred to production scaling phase.
</deferred>

---

*Phase: 01-security-integration*
*Context gathered: 2026-06-28*
