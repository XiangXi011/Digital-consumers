from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _stable_json(payload: Dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def build_replay_signature(
    *,
    stage: str,
    payload: Dict[str, Any],
    version_bundle: Dict[str, Any],
) -> str:
    hasher = hashlib.sha256()
    hasher.update(stage.encode("utf-8"))
    hasher.update(b"\n")
    hasher.update(_stable_json(version_bundle).encode("utf-8"))
    hasher.update(b"\n")
    hasher.update(_stable_json(payload).encode("utf-8"))
    return hasher.hexdigest()[:16]


class RuntimeArtifactStore:
    def __init__(self, base_dir: Path | str):
        self.base_dir = Path(base_dir)
        self.live_dir = self.base_dir / "snapshots" / "live"
        self.frozen_dir = self.base_dir / "snapshots" / "frozen"
        self.metrics_dir = self.base_dir / "metrics"
        self.live_dir.mkdir(parents=True, exist_ok=True)
        self.frozen_dir.mkdir(parents=True, exist_ok=True)
        self.metrics_dir.mkdir(parents=True, exist_ok=True)

    def save_live(
        self,
        *,
        session_id: str,
        stage: str,
        payload: Dict[str, Any],
        metadata: Dict[str, Any] | None = None,
    ) -> str:
        record = {
            "kind": "live",
            "session_id": session_id,
            "stage": stage,
            "created_at": _utc_now_iso(),
            "payload": payload,
        }
        if metadata:
            record["metadata"] = metadata
        return self._write_snapshot(self.live_dir, session_id, stage, record)

    def save_frozen(
        self,
        *,
        session_id: str,
        stage: str,
        payload: Dict[str, Any],
        version_bundle: Dict[str, Any],
    ) -> str:
        record = {
            "kind": "frozen",
            "session_id": session_id,
            "stage": stage,
            "created_at": _utc_now_iso(),
            "version_bundle": version_bundle,
            "replay_signature": build_replay_signature(
                stage=stage,
                payload=payload,
                version_bundle=version_bundle,
            ),
            "payload": payload,
        }
        return self._write_snapshot(self.frozen_dir, session_id, stage, record)

    def save_metrics(self, *, task_id: str, metrics: Dict[str, Any]) -> str:
        path = self.metrics_dir / f"{task_id}__metrics.json"
        path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
        return str(path)

    def _write_snapshot(
        self,
        target_dir: Path,
        session_id: str,
        stage: str,
        record: Dict[str, Any],
    ) -> str:
        session_dir = target_dir / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}__{stage}.json"
        path = session_dir / filename
        path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        return str(path)
