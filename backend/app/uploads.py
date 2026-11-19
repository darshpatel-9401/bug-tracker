"""Rules for what we accept as an attachment. Pure functions, so they are easy to test."""
import re
from pathlib import PurePosixPath

_ALLOWED_MAGIC = {
    ".png": ("image/png", {"image/png"}),
    ".jpg": ("image/jpeg", {"image/jpeg"}),
    ".jpeg": ("image/jpeg", {"image/jpeg"}),
    ".gif": ("image/gif", {"image/gif"}),
    ".webp": ("image/webp", {"image/webp"}),
    ".pdf": ("application/pdf", {"application/pdf"}),
    ".txt": ("text/plain", {"text/plain", "application/octet-stream"}),
    ".log": ("text/plain", {"text/plain", "application/octet-stream"}),
}


class UploadError(ValueError):
    """The file was refused. The message is safe to show to the user."""


def _looks_right(ext: str, head: bytes) -> bool:
    if ext == ".png":
        return head.startswith(b"\x89PNG\r\n\x1a\n")
    if ext in (".jpg", ".jpeg"):
        return head.startswith(b"\xff\xd8\xff")
    if ext == ".gif":
        return head.startswith(b"GIF87a") or head.startswith(b"GIF89a")
    if ext == ".webp":
        return head[:4] == b"RIFF" and head[8:12] == b"WEBP"
    if ext == ".pdf":
        return head.startswith(b"%PDF-")
    return b"\x00" not in head  # .txt / .log: plain text never contains null bytes


def validate_upload(filename, content_type, head: bytes) -> str:
    """Return the canonical content type, or raise UploadError."""
    ext = PurePosixPath((filename or "").replace("\\", "/")).suffix.lower()
    rule = _ALLOWED_MAGIC.get(ext)
    if rule is None:
        raise UploadError("That file type is not allowed. Use png, jpg, gif, webp, pdf, txt or log.")
    canonical, accepted = rule
    if (content_type or "").split(";")[0].strip().lower() not in accepted:
        raise UploadError("The file's content type does not match its extension.")
    if not head:
        raise UploadError("The file is empty.")
    if not _looks_right(ext, head):
        raise UploadError("The file's contents do not match its extension.")
    return canonical


def safe_display_name(raw) -> str:
    """The name we show in the UI. It is never used to build a path on disk."""
    name = PurePosixPath((raw or "").replace("\\", "/")).name
    name = re.sub(r"[\x00-\x1f\x7f]", "", name).strip()
    return name[:255] or "file"
