from datetime import timedelta

from app.security import create_access_token
from tests.helpers import PASSWORD, register_user


def test_register_creates_an_account_without_leaking_the_password(client):
    res = register_user(client, "New.Person@Example.com", "New Person")
    assert res.status_code == 201
    body = res.json()
    assert body["email"] == "new.person@example.com"
    assert body["full_name"] == "New Person"
    assert "password" not in body and "hashed_password" not in body


def test_registering_the_same_email_twice_is_a_conflict(client):
    assert register_user(client, "a@example.com").status_code == 201
    assert register_user(client, "A@EXAMPLE.com").status_code == 409


def test_weak_password_is_rejected(client):
    assert register_user(client, "a@example.com", password="short").status_code == 422


def test_bad_email_is_rejected(client):
    assert register_user(client, "nope").status_code == 422


def test_login_returns_a_working_token(client):
    register_user(client, "a@example.com", "Ann")
    res = client.post("/api/auth/login", json={"email": "a@example.com", "password": PASSWORD})
    assert res.status_code == 200
    assert res.json()["token_type"] == "bearer"
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {res.json()['access_token']}"})
    assert me.status_code == 200
    assert me.json()["email"] == "a@example.com"


def test_wrong_password_and_unknown_user_look_identical(client):
    register_user(client, "a@example.com")
    wrong = client.post("/api/auth/login", json={"email": "a@example.com", "password": "Wrong12345"})
    unknown = client.post("/api/auth/login", json={"email": "ghost@example.com", "password": PASSWORD})
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()


def test_me_requires_a_token(client):
    assert client.get("/api/auth/me").status_code == 401


def test_me_rejects_garbage_token(client):
    res = client.get("/api/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert res.status_code == 401


def test_me_rejects_expired_token(client):
    register_user(client, "a@example.com")
    token = create_access_token(1, expires_delta=timedelta(minutes=-5))
    assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_token_for_a_user_that_does_not_exist_is_rejected(client):
    token = create_access_token(9999)
    assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_every_protected_route_refuses_anonymous_requests(client):
    for method, url in [
        ("get", "/api/projects"),
        ("post", "/api/projects"),
        ("get", "/api/projects/1"),
        ("get", "/api/projects/1/tickets"),
        ("get", "/api/tickets/1"),
        ("get", "/api/tickets/1/comments"),
        ("get", "/api/attachments/1/download"),
    ]:
        res = client.request(method, url, json={"name": "x"} if method == "post" else None)
        assert res.status_code == 401, f"{method} {url}"


def test_health_check_and_security_headers(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.headers["x-content-type-options"] == "nosniff"
    assert res.headers["x-frame-options"] == "DENY"
