# Coding Conventions

**Analysis Date:** 2026-06-28

## Naming Patterns

**Files:**
- snake_case for all Python script files (e.g., `pdf_parser.py`, `state_machine.py`).
- `test_*.py` for test suites.
- standard web naming (`app.js`, `style.css`) for frontend assets.

**Classes:**
- PascalCase for all classes (e.g., `CallStateMachine`, `OpenRouterAdapter`).
- Base classes have adapter suffixes (e.g., `LLMAdapter`).

**Functions & Methods:**
- snake_case for all functions and methods (e.g., `process_turn`, `generate_response`, `scrape_job_description`).

**Variables:**
- snake_case for standard variables (e.g., `user_message_clean`, `fit_score`).
- UPPER_SNAKE_CASE for modules-level constants (e.g., `CONFIG_PATH`).

---

## Code Style

**Formatting:**
- standard PEP 8 spacing and indentations (4 spaces per indent).
- 2 spaces for frontend assets (`app.js`, `style.css`).

**Typing:**
- standard Python type hints are utilized in signatures where helpful (e.g., `url: str`, `history: list`).

---

## Import Organization

**Order:**
1. Standard library imports (e.g., `import sqlite3`, `import os`, `import re`).
2. Third-party packages (e.g., `import httpx`, `from fastapi import FastAPI`).
3. Local application modules (e.g., `from adapters import LLMAdapter`, `import db`).

**Path References:**
- Relative imports within package boundaries (e.g., `from .base import LLMAdapter`).

---

## Error Handling

**Strategy:**
- **Explicit Fallbacks:** Handled via custom fallback classes (e.g., `FallbackLLMAdapter`) which catch connection exceptions and route queries to secondary endpoints, or ultimately local mock services.
- **Fail Fast on Missing Config:** Adapters throw a `ValueError` during execution if credentials are unconfigured or placeholder strings remain.
- **Database Safety:** SQLite connections are opened, transactioned, and closed explicitly within each database helper function, avoiding dangling connections.

---

## Logging

- Standard `print()` statements for diagnostic traces in stdout/stderr.
- Log error messages along with caught exceptions using Python tracebacks inside backend methods.

---

## Comments

- Clear, descriptive docstrings for main interface methods and class definitions.
- Explanations of why specific regex or heuristics were selected (e.g., in `core/pdf_parser.py` and `core/scraper.py`).
- Clear phase tags corresponding to the dialogue states in call flows.

---

*Convention analysis: 2026-06-28*
*Update when patterns change*
