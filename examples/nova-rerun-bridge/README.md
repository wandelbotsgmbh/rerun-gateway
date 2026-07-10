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

The recommended way to run it is from the **in-cluster VS Code app**, so everything
(NOVA, the gateway, and your program) runs inside the same cluster network — no local
tooling, no port-forwarding. `<HOST>` below is your instance host (e.g. `172.31.10.154`).

---

## Quick start (in-cluster VS Code app)

### 1. Deploy the rerun-gateway app

No terminal or auth cookies needed — use the instance's built-in **Swagger UI**, an
interactive web form for the API.

1. Open the API explorer in your browser (also linked from the instance home screen):

   ```
   https://<HOST>/api/v2/ui
   ```

2. If your instance requires login, click **Authorize** (top right) and paste the
   access token from the Developer Portal. (Local/unauthenticated instances skip this.)
3. Find **`POST /cells/{cell}/apps`** ("Install an app"), click it, then **Try it out**.
4. Set `cell` to `cell` and paste this into the request body, then click **Execute**:

   ```json
   {
     "name": "rerun-gateway",
     "app_icon": "app-icon.png",
     "container_image": { "image": "wandelbots.azurecr.io/rerun-gateway:0.26.2-test" },
     "environment": [ { "name": "RERUN_MEMORY_LIMIT", "value": "500MB" } ],
     "resources": { "memory_limit": "2000Mi" },
     "port": 8080
   }
   ```

   > This is a Rerun **0.26.2** build — the version nova-rerun-bridge needs. See
   > [Version compatibility](#version-compatibility) if you want the details.

5. Check it is running with **`GET /cells/{cell}/apps`** (`cell` = `cell`) → the response
   should list `"rerun-gateway"`.

### 2. Open the VS Code app

Install/open the **Visual Studio Code** app (`visual-studio-code`) from your instance
home screen — this gives you a browser-based VS Code running inside the cluster. If it
isn't installed yet, install it the same way as step 1 (`POST /cells/{cell}/apps`) or
from the instance's app catalog.

### 3. Run the example in the VS Code terminal

Open a terminal in the VS Code app and run:

```bash
# get the example
git clone https://github.com/wandelbotsgmbh/rerun-gateway.git
cd rerun-gateway/examples/nova-rerun-bridge

# install (pulls rerun-sdk 0.26.2 automatically); Python 3.11 or 3.12
pip install "wandelbots-nova[nova-rerun-bridge]"
download-models   # optional: pre-fetch robot meshes so the first run is faster

# point at your NOVA instance and run — no port-forward needed
export NOVA_API="http://<HOST>"
python plan_and_log.py
```

`RERUN_ADDRESS` defaults to the in-cluster service name
`rerun+http://app-rerun-gateway:8080/proxy`, which the VS Code pod reaches directly — so
you only set `NOVA_API`. (On authenticated instances also `export NOVA_ACCESS_TOKEN=...`.)

### 4. View the trajectory

Open the gateway's web viewer; the recording appears as soon as the program finishes:

```
https://<HOST>/cell/rerun-gateway/
```

You should see the UR10e robot and its planned trajectory in the 3D view.

---

## Advanced

### Run from your laptop (with port-forward)

If you'd rather run the program on your own machine, the gateway's gRPC endpoint isn't
directly reachable through the ingress, so tunnel to it with `kubectl port-forward` (raw
TCP preserves the HTTP/2 h2c stream Rerun needs):

```bash
kubectl port-forward -n cell svc/app-rerun-gateway 8080:8080 &

export NOVA_API="http://<HOST>"
export RERUN_ADDRESS="rerun+http://127.0.0.1:8080/proxy"
python plan_and_log.py
```

| Env var             | Purpose                                                          |
|---------------------|------------------------------------------------------------------|
| `NOVA_API`          | Base URL of the NOVA instance, e.g. `http://<HOST>`              |
| `NOVA_ACCESS_TOKEN` | Access token (omit for local/unauthenticated instances)         |
| `RERUN_ADDRESS`     | Rerun gRPC endpoint (default: the in-cluster service name)       |

### How the remote connection works

With `spawn=False` the bridge doesn't launch a local viewer. The example initializes the
recording (`application_id="nova"`, which the bridge's blueprint targets) and redirects
its sink to the gateway:

```python
async with NovaRerunBridge(nova_client, spawn=False) as bridge:
    rr.init(application_id="nova", spawn=False)
    rr.connect_grpc(RERUN_ADDRESS)      # all bridge.log_* calls now stream to the gateway
    ...
```

The bridge special-cases the VS Code environment (`VSCODE_PROXY_URI` is set there) by
writing a `nova.rrd` file. The example deliberately calls `rr.connect_grpc()` **after**
constructing the bridge, so the live gRPC stream to the gateway wins in that environment
too — which is why the in-cluster VS Code run streams straight to `app-rerun-gateway:8080`
with no port-forward.

### Version compatibility

`nova-rerun-bridge` (shipped with `wandelbots-nova` 5.x) pins **`rerun-sdk==0.26.2`** and
uses APIs removed in later Rerun releases (e.g. `rr.Transform3D(clear=...)`, gone in 0.33).
**The Rerun client and the gateway server must both be on the 0.26.x line.**

The published gateway image and this repo's [`Dockerfile`](../../rerun-gateway/Dockerfile)
default to `RERUN_SDK_VERSION=0.34.1`, which is **incompatible** with the bridge. A
matching **0.26.2 image has already been built and pushed** to the Wandelbots registry —
`wandelbots.azurecr.io/rerun-gateway:0.26.2-test` — which is what step 1 deploys.

To rebuild it yourself:

```bash
docker buildx build --platform linux/amd64 \
  --build-arg RERUN_SDK_VERSION=0.26.2 \
  -t <registry>/rerun-gateway:0.26.2 --push ../../rerun-gateway/
```

> rerun 0.26.2 rejects `--cors-allow-origin`; drop that flag from `supervisord.conf` in
> the 0.26.2 build (the browser fetch interceptor injects the needed headers anyway).

### novax note & cleanup

The `novax` CLI (`wandelbots-nova[novax]`) serves your *programs* locally/in-app; the
rerun-gateway itself is a plain container app, installed through the Apps endpoints (the
same App system a novax app is published to). To remove the gateway later, use
**`DELETE /cells/{cell}/apps/{app}`** in the Swagger UI with app `rerun-gateway`.
