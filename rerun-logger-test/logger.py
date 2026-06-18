import rerun as rr
import numpy as np
import time
import sys
import os
import traceback
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import json
from datetime import datetime, timezone

# --- Configuration ---
VIEWER_URL = os.environ.get("VIEWER_URL", "rerun+http://app-rerun-gateway:8080/proxy")
# Heavier data: 1000 points per frame (10x more), faster rate (100ms instead of 500ms)
NUM_POINTS = int(os.environ.get("NUM_POINTS", "1000"))
FRAME_INTERVAL = float(os.environ.get("FRAME_INTERVAL", "0.1"))  # 100ms = 10 FPS
# Flush every N frames to detect connection failures
FLUSH_EVERY = int(os.environ.get("FLUSH_EVERY", "50"))
FLUSH_TIMEOUT = float(os.environ.get("FLUSH_TIMEOUT", "5.0"))  # seconds
# Reconnect settings
MAX_RECONNECT_ATTEMPTS = int(os.environ.get("MAX_RECONNECT_ATTEMPTS", "10"))
RECONNECT_DELAY = float(os.environ.get("RECONNECT_DELAY", "5.0"))

# --- Health endpoint with status ---
health_status = {
    "connected": False,
    "last_flush_ok": None,
    "last_flush_time": None,
    "frames_sent": 0,
    "flush_failures": 0,
    "reconnects": 0,
    "started_at": datetime.now(timezone.utc).isoformat(),
}


class Health(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/app-icon.png":
            try:
                with open("/app-icon.png", "rb") as f:
                    data = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            except FileNotFoundError:
                self.send_response(404)
                self.end_headers()
        else:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(health_status, indent=2).encode())

    def log_message(self, *args):
        pass


threading.Thread(
    target=lambda: HTTPServer(("", 8080), Health).serve_forever(), daemon=True
).start()


def log_msg(msg):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    print(f"[{ts}] {msg}", flush=True)


def connect():
    """Connect to the rerun viewer, with retry logic."""
    for attempt in range(MAX_RECONNECT_ATTEMPTS):
        try:
            log_msg(f"Connecting to {VIEWER_URL} (attempt {attempt + 1})...")
            rr.connect_grpc(VIEWER_URL)
            health_status["connected"] = True
            log_msg("Connected successfully.")
            return True
        except Exception as e:
            log_msg(f"Connection failed: {e}")
            if attempt < MAX_RECONNECT_ATTEMPTS - 1:
                time.sleep(RECONNECT_DELAY)
    log_msg("FATAL: All reconnect attempts exhausted.")
    health_status["connected"] = False
    return False


def flush_with_timeout():
    """Attempt to flush pending data. Returns True on success, False on failure."""
    try:
        # flush() is on RecordingStream, not a top-level function in rerun 0.33
        rec = rr.get_data_recording()
        if rec is None:
            log_msg("FLUSH FAILED: No active recording stream")
            return False
        rec.flush(timeout_sec=FLUSH_TIMEOUT)
        return True
    except Exception as e:
        log_msg(f"FLUSH FAILED: {type(e).__name__}: {e}")
        traceback.print_exc()
        return False


# --- Main loop ---
rec = rr.init("test_recording", spawn=False)

if not connect():
    log_msg("Cannot connect to viewer. Exiting.")
    sys.exit(1)

log_msg(
    f"Logging started: {NUM_POINTS} points/frame, "
    f"{FRAME_INTERVAL}s interval, flush every {FLUSH_EVERY} frames"
)

i = 0
consecutive_flush_failures = 0

while True:
    try:
        # Generate heavier test data
        positions = np.random.randn(NUM_POINTS, 3).astype(np.float32)
        colors = np.random.randint(0, 255, (NUM_POINTS, 3), dtype=np.uint8)
        radii = np.random.uniform(0.02, 0.1, NUM_POINTS).astype(np.float32)

        rr.set_time("frame", sequence=i)
        rr.log("world/points", rr.Points3D(positions, colors=colors, radii=radii))
        rr.log("world/text", rr.TextLog(f"Frame {i}: {NUM_POINTS} points"))

        # Also log a mesh-like entity for extra data weight
        if i % 10 == 0:
            mesh_positions = np.random.randn(500, 3).astype(np.float32) * 2
            mesh_colors = np.random.randint(0, 255, (500, 3), dtype=np.uint8)
            rr.log(
                "world/cloud",
                rr.Points3D(mesh_positions, colors=mesh_colors, radii=0.03),
            )

        health_status["frames_sent"] = i

        # Periodic flush to verify connection is alive
        if i > 0 and i % FLUSH_EVERY == 0:
            flush_ok = flush_with_timeout()
            health_status["last_flush_time"] = datetime.now(timezone.utc).isoformat()
            health_status["last_flush_ok"] = flush_ok

            if flush_ok:
                consecutive_flush_failures = 0
                if i % (FLUSH_EVERY * 10) == 0:
                    log_msg(
                        f"Frame {i}: flush OK, "
                        f"{health_status['flush_failures']} total failures, "
                        f"{health_status['reconnects']} reconnects"
                    )
            else:
                consecutive_flush_failures += 1
                health_status["flush_failures"] += 1
                log_msg(
                    f"Frame {i}: flush FAILED "
                    f"({consecutive_flush_failures} consecutive)"
                )

                # After 3 consecutive failures, attempt reconnect
                if consecutive_flush_failures >= 3:
                    log_msg("3 consecutive flush failures — attempting reconnect...")
                    health_status["reconnects"] += 1
                    health_status["connected"] = False

                    if connect():
                        consecutive_flush_failures = 0
                    else:
                        log_msg("Reconnect failed. Will retry on next flush cycle.")

        if i % 100 == 0:
            log_msg(f"Logged frame {i}")

        time.sleep(FRAME_INTERVAL)
        i += 1

    except KeyboardInterrupt:
        log_msg("Interrupted. Exiting.")
        break
    except Exception as e:
        log_msg(f"ERROR in main loop: {type(e).__name__}: {e}")
        traceback.print_exc()
        time.sleep(1.0)
