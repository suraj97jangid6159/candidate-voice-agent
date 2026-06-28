from abc import ABC, abstractmethod

class LLMAdapter(ABC):
    @abstractmethod
    async def generate_response(self, system_prompt: str, user_message: str, history: list = None) -> str:
        """Generates a text response from the LLM based on system prompt, user prompt, and conversation history."""
        pass

class STTAdapter(ABC):
    @abstractmethod
    async def speech_to_text(self, audio_data: bytes) -> str:
        """Converts spoken audio data into raw text transcript."""
        pass

class TTSAdapter(ABC):
    @abstractmethod
    async def text_to_speech(self, text: str) -> bytes:
        """Converts raw text input into synthesized audio bytes (e.g. MP3/WAV)."""
        pass

class TelephonyAdapter(ABC):
    @abstractmethod
    async def make_call(self, to_number: str, from_number: str, webhook_url: str) -> str:
        """Places an outbound call to the target number. Returns call reference ID or session ID."""
        pass
        
    @abstractmethod
    async def transfer_call(self, session_id: str, target_number: str) -> bool:
        """Bridges the current call session with a target phone number (warm transfer)."""
        pass
