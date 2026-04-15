"""Repository classes — thin data-access layer over SQLAlchemy models.

All methods are async and accept an AsyncSession.
"""

from __future__ import annotations

import json
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Sequence

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import (
    AuditLog,
    FrozenSnapshot,
    Project,
    Report,
    ShareToken,
    SystemSetting,
    User,
)


# ─── ProjectRepo ──────────────────────────────────────────────────────────────


class ProjectRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.s = session

    async def create(
        self,
        *,
        owner_id: str,
        session_id: str,
        name: str = "",
        project_type: str = "concept_test",
        status: str = "collecting",
        fields: Optional[Dict[str, Any]] = None,
        group_id: str = "",
        conversation_id: str = "",
        user_id: str = "",
    ) -> Project:
        project = Project(
            owner_id=owner_id,
            session_id=session_id,
            name=name,
            project_type=project_type,
            status=status,
            fields=fields or {},
            group_id=group_id,
            conversation_id=conversation_id,
            user_id=user_id,
        )
        self.s.add(project)
        await self.s.flush()
        return project

    async def get(self, project_id: str) -> Optional[Project]:
        return await self.s.get(Project, project_id)

    async def get_by_session_id(self, session_id: str) -> Optional[Project]:
        stmt = select(Project).where(Project.session_id == session_id)
        return (await self.s.execute(stmt)).scalar_one_or_none()

    async def list_by_owner(
        self,
        owner_id: str,
        *,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Project]:
        stmt = select(Project).where(Project.owner_id == owner_id)
        if status:
            stmt = stmt.where(Project.status == status)
        stmt = stmt.order_by(Project.created_at.desc()).limit(limit).offset(offset)
        return list((await self.s.execute(stmt)).scalars().all())

    async def list_all(self, *, status: Optional[str] = None, limit: int = 100, offset: int = 0) -> List[Project]:
        stmt = select(Project)
        if status:
            stmt = stmt.where(Project.status == status)
        stmt = stmt.order_by(Project.created_at.desc()).limit(limit).offset(offset)
        return list((await self.s.execute(stmt)).scalars().all())

    async def update(self, project_id: str, **kwargs: Any) -> None:
        stmt = (
            update(Project)
            .where(Project.id == project_id)
            .values(updated_at=datetime.now(timezone.utc), **kwargs)
        )
        await self.s.execute(stmt)

    async def count_by_owner(self, owner_id: str) -> int:
        stmt = select(func.count()).select_from(Project).where(Project.owner_id == owner_id)
        return (await self.s.execute(stmt)).scalar_one()

    async def count_by_status(self, owner_id: Optional[str] = None) -> Dict[str, int]:
        stmt = select(Project.status, func.count()).group_by(Project.status)
        if owner_id:
            stmt = stmt.where(Project.owner_id == owner_id)
        rows = (await self.s.execute(stmt)).all()
        return {row[0]: row[1] for row in rows}


# ─── ReportRepo ──────────────────────────────────────────────────────────────


class ReportRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.s = session

    async def create(self, **kwargs: Any) -> Report:
        report = Report(**kwargs)
        self.s.add(report)
        await self.s.flush()
        return report

    async def get(self, report_id: str) -> Optional[Report]:
        return await self.s.get(Report, report_id)

    async def list_by_project(self, project_id: str) -> List[Report]:
        stmt = (
            select(Report)
            .where(Report.project_id == project_id)
            .order_by(Report.created_at.desc())
        )
        return list((await self.s.execute(stmt)).scalars().all())

    async def list_by_owner(self, owner_id: str, *, limit: int = 50, offset: int = 0) -> List[Report]:
        stmt = (
            select(Report)
            .where(Report.owner_id == owner_id)
            .order_by(Report.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list((await self.s.execute(stmt)).scalars().all())

    async def count_by_owner(self, owner_id: str) -> int:
        stmt = select(func.count()).select_from(Report).where(Report.owner_id == owner_id)
        return (await self.s.execute(stmt)).scalar_one()

    # ── share tokens ──

    async def create_share_token(self, report_id: str, *, ttl_days: int = 7) -> str:
        token = secrets.token_urlsafe(32)
        st = ShareToken(
            token=token,
            report_id=report_id,
            expires_at=datetime.now(timezone.utc) + timedelta(days=ttl_days),
        )
        self.s.add(st)
        await self.s.flush()
        return token

    async def get_share_token(self, token: str) -> Optional[ShareToken]:
        return await self.s.get(ShareToken, token)

    async def revoke_share_token(self, token: str) -> None:
        stmt = (
            update(ShareToken)
            .where(ShareToken.token == token)
            .values(revoked=True, revoked_at=datetime.now(timezone.utc))
        )
        await self.s.execute(stmt)


# ─── UserRepo ────────────────────────────────────────────────────────────────


class UserRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.s = session

    async def create(
        self,
        *,
        email: str,
        display_name: str,
        password_hash: str,
        role: str = "viewer",
    ) -> User:
        user = User(
            email=email,
            display_name=display_name,
            password_hash=password_hash,
            role=role,
        )
        self.s.add(user)
        await self.s.flush()
        return user

    async def get(self, user_id: str) -> Optional[User]:
        return await self.s.get(User, user_id)

    async def get_by_email(self, email: str) -> Optional[User]:
        stmt = select(User).where(User.email == email)
        return (await self.s.execute(stmt)).scalar_one_or_none()

    async def list_all(self, *, limit: int = 100, offset: int = 0) -> List[User]:
        stmt = select(User).order_by(User.created_at.desc()).limit(limit).offset(offset)
        return list((await self.s.execute(stmt)).scalars().all())

    async def count(self) -> int:
        stmt = select(func.count()).select_from(User)
        return (await self.s.execute(stmt)).scalar_one()

    async def update_role(self, user_id: str, role: str) -> None:
        stmt = (
            update(User)
            .where(User.id == user_id)
            .values(role=role, updated_at=datetime.now(timezone.utc))
        )
        await self.s.execute(stmt)

    async def set_active(self, user_id: str, is_active: bool) -> None:
        stmt = (
            update(User)
            .where(User.id == user_id)
            .values(is_active=is_active, updated_at=datetime.now(timezone.utc))
        )
        await self.s.execute(stmt)


# ─── SettingsRepo ─────────────────────────────────────────────────────────────


class SettingsRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.s = session

    async def get(self, key: str) -> Optional[SystemSetting]:
        return await self.s.get(SystemSetting, key)

    async def get_value(self, key: str) -> Optional[str]:
        setting = await self.get(key)
        return setting.value if setting else None

    async def upsert(self, key: str, value: str, *, is_secret: bool = False, updated_by: Optional[str] = None) -> None:
        setting = await self.get(key)
        if setting:
            setting.value = value
            setting.is_secret = is_secret
            setting.updated_by = updated_by
            setting.updated_at = datetime.now(timezone.utc)
        else:
            self.s.add(
                SystemSetting(key=key, value=value, is_secret=is_secret, updated_by=updated_by)
            )
        await self.s.flush()

    async def list_all(self, *, include_secrets: bool = False) -> Dict[str, str]:
        stmt = select(SystemSetting)
        if not include_secrets:
            stmt = stmt.where(SystemSetting.is_secret == False)  # noqa: E712
        rows = (await self.s.execute(stmt)).scalars().all()
        return {r.key: r.value for r in rows}


# ─── AuditLogRepo ─────────────────────────────────────────────────────────────


class AuditLogRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.s = session

    async def log(
        self,
        *,
        user_id: Optional[str],
        action: str,
        resource: str,
        resource_id: Optional[str] = None,
        detail: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
    ) -> None:
        entry = AuditLog(
            user_id=user_id,
            action=action,
            resource=resource,
            resource_id=resource_id,
            detail=detail,
            ip_address=ip_address,
        )
        self.s.add(entry)
        await self.s.flush()

    async def list_by_user(
        self, user_id: str, *, limit: int = 50, offset: int = 0
    ) -> List[AuditLog]:
        stmt = (
            select(AuditLog)
            .where(AuditLog.user_id == user_id)
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list((await self.s.execute(stmt)).scalars().all())
