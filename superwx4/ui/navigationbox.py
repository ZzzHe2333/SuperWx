from superwx4 import uia
from superwx4.param import (
    WxParam,
    WxResponse,
)
from superwx4.ui.driver import get_driver
from superwx4.utils.win32 import Click, set_cursor_pos


class NavigationBox:
    def __init__(self, control, parent):
        self.control: uia.Control = control
        self.root = parent.root
        self.parent = parent
        self.init()

    def init(self):
        self.chat_icon = self.control.ButtonControl(Name=self._lang('微信'))
        self.contact_icon = self.control.ButtonControl(Name=self._lang('通讯录'))
        self.favorites_icon = self.control.ButtonControl(Name=self._lang('收藏'))
        self.files_icon = self.control.ButtonControl(Name=self._lang('聊天文件'))
        self.moments_icon = self.control.ButtonControl(Name=self._lang('朋友圈'))
        self.browser_icon = self.control.ButtonControl(Name=self._lang('搜一搜'))
        self.video_icon = self.control.ButtonControl(Name=self._lang('视频号'))
        self.stories_icon = self.control.ButtonControl(Name=self._lang('看一看'))
        self.mini_program_icon = self.control.ButtonControl(Name=self._lang('小程序面板'))
        self.phone_icon = self.control.ButtonControl(Name=self._lang('手机'))
        self.settings_icon = self.control.ButtonControl(Name=self._lang('更多'))

    def _lang(self, text):
        return text

    def _win32_click(self, control, allow_foreground=False):
        """Click a navigation control.

        Strategy:
        1. Try driver.click() — UIA InvokePattern (background, no mouse)
        2. If allow_foreground: fallback to Win32 mouse click
        3. Otherwise: return failure
        """
        driver = get_driver()
        result = driver.click(control, reason='navigation click',
                              allow_foreground=False)
        if result.is_success:
            return result

        if allow_foreground:
            try:
                rect = control.BoundingRectangle
                cx = int((rect.left + rect.right) / 2)
                cy = int((rect.top + rect.bottom) / 2)
                set_cursor_pos(cx, cy)
                import time
                time.sleep(0.1)
                Click(uia.Rect(cx, cy, cx + 1, cy + 1))
                return WxResponse.success('foreground win32 click')
            except Exception:
                # fallback: try UIA Click
                try:
                    control.Click()
                    return WxResponse.success('foreground UIA click')
                except Exception as e:
                    return WxResponse.failure(f'click failed: {e}')

        return WxResponse.failure(
            f'foreground required: navigation click',
            data={'method': 'NavigationBox._win32_click', 'requires_foreground': True},
        )

    def switch_to_chat_page(self, allow_foreground=False):
        return self._win32_click(self.chat_icon, allow_foreground=allow_foreground)

    def switch_to_contact_page(self, allow_foreground=False):
        return self._win32_click(self.contact_icon, allow_foreground=allow_foreground)

    def switch_to_favorites_page(self, allow_foreground=False):
        return self._win32_click(self.favorites_icon, allow_foreground=allow_foreground)

    def switch_to_files_page(self, allow_foreground=False):
        return self._win32_click(self.files_icon, allow_foreground=allow_foreground)

    def switch_to_browser_page(self, allow_foreground=False):
        return self._win32_click(self.browser_icon, allow_foreground=allow_foreground)

    def switch_to_moments_page(self, allow_foreground=False):
        return self._win32_click(self.moments_icon, allow_foreground=allow_foreground)

    def switch_to_video_page(self, allow_foreground=False):
        return self._win32_click(self.video_icon, allow_foreground=allow_foreground)

    def switch_to_stories_page(self, allow_foreground=False):
        return self._win32_click(self.stories_icon, allow_foreground=allow_foreground)

    def switch_to_mini_program_page(self, allow_foreground=False):
        return self._win32_click(self.mini_program_icon, allow_foreground=allow_foreground)

    def switch_to_phone_page(self, allow_foreground=False):
        return self._win32_click(self.phone_icon, allow_foreground=allow_foreground)

    def switch_to_settings_page(self, allow_foreground=False):
        return self._win32_click(self.settings_icon, allow_foreground=allow_foreground)
