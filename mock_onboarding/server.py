#!/usr/bin/env python3
"""Mock account-opening ingestion service with injected failures.

Each accepted file represents a submission of approved account applications.
Duplicate ingestion repeats the submission. The ingestion API has no cancellation.

Uses only the Python standard library:
    python3 server.py [--port 9200] [--seed 7]

Configuration: ONBOARDING_FAIL_RATE, ONBOARDING_LOST_RATE,
ONBOARDING_LOST_SECONDS, ONBOARDING_SEED, ONBOARDING_PORT.
"""
import argparse
import hashlib
import json
import os
import random
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

FAIL_RATE = float(os.environ.get("ONBOARDING_FAIL_RATE", "0.20"))    # Rejected before ingestion.
LOST_RATE = float(os.environ.get("ONBOARDING_LOST_RATE", "0.15"))    # Delayed response after ingestion.
LOST_SECONDS = float(os.environ.get("ONBOARDING_LOST_SECONDS", "120"))

DELIVERIES = []          # Accepted submissions. Records are shared with KEYS.
KEYS = {}                # idempotency_key -> delivery record
_rng = None
_lock = threading.Lock()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _json(self, code: int, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/online":
            return self._json(200, {"online": True})
        if self.path == "/debug/deliveries":
            return self._json(200, DELIVERIES)
        if self.path == "/debug/reset":
            with _lock:
                DELIVERIES.clear()
                KEYS.clear()
            return self._json(200, {"cleared": True})
        return self._json(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/ingest":
            return self._json(404, {"error": "not found"})
        key = self.headers.get("Idempotency-Key")
        if not key:
            return self._json(400, {"error": "missing Idempotency-Key header"})
        file_name = self.headers.get("X-File-Name", "unnamed")
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        sha = hashlib.sha256(body).hexdigest()

        with _lock:
            seen = KEYS.get(key)
            if seen is not None:  # repeated delivery of the same operation: no re-ingestion
                seen["attempts"] += 1
                return self._json(200, {**seen, "deduplicated": True})

            roll = _rng.random()  # one outcome roll per attempt; seeded => reproducible
            if roll < FAIL_RATE:
                return self._json(500, {"error": "ingestion temporarily unavailable"})

            record = {"delivery_id": f"DLV-{len(DELIVERIES) + 1:04d}",
                      "idempotency_key": key, "file_name": file_name,
                      "sha256": sha, "ingested_at": int(time.time()), "attempts": 1}
            KEYS[key] = record
            DELIVERIES.append(record)  # Record ingestion before sending the response.

        if roll < FAIL_RATE + LOST_RATE:  # Delay the receipt after ingestion.
            time.sleep(LOST_SECONDS)
        return self._json(200, record)


def main():
    global _rng
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=int(os.environ.get("ONBOARDING_PORT", "9200")))
    ap.add_argument("--seed", type=int, default=int(os.environ.get("ONBOARDING_SEED", "7")))
    args = ap.parse_args()
    _rng = random.Random(args.seed)
    print(f"mock_onboarding listening on :{args.port}  seed={args.seed} "
          f"fail={FAIL_RATE} lost={LOST_RATE} lost_seconds={LOST_SECONDS}")
    ThreadingHTTPServer(("0.0.0.0", args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
