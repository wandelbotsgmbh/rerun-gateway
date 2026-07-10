ARG RERUN_SDK_VERSION=0.34.1
FROM python:3.12-slim AS base

RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

ARG RERUN_SDK_VERSION
RUN pip install --no-cache-dir rerun-sdk==${RERUN_SDK_VERSION}

# Copy square app icon for self-hosting
COPY app-icon.png /opt/rerun-gateway/app-icon.png

# Generate the entrypoint that creates nginx config dynamically from BASE_PATH env
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf.template
COPY nginx.conf.template /etc/nginx/nginx.conf.template
COPY index.html.template /opt/rerun-gateway/index.html.template

EXPOSE 8080

CMD ["/entrypoint.sh"]
