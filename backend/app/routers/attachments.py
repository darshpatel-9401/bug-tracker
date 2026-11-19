import os
import uuid
from pathlib import PurePosixPath
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.deps import get_current_user, get_ticket_for_user
from app.enums import Role
from app.models import Attachment, User
from app.schemas import AttachmentOut
from app.uploads import UploadError, safe_display_name, validate_upload
from app.uploads_store import file_path, remove_files

router = APIRouter(tags=["attachments"])


@router.get("/tickets/{ticket_id}/attachments", response_model=List[AttachmentOut])
def list_attachments(ticket_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    get_ticket_for_user(db, ticket_id, user, Role.viewer)
    return db.scalars(select(Attachment).where(Attachment.ticket_id == ticket_id).order_by(Attachment.id)).all()


@router.post("/tickets/{ticket_id}/attachments", response_model=AttachmentOut, status_code=201)
def upload_attachment(
    ticket_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    get_ticket_for_user(db, ticket_id, user, Role.developer)

    # Read one byte more than the limit so we can tell "exactly at the limit" from "too big".
    data = file.file.read(settings.max_upload_bytes + 1)
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail="File is too large")
    try:
        content_type = validate_upload(file.filename, file.content_type, data[:1024])
    except UploadError as problem:
        raise HTTPException(status_code=400, detail=str(problem)) from None

    # Same suffix rule validate_upload just approved, so only a whitelisted extension can reach the disk.
    extension = PurePosixPath((file.filename or "").replace("\\", "/")).suffix.lower()
    stored_name = f"{uuid.uuid4().hex}{extension}"
    os.makedirs(settings.upload_dir, exist_ok=True)
    with open(file_path(stored_name), "wb") as out:
        out.write(data)

    attachment = Attachment(
        ticket_id=ticket_id,
        uploader_id=user.id,
        filename=safe_display_name(file.filename),
        stored_name=stored_name,
        content_type=content_type,
        size=len(data),
    )
    db.add(attachment)
    try:
        db.commit()
    except Exception:
        db.rollback()
        remove_files([stored_name])  # do not leave an orphan file behind
        raise
    return attachment


def _get_attachment(db: Session, attachment_id: int) -> Attachment:
    attachment = db.get(Attachment, attachment_id)
    if attachment is None:
        raise HTTPException(status_code=404, detail="Not found")
    return attachment


@router.get("/attachments/{attachment_id}/download")
def download_attachment(attachment_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    attachment = _get_attachment(db, attachment_id)
    get_ticket_for_user(db, attachment.ticket_id, user, Role.viewer)
    path = file_path(attachment.stored_name)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="File is missing on the server")
    return FileResponse(path, media_type=attachment.content_type, filename=attachment.filename)


@router.delete("/attachments/{attachment_id}", status_code=204)
def delete_attachment(attachment_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    attachment = _get_attachment(db, attachment_id)
    _, member = get_ticket_for_user(db, attachment.ticket_id, user, Role.viewer)
    if attachment.uploader_id != user.id and member.role != Role.admin.value:
        raise HTTPException(status_code=403, detail="Only the uploader or an admin can delete this file")
    stored_name = attachment.stored_name
    db.delete(attachment)
    db.commit()
    remove_files([stored_name])
    return Response(status_code=204)
