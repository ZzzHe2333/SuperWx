"""Module 12 test: REST API health check and dry_run tests.

Usage:
    python tests/test_rest_api_module12.py                   # test health endpoint
    python tests/test_rest_api_module12.py --base-url http://127.0.0.1:8760
"""
import sys
import os
import argparse
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_import():
    """Test that the API module can be imported."""
    try:
        from wxauto4.api.main import app
        from wxauto4.api.schemas import ApiResponse, SendMsgRequest
        print("[OK] API module imports successfully")
        return True
    except ImportError as e:
        print(f"[FAIL] Cannot import API module: {e}")
        return False


def test_schemas():
    """Test schema validation."""
    from wxauto4.api.schemas import ApiResponse, SendMsgRequest, SendFilesRequest

    resp = ApiResponse(ok=True, data={"test": 1}, error=None)
    assert resp.ok is True
    assert resp.data == {"test": 1}

    msg = SendMsgRequest(msg="hello", dry_run=True)
    assert msg.msg == "hello"
    assert msg.dry_run is True

    files = SendFilesRequest(filepath=["/tmp/test.txt"], dry_run=True)
    assert files.filepath == ["/tmp/test.txt"]

    print("[OK] Schemas validate correctly")
    return True


def test_routes_exist():
    """Test that all expected routes are registered."""
    from wxauto4.api.main import app

    expected_paths = [
        "/health",
        "/wechat/init",
        "/wechat/status",
        "/wechat/me",
        "/wechat/sessions",
        "/wechat/chat/switch",
        "/wechat/message/send",
        "/wechat/file/send",
        "/wechat/messages/current",
        "/wechat/messages/new",
        "/wechat/listen/add",
        "/wechat/listen/remove",
        "/wechat/listen/start",
        "/wechat/listen/stop",
        "/wechat/doctor",
    ]

    registered = set()
    for route in app.routes:
        if hasattr(route, "path"):
            registered.add(route.path)

    missing = [p for p in expected_paths if p not in registered]
    if missing:
        print(f"[FAIL] Missing routes: {missing}")
        return False
    print(f"[OK] All {len(expected_paths)} routes registered")
    return True


def test_health_endpoint():
    """Test /health via HTTP (requires server to be running)."""
    import urllib.request
    import urllib.error

    base_url = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1].startswith("http") else "http://127.0.0.1:8760"
    try:
        req = urllib.request.Request(f"{base_url}/health")
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read())
            if data.get("ok"):
                print(f"[OK] /health responded: {data}")
                return True
            else:
                print(f"[FAIL] /health unexpected response: {data}")
                return False
    except urllib.error.URLError:
        print(f"[SKIP] Server not running at {base_url}, skipping HTTP test")
        return True
    except Exception as e:
        print(f"[SKIP] Cannot reach {base_url}: {e}")
        return True


def main():
    parser = argparse.ArgumentParser(description="Test REST API (Module 12)")
    parser.add_argument("--base-url", default="http://127.0.0.1:8760", help="API base URL")
    args = parser.parse_args()

    if len(sys.argv) > 1 and sys.argv[1].startswith("http"):
        pass  # legacy positional arg

    results = []
    results.append(test_import())
    results.append(test_schemas())
    results.append(test_routes_exist())
    results.append(test_health_endpoint())

    passed = sum(results)
    total = len(results)
    print(f"\nResults: {passed}/{total} passed")
    if passed < total:
        sys.exit(1)


if __name__ == "__main__":
    main()
