"""The fixed vocabularies of the app, kept in one place so the API, the database
and the frontend all agree on spelling."""
from enum import Enum


class Role(str, Enum):
    admin = "admin"
    developer = "developer"
    viewer = "viewer"


class TicketType(str, Enum):
    bug = "bug"
    task = "task"
    feature = "feature"


class TicketStatus(str, Enum):
    todo = "todo"
    in_progress = "in_progress"
    in_review = "in_review"
    done = "done"


class Priority(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"
