import json
import importlib
from unittest.mock import patch

import app as a


def make_client():
    importlib.reload(a)
    return a.app.test_client()


def mock_anu(numbers=None):
    if numbers is None:
        numbers = list(range(64))
    m = __import__("unittest.mock", fromlist=["MagicMock"]).MagicMock()
    m.raise_for_status = lambda: None
    m.json = lambda: {"data": numbers}
    return m


def test_roll_in_range():
    with patch("requests.get", return_value=mock_anu()):
        client = make_client()
        for _ in range(10):
            resp = client.get("/roll")
            assert resp.status_code == 200
            data = json.loads(resp.data)
            assert "roll" in data
            assert 1 <= data["roll"] <= 6, f"out of range: {data}"
    print("PASS test_roll_in_range")


def test_cache_refills():
    """Exhaust the first batch, confirm a second fetch is triggered."""
    call_count = 0
    original_fetch = a._fetch_batch

    def counting_fetch():
        nonlocal call_count
        call_count += 1
        return list(range(64))

    with patch.object(a, "_fetch_batch", side_effect=counting_fetch):
        importlib.reload(a)
        a._fetch_batch = counting_fetch
        client = a.app.test_client()
        # 65 calls should trigger exactly 2 fetches (batch size = 64)
        for _ in range(65):
            client.get("/roll")
    assert call_count == 2, f"expected 2 fetches, got {call_count}"
    print("PASS test_cache_refills")


def test_anu_error_returns_500():
    with patch("requests.get", side_effect=Exception("ANU down")):
        client = make_client()
        resp = client.get("/roll")
        assert resp.status_code == 500
    print("PASS test_anu_error_returns_500")


if __name__ == "__main__":
    test_roll_in_range()
    test_cache_refills()
    test_anu_error_returns_500()
    print("\nAll tests passed.")
