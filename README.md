# Rerun Gateway

Deploy [Rerun](https://rerun.io) as a Wandelbots App on a service manager cluster.

## Problem

The App CRD routes traffic at `/<namespace>/<app-name>/*`. Rerun's WASM viewer sends gRPC-web requests to the host root (`/rerun.Service/Method`), which falls outside the allowed path.

## Solution

- **Browser**: a fetch interceptor in a custom `index.html` rewrites gRPC-web URLs before they leave the page
- **Nginx**: dual-protocol proxy (gRPC-web for browsers, native gRPC for SDK clients)
- **Native viewer**: a local nginx proxy prepends the base path and forwards over HTTPS

```
Browser (gRPC-web)
  -> Traefik -> nginx proxy_pass -> rerun :9876

Cluster pods (native gRPC)
  -> app-rerun-viewer.cell.svc.cluster.local:8080
     -> nginx grpc_pass -> rerun :9876

Native viewer via local-proxy.sh (native gRPC)
  -> local nginx -> Traefik (h2c) -> nginx grpc_pass -> rerun :9876
```

## Deploy

### 1. Build and push image (manual)

Only needed if not using CI. The image must be built for `linux/amd64`:

```bash
az acr login --name wandelbots
docker buildx build --platform linux/amd64 \
  -t wandelbots.azurecr.io/rerun-gateway:0.1.0 \
  -t wandelbots.azurecr.io/rerun-gateway:latest \
  --push ./rerun-viewer/
```

### 1b. Build via CI (automatic)

On merge to `main`, the GitLab CI pipeline builds and pushes `wandelbots.azurecr.io/rerun-gateway:latest`.

To publish a versioned release, create a git tag:

```bash
git tag v0.2.0
git push --tags
```

CI will push both `:0.2.0` and `:latest`.

### 2. Deploy via API

```bash
curl -sk -X POST "https://<INSTANCE_HOST>/api/v2/cells/cell/apps" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "rerun-viewer",
    "app_icon": "logo_dark_mode.png",
    "container_image": {
      "image": "wandelbots.azurecr.io/rerun-gateway:0.1.0",
      "secrets": [
        {"name": "pull-secret-wandelbots-azurecr-io"}
      ]
    },
    "port": 8080,
    "health_path": "/healthz",
    "environment": [
      {"name": "RERUN_MEMORY_LIMIT", "value": "1GB"}
    ]
  }'
```

The `secrets` field references an existing image pull secret in the cluster.

### 3. Update an existing deployment

To update the image version of a running app:

```bash
curl -sk -X PATCH "https://<INSTANCE_HOST>/api/v2/cells/cell/apps/rerun-viewer" \
  -H "Content-Type: application/json" \
  -d '{
    "container_image": {
      "image": "wandelbots.azurecr.io/rerun-gateway:0.2.0",
      "secrets": [
        {"name": "pull-secret-wandelbots-azurecr-io"}
      ]
    }
  }'
```

### 4. Delete the app

```bash
curl -sk -X DELETE "https://<INSTANCE_HOST>/api/v2/cells/cell/apps/rerun-viewer"
```

## Access

### Web viewer

```
https://<INSTANCE_HOST>/cell/rerun-viewer/
```

Requires HTTPS (gRPC-web needs HTTP/2, browsers only negotiate it over TLS). Use `--ignore-certificate-errors` in Chrome for self-signed certs.

### Native viewer (from your machine)

Requires kubectl access. Traefik downgrades backend traffic to HTTP/1.1 by
default, which breaks native gRPC. A one-time service annotation is needed to
enable HTTP/2 (h2c) passthrough, and the App CRD API does not expose service
annotations. Without kubectl, use the web viewer.

```bash
# One-time: enable h2c on the service (requires kubectl)
kubectl annotate service app-rerun-viewer -n cell \
  "traefik.ingress.kubernetes.io/service.serversscheme=h2c"

# Run the local proxy
brew install nginx
./rerun-viewer/local-proxy.sh <INSTANCE_HOST>
# Then: rerun +http://127.0.0.1:9876/proxy
```

### From cluster pods

```python
import rerun as rr
rr.init("my_recording", spawn=False)
rr.connect_grpc("rerun+http://app-rerun-viewer.cell.svc.cluster.local:8080/proxy")
rr.log("world/points", rr.Points3D([[1, 2, 3]]))
```

### Test logger app

Deploy a test app that continuously logs random 3D points to the viewer:

```bash
curl -sk -X POST "https://<INSTANCE_HOST>/api/v2/cells/cell/apps" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "rerun-logger",
    "app_icon": "logo_dark_mode.png",
    "container_image": {
      "image": "wandelbots.azurecr.io/rerun-logger:latest",
      "secrets": [
        {"name": "pull-secret-wandelbots-azurecr-io"}
      ]
    },
    "port": 8080,
    "health_path": "/healthz"
  }'
```

## File Structure

```
.gitlab-ci.yml            # CI pipeline: build, lint, publish
rerun-viewer/
  Dockerfile              # python:3.11-slim + nginx + supervisor + rerun
  entrypoint.sh           # Generates nginx.conf from BASE_PATH env var
  nginx.conf.template     # Dual-protocol proxy config
  index.html.template     # Viewer page with fetch interceptor
  supervisord.conf        # Manages nginx + rerun processes
  app.yaml                # App CRD manifest (alternative to API deploy)
  local-proxy.sh          # Local nginx wrapper for native viewer access
rerun-logger-test/
  Dockerfile              # Test logger image
  logger.py               # Logs random 3D points to rerun-viewer
  app.yaml                # App CRD manifest
```
