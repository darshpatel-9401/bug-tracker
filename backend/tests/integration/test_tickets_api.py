from tests.helpers import create_ticket, make_ticket


def test_developer_creates_a_ticket_with_sensible_defaults(client, team):
    ticket = make_ticket(client, team.dev, team.project_id, title="Crash on save")
    assert ticket["title"] == "Crash on save"
    assert ticket["status"] == "todo"
    assert ticket["priority"] == "medium"
    assert ticket["type"] == "task"
    assert ticket["reporter"]["email"] == "dev@example.com"
    assert ticket["assignee"] is None


def test_viewer_cannot_create_and_outsider_cannot_even_see_the_project(client, team):
    assert create_ticket(client, team.viewer, team.project_id).status_code == 403
    assert create_ticket(client, team.outsider, team.project_id).status_code == 404


def test_bad_input_is_rejected(client, team):
    assert create_ticket(client, team.dev, team.project_id, title="   ").status_code == 422
    assert create_ticket(client, team.dev, team.project_id, priority="urgent!!").status_code == 422
    assert create_ticket(client, team.dev, team.project_id, type="epic").status_code == 422
    assert create_ticket(client, team.dev, team.project_id, title="x" * 201).status_code == 422


def test_ticket_can_be_assigned_to_a_developer_or_admin_only(client, team):
    assert create_ticket(client, team.admin, team.project_id, assignee_id=team.dev_id).status_code == 201
    assert create_ticket(client, team.admin, team.project_id, assignee_id=team.admin_id).status_code == 201
    assert create_ticket(client, team.admin, team.project_id, assignee_id=team.viewer_id).status_code == 400
    assert create_ticket(client, team.admin, team.project_id, assignee_id=team.outsider_id).status_code == 400
    assert create_ticket(client, team.admin, team.project_id, assignee_id=99999).status_code == 400


def test_members_can_read_a_ticket_but_outsiders_cannot(client, team):
    ticket = make_ticket(client, team.dev, team.project_id)
    url = f"/api/tickets/{ticket['id']}"
    assert client.get(url, headers=team.viewer).status_code == 200
    assert client.get(url, headers=team.outsider).status_code == 404
    assert client.get("/api/tickets/424242", headers=team.admin).status_code == 404


def test_list_filters(client, team):
    p = team.project_id
    make_ticket(client, team.dev, p, title="Login crash", type="bug", priority="critical", assignee_id=team.dev_id)
    make_ticket(client, team.dev, p, title="Dark mode", type="feature", priority="low", status="in_progress")
    make_ticket(client, team.dev, p, title="Update docs", type="task", priority="low", description="mentions login flow")
    url = f"/api/projects/{p}/tickets"

    everything = client.get(url, headers=team.viewer).json()
    assert everything["total"] == 3

    def titles(**params):
        res = client.get(url, params=params, headers=team.viewer)
        assert res.status_code == 200
        return sorted(t["title"] for t in res.json()["items"])

    assert titles(type="bug") == ["Login crash"]
    assert titles(priority="low") == ["Dark mode", "Update docs"]
    assert titles(status="in_progress") == ["Dark mode"]
    assert titles(assignee_id=team.dev_id) == ["Login crash"]
    assert titles(q="login") == ["Login crash", "Update docs"]  # title OR description, case-insensitive
    assert titles(q="LOGIN", priority="low") == ["Update docs"]  # filters combine
    assert titles(q="nothing-matches-this") == []


def test_search_treats_percent_and_underscore_literally(client, team):
    p = team.project_id
    make_ticket(client, team.dev, p, title="Discount shows 100% wrong")
    make_ticket(client, team.dev, p, title="Something else entirely")
    make_ticket(client, team.dev, p, title="snake_case naming")
    url = f"/api/projects/{p}/tickets"
    got = client.get(url, params={"q": "%"}, headers=team.dev).json()
    assert [t["title"] for t in got["items"]] == ["Discount shows 100% wrong"]
    got = client.get(url, params={"q": "_"}, headers=team.dev).json()
    assert [t["title"] for t in got["items"]] == ["snake_case naming"]


def test_search_with_sql_injection_text_is_harmless(client, team):
    make_ticket(client, team.dev, team.project_id, title="Normal ticket")
    res = client.get(
        f"/api/projects/{team.project_id}/tickets",
        params={"q": "'; DROP TABLE tickets; --"},
        headers=team.dev,
    )
    assert res.status_code == 200 and res.json()["total"] == 0
    assert client.get(f"/api/projects/{team.project_id}/tickets", headers=team.dev).json()["total"] == 1


def test_pagination_reports_the_full_total(client, team):
    for n in range(5):
        make_ticket(client, team.dev, team.project_id, title=f"Ticket {n}")
    url = f"/api/projects/{team.project_id}/tickets"
    page = client.get(url, params={"limit": 2, "skip": 0}, headers=team.dev).json()
    assert page["total"] == 5 and len(page["items"]) == 2
    assert page["items"][0]["title"] == "Ticket 4"  # newest first
    last = client.get(url, params={"limit": 2, "skip": 4}, headers=team.dev).json()
    assert len(last["items"]) == 1


def test_pagination_limits_are_enforced(client, team):
    url = f"/api/projects/{team.project_id}/tickets"
    assert client.get(url, params={"limit": 201}, headers=team.dev).status_code == 422
    assert client.get(url, params={"limit": 0}, headers=team.dev).status_code == 422
    assert client.get(url, params={"skip": -1}, headers=team.dev).status_code == 422


def test_tickets_from_other_projects_never_show_up(client, team):
    from tests.helpers import create_project

    other = create_project(client, team.outsider, "Secret project")
    make_ticket(client, team.outsider, other["id"], title="Top secret")
    mine = client.get(f"/api/projects/{team.project_id}/tickets", headers=team.admin).json()
    assert mine["total"] == 0


def test_developer_can_move_a_ticket_between_columns(client, team):
    ticket = make_ticket(client, team.admin, team.project_id)
    res = client.patch(f"/api/tickets/{ticket['id']}", json={"status": "in_review"}, headers=team.dev)
    assert res.status_code == 200 and res.json()["status"] == "in_review"


def test_viewer_cannot_edit_and_outsider_cannot_find_it(client, team):
    ticket = make_ticket(client, team.admin, team.project_id)
    url = f"/api/tickets/{ticket['id']}"
    assert client.patch(url, json={"status": "done"}, headers=team.viewer).status_code == 403
    assert client.patch(url, json={"status": "done"}, headers=team.outsider).status_code == 404


def test_edit_can_assign_and_unassign(client, team):
    ticket = make_ticket(client, team.admin, team.project_id)
    url = f"/api/tickets/{ticket['id']}"
    res = client.patch(url, json={"assignee_id": team.dev_id}, headers=team.admin)
    assert res.json()["assignee"]["id"] == team.dev_id
    res = client.patch(url, json={"assignee_id": None}, headers=team.admin)
    assert res.json()["assignee"] is None


def test_edit_cannot_assign_to_a_viewer(client, team):
    ticket = make_ticket(client, team.admin, team.project_id)
    res = client.patch(f"/api/tickets/{ticket['id']}", json={"assignee_id": team.viewer_id}, headers=team.admin)
    assert res.status_code == 400


def test_edit_rejects_nulls_for_required_fields(client, team):
    ticket = make_ticket(client, team.admin, team.project_id)
    url = f"/api/tickets/{ticket['id']}"
    for field in ("title", "status", "priority", "type"):
        assert client.patch(url, json={field: None}, headers=team.admin).status_code == 422


def test_empty_patch_changes_nothing(client, team):
    ticket = make_ticket(client, team.admin, team.project_id, title="Keep me")
    res = client.patch(f"/api/tickets/{ticket['id']}", json={}, headers=team.admin)
    assert res.status_code == 200 and res.json()["title"] == "Keep me"


def test_client_cannot_overwrite_server_controlled_fields(client, team):
    ticket = make_ticket(client, team.dev, team.project_id)
    client.patch(
        f"/api/tickets/{ticket['id']}",
        json={"reporter_id": team.admin_id, "project_id": 999, "id": 999},
        headers=team.admin,
    )
    after = client.get(f"/api/tickets/{ticket['id']}", headers=team.admin).json()
    assert after["id"] == ticket["id"]
    assert after["project_id"] == team.project_id
    assert after["reporter"]["id"] == team.dev_id


def test_delete_rules(client, team):
    mine = make_ticket(client, team.dev, team.project_id, title="Dev's own")
    theirs = make_ticket(client, team.admin, team.project_id, title="Admin's")
    assert client.delete(f"/api/tickets/{theirs['id']}", headers=team.dev).status_code == 403
    assert client.delete(f"/api/tickets/{mine['id']}", headers=team.viewer).status_code == 403
    assert client.delete(f"/api/tickets/{mine['id']}", headers=team.outsider).status_code == 404
    assert client.delete(f"/api/tickets/{mine['id']}", headers=team.dev).status_code == 204
    assert client.delete(f"/api/tickets/{theirs['id']}", headers=team.admin).status_code == 204
    assert client.get(f"/api/tickets/{mine['id']}", headers=team.admin).status_code == 404
