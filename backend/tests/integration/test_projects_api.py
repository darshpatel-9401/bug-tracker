from tests.helpers import add_member, create_project, create_ticket, login_headers, make_ticket


def test_creator_becomes_admin_and_sees_the_project(client):
    owner = login_headers(client, "owner@example.com")
    project = create_project(client, owner, "Apollo", "Moon stuff")
    assert project["my_role"] == "admin"
    listing = client.get("/api/projects", headers=owner).json()
    assert [p["name"] for p in listing] == ["Apollo"]


def test_people_only_see_projects_they_belong_to(client, team):
    other = login_headers(client, "someone@example.com")
    assert client.get("/api/projects", headers=other).json() == []
    assert client.get("/api/projects", headers=team.viewer).json()[0]["my_role"] == "viewer"


def test_non_member_gets_404_not_403_so_existence_is_not_leaked(client, team):
    assert client.get(f"/api/projects/{team.project_id}", headers=team.outsider).status_code == 404


def test_detail_includes_members_with_roles(client, team):
    detail = client.get(f"/api/projects/{team.project_id}", headers=team.admin).json()
    roles = {m["user"]["email"]: m["role"] for m in detail["members"]}
    assert roles == {
        "admin@example.com": "admin",
        "dev@example.com": "developer",
        "viewer@example.com": "viewer",
    }


def test_blank_project_name_is_rejected(client):
    owner = login_headers(client, "owner@example.com")
    assert client.post("/api/projects", json={"name": "   "}, headers=owner).status_code == 422


def test_only_admin_can_edit_project(client, team):
    url = f"/api/projects/{team.project_id}"
    assert client.patch(url, json={"name": "Hax"}, headers=team.dev).status_code == 403
    assert client.patch(url, json={"name": "Hax"}, headers=team.viewer).status_code == 403
    assert client.patch(url, json={"name": "Hax"}, headers=team.outsider).status_code == 404
    ok = client.patch(url, json={"name": "Apollo 2"}, headers=team.admin)
    assert ok.status_code == 200 and ok.json()["name"] == "Apollo 2"


def test_only_admin_can_delete_project_and_it_takes_its_tickets_along(client, team):
    ticket = make_ticket(client, team.dev, team.project_id)
    url = f"/api/projects/{team.project_id}"
    assert client.delete(url, headers=team.dev).status_code == 403
    assert client.delete(url, headers=team.admin).status_code == 204
    assert client.get(url, headers=team.admin).status_code == 404
    assert client.get(f"/api/tickets/{ticket['id']}", headers=team.admin).status_code == 404


def test_only_admin_can_add_members(client, team):
    newcomer = login_headers(client, "new@example.com")
    assert add_member(client, team.dev, team.project_id, "new@example.com").status_code == 403
    assert add_member(client, team.outsider, team.project_id, "new@example.com").status_code == 404
    res = add_member(client, team.admin, team.project_id, "new@example.com", "viewer")
    assert res.status_code == 201
    assert res.json()["role"] == "viewer"
    assert client.get(f"/api/projects/{team.project_id}", headers=newcomer).status_code == 200


def test_adding_unknown_or_duplicate_member_fails(client, team):
    assert add_member(client, team.admin, team.project_id, "ghost@example.com").status_code == 404
    assert add_member(client, team.admin, team.project_id, "dev@example.com").status_code == 409


def test_invalid_role_is_rejected(client, team):
    assert add_member(client, team.admin, team.project_id, "outsider@example.com", "emperor").status_code == 422


def test_admin_can_change_a_role(client, team):
    url = f"/api/projects/{team.project_id}/members/{team.viewer_id}"
    res = client.patch(url, json={"role": "developer"}, headers=team.admin)
    assert res.status_code == 200 and res.json()["role"] == "developer"
    assert client.patch(url, json={"role": "admin"}, headers=team.dev).status_code == 403


def test_the_last_admin_cannot_be_demoted_or_removed(client, team):
    url = f"/api/projects/{team.project_id}/members/{team.admin_id}"
    assert client.patch(url, json={"role": "viewer"}, headers=team.admin).status_code == 400
    assert client.delete(url, headers=team.admin).status_code == 400


def test_with_a_second_admin_the_first_can_step_down(client, team):
    promote = f"/api/projects/{team.project_id}/members/{team.dev_id}"
    assert client.patch(promote, json={"role": "admin"}, headers=team.admin).status_code == 200
    demote = f"/api/projects/{team.project_id}/members/{team.admin_id}"
    assert client.patch(demote, json={"role": "viewer"}, headers=team.dev).status_code == 200


def test_changing_role_of_a_non_member_is_404(client, team):
    url = f"/api/projects/{team.project_id}/members/{team.outsider_id}"
    assert client.patch(url, json={"role": "viewer"}, headers=team.admin).status_code == 404


def test_removing_a_member_unassigns_their_tickets_and_cuts_access(client, team):
    ticket = make_ticket(client, team.admin, team.project_id, assignee_id=team.dev_id)
    url = f"/api/projects/{team.project_id}/members/{team.dev_id}"
    assert client.delete(url, headers=team.admin).status_code == 204
    after = client.get(f"/api/tickets/{ticket['id']}", headers=team.admin).json()
    assert after["assignee"] is None
    assert client.get(f"/api/projects/{team.project_id}", headers=team.dev).status_code == 404
