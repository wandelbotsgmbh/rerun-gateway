#!/bin/bash
set -e

# BASE_PATH is set by the App CRD operator (e.g., /cell/rerun-viewer)
BASE_PATH="${BASE_PATH:-/cell/rerun-viewer}"

echo "Starting rerun-gateway with BASE_PATH=$BASE_PATH"

# Generate nginx config from template
sed "s|__BASE_PATH__|${BASE_PATH}|g" /etc/nginx/nginx.conf.template > /etc/nginx/nginx.conf

# Generate index.html with fetch interceptor
sed "s|__BASE_PATH__|${BASE_PATH}|g" /opt/rerun-gateway/index.html.template > /opt/rerun-gateway/index.html

# Start supervisor (manages nginx + rerun)
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf
