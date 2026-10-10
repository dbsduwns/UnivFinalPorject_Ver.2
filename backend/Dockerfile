FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    HF_HOME=/opt/huggingface

WORKDIR /app

COPY requirements.server.txt ./requirements.server.txt

RUN python -m pip install --upgrade pip \
    && python -m pip install -r requirements.server.txt \
    && python -m playwright install --with-deps chromium \
    && mkdir -p /app/chroma_db /app/static/shuttle /opt/huggingface

COPY . .

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1"]
