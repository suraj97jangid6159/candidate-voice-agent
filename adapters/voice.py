import httpx
import traceback
from .base import STTAdapter, TTSAdapter
from .utils import is_valid_api_key, validate_nonempty_text, with_retries


class DeepgramSTT(STTAdapter):
    def __init__(self, api_key: str, timeout_seconds: float = 30.0, max_retries: int = 2):
        self.api_key = api_key
        self.url = "https://api.deepgram.com/v1/listen"
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries

    async def speech_to_text(self, audio_data: bytes) -> str:
        if not is_valid_api_key(self.api_key):
            raise ValueError("Deepgram API key is missing or invalid.")

        headers = {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": "audio/wav",
        }
        params = {"model": "nova-2", "smart_format": "true"}

        async def _request():
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(
                    self.url, headers=headers, params=params, content=audio_data
                )
                if response.status_code != 200:
                    raise httpx.HTTPStatusError(
                        f"Deepgram HTTP Error {response.status_code}: {response.text}",
                        request=response.request,
                        response=response,
                    )
                data = response.json()
                channels = data.get("results", {}).get("channels", [])
                if channels:
                    alternatives = channels[0].get("alternatives", [])
                    if alternatives:
                        return validate_nonempty_text(
                            alternatives[0].get("transcript", ""), "STT transcript"
                        )
                raise ValueError("Deepgram returned empty transcript")

        return await with_retries(_request, max_retries=self.max_retries)


class WhisperLocalSTT(STTAdapter):
    def __init__(self, api_key: str = None, timeout_seconds: float = 30.0, max_retries: int = 2):
        self.api_key = api_key
        self.url = "https://api.openai.com/v1/audio/transcriptions"
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries

    async def speech_to_text(self, audio_data: bytes) -> str:
        if is_valid_api_key(self.api_key):
            headers = {"Authorization": f"Bearer {self.api_key}"}
            files = {"file": ("audio.wav", audio_data, "audio/wav")}
            data = {"model": "whisper-1"}

            async def _request():
                async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                    response = await client.post(
                        self.url, headers=headers, files=files, data=data
                    )
                    if response.status_code != 200:
                        raise httpx.HTTPStatusError(
                            f"Whisper HTTP Error {response.status_code}: {response.text}",
                            request=response.request,
                            response=response,
                        )
                    return validate_nonempty_text(
                        response.json().get("text", ""), "STT transcript"
                    )

            return await with_retries(_request, max_retries=self.max_retries)

        raise ValueError("Whisper STT: no valid API key configured")


class ElevenLabsTTS(TTSAdapter):
    def __init__(
        self,
        api_key: str,
        voice_id: str = "21m00Tcm4TlvDq8ikWAM",
        timeout_seconds: float = 30.0,
        max_retries: int = 2,
    ):
        self.api_key = api_key
        self.voice_id = voice_id
        self.url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries

    async def text_to_speech(self, text: str) -> bytes:
        if not is_valid_api_key(self.api_key):
            raise ValueError("ElevenLabs API key is missing or invalid.")
        if not text or not text.strip():
            raise ValueError("TTS input text cannot be empty")

        headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json",
            "accept": "audio/mpeg",
        }
        payload = {
            "text": text,
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
        }

        async def _request():
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(self.url, headers=headers, json=payload)
                if response.status_code != 200:
                    raise httpx.HTTPStatusError(
                        f"ElevenLabs HTTP Error {response.status_code}: {response.text}",
                        request=response.request,
                        response=response,
                    )
                if not response.content:
                    raise ValueError("ElevenLabs returned empty audio")
                return response.content

        return await with_retries(_request, max_retries=self.max_retries)


class PlayHTTTS(TTSAdapter):
    def __init__(
        self,
        api_key: str,
        user_id: str,
        voice_id: str = "larry",
        timeout_seconds: float = 30.0,
        max_retries: int = 2,
    ):
        self.api_key = api_key
        self.user_id = user_id
        self.voice_id = voice_id
        self.url = "https://api.play.ht/api/v2/tts"
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries

    async def text_to_speech(self, text: str) -> bytes:
        if not is_valid_api_key(self.api_key) or not self.user_id:
            raise ValueError("PlayHT credentials are missing or invalid.")
        if not text or not text.strip():
            raise ValueError("TTS input text cannot be empty")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "X-User-Id": self.user_id,
            "Content-Type": "application/json",
        }
        payload = {"text": text, "voice": self.voice_id, "output_format": "mp3"}

        async def _request():
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(self.url, headers=headers, json=payload)
                if response.status_code not in (200, 201):
                    raise httpx.HTTPStatusError(
                        f"PlayHT HTTP Error {response.status_code}: {response.text}",
                        request=response.request,
                        response=response,
                    )
                data = response.json()
                audio_url = data.get("_links", [{}])[0].get("href") or data.get("audioUrl")
                if not audio_url:
                    raise ValueError("Play.ht returned no audio link")
                audio_res = await client.get(audio_url)
                if not audio_res.content:
                    raise ValueError("Play.ht audio download returned empty content")
                return audio_res.content

        return await with_retries(_request, max_retries=self.max_retries)


class EdgeTTS(TTSAdapter):
    def __init__(self, voice: str = "en-US-EmmaMultilingualNeural", max_retries: int = 2):
        self.voice = voice
        self.max_retries = max_retries

    async def text_to_speech(self, text: str) -> bytes:
        if not text or not text.strip():
            raise ValueError("TTS input text cannot be empty")

        async def _request():
            import edge_tts

            communicate = edge_tts.Communicate(text, self.voice)
            audio_bytes = b""
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_bytes += chunk["data"]
            if not audio_bytes:
                raise ValueError("EdgeTTS returned empty audio")
            return audio_bytes

        return await with_retries(_request, max_retries=self.max_retries)


class MockVoiceAdapter(STTAdapter, TTSAdapter):
    async def speech_to_text(self, audio_data: bytes) -> str:
        if not audio_data:
            raise ValueError("Empty audio data")
        return "Hello. This is the hiring manager. Tell me about the candidate."

    async def text_to_speech(self, text: str) -> bytes:
        wav_header = (
            b"RIFF\x24\x08\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00"
            b"\x22\x56\x00\x00\x22\x56\x00\x00\x01\x00\x08\x00data\x00\x08\x00\x00"
            b"\x80\x80\x80\x80\x80\x80\x80\x80"
        )
        return wav_header


class FallbackSTTAdapter(STTAdapter):
    def __init__(self, primary: STTAdapter, fallback: STTAdapter):
        self.primary = primary
        self.fallback = fallback

    async def speech_to_text(self, audio_data: bytes) -> str:
        try:
            return await self.primary.speech_to_text(audio_data)
        except Exception as e:
            print(f"Primary STT failed: {e}. Trying fallback...")
            try:
                return await self.fallback.speech_to_text(audio_data)
            except Exception as e2:
                print(f"Fallback STT failed: {e2}")
                mock = MockVoiceAdapter()
                return await mock.speech_to_text(audio_data)


class FallbackTTSAdapter(TTSAdapter):
    def __init__(self, primary: TTSAdapter, fallback: TTSAdapter):
        self.primary = primary
        self.fallback = fallback

    async def text_to_speech(self, text: str) -> bytes:
        try:
            return await self.primary.text_to_speech(text)
        except Exception as e:
            print(f"Primary TTS failed: {e}. Trying fallback...")
            try:
                return await self.fallback.text_to_speech(text)
            except Exception as e2:
                print(f"Fallback TTS failed: {e2}")
                mock = MockVoiceAdapter()
                return await mock.text_to_speech(text)
