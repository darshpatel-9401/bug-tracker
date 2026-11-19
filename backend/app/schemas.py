"""Pydantic models: what the API accepts (…In / …Create / …Update) and what it returns (…Out)."""
from datetime import datetime
from typing import Annotated, List, Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from app.enums import Priority, Role, TicketStatus, TicketType

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
CommentBody = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=5000)]
LongText = Annotated[str, StringConstraints(max_length=10000)]


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------- auth ----------
class RegisterIn(BaseModel):
    email: EmailStr
    full_name: Name
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def lowercase_email(cls, value: str) -> str:
        return value.lower()

    @field_validator("password")
    @classmethod
    def password_needs_letter_and_digit(cls, value: str) -> str:
        if not any(c.isalpha() for c in value) or not any(c.isdigit() for c in value):
            raise ValueError("password must contain at least one letter and one digit")
        return value


class LoginIn(BaseModel):
    email: str = Field(max_length=255)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def clean_email(cls, value: str) -> str:
        return value.strip().lower()


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(ORMModel):
    id: int
    email: str
    full_name: str


# ---------- projects ----------
class ProjectCreate(BaseModel):
    name: Name
    description: Optional[LongText] = None


class ProjectUpdate(BaseModel):
    name: Optional[Name] = None
    description: Optional[LongText] = None

    @model_validator(mode="after")
    def name_cannot_be_null(self):
        if "name" in self.model_fields_set and self.name is None:
            raise ValueError("name cannot be null")
        return self


class ProjectOut(BaseModel):
    id: int
    name: str
    description: Optional[str]
    owner_id: int
    created_at: datetime
    my_role: Role


class MemberAdd(BaseModel):
    email: EmailStr
    role: Role = Role.developer

    @field_validator("email")
    @classmethod
    def lowercase_email(cls, value: str) -> str:
        return value.lower()


class MemberRoleUpdate(BaseModel):
    role: Role


class MemberOut(ORMModel):
    user: UserOut
    role: Role


class ProjectDetail(ProjectOut):
    members: List[MemberOut]


# ---------- tickets ----------
class TicketCreate(BaseModel):
    title: Title
    description: Optional[LongText] = None
    type: TicketType = TicketType.task
    status: TicketStatus = TicketStatus.todo
    priority: Priority = Priority.medium
    assignee_id: Optional[int] = None


class TicketUpdate(BaseModel):
    title: Optional[Title] = None
    description: Optional[LongText] = None
    type: Optional[TicketType] = None
    status: Optional[TicketStatus] = None
    priority: Optional[Priority] = None
    assignee_id: Optional[int] = None

    @model_validator(mode="after")
    def required_fields_cannot_be_null(self):
        # description and assignee_id may be set to null on purpose; the others may not.
        for name in ("title", "type", "status", "priority"):
            if name in self.model_fields_set and getattr(self, name) is None:
                raise ValueError(f"{name} cannot be null")
        return self


class TicketOut(ORMModel):
    id: int
    project_id: int
    title: str
    description: Optional[str]
    type: TicketType
    status: TicketStatus
    priority: Priority
    reporter: UserOut
    assignee: Optional[UserOut]
    created_at: datetime
    updated_at: datetime


class TicketPage(BaseModel):
    items: List[TicketOut]
    total: int


# ---------- comments ----------
class CommentCreate(BaseModel):
    body: CommentBody
    parent_id: Optional[int] = None


class CommentUpdate(BaseModel):
    body: CommentBody


class CommentOut(ORMModel):
    id: int
    ticket_id: int
    parent_id: Optional[int]
    body: str
    author: UserOut
    created_at: datetime
    updated_at: datetime


# ---------- attachments ----------
class AttachmentOut(ORMModel):
    id: int
    ticket_id: int
    filename: str
    content_type: str
    size: int
    uploader_id: int
    created_at: datetime
