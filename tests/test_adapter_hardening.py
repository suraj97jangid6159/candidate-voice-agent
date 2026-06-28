import os
import sys
import asyncio
from unittest import mock

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from adapters.utils import is_valid_api_key, validate_nonempty_text, with_retries
from adapters.telephony import MockTelephony, FallbackTelephonyAdapter, TwilioTelephony
from adapters.voice import MockVoiceAdapter, FallbackTTSAdapter, EdgeTTS, ElevenLabsTTS
from adapters import load_config, get_telephony_adapter, get_tts_adapter


class TestAdapterValidation:
    def test_rejects_placeholder_api_keys(self):
        assert is_valid_api_key("") is False
        assert is_valid_api_key("YOUR_OPENROUTER_KEY") is False
        assert is_valid_api_key("sk-real-key-abc123") is True

    def test_validate_nonempty_text_raises_on_empty(self):
        with pytest.raises(ValueError, match="Empty"):
            validate_nonempty_text("   ", "response")
        assert validate_nonempty_text("hello") == "hello"


class TestRetryUtility:
    @pytest.mark.asyncio
    async def test_retries_then_succeeds(self):
        attempts = {"count": 0}

        async def flaky():
            attempts["count"] += 1
            if attempts["count"] < 2:
                raise ConnectionError("temporary failure")
            return "ok"

        result = await with_retries(flaky, max_retries=2, base_delay=0.01)
        assert result == "ok"
        assert attempts["count"] == 2

    @pytest.mark.asyncio
    async def test_exhausts_retries(self):
        async def always_fail():
            raise RuntimeError("permanent failure")

        with pytest.raises(RuntimeError, match="permanent failure"):
            await with_retries(always_fail, max_retries=1, base_delay=0.01)


class TestTelephonyFallback:
    @pytest.mark.asyncio
    async def test_fallback_on_primary_failure(self):
        class FailingTelephony(MockTelephony):
            async def make_call(self, to_number, from_number, webhook_url):
                raise ConnectionError("primary down")

        primary = FailingTelephony()
        fallback = MockTelephony()
        adapter = FallbackTelephonyAdapter(primary, fallback)

        sid = await adapter.make_call("+15551234567", "+15550001111", "http://localhost/webhook")
        assert sid.startswith("MC_")

    @pytest.mark.asyncio
    async def test_twilio_rejects_missing_destination(self):
        tel = TwilioTelephony("AC123", "token", "+15550001111")
        with pytest.raises(ValueError, match="Destination"):
            await tel.make_call("", "+15550001111", "http://localhost/webhook")


class TestTTSFallback:
    @pytest.mark.asyncio
    async def test_fallback_to_edge_on_elevenlabs_failure(self):
        class FailingElevenLabs(ElevenLabsTTS):
            async def text_to_speech(self, text):
                raise ConnectionError("ElevenLabs unavailable")

        primary = FailingElevenLabs("YOUR_ELEVENLABS_KEY")
        fallback = EdgeTTS(max_retries=1)

        with mock.patch.object(EdgeTTS, "text_to_speech", new=MockVoiceAdapter().text_to_speech):
            adapter = FallbackTTSAdapter(primary, fallback)
            audio = await adapter.text_to_speech("Hello candidate pitch.")
            assert len(audio) > 0


class TestAdapterFactory:
    def test_load_config_has_retry_settings(self):
        config = load_config()
        assert config["adapters"]["llm"]["max_retries"] == 2
        assert config["adapters"]["telephony"]["timeout_seconds"] == 30

    def test_mock_mode_returns_mock_telephony(self):
        config = load_config()
        config["app"]["mock_mode"] = True
        adapter = get_telephony_adapter(config)
        assert isinstance(adapter, MockTelephony)

    def test_tts_fallback_chain_in_mock_off_mode(self):
        config = load_config()
        config["app"]["mock_mode"] = False
        config["adapters"]["tts"]["primary"] = "elevenlabs"
        config["adapters"]["tts"]["fallback"] = "edge-tts"
        adapter = get_tts_adapter(config)
        assert isinstance(adapter, FallbackTTSAdapter)
