from tests.helpers import make_ticket


def post_comment(client, headers, ticket_id, body="Looks like a race condition", parent_id=None):
    payload = {"body": body}
    if parent_id is not None:
        payload["parent_id"] = parent_id
    return client.post(f"/api/tickets/{ticket_id}/comments", json=payload, headers=headers)


def test_developer_comments_and_everyone_on_the_project_can_read(client, team):
    ticket = make_ticket(client, team.admin, team.project_id)
    res = post_comment(client, team.dev, ticket["id"])
    assert res.status_code == 201
    assert res.json()["author"]["email"] == "dev@example.com"
    assert res.json()["parent_id"] is None
    listing = client.get(f"/api/tickets/{ticket['id']}/comments", headers=team.viewer)
    assert listing.status_code == 200 and len(listing.json()) == 1


def test_viewer_cannot_comment_and_outsider_cannot_read(client, team):
    ticket = make_ticket(client, team.admin, team.project_id)
    assert post_comment(client, team.viewer, ticket["id"]).status_code == 403
    assert post_comment(client, team.outsider, ticket["id"]).status_code == 404
    assert client.get(f"/api/tickets/{ticket['id']}/comments", headers=team.outsider).status_code == 404


def test_blank_comment_is_rejected(client, team):
    ticket = make_ticket(client, team.admin, team.project_id)
    assert post_comment(client, team.dev, ticket["id"], body="   ").status_code == 422


def test_replies_are_threaded(client, team):
    ticket = make_ticket(client, team.admin, team.project_id)
    root = post_comment(client, team.dev, ticket["id"], "Root").json()
    reply = post_comment(client, team.admin, ticket["id"], "Reply", parent_id=root["id"]).json()
    assert reply["parent_id"] == root["id"]
    listing = client.get(f"/api/tickets/{ticket['id']}/comments", headers=team.dev).json()
    assert [c["body"] for c in listing] == ["Root", "Reply"]


def test_cannot_reply_to_a_comment_on_another_ticket(client, team):
    a = make_ticket(client, team.admin, team.project_id, title="A")
    b = make_ticket(client, team.admin, team.project_id, title="B")
    on_a = post_comment(client, team.dev, a["id"]).json()
    assert post_comment(client, team.dev, b["id"], parent_id=on_a["id"]).status_code == 400
    assert post_comment(client, team.dev, b["id"], parent_id=99999).status_code == 400


def test_only_the_author_can_edit(client, team):
    ticket = make_ticket(client, team.admin, team.project_id)
    comment = post_comment(client, team.dev, ticket["id"]).json()
    url = f"/api/comments/{comment['id']}"
    ok = client.patch(url, json={"body": "Edited"}, headers=team.dev)
    assert ok.status_code == 200 and ok.json()["body"] == "Edited"
    assert client.patch(url, json={"body": "Hijack"}, headers=team.admin).status_code == 403
    assert client.patch(url, json={"body": "Hijack"}, headers=team.viewer).status_code == 403
    assert client.patch(url, json={"body": "Hijack"}, headers=team.outsider).status_code == 404


def test_author_or_admin_can_delete_but_nobody_else(client, team):
    ticket = make_ticket(client, team.admin, team.project_id)
    comment = post_comment(client, team.dev, ticket["id"]).json()
    url = f"/api/comments/{comment['id']}"
    assert client.delete(url, headers=team.viewer).status_code == 403
    assert client.delete(url, headers=team.outsider).status_code == 404
    assert client.delete(url, headers=team.admin).status_code == 204
    assert client.delete(url, headers=team.admin).status_code == 404


def test_deleting_a_comment_removes_its_replies(client, team):
    ticket = make_ticket(client, team.admin, team.project_id)
    root = post_comment(client, team.dev, ticket["id"], "Root").json()
    child = post_comment(client, team.admin, ticket["id"], "Child", parent_id=root["id"]).json()
    post_comment(client, team.dev, ticket["id"], "Grandchild", parent_id=child["id"])
    post_comment(client, team.dev, ticket["id"], "Unrelated")
    assert client.delete(f"/api/comments/{root['id']}", headers=team.dev).status_code == 204
    left = client.get(f"/api/tickets/{ticket['id']}/comments", headers=team.dev).json()
    assert [c["body"] for c in left] == ["Unrelated"]
