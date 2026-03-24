from __future__ import annotations

import base64
import json
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

from app.core.config import settings


class CommandSigningService:
    algorithm = 'ECDSA_P256_SHA256'

    def __init__(self) -> None:
        self._private_key = self._load_private_key()
        self._public_key = self._load_public_key()
        if self._private_key is None and settings.environment in {'development', 'test'}:
            self._private_key = ec.generate_private_key(ec.SECP256R1())
            self._public_key = self._private_key.public_key()

    def sign(self, envelope: dict) -> str:
        if self._private_key is None:
            raise RuntimeError('Command signing private key is not configured.')
        signature = self._private_key.sign(
            self._canonical_json(envelope),
            ec.ECDSA(hashes.SHA256()),
        )
        return base64.b64encode(signature).decode('ascii')

    def verify(self, envelope: dict, signature: str) -> bool:
        if self._public_key is None:
            return False
        try:
            self._public_key.verify(
                base64.b64decode(signature),
                self._canonical_json(envelope),
                ec.ECDSA(hashes.SHA256()),
            )
        except (InvalidSignature, ValueError):
            return False
        return True

    def public_key_pem(self) -> str | None:
        if self._public_key is None:
            return None
        return self._public_key.public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode('utf-8')

    def _canonical_json(self, envelope: dict) -> bytes:
        return json.dumps(envelope, sort_keys=True, separators=(',', ':')).encode('utf-8')

    def _load_private_key(self):
        pem = self._read_material(
            direct_value=settings.command_signing_private_key_pem,
            path_value=settings.command_signing_private_key_path,
        )
        if not pem:
            return None
        return serialization.load_pem_private_key(pem.encode('utf-8'), password=None)

    def _load_public_key(self):
        pem = self._read_material(
            direct_value=settings.command_signing_public_key_pem,
            path_value=settings.command_signing_public_key_path,
        )
        if pem:
            return serialization.load_pem_public_key(pem.encode('utf-8'))
        if self._private_key is not None:
            return self._private_key.public_key()
        return None

    def _read_material(self, *, direct_value: str | None, path_value: str | None) -> str | None:
        if direct_value:
            return direct_value.replace('\\n', '\n').strip() + '\n'
        if path_value:
            return Path(path_value).read_text(encoding='utf-8').strip() + '\n'
        return None
