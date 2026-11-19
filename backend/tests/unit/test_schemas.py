import pytest
from pydantic import ValidationError

from app.enums import Priority, TicketStatus
from app.schemas import LoginIn, RegisterIn, TicketCreate, TicketUpdate


def test_register_lowercases_and_trims():
    data = RegisterIn(email="Dev@Example.COM", full_name="  Asha Patel ", password="Password123")
    assert data.email == "dev@example.com"
    assert data.full_name == "Asha Patel"


@pytest.mark.parametrize("pw", ["short1", "allletters", "12345678"])
def test_weak_passwords_are_rejected(pw):
    with pytest.raises(ValidationError):
        RegisterIn(email="a@example.com", full_name="A", password=pw)


def test_overlong_password_is_rejected():
    with pytest.raises(ValidationError):
        RegisterIn(email="a@example.com", full_name="A", password="a1" * 100)


def test_bad_email_is_rejected():
    with pytest.raises(ValidationError):
        RegisterIn(email="not-an-email", full_name="A", password="Password123")


def test_login_normalises_email():
    assert LoginIn(email="  A@B.com ", password="x").email == "a@b.com"


def test_ticket_defaults():
    t = TicketCreate(title="Crash on save")
    assert t.status == TicketStatus.todo
    assert t.priority == Priority.medium
    assert t.assignee_id is None


def test_ticket_title_cannot_be_blank():
    with pytest.raises(ValidationError):
        TicketCreate(title="   ")


def test_ticket_enum_values_are_checked():
    with pytest.raises(ValidationError):
        TicketCreate(title="x", priority="urgent!!")


def test_update_only_reports_fields_the_client_sent():
    u = TicketUpdate(status="done")
    assert u.model_dump(exclude_unset=True) == {"status": TicketStatus.done}


def test_update_allows_explicit_null_assignee():
    u = TicketUpdate(assignee_id=None)
    assert u.model_dump(exclude_unset=True) == {"assignee_id": None}


@pytest.mark.parametrize("field", ["title", "type", "status", "priority"])
def test_update_rejects_null_for_required_fields(field):
    with pytest.raises(ValidationError):
        TicketUpdate(**{field: None})
