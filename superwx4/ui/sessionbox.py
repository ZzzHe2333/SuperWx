from __future__ import annotations
from superwx4 import uia
from superwx4.param import (
    WxParam,
    WxResponse,
)
from superwx4.languages import MENU_OPTIONS
from superwx4.ui.component import Menu
from superwx4.ui.driver import get_driver
from superwx4.utils.win32 import SetClipboardText
from superwx4.logger import wxlog
import time
from typing import (
    Union,
    List
)
import re


class SessionBox:
    def __init__(self, control, parent):
        self.control: uia.Control = control
        self.root = parent.root
        self.parent = parent
        self.init()

    def init(self):
        # Search box — try XSearchField group first, then name/class fallbacks
        self.searchbox = (
            self.control.GroupControl(ClassName="mmui::XSearchField").EditControl()
            or self.control.EditControl(Name="搜索")
            or self.control.EditControl(ClassName="mmui::XValidatorTextEdit")
            or self.control.EditControl()
        )

        # Session list — try AutomationId first (WeChat 4.x), then legacy selectors
        self.session_list = (
            self.control.ListControl(AutomationId="session_list")
            or self.control.ListControl(ClassName="mmui::XTableView")
            or self.control.GroupControl(ClassName="mmui::ChatSessionList").ListControl(ClassName="mmui::XTableView", Name="会话")
            or self.control.ListControl()  # fallback: the first list under session area
        )

        self.search_content = self.parent.control.WindowControl(ClassName="mmui::SearchContentPopover")

    def roll_up(self, n: int=5):
        driver = get_driver()
        driver.wheel_up(self.control, wheelTimes=n, reason='session roll_up')

    def roll_down(self, n: int=5):
        driver = get_driver()
        driver.wheel_down(self.control, wheelTimes=n, reason='session roll_down')

    def get_session(self) -> List[SessionElement]:
        if self.session_list.Exists(0):
            return [SessionElement(i, self) for i in self.session_list.GetChildren()]
        else:
            return []

    def search(
            self,
            keywords: str,
            force: bool = False,
            force_wait: Union[float, int] = 0.5,
            allow_foreground: bool = False,
        ):
        driver = get_driver()

        # Try ValuePattern first for search input
        result = driver.set_text(self.searchbox, keywords, reason='search input')
        if not result.is_success:
            # Fallback: clipboard + right-click paste (requires foreground)
            SetClipboardText(keywords)
            driver.right_click(self.searchbox, reason='search paste',
                               allow_foreground=allow_foreground)
            menu = Menu(self)
            menu.select('粘贴')

        driver.send_keys(self.searchbox, '{ENTER}', reason='search confirm')

        search_result = self.search_content.ListControl()

        if force:
            time.sleep(force_wait)

        return [SearchResultElement(i) for i in search_result.GetChildren()]

    def switch_chat(
        self,
        keywords: str,
        exact: bool = True,
        force: bool = False,
        force_wait: Union[float, int] = 0.5,
        allow_foreground: bool = False,
    ):
        wxlog.debug(f"切换聊天窗口: {keywords}, {exact}, {force}, {force_wait}")
        driver = get_driver()

        # Fast path 1: click session item directly by AutomationId
        try:
            direct = (
                self.parent.control.ListItemControl(AutomationId=f"session_item_{keywords}")
                or self.root.control.ListItemControl(AutomationId=f"session_item_{keywords}")
            )
            if direct and direct.Exists(0):
                result = driver.click(direct, reason=f'switch_chat direct: {keywords}',
                                      allow_foreground=allow_foreground)
                if result.is_success:
                    return keywords
        except Exception:
            pass

        # Fast path 2: scan visible session list items by name
        try:
            if self.session_list.Exists(0):
                for item in self.session_list.GetChildren():
                    item_name = (item.Name or '').split('\n')[0].strip()
                    if exact:
                        if item_name == keywords:
                            result = driver.click(item, reason=f'switch_chat scan: {keywords}',
                                                  allow_foreground=allow_foreground)
                            if result.is_success:
                                return keywords
                    else:
                        if keywords in item_name:
                            result = driver.click(item, reason=f'switch_chat scan: {keywords}',
                                                  allow_foreground=allow_foreground)
                            if result.is_success:
                                return item_name
        except Exception:
            pass

        # Fallback: use search
        search_box = self.search_content.ListControl()
        search_result = self.search(keywords, force, force_wait,
                                    allow_foreground=allow_foreground)
        t0 = time.time()
        while time.time() - t0 < WxParam.SEARCH_CHAT_TIMEOUT:
            results = []
            search_result_items = search_box.GetChildren()
            for search_result_item in search_result_items:
                text: str = search_result_item.Name
                if exact:
                    if text == keywords:
                        result = driver.click(search_result_item,
                                              reason=f'switch_chat search result: {keywords}',
                                              allow_foreground=allow_foreground)
                        if result.is_success:
                            return keywords
                    elif (
                        ' 微信号: ' in text
                        and (split:=text.split(' 微信号: '))[-1].lower() == keywords.lower()
                    ):
                        result = driver.click(search_result_item,
                                              reason=f'switch_chat search result: {keywords}',
                                              allow_foreground=allow_foreground)
                        if result.is_success:
                            return split[0]
                    elif (
                        ' 昵称: ' in text
                        and (split:=text.split(' 昵称: '))[-1].lower() == keywords.lower()
                    ):
                        result = driver.click(search_result_item,
                                              reason=f'switch_chat search result: {keywords}',
                                              allow_foreground=allow_foreground)
                        if result.is_success:
                            return split[0]
                else:
                    if keywords in text:
                        result = driver.click(search_result_item,
                                              reason=f'switch_chat search result: {keywords}',
                                              allow_foreground=allow_foreground)
                        if result.is_success:
                            return text

        if self.search_content.Exists(0):
            driver.send_keys(self.search_content, '{Esc}', reason='search dismiss')

    def open_separate_window(self, name: str, allow_foreground: bool = False):
        wxlog.debug(f"打开独立窗口: {name}")
        realname = self.switch_chat(name, allow_foreground=allow_foreground)
        if not realname:
            return WxResponse.failure('未找到会话')
        time.sleep(0.3)
        while True:
            session = [i for i in self.get_session() if uia.IsElementInWindow(self.session_list, i.control)][0]
            if session.content.startswith(realname):
                break
        session.double_click(allow_foreground=allow_foreground)
        return WxResponse.success(data={'nickname': realname})


    def go_top(self):
        wxlog.debug("回到会话列表顶部")
        driver = get_driver()
        driver.send_keys(self.control, '{Home}', reason='session go_top')

    def go_bottom(self):
        wxlog.debug("回到会话列表底部")
        driver = get_driver()
        driver.send_keys(self.control, '{End}', reason='session go_bottom')

class SessionElement:
    def __init__(
            self,
            control: uia.Control,
            parent: SessionBox,
        ):
        self.root = parent.root
        self.parent = parent
        self.control = control
        self.content = control.Name

    @property
    def texts(self) -> List[str]:
        """拆分当前会话控件中的文本行"""

        return [
            line for line in str(self.content).split('\n')
            if line and line.strip()
        ]

    @property
    def name(self) -> str:
        """会话名称"""

        if self.texts:
            return self.texts[0]
        return ''

    @property
    def unread_count(self) -> int:
        """未读消息数量"""

        unread_pattern = re.compile(r'\[(\d+)条\]')
        for text in self.texts:
            if match := unread_pattern.search(text):
                return int(match.group(1))
        return 0

    def _menu_option_text(self, option_key: str) -> str:
        option = MENU_OPTIONS.get(option_key, {})
        lang = getattr(WxParam, 'LANGUAGE', 'cn')
        text = option.get(lang) if isinstance(option, dict) else None
        if not text:
            text = option.get('cn') if isinstance(option, dict) else None
        return text or option_key

    def select_menu_option(self, option_key: str, wait=0.3, allow_foreground: bool = False):
        """根据配置语言选择菜单项"""

        option_text = self._menu_option_text(option_key)
        return self.select_option(option_text, wait, allow_foreground=allow_foreground)

    def __repr__(self):
        content = str(self.content).replace('\n', ' ')
        if len(content) > 5:
            content = content[:5] + '...'
        return f"<superwx4 Session Element({content})>"

    def roll_into_view(self):
        uia.RollIntoView(self.control.GetParentControl(), self.control)

    def _click(self, right: bool=False, double: bool=False, allow_foreground: bool = False):
        self.roll_into_view()
        driver = get_driver()
        if right:
            return driver.right_click(self.control, reason='session right_click',
                                       allow_foreground=allow_foreground)
        elif double:
            return driver.double_click(self.control, reason='session double_click',
                                        allow_foreground=allow_foreground)
        else:
            return driver.click(self.control, reason='session click',
                                allow_foreground=allow_foreground)

    def click(self, allow_foreground: bool = False):
        return self._click(allow_foreground=allow_foreground)

    def right_click(self, allow_foreground: bool = False):
        return self._click(right=True, allow_foreground=allow_foreground)

    def double_click(self, allow_foreground: bool = False):
        return self._click(allow_foreground=allow_foreground) or self._click(double=True, allow_foreground=allow_foreground)

    def select_option(self, option: str, wait=0.3, allow_foreground: bool = False):
        self.roll_into_view()
        driver = get_driver()
        result = driver.right_click(self.control, reason='session select_option',
                                    allow_foreground=allow_foreground)
        if not result.is_success:
            return result
        time.sleep(wait)
        menu = Menu(self.parent)
        return menu.select(option)

    def pin(self, allow_foreground: bool = False):
        """置顶聊天"""
        return self.select_menu_option('置顶', allow_foreground=allow_foreground)

    def unpin(self, allow_foreground: bool = False):
        """取消置顶聊天"""
        return self.select_menu_option('取消置顶', allow_foreground=allow_foreground)

    def mark_unread(self, allow_foreground: bool = False):
        """标记为未读"""
        return self.select_menu_option('标为未读', allow_foreground=allow_foreground)

    def toggle_mute(self, allow_foreground: bool = False):
        """切换消息免打扰状态"""
        return self.select_menu_option('消息免打扰', allow_foreground=allow_foreground)

    def open_in_separate_window(self, allow_foreground: bool = False):
        """在独立窗口中打开会话"""
        return self.select_menu_option('在独立窗口打开', allow_foreground=allow_foreground)

    def hide(self, allow_foreground: bool = False):
        """不显示聊天"""
        return self.select_menu_option('不显示聊天', allow_foreground=allow_foreground)

    def delete(self, allow_foreground: bool = False):
        """删除聊天"""
        return self.select_menu_option('删除聊天', allow_foreground=allow_foreground)

class SearchResultElement:
    def __init__(self, control):
        self.control = control
        self.content = control.Name
        self.type = control.ClassName

    def __repr__(self):
        content = str(self.content).replace('\n', ' ')
        if len(content) > 5:
            content = content[:5] + '...'
        return f"<superwx4 Search Element({content})>"

    def get_all_text(self):
        return [
            line for line in str(self.content).split('\n')
            if line and line.strip()
        ]

    def click(self, allow_foreground: bool = False):
        uia.RollIntoView(self.control.GetParentControl(), self.control)
        driver = get_driver()
        return driver.click(self.control, reason='search result click',
                            allow_foreground=allow_foreground)

    def close(self):
        driver = get_driver()
        driver.send_keys(self.control, '{Esc}', reason='search result close')
