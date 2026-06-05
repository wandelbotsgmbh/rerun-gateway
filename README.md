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

### 1. Build and push image

```bash
az acr login --name wandelbots
docker build -t wandelbots.azurecr.io/rerun-gateway:latest ./docker/
docker push wandelbots.azurecr.io/rerun-gateway:latest
```

### 2. Deploy via API

```bash
curl -sk -X POST "https://<CLUSTER_IP>/api/v2/cells/cell/apps" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "rerun-viewer",
    "app_icon": "https://raw.githubusercontent.com/rerun-io/rerun/main/crates/viewer/re_ui/data/logo_dark_mode.png",
    "container_image": {
      "image": "wandelbots.azurecr.io/rerun-gateway:latest",
      "credentials": {
        "registry": "wandelbots.azurecr.io",
        "user": "00000000-0000-0000-0000-000000000000",
        "password": "<ACR_TOKEN>"
      }
    },
    "port": 8080,
    "health_path": "/healthz"
  }'
```

Get the token with: `az acr login --name wandelbots --expose-token --output tsv --query accessToken`

### 3. Enable native gRPC passthrough (for local viewer)

```bash
kubectl annotate service app-rerun-viewer -n cell \
  "traefik.ingress.kubernetes.io/service.serversscheme=h2c"
```

## Access

### Web viewer

```
https://<CLUSTER_IP>/cell/rerun-viewer/
```

Requires HTTPS (gRPC-web needs HTTP/2, browsers only negotiate it over TLS). Use `--ignore-certificate-errors` in Chrome for self-signed certs.

### Native viewer (from your machine)

```bash
brew install nginx
./local-proxy.sh <CLUSTER_IP>
# Then: rerun +http://127.0.0.1:9876/proxy
```

### From cluster pods

```python
import rerun as rr
rr.init("my_recording", spawn=False)
rr.connect_grpc("rerun+http://app-rerun-viewer.cell.svc.cluster.local:8080/proxy")
rr.log("world/points", rr.Points3D([[1, 2, 3]]))
```

## File Structure

```
docker/
  Dockerfile              # python:3.11-slim + nginx + supervisor + rerun
  entrypoint.sh           # Generates nginx.conf from BASE_PATH env var
  nginx.conf.template     # Dual-protocol proxy config
  index.html.template     # Viewer page with fetch interceptor
  supervisord.conf        # Manages nginx + rerun processes
k8s/
  rerun-app-crd.yaml      # App CRD manifest (alternative to API deploy)
  rerun-logger.yaml       # Test pod that sends data to rerun
local-proxy.sh            # Local nginx wrapper for native viewer access
```
