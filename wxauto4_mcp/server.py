"""wxauto4 MCP Server — stdio-based MCP server for Claude Desktop / Claude Code.

Usage:
    python -m wxauto4_mcp.server
    python -m wxauto4_mcp.server --api-url http://127.0.0.1:8760

For Claude Desktop config (claude_desktop_config.json):
{
  "mcpServers": {
    "wxauto4": {
      "command": "python",
      "args": ["-m", "wxauto4_mcp.server"],
      "env": {}
    }
  }
}
"""
from __future__ import annotations
import sys
import json
import argparse
from wxauto4_mcp.tools import TOOLS, handle_tool, configure


def _read_message() -> dict | None:
    """Read a JSON-RPC message from stdin."""
    line = sys.stdin.readline()
    if not line:
        return None
    try:
        return json.loads(line.strip())
    except json.JSONDecodeError:
        return None


def _send_message(msg: dict):
    """Write a JSON-RPC message to stdout."""
    sys.stdout.write(json.dumps(msg) + "\n")
    sys.stdout.flush()


def _handle_request(msg: dict) -> dict:
    method = msg.get("method", "")
    params = msg.get("params", {})
    msg_id = msg.get("id")

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "wxauto4-mcp", "version": "1.0.0"},
            },
        }
    elif method == "notifications/initialized":
        return None  # notification, no response
    elif method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {"tools": TOOLS},
        }
    elif method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})
        result = handle_tool(tool_name, arguments)
        # Format as MCP tool result
        is_error = not result.get("ok", False)
        content_text = json.dumps(result, ensure_ascii=False, indent=2)
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "content": [{"type": "text", "text": content_text}],
                "isError": is_error,
            },
        }
    else:
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "error": {"code": -32601, "message": f"Method not found: {method}"},
        }


def main():
    parser = argparse.ArgumentParser(description="wxauto4 MCP server (stdio)")
    parser.add_argument("--api-url", default="http://127.0.0.1:8760", help="wxauto4 REST API URL")
    parser.add_argument("--api-token", default=None, help="API token")
    parser.add_argument("--no-dry-run", action="store_true", help="Disable dry_run default")
    args = parser.parse_args()

    configure(
        base_url=args.api_url,
        api_token=args.api_token,
        dry_run_default=not args.no_dry_run,
    )

    # MCP stdio loop
    while True:
        msg = _read_message()
        if msg is None:
            break
        response = _handle_request(msg)
        if response is not None:
            _send_message(response)


if __name__ == "__main__":
    main()
