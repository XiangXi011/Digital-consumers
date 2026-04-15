"""Privacy and retention helpers for the DingTalk research runtime."""

from __future__ import annotations

import hashlib
import re


IMAGE_URL_RETENTION_DAYS = 7
RAW_CHAT_RETENTION_DAYS = 30
DEBUG_JSON_RETENTION_DAYS = 90


def _looks_hashed(value: str) -> bool:
    return bool(re.fullmatch(r"[0-9a-f]{8}", value))


def hash_user_id(user_id: str) -> str:
    """Hash a user identifier for at-rest storage and logs."""
    if _looks_hashed(user_id):
        return user_id
    return hashlib.sha256(user_id.encode("utf-8")).hexdigest()[:8]


def hash_nickname(nickname: str) -> str:
    """Hash a DingTalk nickname for at-rest storage and logs."""
    if _looks_hashed(nickname):
        return nickname
    return hashlib.sha256(nickname.encode("utf-8")).hexdigest()[:8]


def hash_identifier(value: str) -> str:
    """Hash any persisted identifier while avoiding double hashing."""
    return hash_user_id(value)


def matches_hashed_identifier(stored_value: str | None, raw_value: str | None) -> bool:
    """Match either raw or hashed identifiers during runtime checks."""
    if not stored_value or not raw_value:
        return False
    return stored_value == raw_value or stored_value == hash_identifier(raw_value)


def build_retention_policy() -> dict[str, object]:
    """Return the retention policy attached to persisted artifacts."""
    return {
        "image_url_days": IMAGE_URL_RETENTION_DAYS,
        "raw_text_days": RAW_CHAT_RETENTION_DAYS,
        "debug_json_days": DEBUG_JSON_RETENTION_DAYS,
        "metrics_retention": "long_term_allowed",
    }


_SANITIZE_REPLACEMENTS = [
    (re.compile(r"trace[_-]?id\s*[:=]\s*[\w\-]+", re.IGNORECASE), "[redacted]"),
    (re.compile(r"request[_-]?id\s*[:=]\s*[\w\-]+", re.IGNORECASE), "[redacted]"),
    (re.compile(r"(latency\s*[:=]\s*)[\d.]+\s*(?:ms|s)", re.IGNORECASE), r"\1[redacted]"),
    (re.compile(r"(duration\s*[:=]\s*)[\d.]+\s*(?:ms|s)", re.IGNORECASE), r"\1[redacted]"),
    (re.compile(r"raw[_-]?chat\s*[:=].*", re.IGNORECASE), "[redacted]"),
    (re.compile(r"(session[_-]?id\s*[:=]\s*)[^\s<,;]+", re.IGNORECASE), r"\1[redacted]"),
]


def sanitize_report(html: str) -> str:
    """Remove trace IDs, raw chat snapshots, and timing internals from HTML."""
    result = html
    for pattern, replacement in _SANITIZE_REPLACEMENTS:
        result = pattern.sub(replacement, result)
    return result
