"""Role checks. Roles form a ladder: an admin can do everything a developer can,
and a developer can do everything a viewer can."""
from app.enums import Role

_RANK = {Role.viewer: 1, Role.developer: 2, Role.admin: 3}


def has_role(actual, minimum: Role) -> bool:
    """True if `actual` (a Role or the plain string stored in the DB) is at least `minimum`.
    Anything we do not recognise gets no access."""
    try:
        actual_role = Role(actual)
    except ValueError:
        return False
    return _RANK[actual_role] >= _RANK[minimum]
