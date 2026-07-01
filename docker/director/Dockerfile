FROM python:3.11-slim-bookworm

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY docker/director/requirements-server.txt /tmp/requirements-server.txt
RUN pip install --no-cache-dir -r /tmp/requirements-server.txt

COPY lol_cam_switcher/ /app/lol_cam_switcher/
COPY server_main.py /app/server_main.py

ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    LOGS_DIR=/data/logs

RUN mkdir -p /data/logs

EXPOSE 8750

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8750/health || exit 1

CMD ["python", "-m", "lol_cam_switcher.server"]
