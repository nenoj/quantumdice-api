import os
import threading
from collections import deque

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify

load_dotenv()

app = Flask(__name__)

ANU_URL = "https://api.quantumnumbers.anu.edu.au"
BATCH_SIZE = 64

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


def _get_quantum_byte():
    with _lock:
        if not _cache:
            numbers = _fetch_batch()
            _cache.extend(numbers)
        return _cache.popleft()


@app.route("/roll")
def roll():
    try:
        byte = _get_quantum_byte()
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    result = (byte % 6) + 1
    return jsonify({"roll": result})


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
