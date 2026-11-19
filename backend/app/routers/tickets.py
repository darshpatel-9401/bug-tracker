from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.deps import get_current_user, get_ticket_for_user, require_membership
from app.enums import Priority, Role, TicketStatus, TicketType
from app.models import ProjectMember, Ticket, User
from app.permissions import has_role
from app.schemas import TicketCreate, TicketOut, TicketPage, TicketUpdate
from app.uploads_store import remove_files

router = APIRouter(tags=["tickets"])


def _check_assignee(db: Session, project_id: int, assignee_id: int) -> None:
    member = db.scalar(
        select(ProjectMember).where(ProjectMember.project_id == project_id, ProjectMember.user_id == assignee_id)
    )
    if member is None or not has_role(member.role, Role.developer):
        raise HTTPException(status_code=400, detail="Assignee must be a developer or admin on this project")


def _escape_like(term: str) -> str:
    """Make % and _ match themselves instead of acting as wildcards."""
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


@router.post("/projects/{project_id}/tickets", response_model=TicketOut, status_code=201)
def create_ticket(
    project_id: int,
    payload: TicketCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_membership(db, project_id, user, Role.developer)
    if payload.assignee_id is not None:
        _check_assignee(db, project_id, payload.assignee_id)
    ticket = Ticket(
        project_id=project_id,
        title=payload.title,
        description=payload.description,
        type=payload.type.value,
        status=payload.status.value,
        priority=payload.priority.value,
        reporter_id=user.id,
        assignee_id=payload.assignee_id,
    )
    db.add(ticket)
    db.commit()
    return ticket


@router.get("/projects/{project_id}/tickets", response_model=TicketPage)
def list_tickets(
    project_id: int,
    status: Optional[TicketStatus] = None,
    priority: Optional[Priority] = None,
    type: Optional[TicketType] = None,
    assignee_id: Optional[int] = None,
    q: Optional[str] = Query(None, max_length=100),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_membership(db, project_id, user, Role.viewer)

    query = select(Ticket).where(Ticket.project_id == project_id)
    if status is not None:
        query = query.where(Ticket.status == status.value)
    if priority is not None:
        query = query.where(Ticket.priority == priority.value)
    if type is not None:
        query = query.where(Ticket.type == type.value)
    if assignee_id is not None:
        query = query.where(Ticket.assignee_id == assignee_id)
    if q and q.strip():
        like = f"%{_escape_like(q.strip())}%"
        query = query.where(or_(Ticket.title.ilike(like, escape="\\"), Ticket.description.ilike(like, escape="\\")))

    total = db.scalar(select(func.count()).select_from(query.subquery()))
    items = db.scalars(
        query.options(selectinload(Ticket.reporter), selectinload(Ticket.assignee))
        .order_by(Ticket.id.desc())
        .offset(skip)
        .limit(limit)
    ).all()
    return TicketPage(items=[TicketOut.model_validate(t) for t in items], total=total)


@router.get("/tickets/{ticket_id}", response_model=TicketOut)
def get_ticket(ticket_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ticket, _ = get_ticket_for_user(db, ticket_id, user, Role.viewer)
    return ticket


@router.patch("/tickets/{ticket_id}", response_model=TicketOut)
def update_ticket(
    ticket_id: int,
    payload: TicketUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    ticket, _ = get_ticket_for_user(db, ticket_id, user, Role.developer)
    changes = payload.model_dump(exclude_unset=True, mode="json")  # enums become their plain string values
    if changes.get("assignee_id") is not None:
        _check_assignee(db, ticket.project_id, changes["assignee_id"])
    for field, value in changes.items():
        setattr(ticket, field, value)
    db.commit()
    return ticket


@router.delete("/tickets/{ticket_id}", status_code=204)
def delete_ticket(ticket_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ticket, member = get_ticket_for_user(db, ticket_id, user, Role.developer)
    is_admin = member.role == Role.admin.value
    if not is_admin and ticket.reporter_id != user.id:
        raise HTTPException(status_code=403, detail="Only an admin or the reporter can delete this ticket")
    stored_names = [a.stored_name for a in ticket.attachments]
    db.delete(ticket)
    db.commit()
    remove_files(stored_names)
    return Response(status_code=204)
