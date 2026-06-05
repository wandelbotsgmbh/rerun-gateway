import rerun as rr
import numpy as np
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

# Simple health endpoint
class Health(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")
    def log_message(self, *args):
        pass

threading.Thread(target=lambda: HTTPServer(("", 8080), Health).serve_forever(), daemon=True).start()

rr.init("test_recording", spawn=False)
rr.connect_grpc("rerun+http://app-rerun-viewer.cell.svc.cluster.local:8080/proxy")

print("Logging test data...")
i = 0
while True:
    positions = np.random.randn(100, 3).astype(np.float32)
    colors = np.random.randint(0, 255, (100, 3), dtype=np.uint8)
    rr.set_time("frame", sequence=i)
    rr.log("world/points", rr.Points3D(positions, colors=colors, radii=0.05))
    rr.log("world/text", rr.TextLog(f"Frame {i}: logged 100 random points"))
    if i % 10 == 0:
        print(f"Logged frame {i}")
    time.sleep(0.5)
    i += 1
