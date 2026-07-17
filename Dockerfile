FROM node:22-alpine AS frontend-builder

WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build


FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_HOST=0.0.0.0 \
    APP_PORT=8991 \
    STORAGE_DIR=/app/storage \
    FRONTEND_DIST_DIR=/app/frontend-dist \
    CHARACTER_IMAGE_PATH=/app/assets/001.svg

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir --requirement requirements.txt

COPY app/ ./app/
COPY assets/ ./assets/
COPY --from=frontend-builder /frontend/dist ./frontend-dist/

RUN mkdir -p /app/storage/jobs

EXPOSE 8991

HEALTHCHECK --interval=20s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8991/health', timeout=3)" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8991"]
