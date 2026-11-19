import os
import sys

# Ensure UTF-8 output on console
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

import uvicorn

# Ensure the root directory is on the python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    print("=" * 70)
    print(">> STARTING SCALER PROGRAM EVALUATOR & SALES DECISION ENGINE")
    print("=" * 70)
    print(">> Empirical Funnel Matrix: 13,180 records precomputed")
    print(f">> Server listening on: http://{host}:{port}")
    # On Render free/starter (<=1GB RAM), default to 1 worker to prevent OOM.
    # Each uvicorn worker uses ~150-200MB. 4 workers = 600-800MB -> instant OOM on 512MB.
    # Set WORKERS env var in Render dashboard to override (max 2 on 512MB, max 4 on 2GB+).
    default_workers = 1  # Safe default for Render free tier
    workers_count = int(os.environ.get("WEB_CONCURRENCY", os.environ.get("WORKERS", default_workers)))
    print(f">> Worker Processes: {workers_count}")
    print("=" * 70)
    uvicorn.run("src.server:app", host=host, port=port, workers=workers_count, log_level="info", timeout_keep_alive=120)
