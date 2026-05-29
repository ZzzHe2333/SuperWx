"""Module 13 test: MCP tools schema and server import check.

Usage:
    python tests/test_mcp_tools_module13.py
"""
import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_import():
    """Test MCP module imports."""
    try:
        from wxauto4_mcp.tools import TOOLS, handle_tool, configure
        from wxauto4_mcp.server import _handle_request
        print("[OK] MCP module imports successfully")
        return True
    except ImportError as e:
        print(f"[FAIL] Cannot import MCP module: {e}")
        return False


def test_tool_count():
    """Test that all expected tools are defined."""
    from wxauto4_mcp.tools import TOOLS

    expected = [
        "wechat_initialize", "wechat_status", "get_my_info", "get_sessions",
        "switch_chat", "send_message", "send_files", "get_messages",
        "get_next_new_message", "add_listen_chat", "remove_listen_chat",
        "start_listening", "stop_listening", "get_recent_groups", "doctor",
    ]
    names = {t["name"] for t in TOOLS}
    missing = [n for n in expected if n not in names]
    if missing:
        print(f"[FAIL] Missing tools: {missing}")
        return False
    print(f"[OK] All {len(expected)} tools defined")
    return True


def test_tool_schemas():
    """Test that all tools have valid JSON Schema."""
    from wxauto4_mcp.tools import TOOLS
    for tool in TOOLS:
        assert "name" in tool, f"Tool missing 'name'"
        assert "description" in tool, f"Tool {tool['name']} missing 'description'"
        assert "inputSchema" in tool, f"Tool {tool['name']} missing 'inputSchema'"
        schema = tool["inputSchema"]
        assert schema.get("type") == "object", f"Tool {tool['name']} inputSchema.type != object"
    print("[OK] All tool schemas valid")
    return True


def test_initialize_handler():
    """Test the initialize JSON-RPC handler."""
    from wxauto4_mcp.server import _handle_request
    msg = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
    resp = _handle_request(msg)
    assert resp["id"] == 1
    assert "result" in resp
    assert resp["result"]["serverInfo"]["name"] == "wxauto4-mcp"
    print("[OK] initialize handler works")
    return True


def test_tools_list_handler():
    """Test the tools/list JSON-RPC handler."""
    from wxauto4_mcp.server import _handle_request
    msg = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
    resp = _handle_request(msg)
    assert resp["id"] == 2
    tools = resp["result"]["tools"]
    assert len(tools) >= 15
    print(f"[OK] tools/list returns {len(tools)} tools")
    return True


def test_unknown_method():
    """Test unknown method returns error."""
    from wxauto4_mcp.server import _handle_request
    msg = {"jsonrpc": "2.0", "id": 3, "method": "unknown/method", "params": {}}
    resp = _handle_request(msg)
    assert "error" in resp
    print("[OK] Unknown method returns error")
    return True


def main():
    results = [
        test_import(),
        test_tool_count(),
        test_tool_schemas(),
        test_initialize_handler(),
        test_tools_list_handler(),
        test_unknown_method(),
    ]
    passed = sum(results)
    total = len(results)
    print(f"\nResults: {passed}/{total} passed")
    if passed < total:
        sys.exit(1)


if __name__ == "__main__":
    main()
