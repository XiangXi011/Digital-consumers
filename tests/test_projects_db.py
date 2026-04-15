"""Database-layer CRUD tests for Project and Report repositories."""

import os
import uuid

import pytest

# Ensure test mode
os.environ["_"] = "pytest"

from backend.db.models import Base, Project, Report
from backend.db.repositories import ProjectRepo, ReportRepo, UserRepo
from backend.db.session import async_session


@pytest.fixture(autouse=True)
async def _create_tables():
    """Create all tables before each test, drop after."""
    from backend.db.session import engine as _engine

    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.asyncio
async def test_project_crud():
    async with async_session() as session:
        repo = ProjectRepo(session)
        project = await repo.create(
            owner_id=str(uuid.uuid4()),
            session_id=f"test-{uuid.uuid4().hex[:8]}",
            name="Test Project",
            project_type="concept_test",
            fields={"product_info": {"value": "test", "status": "provided"}},
        )
        await session.commit()

        assert project.id is not None
        assert project.name == "Test Project"
        assert project.fields["product_info"]["value"] == "test"

        fetched = await repo.get(project.id)
        assert fetched is not None
        assert fetched.name == "Test Project"


@pytest.mark.asyncio
async def test_project_get_by_session_id():
    async with async_session() as session:
        repo = ProjectRepo(session)
        sid = f"sid-{uuid.uuid4().hex[:8]}"
        await repo.create(owner_id=str(uuid.uuid4()), session_id=sid, name="By SID")
        await session.commit()

        found = await repo.get_by_session_id(sid)
        assert found is not None
        assert found.name == "By SID"


@pytest.mark.asyncio
async def test_project_list_by_owner():
    async with async_session() as session:
        repo = ProjectRepo(session)
        owner = str(uuid.uuid4())
        for i in range(3):
            await repo.create(owner_id=owner, session_id=f"p{i}-{uuid.uuid4().hex[:8]}", name=f"P{i}")
        await session.commit()

        projects = await repo.list_by_owner(owner)
        assert len(projects) == 3


@pytest.mark.asyncio
async def test_project_update():
    async with async_session() as session:
        repo = ProjectRepo(session)
        p = await repo.create(
            owner_id=str(uuid.uuid4()),
            session_id=f"upd-{uuid.uuid4().hex[:8]}",
            status="collecting",
        )
        await session.commit()

        await repo.update(p.id, status="completed")
        await session.commit()

        fetched = await repo.get(p.id)
        assert fetched.status == "completed"


@pytest.mark.asyncio
async def test_report_crud():
    async with async_session() as session:
        proj_repo = ProjectRepo(session)
        owner_id = str(uuid.uuid4())
        project = await proj_repo.create(
            owner_id=owner_id,
            session_id=f"rpt-{uuid.uuid4().hex[:8]}",
        )

        report_repo = ReportRepo(session)
        report = await report_repo.create(
            project_id=project.id,
            owner_id=owner_id,
            report_type="full",
            name="Test Report",
        )
        await session.commit()

        assert report.id is not None
        reports = await report_repo.list_by_project(project.id)
        assert len(reports) == 1
        assert reports[0].name == "Test Report"


@pytest.mark.asyncio
async def test_share_token_create_and_revoke():
    async with async_session() as session:
        proj_repo = ProjectRepo(session)
        owner_id = str(uuid.uuid4())
        project = await proj_repo.create(
            owner_id=owner_id,
            session_id=f"share-{uuid.uuid4().hex[:8]}",
        )
        report_repo = ReportRepo(session)
        report = await report_repo.create(
            project_id=project.id,
            owner_id=owner_id,
        )
        await session.commit()

        token = await report_repo.create_share_token(report.id)
        assert len(token) > 20

        st = await report_repo.get_share_token(token)
        assert st is not None
        assert st.revoked is False

        await report_repo.revoke_share_token(token)
        await session.commit()

        st2 = await report_repo.get_share_token(token)
        assert st2.revoked is True
