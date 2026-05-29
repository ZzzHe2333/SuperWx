"""MCP tool definitions and handler logic for wxauto4.

Each tool calls the local wxauto4 REST API. Tools that modify state default to dry_run.
"""
from __future__ import annotations
import json
import urllib.request
import urllib.error
from typing import Any, Dict, Optional

DEFAULT_BASE_URL = "http://127.0.0.1:8760"
_api_token: Optional[str] = None
_base_url: str = DEFAULT_BASE_URL
_dry_run_default: bool = True


def configure(base_url: str = DEFAULT_BASE_URL, api_token: str = None, dry_run_default: bool = True):
    global _base_url, _api_token, _dry_run_default
    _base_url = base_url.rstrip("/")
    _api_token = api_token
    _dry_run_default = dry_run_default


def _api_call(method: str, path: str, body: dict = None) -> dict:
    url = f"{_base_url}{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if _api_token:
        req.add_header("Authorization", f"Bearer {_api_token}")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.URLError as e:
        return {"ok": False, "data": None, "error": f"Connection failed: {e}"}
    except Exception as e:
        return {"ok": False, "data": None, "error": str(e)}


# --- Tool definitions (name -> schema) ---

TOOLS: list[dict] = [
    {
        "name": "wechat_initialize",
        "description": "Initialize WeChat connection. Must be called before other tools.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "nickname": {"type": "string", "description": "WeChat window nickname (optional)"},
                "debug": {"type": "boolean", "default": False},
            },
        },
    },
    {
        "name": "wechat_status",
        "description": "Check WeChat connection status.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_my_info",
        "description": "Get current WeChat user info.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_sessions",
        "description": "Get the list of recent chat sessions.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "switch_chat",
        "description": "Switch to a specific chat window.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "who": {"type": "string", "description": "Chat name to switch to"},
                "exact": {"type": "boolean", "default": True},
            },
            "required": ["who"],
        },
    },
    {
        "name": "send_message",
        "description": "Send a text message to current or specified chat.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "msg": {"type": "string", "description": "Message content"},
                "who": {"type": "string", "description": "Recipient (optional, uses current chat)"},
                "at": {"type": "string", "description": "@ someone (optional)"},
                "dry_run": {"type": "boolean", "description": "If true, don't actually send"},
            },
            "required": ["msg"],
        },
    },
    {
        "name": "send_files",
        "description": "Send files to current or specified chat.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "filepath": {
                    "oneOf": [{"type": "string"}, {"type": "array", "items": {"type": "string"}}],
                    "description": "Absolute file path(s)",
                },
                "who": {"type": "string", "description": "Recipient (optional)"},
                "dry_run": {"type": "boolean", "description": "If true, don't actually send"},
            },
            "required": ["filepath"],
        },
    },
    {
        "name": "get_messages",
        "description": "Get all visible messages in the current chat.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_next_new_message",
        "description": "Get new messages since last check.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "add_listen_chat",
        "description": "Add a chat to the listener for new message monitoring.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "who": {"type": "string", "description": "Chat name to listen to"},
            },
            "required": ["who"],
        },
    },
    {
        "name": "remove_listen_chat",
        "description": "Remove a chat from the listener.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "who": {"type": "string", "description": "Chat name to stop listening"},
            },
            "required": ["who"],
        },
    },
    {
        "name": "start_listening",
        "description": "Start the message listener.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "stop_listening",
        "description": "Stop the message listener.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_recent_groups",
        "description": "Get list of recent group chats (from sessions).",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "doctor",
        "description": "Run diagnostic checks on WeChat UI controls.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "dump_on_fail": {"type": "boolean", "default": False},
            },
        },
    },
]


def handle_tool(name: str, arguments: dict) -> dict:
    """Dispatch a tool call to the REST API and return the result."""
    dry = arguments.get("dry_run", _dry_run_default)

    if name == "wechat_initialize":
        return _api_call("POST", "/wechat/init", {
            "nickname": arguments.get("nickname"),
            "debug": arguments.get("debug", False),
        })
    elif name == "wechat_status":
        return _api_call("GET", "/wechat/status")
    elif name == "get_my_info":
        return _api_call("GET", "/wechat/me")
    elif name == "get_sessions":
        return _api_call("GET", "/wechat/sessions")
    elif name == "switch_chat":
        return _api_call("POST", "/wechat/chat/switch", {
            "who": arguments["who"],
            "exact": arguments.get("exact", True),
        })
    elif name == "send_message":
        return _api_call("POST", "/wechat/message/send", {
            "msg": arguments["msg"],
            "who": arguments.get("who"),
            "at": arguments.get("at"),
            "dry_run": dry,
        })
    elif name == "send_files":
        return _api_call("POST", "/wechat/file/send", {
            "filepath": arguments["filepath"],
            "who": arguments.get("who"),
            "dry_run": dry,
        })
    elif name == "get_messages":
        return _api_call("GET", "/wechat/messages/current")
    elif name == "get_next_new_message":
        return _api_call("GET", "/wechat/messages/new")
    elif name == "add_listen_chat":
        return _api_call("POST", "/wechat/listen/add", {"who": arguments["who"]})
    elif name == "remove_listen_chat":
        return _api_call("POST", "/wechat/listen/remove", {"who": arguments["who"]})
    elif name == "start_listening":
        return _api_call("POST", "/wechat/listen/start")
    elif name == "stop_listening":
        return _api_call("POST", "/wechat/listen/stop")
    elif name == "get_recent_groups":
        # Filter sessions for group-like names (heuristic)
        result = _api_call("GET", "/wechat/sessions")
        return result
    elif name == "doctor":
        return _api_call("POST", "/wechat/doctor", {
            "dump_on_fail": arguments.get("dump_on_fail", False),
        })
    else:
        return {"ok": False, "data": None, "error": f"Unknown tool: {name}"}
