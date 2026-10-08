import json
import unittest
import httpx
from backend.app.core.config import Settings
from backend.app.rag.generation.provider import DeepSeek, ProviderFailure


class ProviderTests(unittest.IsolatedAsyncioTestCase):
    async def test_request_contract(self):
        def handle(request):
            self.assertEqual(str(request.url),'https://api.deepseek.com/chat/completions')
            data=json.loads(request.content)
            self.assertEqual(data['response_format'],{'type':'json_object'})
            self.assertEqual(data['max_tokens'],900)
            self.assertEqual(data['thinking'],{'type':'disabled'})
            self.assertEqual(request.headers['authorization'],'Bearer fixture-key')
            return httpx.Response(200,json={'choices':[{'finish_reason':'stop','message':{'content':'{}'}}]})
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            self.assertEqual(await DeepSeek(Settings(deepseek_api_key='fixture-key'),client).generate([]),'{}')

    async def test_rate_limits_timeouts_and_bad_responses(self):
        cases=[(429,{},'provider_rate_limit'),(401,{'secret':'never expose'},'provider_authentication'),
               (402,{},'provider_insufficient_balance'),(400,{},'provider_bad_request'),
               (404,{},'provider_model_unavailable'),(503,{},'provider_unavailable'),
               (200,{'choices':[{'finish_reason':'length','message':{'content':'{}'}}]},'provider_output_truncated'),
               (200,{'choices':[]},'provider_invalid_response')]
        for status,body,code in cases:
            async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r:httpx.Response(status,json=body))) as client:
                with self.assertRaises(ProviderFailure) as caught:
                    await DeepSeek(Settings(),client).generate([])
                self.assertEqual(caught.exception.code,code)
                self.assertNotIn('secret',str(caught.exception))
        def timeout(request):raise httpx.ReadTimeout('secret provider detail')
        async with httpx.AsyncClient(transport=httpx.MockTransport(timeout)) as client:
            with self.assertRaises(ProviderFailure) as caught:await DeepSeek(Settings(),client).generate([])
            self.assertEqual(caught.exception.code,'provider_timeout')

    async def test_response_size_cap(self):
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r:httpx.Response(200,content=b'x'*65537))) as client:
            with self.assertRaises(ProviderFailure) as caught:await DeepSeek(Settings(),client).generate([])
            self.assertEqual(caught.exception.code,'provider_response_too_large')
