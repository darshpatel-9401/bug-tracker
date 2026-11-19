import os

from app.config import settings
from tests.helpers import make_ticket

PNG = b"\x89PNG\r\n\x1a\n" + b"fake-image-bytes" * 4


def upload(client, headers, ticket_id, name="shot.png", data=PNG, mime="image/png"):
    return client.post(
        f"/api/tickets/{ticket_id}/attachments",
        files={"file": (name, data, mime)},
        headers=headers,
    )


def test_developer_uploads_a_screenshot_and_everyone_can_list_and_download_it(client, team):
    ticket = make_ticket(client, team.admin, team.project_id)
    res = upload(client, team.dev, ticket["id"])
    assert res.status_code == 201
    att = res.json()
    assert att["filename"] == "shot.png"
    assert att["content_type"] == "image/png"
    assert att["size"] == len(PNG)
    assert "stored_name" not in att  # server paths stay private

    listing = client.get(f"/api/tickets/{ticket['id']}/attachments", headers=team.viewer)
    assert listing.status_code == 200 and len(listing.json()) == 1

    download = client.get(f"/api/attachments/{att['id']}/download", headers=team.viewer)
    assert download.status_code == 200
    assert download.content == PNG
    assert download.headers["x-content-type-options"] == "nosniff"


def test_viewer_cannot_upload_but_outsider_cannot_see_anything(client, team):
    ticket = make_ticket(client, team.admin, team.project_id)
    assert upload(client, team.viewer, ticket["id"]).status_code == 403
    assert upload(client, team.outsider, ticket["id"]).status_code == 404
    att = upload(client, team.dev, ticket["id"]).json()
    assert client.get(f"/api/attachments/{att['id']}/download", headers=team.outsider).status_code == 404
    assert client.get(f"/api/tickets/{ticket['id']}/attachments", headers=team.outsider).status_code == 404


def test_dangerous_or_mismatched_files_are_rejected(client, team):
    ticket = make_ticket(client, team.admin, team.project_id)
    assert upload(client, team.dev, ticket["id"], "evil.exe", b"MZ....", "application/octet-stream").status_code == 400
    assert upload(client, team.dev, ticket["id"], "page.html", b"<script>1</script>", "text/html").status_code == 400
    assert upload(client, team.dev, ticket["id"], "fake.png", b"<html></html>", "image/png").status_code == 400
    assert upload(client, team.dev, ticket["id"], "empty.png", b"", "image/png").status_code == 400


def test_oversized_files_are_rejected(client, team, monkeypatch):
    monkeypatch.setattr(settings, "max_upload_bytes", 100)
    ticket = make_ticket(client, team.admin, team.project_id)
    big = PNG + b"0" * 200
    assert upload(client, team.dev, ticket["id"], data=big).status_code == 413


def test_path_traversal_in_filename_is_neutralised(client, team):
    ticket = make_ticket(client, team.admin, team.project_id)
    res = upload(client, team.dev, ticket["id"], name="../../evil.png")
    assert res.status_code == 201
    assert res.json()["filename"] == "evil.png"
    stored = os.listdir(settings.upload_dir)
    assert len(stored) == 1 and ".." not in stored[0] and stored[0].endswith(".png")


def test_uploader_or_admin_can_delete_and_the_file_leaves_the_disk(client, team):
    ticket = make_ticket(client, team.admin, team.project_id)
    att = upload(client, team.dev, ticket["id"]).json()
    url = f"/api/attachments/{att['id']}"
    assert os.listdir(settings.upload_dir)
    assert client.delete(url, headers=team.viewer).status_code == 403
    assert client.delete(url, headers=team.outsider).status_code == 404
    assert client.delete(url, headers=team.dev).status_code == 204
    assert os.listdir(settings.upload_dir) == []
    assert client.get(f"{url}/download", headers=team.admin).status_code == 404


def test_another_developer_cannot_delete_someone_elses_upload_but_admin_can(client, team):
    from tests.helpers import add_member, login_headers

    dev2 = login_headers(client, "dev2@example.com")
    add_member(client, team.admin, team.project_id, "dev2@example.com", "developer")
    ticket = make_ticket(client, team.admin, team.project_id)
    att = upload(client, team.dev, ticket["id"]).json()
    url = f"/api/attachments/{att['id']}"
    assert client.delete(url, headers=dev2).status_code == 403
    assert client.delete(url, headers=team.admin).status_code == 204


def test_deleting_a_ticket_or_project_cleans_up_its_files(client, team):
    ticket = make_ticket(client, team.admin, team.project_id)
    upload(client, team.dev, ticket["id"])
    assert len(os.listdir(settings.upload_dir)) == 1
    assert client.delete(f"/api/tickets/{ticket['id']}", headers=team.admin).status_code == 204
    assert os.listdir(settings.upload_dir) == []

    ticket2 = make_ticket(client, team.admin, team.project_id)
    upload(client, team.dev, ticket2["id"])
    assert client.delete(f"/api/projects/{team.project_id}", headers=team.admin).status_code == 204
    assert os.listdir(settings.upload_dir) == []
