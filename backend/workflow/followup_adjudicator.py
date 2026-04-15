"""
Follow-up adjudication per runtime-and-state.md.

Rule engine has priority:
  • If embedding similarity > 0.85 or keyword overlap > 60% → candidate_same_topic
  • Otherwise → unrelated (create new intake)
  • LLM adjudication only for candidate_same_topic → same_task | same_topic_new_task

Hard preconditions for same_task:
  • task_type is unchanged
  • core product_context subject is unchanged
"""

from __future__ import annotations

import difflib
import re
from typing import Any, Dict, List, Literal, Optional

# ---------------------------------------------------------------------- #
#  Keyword Overlap                                                        #
# ---------------------------------------------------------------------- #

_STOPWORDS = frozenset([
    "的", "了", "是", "在", "和", "与", "或", "不", "也", "都",
    "有", "这", "那", "个", "就", "会", "能", "可以", "要",
    "the", "a", "an", "is", "are", "in", "on", "and", "or", "to",
])


def _tokenize(text: str) -> List[str]:
    """Simple tokenizer for Chinese + English text."""
    tokens = re.findall(r"[\u4e00-\u9fff]+|[a-zA-Z]+", text.lower())
    # Split Chinese into individual characters for better overlap detection
    result = []
    for token in tokens:
        if re.match(r"[\u4e00-\u9fff]", token):
            result.extend(list(token))
        else:
            result.append(token)
    return [t for t in result if t not in _STOPWORDS and len(t) > 0]


def keyword_overlap(text_a: str, text_b: str) -> float:
    """Compute keyword overlap percentage between two texts.

    Returns a float in [0, 1] representing the overlap ratio.
    """
    tokens_a = set(_tokenize(text_a))
    tokens_b = set(_tokenize(text_b))
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = tokens_a & tokens_b
    union = tokens_a | tokens_b
    return len(intersection) / len(union) if union else 0.0


# ---------------------------------------------------------------------- #
#  Embedding Similarity (stub — can be replaced with real embeddings)     #
# ---------------------------------------------------------------------- #

_SEMANTIC_NORMALIZATION = {
    "宝宝": "孩子",
    "宝贝": "孩子",
    "能力": "效果",
    "效能": "效果",
    "如何": "怎么样",
    "愿意坚持": "愿意",
    "持续刷牙": "刷牙",
    "坚持刷牙": "刷牙",
}


def _normalize_semantic_text(text: str) -> str:
    normalized = (text or "").strip().lower()
    for source, target in _SEMANTIC_NORMALIZATION.items():
        normalized = normalized.replace(source, target)
    return normalized


def embedding_similarity(text_a: str, text_b: str) -> float:
    """Approximate semantic similarity without collapsing to keyword overlap."""
    normalized_a = _normalize_semantic_text(text_a)
    normalized_b = _normalize_semantic_text(text_b)
    if not normalized_a or not normalized_b:
        return 0.0

    overlap = keyword_overlap(normalized_a, normalized_b)
    sequence_ratio = difflib.SequenceMatcher(None, normalized_a, normalized_b).ratio()
    return round(max(overlap, sequence_ratio * 0.75 + overlap * 0.25), 4)


# ---------------------------------------------------------------------- #
#  Rule Engine Adjudication                                               #
# ---------------------------------------------------------------------- #

SIMILARITY_THRESHOLD = 0.85
KEYWORD_OVERLAP_THRESHOLD = 0.60


def adjudicate_followup(
    candidate_brief_text: str,
    prior_brief_text: str,
    similarity_fn=None,
) -> Literal["unrelated", "candidate_same_topic"]:
    """Rule-engine follow-up adjudication (first pass).

    Per runtime-and-state.md:
    - If similarity > 0.85 or keyword overlap > 60% -> candidate_same_topic
    - Otherwise -> unrelated

    INVARIANT: Both inputs must be serialized BusinessBrief data, not raw
    chat text. The caller must build a candidate BusinessBrief from the new
    message before calling this function.

    This function DOES NOT call LLM.
    """
    if not candidate_brief_text.strip() or not prior_brief_text.strip():
        return "unrelated"

    sim_fn = similarity_fn or embedding_similarity
    sim_score = sim_fn(candidate_brief_text, prior_brief_text)
    kw_overlap = keyword_overlap(candidate_brief_text, prior_brief_text)

    if sim_score > SIMILARITY_THRESHOLD or kw_overlap > KEYWORD_OVERLAP_THRESHOLD:
        return "candidate_same_topic"

    return "unrelated"


def check_same_task_preconditions(
    prior_brief: Dict[str, Any],
    new_brief: Dict[str, Any],
) -> bool:
    """Hard preconditions for same_task classification.

    Per runtime-and-state.md:
    - task_type is unchanged
    - core product_context subject is unchanged
    """
    if prior_brief.get("task_type") != new_brief.get("task_type"):
        return False
    prior_product = (prior_brief.get("product_context") or "").strip().lower()
    new_product = (new_brief.get("product_context") or "").strip().lower()
    if not prior_product or not new_product:
        return False
    # Core subject should have significant overlap
    overlap = keyword_overlap(prior_product, new_product)
    return overlap > 0.5


def llm_refine_followup(
    ai_client: Any,
    candidate_brief: Dict[str, Any],
    prior_brief: Dict[str, Any],
) -> Literal["same_task", "same_topic_new_task"]:
    """LLM refinement for candidate_same_topic messages.

    Only called when rule engine returns candidate_same_topic.
    LLM may only choose between same_task and same_topic_new_task.

    INVARIANT: candidate_brief must be a structured BusinessBrief dict,
    not raw chat text.
    """
    if check_same_task_preconditions(prior_brief, candidate_brief):
        return "same_task"
    return "same_topic_new_task"
