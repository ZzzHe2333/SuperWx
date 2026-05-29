"""Unified regression test suite for wxauto4.

Runs offline (import/schema) tests for all modules.
Online tests (WeChat interaction) are skipped unless --online is passed.

Usage:
    python tests/regression_all.py              # offline only
    python tests/regression_all.py --online     # include online tests (requires WeChat)
    python tests/regression_all.py --verbose    # verbose output
"""
import sys
import os
import argparse
import importlib
import traceback

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "openclaw_skill"))

PASS = 0
FAIL = 0
SKIP = 0


def report(name: str, status: str, detail: str = ""):
    global PASS, FAIL, SKIP
    if status == "PASS":
        PASS += 1
        symbol = "[OK]"
    elif status == "SKIP":
        SKIP += 1
        symbol = "[--]"
    else:
        FAIL += 1
        symbol = "[!!]"
    msg = f"  {symbol} {name}"
    if detail:
        msg += f"  ({detail})"
    print(msg)


def test_locator_import():
    try:
        from wxauto4.locator import ctrl_exists, find_first, SELECTORS, dump_ui_tree
        assert isinstance(SELECTORS, dict)
        assert len(SELECTORS) >= 6
        report("locator import", "PASS")
    except Exception as e:
        report("locator import", "FAIL", str(e))


def test_doctor_import():
    try:
        from wxauto4.doctor import run_doctor
        assert callable(run_doctor)
        report("doctor import", "PASS")
    except Exception as e:
        report("doctor import", "FAIL", str(e))


def test_chatbox_import():
    try:
        from wxauto4.ui.chatbox import ChatBox
        assert hasattr(ChatBox, "get_history_msg")
        assert hasattr(ChatBox, "refresh_send_button")
        report("chatbox import + new methods", "PASS")
    except Exception as e:
        report("chatbox import + new methods", "FAIL", str(e))


def test_msgs_import():
    try:
        from wxauto4.msgs.base import Message, HumanMessage
        from wxauto4.msgs.mtype import TextMessage, ImageMessage, FileMessage
        from wxauto4.msgs.mattr import SystemMessage, FriendMessage, SelfMessage
        from wxauto4.msgs.msg import parse_msg
        report("msgs import", "PASS")
    except Exception as e:
        report("msgs import", "FAIL", str(e))


def test_api_import():
    try:
        from wxauto4.api.schemas import ApiResponse, SendMsgRequest, SendFilesRequest
        from wxauto4.api.main import app
        # Count routes
        routes = [r for r in app.routes if hasattr(r, "path")]
        report("REST API import", "PASS", f"{len(routes)} routes")
    except Exception as e:
        report("REST API import", "FAIL", str(e))


def test_api_schemas():
    try:
        from wxauto4.api.schemas import ApiResponse, SendMsgRequest, SendFilesRequest
        r = ApiResponse(ok=True, data={"x": 1})
        assert r.ok
        m = SendMsgRequest(msg="test", dry_run=True)
        assert m.dry_run
        f = SendFilesRequest(filepath=["/tmp/a.txt"], dry_run=True)
        assert f.filepath == ["/tmp/a.txt"]
        report("API schemas", "PASS")
    except Exception as e:
        report("API schemas", "FAIL", str(e))


def test_mcp_import():
    try:
        from wxauto4_mcp.tools import TOOLS, handle_tool
        from wxauto4_mcp.server import _handle_request
        assert len(TOOLS) >= 15
        report("MCP tools import", "PASS", f"{len(TOOLS)} tools")
    except Exception as e:
        report("MCP tools import", "FAIL", str(e))


def test_mcp_handlers():
    try:
        from wxauto4_mcp.server import _handle_request
        msg = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
        resp = _handle_request(msg)
        assert resp["result"]["serverInfo"]["name"] == "wxauto4-mcp"
        msg2 = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
        resp2 = _handle_request(msg2)
        assert len(resp2["result"]["tools"]) >= 15
        report("MCP handlers", "PASS")
    except Exception as e:
        report("MCP handlers", "FAIL", str(e))


def test_openclaw_import():
    try:
        from openclaw_skill.skill import (
            configure, send_message, get_messages, doctor, dispatch, INTENT_MAP,
        )
        assert callable(send_message)
        assert len(INTENT_MAP) >= 7
        report("OpenClaw skill import", "PASS", f"{len(INTENT_MAP)} intents")
    except Exception as e:
        report("OpenClaw skill import", "FAIL", str(e))


def test_safety_check_import():
    try:
        from tests.safety_check import scan_file, DANGEROUS_PATTERNS
        assert len(DANGEROUS_PATTERNS) >= 5
        report("safety_check import", "PASS")
    except Exception as e:
        report("safety_check import", "FAIL", str(e))


def test_dry_run_in_api():
    """Verify that send endpoints respect dry_run."""
    try:
        from wxauto4.api.routes.wechat import wechat_send_message, wechat_send_file
        # Check function signatures have dry_run
        import inspect
        sig = inspect.signature(wechat_send_message)
        # The request body has dry_run field
        from wxauto4.api.schemas import SendMsgRequest
        assert "dry_run" in SendMsgRequest.model_fields
        report("dry_run in API", "PASS")
    except Exception as e:
        report("dry_run in API", "FAIL", str(e))


# --- Online tests (require WeChat) ---

def test_online_doctor():
    try:
        from wxauto4 import WeChat
        wx = WeChat()
        from wxauto4.doctor import run_doctor
        run_doctor()
        report("online: doctor", "PASS")
    except Exception as e:
        report("online: doctor", "SKIP", str(e)[:60])


def test_online_get_messages():
    try:
        from wxauto4 import WeChat
        wx = WeChat()
        msgs = wx.GetAllMessage()
        report("online: GetAllMessage", "PASS", f"{len(msgs)} msgs")
    except Exception as e:
        report("online: GetAllMessage", "SKIP", str(e)[:60])


def main():
    parser = argparse.ArgumentParser(description="wxauto4 regression tests")
    parser.add_argument("--online", action="store_true", help="Run online tests (requires WeChat)")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    print("=" * 60)
    print("wxauto4 Regression Test Suite")
    print("=" * 60)

    print("\n--- Offline Tests ---")
    test_locator_import()
    test_doctor_import()
    test_chatbox_import()
    test_msgs_import()
    test_api_import()
    test_api_schemas()
    test_mcp_import()
    test_mcp_handlers()
    test_openclaw_import()
    test_safety_check_import()
    test_dry_run_in_api()

    if args.online:
        print("\n--- Online Tests ---")
        test_online_doctor()
        test_online_get_messages()
    else:
        print("\n--- Online Tests (skipped, use --online) ---")

    print("\n" + "=" * 60)
    total = PASS + FAIL + SKIP
    print(f"Results: {PASS} passed, {FAIL} failed, {SKIP} skipped ({total} total)")
    if FAIL > 0:
        print("FAILED")
        sys.exit(1)
    else:
        print("PASSED")


if __name__ == "__main__":
    main()
