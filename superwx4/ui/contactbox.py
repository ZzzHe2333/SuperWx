"""ContactBox - 联系人页面交互

提供联系人列表的只读采集能力。
"""

import time
import json
import os
from typing import List, Dict, Optional, TYPE_CHECKING

from superwx4 import uia
from superwx4.param import WxResponse
from superwx4.utils.win32 import Click as Win32Click, set_cursor_pos

if TYPE_CHECKING:
    from superwx4.ui.main import WeChatMainWnd


class ContactBox:
    """联系人页面交互类"""

    # 联系人列表控件标识
    CONTACT_LIST_AID = 'primary_table_.contact_list'
    CONTACT_ITEM_CLASS = 'mmui::ContactsCellItemView'
    CONTACT_GROUP_CLASS = 'mmui::ContactsCellGroupView'
    CONTACT_CLASSIFY_CLASS = 'mmui::ContactsCellClassifyView'

    # 分组标题（不是联系人）
    GROUP_TITLES = {'群聊', '公众号', '服务号', '企业微信联系人', '联系人',
                    '新的朋友', '标签', '公众号'}

    def __init__(self, root: "WeChatMainWnd"):
        self.root = root
        self.control = root.control

    def _navigate_to_contacts(self) -> bool:
        """切换到联系人页面"""
        try:
            btn = self.control.ButtonControl(Name='通讯录')
            if btn.Exists(0):
                rect = btn.BoundingRectangle
                cx = int((rect.left + rect.right) / 2)
                cy = int((rect.top + rect.bottom) / 2)
                set_cursor_pos(cx, cy)
                time.sleep(0.1)
                Win32Click(uia.Rect(cx, cy, cx + 1, cy + 1))
                time.sleep(1.5)
                return True
        except Exception:
            pass
        return False

    def _find_contact_list(self) -> Optional[uia.Control]:
        """定位联系人列表控件"""
        try:
            # Navigate through the control tree to find contact list
            outer_main = self.control.GroupControl(AutomationId='MainView')
            if not outer_main.Exists(0):
                return None

            inner_container = outer_main.GetChildren()[1]
            inner_main = inner_container.GetChildren()[0]
            splitter = inner_main.GetChildren()[0]
            stacked = splitter.GetChildren()[0]
            sub_splitter = stacked.GetChildren()[0]
            xview = sub_splitter.GetChildren()[1]
            inner_xview = xview.GetChildren()[0]
            contact_table = inner_xview.GetChildren()[1]

            if contact_table.AutomationId != 'primary_table_':
                return None

            # Find the list control inside
            for child in contact_table.GetChildren():
                if child.ControlTypeName == 'ListControl':
                    return child

        except Exception:
            pass
        return None

    def _extract_contacts_from_list(self, contact_list: uia.Control) -> List[Dict]:
        """从列表控件中提取联系人信息"""
        contacts = []
        try:
            for item in contact_list.GetChildren():
                try:
                    cls = item.ClassName or ''
                    name = item.Name or ''

                    if cls == self.CONTACT_CLASSIFY_CLASS:
                        # 字母分组标题，跳过
                        continue

                    if cls == self.CONTACT_GROUP_CLASS:
                        # 功能分组（群聊、公众号等），跳过
                        continue

                    if cls == self.CONTACT_ITEM_CLASS:
                        # 联系人项
                        if not name or not name.strip():
                            continue

                        # 解析联系人信息
                        # Name 格式通常是: nickname + remark + 其他信息
                        # 例如: 'Aa清濛旗达红旗_小凤18876549496'
                        contact = {
                            'nickname': name.strip(),
                            'raw_name': name,
                            'class_name': cls,
                            'automation_id': item.AutomationId or '',
                            'control_type': item.ControlTypeName,
                            'rect': {
                                'left': item.BoundingRectangle.left,
                                'top': item.BoundingRectangle.top,
                                'right': item.BoundingRectangle.right,
                                'bottom': item.BoundingRectangle.bottom,
                                'width': item.BoundingRectangle.width(),
                                'height': item.BoundingRectangle.height(),
                            },
                            'source': 'contact_list',
                        }
                        contacts.append(contact)

                except Exception:
                    continue

        except Exception:
            pass

        return contacts

    def _is_group_title(self, name: str) -> bool:
        """判断是否为功能分组标题"""
        if not name:
            return True
        # 去掉数字后缀（如 '群聊5' -> '群聊'）
        import re
        base = re.sub(r'\d+$', '', name.strip())
        return base in self.GROUP_TITLES

    def get_all_contacts(
        self,
        max_scroll: int = 200,
        interval: float = 0.2,
        stop_on_repeat: int = 3,
    ) -> WxResponse:
        """获取所有联系人（只读）

        Args:
            max_scroll: 最大滚动次数
            interval: 每次滚动间隔
            stop_on_repeat: 连续无新增时停止

        Returns:
            WxResponse: data 包含 contacts 列表
        """
        # Step 1: Navigate to contacts page
        if not self._navigate_to_contacts():
            return WxResponse.failure('切换到联系人页面失败')

        # Step 2: Find contact list
        contact_list = self._find_contact_list()
        if contact_list is None:
            return WxResponse.failure('未找到联系人列表控件')

        # Step 3: Scroll to top first (list may start at bottom of alphabet)
        for _ in range(20):
            contact_list.WheelUp(wheelTimes=5)
            time.sleep(0.3)
        time.sleep(1)

        # Step 4: Collect contacts by scrolling down
        seen_names = set()
        all_contacts = []
        stale_rounds = 0

        for round_num in range(max_scroll):
            # Read current visible contacts
            visible = self._extract_contacts_from_list(contact_list)
            new_count = 0

            for contact in visible:
                name = contact['nickname']
                if name and name not in seen_names:
                    seen_names.add(name)
                    all_contacts.append(contact)
                    new_count += 1

            # Check stop conditions
            if new_count == 0:
                stale_rounds += 1
                if stale_rounds >= stop_on_repeat:
                    break
            else:
                stale_rounds = 0

            # Scroll down
            try:
                contact_list.WheelDown(waitTime=interval, wheelTimes=3)
                time.sleep(interval)
            except Exception:
                break

        return WxResponse.success(data={
            'contacts': all_contacts,
            'total': len(all_contacts),
        })
# 1
