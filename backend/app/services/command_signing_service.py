from __future__ import annotations

import hashlib
import hmac
import json

from app.core.config import settings


class CommandSigningService:
    algorithm = 'HMAC_SHA256_PLACEHOLDER'

    def sign(self, envelope: dict) -> str:
        return hmac.new(self._secret(), self._canonical_json(envelope), hashlib.sha256).hexdigest()

    def verify(self, envelope: dict, signature: str) -> bool:
        expected = self.sign(envelope)
        return hmac.compare_digest(expected, signature)

    def _canonical_json(self, envelope: dict) -> bytes:
        return json.dumps(envelope, sort_keys=True, separators=(',', ':')).encode('utf-8')

    def _secret(self) -> bytes:
        secret = settings.command_signing_secret or 'trackme-dev-command-secret-change-me'
        return secret.encode('utf-8')
