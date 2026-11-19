from typing import List

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.deps import get_current_user, require_membership
from app.enums import Role
from app.models import Attachment, Project, ProjectMember, Ticket, User
from app.schemas import (
    MemberAdd,
    MemberOut,
    MemberRoleUpdate,
    ProjectCreate,
    ProjectDetail,
    ProjectOut,
    ProjectUpdate,
)
from app.uploads_store import remove_files

router = APIRouter(prefix="/projects", tags=["projects"])


def _project_out(project: Project, role) -> ProjectOut:
    return ProjectOut(
        id=project.id,
        name=project.name,
        description=project.description,
        owner_id=project.owner_id,
        created_at=project.created_at,
        my_role=Role(role),
    )


def _admin_count(db: Session, project_id: int) -> int:
    return db.scalar(
        select(func.count())
        .select_from(ProjectMember)
        .where(ProjectMember.project_id == project_id, ProjectMember.role == Role.admin.value)
    )


def _get_member(db: Session, project_id: int, user_id: int) -> ProjectMember:
    member = db.scalar(
        select(ProjectMember).where(ProjectMember.project_id == project_id, ProjectMember.user_id == user_id)
    )
    if member is None:
        raise HTTPException(status_code=404, detail="That person is not a member of this project")
    return member


@router.post("", response_model=ProjectOut, status_code=201)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    project = Project(name=payload.name, description=payload.description, owner_id=user.id)
    project.members.append(ProjectMember(user_id=user.id, role=Role.admin.value))
    db.add(project)
    db.commit()
    return _project_out(project, Role.admin)


@router.get("", response_model=List[ProjectOut])
def list_my_projects(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.execute(
        select(Project, ProjectMember.role)
        .join(ProjectMember, ProjectMember.project_id == Project.id)
        .where(ProjectMember.user_id == user.id)
        .order_by(Project.id.desc())
    ).all()
    return [_project_out(project, role) for project, role in rows]


@router.get("/{project_id}", response_model=ProjectDetail)
def get_project(project_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    me = require_membership(db, project_id, user, Role.viewer)
    project = db.scalar(
        select(Project)
        .where(Project.id == project_id)
        .options(selectinload(Project.members).selectinload(ProjectMember.user))
    )
    base = _project_out(project, me.role)
    return ProjectDetail(
        **base.model_dump(),
        members=[MemberOut.model_validate(m) for m in project.members],
    )


@router.patch("/{project_id}", response_model=ProjectOut)
def update_project(
    project_id: int,
    payload: ProjectUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    me = require_membership(db, project_id, user, Role.admin)
    project = db.get(Project, project_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(project, field, value)
    db.commit()
    return _project_out(project, me.role)


@router.delete("/{project_id}", status_code=204)
def delete_project(project_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_membership(db, project_id, user, Role.admin)
    project = db.get(Project, project_id)
    stored_names = db.scalars(
        select(Attachment.stored_name).join(Ticket, Attachment.ticket_id == Ticket.id).where(Ticket.project_id == project_id)
    ).all()
    db.delete(project)
    db.commit()
    remove_files(stored_names)  # only after the database change succeeded
    return Response(status_code=204)


# ---------- team management ----------
@router.post("/{project_id}/members", response_model=MemberOut, status_code=201)
def add_member(
    project_id: int,
    payload: MemberAdd,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_membership(db, project_id, user, Role.admin)
    target = db.scalar(select(User).where(User.email == payload.email))
    if target is None:
        raise HTTPException(status_code=404, detail="No user with that email has registered yet")
    already = db.scalar(
        select(ProjectMember.id).where(ProjectMember.project_id == project_id, ProjectMember.user_id == target.id)
    )
    if already is not None:
        raise HTTPException(status_code=409, detail="That person is already on this project")
    member = ProjectMember(project_id=project_id, user_id=target.id, role=payload.role.value)
    db.add(member)
    db.commit()
    return member


@router.patch("/{project_id}/members/{user_id}", response_model=MemberOut)
def change_member_role(
    project_id: int,
    user_id: int,
    payload: MemberRoleUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_membership(db, project_id, user, Role.admin)
    member = _get_member(db, project_id, user_id)
    if member.role == Role.admin.value and payload.role != Role.admin and _admin_count(db, project_id) <= 1:
        raise HTTPException(status_code=400, detail="A project must keep at least one admin")
    member.role = payload.role.value
    db.commit()
    return member


@router.delete("/{project_id}/members/{user_id}", status_code=204)
def remove_member(
    project_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_membership(db, project_id, user, Role.admin)
    member = _get_member(db, project_id, user_id)
    if member.role == Role.admin.value and _admin_count(db, project_id) <= 1:
        raise HTTPException(status_code=400, detail="A project must keep at least one admin")
    # Their open tickets go back to "unassigned" instead of pointing at someone who left.
    db.execute(
        update(Ticket).where(Ticket.project_id == project_id, Ticket.assignee_id == user_id).values(assignee_id=None)
    )
    db.delete(member)
    db.commit()
    return Response(status_code=204)
