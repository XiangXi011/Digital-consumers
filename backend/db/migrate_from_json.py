"""One-shot migration: JSON session files → PostgreSQL.

Usage:
    python -m backend.db.migrate_from_json

Idempotent — uses INSERT … ON CONFLICT DO NOTHING on session_id.
"""

import asyncio
import json
import logging
from pathlib import Path

from backend.db.models import Project, Report, ShareToken, User
from backend.db.session import async_session, engine
from backend.paths import (
    DINGTALK_REPORTS_DIR,
    DINGTALK_SESSIONS_DIR,
    OUTPUTS_DIR,
    REPORT_SHARES_PATH,
)

logger = logging.getLogger(__name__)


async def migrate_sessions(default_owner_id: str) -> int:
    """Scan outputs/dingtalk_sessions/*.json → projects table."""
    if not DINGTALK_SESSIONS_DIR.exists():
        logger.warning("Session dir %s does not exist, skipping.", DINGTALK_SESSIONS_DIR)
        return 0

    count = 0
    async with async_session() as session:
        for path in sorted(DINGTALK_SESSIONS_DIR.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                logger.exception("Failed to read %s, skipping.", path)
                continue

            session_id = data.get("session_id") or path.stem
            # Idempotent insert — skip if session_id already in DB
            exists = await session.execute(
                Project.__table__.select().where(Project.session_id == session_id)
            )
            if exists.first():
                continue

            project = Project(
                owner_id=default_owner_id,
                session_id=session_id,
                group_id=data.get("group_id", ""),
                conversation_id=data.get("conversation_id", ""),
                user_id=data.get("user_id", ""),
                name=session_id,
                status=data.get("status", "collecting"),
                fields=data.get("fields", {}),
                attachments=data.get("attachments", []),
                source_links=data.get("source_links", []),
                custom_questions=data.get("custom_questions", []),
                product_context_notes=data.get("product_context_notes", []),
                follow_up_context=data.get("follow_up_context", ""),
                business_brief=data.get("business_brief"),
                research_plan=data.get("research_plan"),
                readiness_decision=data.get("readiness_decision"),
                html_report_path=data.get("html_report_path"),
                json_report_path=data.get("json_report_path"),
                metrics_path=data.get("metrics_path"),
                checklist_sent=data.get("checklist_sent", False),
                partial_run_authorized=data.get("partial_run_authorized", False),
                live_snapshot_refs=data.get("live_snapshot_refs", []),
                frozen_snapshot_refs=data.get("frozen_snapshot_refs", []),
                retention_policy=data.get("retention_policy", {}),
                suspended_messages=data.get("suspended_messages", []),
            )
            session.add(project)
            count += 1

        await session.commit()
    logger.info("Migrated %d sessions.", count)
    return count


async def migrate_reports(default_owner_id: str) -> int:
    """Scan report JSON files → reports table."""
    report_dirs = [
        OUTPUTS_DIR / "dingtalk_reports",
        OUTPUTS_DIR / "web_uploads",
    ]
    count = 0
    async with async_session() as session:
        for rdir in report_dirs:
            if not rdir.exists():
                continue
            for path in sorted(rdir.glob("*.json")):
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                except Exception:
                    logger.exception("Failed to read %s, skipping.", path)
                    continue

                report_id_str = data.get("id") or path.stem
                exists = await session.execute(
                    Report.__table__.select().where(Report.id == report_id_str)
                )
                if exists.first():
                    continue

                html_path = str(path.with_suffix(".html")) if path.with_suffix(".html").exists() else None

                report = Report(
                    id=report_id_str,
                    project_id=data.get("project_id", report_id_str),
                    owner_id=data.get("owner_id", default_owner_id),
                    report_type=data.get("report_type", "full"),
                    name=data.get("name", path.stem),
                    json_path=str(path),
                    html_path=html_path,
                    meta=data.get("meta"),
                    evaluation_metrics=data.get("evaluation_metrics"),
                )
                session.add(report)
                count += 1

        await session.commit()
    logger.info("Migrated %d reports.", count)
    return count


async def migrate_share_tokens() -> int:
    """Read report_shares.json → share_tokens table."""
    if not REPORT_SHARES_PATH.exists():
        logger.info("No report_shares.json found, skipping.")
        return 0

    try:
        shares = json.loads(REPORT_SHARES_PATH.read_text(encoding="utf-8"))
    except Exception:
        logger.exception("Failed to read %s", REPORT_SHARES_PATH)
        return 0

    count = 0
    async with async_session() as session:
        for entry in shares:
            token_str = entry.get("token")
            if not token_str:
                continue
            exists = await session.execute(
                ShareToken.__table__.select().where(ShareToken.token == token_str)
            )
            if exists.first():
                continue

            st = ShareToken(
                token=token_str,
                report_id=entry.get("report_id", ""),
                expires_at=entry.get("expires_at", "2099-01-01T00:00:00+00:00"),
                revoked=entry.get("revoked", False),
            )
            session.add(st)
            count += 1

        await session.commit()
    logger.info("Migrated %d share tokens.", count)
    return count


async def ensure_default_owner() -> str:
    """Create a bootstrap admin user if no users exist, return its id."""
    async with async_session() as session:
        from sqlalchemy import func, select

        from backend.db.models import User

        result = await session.execute(select(func.count()).select_from(User))
        user_count = result.scalar_one()

        if user_count == 0:
            from passlib.hash import bcrypt

            admin = User(
                email="admin@local",
                display_name="Admin",
                role="admin",
                password_hash=bcrypt.hash("changeme"),
            )
            session.add(admin)
            await session.commit()
            logger.info("Created bootstrap admin user (id=%s).", admin.id)
            return admin.id
        else:
            first = await session.execute(
                select(User).order_by(User.created_at).limit(1)
            )
            return first.scalar_one().id


async def run_all() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logger.info("Starting JSON → DB migration ...")

    default_owner_id = await ensure_default_owner()
    s = await migrate_sessions(default_owner_id)
    r = await migrate_reports(default_owner_id)
    t = await migrate_share_tokens()
    logger.info("Migration complete: %d sessions, %d reports, %d share tokens.", s, r, t)

    await engine.dispose()


def main() -> None:
    asyncio.run(run_all())


if __name__ == "__main__":
    main()
