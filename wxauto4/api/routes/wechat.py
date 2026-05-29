"""WeChat control routes."""
from __future__ import annotations
import os
from fastapi import APIRouter, HTTPException
from wxauto4.api.schemas import (
    ApiResponse, InitRequest, SwitchChatRequest,
    SendMsgRequest, SendFilesRequest, ListenRequest, DoctorRequest,
)

router = APIRouter(prefix="/wechat", tags=["wechat"])

# Global state: the WeChat instance (initialized on /wechat/init)
_wx = None


def _get_wx():
    if _wx is None:
        raise HTTPException(400, "WeChat not initialized. Call POST /wechat/init first.")
    return _wx


def _ok(data=None):
    return ApiResponse(ok=True, data=data, error=None)


def _err(msg: str):
    return ApiResponse(ok=False, data=None, error=msg)


@router.post("/init")
def wechat_init(req: InitRequest):
    global _wx
    try:
        from wxauto4 import WeChat
        _wx = WeChat(nickname=req.nickname, debug=req.debug)
        return _ok({"nickname": _wx.nickname})
    except Exception as e:
        return _err(str(e))


@router.get("/status")
def wechat_status():
    wx = _get_wx()
    return _ok({"nickname": wx.nickname, "initialized": True})


@router.get("/me")
def wechat_me():
    wx = _get_wx()
    try:
        return _ok(wx.ChatInfo())
    except Exception as e:
        return _err(str(e))


@router.get("/sessions")
def wechat_sessions():
    wx = _get_wx()
    try:
        sessions = wx.GetSession()
        data = [{"name": s.Name, "type": s.ControlTypeName} for s in sessions] if sessions else []
        return _ok(data)
    except Exception as e:
        return _err(str(e))


@router.post("/chat/switch")
def wechat_switch_chat(req: SwitchChatRequest):
    wx = _get_wx()
    try:
        result = wx.ChatWith(req.who, exact=req.exact, force=req.force, force_wait=req.force_wait)
        return _ok({"result": str(result)})
    except Exception as e:
        return _err(str(e))


@router.post("/message/send")
def wechat_send_message(req: SendMsgRequest):
    wx = _get_wx()
    if req.dry_run:
        return _ok({"dry_run": True, "msg": req.msg, "who": req.who, "at": req.at})
    try:
        result = wx.SendMsg(req.msg, who=req.who, at=req.at, clear=req.clear, exact=req.exact)
        return _ok({"result": str(result)})
    except Exception as e:
        return _err(str(e))


@router.post("/file/send")
def wechat_send_file(req: SendFilesRequest):
    wx = _get_wx()
    # Validate paths
    paths = [req.filepath] if isinstance(req.filepath, str) else req.filepath
    for p in paths:
        if not os.path.isabs(p):
            return _err(f"File path must be absolute: {p}")
        if not os.path.exists(p):
            return _err(f"File not found: {p}")
    if req.dry_run:
        return _ok({"dry_run": True, "filepath": paths, "who": req.who})
    try:
        result = wx.SendFiles(paths, who=req.who, exact=req.exact)
        return _ok({"result": str(result)})
    except Exception as e:
        return _err(str(e))


@router.get("/messages/current")
def wechat_get_messages():
    wx = _get_wx()
    try:
        msgs = wx.GetAllMessage()
        data = [m.to_dict() for m in msgs] if msgs else []
        return _ok(data)
    except Exception as e:
        return _err(str(e))


@router.get("/messages/new")
def wechat_get_new_messages():
    wx = _get_wx()
    try:
        msgs = wx.GetNewMessage()
        data = [m.to_dict() for m in msgs] if msgs else []
        return _ok(data)
    except Exception as e:
        return _err(str(e))


@router.post("/listen/add")
def wechat_add_listen(req: ListenRequest):
    wx = _get_wx()
    try:
        def _default_callback(msg, chat):
            pass
        result = wx.AddListenChat(req.who, _default_callback)
        return _ok({"result": str(result)})
    except Exception as e:
        return _err(str(e))


@router.post("/listen/remove")
def wechat_remove_listen(req: ListenRequest):
    wx = _get_wx()
    try:
        result = wx.RemoveListenChat(req.who)
        return _ok({"result": str(result)})
    except Exception as e:
        return _err(str(e))


@router.post("/listen/start")
def wechat_start_listening():
    wx = _get_wx()
    try:
        wx.StartListening()
        return _ok({"listening": True})
    except Exception as e:
        return _err(str(e))


@router.post("/listen/stop")
def wechat_stop_listening():
    wx = _get_wx()
    try:
        wx.StopListening(remove=False)
        return _ok({"listening": False})
    except Exception as e:
        return _err(str(e))


@router.post("/doctor")
def wechat_doctor(req: DoctorRequest):
    try:
        from wxauto4.doctor import run_doctor
        import io, sys
        buf = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = buf
        try:
            run_doctor(report_path=None, dump_on_fail=req.dump_on_fail)
        finally:
            sys.stdout = old_stdout
        return _ok({"output": buf.getvalue()})
    except Exception as e:
        return _err(str(e))
