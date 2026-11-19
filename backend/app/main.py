from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import attachments, auth, comments, projects, tickets

app = FastAPI(
    title="Bug Tracker API",
    description="A Jira-style issue tracker: projects, tickets, Kanban status, comments and attachments.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,  # we use Authorization headers, not cookies
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


for module in (auth, projects, tickets, comments, attachments):
    app.include_router(module.router, prefix="/api")


@app.get("/api/health", tags=["health"])
def health():
    return {"status": "ok"}
