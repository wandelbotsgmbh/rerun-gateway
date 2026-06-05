FROM python:3.11-slim AS base

RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx \
    supervisor \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir rerun-sdk==0.33.0

# Generate the entrypoint that creates nginx config dynamically from BASE_PATH env
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY nginx.conf.template /etc/nginx/nginx.conf.template
COPY index.html.template /opt/rerun-gateway/index.html.template

EXPOSE 8080

CMD ["/entrypoint.sh"]
