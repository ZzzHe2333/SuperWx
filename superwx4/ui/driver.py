"""
Background-first operation driver for superwx4.

All click, right-click, text input, and keyboard operations should go through
this driver to avoid moving the real mouse cursor or stealing foreground focus.

Usage:
    from superwx4.ui.driver import get_driver
    driver = get_driver()
    driver.click(some_control, reason="send button")
"""

import time
import win32gui
import win32con
import win32api
from superwx4.param import WxParam, WxResponse
from superwx4.logger import wxlog


class OperationMode:
    BACKGROUND = "background"   # never move mouse, pure UIA patterns only
    FOREGROUND = "foreground"   # allow real mouse clicks
    SAFE = "safe"               # try background first, fallback to foreground with lease


class OperationDriver:
    def __init__(self, mode=None):
        if mode is None:
            mode = OperationMode.BACKGROUND if WxParam.BACKGROUND_MODE else OperationMode.FOREGROUND
        self.mode = mode
        self._saved_mouse = None
        self._saved_fg_hwnd = None
        self._foreground_lease_until = 0

    # ------------------------------------------------------------------
    # Core operations
    # ------------------------------------------------------------------

    def click(self, control, reason="", allow_foreground=False, dry_run=False):
        """
        Click a control without moving the real mouse when possible.

        Strategy:
        1. Try InvokePattern.Invoke() — pure UIA, no mouse
        2. Try TogglePattern.Toggle() — for checkboxes
        3. If allow_foreground or mode=foreground: real Click with save/restore
        4. Otherwise: return failure

        If dry_run=True: only report which strategy would be used, don't execute.
        """
        if not control.Exists(0):
            return WxResponse.failure(f'控件不存在: {reason}')

        # Strategy 1: InvokePattern
        try:
            pattern = control.GetInvokePattern()
            if pattern:
                if dry_run:
                    return WxResponse.success('invoke (dry_run)')
                wxlog.debug(f'[driver] invoke click: {reason}')
                pattern.Invoke()
                return WxResponse.success('invoke')
        except Exception:
            pass

        # Strategy 2: TogglePattern (checkboxes)
        try:
            pattern = control.GetTogglePattern()
            if pattern:
                if dry_run:
                    return WxResponse.success('toggle (dry_run)')
                wxlog.debug(f'[driver] toggle click: {reason}')
                pattern.Toggle()
                return WxResponse.success('toggle')
        except Exception:
            pass

        # Strategy 3: Real click (foreground)
        if allow_foreground or self.mode == OperationMode.FOREGROUND or self._lease_active():
            if dry_run:
                return WxResponse.success('foreground_click (dry_run)')
            return self._real_click(control, reason)

        # Strategy 4: Blocked
        if dry_run:
            return WxResponse.failure(f'blocked (dry_run): {reason}')
        wxlog.warning(
            f'[driver] foreground required for click: {reason} | '
            f'allow_foreground=False, mode={self.mode}'
        )
        return WxResponse.failure(f'foreground required: {reason}')

    def right_click(self, control, x=None, y=None, ratioX=0, ratioY=0,
                    reason="", allow_foreground=False):
        """
        Right-click a control. Always requires foreground (no UIA pattern for context menu).
        """
        if not control.Exists(0):
            return WxResponse.failure(f'控件不存在: {reason}')

        if not (allow_foreground or self.mode == OperationMode.FOREGROUND or self._lease_active()):
            wxlog.warning(
                f'[driver] foreground required for right_click: {reason} | '
                f'allow_foreground=False, mode={self.mode}'
            )
            return WxResponse.failure(f'foreground required: {reason}')

        return self._real_right_click(control, x, y, ratioX, ratioY, reason)

    def set_text(self, edit_control, text, reason=""):
        """
        Set text in an edit control. Pure UIA via ValuePattern, no mouse needed.
        Falls back to clipboard + SendKeys if ValuePattern unavailable.
        """
        if not edit_control.Exists(0):
            return WxResponse.failure(f'编辑控件不存在: {reason}')

        # Strategy 1: ValuePattern.SetValue
        try:
            pattern = edit_control.GetValuePattern()
            if pattern:
                wxlog.debug(f'[driver] SetValue: {reason}')
                pattern.SetValue(text)
                time.sleep(0.1)
                return WxResponse.success('SetValue')
        except Exception:
            pass

        # Strategy 2: Clipboard + Ctrl+V (needs focus but no mouse movement)
        from superwx4.utils.win32 import SetClipboardText
        wxlog.debug(f'[driver] clipboard set_text: {reason}')
        SetClipboardText(text)
        edit_control.SendKeys('{Ctrl}a', waitTime=0)
        edit_control.SendKeys('{Ctrl}v', waitTime=0.2)
        return WxResponse.success('clipboard')

    def send_keys(self, control, keys, reason="", allow_foreground=False):
        """
        SendKeys to a control. SendKeys needs focus but doesn't move mouse.
        """
        if not control.Exists(0):
            return WxResponse.failure(f'控件不存在: {reason}')

        wxlog.debug(f'[driver] SendKeys({keys!r}): {reason}')
        control.SendKeys(keys)
        return WxResponse.success('SendKeys')

    def invoke(self, control, reason="", dry_run=False):
        """
        InvokePattern.Invoke() — pure UIA, no mouse, no focus needed.
        If dry_run=True: only check if InvokePattern exists, don't call Invoke().
        """
        if not control.Exists(0):
            return WxResponse.failure(f'控件不存在: {reason}')

        try:
            pattern = control.GetInvokePattern()
            if pattern:
                if dry_run:
                    return WxResponse.success('invoke (dry_run)')
                wxlog.debug(f'[driver] invoke: {reason}')
                pattern.Invoke()
                return WxResponse.success('invoke')
        except Exception:
            pass

        return WxResponse.failure(f'InvokePattern not available: {reason}')

    def can_invoke(self, control):
        """Check if InvokePattern is available without calling Invoke()."""
        if not control.Exists(0):
            return False
        try:
            return control.GetInvokePattern() is not None
        except Exception:
            return False

    def can_set_value(self, control):
        """Check if ValuePattern is available without calling SetValue()."""
        if not control.Exists(0):
            return False
        try:
            return control.GetValuePattern() is not None
        except Exception:
            return False

    def describe_patterns(self, control):
        """Return a dict describing which UIA patterns are available on a control."""
        info = {
            'has_invoke': False,
            'has_value': False,
            'has_toggle': False,
            'control_type': '',
            'class_name': '',
            'name': '',
        }
        if not control.Exists(0):
            return info
        try:
            info['control_type'] = control.ControlTypeName
            info['class_name'] = control.ClassName or ''
            info['name'] = control.Name or ''
        except Exception:
            pass
        try:
            info['has_invoke'] = control.GetInvokePattern() is not None
        except Exception:
            pass
        try:
            info['has_value'] = control.GetValuePattern() is not None
        except Exception:
            pass
        try:
            info['has_toggle'] = control.GetTogglePattern() is not None
        except Exception:
            pass
        return info

    # ------------------------------------------------------------------
    # Foreground lease
    # ------------------------------------------------------------------

    def foreground_lease(self, timeout=None):
        """
        Temporarily allow foreground operations for `timeout` seconds.
        """
        if timeout is None:
            timeout = WxParam.FOREGROUND_LEASE_SECONDS
        self._foreground_lease_until = time.time() + timeout
        wxlog.debug(f'[driver] foreground lease granted for {timeout}s')

    def _lease_active(self):
        return time.time() < self._foreground_lease_until

    # ------------------------------------------------------------------
    # Mouse / foreground save/restore
    # ------------------------------------------------------------------

    def _save_state(self):
        """Save current mouse position and foreground window."""
        if WxParam.RESTORE_MOUSE_POSITION:
            try:
                self._saved_mouse = win32api.GetCursorPos()
            except Exception:
                self._saved_mouse = None
        if WxParam.RESTORE_FOREGROUND_WINDOW:
            try:
                self._saved_fg_hwnd = win32gui.GetForegroundWindow()
            except Exception:
                self._saved_fg_hwnd = None

    def restore_mouse(self):
        """Restore saved mouse position and foreground window."""
        if self._saved_mouse and WxParam.RESTORE_MOUSE_POSITION:
            try:
                win32api.SetCursorPos(self._saved_mouse)
                wxlog.debug(f'[driver] mouse restored to {self._saved_mouse}')
            except Exception:
                pass
            self._saved_mouse = None

        if self._saved_fg_hwnd and WxParam.RESTORE_FOREGROUND_WINDOW:
            try:
                win32gui.SetForegroundWindow(self._saved_fg_hwnd)
                wxlog.debug(f'[driver] foreground restored to {self._saved_fg_hwnd}')
            except Exception:
                pass
            self._saved_fg_hwnd = None

    def _activate_wechat(self):
        """Bring WeChat window to foreground."""
        from superwx4.utils.win32 import GetAllWindows
        wins = GetAllWindows(classname='WeChatMainWndForPC')
        if not wins:
            wins = GetAllWindows(name='微信')
        if wins:
            hwnd = wins[0][0]
            try:
                win32gui.ShowWindow(hwnd, 9)  # SW_RESTORE
                win32gui.SetForegroundWindow(hwnd)
                time.sleep(0.1)
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Real click implementation (foreground only)
    # ------------------------------------------------------------------

    def _real_click(self, control, reason=""):
        """Execute a real Click with save/restore."""
        self._save_state()
        try:
            self._activate_wechat()
            wxlog.warning(f'[driver] foreground click: {reason}')
            control.Click()
            time.sleep(0.1)
        finally:
            self.restore_mouse()
        return WxResponse.success('foreground click')

    def _real_right_click(self, control, x, y, ratioX, ratioY, reason=""):
        """Execute a real RightClick with save/restore."""
        self._save_state()
        try:
            self._activate_wechat()
            wxlog.warning(f'[driver] foreground right_click: {reason}')
            if x is not None:
                control.RightClick(x=x, y=y or 0, ratioX=ratioX, ratioY=ratioY)
            else:
                control.RightClick()
            time.sleep(0.1)
        finally:
            self.restore_mouse()
        return WxResponse.success('foreground right_click')


# ------------------------------------------------------------------
# Module-level singleton
# ------------------------------------------------------------------

_driver_instance = None

def get_driver(mode=None):
    """Get or create the global OperationDriver instance."""
    global _driver_instance
    if _driver_instance is None or (mode is not None and mode != _driver_instance.mode):
        _driver_instance = OperationDriver(mode=mode)
    return _driver_instance
# 1
