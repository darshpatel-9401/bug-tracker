"""Tiny helpers so the tests read like a story instead of a pile of HTTP calls."""

PASSWORD = "Password123"


def register_user(client, email, name="Test User", password=PASSWORD):
    return client.post(
        "/api/auth/register",
        json={"email": email, "full_name": name, "password": password},
    )


def login_headers(client, email, name="Test User"):
    register_user(client, email, name)
    res = client.post("/api/auth/login", json={"email": email, "password": PASSWORD})
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def user_id(client, headers):
    return client.get("/api/auth/me", headers=headers).json()["id"]


def create_project(client, headers, name="Apollo", description=None):
    res = client.post("/api/projects", json={"name": name, "description": description}, headers=headers)
    assert res.status_code == 201, res.text
    return res.json()


def add_member(client, headers, project_id, email, role="developer"):
    return client.post(
        f"/api/projects/{project_id}/members",
        json={"email": email, "role": role},
        headers=headers,
    )


def create_ticket(client, headers, project_id, **fields):
    payload = {"title": "Login button does nothing"}
    payload.update(fields)
    return client.post(f"/api/projects/{project_id}/tickets", json=payload, headers=headers)


def make_ticket(client, headers, project_id, **fields):
    res = create_ticket(client, headers, project_id, **fields)
    assert res.status_code == 201, res.text
    return res.json()
