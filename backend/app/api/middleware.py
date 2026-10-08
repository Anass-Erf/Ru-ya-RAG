import json
import logging
import time
from uuid import uuid4
from starlette.responses import JSONResponse

logger = logging.getLogger('ruya.requests')


class RequestBoundary:
    """Cap actual body bytes, including chunked requests; log no user content."""
    def __init__(self, app, max_bytes):
        self.app, self.max_bytes = app, max_bytes

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        request_id = uuid4().hex
        scope.setdefault('state', {})['request_id'] = request_id
        start, status = time.monotonic(), 500

        async def tracked(message):
            nonlocal status
            if message['type'] == 'http.response.start':
                status = message['status']
                headers = [(key, value) for key, value in message.get('headers', []) if key.lower() != b'x-request-id']
                message['headers'] = headers + [(b'x-request-id', request_id.encode())]
            await send(message)

        try:
            body = bytearray()
            while True:
                message = await receive()
                if message['type'] == 'http.disconnect':
                    return
                body.extend(message.get('body', b''))
                if len(body) > self.max_bytes:
                    response = JSONResponse({'error': {'code': 'request_too_large', 'message': 'Request body is too large.',
                        'request_id': request_id, 'fields': []}}, status_code=413)
                    return await response(scope, receive, tracked)
                if not message.get('more_body', False):
                    break
            delivered = False

            async def replay():
                nonlocal delivered
                if not delivered:
                    delivered = True
                    return {'type': 'http.request', 'body': bytes(body), 'more_body': False}
                return await receive()
            await self.app(scope, replay, tracked)
        finally:
            logger.info(json.dumps({'event': 'request', 'request_id': request_id, 'method': scope['method'],
                                    'status': status, 'elapsed_ms': round((time.monotonic()-start)*1000, 2)}))
