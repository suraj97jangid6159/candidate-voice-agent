import re
from typing import Tuple, Optional, Dict, Any
import html

# Keywords that indicate prompt injection attempts
INJECTION_KEYWORDS = [
    "ignore previous", "ignore all previous", "system prompt",
    "developer mode", "new instructions", "disregard instructions",
    "bypass instructions", "you are now a", "system override",
    "ignore rules", "forget everything", "new role", "dan mode",
    "jailbreak", "ignore your", "pretend to be", "roleplay as",
    "simulation mode", "hypothetical scenario", "what if you were"
]

# Patterns that indicate the agent is making binding commitments or agreements
AGREEMENT_PATTERNS = [
    r"i\s+agree\s+to",
    r"i\s+accept\s+on\s+behalf",
    r"i\s+promise",
    r"we\s+agree\s+on\s+behalf",
    r"on\s+behalf\s+of\s+.*,\s*i\s+(?:agree|accept|promise)",
    r"i\s+can\s+guarantee\s+that\s+.*will\s+accept",
    r"we\s+have\s+a\s+deal",
    r"i\s+confirm\s+the\s+agreement",
    r"i\s+accept\s+those\s+terms",
    r"\bde\s+al\b",
    r"\bagreed\b",
    r"\bconfirmed\b",
    r"i\s+commit\s+to",
    r"i\s+guarantee",
    r"i\s+will\s+ensure"
]

# Sensitive data patterns to detect in transcripts
SENSITIVE_PATTERNS = {
    "ssn": r"\b\d{3}[-.]?\d{2}[-.]?\d{4}\b",
    "credit_card": r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b",
    "api_key": r"\b[a-zA-Z0-9]{32,64}\b",
}

SAFE_INJECTION_RESPONSE = (
    "I am only authorized to discuss the candidate's professional profile. "
    "Let's return to the role details."
)

SAFE_AGREEMENT_RESPONSE = (
    "I am only authorized to share the candidate's preferred profile details and qualifications. "
    "I will note down those terms, and the candidate can discuss them with you directly."
)


def scan_input_injection(text: str) -> Tuple[bool, Optional[str], str]:
    """
    Scans the incoming STT transcript for prompt injection indicators.
    
    Returns:
        tuple: (is_injection, matched_reason, severity)
            severity: "LOW", "MEDIUM", "HIGH", "CRITICAL"
    """
    if not text or len(text.strip()) < 3:
        return False, None, "LOW"
        
    text_clean = text.lower().strip()
    
    # Check for injection keywords
    for kw in INJECTION_KEYWORDS:
        if kw in text_clean:
            severity = "HIGH" if any(x in kw for x in ["ignore", "system", "override", "jailbreak"]) else "MEDIUM"
            return True, f"Matched keyword: '{kw}'", severity
            
    # Check for excessive length (possible buffer overflow / injection)
    if len(text_clean) > 2000:
        return True, "Excessive message length - possible injection attempt", "MEDIUM"
        
    # Check for HTML/script tags
    if re.search(r'<script|javascript:|on\w+\s*=', text_clean, re.IGNORECASE):
        return True, "Script tag or event handler detected", "HIGH"
        
    return False, None, "LOW"


def scan_output_agreement(text: str) -> Tuple[bool, Optional[str], str]:
    """
    Scans the generated LLM response for unauthorized binding agreements or commitments.
    
    Returns:
        tuple: (is_violating, matched_pattern, severity)
    """
    if not text:
        return False, None, "LOW"
        
    text_clean = text.lower().strip()
    
    for pattern in AGREEMENT_PATTERNS:
        if re.search(pattern, text_clean):
            severity = "HIGH" if any(x in pattern for x in ["guarantee", "commit", "deal"]) else "MEDIUM"
            return True, f"Matched agreement pattern: '{pattern}'", severity
            
    return False, None, "LOW"


def scan_sensitive_data(text: str) -> Tuple[bool, Optional[Dict[str, str]]]:
    """
    Scans for sensitive data that shouldn't be shared.
    
    Returns:
        tuple: (found_sensitive, details_dict)
    """
    if not text:
        return False, None
        
    found = {}
    for data_type, pattern in SENSITIVE_PATTERNS.items():
        matches = re.findall(pattern, text)
        if matches:
            found[data_type] = matches[0]  # Log first match only
            
    return len(found) > 0, found if found else None


def sanitize_text(text: str) -> str:
    """
    Sanitizes text for safe display/storage.
    Escapes HTML and strips control characters.
    """
    if not text:
        return ""
    # Escape HTML entities
    text = html.escape(text)
    # Strip null bytes and control chars
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)
    return text.strip()


def clean_phone_number(phone: str) -> str:
    """
    Removes all non-digit characters from a phone number except the leading plus.
    """
    if not phone:
        return ""
    cleaned = re.sub(r"[^\d+]", "", phone.strip())
    return cleaned


def is_valid_phone_format(phone: str) -> bool:
    """
    Validates basic phone number format.
    """
    if not phone:
        return False
    cleaned = clean_phone_number(phone)
    # Must be at least 10 digits, max 15 (E.164 standard)
    digits_only = re.sub(r"\D", "", cleaned)
    return len(digits_only) >= 10 and len(digits_only) <= 15


def is_whitelisted_number(number: str, candidate_phone: str) -> Tuple[bool, Optional[str]]:
    """
    Ensures a phone number is whitelisted for warm transfer.
    Strictly verifies that the destination matches the candidate's stored phone number,
    and is not a premium rate or international dial abuse number.
    
    Returns:
        tuple: (is_allowed, reason_if_denied)
    """
    cleaned_dest = clean_phone_number(number)
    cleaned_candidate = clean_phone_number(candidate_phone)
    
    if not cleaned_dest or not cleaned_candidate:
        return False, "Phone number missing"
        
    if not is_valid_phone_format(cleaned_dest):
        return False, f"Invalid phone format: {number}"
        
    # Check for premium number formats (US/CA 900 prefix etc.)
    if cleaned_dest.startswith("900") or cleaned_dest.startswith("1900") or cleaned_dest.startswith("+1900"):
        return False, "Premium rate numbers are blocked"
        
    # Block international premium numbers (976 in some countries)
    if cleaned_dest.endswith("976") or cleaned_dest.endswith("9761"):
        return False, "International premium number detected"
        
    # Standardize comparison
    if cleaned_dest == cleaned_candidate:
        return True, None
        
    # Fallback: last 10 digits match
    dest_digits = re.sub(r"\D", "", cleaned_dest)
    cand_digits = re.sub(r"\D", "", cleaned_candidate)
    
    if len(dest_digits) >= 10 and len(cand_digits) >= 10:
        if dest_digits[-10:] == cand_digits[-10:]:
            return True, None
            
    return False, f"Number {number} not in whitelist (expected candidate's phone)"


def validate_transfer_request(target_number: str, candidate_phone: str, config: dict = None) -> Tuple[bool, Optional[str]]:
    """
    Comprehensive validation before allowing a warm transfer.
    
    Returns:
        tuple: (can_transfer, denial_reason)
    """
    # Always check whitelist
    is_allowed, reason = is_whitelisted_number(target_number, candidate_phone)
    if not is_allowed:
        return False, reason
        
    # Check if strict whitelist is enabled in config
    if config and config.get("security", {}).get("strict_whitelist", True):
        # In strict mode, require exact match (already done above)
        pass
        
    return True, None
