# Testing Patterns

**Analysis Date:** 2026-06-28

## Test Framework

**Runner:**
- `pytest` >= 7.3.0
- `pytest-asyncio` >= 0.21.0 - Async support for testing coroutines.
- FastAPI's `TestClient` (via `starlette.testclient.TestClient`) - Local HTTP client for server endpoint integration testing.

**Assertion Library:**
- standard Python `assert` statements.

**Run Commands:**
```bash
python -m pytest tests/              # Run all tests in the tests/ directory
```

---

## Test File Organization

**Location:**
- Separate flat `tests/` directory at the project root.

**Naming:**
- `test_*.py` for test suites (e.g., `test_adapters.py`, `test_integration.py`).

**Structure:**
```
ai_voice_agent_proejct/
├── core/
│   ├── scraper.py
│   └── state_machine.py
├── adapters/
│   └── llm.py
├── tests/
│   ├── test_adapters.py      # Unit tests for db, scraper, and state machine transitions
│   └── test_integration.py   # Integration/API tests for FastAPI endpoints
```

---

## Test Structure

**Suite & Fixtures:**
- Pytest fixtures are used for test setup (e.g., `@pytest.fixture(autouse=True)` in `tests/test_adapters.py` to initialize/clear the SQLite DB schema before test runs).
- Async tests are marked with `@pytest.mark.asyncio`.

**Example Test Pattern:**
```python
@pytest.mark.asyncio
async def test_state_machine_flow():
    candidate_info = { ... }
    job_info = { ... }
    
    # Arrange
    llm = MockLLMAdapter(candidate_info, job_info)
    state_machine = CallStateMachine(candidate_info, job_info, llm)
    
    # Act
    state, response, action = await state_machine.process_turn("START", "")
    
    # Assert
    assert state == "OPENING"
    assert "Alex Mercer" in response
```

---

## Mocking

**Framework & Handlers:**
- Standard Library `unittest.mock` (via `mock.patch` decorators) is used to patch external functions (like `parse_resume_pdf`).
- Concrete mock adapter classes (`MockLLMAdapter` in `adapters/llm.py`, `MockVoiceAdapter` in `adapters/voice.py`, and `MockTelephony` in `adapters/telephony.py`) bypass third-party APIs during testing.

**Examples of Mocking:**
```python
@mock.patch("main.parse_resume_pdf")
def test_full_flow(mock_parse):
    # Setup mock parser response
    mock_parse.return_value = {
        "name": "Jane Doe",
        "skills": ["Python", "FastAPI"],
        ...
    }
```

---

## Coverage & Test Types

**Unit Tests (`tests/test_adapters.py`):**
- Covers helper functionality like `analyze_resume_jd_fit` in `core/scraper.py`.
- Covers database operations (saving/retrieving jobs and candidates).
- Verifies dialogue transition rules in `core/state_machine.py` against expected keywords.

**Integration Tests (`tests/test_integration.py`):**
- Uses FastAPI `TestClient` to execute the full sequence from candidate resume upload (`/api/candidate`), job mapping (`/api/job`), call initialization (`/api/call`), and call history querying (`/api/calls`).
- Verifies return status codes (200 OK) and structure of returned JSON payloads.

---

*Testing analysis: 2026-06-28*
*Update when test patterns change*
