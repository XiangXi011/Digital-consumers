"""
CI Blocking Test: Authorization Binding

Validates that classify_authorization() enforces user_id binding,
bot-mention/private-chat requirement, time-window, and denial detection.
"""

import json
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from task_session_manager import (
    AUTHORIZATION_WINDOW_SECONDS,
    TaskSession,
    TaskSessionManager,
)


def _persona_path():
    return Path(__file__).resolve().parents[1] / "persona_samples_complete.json"


def _make_manager(tmp_dir: str) -> TaskSessionManager:
    return TaskSessionManager(
        session_dir=Path(tmp_dir) / "sessions",
        persona_path=_persona_path(),
    )


def _event(
    *,
    user_id="user-1",
    is_bot_mentioned=False,
    is_private_chat=False,
    create_ts=None,
):
    return {
        "group_id": "group-1",
        "conversation_id": "conv-1",
        "user_id": user_id,
        "text": "",
        "attachments": [],
        "is_bot_mentioned": is_bot_mentioned,
        "is_private_chat": is_private_chat,
        "create_ts": create_ts or time.time() * 1000,
    }


class TestClassifyAuthorization(unittest.TestCase):

    def test_strong_affirm_with_bot_mention(self):
        """Strong affirmation + bot-mention -> strong_affirm."""
        with tempfile.TemporaryDirectory() as tmp:
            mgr = _make_manager(tmp)
            result = mgr.classify_authorization(
                "按当前信息运行", "user-1",
                _event(user_id="user-1", is_bot_mentioned=True),
            )
            self.assertEqual(result, "strong_affirm")

    def test_strong_affirm_with_private_chat(self):
        """Strong affirmation + private chat -> strong_affirm."""
        with tempfile.TemporaryDirectory() as tmp:
            mgr = _make_manager(tmp)
            result = mgr.classify_authorization(
                "开始分析", "user-1",
                _event(user_id="user-1", is_private_chat=True),
            )
            self.assertEqual(result, "strong_affirm")

    def test_strong_affirm_no_mention_no_private(self):
        """Strong affirmation + no bot-mention + not private -> none (rejected)."""
        with tempfile.TemporaryDirectory() as tmp:
            mgr = _make_manager(tmp)
            result = mgr.classify_authorization(
                "按当前信息运行", "user-1",
                _event(user_id="user-1", is_bot_mentioned=False, is_private_chat=False),
            )
            self.assertEqual(result, "none")

    def test_weak_affirm_same_user_within_window(self):
        """Weak affirmation + same user + within 5min + bot-mention -> weak_affirm."""
        with tempfile.TemporaryDirectory() as tmp:
            mgr = _make_manager(tmp)
            now_ms = time.time() * 1000
            session = TaskSession(
                session_id="test-session",
                group_id="group-1",
                conversation_id="conv-1",
                user_id="user-1",
                status="awaiting_run_confirmation",
                authorization_requested_at=now_ms - 60_000,  # 1 minute ago
                authorization_requested_by="user-1",
            )
            result = mgr.classify_authorization(
                "好", "user-1",
                _event(user_id="user-1", is_bot_mentioned=True, create_ts=now_ms),
                session=session,
            )
            self.assertEqual(result, "weak_affirm")

    def test_weak_affirm_different_user_rejected(self):
        """Weak affirmation + different user -> none (rejected)."""
        with tempfile.TemporaryDirectory() as tmp:
            mgr = _make_manager(tmp)
            now_ms = time.time() * 1000
            session = TaskSession(
                session_id="test-session",
                group_id="group-1",
                conversation_id="conv-1",
                user_id="user-1",
                status="awaiting_run_confirmation",
                authorization_requested_at=now_ms - 60_000,
                authorization_requested_by="user-1",
            )
            result = mgr.classify_authorization(
                "好", "user-2",  # different user
                _event(user_id="user-2", is_bot_mentioned=True, create_ts=now_ms),
                session=session,
            )
            self.assertEqual(result, "none")

    def test_weak_affirm_expired_window(self):
        """Weak affirmation + same user + > 5 minutes -> none (rejected)."""
        with tempfile.TemporaryDirectory() as tmp:
            mgr = _make_manager(tmp)
            now_ms = time.time() * 1000
            session = TaskSession(
                session_id="test-session",
                group_id="group-1",
                conversation_id="conv-1",
                user_id="user-1",
                status="awaiting_run_confirmation",
                authorization_requested_at=now_ms - (AUTHORIZATION_WINDOW_SECONDS + 10) * 1000,
                authorization_requested_by="user-1",
            )
            result = mgr.classify_authorization(
                "可以", "user-1",
                _event(user_id="user-1", is_bot_mentioned=True, create_ts=now_ms),
                session=session,
            )
            self.assertEqual(result, "none")

    def test_denial_tokens(self):
        """Denial words -> denial regardless of other conditions."""
        with tempfile.TemporaryDirectory() as tmp:
            mgr = _make_manager(tmp)
            for token in ["等等", "先别", "不要", "暂停"]:
                result = mgr.classify_authorization(
                    token, "user-1",
                    _event(user_id="user-1", is_bot_mentioned=True),
                )
                self.assertEqual(result, "denial", f"Expected denial for '{token}'")

    def test_session_serialization_roundtrip(self):
        """authorization_requested_at and authorization_requested_by survive to_dict/from_dict."""
        now_ms = time.time() * 1000
        session = TaskSession(
            session_id="test-session",
            group_id="group-1",
            conversation_id="conv-1",
            user_id="user-1",
            status="awaiting_run_confirmation",
            authorization_requested_at=now_ms,
            authorization_requested_by="user-1",
        )
        restored = TaskSession.from_dict(session.to_dict())
        self.assertAlmostEqual(restored.authorization_requested_at, now_ms, places=0)
        self.assertEqual(restored.authorization_requested_by, "user-1")


if __name__ == "__main__":
    unittest.main()
