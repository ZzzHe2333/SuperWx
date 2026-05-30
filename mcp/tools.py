# -*- coding: utf-8 -*-
"""MCP tool definitions and handler dispatch for superwx4.

Each tool directly calls the superwx4 Python API (no REST proxy).
Write tools default to dry_run=True for safety.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from mcp.cancel import CancelToken

log = logging.getLogger("mcp.tools")

# Global WeChat instance (lazy init)
_wx = None
_dry_run_default: bool = True


def configure(dry_run_default: bool = True):
    global _dry_run_default
    _dry_run_default = dry_run_default


def _get_wx():
    global _wx
    if _wx is None:
        raise RuntimeError("WeChat not initialized. Call wechat_init first.")
    return _wx


def _ok(data=None) -> dict:
    return {"ok": True, "data": data, "error": None}


def _err(msg: str) -> dict:
    return {"ok": False, "data": None, "error": msg}


# ──────────────────────────────────────────────
# Tool schema definitions (MCP tools/list format)
# ──────────────────────────────────────────────

TOOLS: List[Dict[str, Any]] = [
    {
        "name": "wechat_init",
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
        "name": "get_new_messages",
        "description": "Get new messages since last check.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_history_message",
        "description": "Scroll up and collect historical messages from current chat.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "n": {"type": "integer", "default": 50, "description": "Number of messages to collect"},
            },
        },
    },
    {
        "name": "get_friend_list",
        "description": "Get contact/friend list.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "max_scroll": {"type": "integer", "default": 50, "description": "Max scroll iterations"},
            },
        },
    },
    {
        "name": "get_friend_details",
        "description": "Get detailed info for N friends.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "n": {"type": "integer", "description": "Number of friends to inspect"},
            },
        },
    },
    {
        "name": "get_recent_groups",
        "description": "Get list of recent group chats.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "is_online",
        "description": "Check if WeChat is online.",
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
]


# ──────────────────────────────────────────────
# Handler dispatch
# ──────────────────────────────────────────────

def handle_tool(name: str, arguments: dict, cancel_token: CancelToken = None) -> dict:
    """Dispatch a tool call. Returns a dict with ok/data/error."""
    try:
        handler = _HANDLERS.get(name)
        if handler is None:
            return _err(f"Unknown tool: {name}")
        return handler(arguments, cancel_token)
    except Exception as e:
        log.exception("Tool %s raised: %s", name, e)
        return _err(str(e))


def _check_cancel(token: Optional[CancelToken]):
    if token and token.is_cancelled():
        raise _Cancelled(f"Request {token.request_id} was cancelled")


class _Cancelled(Exception):
    pass


# ──────────────────────────────────────────────
# Individual tool handlers
# ──────────────────────────────────────────────

def _handle_wechat_init(args: dict, token: CancelToken) -> dict:
    global _wx
    from superwx4 import WeChat
    _check_cancel(token)
    _wx = WeChat(
        nickname=args.get("nickname"),
        debug=args.get("debug", False),
    )
    return _ok({"nickname": _wx.nickname})


def _handle_wechat_status(args: dict, token: CancelToken) -> dict:
    try:
        wx = _get_wx()
        return _ok({"nickname": wx.nickname, "initialized": True})
    except RuntimeError:
        return _ok({"initialized": False})


def _handle_get_my_info(args: dict, token: CancelToken) -> dict:
    _check_cancel(token)
    wx = _get_wx()
    return _ok(wx.GetMyInfo())


def _handle_get_sessions(args: dict, token: CancelToken) -> dict:
    _check_cancel(token)
    wx = _get_wx()
    sessions = wx.GetSession()
    data = [{"name": s.Name, "type": s.ControlTypeName} for s in sessions] if sessions else []
    return _ok(data)


def _handle_switch_chat(args: dict, token: CancelToken) -> dict:
    _check_cancel(token)
    wx = _get_wx()
    result = wx.ChatWith(args["who"], exact=args.get("exact", True))
    return _ok({"result": str(result)})


def _handle_send_message(args: dict, token: CancelToken) -> dict:
    dry = args.get("dry_run", _dry_run_default)
    if dry:
        return _ok({"dry_run": True, "msg": args["msg"], "who": args.get("who"), "at": args.get("at")})
    _check_cancel(token)
    wx = _get_wx()
    result = wx.SendMsg(args["msg"], who=args.get("who"), at=args.get("at"))
    return _ok({"result": str(result)})


def _handle_send_files(args: dict, token: CancelToken) -> dict:
    import os
    paths = args["filepath"]
    if isinstance(paths, str):
        paths = [paths]
    for p in paths:
        if not os.path.isabs(p):
            return _err(f"File path must be absolute: {p}")
        if not os.path.exists(p):
            return _err(f"File not found: {p}")
    dry = args.get("dry_run", _dry_run_default)
    if dry:
        return _ok({"dry_run": True, "filepath": paths, "who": args.get("who")})
    _check_cancel(token)
    wx = _get_wx()
    result = wx.SendFiles(paths, who=args.get("who"))
    return _ok({"result": str(result)})


def _handle_get_messages(args: dict, token: CancelToken) -> dict:
    _check_cancel(token)
    wx = _get_wx()
    msgs = wx.GetAllMessage()
    data = [m.to_dict() for m in msgs] if msgs else []
    return _ok(data)


def _handle_get_new_messages(args: dict, token: CancelToken) -> dict:
    _check_cancel(token)
    wx = _get_wx()
    msgs = wx.GetNewMessage()
    data = [m.to_dict() for m in msgs] if msgs else []
    return _ok(data)


def _handle_get_history_message(args: dict, token: CancelToken) -> dict:
    _check_cancel(token)
    wx = _get_wx()
    n = args.get("n", 50)
    msgs = wx.GetHistoryMessage(n=n)
    data = [m.to_dict() for m in msgs] if msgs else []
    return _ok(data)


def _handle_get_friend_list(args: dict, token: CancelToken) -> dict:
    _check_cancel(token)
    wx = _get_wx()
    result = wx.GetFriendList(max_scroll=args.get("max_scroll", 50))
    return _ok(result if isinstance(result, dict) else {"result": str(result)})


def _handle_get_friend_details(args: dict, token: CancelToken) -> dict:
    _check_cancel(token)
    wx = _get_wx()
    result = wx.GetFriendDetails(n=args.get("n"))
    return _ok(result if isinstance(result, dict) else {"result": str(result)})


def _handle_get_recent_groups(args: dict, token: CancelToken) -> dict:
    _check_cancel(token)
    wx = _get_wx()
    groups = wx.GetAllRecentGroups()
    return _ok(groups)


def _handle_is_online(args: dict, token: CancelToken) -> dict:
    _check_cancel(token)
    wx = _get_wx()
    return _ok({"online": wx.IsOnline()})


def _handle_doctor(args: dict, token: CancelToken) -> dict:
    _check_cancel(token)
    import io, sys
    from superwx4.doctor import run_doctor
    buf = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = buf
    try:
        run_doctor(report_path=None, dump_on_fail=args.get("dump_on_fail", False))
    finally:
        sys.stdout = old_stdout
    return _ok({"output": buf.getvalue()})


def _handle_add_listen_chat(args: dict, token: CancelToken) -> dict:
    _check_cancel(token)
    wx = _get_wx()
    def _cb(msg, chat):
        pass
    result = wx.AddListenChat(args["who"], _cb)
    return _ok({"result": str(result)})


def _handle_remove_listen_chat(args: dict, token: CancelToken) -> dict:
    _check_cancel(token)
    wx = _get_wx()
    result = wx.RemoveListenChat(args["who"])
    return _ok({"result": str(result)})


def _handle_start_listening(args: dict, token: CancelToken) -> dict:
    _check_cancel(token)
    wx = _get_wx()
    wx.StartListening()
    return _ok({"listening": True})


def _handle_stop_listening(args: dict, token: CancelToken) -> dict:
    _check_cancel(token)
    wx = _get_wx()
    wx.StopListening(remove=False)
    return _ok({"listening": False})


# Handler registry
_HANDLERS = {
    "wechat_init": _handle_wechat_init,
    "wechat_status": _handle_wechat_status,
    "get_my_info": _handle_get_my_info,
    "get_sessions": _handle_get_sessions,
    "switch_chat": _handle_switch_chat,
    "send_message": _handle_send_message,
    "send_files": _handle_send_files,
    "get_messages": _handle_get_messages,
    "get_new_messages": _handle_get_new_messages,
    "get_history_message": _handle_get_history_message,
    "get_friend_list": _handle_get_friend_list,
    "get_friend_details": _handle_get_friend_details,
    "get_recent_groups": _handle_get_recent_groups,
    "is_online": _handle_is_online,
    "doctor": _handle_doctor,
    "add_listen_chat": _handle_add_listen_chat,
    "remove_listen_chat": _handle_remove_listen_chat,
    "start_listening": _handle_start_listening,
    "stop_listening": _handle_stop_listening,
}
