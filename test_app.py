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
            assert 1 <= data["roll"] <= 6, f"out of range: {data}"
    print("PASS test_roll_in_range")


def test_cache_fills_on_startup():
    """Module load triggers exactly one ANU fetch."""
    with patch("requests.get", return_value=mock_anu()) as mock:
        importlib.reload(a)
        assert mock.call_count == 1, f"expected 1 fetch on startup, got {mock.call_count}"
    print("PASS test_cache_fills_on_startup")


def test_rolls_served_from_cache():
    """Rolls consume from cache without hitting ANU again."""
    with patch("requests.get", return_value=mock_anu()) as mock:
        importlib.reload(a)
        client = a.app.test_client()
        for _ in range(10):
            client.get("/roll")
        assert mock.call_count == 1, f"ANU hit {mock.call_count} times, expected 1"
    print("PASS test_rolls_served_from_cache")


def test_fallback_when_cache_empty():
    """Cache exhausted → 200 with source=fallback, no extra ANU call."""
    with patch("requests.get", return_value=mock_anu(numbers=[42])) as mock:
        importlib.reload(a)
        client = a.app.test_client()
        client.get("/roll")  # consumes the one quantum number
        resp = client.get("/roll")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["source"] == "fallback"
        assert 1 <= data["roll"] <= 6
        assert mock.call_count == 1, "should not re-hit ANU when cache empty"
    print("PASS test_fallback_when_cache_empty")


def test_anu_error_uses_fallback():
    """ANU unreachable at startup → rolls still return 200 with fallback."""
    with patch("requests.get", side_effect=Exception("ANU down")):
        importlib.reload(a)
        client = a.app.test_client()
        resp = client.get("/roll")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["source"] == "fallback"
        assert 1 <= data["roll"] <= 6
    print("PASS test_anu_error_uses_fallback")


def test_refresh_replaces_cache():
    """_refresh_cache clears old numbers and loads fresh ones."""
    with patch("requests.get", return_value=mock_anu(numbers=list(range(10)))):
        importlib.reload(a)
    with patch("requests.get", return_value=mock_anu(numbers=[255] * 10)):
        a._refresh_cache()
    client = a.app.test_client()
    resp = client.get("/roll")
    data = json.loads(resp.data)
    assert data["source"] == "quantum"
    assert data["roll"] == 255 % 6 + 1  # 4
    print("PASS test_refresh_replaces_cache")


if __name__ == "__main__":
    test_roll_in_range()
    test_cache_fills_on_startup()
    test_rolls_served_from_cache()
    test_fallback_when_cache_empty()
    test_anu_error_uses_fallback()
    test_refresh_replaces_cache()
    print("\nAll tests passed.")
