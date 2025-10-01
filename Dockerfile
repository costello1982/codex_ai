FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY README.md ./README.md

RUN useradd --create-home --shell /usr/sbin/nologin appuser \
    && mkdir -p /app/ipam-data \
    && chown -R appuser:appuser /app

USER appuser

ENV IPAM_DB_PATH=/app/ipam-data/ipam.db

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
