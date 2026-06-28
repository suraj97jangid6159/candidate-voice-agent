import httpx
import json
import traceback
import asyncio
import os
from .base import LLMAdapter

class OpenRouterAdapter(LLMAdapter):
    def __init__(self, api_key: str, model: str = "meta-llama/llama-3-70b-instruct", max_retries: int = 2):
        self.api_key = api_key
        self.model = model
        self.url = "https://openrouter.ai/api/v1/chat/completions"
        self.max_retries = max_retries

    async def generate_response(self, system_prompt: str, user_message: str, history: list = None) -> str:
        if not self.api_key or "YOUR_" in self.api_key or not self.api_key.strip():
            raise ValueError("OpenRouter API key is missing or default placeholder.")
            
        history = history or []
        messages = [{"role": "system", "content": system_prompt}]
        for item in history:
            messages.append(item)
        messages.append({"role": "user", "content": user_message})

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/ai-voice-agent",
            "X-Title": "AI Voice Agent"
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.3,
            "max_tokens": 512
        }

        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(self.url, headers=headers, json=payload)
                    if response.status_code == 429:  # Rate limit
                        wait_time = 2 ** attempt  # Exponential backoff
                        await asyncio.sleep(wait_time)
                        continue
                    if response.status_code != 200:
                        raise httpx.HTTPStatusError(f"HTTP Error {response.status_code}: {response.text}", request=response.request, response=response)
                    
                    data = response.json()
                    return data["choices"][0]["message"]["content"]
            except Exception as e:
                last_error = e
                if attempt < self.max_retries:
                    wait_time = 2 ** attempt
                    await asyncio.sleep(wait_time)
                continue
        
        raise last_error or Exception("OpenRouter: Max retries exceeded")

class OpenAIAdapter(LLMAdapter):
    def __init__(self, api_key: str, model: str = "gpt-4o-mini", max_retries: int = 2):
        self.api_key = api_key
        self.model = model
        self.url = "https://api.openai.com/v1/chat/completions"
        self.max_retries = max_retries

    async def generate_response(self, system_prompt: str, user_message: str, history: list = None) -> str:
        if not self.api_key or "YOUR_" in self.api_key or not self.api_key.strip():
            raise ValueError("OpenAI API key is missing.")
            
        history = history or []
        messages = [{"role": "system", "content": system_prompt}]
        for item in history:
            messages.append(item)
        messages.append({"role": "user", "content": user_message})

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.3,
            "max_tokens": 512
        }

        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(self.url, headers=headers, json=payload)
                    if response.status_code == 429:
                        wait_time = 2 ** attempt
                        await asyncio.sleep(wait_time)
                        continue
                    if response.status_code != 200:
                        raise httpx.HTTPStatusError(f"HTTP Error {response.status_code}: {response.text}", request=response.request, response=response)
                    
                    data = response.json()
                    return data["choices"][0]["message"]["content"]
            except Exception as e:
                last_error = e
                if attempt < self.max_retries:
                    wait_time = 2 ** attempt
                    await asyncio.sleep(wait_time)
                continue
        
        raise last_error or Exception("OpenAI: Max retries exceeded")

class AnthropicAdapter(LLMAdapter):
    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20240620", max_retries: int = 2):
        self.api_key = api_key
        self.model = model
        self.url = "https://api.anthropic.com/v1/messages"
        self.max_retries = max_retries

    async def generate_response(self, system_prompt: str, user_message: str, history: list = None) -> str:
        if not self.api_key or "YOUR_" in self.api_key or not self.api_key.strip():
            raise ValueError("Anthropic API key is missing.")
            
        history = history or []
        messages = []
        for item in history:
            messages.append(item)
        messages.append({"role": "user", "content": user_message})

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "system": system_prompt,
            "messages": messages,
            "max_tokens": 512,
            "temperature": 0.3
        }

        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(self.url, headers=headers, json=payload)
                    if response.status_code != 200:
                        raise httpx.HTTPStatusError(f"HTTP Error {response.status_code}: {response.text}", request=response.request, response=response)
                    
                    data = response.json()
                    return data["content"][0]["text"]
            except Exception as e:
                last_error = e
                if attempt < self.max_retries:
                    wait_time = 2 ** attempt
                    await asyncio.sleep(wait_time)
                continue
        
        raise last_error or Exception("Anthropic: Max retries exceeded")

class GeminiAdapter(LLMAdapter):
    def __init__(self, api_key: str, model: str = "gemini-1.5-flash", max_retries: int = 2):
        self.api_key = api_key
        self.model = model
        self.url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        self.max_retries = max_retries

    async def generate_response(self, system_prompt: str, user_message: str, history: list = None) -> str:
        if not self.api_key or "YOUR_" in self.api_key or not self.api_key.strip():
            raise ValueError("Gemini API key is missing.")
            
        contents = []
        
        contents.append({
            "role": "user",
            "parts": [{"text": f"SYSTEM INSTRUCTION: {system_prompt}"}]
        })
        contents.append({
            "role": "model",
            "parts": [{"text": "Understood. I will act according to these system instructions."}]
        })
        
        history = history or []
        for item in history:
            role = "user" if item["role"] == "user" else "model"
            contents.append({
                "role": role,
                "parts": [{"text": item["content"]}]
            })
            
        contents.append({
            "role": "user",
            "parts": [{"text": user_message}]
        })

        params = {"key": self.api_key}
        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": 0.3,
                "maxOutputTokens": 512
            }
        }

        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(self.url, params=params, json=payload)
                    if response.status_code != 200:
                        raise httpx.HTTPStatusError(f"HTTP Error {response.status_code}: {response.text}", request=response.request, response=response)
                    
                    data = response.json()
                    return data["candidates"][0]["content"]["parts"][0]["text"]
            except Exception as e:
                last_error = e
                if attempt < self.max_retries:
                    wait_time = 2 ** attempt
                    await asyncio.sleep(wait_time)
                continue
        
        raise last_error or Exception("Gemini: Max retries exceeded")

class KimiAdapter(LLMAdapter):
    def __init__(self, api_key: str, model: str = "moonshot-v1-8k", max_retries: int = 2):
        self.api_key = api_key
        self.model = model
        self.url = "https://api.moonshot.cn/v1/chat/completions"
        self.max_retries = max_retries

    async def generate_response(self, system_prompt: str, user_message: str, history: list = None) -> str:
        if not self.api_key or "YOUR_" in self.api_key or not self.api_key.strip():
            raise ValueError("Kimi/Moonshot API key is missing.")
            
        history = history or []
        messages = [{"role": "system", "content": system_prompt}]
        for item in history:
            messages.append(item)
        messages.append({"role": "user", "content": user_message})

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.3,
            "max_tokens": 512
        }

        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(self.url, headers=headers, json=payload)
                    if response.status_code != 200:
                        raise httpx.HTTPStatusError(f"HTTP Error {response.status_code}: {response.text}", request=response.request, response=response)
                    
                    data = response.json()
                    return data["choices"][0]["message"]["content"]
            except Exception as e:
                last_error = e
                if attempt < self.max_retries:
                    wait_time = 2 ** attempt
                    await asyncio.sleep(wait_time)
                continue
        
        raise last_error or Exception("Kimi: Max retries exceeded")

class MockLLMAdapter(LLMAdapter):
    def __init__(self, candidate_info: dict = None, job_info: dict = None):
        self.candidate_info = candidate_info or {
            "name": "Alex Mercer",
            "phone": "+15550199",
            "current_ctc": "$90,000",
            "expected_ctc": "$110,000",
            "notice_period": "30 days",
            "skills": "Python, FastAPI, AWS, Docker"
        }
        self.job_info = job_info or {
            "company_name": "Tech Corp",
            "job_title": "Backend Engineer"
        }

    async def generate_response(self, system_prompt: str, user_message: str, history: list = None) -> str:
        msg = user_message.lower()
        cand_name = self.candidate_info.get("name", "the candidate")
        job_title = self.job_info.get("job_title", "Software Engineer")
        company = self.job_info.get("company_name", "your company")
        
        # Opening / Greeting — only when the turn is an initial outreach
        if "is this a good time" in system_prompt.lower() or (
            not history and user_message.lower().strip() in ("", "start")
        ):
            return f"Hello, I am the virtual representative calling on behalf of {cand_name}. I'm reaching out regarding the {job_title} vacancy at {company}. Is this a good time to speak briefly?"
        
        # Busy / Call later
        if any(k in msg for k in ["busy", "call later", "no time", "meeting", "driving"]):
            return f"I completely understand you're busy. Could we schedule a brief call for tomorrow at 11 AM, or is there another time that works better?"
            
        # Positive response / Go ahead
        if any(k in msg for k in ["yes", "go ahead", "sure", "tell me", "pitch", "interested"]):
            skills = self.candidate_info.get("skills", "software engineering")
            return f"Fantastic! {cand_name} is a skilled professional with extensive expertise in {skills}. They are highly interested in the {job_title} role because their background matches your requirements perfectly. Would you like to review their details or ask some screening questions?"
            
        # Salary / CTC
        if any(k in msg for k in ["salary", "package", "ctc", "compensation", "pay"]):
            current = self.candidate_info.get("current_ctc", "Not Specified")
            expected = self.candidate_info.get("expected_ctc", "Not Specified")
            return f"Regarding compensation, {cand_name}'s current CTC is {current}, and they are looking for an expected CTC of around {expected}, which is negotiable based on the overall role benefits. Does that align with your budget?"
            
        # Notice period / Availability
        if any(k in msg for k in ["notice", "join", "start", "available"]):
            np = self.candidate_info.get("notice_period", "Immediate")
            return f"{cand_name} has a notice period of {np}. They can wrap up their current responsibilities and join within this timeframe, or potentially sooner if there's an option for notice buyout."

        # Transfer / Connect / Interview
        if any(k in msg for k in ["transfer", "connect", "talk to", "speak with", "interview", "schedule"]):
            return f"That sounds great! I would love to warm-transfer this call directly to {cand_name} right now so you can speak to them for a quick introduction. Would that be fine with you?"

        # Default fallback QA
        return f"Regarding that, {cand_name} has hands-on experience in their profile and has handled similar scenarios in past projects. If you would like, we can arrange a direct technical interview or I can transfer you to {cand_name} now. Would you like me to transfer the call?"


class FallbackLLMAdapter(LLMAdapter):
    def __init__(self, primary: LLMAdapter, fallback: LLMAdapter):
        self.primary = primary
        self.fallback = fallback

    async def generate_response(self, system_prompt: str, user_message: str, history: list = None) -> str:
        try:
            return await self.primary.generate_response(system_prompt, user_message, history)
        except Exception as e:
            print(f"Primary LLM failed with: {e}. Attempting fallback...")
            try:
                return await self.fallback.generate_response(system_prompt, user_message, history)
            except Exception as e2:
                print(f"Fallback LLM also failed: {e2}")
                mock = MockLLMAdapter()
                return await mock.generate_response(system_prompt, user_message, history)
