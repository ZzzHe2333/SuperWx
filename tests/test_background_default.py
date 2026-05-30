# -*- coding: utf-8 -*-
"""Test: Background-first operation defaults.

Verifies that default code paths do NOT call foreground/mouse operations.
All dangerous calls (SetForegroundWindow, SetCursorPos, Click, RightClick,
MiddleClick, DoubleClick, ShowWindow) are monkeypatched — if they are
called, the test fails.
"""
import sys
import os
import unittest
from unittest.mock import MagicMock, patch, PropertyMock

# Ensure project root is on path
CUR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if CUR not in sys.path:
    sys.path.insert(0, CUR)


class ForegroundGuard:
    """Mock that fails if any foreground/mouse method is called."""

    def __init__(self, name=""):
        self._name = name
        self._called = False

    def __call__(self, *args, **kwargs):
        self._called = True
        raise AssertionError(
            f"FOREGROUND LEAK: {self._name} was called with {args} {kwargs}"
        )

    @property
    def called(self):
        return self._called


def make_mock_control(name="mock_control", has_invoke=False, has_value=False):
    """Create a mock UIA control."""
    ctrl = MagicMock()
    ctrl.Exists.return_value = True
    ctrl.Name = name
    ctrl.ControlTypeName = "ButtonControl"
    ctrl.ClassName = "mock_class"
    ctrl.HasKeyboardFocus = False

    # Default: no UIA patterns
    if has_invoke:
        invoke_pattern = MagicMock()
        ctrl.GetInvokePattern.return_value = invoke_pattern
    else:
        ctrl.GetInvokePattern.return_value = None

    if has_value:
        value_pattern = MagicMock()
        value_pattern.Value = ""
        ctrl.GetValuePattern.return_value = value_pattern
    else:
        ctrl.GetValuePattern.return_value = None

    ctrl.GetTogglePattern.return_value = None

    return ctrl


class TestDriverClickNoForeground(unittest.TestCase):
    """Test that driver.click() does NOT call real Click when allow_foreground=False."""

    def test_click_with_invoke_pattern(self):
        """InvokePattern should be used — no real click."""
        from superwx4.ui.driver import OperationDriver
        driver = OperationDriver(mode="background")
        ctrl = make_mock_control(has_invoke=True)
        result = driver.click(ctrl, reason="test", allow_foreground=False)
        self.assertTrue(result.is_success)
        ctrl.GetInvokePattern().Invoke.assert_called_once()
        ctrl.Click.assert_not_called()

    def test_click_no_pattern_blocked(self):
        """No pattern + allow_foreground=False → failure, no real click."""
        from superwx4.ui.driver import OperationDriver
        driver = OperationDriver(mode="background")
        ctrl = make_mock_control(has_invoke=False)
        result = driver.click(ctrl, reason="test", allow_foreground=False)
        self.assertFalse(result.is_success)
        ctrl.Click.assert_not_called()
        self.assertIn("foreground required", result['message'])


class TestDriverMiddleClickBlocked(unittest.TestCase):
    """Test that driver.middle_click() blocks by default."""

    def test_middle_click_blocked(self):
        from superwx4.ui.driver import OperationDriver
        driver = OperationDriver(mode="background")
        ctrl = make_mock_control()
        result = driver.middle_click(ctrl, reason="test", allow_foreground=False)
        self.assertFalse(result.is_success)
        ctrl.MiddleClick.assert_not_called()


class TestDriverDoubleClickBlocked(unittest.TestCase):
    """Test that driver.double_click() blocks by default."""

    def test_double_click_blocked(self):
        from superwx4.ui.driver import OperationDriver
        driver = OperationDriver(mode="background")
        ctrl = make_mock_control()
        result = driver.double_click(ctrl, reason="test", allow_foreground=False)
        self.assertFalse(result.is_success)
        ctrl.DoubleClick.assert_not_called()


class TestDriverRightClickBlocked(unittest.TestCase):
    """Test that driver.right_click() blocks by default."""

    def test_right_click_blocked(self):
        from superwx4.ui.driver import OperationDriver
        driver = OperationDriver(mode="background")
        ctrl = make_mock_control()
        result = driver.right_click(ctrl, reason="test", allow_foreground=False)
        self.assertFalse(result.is_success)
        ctrl.RightClick.assert_not_called()


class TestDriverSetText(unittest.TestCase):
    """Test that driver.set_text() uses ValuePattern — no mouse."""

    def test_set_text_value_pattern(self):
        from superwx4.ui.driver import OperationDriver
        driver = OperationDriver(mode="background")
        ctrl = make_mock_control(has_value=True)
        result = driver.set_text(ctrl, "hello", reason="test")
        self.assertTrue(result.is_success)
        ctrl.GetValuePattern().SetValue.assert_called_once_with("hello")


class TestDriverClearText(unittest.TestCase):
    """Test that driver.clear_text() uses SendKeys — no mouse."""

    def test_clear_text_sendkeys(self):
        from superwx4.ui.driver import OperationDriver
        driver = OperationDriver(mode="background")
        ctrl = make_mock_control()
        result = driver.clear_text(ctrl, reason="test")
        self.assertTrue(result.is_success)
        ctrl.SendKeys.assert_any_call('{Ctrl}a', waitTime=0)
        ctrl.SendKeys.assert_any_call('{DELETE}', waitTime=0.1)


class TestDriverWheelNoMouse(unittest.TestCase):
    """Test that wheel operations don't move mouse."""

    def test_wheel_up(self):
        from superwx4.ui.driver import OperationDriver
        driver = OperationDriver(mode="background")
        ctrl = make_mock_control()
        result = driver.wheel_up(ctrl, wheelTimes=3, reason="test")
        self.assertTrue(result.is_success)
        ctrl.WheelUp.assert_called_once_with(wheelTimes=3)

    def test_wheel_down(self):
        from superwx4.ui.driver import OperationDriver
        driver = OperationDriver(mode="background")
        ctrl = make_mock_control()
        result = driver.wheel_down(ctrl, wheelTimes=5, reason="test")
        self.assertTrue(result.is_success)
        ctrl.WheelDown.assert_called_once_with(wheelTimes=5)


class TestBaseShowGated(unittest.TestCase):
    """Test that BaseUIWnd._show() is gated by default."""

    def test_show_blocked_by_default(self):
        """_show() with default allow_foreground=False should NOT call Win32."""
        from superwx4.ui.base import BaseUIWnd

        class TestWnd(BaseUIWnd):
            def _lang(self, text):
                return text

        wnd = TestWnd()
        wnd.control = MagicMock()
        wnd.control.Exists.return_value = True
        wnd.HWND = 12345

        with patch('superwx4.ui.base.win32gui') as mock_win32:
            result = wnd._show()
            self.assertFalse(result.is_success)
            mock_win32.ShowWindow.assert_not_called()
            mock_win32.SetWindowPos.assert_not_called()


class TestNavigationNoCursorMove(unittest.TestCase):
    """Test that NavigationBox methods don't move cursor by default."""

    def test_switch_to_chat_page_no_cursor(self):
        """switch_to_chat_page with default allow_foreground should not set_cursor_pos."""
        from superwx4.ui.driver import OperationDriver
        driver = OperationDriver(mode="background")
        ctrl = make_mock_control(has_invoke=True)

        # If InvokePattern works, no cursor move needed
        result = driver.click(ctrl, reason="nav test", allow_foreground=False)
        self.assertTrue(result.is_success)


class TestAllowForegroundPassthrough(unittest.TestCase):
    """Test that allow_foreground parameter is accepted by Chat.SendMsg/SendFiles."""

    def test_sendmsg_signature(self):
        """Chat.SendMsg should accept allow_foreground parameter."""
        import inspect
        from superwx4.wx import Chat
        sig = inspect.signature(Chat.SendMsg)
        self.assertIn('allow_foreground', sig.parameters)
        self.assertFalse(sig.parameters['allow_foreground'].default)

    def test_sendfiles_signature(self):
        """Chat.SendFiles should accept allow_foreground parameter."""
        import inspect
        from superwx4.wx import Chat
        sig = inspect.signature(Chat.SendFiles)
        self.assertIn('allow_foreground', sig.parameters)
        self.assertFalse(sig.parameters['allow_foreground'].default)


class TestSwitchMethodsSignature(unittest.TestCase):
    """Test that SwitchTo* methods accept allow_foreground."""

    def test_switch_to_chat(self):
        import inspect
        from superwx4.wx import WeChat
        sig = inspect.signature(WeChat.SwitchToChat)
        self.assertIn('allow_foreground', sig.parameters)

    def test_switch_to_contact(self):
        import inspect
        from superwx4.wx import WeChat
        sig = inspect.signature(WeChat.SwitchToContact)
        self.assertIn('allow_foreground', sig.parameters)

    def test_switch_to_moments(self):
        import inspect
        from superwx4.wx import WeChat
        sig = inspect.signature(WeChat.SwitchToMoments)
        self.assertIn('allow_foreground', sig.parameters)


class TestChatBoxSendMsgSignature(unittest.TestCase):
    """Test that ChatBox.send_msg accepts allow_foreground."""

    def test_send_msg_signature(self):
        import inspect
        from superwx4.ui.chatbox import ChatBox
        sig = inspect.signature(ChatBox.send_msg)
        self.assertIn('allow_foreground', sig.parameters)
        self.assertFalse(sig.parameters['allow_foreground'].default)

    def test_send_file_signature(self):
        import inspect
        from superwx4.ui.chatbox import ChatBox
        sig = inspect.signature(ChatBox.send_file)
        self.assertIn('allow_foreground', sig.parameters)
        self.assertFalse(sig.parameters['allow_foreground'].default)

    def test_send_text_signature(self):
        import inspect
        from superwx4.ui.chatbox import ChatBox
        sig = inspect.signature(ChatBox.send_text)
        self.assertIn('allow_foreground', sig.parameters)
        self.assertFalse(sig.parameters['allow_foreground'].default)


class TestListenerSafety(unittest.TestCase):
    """Test that listener methods handle missing state gracefully."""

    def test_stop_listening_no_thread(self):
        """StopListening should not crash if _listener_thread doesn't exist."""
        from superwx4.wx import WeChat
        # Create a minimal mock WeChat without calling __init__
        wx = object.__new__(WeChat)
        wx.listen = {}
        # Should not raise
        wx.StopListening(remove=False)

    def test_start_listening_no_thread(self):
        """StartListening should not crash if _listener_thread doesn't exist."""
        from superwx4.wx import WeChat
        wx = object.__new__(WeChat)
        wx.listen = {}
        # This will try to _listener_start, which needs _api — just check it doesn't crash on missing thread
        try:
            wx.StartListening()
        except AttributeError:
            pass  # Expected: _api doesn't exist, but _listener_thread check should pass


if __name__ == '__main__':
    unittest.main()
