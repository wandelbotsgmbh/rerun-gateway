#!/bin/bash
set -e

# BASE_PATH is set by the App CRD operator (e.g., /cell/rerun-viewer)
BASE_PATH="${BASE_PATH:-/cell/rerun-viewer}"
# Memory limit for the rerun gRPC server buffer (drops oldest data when reached)
# Platform caps pod memory at 1000Mi; leave headroom for nginx/supervisor/OS
RERUN_MEMORY_LIMIT="${RERUN_MEMORY_LIMIT:-500MB}"

echo "Starting rerun-gateway with BASE_PATH=$BASE_PATH RERUN_MEMORY_LIMIT=$RERUN_MEMORY_LIMIT"

# Generate nginx config from template
sed "s|__BASE_PATH__|${BASE_PATH}|g" /etc/nginx/nginx.conf.template > /etc/nginx/nginx.conf

# Generate index.html with fetch interceptor
sed "s|__BASE_PATH__|${BASE_PATH}|g" /opt/rerun-gateway/index.html.template > /opt/rerun-gateway/index.html

# Generate supervisord config with memory limit
sed "s|__RERUN_MEMORY_LIMIT__|${RERUN_MEMORY_LIMIT}|g" /etc/supervisor/conf.d/supervisord.conf.template > /etc/supervisor/conf.d/supervisord.conf

# Start supervisor (manages nginx + rerun)
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf
