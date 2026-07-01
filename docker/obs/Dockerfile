# Optional OBS headless container (profile: full)
# Requires profile "full": docker compose --profile full up -d
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive \
    DISPLAY=:99 \
    OBS_WEBSOCKET_PORT=4455

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        software-properties-common \
        ca-certificates \
        xvfb \
        curl \
    && add-apt-repository -y ppa:obsproject/obs-studio \
    && apt-get update \
    && apt-get install -y --no-install-recommends obs-studio \
    && rm -rf /var/lib/apt/lists/*

COPY docker/obs/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 4455

HEALTHCHECK --interval=30s --timeout=10s --retries=5 --start-period=60s \
    CMD curl -sf "http://127.0.0.1:${OBS_WEBSOCKET_PORT}/" || exit 1

ENTRYPOINT ["/entrypoint.sh"]
