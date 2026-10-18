#!/usr/bin/env python3
"""Mock identity-card OCR service with injected failures. Uses the standard library.

    python3 server.py [--port 9100] [--seed 42]

Tunable via env: OCR_FAIL_RATE, OCR_HANG_RATE, OCR_HANG_SECONDS, OCR_SEED, OCR_PORT.
"""
import argparse
import hashlib
import json
import os
import random
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

FAIL_RATE = float(os.environ.get("OCR_FAIL_RATE", "0.20"))
HANG_RATE = float(os.environ.get("OCR_HANG_RATE", "0.10"))
HANG_SECONDS = float(os.environ.get("OCR_HANG_SECONDS", "600"))  # Simulated response delay.

REQUESTS = []          # Recorded attempts for debugging.
_rng = None
_lock = threading.Lock()


def parse_fields(image_ref: str) -> dict:
    """Deterministic: the same image always yields the same fields."""
    h = int(hashlib.sha256(image_ref.encode()).hexdigest(), 16)
    return {
        "id_number": f"TEST-ID-{100000 + h % 900000}",
        "full_name": f"Test Applicant {h % 10000:04d}",
        "dob": f"{1955 + h % 45}-{1 + (h >> 6) % 12:02d}-{1 + (h >> 11) % 28:02d}",
        "issue_date": f"{2016 + (h >> 17) % 10}-{1 + (h >> 21) % 12:02d}-{1 + (h >> 26) % 28:02d}",
        "confidence": round(0.80 + (h % 20) / 100.0, 2),
    }


def is_unreadable(image_ref: str) -> bool:
    """Return whether the image reference identifies an unreadable scan."""
    return "badscan" in image_ref.lower()


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

    def _record(self, case_id, image_ref, outcome):
        with _lock:
            REQUESTS.append({"seq": len(REQUESTS) + 1, "case_id": case_id,
                             "image_ref": image_ref, "outcome": outcome,
                             "ts": round(time.time(), 3)})

    def do_GET(self):
        if self.path == "/online":
            return self._json(200, {"online": True})
        if self.path == "/debug/requests":
            return self._json(200, REQUESTS)
        if self.path == "/debug/reset":
            with _lock:
                REQUESTS.clear()
            return self._json(200, {"cleared": True})
        return self._json(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/ocr/parse":
            return self._json(404, {"error": "not found"})
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
            case_id, image_ref = str(body["case_id"]), str(body["image_ref"])
        except Exception:
            return self._json(400, {"error": "need JSON body {case_id, image_ref}"})

        if is_unreadable(image_ref):
            self._record(case_id, image_ref, "unreadable")
            return self._json(422, {"error": f"cannot read identity-card fields from '{image_ref}' (scan quality)"})

        with _lock:  # one outcome roll per attempt; seeded => reproducible per request sequence
            roll = _rng.random()

        if roll < FAIL_RATE:  # Transient failure before a result is produced.
            self._record(case_id, image_ref, "error_500")
            return self._json(500, {"error": "internal OCR engine error (transient)"})

        if roll < FAIL_RATE + HANG_RATE:  # Delay the result to simulate a client timeout.
            self._record(case_id, image_ref, "hang")
            time.sleep(HANG_SECONDS)
            return self._json(200, parse_fields(image_ref))

        self._record(case_id, image_ref, "ok")
        return self._json(200, parse_fields(image_ref))


def main():
    global _rng
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=int(os.environ.get("OCR_PORT", "9100")))
    ap.add_argument("--seed", type=int, default=int(os.environ.get("OCR_SEED", "42")))
    args = ap.parse_args()
    _rng = random.Random(args.seed)
    print(f"mock_ocr listening on :{args.port}  seed={args.seed} "
          f"fail={FAIL_RATE} hang={HANG_RATE} hang_seconds={HANG_SECONDS}")
    ThreadingHTTPServer(("0.0.0.0", args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
