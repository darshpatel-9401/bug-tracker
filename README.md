# Bugtracker: a Jira-style issue tracker

FastAPI + PostgreSQL backend, React + Tailwind + dnd-kit frontend.
Roles per project: **admin**, **developer**, **viewer**.

```
backend/   FastAPI app, Alembic migrations, tests, load-test script
frontend/  React (Vite) app
```

## 1. Run it locally

**Backend** (Python 3.12)
```bash
cd backend
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env                                    # optional; defaults work with SQLite
alembic upgrade head                                    # creates the tables
uvicorn app.main:app --reload
```
API docs: http://localhost:8000/docs (click Authorize and paste the token from /api/auth/login).

Want PostgreSQL locally? `docker compose up db` from the project root, then set
`DATABASE_URL=postgresql://bugtracker:bugtracker@localhost:5432/bugtracker`.

**Frontend** (Node 18+)
```bash
cd frontend
cp .env.example .env
npm install
npm run dev          # http://localhost:5173
```

## 2. Run the tests
```bash
cd backend
pytest                      # everything
pytest tests/unit           # pure logic, fast
pytest tests/integration    # full API through HTTP, in-memory SQLite
```

## 3. Simulate many users (security + bug hunt)
Start the API on a throwaway database, then:
```bash
pip install httpx
python loadtest/simulate_users.py --base-url http://localhost:8000 --users 1000 --concurrency 50
```
It prints latency percentiles, unexpected status codes and any "must be refused" request that was accepted.

## 4. Deploy

### Backend on Railway
1. Push this repo to GitHub.
2. Railway -> New Project -> Deploy from GitHub repo -> set **Root Directory** to `backend` (it builds the Dockerfile).
3. Add a **PostgreSQL** plugin; Railway injects `DATABASE_URL` (the app rewrites `postgres://` for you).
4. Add a **Volume** mounted at `/data` (uploads must survive redeploys). If uploads fail with a permission error, add variable `RAILWAY_RUN_UID=0`.
5. Variables:
   - `ENVIRONMENT=production`
   - `SECRET_KEY=` output of `python -c "import secrets; print(secrets.token_urlsafe(48))"`
   - `UPLOAD_DIR=/data/uploads`
   - `CORS_ORIGINS=https://your-frontend-domain` (fill in after step 6)
6. Deploy. Migrations run automatically on start. Check `https://<backend>/api/health`.

The app refuses to start in production with a short/default secret or SQLite, on purpose.

### Frontend on Vercel (or Netlify)
1. New Project -> import the repo -> Root Directory `frontend`, framework Vite.
2. Env var `VITE_API_URL=https://<your-backend-domain>` (no trailing slash, no `/api`).
3. Deploy, then put the resulting URL into the backend's `CORS_ORIGINS` and redeploy the backend.

## Permission matrix
| Action | viewer | developer | admin |
|---|---|---|---|
| View project, tickets, comments, files | yes | yes | yes |
| Create/edit/move tickets, comment, upload | no | yes | yes |
| Delete a ticket | no | own only | any |
| Delete a comment / file | no | own only | any |
| Manage members, edit/delete project | no | no | yes |

Non-members get 404 (not 403) so project ids cannot be probed.
