"""Pydantic schemas for wxauto4 REST API."""
from __future__ import annotations
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel


class ApiResponse(BaseModel):
    ok: bool = True
    data: Any = None
    error: Optional[str] = None


class InitRequest(BaseModel):
    nickname: Optional[str] = None
    debug: bool = False


class SwitchChatRequest(BaseModel):
    who: str
    exact: bool = True
    force: bool = False
    force_wait: float = 0.5


class SendMsgRequest(BaseModel):
    msg: str
    who: Optional[str] = None
    at: Optional[Union[str, List[str]]] = None
    clear: bool = True
    exact: bool = False
    dry_run: bool = False


class SendFilesRequest(BaseModel):
    filepath: Union[str, List[str]]
    who: Optional[str] = None
    exact: bool = False
    dry_run: bool = False


class ListenRequest(BaseModel):
    who: str


class DoctorRequest(BaseModel):
    dump_on_fail: bool = False
    report: bool = False
