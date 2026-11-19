import pytest

from app.enums import Role
from app.permissions import has_role


@pytest.mark.parametrize(
    "actual, needed, expected",
    [
        (Role.admin, Role.admin, True),
        (Role.admin, Role.developer, True),
        (Role.admin, Role.viewer, True),
        (Role.developer, Role.admin, False),
        (Role.developer, Role.developer, True),
        (Role.developer, Role.viewer, True),
        (Role.viewer, Role.admin, False),
        (Role.viewer, Role.developer, False),
        (Role.viewer, Role.viewer, True),
    ],
)
def test_role_hierarchy(actual, needed, expected):
    assert has_role(actual, needed) is expected


def test_plain_strings_from_the_database_work_too():
    assert has_role("developer", Role.viewer) is True
    assert has_role("viewer", Role.developer) is False


def test_unknown_role_never_gets_access():
    assert has_role("superuser", Role.viewer) is False
    assert has_role("", Role.viewer) is False
