from typing import List

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.deps import get_current_user, get_ticket_for_user
from app.enums import Role
from app.models import Comment, User
from app.schemas import CommentCreate, CommentOut, CommentUpdate

router = APIRouter(tags=["comments"])


def _get_comment(db: Session, comment_id: int) -> Comment:
    comment = db.get(Comment, comment_id)
    if comment is None:
        raise HTTPException(status_code=404, detail="Not found")
    return comment


@router.get("/tickets/{ticket_id}/comments", response_model=List[CommentOut])
def list_comments(ticket_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    get_ticket_for_user(db, ticket_id, user, Role.viewer)
    return db.scalars(
        select(Comment)
        .where(Comment.ticket_id == ticket_id)
        .options(selectinload(Comment.author))
        .order_by(Comment.id)
    ).all()


@router.post("/tickets/{ticket_id}/comments", response_model=CommentOut, status_code=201)
def add_comment(
    ticket_id: int,
    payload: CommentCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    get_ticket_for_user(db, ticket_id, user, Role.developer)
    if payload.parent_id is not None:
        parent = db.get(Comment, payload.parent_id)
        if parent is None or parent.ticket_id != ticket_id:
            raise HTTPException(status_code=400, detail="You can only reply to a comment on the same ticket")
    comment = Comment(ticket_id=ticket_id, author_id=user.id, parent_id=payload.parent_id, body=payload.body)
    db.add(comment)
    db.commit()
    return comment


@router.patch("/comments/{comment_id}", response_model=CommentOut)
def edit_comment(
    comment_id: int,
    payload: CommentUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    comment = _get_comment(db, comment_id)
    get_ticket_for_user(db, comment.ticket_id, user, Role.developer)
    if comment.author_id != user.id:
        raise HTTPException(status_code=403, detail="You can only edit your own comments")
    comment.body = payload.body
    db.commit()
    return comment


@router.delete("/comments/{comment_id}", status_code=204)
def delete_comment(comment_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    comment = _get_comment(db, comment_id)
    _, member = get_ticket_for_user(db, comment.ticket_id, user, Role.viewer)
    if comment.author_id != user.id and member.role != Role.admin.value:
        raise HTTPException(status_code=403, detail="Only the author or an admin can delete this comment")
    db.delete(comment)  # replies go with it
    db.commit()
    return Response(status_code=204)
