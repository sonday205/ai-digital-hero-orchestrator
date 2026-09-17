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
    CHARACTER_IMAGE_PATH=/app/character-images/001 \
    VO_THI_SAU_IMAGE_PATH=/app/character-images/002 \
    KIM_DONG_IMAGE_PATH=/app/character-images/003 \
    LE_VAN_TAM_IMAGE_PATH=/app/character-images/004 \
    NGUYEN_VAN_TROI_IMAGE_PATH=/app/character-images/005 \
    LE_HONG_PHONG_IMAGE_PATH=/app/character-images/006 \
    NGUYEN_BINH_KHIEM_IMAGE_PATH=/app/character-images/007 \
    NGUYEN_BA_NGOC_IMAGE_PATH=/app/character-images/008 \
    LE_CHAN_IMAGE_PATH=/app/character-images/009 \
    LE_NGOC_HAN_IMAGE_PATH=/app/character-images/010 \
    DINH_NUP_IMAGE_PATH=/app/character-images/011 \
    NGO_QUYEN_IMAGE_PATH=/app/character-images/012 \
    QUANG_TRUNG_NGUYEN_HUE_IMAGE_PATH=/app/character-images/013 \
    LE_LOI_IMAGE_PATH=/app/character-images/014

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir --requirement requirements.txt

COPY app/ ./app/
COPY --from=frontend-builder /frontend/dist ./frontend-dist/

RUN mkdir -p /app/storage/jobs

EXPOSE 8991

HEALTHCHECK --interval=20s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8991/health', timeout=3)" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8991"]
