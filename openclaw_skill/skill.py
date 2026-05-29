"""wxauto4 OpenClaw / Hermes-Agent skill.

Wraps the wxauto4 REST API into callable skill functions.
Each function returns a dict with {ok, data, error}.
"""
from __future__ import annotations
import json
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional, Union

DEFAULT_BASE_URL = "http://127.0.0.1:8760"
_base_url: str = DEFAULT_BASE_URL
_api_token: Optional[str] = None
_dry_run_default: bool = True


def configure(base_url: str = DEFAULT_BASE_URL, api_token: str = None, dry_run_default: bool = True):
    """Configure the skill's connection to the wxauto4 REST API."""
    global _base_url, _api_token, _dry_run_default
    _base_url = base_url.rstrip("/")
    _api_token = api_token
    _dry_run_default = dry_run_default


def _api(method: str, path: str, body: dict = None) -> dict:
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


# --- Skill functions ---

def initialize(nickname: str = None, debug: bool = False) -> dict:
    """Initialize WeChat connection."""
    return _api("POST", "/wechat/init", {"nickname": nickname, "debug": debug})


def status() -> dict:
    """Check WeChat connection status."""
    return _api("GET", "/wechat/status")


def get_my_info() -> dict:
    """Get current WeChat user info."""
    return _api("GET", "/wechat/me")


def get_sessions() -> dict:
    """Get list of recent chat sessions."""
    return _api("GET", "/wechat/sessions")


def switch_chat(who: str, exact: bool = True) -> dict:
    """Switch to a chat window."""
    return _api("POST", "/wechat/chat/switch", {"who": who, "exact": exact})


def send_message(msg: str, who: str = None, at: str = None, dry_run: bool = None) -> dict:
    """Send a text message.

    Args:
        msg: Message text
        who: Recipient (optional, uses current chat)
        at: @ someone (optional)
        dry_run: If True, don't actually send. Defaults to skill config.
    """
    if dry_run is None:
        dry_run = _dry_run_default
    return _api("POST", "/wechat/message/send", {
        "msg": msg, "who": who, "at": at, "dry_run": dry_run,
    })


def send_files(filepath: Union[str, List[str]], who: str = None, dry_run: bool = None) -> dict:
    """Send file(s) to a chat.

    Args:
        filepath: Absolute path(s) to files
        who: Recipient (optional)
        dry_run: If True, don't actually send.
    """
    if dry_run is None:
        dry_run = _dry_run_default
    return _api("POST", "/wechat/file/send", {
        "filepath": filepath, "who": who, "dry_run": dry_run,
    })


def get_messages() -> dict:
    """Get all visible messages in current chat."""
    return _api("GET", "/wechat/messages/current")


def get_new_messages() -> dict:
    """Get new messages since last check."""
    return _api("GET", "/wechat/messages/new")


def add_listen(who: str) -> dict:
    """Add a chat to the listener."""
    return _api("POST", "/wechat/listen/add", {"who": who})


def remove_listen(who: str) -> dict:
    """Remove a chat from the listener."""
    return _api("POST", "/wechat/listen/remove", {"who": who})


def start_listening() -> dict:
    """Start the message listener."""
    return _api("POST", "/wechat/listen/start")


def stop_listening() -> dict:
    """Stop the message listener."""
    return _api("POST", "/wechat/listen/stop")


def doctor(dump_on_fail: bool = False) -> dict:
    """Run diagnostic checks on WeChat UI controls."""
    return _api("POST", "/wechat/doctor", {"dump_on_fail": dump_on_fail})


# --- Natural language intent dispatch ---

INTENT_MAP = {
    "发微信": "send_message",
    "发送消息": "send_message",
    "发消息": "send_message",
    "查看消息": "get_messages",
    "当前消息": "get_messages",
    "新消息": "get_new_messages",
    "会话列表": "get_sessions",
    "切换聊天": "switch_chat",
    "发送文件": "send_files",
    "发文件": "send_files",
    "监听": "add_listen",
    "停止监听": "stop_listening",
    "检查状态": "doctor",
    "doctor": "doctor",
    "初始化": "initialize",
}


def dispatch(intent: str, **kwargs) -> dict:
    """Dispatch a natural-language intent to the corresponding skill function."""
    func_name = INTENT_MAP.get(intent)
    if func_name is None:
        return {"ok": False, "data": None, "error": f"Unknown intent: {intent}"}
    import sys
    mod = sys.modules[__name__]
    func = getattr(mod, func_name, None)
    if func is None:
        return {"ok": False, "data": None, "error": f"Function not found: {func_name}"}
    return func(**kwargs)
