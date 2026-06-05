#!/bin/bash
# Local gRPC proxy for connecting native Rerun viewer to a remote cluster.
# Uses nginx to handle HTTP/2 gRPC streaming properly.
#
# WHY THIS NEEDS KUBECTL:
#   Native gRPC requires HTTP/2 end-to-end. Traefik (the cluster ingress)
#   downgrades all backend traffic to HTTP/1.1 by default, which breaks
#   native gRPC framing. The only way to make Traefik use HTTP/2 (h2c) to
#   the backend is a service annotation — and the App CRD API does not
#   expose service annotations. So kubectl is required for this one-time
#   setup. Without it, use the web viewer instead.
#
# Prerequisites:
#   brew install nginx
#   kubectl annotate service app-rerun-viewer -n cell \
#     "traefik.ingress.kubernetes.io/service.serversscheme=h2c"
#
# Usage:
#   ./local-proxy.sh <cluster-ip> [port] [base-path]
#
# Then connect:
#   rerun +http://127.0.0.1:9876/proxy

set -e

CLUSTER_IP="${1:?Usage: $0 <cluster-ip> [local-port] [base-path]}"
LOCAL_PORT="${2:-9876}"
BASE_PATH="${3:-/cell/rerun-viewer}"
TMPDIR=$(mktemp -d)

trap "echo 'Stopping...'; nginx -s stop -p $TMPDIR -c $TMPDIR/nginx.conf 2>/dev/null; rm -rf $TMPDIR" EXIT

cat > "$TMPDIR/nginx.conf" << EOF
worker_processes 1;
pid $TMPDIR/nginx.pid;
error_log /dev/stderr warn;
daemon off;

events {
    worker_connections 128;
}

http {
    access_log /dev/stdout;

    server {
        listen $LOCAL_PORT http2;
        server_name _;

        # Native gRPC from local Rerun viewer -> remote cluster via HTTPS
        # Rewrites paths: /proxy -> /cell/rerun-viewer/proxy
        #                 /rerun.Svc/Method -> /cell/rerun-viewer/rerun.Svc/Method
        location / {
            grpc_pass grpcs://$CLUSTER_IP:443;
            grpc_ssl_verify off;
            grpc_ssl_server_name on;

            grpc_set_header Host $CLUSTER_IP;
            grpc_read_timeout 86400s;
            grpc_send_timeout 86400s;

            # Rewrite: prepend base path
            rewrite ^/(.*)$ ${BASE_PATH}/\$1 break;
        }
    }
}
EOF

echo "Local gRPC proxy listening on http://127.0.0.1:$LOCAL_PORT"
echo "Forwarding to https://$CLUSTER_IP$BASE_PATH/"
echo ""
echo "Connect native Rerun viewer:"
echo "  rerun +http://127.0.0.1:$LOCAL_PORT/proxy"
echo ""

nginx -p "$TMPDIR" -c "$TMPDIR/nginx.conf"
