"""Small provider boundary; no automatic retries or provider response logging."""
import asyncio
import json
from typing import Protocol
import httpx
from backend.app.core.config import Settings


class ProviderFailure(Exception):
    def __init__(self, code: str, retryable: bool = False):
        super().__init__(code)
        self.code, self.retryable = code, retryable


class Provider(Protocol):
    async def generate(self, messages: list[dict[str, str]]) -> str: ...


class DeepSeek:
    def __init__(self, settings: Settings, client: httpx.AsyncClient):
        self.settings, self.client = settings, client

    async def generate(self, messages: list[dict[str, str]]) -> str:
        try:
            return await asyncio.wait_for(self._request(messages), self.settings.provider_timeout_seconds)
        except (TimeoutError, httpx.TimeoutException) as exc:
            raise ProviderFailure('provider_timeout', True) from exc
        except httpx.HTTPError as exc:
            raise ProviderFailure('provider_unavailable', True) from exc

    async def _request(self, messages):
        async with self.client.stream('POST', 'https://api.deepseek.com/chat/completions',
            headers={'Authorization': 'Bearer ' + self.settings.deepseek_api_key.get_secret_value()},
            json={'model': self.settings.deepseek_model, 'messages': messages, 'stream': False,
                  'max_tokens': self.settings.max_output_tokens, 'temperature': 0.2,
                  'thinking': {'type': 'disabled'}, 'response_format': {'type': 'json_object'}},
            timeout=self.settings.provider_timeout_seconds, follow_redirects=False) as response:
            if response.status_code != 200:
                code = 'provider_rate_limit' if response.status_code == 429 else 'provider_unavailable'
                raise ProviderFailure(code, response.status_code == 429 or response.status_code >= 500)
            body = bytearray()
            async for part in response.aiter_bytes():
                body.extend(part)
                if len(body) > 65536:
                    raise ProviderFailure('provider_response_too_large')
        try:
            choice = json.loads(body)['choices'][0]
            content = choice['message']['content']
            if choice['finish_reason'] != 'stop' or not isinstance(content, str) or not content.strip():
                raise ValueError('Incomplete response')
            return content
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise ProviderFailure('provider_invalid_response') from exc
