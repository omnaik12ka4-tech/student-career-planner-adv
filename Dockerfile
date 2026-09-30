FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# SQLite file lives here - mount a volume on this path to keep data
# between container restarts (see docker-compose.yml).
RUN mkdir -p /data
ENV DATABASE_PATH=/data/career_planner.db

EXPOSE 8000
CMD ["gunicorn", "wsgi:app", "--bind", "0.0.0.0:8000", "--workers", "2"]
