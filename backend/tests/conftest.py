"""Shared fixtures.

Every test gets a brand-new in-memory SQLite database and its own upload folder,
so tests can never leak data into each other.
"""
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from tests.helpers import add_member, create_project, login_headers, user_id


@pytest.fixture()
def client(tmp_path, monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # one shared connection so the in-memory db survives between requests
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path / "uploads"))

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    engine.dispose()


@pytest.fixture()
def team(client):
    """A project with one person in every role, plus someone who is not a member."""
    admin = login_headers(client, "admin@example.com", "Ada Admin")
    dev = login_headers(client, "dev@example.com", "Dev Dan")
    viewer = login_headers(client, "viewer@example.com", "Vic Viewer")
    outsider = login_headers(client, "outsider@example.com", "Olly Outsider")

    project = create_project(client, admin, "Apollo")
    assert add_member(client, admin, project["id"], "dev@example.com", "developer").status_code == 201
    assert add_member(client, admin, project["id"], "viewer@example.com", "viewer").status_code == 201

    return SimpleNamespace(
        project_id=project["id"],
        admin=admin,
        dev=dev,
        viewer=viewer,
        outsider=outsider,
        admin_id=user_id(client, admin),
        dev_id=user_id(client, dev),
        viewer_id=user_id(client, viewer),
        outsider_id=user_id(client, outsider),
    )
