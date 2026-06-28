import httpx
import uuid
from .base import TelephonyAdapter
from .utils import is_valid_api_key, with_retries


class TwilioTelephony(TelephonyAdapter):
    def __init__(
        self,
        account_sid: str,
        auth_token: str,
        from_number: str,
        timeout_seconds: float = 30.0,
        max_retries: int = 2,
    ):
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.from_number = from_number
        self.base_url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Calls.json"
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries

    def _validate_number(self, number: str, label: str) -> str:
        if not number or not number.strip():
            raise ValueError(f"{label} phone number is required")
        return number.strip()

    async def make_call(self, to_number: str, from_number: str, webhook_url: str) -> str:
        if not is_valid_api_key(self.account_sid) or not is_valid_api_key(self.auth_token):
            raise ValueError("Twilio credentials are not configured.")
        to_number = self._validate_number(to_number, "Destination")
        if not webhook_url:
            raise ValueError("Webhook URL is required for outbound calls")

        from_num = from_number or self.from_number
        payload = {"To": to_number, "From": from_num, "Url": webhook_url, "Method": "POST"}
        auth = (self.account_sid, self.auth_token)

        async def _request():
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(self.base_url, data=payload, auth=auth)
                if response.status_code != 201:
                    raise httpx.HTTPStatusError(
                        f"Twilio Call Error {response.status_code}: {response.text}",
                        request=response.request,
                        response=response,
                    )
                sid = response.json().get("sid", "")
                if not sid:
                    raise ValueError("Twilio returned empty call SID")
                return sid

        return await with_retries(_request, max_retries=self.max_retries)

    async def transfer_call(self, session_id: str, target_number: str) -> bool:
        if not self.account_sid:
            raise ValueError("Twilio account SID is missing.")
        target_number = self._validate_number(target_number, "Transfer target")

        redirect_url = (
            f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Calls/{session_id}.json"
        )
        twiml = f"<Response><Dial><Number>{target_number}</Number></Dial></Response>"
        payload = {"Twiml": twiml}
        auth = (self.account_sid, self.auth_token)

        async def _request():
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(redirect_url, data=payload, auth=auth)
                if response.status_code != 200:
                    raise httpx.HTTPStatusError(
                        f"Twilio Transfer Error {response.status_code}: {response.text}",
                        request=response.request,
                        response=response,
                    )
                return True

        return await with_retries(_request, max_retries=self.max_retries)


class VapiTelephony(TelephonyAdapter):
    def __init__(self, api_key: str, timeout_seconds: float = 30.0, max_retries: int = 2):
        self.api_key = api_key
        self.base_url = "https://api.vapi.ai/call"
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries

    async def make_call(self, to_number: str, from_number: str, webhook_url: str) -> str:
        if not is_valid_api_key(self.api_key):
            raise ValueError("Vapi API key is missing or invalid.")
        if not to_number or not to_number.strip():
            raise ValueError("Destination phone number is required")
        if not webhook_url:
            raise ValueError("Webhook URL is required for Vapi calls")

        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {
            "type": "outboundPhoneCall",
            "phoneNumberId": from_number,
            "customer": {"number": to_number},
            "assistant": {
                "firstMessage": (
                    "Hello. I am the virtual assistant calling on behalf of the candidate. "
                    "Is this a good time to talk?"
                ),
                "model": {"provider": "custom-llm", "url": webhook_url},
            },
        }

        async def _request():
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(self.base_url, headers=headers, json=payload)
                if response.status_code != 201:
                    raise httpx.HTTPStatusError(
                        f"Vapi Call Error {response.status_code}: {response.text}",
                        request=response.request,
                        response=response,
                    )
                call_id = response.json().get("id", "")
                if not call_id:
                    raise ValueError("Vapi returned empty call ID")
                return call_id

        return await with_retries(_request, max_retries=self.max_retries)

    async def transfer_call(self, session_id: str, target_number: str) -> bool:
        if not is_valid_api_key(self.api_key):
            raise ValueError("Vapi API key is missing or invalid.")
        if not target_number or not target_number.strip():
            raise ValueError("Transfer target number is required")

        url = f"{self.base_url}/{session_id}/transfer"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {"destination": {"type": "number", "number": target_number}}

        async def _request():
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(url, headers=headers, json=payload)
                if response.status_code not in (200, 201):
                    raise httpx.HTTPStatusError(
                        f"Vapi Transfer Error {response.status_code}: {response.text}",
                        request=response.request,
                        response=response,
                    )
                return True

        return await with_retries(_request, max_retries=self.max_retries)


class MockTelephony(TelephonyAdapter):
    async def make_call(self, to_number: str, from_number: str, webhook_url: str) -> str:
        mock_sid = f"MC_{uuid.uuid4().hex[:16]}"
        print(f"MockTelephony: Dialing {to_number} from {from_number}. Call SID: {mock_sid}")
        return mock_sid

    async def transfer_call(self, session_id: str, target_number: str) -> bool:
        print(f"MockTelephony: Warm-transferring call {session_id} to {target_number}")
        return True


class FallbackTelephonyAdapter(TelephonyAdapter):
    def __init__(self, primary: TelephonyAdapter, fallback: TelephonyAdapter):
        self.primary = primary
        self.fallback = fallback

    async def make_call(self, to_number: str, from_number: str, webhook_url: str) -> str:
        try:
            return await self.primary.make_call(to_number, from_number, webhook_url)
        except Exception as e:
            print(f"Primary telephony failed: {e}. Trying fallback...")
            return await self.fallback.make_call(to_number, from_number, webhook_url)

    async def transfer_call(self, session_id: str, target_number: str) -> bool:
        try:
            return await self.primary.transfer_call(session_id, target_number)
        except Exception as e:
            print(f"Primary transfer failed: {e}. Trying fallback...")
            return await self.fallback.transfer_call(session_id, target_number)
