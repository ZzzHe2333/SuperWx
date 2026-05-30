from .base import (
    BaseMessage,
    HumanMessage
)
from superwx4 import uia
from superwx4.ui.driver import get_driver
from superwx4.param import (
    WxParam,
    WxResponse,
    PROJECT_NAME
)

from typing import (
    Dict, 
    List, 
    Any,
    TYPE_CHECKING
)
if TYPE_CHECKING:
    from superwx4.ui.chatbox import ChatBox

class SystemMessage(BaseMessage):
    attr = 'system'
    
    def __init__(
            self, 
            control: uia.Control, 
            parent: "ChatBox",
            additonal_attr: Dict[str, Any]={}
        ):
        super().__init__(control, parent, additonal_attr)
        self.sender = 'system'
        self.sender_remark = 'system'

class FriendMessage(HumanMessage):
    attr = 'friend'

    def __init__(
            self, 
            control: uia.Control, 
            parent: "ChatBox",
            additonal_attr: Dict[str, Any]={}
        ):
        super().__init__(control, parent, additonal_attr)

    def _click(self, x, y, right=False):
        self.roll_into_view()
        if right:
            self.control.RightClick(x=x, y=y, ratioX=0, ratioY=0)
        else:
            self.control.Click(ratioX=0, ratioY=0)

    @property
    def _bias(self):
        return WxParam.DEFAULT_MESSAGE_XBIAS

    def sender_info(self):
        """获取消息发送者详细信息

        Returns:
            WxResponse: data 包含发送者资料

        Note:
            LOW 风险。只读。
        """
        return WxResponse.failure('not implemented: FriendMessage.sender_info')

    def delete_friend(self, block=False, dry_run=True, allow_foreground=False):
        """删除消息发送者好友

        Args:
            block (bool): 是否同时拉黑
            dry_run (bool): 默认 True，不真实执行
            allow_foreground (bool): 默认 False

        Returns:
            WxResponse

        Note:
            HIGH 风险。默认 dry_run=True。
        """
        if not allow_foreground:
            return WxResponse.failure(
                'dry_run: FriendMessage.delete_friend 不会真实执行。'
                '需要显式 allow_foreground=True 以执行。',
                data={'method': 'FriendMessage.delete_friend', 'dry_run': True, 'risk': 'HIGH'},
            )
        return WxResponse.failure('not implemented: FriendMessage.delete_friend')

    def add_friend(self, addmsg=None, remark=None, tags=None, permission="朋友圈", timeout=3):
        """通过消息发送者添加好友

        Args:
            addmsg (str): 验证消息
            remark (str): 备注名
            tags (str|list): 标签
            permission (str): 朋友圈权限
            timeout (int): 超时时间

        Returns:
            WxResponse

        Note:
            HIGH 风险。默认 dry_run=True。
        """
        return WxResponse.failure(
            'dry_run: FriendMessage.add_friend 不会真实执行。'
            '需要显式 allow_foreground=True 以执行。',
            data={'method': 'FriendMessage.add_friend', 'dry_run': True, 'risk': 'HIGH'},
        )


class SelfMessage(HumanMessage):
    attr = 'self'

    def __init__(
            self, 
            control: uia.Control, 
            parent: "ChatBox",
            additonal_attr: Dict[str, Any]={}
        ):
        super().__init__(control, parent, additonal_attr)

    def _click(self, x, y, right=False):
        self.roll_into_view()
        if right:
            self.control.RightClick(x=x, y=y, ratioX=1, ratioY=0)
        else:
            self.control.Click(x=x, y=y, ratioX=1, ratioY=0)

    @property
    def _bias(self):
        return -WxParam.DEFAULT_MESSAGE_XBIAS