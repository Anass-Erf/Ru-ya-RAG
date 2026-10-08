import asyncio
from collections import deque
import json
import time
from starlette.concurrency import run_in_threadpool
from backend.app.schemas.api import InterpretRequest, InterpretResponse, GenerationIssue
from backend.app.rag.generation.grounding import sources_for, messages_for, validate_draft
from backend.app.rag.generation.provider import Provider, ProviderFailure


class Interpreter:
    def __init__(self, settings, library, provider: Provider):
        self.settings, self.library, self.provider = settings, library, provider
        self.calls = deque()
        self.active = 0

    async def interpret(self, request: InterpretRequest) -> InterpretResponse:
        result = await run_in_threadpool(self.library.search, request)
        sources = sources_for(result, self.settings.max_context_chars)
        base = dict(retrieval=result, sources=sources, evidence_sufficient=bool(sources))
        if not request.generate:
            return InterpretResponse(**base, status='retrieval_only', message='نتائج الاسترجاع دون توليد.')
        if not sources:
            return InterpretResponse(**base, status='insufficient_sources', message='لا توجد شواهد مراجعة كافية تطابق الرمز المذكور صراحة في الطلب.')
        if not self.settings.enable_generation or not self.settings.deepseek_api_key.get_secret_value():
            return InterpretResponse(**base, status='retrieval_only', message='التوليد غير مفعّل؛ تعرض الشواهد المتاحة فقط.')
        messages = messages_for(request.query, sources)
        issue = None
        if len(json.dumps(messages, ensure_ascii=False).encode()) > self.settings.max_prompt_bytes:
            issue = GenerationIssue(code='context_limit', message='السياق يتجاوز الحد المسموح؛ اختصر الطلب.')
        now = time.monotonic()
        while self.calls and now - self.calls[0] >= 60:
            self.calls.popleft()
        if issue is None and (len(self.calls) >= self.settings.generation_calls_per_minute or self.active >= 2):
            issue = GenerationIssue(code='generation_rate_limit', message='بلغ التوليد حد الاستخدام؛ حاول لاحقا.', retryable=True)
        if issue:
            return InterpretResponse(**base, status='generation_failed', message='تعذر التوليد؛ الشواهد متاحة.', generation_issue=issue)
        self.calls.append(now)
        self.active += 1
        try:
            content = await asyncio.wait_for(self.provider.generate(messages), self.settings.provider_timeout_seconds)
            draft, claims, differences = validate_draft(content, sources)
            return InterpretResponse(**base, status='insufficient_sources' if draft.insufficient else 'generated',
                message='الشواهد غير كافية للإجابة.' if draft.insufficient else 'تلخيص منسوب إلى الشواهد التاريخية.',
                synthesis=claims, differences=differences, provider_model=self.settings.deepseek_model)
        except (ProviderFailure, ValueError, TimeoutError) as exc:
            code = exc.code if isinstance(exc, ProviderFailure) else 'provider_timeout' if isinstance(exc, TimeoutError) else 'grounding_validation_failed'
            return InterpretResponse(**base, status='generation_failed', message='تعذر التوليد؛ الشواهد متاحة.',
                generation_issue=GenerationIssue(code=code, message='لم تتوفر إجابة مكتملة اجتازت فحص الاستشهادات.',
                    retryable=isinstance(exc, TimeoutError) or (isinstance(exc, ProviderFailure) and exc.retryable)))
        finally:
            self.active -= 1
