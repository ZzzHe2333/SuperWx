from typing import Literal
import os

PROJECT_NAME = 'superwx4'

class WxParam:
    # 语言设置
    LANGUAGE: Literal['cn', 'cn_t', 'en'] = 'cn'

    # 是否启用日志文件
    ENABLE_FILE_LOGGER: bool = True

    # 下载文件/图片默认保存路径
    DEFAULT_SAVE_PATH: str = os.path.join(os.getcwd(), 'superwx4文件下载')

    # 是否启用消息哈希值用于辅助判断消息，开启后会稍微影响性能
    MESSAGE_HASH: bool = False

    # 头像到消息X偏移量，用于消息定位，点击消息等操作
    DEFAULT_MESSAGE_XBIAS = 51
    DEFAULT_MESSAGE_YBIAS = 30

    # 是否强制重新自动获取X偏移量，如果设置为True，则每次启动都会重新获取
    FORCE_MESSAGE_XBIAS: bool = False

    # 监听消息时间间隔，单位秒
    LISTEN_INTERVAL: int = 1

    # 监听执行器线程池大小
    LISTENER_EXCUTOR_WORKERS: int = 4

    # 搜索聊天对象超时时间，单位秒
    SEARCH_CHAT_TIMEOUT: int = 2

    # 微信笔记加载超时时间，单位秒
    NOTE_LOAD_TIMEOUT: int = 30

    # 发送文件超时时间，单位秒
    SEND_FILE_TIMEOUT: int = 10

    # 聊天窗口大小
    CHAT_WINDOW_SIZE: tuple = (800, 6000)

    # 发送内容比例
    SEND_CONTENT_RATIO: float = 0.9

    # 获取下一条消息的最大数量和最大运行时间
    GET_NEXT_MAX_QUANTITY: int = 30
    GET_NEXT_MAX_RUNTIME: int = 10

    # 特殊会话名称
    SPECIAL_SESSION_NAME: list = ["公众号", "折叠的聊天", "QQ邮箱提醒", "服务号"]

    # 回调停止标志
    CALLBACK_STOP_SIGN: str = "stop"

    # 输入@间隔时间
    INPUT_AT_INTERVAL: float = 0.5

    # 默认表情列表
    DEFAULT_STICKERS: list = [
        "[微笑]", "[撇嘴]", "[色]", "[发呆]", "[得意]", "[流泪]", "[害羞]", "[闭嘴]", "[睡]", "[大哭]",
        "[尴尬]", "[发怒]", "[调皮]", "[呲牙]", "[惊讶]", "[难过]", "[囧]", "[抓狂]", "[吐]", "[偷笑]",
        "[愉快]", "[白眼]", "[傲慢]", "[困]", "[惊恐]", "[憨笑]", "[悠闲]", "[咒骂]", "[疑问]", "[嘘]",
        "[晕]", "[衰]", "[骷髅]", "[敲打]", "[再见]", "[擦汗]", "[抠鼻]", "[鼓掌]", "[坏笑]",
        "[爱心]", "[拥抱]", "[强]", "[弱]", "[握手]", "[胜利]", "[OK]", "[合十]",
        "[蛋糕]", "[玫瑰]", "[礼物]", "[红包]",
    ]

    # 后台优先操作模式
    BACKGROUND_MODE: bool = True
    ALLOW_FOREGROUND_FALLBACK: bool = False
    FOREGROUND_LEASE_SECONDS: int = 3
    RESTORE_MOUSE_POSITION: bool = True
    RESTORE_FOREGROUND_WINDOW: bool = True

class WxResponse(dict):
    def __init__(self, status: str, message: str, data: dict = None):
        super().__init__(status=status, message=message, data=data)

    def __str__(self):
        return str(self.to_dict())
    
    def __repr__(self):
        return str(self.to_dict())

    def to_dict(self):
        return {
            'status': self['status'],
            'message': self['message'],
            'data': self['data']
        }

    def __bool__(self):
        return self.is_success
    
    @property
    def is_success(self):
        return self['status'] == '成功'

    @classmethod
    def success(cls, message=None, data: dict = None):
        return cls(status="成功", message=message, data=data)

    @classmethod
    def failure(cls, message: str, data: dict = None):
        return cls(status="失败", message=message, data=data)

    @classmethod
    def error(cls, message: str, data: dict = None):
        return cls(status="错误", message=message, data=data)