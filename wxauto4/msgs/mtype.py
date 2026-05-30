from .base import (
    BaseMessage,
    HumanMessage,
)
from wxauto4 import uia
from wxauto4.ui.driver import get_driver
from wxauto4.param import (
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
import os
import re
if TYPE_CHECKING:
    from wxauto4.ui.chatbox import ChatBox


class TextMessage(BaseMessage):
    type = 'text'

    def __init__(
            self,
            control: uia.Control,
            parent: "ChatBox",
            additonal_attr: Dict[str, Any]={}
        ):
        super().__init__(control, parent, additonal_attr)

class QuoteMessage(BaseMessage):
    type = 'quote'
    repattern = r"^(.*?) \n引用 (.*?) 的消息 : (.*?)$"

    def __init__(
            self,
            control: uia.Control,
            parent: "ChatBox",
            additonal_attr: Dict[str, Any]={}
        ):
        super().__init__(control, parent, additonal_attr)
        self.content, self.quote_nickname, self.quote_content = \
            re.findall(self.repattern, self.content, re.DOTALL)[0]

    def download_quote_image(self, dir_path=None, timeout=10):
        """下载引用消息中的图片

        Args:
            dir_path (str): 保存目录
            timeout (int): 超时时间

        Returns:
            WxResponse

        Note:
            MEDIUM 风险。需要点击引用消息触发图片加载。
        """
        return WxResponse.failure('not implemented: QuoteMessage.download_quote_image')
        
class VoiceMessage(BaseMessage):
    type = 'voice'

    def __init__(
            self,
            control: uia.Control,
            parent: "ChatBox",
            additonal_attr: Dict[str, Any]={}
        ):
        super().__init__(control, parent, additonal_attr)

    def to_text(self):
        """将语音消息转为文字

        Returns:
            WxResponse: data 包含 text 字段

        Note:
            LOW 风险。只读转换。
        """
        return WxResponse.failure('not implemented: VoiceMessage.to_text')

class ImageMessage(BaseMessage):
    type = 'image'

    def __init__(
            self,
            control: uia.Control,
            parent: "ChatBox",
            additonal_attr: Dict[str, Any]={}
        ):
        super().__init__(control, parent, additonal_attr)

    def download(self, dir_path=None, original=False):
        """下载图片

        Args:
            dir_path (str): 保存目录
            original (bool): 是否下载原图

        Returns:
            WxResponse

        Note:
            MEDIUM 风险。可能需要点击图片触发下载。
        """
        return WxResponse.failure('not implemented: ImageMessage.download')

    def ocr(self, timeout=3):
        """图片 OCR 识别

        Args:
            timeout (int): 超时时间

        Returns:
            WxResponse

        Note:
            MEDIUM 风险。可能需要打开图片查看器。
        """
        return WxResponse.failure('not implemented: ImageMessage.ocr')

class VideoMessage(BaseMessage):
    type = 'video'
    repattern = r'视频(\d+):(\d+)'

    def __init__(
            self,
            control: uia.Control,
            parent: "ChatBox",
            additonal_attr: Dict[str, Any]={}
        ):
        super().__init__(control, parent, additonal_attr)

    def download(self, dir_path=None, original=False, timeout=10):
        """下载视频

        Args:
            dir_path (str): 保存目录
            original (bool): 是否下载原视频
            timeout (int): 超时时间

        Returns:
            WxResponse

        Note:
            MEDIUM 风险。可能需要点击视频触发下载。
        """
        return WxResponse.failure('not implemented: VideoMessage.download')

class FileMessage(BaseMessage):
    type = 'file'
    repattern = r"^文件\n([^\n]+)\n(\d+(\.\d+)?)(B|KB|MB|GB|TB)\n微信电脑版$"

    def __init__(
            self,
            control: uia.Control,
            parent: "ChatBox",
            additonal_attr: Dict[str, Any]={}
        ):
        super().__init__(control, parent, additonal_attr)

    def download(self, dir_path=None, force_click=False, timeout=10):
        """下载文件

        Args:
            dir_path (str): 保存目录
            force_click (bool): 是否强制点击下载
            timeout (int): 超时时间

        Returns:
            WxResponse

        Note:
            MEDIUM 风险。可能需要点击文件触发下载。
        """
        return WxResponse.failure('not implemented: FileMessage.download')

class OtherMessage(BaseMessage):
    type = 'other'

    def __init__(
            self,
            control: uia.Control,
            parent: "ChatBox",
            additonal_attr: Dict[str, Any]={}
        ):
        super().__init__(control, parent, additonal_attr)


class TimeMessage(BaseMessage):
    """时间分隔消息"""
    type = 'time'

    def __init__(
            self,
            control: uia.Control,
            parent: "ChatBox",
            additonal_attr: Dict[str, Any]={}
        ):
        super().__init__(control, parent, additonal_attr)


class LocationMessage(BaseMessage):
    """位置消息"""
    type = 'location'

    def __init__(
            self,
            control: uia.Control,
            parent: "ChatBox",
            additonal_attr: Dict[str, Any]={}
        ):
        super().__init__(control, parent, additonal_attr)


class LinkMessage(BaseMessage):
    """链接消息"""
    type = 'link'

    def __init__(
            self,
            control: uia.Control,
            parent: "ChatBox",
            additonal_attr: Dict[str, Any]={}
        ):
        super().__init__(control, parent, additonal_attr)

    def get_url(self, timeout=10):
        """获取链接 URL

        Args:
            timeout (int): 超时时间

        Returns:
            WxResponse: data 包含 url 字段

        Note:
            LOW 风险。只读。
        """
        return WxResponse.failure('not implemented: LinkMessage.get_url')


class EmotionMessage(BaseMessage):
    """表情消息"""
    type = 'emotion'

    def __init__(
            self,
            control: uia.Control,
            parent: "ChatBox",
            additonal_attr: Dict[str, Any]={}
        ):
        super().__init__(control, parent, additonal_attr)


class MergeMessage(BaseMessage):
    """合并转发消息"""
    type = 'merge'

    def __init__(
            self,
            control: uia.Control,
            parent: "ChatBox",
            additonal_attr: Dict[str, Any]={}
        ):
        super().__init__(control, parent, additonal_attr)


class PersonalCardMessage(BaseMessage):
    """个人名片消息"""
    type = 'personal_card'

    def __init__(
            self,
            control: uia.Control,
            parent: "ChatBox",
            additonal_attr: Dict[str, Any]={}
        ):
        super().__init__(control, parent, additonal_attr)

    def add_friend(self, addmsg=None, remark=None, tags=None, permission="朋友圈", timeout=3):
        """通过名片添加好友

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
            'dry_run: PersonalCardMessage.add_friend 不会真实执行。'
            '需要显式 allow_foreground=True 以执行。',
            data={'method': 'PersonalCardMessage.add_friend', 'dry_run': True, 'risk': 'HIGH'},
        )


class NoteMessage(BaseMessage):
    """笔记消息"""
    type = 'note'

    def __init__(
            self,
            control: uia.Control,
            parent: "ChatBox",
            additonal_attr: Dict[str, Any]={}
        ):
        super().__init__(control, parent, additonal_attr)

    def get_content(self):
        """获取笔记内容

        Returns:
            WxResponse: data 包含 content 字段

        Note:
            LOW 风险。只读。
        """
        return WxResponse.failure('not implemented: NoteMessage.get_content')

    def save_files(self, dir_path=None):
        """保存笔记中的文件

        Args:
            dir_path (str): 保存目录

        Returns:
            WxResponse

        Note:
            MEDIUM 风险。可能需要点击触发下载。
        """
        return WxResponse.failure('not implemented: NoteMessage.save_files')

    def to_markdown(self, dir_path=None):
        """将笔记转换为 Markdown

        Args:
            dir_path (str): 保存目录

        Returns:
            WxResponse

        Note:
            LOW 风险。基于已解析内容生成。
        """
        return WxResponse.failure('not implemented: NoteMessage.to_markdown')