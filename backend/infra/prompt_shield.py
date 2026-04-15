"""
Pre-routing prompt-injection shield.

Intercepts prompt injection before any routing model call per runtime-and-state.md:
  • Block role reassignment requests
  • Block system prompt override attempts
  • Block "ignore previous rules" instructions

Returns True if the text is safe, False if injection detected.
"""

from __future__ import annotations

import re
from typing import List, Tuple

# Compiled patterns — each is (description, regex)
_INJECTION_PATTERNS: List[Tuple[str, re.Pattern]] = [
    # NOTE: role-reassignment patterns were removed due high false-positive rate in normal business prompts.
    # We keep hard blocks for system override / ignore-rules / jailbreak and output-manipulation attempts.
    # System prompt override
    ("system_override_en", re.compile(
        r"(?:system\s*(?:prompt|message|instruction)|override\s+(?:system|instructions))",
        re.IGNORECASE,
    )),
    ("system_override_zh", re.compile(
        r"(?:系统(?:提示|指令|消息)|覆盖(?:系统|指令))",
    )),
    # Ignore previous rules
    ("ignore_rules_en", re.compile(
        r"(?:ignore\s+(?:all\s+)?(?:previous|prior|above)\s+(?:rules|instructions|prompts|guidelines))",
        re.IGNORECASE,
    )),
    ("ignore_rules_zh", re.compile(
        r"(?:忽略(?:之前|以上|上面|先前)的(?:规则|指令|提示|要求)|不要遵守|无视之前)",
    )),
    # DAN / jailbreak patterns
    ("jailbreak_en", re.compile(
        r"(?:DAN\s+mode|developer\s+mode|jailbreak|bypass\s+(?:safety|filter|restriction))",
        re.IGNORECASE,
    )),
    # Positivity forcing — prevent "always agree" or "be positive" injection
    ("positivity_forcing_en", re.compile(
        r"(?:always\s+(?:agree|be\s+positive|output\s+positive|say\s+yes)|must\s+(?:agree|be\s+positive|approve))",
        re.IGNORECASE,
    )),
    ("positivity_forcing_zh", re.compile(
        r"(?:必须(?:积极|同意|支持|正面)|所有(?:画像|人物|角色)(?:都)?必须(?:选择|输出|回答)?(?:interested|positive|同意|支持|积极))",
    )),
    # Minority suppression — prevent "ignore rejecting personas" injection
    ("minority_suppress_en", re.compile(
        r"(?:ignore\s+(?:reject|dissent|minority|negative)|suppress\s+(?:reject|dissent|minority|negative)|hide\s+(?:reject|negative))",
        re.IGNORECASE,
    )),
    ("minority_suppress_zh", re.compile(
        r"(?:忽略(?:反对|拒绝|否定|少数)|不要(?:输出|显示|保留)(?:反对|拒绝|否定|少数)(?:意见|声音|观点)?|隐藏(?:反对|负面))",
    )),
    # Chinese jailbreak patterns
    ("jailbreak_zh", re.compile(
        r"(?:越狱|开发者模式|无限制模式|解除限制|解锁(?:全部|所有)功能|进入(?:调试|测试|开发)模式)",
    )),
]


def get_prompt_injection_label(text: str) -> str:
    """Return the first matched injection label, or empty string if safe."""
    if not text or not text.strip():
        return ""
    for label, pattern in _INJECTION_PATTERNS:
        if pattern.search(text):
            return label
    return ""


def check_prompt_injection(text: str) -> bool:
    """Return True if the text contains a prompt injection attempt.

    Should be called before any routing or LLM call.
    """
    return bool(get_prompt_injection_label(text))


def sanitize_for_routing(text: str) -> str:
    """Strip known injection markers while keeping the rest of the text.

    Use this when you want to pass user text through but strip dangerous
    fragments rather than rejecting the whole message.
    """
    cleaned = text
    for _label, pattern in _INJECTION_PATTERNS:
        cleaned = pattern.sub("", cleaned)
    return cleaned.strip()
