import os
import yaml
from dotenv import load_dotenv
from .base import LLMAdapter, STTAdapter, TTSAdapter, TelephonyAdapter
from .llm import (
    OpenRouterAdapter, OpenAIAdapter, AnthropicAdapter, 
    GeminiAdapter, KimiAdapter, MockLLMAdapter, FallbackLLMAdapter
)
from .voice import (
    DeepgramSTT, WhisperLocalSTT, ElevenLabsTTS, 
    PlayHTTTS, EdgeTTS, MockVoiceAdapter, 
    FallbackSTTAdapter, FallbackTTSAdapter
)
from .telephony import TwilioTelephony, VapiTelephony, MockTelephony, FallbackTelephonyAdapter

# Load environment variables
load_dotenv()

def load_config():
    """
    Load configuration from config.yaml and merge with environment variables.
    Environment variables take precedence over config file values.
    """
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.yaml")
    config = {}
    
    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f) or {}
    except Exception as e:
        print(f"Warning: Error loading config.yaml: {e}")
        config = {}
    
    # Override with environment variables
    config["app"] = config.get("app", {})
    config["app"]["port"] = int(os.getenv("APP_PORT", config["app"].get("port", 8000)))
    config["app"]["host"] = os.getenv("APP_HOST", config["app"].get("host", "127.0.0.1"))
    config["app"]["db_path"] = os.getenv("APP_DB_PATH", config["app"].get("db_path", "database.db"))
    config["app"]["mock_mode"] = os.getenv("APP_MOCK_MODE", str(config["app"].get("mock_mode", True))).lower() == "true"
    config["app"]["log_level"] = os.getenv("LOG_LEVEL", config["app"].get("log_level", "INFO"))
    config["app"]["max_call_duration_minutes"] = int(os.getenv("SECURITY_MAX_CALL_DURATION_MINUTES", 
                                                                  config["app"].get("max_call_duration_minutes", 30)))
    
    config["credentials"] = {
        "openrouter_api_key": os.getenv("OPENROUTER_API_KEY", ""),
        "openai_api_key": os.getenv("OPENAI_API_KEY", ""),
        "anthropic_api_key": os.getenv("ANTHROPIC_API_KEY", ""),
        "gemini_api_key": os.getenv("GEMINI_API_KEY", os.getenv("OPENAI_API_KEY", "")),
        "kimi_api_key": os.getenv("KIMI_API_KEY", os.getenv("OPENAI_API_KEY", "")),
        "deepgram_api_key": os.getenv("DEEPGRAM_API_KEY", ""),
        "elevenlabs_api_key": os.getenv("ELEVENLABS_API_KEY", ""),
        "playht_api_key": os.getenv("PLAYHT_API_KEY", ""),
        "playht_user_id": os.getenv("PLAYHT_USER_ID", ""),
        "vapi_api_key": os.getenv("VAPI_API_KEY", ""),
        "twilio_account_sid": os.getenv("TWILIO_ACCOUNT_SID", ""),
        "twilio_auth_token": os.getenv("TWILIO_AUTH_TOKEN", ""),
        "twilio_phone_number": os.getenv("TWILIO_PHONE_NUMBER", ""),
        "telnyx_api_key": os.getenv("TELNYX_API_KEY", ""),
        "sendgrid_api_key": os.getenv("SENDGRID_API_KEY", ""),
        "sendgrid_from_email": os.getenv("SENDGRID_FROM_EMAIL", "noreply@voiceagent.local"),
    }
    
    config["security"] = config.get("security", {})
    config["security"]["strict_whitelist"] = os.getenv("SECURITY_STRICT_WHITELIST", 
                                                        str(config["security"].get("strict_whitelist", True))).lower() == "true"
    config["security"]["block_agreements"] = os.getenv("SECURITY_BLOCK_AGREEMENTS", 
                                                        str(config["security"].get("block_agreements", True))).lower() == "true"
    config["security"]["log_all_events"] = os.getenv("SECURITY_LOG_ALL_EVENTS", 
                                                      str(config["security"].get("log_all_events", True))).lower() == "true"
    config["security"]["scan_inputs"] = os.getenv("SECURITY_SCAN_INPUTS",
                                                   str(config["security"].get("scan_inputs", True))).lower() == "true"
    
    return config


def _adapter_settings(config, adapter_type):
    """Read timeout and retry settings for a given adapter type from config."""
    cfg = config.get("adapters", {}).get(adapter_type, {})
    return {
        "timeout_seconds": float(cfg.get("timeout_seconds", 30)),
        "max_retries": int(cfg.get("max_retries", 2)),
    }


def get_llm_adapter(config=None, candidate_info=None, job_info=None):
    config = config or load_config()
    mock_mode = config.get("app", {}).get("mock_mode", False)
    
    if mock_mode:
        return MockLLMAdapter(candidate_info, job_info)
        
    adapters_cfg = config.get("adapters", {}).get("llm", {})
    primary_name = adapters_cfg.get("primary", "mock")
    fallback_name = adapters_cfg.get("fallback", "mock")
    model = adapters_cfg.get("model", "meta-llama/llama-3-70b-instruct")
    llm_settings = _adapter_settings(config, "llm")
    
    creds = config.get("credentials", {})
    
    def create_adapter(name):
        kwargs = {"max_retries": llm_settings["max_retries"]}
        if name == "openrouter":
            return OpenRouterAdapter(creds.get("openrouter_api_key", ""), model, **kwargs)
        elif name == "openai":
            return OpenAIAdapter(creds.get("openai_api_key", ""), **kwargs)
        elif name == "anthropic":
            return AnthropicAdapter(creds.get("anthropic_api_key", ""), **kwargs)
        elif name == "gemini":
            return GeminiAdapter(creds.get("gemini_api_key", ""), **kwargs)
        elif name == "kimi":
            return KimiAdapter(creds.get("kimi_api_key", ""), **kwargs)
        else:
            return MockLLMAdapter(candidate_info, job_info)
            
    primary_adapter = create_adapter(primary_name)
    fallback_adapter = create_adapter(fallback_name)
    
    return FallbackLLMAdapter(primary_adapter, fallback_adapter)


def get_stt_adapter(config=None):
    config = config or load_config()
    mock_mode = config.get("app", {}).get("mock_mode", False)
    
    if mock_mode:
        return MockVoiceAdapter()
        
    adapters_cfg = config.get("adapters", {}).get("stt", {})
    primary_name = adapters_cfg.get("primary", "mock")
    fallback_name = adapters_cfg.get("fallback", "mock")
    stt_settings = _adapter_settings(config, "stt")
    creds = config.get("credentials", {})
    
    def create_adapter(name):
        kwargs = {
            "timeout_seconds": stt_settings["timeout_seconds"],
            "max_retries": stt_settings["max_retries"],
        }
        if name == "deepgram":
            return DeepgramSTT(creds.get("deepgram_api_key", ""), **kwargs)
        elif name == "whisper-local":
            return WhisperLocalSTT(creds.get("openai_api_key", ""), **kwargs)
        else:
            return MockVoiceAdapter()
            
    primary_adapter = create_adapter(primary_name)
    fallback_adapter = create_adapter(fallback_name)
    
    return FallbackSTTAdapter(primary_adapter, fallback_adapter)


def get_tts_adapter(config=None):
    config = config or load_config()
    mock_mode = config.get("app", {}).get("mock_mode", False)
    
    if mock_mode:
        return MockVoiceAdapter()
        
    adapters_cfg = config.get("adapters", {}).get("tts", {})
    primary_name = adapters_cfg.get("primary", "mock")
    fallback_name = adapters_cfg.get("fallback", "mock")
    tts_settings = _adapter_settings(config, "tts")
    creds = config.get("credentials", {})
    
    def create_adapter(name):
        kwargs = {
            "timeout_seconds": tts_settings["timeout_seconds"],
            "max_retries": tts_settings["max_retries"],
        }
        if name == "elevenlabs":
            return ElevenLabsTTS(creds.get("elevenlabs_api_key", ""), **kwargs)
        elif name == "playht":
            return PlayHTTTS(
                creds.get("playht_api_key", ""),
                creds.get("playht_user_id", ""),
                **kwargs,
            )
        elif name == "edge-tts":
            return EdgeTTS(max_retries=tts_settings["max_retries"])
        else:
            return MockVoiceAdapter()
            
    primary_adapter = create_adapter(primary_name)
    fallback_adapter = create_adapter(fallback_name)
    
    return FallbackTTSAdapter(primary_adapter, fallback_adapter)


def get_telephony_adapter(config=None):
    config = config or load_config()
    mock_mode = config.get("app", {}).get("mock_mode", False)
    
    if mock_mode:
        return MockTelephony()
        
    adapters_cfg = config.get("adapters", {}).get("telephony", {})
    primary_name = adapters_cfg.get("primary", "mock")
    fallback_name = adapters_cfg.get("fallback", "mock")
    tel_settings = _adapter_settings(config, "telephony")
    creds = config.get("credentials", {})
    
    def create_adapter(name):
        kwargs = {
            "timeout_seconds": tel_settings["timeout_seconds"],
            "max_retries": tel_settings.get("max_retries", 2),
        }
        if name == "vapi":
            return VapiTelephony(creds.get("vapi_api_key", ""), **kwargs)
        elif name == "twilio":
            return TwilioTelephony(
                creds.get("twilio_account_sid", ""),
                creds.get("twilio_auth_token", ""),
                creds.get("twilio_phone_number", ""),
                **kwargs,
            )
        else:
            return MockTelephony()
            
    primary_adapter = create_adapter(primary_name)
    fallback_adapter = create_adapter(fallback_name)
    
    if primary_name == fallback_name or fallback_name == "mock":
        return primary_adapter
    return FallbackTelephonyAdapter(primary_adapter, fallback_adapter)

__all__ = [
    "LLMAdapter", "STTAdapter", "TTSAdapter", "TelephonyAdapter",
    "load_config", "get_llm_adapter", "get_stt_adapter", 
    "get_tts_adapter", "get_telephony_adapter"
]
