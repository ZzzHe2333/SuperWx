from wxauto4 import uia
from wxauto4.ui.driver import get_driver
from wxauto4.param import (
    WxParam,
    WxResponse,
)

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

    def switch_to_chat_page(self):
        driver = get_driver()
        driver.click(self.chat_icon, reason='nav: chat page')

    def switch_to_contact_page(self):
        driver = get_driver()
        driver.click(self.contact_icon, reason='nav: contact page')

    def switch_to_favorites_page(self):
        driver = get_driver()
        driver.click(self.favorites_icon, reason='nav: favorites page')

    def switch_to_files_page(self):
        driver = get_driver()
        driver.click(self.files_icon, reason='nav: files page')

    def switch_to_browser_page(self):
        driver = get_driver()
        driver.click(self.browser_icon, reason='nav: browser page')

    def switch_to_moments_page(self):
        driver = get_driver()
        driver.click(self.moments_icon, reason='nav: moments page')

    def switch_to_video_page(self):
        driver = get_driver()
        driver.click(self.video_icon, reason='nav: video page')

    def switch_to_stories_page(self):
        driver = get_driver()
        driver.click(self.stories_icon, reason='nav: stories page')

    def switch_to_mini_program_page(self):
        driver = get_driver()
        driver.click(self.mini_program_icon, reason='nav: mini program page')

    def switch_to_phone_page(self):
        driver = get_driver()
        driver.click(self.phone_icon, reason='nav: phone page')

    def switch_to_settings_page(self):
        driver = get_driver()
        driver.click(self.settings_icon, reason='nav: settings page')
