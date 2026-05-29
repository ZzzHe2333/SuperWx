"""Centralized UI control locators for WeChat 4.x.

This module is purely additive — it does not modify any existing wxauto4 code.
"""

from .engine import (
    ctrl_exists,
    rect_to_dict,
    safe_get,
    find_first,
    find_wechat_window,
    describe_control,
)
from .selectors import SELECTORS
from .dump import dump_ui_tree
from .repair_context import generate_repair_context
from .patch_guard import validate_patch, guard_report

__all__ = [
    "ctrl_exists",
    "rect_to_dict",
    "safe_get",
    "find_first",
    "find_wechat_window",
    "describe_control",
    "SELECTORS",
    "dump_ui_tree",
    "generate_repair_context",
    "validate_patch",
    "guard_report",
]
