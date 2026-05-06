"""Stable idempotency fingerprint helpers."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from core.exceptions import FingerprintError


@dataclass(frozen=True)
class FingerprintParts:
    source_type: str
    source_id: str
    content_hash: str


def content_hash(payload: bytes | str) -> str:
    data = payload.encode("utf-8") if isinstance(payload, str) else payload
    return hashlib.sha256(data).hexdigest()


def idempotency_fingerprint(source_type: str, source_id: str, content_hash_value: str) -> str:
    if not source_type or not source_id or not content_hash_value:
        raise FingerprintError("source_type, source_id, and content_hash are required")
    canonical = json.dumps(
        {"source_type": source_type, "source_id": source_id, "content_hash": content_hash_value},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

