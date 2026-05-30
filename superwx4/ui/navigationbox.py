from superwx4 import uia
from superwx4.param import (
    WxParam,
    WxResponse,
)
from superwx4.utils.win32 import Click, set_cursor_pos


class NavigationBox:
    def __init__(self, control, parent):
        self.control: uia.Control = control
        self.root = parent.root
        self.parent = parent
        self.init()

    def init(self):
        # self.my_icon = self.control.ButtonControl()
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

    def _win32_click(self, control):
        """使用 Win32 鼠标事件点击控件（UIA Click 对 Qt/mmui 标签页无效）。"""
        try:
            rect = control.BoundingRectangle
            cx = int((rect.left + rect.right) / 2)
            cy = int((rect.top + rect.bottom) / 2)
            set_cursor_pos(cx, cy)
            import time
            time.sleep(0.1)
            Click(uia.Rect(cx, cy, cx + 1, cy + 1))
        except Exception:
            # fallback: try UIA Click
            control.Click()

    def switch_to_chat_page(self):
        self._win32_click(self.chat_icon)

    def switch_to_contact_page(self):
        self._win32_click(self.contact_icon)

    def switch_to_favorites_page(self):
        self._win32_click(self.favorites_icon)

    def switch_to_files_page(self):
        self._win32_click(self.files_icon)

    def switch_to_browser_page(self):
        self._win32_click(self.browser_icon)

    def switch_to_moments_page(self):
        self._win32_click(self.moments_icon)

    def switch_to_video_page(self):
        self._win32_click(self.video_icon)

    def switch_to_stories_page(self):
        self._win32_click(self.stories_icon)

    def switch_to_mini_program_page(self):
        self._win32_click(self.mini_program_icon)

    def switch_to_phone_page(self):
        self._win32_click(self.phone_icon)

    def switch_to_settings_page(self):
        self._win32_click(self.settings_icon)

# 1
