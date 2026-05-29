"""Locator engine — try selector fallback chains against a UIA control.

Provides helpers for probing WeChat 4.x UI controls without modifying
any existing wxauto4 business logic.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from wxauto4 import uia
from wxauto4.locator.selectors import SELECTORS


# ---- basic helpers ----

def ctrl_exists(ctrl, timeout: float = 0) -> bool:
    """Safe Exists() check that never raises."""
    try:
        return bool(ctrl.Exists(timeout))
    except Exception:
        return False


def rect_to_dict(ctrl) -> Dict[str, Any]:
    """Convert BoundingRectangle to a plain dict."""
    try:
        r = ctrl.BoundingRectangle
        return {"left": r.left, "top": r.top, "right": r.right, "bottom": r.bottom}
    except Exception:
        return {}


def safe_get(ctrl, attr: str, default=None):
    """Safely read an attribute from a control."""
    try:
        return getattr(ctrl, attr, default)
    except Exception:
        return default


# ---- core lookup ----

def find_first(
    root: uia.Control,
    selectors_key: str,
    search_depth: int = 30,
) -> Optional[uia.Control]:
    """Try each selector in the fallback chain, return first match that Exists().

    Args:
        root: The parent control to search under.
        selectors_key: Key into the SELECTORS dict.
        search_depth: UIA search depth.

    Returns:
        The first matching control, or None.
    """
    selectors = SELECTORS.get(selectors_key, [])
    for sel in selectors:
        method_name = sel["method"]
        kwargs = {k: v for k, v in sel.items() if k != "method"}
        if search_depth:
            kwargs["searchDepth"] = search_depth
        try:
            method = getattr(root, method_name, None)
            if method is None:
                continue
            ctrl = method(**kwargs)
            if ctrl_exists(ctrl, 0.1):
                return ctrl
        except Exception:
            continue
    return None


def find_wechat_window() -> Optional[uia.Control]:
    """Find the WeChat main window control via UIAutomation.

    Tries multiple name variants and class names.

    Returns:
        The main window control, or None.
    """
    _names = ['微信', 'Weixin', 'WeChat']
    _cls = 'mmui::MainWindow'
    try:
        root = uia.GetRootControl()
        # Pass 1: ClassName + known names
        for w in root.GetChildren():
            try:
                if w.ClassName == _cls and (w.Name or '') in _names:
                    return w
            except Exception:
                continue
        # Pass 2: ClassName only
        for w in root.GetChildren():
            try:
                if w.ClassName == _cls:
                    return w
            except Exception:
                continue
        # Pass 3: fuzzy name match
        for w in root.GetChildren():
            try:
                name_lower = (w.Name or '').lower()
                if any(kw in name_lower for kw in ('wechat', 'weixin', '微信')):
                    return w
            except Exception:
                continue
    except Exception:
        pass
    return None


def describe_control(ctrl) -> Dict[str, Any]:
    """Return a debug dict describing a UIA control."""
    if ctrl is None:
        return {"status": "None"}
    try:
        return {
            "exists": ctrl_exists(ctrl),
            "Name": safe_get(ctrl, "Name"),
            "ClassName": safe_get(ctrl, "ClassName"),
            "AutomationId": safe_get(ctrl, "AutomationId"),
            "ControlType": safe_get(ctrl, "ControlTypeName"),
            "BoundingRectangle": rect_to_dict(ctrl),
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}
