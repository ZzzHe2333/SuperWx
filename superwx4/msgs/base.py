from superwx4 import uia
from superwx4.ui.component import (
    Menu,
    SelectContactWnd
)
from superwx4.ui.driver import get_driver
from superwx4.utils import uilock
from superwx4.param import WxParam, WxResponse, PROJECT_NAME
from abc import ABC, abstractmethod
from typing import (
    Dict,
    List,
    Union,
    Any,
    TYPE_CHECKING,
    Iterator,
    Tuple
)
from hashlib import md5
import time

if TYPE_CHECKING:
    from superwx4.ui.chatbox import ChatBox

def truncate_string(s: str, n: int=8) -> str:
    s = s.replace('\n', '').strip()
    return s if len(s) <= n else s[:n] + '...'

class Message:
    """消息对象基类

    该类不会直接实例化，而是作为所有消息类型的基类提供
    常用的工具方法。实际的属性均由子类在 ``__init__`` 中
    动态注入。
    """

    _EXCLUDE_FIELDS = {"control", "parent", "root"}

    # region --- 迭代/映射相关 -------------------------------------------------
    def _iter_public_items(self) -> Iterator[Tuple[str, Any]]:
        """遍历当前消息可公开的字段"""

        if not hasattr(self, "__dict__"):
            return

        for key, value in self.__dict__.items():
            if key.startswith("_") or key in self._EXCLUDE_FIELDS:
                continue
            if key == "hash" and not WxParam.MESSAGE_HASH:
                continue
            yield key, value

    def __iter__(self) -> Iterator[str]:
        for key, _ in self._iter_public_items():
            yield key

    def __len__(self) -> int:
        return sum(1 for _ in self._iter_public_items())

    def __getitem__(self, item: str) -> Any:
        for key, value in self._iter_public_items():
            if key == item:
                return value
        raise KeyError(item)

    def __contains__(self, key: object) -> bool:
        if not isinstance(key, str):
            return False
        return any(field == key for field, _ in self._iter_public_items())

    # endregion ----------------------------------------------------------------

    # region --- 字段访问 -------------------------------------------------------
    def keys(self) -> Tuple[str, ...]:
        return tuple(key for key, _ in self._iter_public_items())

    def values(self) -> Tuple[Any, ...]:
        return tuple(value for _, value in self._iter_public_items())

    def items(self) -> Tuple[Tuple[str, Any], ...]:
        return tuple(self._iter_public_items())

    def get(self, key: str, default: Any = None) -> Any:
        for field, value in self._iter_public_items():
            if field == key:
                return value
        return default

    def to_dict(self) -> Dict[str, Any]:
        return dict(self._iter_public_items())

    def copy(self) -> Dict[str, Any]:
        return self.to_dict().copy()

    # endregion ----------------------------------------------------------------

    # region --- 信息访问 -------------------------------------------------------
    @property
    def info(self) -> Dict[str, Any]:
        """消息基本信息（官方接口兼容）"""
        return self.to_dict()

    def chat_info(self) -> "WxResponse":
        """获取消息所属会话信息

        Returns:
            WxResponse: data 包含 who, chat_type 字段

        Note:
            LOW 风险。只读。
        """
        parent = getattr(self, 'parent', None)
        if parent is None:
            return WxResponse.failure('无法获取会话信息：parent 不存在')
        who = getattr(parent, 'who', None)
        chat_type = getattr(parent, 'chat_type', None)
        return WxResponse.success(data={'who': who, 'chat_type': chat_type})

    # endregion ----------------------------------------------------------------

    # region --- 状态判断 -------------------------------------------------------
    def match(self, **conditions: Any) -> bool:
        """判断当前消息是否同时满足给定的字段条件"""

        data = self.to_dict()
        return all(data.get(key) == value for key, value in conditions.items())

    @property
    def is_self(self) -> bool:
        return getattr(self, "attr", None) == "self"

    @property
    def is_friend(self) -> bool:
        return getattr(self, "attr", None) == "friend"

    @property
    def is_system(self) -> bool:
        return getattr(self, "attr", None) == "system"

    # endregion ----------------------------------------------------------------

    # region --- 魔术方法 -------------------------------------------------------
    def __str__(self) -> str:
        content = getattr(self, "content", None)
        if content is None:
            return super().__str__()
        return str(content)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Message):
            return NotImplemented

        self_id = getattr(self, "id", None)
        other_id = getattr(other, "id", None)
        if self_id is not None and other_id is not None:
            return self_id == other_id

        if WxParam.MESSAGE_HASH:
            return getattr(self, "hash", None) == getattr(other, "hash", None)

        return self is other

    def __hash__(self) -> int:
        msg_id = getattr(self, "id", None)
        if msg_id is not None:
            return hash(msg_id)

        if WxParam.MESSAGE_HASH:
            return hash(getattr(self, "hash", None))

        return super().__hash__()

    # endregion ----------------------------------------------------------------

class BaseMessage(Message, ABC):
    type: str = 'base'
    attr: str = 'base'
    control: uia.Control

    def __init__(
            self, 
            control: uia.Control, 
            parent: "ChatBox",
            additonal_attr: Dict[str, Any]={}
        ):
        self.parent = parent
        self.control = control
        self.direction = additonal_attr.get('direction', None)
        self.distince = additonal_attr.get('direction_distence', None)
        self.root = parent.root
        self.id = self.control.runtimeid
        self.content = self.control.Name
        rect = self.control.BoundingRectangle
        self.hash_text = f'({rect.height()},{rect.width()}){self.content}'
        self.hash = md5(self.hash_text.encode()).hexdigest()

    def __repr__(self):
        cls_name = self.__class__.__name__
        content = truncate_string(self.content)
        return f"<{PROJECT_NAME} - {cls_name}({content}) at {hex(id(self))}>"
    
    def roll_into_view(self):
        if not self.exists():
            return WxResponse.failure('消息目标控件不存在，无法滚动至显示窗口')
        if uia.RollIntoView(
            self.parent.msgbox, 
            self.control
        ) == 'not exist':
            return WxResponse.failure('消息目标控件不存在，无法滚动至显示窗口')
        return WxResponse.success('成功')
    
    def exists(self):
        if self.control.Exists(0) and self.control.BoundingRectangle.height() > 0:
            return True
        return False
    


class HumanMessage(BaseMessage, ABC):
    attr = 'human'

    def __init__(
            self, 
            control: uia.Control, 
            parent: "ChatBox",
            additonal_attr: Dict[str, Any]={}
        ):
        super().__init__(control, parent, additonal_attr)

    @abstractmethod
    def _click(self, x, y, right=False):...

    @abstractmethod
    def _bias(self):...

    def click(self):
        driver = get_driver()
        result = driver.click(self.control, reason='message click')
        if not result.is_success:
            self._click(right=False, x=self._bias*2, y=WxParam.DEFAULT_MESSAGE_YBIAS)

    def right_click(self):
        self._click(right=True, x=self._bias, y=WxParam.DEFAULT_MESSAGE_YBIAS)

    def _find_body_controls(self):
        """查找消息内部的文本/气泡子控件"""
        rect = self.control.BoundingRectangle
        candidates = []
        for child, _ in uia.WalkControl(self.control, maxDepth=5):
            ctype = child.ControlTypeName
            cname = child.ClassName or ''
            if ctype in ('TextControl', 'DocumentControl'):
                try:
                    cr = child.BoundingRectangle
                    if cr.width() > 10 and cr.height() > 10:
                        candidates.append(child)
                except:
                    pass
            elif 'ChatText' in cname or 'Bubble' in cname or 'AlbumContent' in cname:
                try:
                    cr = child.BoundingRectangle
                    if cr.width() > 10 and cr.height() > 10:
                        candidates.append(child)
                except:
                    pass
        return candidates

    def right_click_message_body(self, max_retries=3):
        """
        右键点击消息主体区域（而非头像），确保菜单包含有意义的选项。
        返回 (x_off, label, options) 或 None。
        注意：调用方需自行管理菜单（不要用 ESC 关闭，会最小化窗口）。
        """
        if not self.exists():
            return None

        self.roll_into_view()
        time.sleep(0.2)

        rect = self.control.BoundingRectangle
        rw, rh = rect.width(), rect.height()

        # 生成候选 x 偏移（相对于控件左上角，ratioX=0）
        # 基于实测：friend message x=51 点到头像，x=100 点到消息体
        offsets = []
        if self.is_self:
            # self message: 用 ratioX=1, x 为负偏移（从右边算）
            offsets = [
                (-int(rw * 0.35), 'self_35pct', 1),
                (-int(rw * 0.25), 'self_25pct', 1),
                (-120, 'self_120px', 1),
            ]
        else:
            # friend message: 用 ratioX=0, x 为正偏移（从左边算）
            # 头像区域约 50px，需要 > 60 才能避开
            offsets = [
                (max(100, int(rw * 0.15)), 'friend_15pct', 0),
                (max(120, int(rw * 0.25)), 'friend_25pct', 0),
                (max(150, int(rw * 0.35)), 'friend_35pct', 0),
            ]

        AVATAR_ONLY_OPTIONS = {'拍一拍'}

        driver = get_driver()
        for x_off, label, ratio_x in offsets[:max_retries]:
            driver.right_click(
                self.control, x=x_off, y=27, ratioX=ratio_x, ratioY=0,
                reason=f'message body right_click ({label})',
                allow_foreground=True,
            )
            time.sleep(0.4)

            menu = Menu(self, timeout=2)
            if not menu.exists(0):
                continue

            options = menu.option_names
            if options and set(options) != AVATAR_ONLY_OPTIONS:
                return (x_off, label, options)
            # 只有"拍一拍"，点到了头像，按 ESC 关闭菜单再试
            # 注意：ESC 可能最小化窗口，这里用点击空白区域代替
            # 但由于控件可能已失效，这里直接返回失败让调用方处理
            return None

        return None

    @uilock
    def select_option(self, option: str, timeout=2) -> WxResponse:
        if not self.exists():
            return WxResponse.failure('消息对象已失效')
        result = self.right_click_message_body()
        if result is None:
            return WxResponse.failure(
                f'未找到"{option}"选项，可能点击位置仍在头像或该消息不支持该操作'
            )
        x_off, label, options = result
        # right_click_message_body 已打开菜单，直接查找选项
        menu = Menu(self, timeout=timeout)
        if menu.exists(0):
            return menu.select(option)
        return WxResponse.failure('菜单已消失，操作失败')

    @uilock
    def forward(
        self, 
        targets: Union[List[str], str], 
        timeout: int = 3,
        interval: float = 0.1
    ) -> WxResponse:
        """转发消息

        Args:
            targets (Union[List[str], str]): 目标用户列表
            timeout (int, optional): 超时时间，单位为秒，若为None则不启用超时设置
            interval (float): 选择联系人时间间隔

        Returns:
            WxResponse: 调用结果
        """
        if not self.exists():
            return WxResponse.failure('消息对象已失效')
        if not self.select_option('转发...', timeout=timeout):
            return WxResponse.failure('当前消息无法转发')
        
        select_wnd = SelectContactWnd(self)
        return select_wnd.send(targets, interval=interval)
    
    def tickle(self):
        """拍一拍消息发送者

        Returns:
            WxResponse

        Note:
            MEDIUM 风险。需要点击消息触发拍一拍。
        """
        return WxResponse.failure('not implemented: HumanMessage.tickle')

    def download_head_image(self, dir_path=None):
        """下载消息发送者头像

        Args:
            dir_path (str): 保存目录

        Returns:
            WxResponse

        Note:
            MEDIUM 风险。可能需要点击头像触发加载。
        """
        return WxResponse.failure('not implemented: HumanMessage.download_head_image')

    def edit_info(self, remark=None, tags=None, permission=None):
        """编辑消息发送者信息

        Args:
            remark (str): 备注名
            tags (str|list): 标签
            permission (str): 朋友圈权限

        Returns:
            WxResponse

        Note:
            HIGH 风险。默认 dry_run=True。
        """
        return WxResponse.failure(
            'dry_run: HumanMessage.edit_info 不会真实执行。'
            '需要显式 allow_foreground=True 以执行。',
            data={'method': 'HumanMessage.edit_info', 'dry_run': True, 'risk': 'HIGH'},
        )

    @uilock
    def quote(
            self, text: str,
            at: Union[List[str], str] = None,
            timeout: int = 3
        ) -> WxResponse:
        """引用消息
        
        Args:
            text (str): 引用内容
            at (List[str], optional): @用户列表
            timeout (int, optional): 超时时间，单位为秒，若为None则不启用超时设置

        Returns:
            WxResponse: 调用结果
        """
        if not self.exists():
            return WxResponse.failure('消息对象已失效')
        if not self.select_option('引用', timeout=timeout):
            return WxResponse.failure('当前消息无法引用')
        
        if at:
            self.parent.input_at(at)

        return self.parent.send_text(text)
# 1
