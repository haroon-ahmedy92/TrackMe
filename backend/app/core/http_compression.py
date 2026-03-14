from __future__ import annotations

import gzip

from fastapi.responses import JSONResponse


class GzipRequestMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope.get('type') != 'http':
            await self.app(scope, receive, send)
            return

        headers = scope.get('headers', [])
        content_encoding = next(
            (value.decode('latin-1') for key, value in headers if key.lower() == b'content-encoding'),
            '',
        )
        if 'gzip' not in content_encoding.lower():
            await self.app(scope, receive, send)
            return

        body = bytearray()
        more_body = True
        while more_body:
            message = await receive()
            body.extend(message.get('body', b''))
            more_body = message.get('more_body', False)

        try:
            decompressed = gzip.decompress(bytes(body))
        except OSError:
            response = JSONResponse({'detail': 'Invalid gzip request body'}, status_code=400)
            await response(scope, receive, send)
            return

        new_headers = []
        content_length_set = False
        for key, value in headers:
            lower_key = key.lower()
            if lower_key == b'content-encoding':
                continue
            if lower_key == b'content-length':
                new_headers.append((b'content-length', str(len(decompressed)).encode('ascii')))
                content_length_set = True
                continue
            new_headers.append((key, value))
        if not content_length_set:
            new_headers.append((b'content-length', str(len(decompressed)).encode('ascii')))

        scope = dict(scope)
        scope['headers'] = new_headers

        sent = False

        async def new_receive():
            nonlocal sent
            if sent:
                return {'type': 'http.request', 'body': b'', 'more_body': False}
            sent = True
            return {'type': 'http.request', 'body': decompressed, 'more_body': False}

        await self.app(scope, new_receive, send)
