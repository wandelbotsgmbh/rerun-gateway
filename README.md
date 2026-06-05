# Rerun Gateway - App CRD Deployment

Deploy [Rerun](https://rerun.io) as a Wandelbots App CRD (`apps.wandelbots.com/v1alpha1`) on a service manager cluster.

## Problem

The App CRD only routes traffic at `/<namespace>/<app-name>/*` (e.g., `/cell/rerun-viewer/*`).
Rerun's WASM viewer sends gRPC-web requests to the **host root** (`/rerun.sdk_comms.v1alpha1.MessageProxyService/ReadMessages`), which falls outside the allowed path.

Custom IngressRoutes or NodePorts are not available.

## Solution

A browser-side **fetch interceptor** rewrites gRPC-web URLs before they leave the page:

```
/rerun.Service/Method  →  /cell/rerun-viewer/rerun.Service/Method
```

The container runs:
- **nginx** (port 8080) — path-aware reverse proxy with HTTP/2 support
- **rerun** (ports 9876 gRPC + 9090 web viewer) — managed by supervisord

```
Browser (HTTPS/H2)
  → Traefik ingress /cell/rerun-viewer/*
    → nginx :8080
       ├── /cell/rerun-viewer/           → custom index.html (fetch interceptor)
       ├── /cell/rerun-viewer/rerun.*    → proxy_pass → rerun gRPC :9876 (gRPC-web)
       ├── /cell/rerun-viewer/proxy      → proxy_pass → rerun gRPC :9876
       ├── /cell/rerun-viewer/*.js|wasm  → proxy_pass → rerun web viewer :9090
       ├── /rerun.*                      → grpc_pass  → rerun gRPC :9876 (native H2)
       ├── /proxy                        → grpc_pass  → rerun gRPC :9876 (native H2)
       └── /healthz                      → 200 ok

Internal SDK clients (Python/C++)
  → app-rerun-viewer.cell.svc.cluster.local:8080
    → nginx grpc_pass → rerun :9876
```

## Prerequisites

- A k8s cluster with service manager installed (provides the App CRD operator)
- A container registry accessible from the cluster
- `kubectl` configured for the cluster

## Building the Image

### Option A: External registry (production)

If you have push access to a registry the cluster trusts:

```bash
docker build -t <registry>/rerun-gateway:latest ./docker/
docker push <registry>/rerun-gateway:latest
```

Then update `k8s/rerun-app-crd.yaml` with the image path.

### Option B: Local in-cluster registry (development)

When you only have pull credentials (e.g., `ci-admin-user` on `registry.code.wabo.run`):

#### 1. Deploy a local registry

```bash
kubectl apply -f - <<EOF
apiVersion: v1
kind: Pod
metadata:
  name: registry
  namespace: default
  labels:
    app: registry
spec:
  containers:
  - name: registry
    image: registry:2
    ports:
    - containerPort: 5000
---
apiVersion: v1
kind: Service
metadata:
  name: registry
  namespace: default
spec:
  selector:
    app: registry
  ports:
  - port: 5000
    targetPort: 5000
EOF
```

#### 2. Configure k3s to trust the local registry

Get the registry ClusterIP:

```bash
REGISTRY_IP=$(kubectl get svc registry -n default -o jsonpath='{.spec.clusterIP}')
echo $REGISTRY_IP
```

Create a privileged pod to write the k3s registries config:

```bash
kubectl apply -f - <<EOF
apiVersion: v1
kind: Pod
metadata:
  name: configure-registry
  namespace: default
spec:
  hostPID: true
  restartPolicy: Never
  containers:
  - name: configure
    image: busybox
    securityContext:
      privileged: true
    command:
    - sh
    - -c
    - |
      cat > /host/etc/rancher/k3s/registries.yaml << REGEOF
      mirrors:
        "registry.default.svc.cluster.local:5000":
          endpoint:
            - "http://${REGISTRY_IP}:5000"
      REGEOF
      echo "Config written, restarting k3s..."
      nsenter -t 1 -m -u -i -n -p -- systemctl restart k3s
      sleep 10
      echo "Done"
    volumeMounts:
    - name: host
      mountPath: /host
  volumes:
  - name: host
    hostPath:
      path: /
EOF
```

Wait for the pod to complete and the cluster to stabilize (~15s).

#### 3. Build with Kaniko

```bash
# Create build context
cd docker && tar czf /tmp/build-context.tar.gz . && cd ..
BUILD_CONTEXT_B64=$(base64 -w0 /tmp/build-context.tar.gz)

# Run Kaniko build pod
kubectl apply -f - <<EOF
apiVersion: v1
kind: Pod
metadata:
  name: kaniko-build
  namespace: default
spec:
  restartPolicy: Never
  initContainers:
  - name: setup
    image: busybox
    command: ['sh', '-c', 'echo "\$B64" | base64 -d | tar xz -C /workspace']
    env:
    - name: B64
      value: "${BUILD_CONTEXT_B64}"
    volumeMounts:
    - name: workspace
      mountPath: /workspace
  containers:
  - name: kaniko
    image: gcr.io/kaniko-project/executor:latest
    args:
    - "--context=/workspace"
    - "--destination=registry.default.svc.cluster.local:5000/rerun-gateway:latest"
    - "--insecure"
    volumeMounts:
    - name: workspace
      mountPath: /workspace
  volumes:
  - name: workspace
    emptyDir: {}
EOF

# Wait for completion (~60s)
kubectl wait pod/kaniko-build -n default --for=condition=Ready=false --timeout=120s
kubectl logs kaniko-build -n default --tail=3
```

## Deploying the App CRD

```bash
kubectl apply -f k8s/rerun-app-crd.yaml
```

This creates:
- A Deployment with the rerun-gateway container
- A Service (`app-rerun-viewer`) on port 8080
- An Ingress at `/cell/rerun-viewer`

The operator automatically sets the `BASE_PATH` environment variable to `/cell/rerun-viewer`.

Verify:

```bash
kubectl get app rerun-viewer -n cell
kubectl get pods -l app.kubernetes.io/instance=rerun-viewer -n cell
curl -s http://<CLUSTER_IP>/cell/rerun-viewer/healthz  # should return "ok"
```

## Accessing the Viewer

### HTTPS (required for browser)

The viewer must be accessed over **HTTPS** because gRPC-web streaming requires HTTP/2, which browsers only negotiate over TLS:

```
https://<CLUSTER_IP>/cell/rerun-viewer/
```

Since the cluster uses a self-signed certificate, either:

1. **Launch Chrome with cert errors ignored** (recommended for dev):
   ```bash
   # macOS
   open -a "Google Chrome" --args --ignore-certificate-errors --user-data-dir=/tmp/chrome-insecure

   # Linux
   google-chrome --ignore-certificate-errors --user-data-dir=/tmp/chrome-insecure
   ```

2. **Import the cluster's TLS cert** into your OS trust store:
   ```bash
   openssl s_client -connect <CLUSTER_IP>:443 </dev/null 2>/dev/null | openssl x509 > cluster-cert.pem
   # macOS:
   sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain cluster-cert.pem
   # Linux:
   sudo cp cluster-cert.pem /usr/local/share/ca-certificates/cluster.crt && sudo update-ca-certificates
   ```

### Why HTTP doesn't work

Over plain HTTP, browsers attempt h2c (HTTP/2 cleartext) ALPN negotiation for gRPC-web streaming requests. Traefik's HTTP entrypoint doesn't support h2c, resulting in `ERR_ALPN_NEGOTIATION_FAILED`.

## Sending Data from Cluster Pods

Any pod in the cluster can log data to rerun via the App CRD service:

```python
import rerun as rr

rr.init("my_recording", spawn=False)
rr.connect_grpc("rerun+http://app-rerun-viewer.cell.svc.cluster.local:8080/proxy")

rr.log("world/points", rr.Points3D([[1, 2, 3]]))
```

This works because nginx accepts native HTTP/2 gRPC on port 8080 (via `grpc_pass`) and forwards to the rerun server internally.

A test logger pod is provided:

```bash
kubectl apply -f k8s/rerun-logger.yaml
kubectl logs rerun-logger -n cell -f
```

## File Structure

```
docker/
├── Dockerfile              # Image: python:3.11-slim + nginx + supervisor + rerun
├── entrypoint.sh           # Generates nginx.conf and index.html from BASE_PATH env var
├── nginx.conf.template     # Nginx config with __BASE_PATH__ placeholder
├── index.html.template     # Custom viewer page with fetch interceptor
└── supervisord.conf        # Manages nginx + rerun processes

k8s/
├── rerun-app-crd.yaml      # App CRD manifest (the only required resource)
└── rerun-logger.yaml       # Test pod that sends data to rerun
```

## How It Works

### The Fetch Interceptor (browser-side MITM)

The custom `index.html` overrides `window.fetch` before the WASM viewer loads:

```javascript
window.fetch = function(input, init) {
  const parsed = new URL(url, window.location.origin);
  if (parsed.pathname.match(/^\/rerun\./)) {
    // Rewrite: /rerun.Service/Method → /cell/rerun-viewer/rerun.Service/Method
    parsed.pathname = BASE_PATH + parsed.pathname;
    input = new Request(parsed.toString(), input);
  }
  return originalFetch.call(this, input, init);
};
```

The viewer loads normally from the App CRD path, connects to `rerun+https://host/proxy`, and all resulting gRPC-web calls are transparently redirected through the allowed path.

### Nginx Dual-Protocol Support

Nginx serves two types of gRPC clients on the same port (8080):

| Client | Protocol | Path | Nginx directive |
|--------|----------|------|----------------|
| Browser (via Traefik) | gRPC-web over HTTP/1.1 | `/cell/rerun-viewer/rerun.*` | `proxy_pass` |
| Cluster pods (direct) | Native gRPC over HTTP/2 | `/rerun.*`, `/proxy` | `grpc_pass` |

### The `BASE_PATH` Environment Variable

The App CRD operator sets `BASE_PATH=/cell/rerun-viewer` on the container. The entrypoint script substitutes `__BASE_PATH__` in the nginx and HTML templates at startup, making the image generic for any app name/namespace.
