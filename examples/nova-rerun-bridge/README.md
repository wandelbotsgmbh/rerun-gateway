# NOVA + nova-rerun-bridge → rerun-gateway

End-to-end example: plan a robot trajectory with [Wandelbots NOVA](https://github.com/wandelbotsgmbh/wandelbots-nova)
and stream it to a **remote** Rerun viewer — the [`rerun-gateway`](../../README.md) app
running in the cluster — instead of a local desktop viewer.

What [`plan_and_log.py`](./plan_and_log.py) does:

1. **Declares a virtual robot as a decorator dependency.** The `@nova.program`
   decorator lists a `virtual_controller(...)` in its `ProgramPreconditions`. When the
   program runs, NOVA ensures that controller exists in the cell, deploying a simulated
   Universal Robots UR10e on the fly — no physical hardware needed.
2. **Plans a trajectory.** A small out-and-back Cartesian move is planned for that robot.
3. **Logs it via nova-rerun-bridge.** The robot model, safety zones, action waypoints
   and the dense joint trajectory are logged to Rerun and streamed to the gateway over
   gRPC, where you view them in the browser.

---

## ⚠️ Version compatibility (read first)

`nova-rerun-bridge` (shipped with `wandelbots-nova` 5.x) pins **`rerun-sdk==0.26.2`** and
uses APIs removed in later Rerun releases (e.g. `rr.Transform3D(clear=...)`, gone in 0.33).
**The Rerun client and the gateway server must both be on the 0.26.x line.**

The published gateway image and this repo's [`Dockerfile`](../../rerun-gateway/Dockerfile)
default to `RERUN_SDK_VERSION=0.33.0`, which is **incompatible** with the bridge. A
matching **0.26.2 gateway image has already been built and pushed** to the Wandelbots
registry:

```
wandelbots.azurecr.io/rerun-gateway:0.26.2-test
```

> To rebuild it yourself: `docker buildx build --platform linux/amd64 --build-arg RERUN_SDK_VERSION=0.26.2 -t <registry>/rerun-gateway:0.26.2 --push ../../rerun-gateway/`
> (rerun 0.26.2 rejects `--cors-allow-origin`; drop that flag from `supervisord.conf` in the 0.26.2 build.)

---

## Step-by-step

### 1. Deploy the rerun-gateway app (0.26.2)

`<HOST>` = your instance host (e.g. `172.31.10.154`). `<COOKIE>` = the `_oauth2_proxy`
auth cookie (omit the `Cookie` header on local/unauthenticated instances).

**Via the Apps API** (v2):

```bash
curl -s -X POST "http://<HOST>/api/v2/cells/cell/apps" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "rerun-gateway",
    "app_icon": "app-icon.png",
    "container_image": { "image": "wandelbots.azurecr.io/rerun-gateway:0.26.2-test" },
    "environment": [ {"name": "RERUN_MEMORY_LIMIT", "value": "500MB"} ],
    "resources": { "memory_limit": "2000Mi" },
    "port": 8080
  }'
```

Wait until it is running:

```bash
curl -s "http://<HOST>/api/v2/cells/cell/apps"        # -> ["rerun-gateway"]
```

> **novax note:** the `novax` CLI (`wandelbots-nova[novax]`) serves your *programs*
> locally/in-app; the rerun-gateway itself is a plain container app, so it is installed
> through the Apps API above (that endpoint is the same App system a novax app is
> published to). Delete it later with:
> `curl -s -X DELETE "http://<HOST>/api/v2/cells/cell/apps/rerun-gateway"`.

### 2. Install the example dependencies

Python 3.11 or 3.12 (`wandelbots-nova` requires `>=3.11,<3.13`).

```bash
uv venv --python 3.12 && source .venv/bin/activate
uv pip install "wandelbots-nova[nova-rerun-bridge]"   # pulls rerun-sdk 0.26.2
uv run download-models                                # optional: pre-fetch robot meshes
```

### 3. Point the example at NOVA and the gateway

| Env var             | Purpose                                                          |
|---------------------|------------------------------------------------------------------|
| `NOVA_API`          | Base URL of the NOVA instance, e.g. `http://<HOST>`              |
| `NOVA_ACCESS_TOKEN` | Access token (omit for local/unauthenticated instances)         |
| `RERUN_ADDRESS`     | Rerun gRPC endpoint (see the two run modes below)               |

### 4. Run it

**A) From your laptop** — port-forward the gateway (raw TCP preserves the HTTP/2 h2c
gRPC stream), then run:

```bash
kubectl port-forward -n cell svc/app-rerun-gateway 8080:8080 &

export NOVA_API="http://<HOST>"
export RERUN_ADDRESS="rerun+http://127.0.0.1:8080/proxy"
python plan_and_log.py
```

**B) From the in-cluster VS Code app** (`visual-studio-code`) — **no port-forward
needed.** A pod in the cell can reach the gateway by its service DNS name, which is the
script's default `RERUN_ADDRESS`, so you only set `NOVA_API`:

```bash
export NOVA_API="http://api-gateway:8080"             # in-cluster service name
# RERUN_ADDRESS defaults to rerun+http://app-rerun-gateway:8080/proxy
python plan_and_log.py
```

> The bridge special-cases the VS Code environment (`VSCODE_PROXY_URI` is set there) by
> writing a `nova.rrd` file. The example deliberately calls `rr.connect_grpc()` **after**
> constructing the bridge, so the live gRPC stream to the gateway wins in that
> environment too. (Verified: run from an in-cluster pod with `VSCODE_PROXY_URI` set,
> logging straight to `app-rerun-gateway:8080` with no port-forward.)

### 5. View the trajectory

Open the web viewer; the recording appears as soon as the program finishes:

```
https://<HOST>/cell/rerun-gateway/
```

---

## How the remote connection works

With `spawn=False` the bridge doesn't launch a local viewer. The example initializes the
recording (`application_id="nova"`, which the bridge's blueprint targets) and redirects
its sink to the gateway:

```python
async with NovaRerunBridge(nova_client, spawn=False) as bridge:
    rr.init(application_id="nova", spawn=False)
    rr.connect_grpc(RERUN_ADDRESS)      # all bridge.log_* calls now stream to the gateway
    ...
```
