# Rerun Gateway

Deploy [Rerun](https://rerun.io) as a Wandelbots App on a service manager cluster. Provides a shared visualization server that any pod in the cluster can log data to via gRPC, with a web viewer accessible through the platform dashboard.

## Problem

The App CRD routes traffic at `/<cell>/<app-name>/*`. Rerun's WASM viewer sends gRPC-web requests to the host root (`/rerun.Service/Method`), which falls outside the allowed path. Additionally:

- Nginx's default 1MB request body limit silently drops gRPC WriteMessages from the SDK
- Browsers require credentials and stream buffering for requests through oauth2-proxy

## Solution

- **Fetch interceptor**: a custom `index.html` rewrites gRPC-web URLs to the app's base path, buffers ReadableStream bodies (Safari/Chrome compatibility), and injects auth credentials
- **Nginx**: dual-protocol proxy — gRPC-web (HTTP/1.1) for browsers via `proxy_pass`, native gRPC (HTTP/2) for SDK clients via `grpc_pass`, with unlimited request body size
- **Supervisord**: manages both nginx and the rerun server process within a single container

```
Browser (gRPC-web)
  -> Cloud Ingress (Traefik + oauth2-proxy)
     -> nginx proxy_pass -> rerun :9876

Cluster pods (native gRPC over HTTP/2)
  -> app-rerun-viewer:8080
     -> nginx grpc_pass -> rerun :9876
```

## Deploy

### 1. Build and push image (manual)

Images must be built for `linux/amd64` and use unique version tags (the cluster does not re-pull the same tag):

```bash
az acr login --name wandelbots
docker buildx build --platform linux/amd64 \
  -t wandelbots.azurecr.io/nova-apps/rerun-gateway:0.1.8 \
  --push ./rerun-viewer/
```

### 1b. Build via CI (automatic)

On merge to `main`, semantic-release creates a version tag automatically based on conventional commits.

CI will build the image and publish `wandelbots.azurecr.io/nova-apps/rerun-gateway:<version>`.

### 2. Deploy via API

Use the **v2 API** (snake_case fields, supports `resources.memory_limit`):

```bash
curl -s -X POST "https://<INSTANCE_HOST>/api/v2/cells/cell/apps" \
  -H "Content-Type: application/json" \
  -H "Cookie: _oauth2_proxy=<AUTH_COOKIE>" \
  -d '{
    "name": "rerun-viewer",
    "app_icon": "app-icon.png",
    "container_image": {
      "image": "wandelbots.azurecr.io/nova-apps/rerun-gateway:1.0.2",
      "secrets": [{"name": "pull-secret-wandelbots-azurecr-io"}]
    },
    "environment": [
      {"name": "RERUN_MEMORY_LIMIT", "value": "1000MB"}
    ],
    "resources": {
      "memory_limit": "2000Mi"
    },
    "port": 8080
  }'
```

### 4. Delete the app

```bash
curl -s -X DELETE "https://<INSTANCE_HOST>/api/v2/cells/cell/apps/rerun-viewer" \
  -H "Cookie: _oauth2_proxy=<AUTH_COOKIE>"
```

## Access

### Web viewer

```
https://<INSTANCE_HOST>/cell/rerun-viewer/
```

The viewer auto-connects to the rerun server via gRPC-web. Data appears as soon as any logger starts sending.

### From cluster pods (recommended)

Use the short service name (no FQDN needed within the same namespace):

```python
import rerun as rr
rr.init("my_recording", spawn=False)
rr.connect_grpc("rerun+http://app-rerun-viewer:8080/proxy")
rr.log("world/points", rr.Points3D([[1, 2, 3]]))
```

Multiple loggers can connect simultaneously — each creates a separate recording in the viewer.

### Native viewer (from your machine)

Requires kubectl access. Traefik downgrades backend traffic to HTTP/1.1 by
default, which breaks native gRPC. A one-time service annotation is needed to
enable HTTP/2 (h2c) passthrough. Without kubectl, use the web viewer.

```bash
# One-time: enable h2c on the service (requires kubectl)
kubectl annotate service app-rerun-viewer -n <cell-namespace> \
  "traefik.ingress.kubernetes.io/service.serversscheme=h2c"

# Run the local proxy
brew install nginx
./rerun-viewer/local-proxy.sh <INSTANCE_HOST>
# Then: rerun +http://127.0.0.1:9876/proxy
```

### Test logger app

Deploy a test app that continuously logs random 3D points:

```bash
curl -s -X POST "https://<INSTANCE_HOST>/api/v2/cells/cell/apps" \
  -H "Content-Type: application/json" \
  -H "Cookie: _oauth2_proxy=<AUTH_COOKIE>" \
  -d '{
    "name": "rerun-logger",
    "app_icon": "app-icon.png",
    "container_image": {
      "image": "wandelbots.azurecr.io/rerun-logger:0.3.1",
      "secrets": [{"name": "pull-secret-wandelbots-azurecr-io"}]
    },
    "environment": [],
    "port": 8080
  }'
```

## Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `BASE_PATH` | `/cell/rerun-viewer` | Set automatically by the App CRD operator |
| `RERUN_MEMORY_LIMIT` | `1000MB` | Max memory for stored data (oldest dropped when exceeded). Pod `memory_limit` should be at least 2× this value. |

## File Structure

```
.gitlab-ci.yml            # CI pipeline: build, lint, publish
rerun-viewer/
  Dockerfile              # python:3.11-slim + nginx + supervisor + rerun-sdk 0.33.0
  entrypoint.sh           # Generates configs from BASE_PATH/RERUN_MEMORY_LIMIT env
  nginx.conf.template     # Dual-protocol proxy (gRPC-web + native gRPC)
  index.html.template     # Viewer page with fetch interceptor
  supervisord.conf        # Manages nginx + rerun processes
  app.yaml                # App CRD manifest (alternative to API deploy)
  local-proxy.sh          # Local nginx wrapper for native viewer access
rerun-logger-test/
  Dockerfile              # Test logger image
  logger.py               # Logs random 3D points to rerun-viewer
  app.yaml                # App CRD manifest
```
