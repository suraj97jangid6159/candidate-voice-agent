import asyncio
from typing import Callable, Awaitable, TypeVar

T = TypeVar("T")

PLACEHOLDER_PREFIXES = ("YOUR_", "sk-your", "pk-your")


def is_valid_api_key(key: str) -> bool:
    """Return True when an API key looks configured (not empty or placeholder)."""
    if not key or not key.strip():
        return False
    upper = key.strip().upper()
    return not any(upper.startswith(p.upper()) for p in PLACEHOLDER_PREFIXES)


def validate_nonempty_text(text: str, field_name: str = "response") -> str:
    """Ensure adapter output is non-empty after stripping."""
    if not text or not text.strip():
        raise ValueError(f"Empty {field_name} from adapter")
    return text.strip()


async def with_retries(
    operation: Callable[[], Awaitable[T]],
    *,
    max_retries: int = 2,
    base_delay: float = 1.0,
    retry_on_status: tuple = (429, 500, 502, 503, 504),
) -> T:
    """
    Execute an async operation with exponential backoff retries.
    Re-raises the last exception when all attempts are exhausted.
    """
    last_error = None
    for attempt in range(max_retries + 1):
        try:
            return await operation()
        except Exception as e:
            last_error = e
            status_code = getattr(getattr(e, "response", None), "status_code", None)
            if status_code is not None and status_code not in retry_on_status:
                raise
            if attempt < max_retries:
                await asyncio.sleep(base_delay * (2 ** attempt))
    raise last_error or RuntimeError("Max retries exceeded")
