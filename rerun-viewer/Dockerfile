ARG RERUN_SDK_VERSION=0.33.0
FROM wandelbots.azurecr.io/docker.io/library/python:3.12-slim AS base

RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx \
    supervisor \
    curl \
    && rm -rf /var/lib/apt/lists/*

ARG RERUN_SDK_VERSION
RUN pip install --no-cache-dir rerun-sdk==${RERUN_SDK_VERSION}

# Download app icon for self-hosting (avoids external URL issues on the platform dashboard)
RUN mkdir -p /opt/rerun-gateway && \
    curl -fSL -o /opt/rerun-gateway/logo_dark_mode.png \
    "https://raw.githubusercontent.com/rerun-io/rerun/main/crates/viewer/re_ui/data/logo_dark_mode.png"

# Generate the entrypoint that creates nginx config dynamically from BASE_PATH env
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf.template
COPY nginx.conf.template /etc/nginx/nginx.conf.template
COPY index.html.template /opt/rerun-gateway/index.html.template

EXPOSE 8080

CMD ["/entrypoint.sh"]
