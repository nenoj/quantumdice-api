import os
import random
import threading
from collections import deque

import requests
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
from flask import Flask, jsonify

load_dotenv()

app = Flask(__name__)

ANU_URL = "https://api.quantumnumbers.anu.edu.au"
BATCH_SIZE = 1024

FALLBACK_BYTES = [
    196, 63, 168, 122, 249, 64, 213, 18, 124, 116, 108, 16, 37, 34, 57, 243,
    148, 147, 125, 137, 185, 237, 138, 114, 202, 243, 52, 147, 3, 14, 142, 5,
    98, 82, 17, 100, 123, 143, 129, 62, 129, 155, 21, 224, 152, 227, 47, 109,
    194, 77, 67, 5, 63, 181, 134, 104, 205, 62, 30, 242, 106, 137, 161, 126,
    87, 196, 243, 106, 240, 114, 191, 97, 119, 46, 216, 0, 75, 83, 3, 139,
    241, 38, 66, 249, 181, 82, 248, 98, 55, 28, 117, 242, 51, 135, 27, 128,
    174, 217, 253, 226,
]

_cache = deque()
_lock = threading.Lock()


def _fetch_batch():
    api_key = os.getenv("ANU_API_KEY")
    resp = requests.get(
        ANU_URL,
        params={"length": BATCH_SIZE, "type": "uint8"},
        headers={"x-api-key": api_key},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["data"]


def _refresh_cache():
    try:
        numbers = _fetch_batch()
        with _lock:
            _cache.clear()
            _cache.extend(numbers)
    except Exception:
        pass  # keep existing cache if ANU is unreachable


def _get_quantum_byte():
    with _lock:
        if _cache:
            return _cache.popleft(), "quantum"
    return random.choice(FALLBACK_BYTES), "fallback"


@app.route("/roll")
def roll():
    byte, source = _get_quantum_byte()
    result = (byte % 6) + 1
    return jsonify({"roll": result, "source": source})


_refresh_cache()

scheduler = BackgroundScheduler()
scheduler.add_job(_refresh_cache, "interval", hours=24)
scheduler.start()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
