# -*- coding: utf-8 -*-
"""superwx4 OpenClaw / Hermes-Agent skill.

Wraps the superwx4 API into callable skill functions for agent orchestration.
Supports direct superwx4 integration (no REST proxy required).

Each function returns a dict with {ok, data, error}.

Usage:
    from openclaw_skill.skill import initialize, send_message, get_messages

    initialize()
    send_message("你好", who="文件传输助手")

    # Or via intent dispatch:
    from openclaw_skill.skill import dispatch
    dispatch("发消息", msg="你好", who="文件传输助手")
"""
from __future__ import annotations

import os
import logging
from typing import Any, Dict, List, Union

log = logging.getLogger("openclaw_skill")

# ──────────────────────────────────────────────
# Global state
# ──────────────────────────────────────────────

_wx = None
_dry_run_default: bool = True
_initialized: bool = False


def configure(dry_run_default: bool = True):
    """Configure skill defaults."""
    global _dry_run_default
    _dry_run_default = dry_run_default


def _get_wx():
    """Get the WeChat instance, raise if not initialized."""
    if _wx is None:
        raise RuntimeError("WeChat not initialized. Call initialize() first.")
    return _wx


def _ok(data=None) -> dict:
    return {"ok": True, "data": data, "error": None}


def _err(msg: str) -> dict:
    return {"ok": False, "data": None, "error": msg}


# ──────────────────────────────────────────────
# Connection
# ──────────────────────────────────────────────

def initialize(nickname: str = None, debug: bool = False) -> dict:
    """Initialize WeChat connection.

    Args:
        nickname: WeChat window title/nickname (optional, auto-detect)
        debug: Enable debug logging

    Returns:
        {ok, data: {nickname}, error}
    """
    global _wx, _initialized
    try:
        from superwx4 import WeChat
        _wx = WeChat(nickname=nickname, debug=debug)
        _initialized = True
        log.info("WeChat initialized: %s", _wx.nickname)
        return _ok({"nickname": _wx.nickname})
    except Exception as e:
        log.exception("Initialize failed")
        _initialized = False
        return _err(str(e))


def status() -> dict:
    """Check WeChat connection status.

    Returns:
        {ok, data: {initialized, nickname}, error}
    """
    if _wx is None:
        return _ok({"initialized": False, "nickname": None})
    return _ok({"initialized": True, "nickname": _wx.nickname})


def is_online() -> dict:
    """Check if WeChat is online.

    Returns:
        {ok, data: {online}, error}
    """
    try:
        wx = _get_wx()
        return _ok({"online": wx.IsOnline()})
    except Exception as e:
        return _err(str(e))


# ──────────────────────────────────────────────
# User info
# ──────────────────────────────────────────────

def get_my_info() -> dict:
    """Get current WeChat user info.

    Returns:
        {ok, data: {nickname, ...}, error}
    """
    try:
        wx = _get_wx()
        return _ok(wx.GetMyInfo())
    except Exception as e:
        return _err(str(e))


# ──────────────────────────────────────────────
# Sessions & navigation
# ──────────────────────────────────────────────

def get_sessions() -> dict:
    """Get list of recent chat sessions.

    Returns:
        {ok, data: [{name, type}, ...], error}
    """
    try:
        wx = _get_wx()
        sessions = wx.GetSession()
        data = [{"name": s.Name, "type": s.ControlTypeName} for s in sessions] if sessions else []
        return _ok(data)
    except Exception as e:
        return _err(str(e))


def get_recent_groups() -> dict:
    """Get list of recent group chats.

    Returns:
        {ok, data: [group_name, ...], error}
    """
    try:
        wx = _get_wx()
        groups = wx.GetAllRecentGroups()
        return _ok(groups)
    except Exception as e:
        return _err(str(e))


def switch_chat(who: str, exact: bool = True) -> dict:
    """Switch to a chat window.

    Args:
        who: Chat name to switch to
        exact: Exact match (default True)

    Returns:
        {ok, data: {result}, error}
    """
    try:
        wx = _get_wx()
        result = wx.ChatWith(who, exact=exact)
        return _ok({"result": str(result)})
    except Exception as e:
        return _err(str(e))


# ──────────────────────────────────────────────
# Messages
# ──────────────────────────────────────────────

def get_messages() -> dict:
    """Get all visible messages in current chat.

    Returns:
        {ok, data: [{type, content, sender, ...}, ...], error}
    """
    try:
        wx = _get_wx()
        msgs = wx.GetAllMessage()
        data = [m.to_dict() for m in msgs] if msgs else []
        return _ok(data)
    except Exception as e:
        return _err(str(e))


def get_new_messages() -> dict:
    """Get new messages since last check.

    Returns:
        {ok, data: [{type, content, sender, ...}, ...], error}
    """
    try:
        wx = _get_wx()
        msgs = wx.GetNewMessage()
        data = [m.to_dict() for m in msgs] if msgs else []
        return _ok(data)
    except Exception as e:
        return _err(str(e))


def get_last_message() -> dict:
    """Get the last message in current chat.

    Returns:
        {ok, data: {type, content, sender, ...}, error}
    """
    try:
        wx = _get_wx()
        msg = wx.GetLastMessage()
        return _ok(msg.to_dict() if msg else None)
    except Exception as e:
        return _err(str(e))


def get_history_message(n: int = 50) -> dict:
    """Scroll up and collect historical messages.

    Args:
        n: Number of messages to collect (default 50)

    Returns:
        {ok, data: [{type, content, sender, ...}, ...], error}
    """
    try:
        wx = _get_wx()
        msgs = wx.GetHistoryMessage(n=n)
        data = [m.to_dict() for m in msgs] if msgs else []
        return _ok(data)
    except Exception as e:
        return _err(str(e))


# ──────────────────────────────────────────────
# Send
# ──────────────────────────────────────────────

def send_message(msg: str, who: str = None, at: str = None, dry_run: bool = None) -> dict:
    """Send a text message.

    Args:
        msg: Message text
        who: Recipient (optional, uses current chat)
        at: @ someone (optional)
        dry_run: If True, don't actually send. Defaults to skill config.

    Returns:
        {ok, data: {dry_run, msg, who} or {result}, error}
    """
    if dry_run is None:
        dry_run = _dry_run_default
    if dry_run:
        return _ok({"dry_run": True, "msg": msg, "who": who, "at": at})
    try:
        wx = _get_wx()
        result = wx.SendMsg(msg, who=who, at=at)
        return _ok({"result": str(result)})
    except Exception as e:
        return _err(str(e))


def send_files(filepath: Union[str, List[str]], who: str = None, dry_run: bool = None) -> dict:
    """Send file(s) to a chat.

    Args:
        filepath: Absolute path(s) to files
        who: Recipient (optional)
        dry_run: If True, don't actually send.

    Returns:
        {ok, data: {dry_run, filepath} or {result}, error}
    """
    if dry_run is None:
        dry_run = _dry_run_default
    paths = [filepath] if isinstance(filepath, str) else filepath
    # Validate paths
    for p in paths:
        if not os.path.isabs(p):
            return _err(f"File path must be absolute: {p}")
        if not os.path.exists(p):
            return _err(f"File not found: {p}")
    if dry_run:
        return _ok({"dry_run": True, "filepath": paths, "who": who})
    try:
        wx = _get_wx()
        result = wx.SendFiles(paths, who=who)
        return _ok({"result": str(result)})
    except Exception as e:
        return _err(str(e))


def send_audio(filepath: str, duration: float = None, who: str = None, dry_run: bool = None) -> dict:
    """Send a voice message.

    Args:
        filepath: Absolute path to audio file
        duration: Audio duration in seconds (optional, auto-detected)
        who: Recipient (optional)
        dry_run: If True, don't actually send.
    """
    if dry_run is None:
        dry_run = _dry_run_default
    if not os.path.isabs(filepath):
        return _err(f"File path must be absolute: {filepath}")
    if not os.path.exists(filepath):
        return _err(f"File not found: {filepath}")
    if dry_run:
        return _ok({"dry_run": True, "filepath": filepath, "who": who, "duration": duration})
    try:
        wx = _get_wx()
        result = wx.SendAudio(filepath, duration=duration, who=who)
        return _ok({"result": str(result)})
    except Exception as e:
        return _err(str(e))


def send_url_card(url: str, who: str = None, message: str = None, dry_run: bool = None) -> dict:
    """Send a URL card to a chat.

    Args:
        url: URL to share
        who: Recipient (optional)
        message: Accompanying message (optional)
        dry_run: If True, don't actually send.
    """
    if dry_run is None:
        dry_run = _dry_run_default
    if dry_run:
        return _ok({"dry_run": True, "url": url, "who": who, "message": message})
    try:
        wx = _get_wx()
        result = wx.SendUrlCard(url, friends=who, message=message)
        return _ok({"result": str(result)})
    except Exception as e:
        return _err(str(e))


# ──────────────────────────────────────────────
# Friends / contacts
# ──────────────────────────────────────────────

def get_friend_list(max_scroll: int = 50) -> dict:
    """Get contact/friend list.

    Args:
        max_scroll: Maximum scroll iterations (default 50)

    Returns:
        {ok, data: WxResponse, error}
    """
    try:
        wx = _get_wx()
        result = wx.GetFriendList(max_scroll=max_scroll)
        return _ok(result if isinstance(result, (dict, list)) else {"result": str(result)})
    except Exception as e:
        return _err(str(e))


def get_friend_details(n: int = None) -> dict:
    """Get detailed info for friends.

    Args:
        n: Number of friends to inspect (optional, all)

    Returns:
        {ok, data: WxResponse, error}
    """
    try:
        wx = _get_wx()
        result = wx.GetFriendDetails(n=n)
        return _ok(result if isinstance(result, (dict, list)) else {"result": str(result)})
    except Exception as e:
        return _err(str(e))


def get_new_friends(acceptable: bool = True) -> dict:
    """Get new friend requests.

    Args:
        acceptable: Only return acceptable requests (default True)

    Returns:
        {ok, data: WxResponse, error}
    """
    try:
        wx = _get_wx()
        result = wx.GetNewFriends(acceptable=acceptable)
        return _ok(result if isinstance(result, (dict, list)) else {"result": str(result)})
    except Exception as e:
        return _err(str(e))


def add_new_friend(keywords: str, addmsg: str = None, remark: str = None, dry_run: bool = None) -> dict:
    """Search and add a new friend.

    Args:
        keywords: Search keywords
        addmsg: Verification message (optional)
        remark: Friend remark name (optional)
        dry_run: If True, don't actually add.
    """
    if dry_run is None:
        dry_run = _dry_run_default
    if dry_run:
        return _ok({"dry_run": True, "keywords": keywords, "addmsg": addmsg, "remark": remark})
    try:
        wx = _get_wx()
        result = wx.AddNewFriend(keywords, addmsg=addmsg, remark=remark)
        return _ok({"result": str(result)})
    except Exception as e:
        return _err(str(e))


# ──────────────────────────────────────────────
# Groups
# ──────────────────────────────────────────────

def create_group(contacts: Union[str, List[str]], dry_run: bool = None) -> dict:
    """Create a new group chat.

    Args:
        contacts: Contact name(s) to add
        dry_run: If True, don't actually create.
    """
    if dry_run is None:
        dry_run = _dry_run_default
    if dry_run:
        return _ok({"dry_run": True, "contacts": contacts})
    try:
        wx = _get_wx()
        result = wx.CreateGroup(contacts)
        return _ok({"result": str(result)})
    except Exception as e:
        return _err(str(e))


# ──────────────────────────────────────────────
# Listener
# ──────────────────────────────────────────────

def add_listen(who: str) -> dict:
    """Add a chat to the message listener.

    Args:
        who: Chat name to listen to

    Returns:
        {ok, data: {result}, error}
    """
    try:
        wx = _get_wx()
        def _cb(*_a, **_kw):
            pass
        result = wx.AddListenChat(who, _cb)
        return _ok({"result": str(result)})
    except Exception as e:
        return _err(str(e))


def remove_listen(who: str) -> dict:
    """Remove a chat from the listener.

    Args:
        who: Chat name to stop listening

    Returns:
        {ok, data: {result}, error}
    """
    try:
        wx = _get_wx()
        result = wx.RemoveListenChat(who)
        return _ok({"result": str(result)})
    except Exception as e:
        return _err(str(e))


def start_listening() -> dict:
    """Start the message listener.

    Returns:
        {ok, data: {listening: true}, error}
    """
    try:
        wx = _get_wx()
        wx.StartListening()
        return _ok({"listening": True})
    except Exception as e:
        return _err(str(e))


def stop_listening() -> dict:
    """Stop the message listener.

    Returns:
        {ok, data: {listening: false}, error}
    """
    try:
        wx = _get_wx()
        wx.StopListening(remove=False)
        return _ok({"listening": False})
    except Exception as e:
        return _err(str(e))


# ──────────────────────────────────────────────
# Navigation
# ──────────────────────────────────────────────

def switch_to_chat() -> dict:
    """Switch to the Chat tab."""
    try:
        wx = _get_wx()
        wx.SwitchToChat()
        return _ok()
    except Exception as e:
        return _err(str(e))


def switch_to_contact() -> dict:
    """Switch to the Contact tab."""
    try:
        wx = _get_wx()
        wx.SwitchToContact()
        return _ok()
    except Exception as e:
        return _err(str(e))


def switch_to_moments() -> dict:
    """Switch to Moments (朋友圈)."""
    try:
        wx = _get_wx()
        wx.SwitchToMoments()
        return _ok()
    except Exception as e:
        return _err(str(e))


# ──────────────────────────────────────────────
# Diagnostics
# ──────────────────────────────────────────────

def doctor(dump_on_fail: bool = False) -> dict:
    """Run diagnostic checks on WeChat UI controls.

    Args:
        dump_on_fail: Dump UI tree on failure (default False)

    Returns:
        {ok, data: {output}, error}
    """
    try:
        import io, sys
        from superwx4.doctor import run_doctor
        buf = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = buf
        try:
            run_doctor(report_path=None, dump_on_fail=dump_on_fail)
        finally:
            sys.stdout = old_stdout
        return _ok({"output": buf.getvalue()})
    except Exception as e:
        return _err(str(e))


def get_dialog(wait: int = 3) -> dict:
    """Get dialog/popup info.

    Args:
        wait: Seconds to wait for dialog (default 3)

    Returns:
        {ok, data: WxResponse, error}
    """
    try:
        wx = _get_wx()
        result = wx.GetDialog(wait=wait)
        return _ok(result if isinstance(result, dict) else {"result": str(result)})
    except Exception as e:
        return _err(str(e))


# ──────────────────────────────────────────────
# Natural language intent dispatch
# ──────────────────────────────────────────────

INTENT_MAP: Dict[str, str] = {
    # 发送
    "发微信": "send_message",
    "发送消息": "send_message",
    "发消息": "send_message",
    "发条消息": "send_message",
    "微信告诉": "send_message",
    "发送文件": "send_files",
    "发文件": "send_files",
    "发语音": "send_audio",
    "发链接": "send_url_card",
    "发名片": "send_url_card",
    # 查看
    "查看消息": "get_messages",
    "当前消息": "get_messages",
    "看看消息": "get_messages",
    "新消息": "get_new_messages",
    "最新消息": "get_last_message",
    "历史消息": "get_history_message",
    "聊天记录": "get_history_message",
    # 会话
    "会话列表": "get_sessions",
    "最近聊天": "get_sessions",
    "切换聊天": "switch_chat",
    "打开聊天": "switch_chat",
    "找人聊天": "switch_chat",
    # 群组
    "最近群聊": "get_recent_groups",
    "创建群": "create_group",
    "建群": "create_group",
    # 好友
    "好友列表": "get_friend_list",
    "联系人": "get_friend_list",
    "好友详情": "get_friend_details",
    "新好友": "get_new_friends",
    "好友请求": "get_new_friends",
    "加好友": "add_new_friend",
    # 监听
    "监听": "add_listen",
    "开始监听": "start_listening",
    "停止监听": "stop_listening",
    "取消监听": "remove_listen",
    # 导航
    "切换到聊天": "switch_to_chat",
    "切换到通讯录": "switch_to_contact",
    "切换到朋友圈": "switch_to_moments",
    "朋友圈": "switch_to_moments",
    # 状态
    "检查状态": "doctor",
    "doctor": "doctor",
    "诊断": "doctor",
    "初始化": "initialize",
    "连接微信": "initialize",
    "微信状态": "status",
    "在线吗": "is_online",
    "我的信息": "get_my_info",
    "弹窗": "get_dialog",
}


def dispatch(intent: str, **kwargs) -> dict:
    """Dispatch a natural-language intent to the corresponding skill function.

    Args:
        intent: The intent key (Chinese or English)
        **kwargs: Arguments passed to the skill function

    Returns:
        {ok, data, error} from the matched function

    Examples:
        dispatch("发消息", msg="你好", who="文件传输助手")
        dispatch("查看消息")
        dispatch("好友列表")
    """
    func_name = INTENT_MAP.get(intent)
    if func_name is None:
        return _err(f"Unknown intent: {intent}. Available: {', '.join(sorted(set(INTENT_MAP.values())))}")
    import sys
    mod = sys.modules[__name__]
    func = getattr(mod, func_name, None)
    if func is None:
        return _err(f"Function not found: {func_name}")
    try:
        return func(**kwargs)
    except TypeError as e:
        return _err(f"Invalid arguments for {func_name}: {e}")


def list_intents() -> dict:
    """List all available intents and their target functions.

    Returns:
        {ok, data: {intent: func_name, ...}, error}
    """
    return _ok(dict(INTENT_MAP))
