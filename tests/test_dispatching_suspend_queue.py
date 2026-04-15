"""
CI Blocking Test: Dispatching Suspend Queue

Per testing-and-operations.md §test_dispatching_suspend_queue.py:
Verify that messages arriving while a task is dispatching are stored in the
suspend queue and re-offered after completion, not dropped or used to
overwrite the active task.
"""

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from redis_infra import InMemoryStore, SuspendQueue


class TestDispatchingSuspendQueue(unittest.TestCase):
    """Messages during dispatching must go to suspend queue, not overwrite active task."""

    def setUp(self):
        self.store = InMemoryStore()
        self.queue = SuspendQueue(self.store)

    def test_enqueue_stores_message(self):
        """Messages enqueued during dispatch must be retrievable."""
        self.queue.enqueue("session-1", "补充消息：请考虑价格因素")
        self.assertTrue(self.queue.has_pending("session-1"))

    def test_drain_returns_all_messages_in_order(self):
        """Drain must return all messages in FIFO order."""
        self.queue.enqueue("session-1", "第一条补充消息")
        self.queue.enqueue("session-1", "第二条补充消息")
        self.queue.enqueue("session-1", "第三条补充消息")

        messages = self.queue.drain("session-1")

        self.assertEqual(len(messages), 3)
        self.assertEqual(messages[0], "第一条补充消息")
        self.assertEqual(messages[1], "第二条补充消息")
        self.assertEqual(messages[2], "第三条补充消息")

    def test_drain_clears_queue(self):
        """After drain, the queue must be empty."""
        self.queue.enqueue("session-1", "消息")
        self.queue.drain("session-1")

        self.assertFalse(self.queue.has_pending("session-1"))
        self.assertEqual(self.queue.drain("session-1"), [])

    def test_different_sessions_are_isolated(self):
        """Messages from different sessions must not cross-contaminate."""
        self.queue.enqueue("session-1", "session-1的消息")
        self.queue.enqueue("session-2", "session-2的消息")

        messages_1 = self.queue.drain("session-1")
        messages_2 = self.queue.drain("session-2")

        self.assertEqual(messages_1, ["session-1的消息"])
        self.assertEqual(messages_2, ["session-2的消息"])

    def test_has_pending_returns_false_for_empty_queue(self):
        """has_pending must return False when no messages exist."""
        self.assertFalse(self.queue.has_pending("nonexistent-session"))

    def test_suspend_queue_stores_structured_entries(self):
        """Verify suspend queue can handle JSON-structured entries."""
        entry = json.dumps({
            "text": "补充消息",
            "user_id": "user-1",
            "create_ts": 1000,
            "attachments": [],
        }, ensure_ascii=False)
        self.queue.enqueue("session-1", entry)

        messages = self.queue.drain("session-1")
        parsed = json.loads(messages[0])
        self.assertEqual(parsed["text"], "补充消息")
        self.assertEqual(parsed["user_id"], "user-1")


if __name__ == "__main__":
    unittest.main()
