FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run as a normal user, not root.
RUN useradd --create-home appuser && mkdir -p /data/uploads && chown -R appuser /app /data
USER appuser

EXPOSE 8000

# Apply database migrations, then start the API. $PORT is provided by Railway/Fly/Render.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
