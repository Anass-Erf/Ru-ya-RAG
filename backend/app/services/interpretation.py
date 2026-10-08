import asyncio
from collections import deque
import json
import logging
import time
from starlette.concurrency import run_in_threadpool
from backend.app.schemas.api import InterpretRequest, InterpretResponse, GenerationIssue
from backend.app.rag.generation.grounding import sources_for, messages_for, validate_draft, GroundingFailure
from backend.app.rag.generation.provider import Provider, ProviderFailure


ISSUE_MESSAGES = {
    'provider_authentication': 'رفض DeepSeek مفتاح API. تحقق من المفتاح على الخادم ثم أعد تشغيله.',
    'provider_insufficient_balance': 'رصيد حساب DeepSeek غير كاف لإتمام الطلب. تحقق من الرصيد لدى المزود.',
    'provider_access_denied': 'حساب DeepSeek لا يملك صلاحية تنفيذ هذا الطلب.',
    'provider_model_unavailable': 'النموذج المحدد غير متاح لدى DeepSeek. تحقق من إعداد النموذج.',
    'provider_bad_request': 'رفض DeepSeek إعدادات الطلب. يلزم فحص إعداد النموذج ومعاملات التكامل.',
    'provider_rate_limit': 'بلغ حساب DeepSeek حد الطلبات. حاول بعد قليل.',
    'provider_timeout': 'انتهت مهلة انتظار DeepSeek قبل اكتمال الإجابة. يمكنك المحاولة مجددا.',
    'provider_unavailable': 'تعذر الاتصال بخدمة DeepSeek أو أنها غير متاحة مؤقتا.',
    'provider_output_truncated': 'وصلت الإجابة إلى حد طول التوليد قبل اكتمالها؛ لم تُعرض إجابة مبتورة.',
    'provider_invalid_response': 'وصلت استجابة فارغة أو غير صالحة من DeepSeek.',
    'provider_response_too_large': 'تجاوزت استجابة DeepSeek الحد المسموح لحجم البيانات.',
    'generation_quote_mismatch': 'غيّر التلخيص نص اقتباس أصلي؛ رُفض للحفاظ على دقة الشواهد.',
    'generation_unknown_source': 'أشار التلخيص إلى مصدر غير موجود ضمن الشواهد المسترجعة.',
    'generation_schema_invalid': 'لم تلتزم الإجابة بالبنية المطلوبة للتلخيص والاستشهادات.',
    'generation_unsupported_assertion': 'تضمنت الإجابة صياغة قطعية أو إرشادية غير مسموحة، أو أرقام صفحات داخل التلخيص.',
    'generation_unsupported_disagreement': 'لم تدعم الاستشهادات الاختلاف الذي ذكرته الإجابة.',
    'generation_conflicting_abstention': 'تناقضت الإجابة بشأن كفاية الشواهد؛ لم يُعرض التلخيص.',
    'generation_missing_claims': 'لم تتضمن الإجابة تلخيصا يمكن ربطه بالشواهد.',
}


class Interpreter:
    def __init__(self, settings, library, provider: Provider):
        self.settings, self.library, self.provider = settings, library, provider
        self.calls = deque()
        self.active = 0

    async def interpret(self, request: InterpretRequest) -> InterpretResponse:
        result = await run_in_threadpool(self.library.search, request)
        sources = sources_for(result, self.settings.max_context_chars)
        base = dict(retrieval=result, sources=sources, evidence_sufficient=bool(sources),
                    matched_symbols=list(dict.fromkeys(s.symbol for s in sources if s.symbol)),
                    generation_requested=request.generate,
                    generation_available=self.settings.enable_generation and bool(self.settings.deepseek_api_key.get_secret_value()))
        if not request.generate:
            return InterpretResponse(**base, status='retrieval_only', message='شواهد تاريخية مرتبطة ببعض عناصر الطلب، دون تلخيص آلي.' if sources else 'لم نجد شواهد مراجعة تطابق الطلب في المجموعة الحالية؛ التلخيص الآلي غير مطلوب.')
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
            code = exc.code if isinstance(exc, (ProviderFailure, GroundingFailure)) else 'provider_timeout' if isinstance(exc, TimeoutError) else 'grounding_validation_failed'
            logging.getLogger('ruya.generation').warning(json.dumps({'event': 'generation_failed', 'code': code,
                'fields': exc.fields if isinstance(exc, GroundingFailure) else []}))
            return InterpretResponse(**base, status='generation_failed', message='تعذر التوليد؛ الشواهد متاحة.',
                generation_issue=GenerationIssue(code=code, message=ISSUE_MESSAGES.get(code, 'لم تجتز الإجابة فحص الاستشهادات؛ الشواهد الأصلية متاحة.'),
                    retryable=isinstance(exc, TimeoutError) or (isinstance(exc, ProviderFailure) and exc.retryable)))
        finally:
            self.active -= 1
