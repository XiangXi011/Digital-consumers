from __future__ import annotations

import math
from collections import Counter
from typing import Any, Dict, List


REQUIRED_METRICS = {
    "success_full",
    "success_partial",
    "failed_recoverable",
    "failed_terminal",
    "routing_distribution",
    "route_confidence_distribution",
    "clarification_rate_by_task_type",
    "route_override_rate",
    "inter_persona_divergence_score",
    "minority_survival_rate",
    "purchase_intent_entropy",
    "repeated_phrase_rate",
    "pipeline_total_latency_ms",
    "per_persona_latency_ms",
}


def _normalized_entropy(values: List[str]) -> float:
    filtered = [value for value in values if value]
    if len(filtered) <= 1:
        return 0.0
    counts = Counter(filtered)
    total = sum(counts.values())
    entropy = -sum((count / total) * math.log2(count / total) for count in counts.values())
    max_entropy = math.log2(len(counts)) if len(counts) > 1 else 1.0
    if max_entropy == 0:
        return 0.0
    return round(entropy / max_entropy, 4)


def _repeated_phrase_rate(consumer_voice: List[Dict[str, Any]]) -> float:
    phrases = [
        str(item.get("voice_line", "")).strip().lower()
        for item in consumer_voice
        if str(item.get("voice_line", "")).strip()
    ]
    if not phrases:
        return 0.0
    counts = Counter(phrases)
    repeated = sum(count - 1 for count in counts.values() if count > 1)
    return round(repeated / len(phrases), 4)


def _extract_purchase_intent(item: Dict[str, Any]) -> str:
    backend = item.get("backend_evaluation")
    if isinstance(backend, dict):
        intent = backend.get("purchase_intent")
        if isinstance(intent, str):
            return intent
    intent = item.get("purchase_intent")
    return str(intent).strip() if intent else ""


def compute_evaluation_metrics(report: Dict[str, Any]) -> Dict[str, Any]:
    meta = report.get("meta", {})
    research_brief = report.get("research_brief", {})
    consumer_voice = report.get("consumer_voice", [])
    evidence_groups = report.get("evidence_groups", {})

    completion_status = str(meta.get("completion_status", ""))
    question_type = str(meta.get("question_type") or research_brief.get("task_type") or "unknown")
    intents = [_extract_purchase_intent(item) for item in consumer_voice]
    populated_intents = [intent for intent in intents if intent]
    total_intents = len(populated_intents)
    majority_share = 1.0
    if total_intents:
        counts = Counter(populated_intents)
        majority_share = max(counts.values()) / total_intents
    reject_count = sum(1 for intent in populated_intents if intent == "reject")
    minority_evidence = evidence_groups.get("minority_reject_evidence", []) or []
    minority_survival_rate = 1.0 if reject_count == 0 else round(min(1.0, len(minority_evidence) / reject_count), 4)
    per_persona_latency_ms = {
        str(item.get("persona_id", "")).strip(): float(item.get("latency_ms", 0.0))
        for item in consumer_voice
        if str(item.get("persona_id", "")).strip()
    }
    pipeline_total_latency_ms = float(meta.get("pipeline_total_latency_ms") or 0.0)
    if not pipeline_total_latency_ms and per_persona_latency_ms:
        pipeline_total_latency_ms = max(per_persona_latency_ms.values())

    metrics: Dict[str, Any] = {
        "success_full": 1.0 if completion_status == "complete" else 0.0,
        "success_partial": 1.0 if completion_status == "partial" else 0.0,
        "failed_recoverable": 0.0,
        "failed_terminal": 0.0,
        "routing_distribution": {question_type: 1.0},
        "route_confidence_distribution": {question_type: 1.0},
        "clarification_rate_by_task_type": {question_type: 0.0},
        "route_override_rate": 0.0,
        "inter_persona_divergence_score": round(1.0 - majority_share, 4) if total_intents else 0.0,
        "minority_survival_rate": minority_survival_rate,
        "purchase_intent_entropy": _normalized_entropy(populated_intents),
        "repeated_phrase_rate": _repeated_phrase_rate(consumer_voice),
        "pipeline_total_latency_ms": round(pipeline_total_latency_ms, 2),
        "per_persona_latency_ms": {
            persona_id: round(latency, 2) for persona_id, latency in per_persona_latency_ms.items()
        },
    }

    for key in REQUIRED_METRICS:
        metrics.setdefault(key, 0.0)
    return metrics
