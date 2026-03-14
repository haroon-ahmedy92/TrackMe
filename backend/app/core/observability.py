from __future__ import annotations

import json
import logging
import time
import uuid
from contextlib import contextmanager

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.services.observability_service import security_signal_store

logger = logging.getLogger('trackme.observability')

try:  # pragma: no cover
    from opentelemetry import trace
except ModuleNotFoundError:  # pragma: no cover
    trace = None


@contextmanager
def start_span(name: str, attributes: dict[str, str | int | float | bool | None] | None = None):
    if trace is None:  # pragma: no cover
        yield None
        return
    tracer = trace.get_tracer('trackme.backend')
    with tracer.start_as_current_span(name) as span:
        for key, value in (attributes or {}).items():
            if value is not None:
                span.set_attribute(key, value)
        yield span


class StructuredRequestLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        started = time.perf_counter()

        with start_span(
            'http.request',
            attributes={
                'http.method': request.method,
                'http.route': request.url.path,
                'http.request_id': request_id,
            },
        ):
            response = await call_next(request)

        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        forwarded = request.headers.get('x-forwarded-for')
        ip_address = forwarded.split(',')[0].strip() if forwarded else (request.client.host if request.client else 'unknown')
        org_id = request.query_params.get('org_id')

        log_record = {
            'event': 'http_request',
            'request_id': request_id,
            'method': request.method,
            'path': request.url.path,
            'status_code': response.status_code,
            'duration_ms': duration_ms,
            'org_id': org_id,
            'client_ip': ip_address,
        }
        logger.info(json.dumps(log_record, sort_keys=True))

        if response.status_code in {401, 403}:
            security_signal_store.record_auth_failure(
                path=request.url.path,
                ip_address=ip_address,
                actor_hint=request.headers.get('x-actor-sub'),
                org_id=org_id,
                reason='http_unauthorized' if response.status_code == 401 else 'http_forbidden',
                request_id=request_id,
            )
        response.headers['X-Request-ID'] = request_id
        return response
