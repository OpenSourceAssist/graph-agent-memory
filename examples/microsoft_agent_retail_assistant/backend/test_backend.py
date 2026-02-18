"""Standalone smoke tests for the retail assistant backend.

Requires the backend server to be running at http://localhost:8000.
No external dependencies beyond the Python standard library.

Usage:
    python test_backend.py
    python test_backend.py --base-url http://localhost:9000
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request

DEFAULT_BASE_URL = "http://localhost:8000"
SESSION_ID = "smoke-test-1"
MAX_OUTPUT = 200


def truncate(obj: object, max_len: int = MAX_OUTPUT) -> str:
    """Return a truncated string representation of obj."""
    text = json.dumps(obj, indent=2) if isinstance(obj, (dict, list)) else str(obj)
    if len(text) > max_len:
        return text[:max_len] + "..."
    return text


def request(method: str, path: str, base_url: str, body: dict | None = None) -> tuple[int, dict | str]:
    """Make an HTTP request and return (status_code, parsed_response)."""
    url = f"{base_url}{path}"
    data = json.dumps(body).encode() if body else None
    headers = {"Content-Type": "application/json"} if body else {}
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode()
            try:
                return resp.status, json.loads(raw)
            except json.JSONDecodeError:
                return resp.status, raw
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw)
        except json.JSONDecodeError:
            return e.code, raw


def test_health(base_url: str) -> bool:
    """Test the health check endpoint."""
    status, data = request("GET", "/health", base_url)
    ok = status == 200 and isinstance(data, dict) and "status" in data
    print(f"  {truncate(data)}")
    return ok


def test_chat_sync(base_url: str) -> bool:
    """Test the synchronous chat endpoint."""
    body = {"message": "What running shoes do you recommend?", "session_id": SESSION_ID}
    status, data = request("POST", "/chat/sync", base_url, body)
    ok = status == 200 and isinstance(data, dict) and "response" in data
    print(f"  {truncate(data)}")
    return ok


def test_chat_stream(base_url: str) -> bool:
    """Test the SSE streaming chat endpoint (reads first few events)."""
    url = f"{base_url}/chat"
    body = json.dumps({"message": "I prefer Nike shoes under $150", "session_id": SESSION_ID}).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            events = []
            for line in resp:
                decoded = line.decode().strip()
                if decoded.startswith("data:"):
                    events.append(decoded)
                    if len(events) >= 5:
                        break
            ok = resp.status == 200 and len(events) > 0
            print(f"  events_received={len(events)}")
            for ev in events:
                print(f"  {truncate(ev)}")
            return ok
    except urllib.error.HTTPError as e:
        print(f"  status={e.code}")
        return False


def test_memory_context(base_url: str) -> bool:
    """Test the memory context endpoint."""
    path = f"/memory/context?session_id={SESSION_ID}&query=shoes"
    status, data = request("GET", path, base_url)
    ok = status == 200 and isinstance(data, dict)
    print(f"  {truncate(data)}")
    return ok


def test_memory_preferences(base_url: str) -> bool:
    """Test the memory preferences endpoint."""
    path = f"/memory/preferences?session_id={SESSION_ID}"
    status, data = request("GET", path, base_url)
    ok = status == 200 and isinstance(data, dict) and "preferences" in data
    print(f"  {truncate(data)}")
    return ok


def test_memory_graph(base_url: str) -> bool:
    """Test the memory graph endpoint."""
    path = f"/memory/graph?session_id={SESSION_ID}"
    status, data = request("GET", path, base_url)
    ok = status == 200 and isinstance(data, dict) and "nodes" in data and "edges" in data
    print(f"  {truncate(data)}")
    return ok


def test_product_search(base_url: str) -> bool:
    """Test the product search endpoint."""
    path = "/products/search?query=shoes"
    status, data = request("GET", path, base_url)
    ok = status == 200 and isinstance(data, dict) and "products" in data and "total" in data
    print(f"  {truncate(data)}")
    return ok


def _get_a_product_id(base_url: str) -> str | None:
    """Helper to fetch a product ID from search results."""
    status, data = request("GET", "/products/search?query=shoes", base_url)
    if status == 200 and isinstance(data, dict) and data.get("products"):
        return data["products"][0]["id"]
    return None


def test_get_product(base_url: str) -> bool:
    """Test the get product detail endpoint."""
    product_id = _get_a_product_id(base_url)
    if not product_id:
        print("  SKIP: no products found to test with")
        return True

    path = f"/products/{product_id}"
    status, data = request("GET", path, base_url)
    ok = status == 200 and isinstance(data, dict) and "name" in data
    print(f"  {truncate(data)}")
    return ok


def test_related_products(base_url: str) -> bool:
    """Test the related products endpoint."""
    product_id = _get_a_product_id(base_url)
    if not product_id:
        print("  SKIP: no products found to test with")
        return True

    path = f"/products/{product_id}/related"
    status, data = request("GET", path, base_url)
    ok = status == 200 and isinstance(data, dict) and "related_products" in data
    print(f"  {truncate(data)}")
    return ok


TESTS = [
    ("Health check", test_health),
    ("Sync chat", test_chat_sync),
    ("Streaming chat (SSE)", test_chat_stream),
    ("Memory context", test_memory_context),
    ("Memory preferences", test_memory_preferences),
    ("Memory graph", test_memory_graph),
    ("Product search", test_product_search),
    ("Get product", test_get_product),
    ("Related products", test_related_products),
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke tests for the retail assistant backend")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help=f"Backend URL (default: {DEFAULT_BASE_URL})")
    args = parser.parse_args()

    tests = TESTS

    if not tests:
        print("No tests to run (both --skip-api and --skip-neo4j specified)")
        sys.exit(1)

    print(f"Testing backend at {args.base_url}\n")

    passed = 0
    failed = 0

    for name, fn in tests:
        print(f"[TEST] {name}")
        try:
            if fn(args.base_url):
                print(f"  PASS\n")
                passed += 1
            else:
                print(f"  FAIL\n")
                failed += 1
        except Exception as e:
            print(f"  ERROR: {e}\n")
            failed += 1

    print(f"Results: {passed} passed, {failed} failed out of {passed + failed}")
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
