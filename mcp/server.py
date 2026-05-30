# -*- coding: utf-8 -*-
"""superwx4 MCP Server — stdio-based MCP server with cancellation and timeout.

Usage:
    python -m mcp.server
    python -m mcp.server --default-timeout 60
    python -m mcp.server --no-dry-run --log-level DEBUG

Claude Desktop config (claude_desktop_config.json):
{
  "mcpServers": {
    "superwx4": {
      "command": "python",
      "args": ["-m", "mcp.server"],
      "env": {}
    }
  }
}

Supports:
  - MCP protocol version 2024-11-05
  - notifications/cancelled for graceful interruption
  - Per-tool configurable timeouts
  - Dry-run by default for write operations
"""
from __future__ import annotations

import sys
import json
import argparse
import logging
import concurrent.futures
from typing import Any, Dict, Optional

from mcp.cancel import RequestTracker
from mcp.timeout import get_timeout, run_with_timeout, CancelledError
from mcp.tools import TOOLS, handle_tool, configure

log = logging.getLogger("mcp.server")


# ──────────────────────────────────────────────
# JSON-RPC I/O
# ──────────────────────────────────────────────

def _read_message() -> Optional[dict]:
    """Read a JSON-RPC message from stdin (one JSON object per line)."""
    line = sys.stdin.readline()
    if not line:
        return None
    try:
        return json.loads(line.strip())
    except json.JSONDecodeError:
        log.warning("Invalid JSON on stdin: %s", line[:200])
        return None


def _send_message(msg: dict):
    """Write a JSON-RPC message to stdout."""
    sys.stdout.write(json.dumps(msg, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def _error_response(msg_id: Any, code: int, message: str) -> dict:
    return {
        "jsonrpc": "2.0",
        "id": msg_id,
        "error": {"code": code, "message": message},
    }


def _result_response(msg_id: Any, result: Any) -> dict:
    return {
        "jsonrpc": "2.0",
        "id": msg_id,
        "result": result,
    }


# ──────────────────────────────────────────────
# Request handling
# ──────────────────────────────────────────────

# Global tracker for in-flight requests
_tracker = RequestTracker()

# Thread pool for running sync tool handlers
_pool = concurrent.futures.ThreadPoolExecutor(max_workers=4, thread_name_prefix="mcp-tool")


def _handle_initialize(msg: dict) -> dict:
    return _result_response(msg["id"], {
        "protocolVersion": "2024-11-05",
        "capabilities": {
            "tools": {},
            # Advertise cancellation support
            "experimental": {"cancellation": True},
        },
        "serverInfo": {
            "name": "superwx4-mcp",
            "version": "2.0.0",
        },
    })


def _handle_tools_list(msg: dict) -> dict:
    return _result_response(msg["id"], {"tools": TOOLS})


def _handle_tools_call(msg: dict, default_timeout: int) -> Optional[dict]:
    """Handle tools/call with timeout and cancellation."""
    params = msg.get("params", {})
    tool_name = params.get("name", "")
    arguments = params.get("arguments", {})
    msg_id = msg["id"]

    # Create cancel token for this request
    token = _tracker.create(str(msg_id))

    try:
        timeout = get_timeout(tool_name, default_timeout)
        log.debug("tools/call %s (timeout=%ds)", tool_name, timeout)

        result = run_with_timeout(
            fn=handle_tool,
            args=(tool_name, arguments, token),
            timeout=timeout,
            cancel_token=token,
        )

        is_error = not result.get("ok", False)
        content_text = json.dumps(result, ensure_ascii=False, indent=2)
        return _result_response(msg_id, {
            "content": [{"type": "text", "text": content_text}],
            "isError": is_error,
        })

    except TimeoutError as e:
        log.warning("Tool %s timed out: %s", tool_name, e)
        token.cancel()
        return _error_response(msg_id, -32800, f"Tool call timed out after {timeout}s: {tool_name}")

    except CancelledError as e:
        log.info("Tool %s cancelled: %s", tool_name, e)
        return _error_response(msg_id, -32800, f"Request cancelled: {tool_name}")

    except Exception as e:
        log.exception("Tool %s failed", tool_name)
        return _error_response(msg_id, -32603, f"Internal error: {e}")

    finally:
        _tracker.cleanup(str(msg_id))


def _handle_cancelled(msg: dict) -> None:
    """Handle notifications/cancelled from the client."""
    params = msg.get("params", {})
    request_id = str(params.get("requestId", ""))
    if _tracker.cancel(request_id):
        log.info("Cancelled request %s", request_id)
    else:
        log.debug("Cancel for unknown request %s (may have completed)", request_id)
    # Notifications don't get a response


def _dispatch(msg: dict, default_timeout: int) -> Optional[dict]:
    method = msg.get("method", "")

    if method == "initialize":
        return _handle_initialize(msg)

    elif method == "notifications/initialized":
        return None  # no response for notifications

    elif method == "notifications/cancelled":
        _handle_cancelled(msg)
        return None

    elif method == "tools/list":
        return _handle_tools_list(msg)

    elif method == "tools/call":
        return _handle_tools_call(msg, default_timeout)

    else:
        msg_id = msg.get("id")
        if msg_id is not None:
            return _error_response(msg_id, -32601, f"Method not found: {method}")
        return None


# ──────────────────────────────────────────────
# Main loop
# ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="superwx4 MCP server (stdio) with cancellation and timeout support",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m mcp.server
  python -m mcp.server --default-timeout 60
  python -m mcp.server --no-dry-run --log-level DEBUG

Claude Desktop config:
  {
    "mcpServers": {
      "superwx4": {
        "command": "python",
        "args": ["-m", "mcp.server"]
      }
    }
  }
""",
    )
    parser.add_argument("--default-timeout", type=int, default=30, help="Default timeout in seconds (default: 30)")
    parser.add_argument("--no-dry-run", action="store_true", help="Disable dry_run default for write tools")
    parser.add_argument("--log-level", default="WARNING", choices=["DEBUG", "INFO", "WARNING", "ERROR"], help="Log level")
    args = parser.parse_args()

    # Configure logging to stderr (stdout is reserved for MCP protocol)
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        stream=sys.stderr,
    )

    configure(dry_run_default=not args.no_dry_run)

    log.info("superwx4 MCP server starting (timeout=%ds, dry_run=%s)",
             args.default_timeout, not args.no_dry_run)

    try:
        while True:
            msg = _read_message()
            if msg is None:
                log.info("stdin closed, shutting down")
                break

            response = _dispatch(msg, args.default_timeout)
            if response is not None:
                _send_message(response)

    except KeyboardInterrupt:
        log.info("Interrupted, shutting down")
    finally:
        _tracker.cancel_all()
        _pool.shutdown(wait=False)


if __name__ == "__main__":
    main()
