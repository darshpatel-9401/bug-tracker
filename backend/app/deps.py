"""Reusable building blocks for the routers: who is calling, and are they allowed in?"""
from typing import Optional, Tuple

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.enums import Role
from app.models import ProjectMember, Ticket, User
from app.permissions import has_role
from app.security import TokenError, decode_access_token

_bearer = HTTPBearer(auto_error=False)


def _unauthorized(detail: str = "Not authenticated") -> HTTPException:
    return HTTPException(status_code=401, detail=detail, headers={"WWW-Authenticate": "Bearer"})


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise _unauthorized()
    try:
        user_id = decode_access_token(credentials.credentials)
    except TokenError:
        raise _unauthorized("Invalid or expired token") from None
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise _unauthorized("Invalid or expired token")
    return user


def require_membership(db: Session, project_id: int, user: User, minimum: Role = Role.viewer) -> ProjectMember:
    """Return the caller's membership, or stop the request.

    Non-members get 404 (not 403) so nobody can probe which project ids exist.
    Members with too low a role get 403.
    """
    member = db.scalar(
        select(ProjectMember).where(ProjectMember.project_id == project_id, ProjectMember.user_id == user.id)
    )
    if member is None:
        raise HTTPException(status_code=404, detail="Not found")
    if not has_role(member.role, minimum):
        raise HTTPException(status_code=403, detail="You do not have permission to do that")
    return member


def get_ticket_for_user(
    db: Session, ticket_id: int, user: User, minimum: Role = Role.viewer
) -> Tuple[Ticket, ProjectMember]:
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Not found")
    member = require_membership(db, ticket.project_id, user, minimum)
    return ticket, member
