from wxauto4.ui.base import BaseUISubWnd, BaseUIWnd
from wxauto4.ui import WeChatMainWnd, WeChatSubWnd
from wxauto4.logger import wxlog
from wxauto4.param import WxParam, WxResponse, PROJECT_NAME
from wxauto4.utils import GetAllWindows, uilock
from wxauto4.utils.tools import delete_update_files
from wxauto4.moment import Moment
from concurrent.futures import ThreadPoolExecutor
from abc import ABC, abstractmethod
import threading
import traceback
import time
import sys
import os
from typing import (
    Callable,
    TYPE_CHECKING,
    Union, 
    List,
    Dict,
    Literal,
    Optional,
)
if TYPE_CHECKING:
    from wxauto4.msgs.base import Message
    from wxauto4.ui.sessionbox import SessionElement

class Listener(ABC):
    def _listener_start(self):
        wxlog.debug('开始监听')
        self._listener_is_listening = True
        self._listener_messages = {}
        self._lock = threading.RLock()
        self._listener_stop_event = threading.Event()
        self._listener_thread = threading.Thread(target=self._listener_listen, daemon=True)
        self._listener_thread.start()

    def _listener_listen(self):
        self._excutor = ThreadPoolExecutor(max_workers=WxParam.LISTENER_EXCUTOR_WORKERS)
        if not hasattr(self, 'listen') or not self.listen:
            self.listen = {}
        while not self._listener_stop_event.is_set():
            delete_update_files()
            try:
                self._get_listen_messages()
            except KeyboardInterrupt:
                wxlog.debug("监听消息终止")
                self._listener_stop()
                break
            except:
                wxlog.debug(f'监听消息失败：{traceback.format_exc()}')
            time.sleep(WxParam.LISTEN_INTERVAL)

    def _safe_callback(
            self, 
            callback: Callable[['Message', 'Chat'], None], 
            msg: 'Message', 
            chat: 'Chat'
        ):
        try:
            callback(msg, chat)
        except Exception as e:
            wxlog.debug(f"监听消息回调发生错误：{traceback.format_exc()}")

    def _listener_stop(self):
        self._listener_is_listening = False
        self._listener_stop_event.set()
        self._listener_thread.join()
        self._excutor.shutdown(wait=True)

    @abstractmethod
    def _get_listen_messages(self):
        ...

class Chat:
    """微信聊天窗口实例"""

    def __init__(self, core: WeChatSubWnd=None):
        self._api = core
        self.who = self._api.nickname

    @property
    def chat_type(self) -> str:
        """聊天类型（官方接口兼容）"""
        info = self.ChatInfo()
        return info.get('chat_type', 'unknown')

    def __repr__(self):
        return f'<{PROJECT_NAME} - {self.__class__.__name__} object("{self._api.nickname}")>'

    def __str__(self):
        if hasattr(self, 'who'):
            return self.who
        else:
            return self.nickname
    
    def __add__(self, other):
        if hasattr(self, 'who'):
            return self.who + other
        else:
            return self.nickname + other

    def __radd__(self, other):
        if hasattr(self, 'who'):
            return other + self.who
        else:
            return other + self.nickname
        
    def Show(self, allow_foreground: bool = False):
        """显示窗口

        Args:
            allow_foreground (bool): 是否允许前台操作，默认 False

        Returns:
            WxResponse

        Note:
            MEDIUM 风险。会激活窗口。
        """
        if not allow_foreground:
            return WxResponse.failure(
                'foreground required: Show() 需要前台操作',
                data={'method': 'Chat.Show', 'requires_foreground': True, 'risk': 'MEDIUM'},
            )
        self._api._show()
        return WxResponse.success()

    def ChatInfo(self) -> Dict[str, str]:
        """获取聊天窗口信息
        
        Returns:
            dict: 聊天窗口信息
        """
        return self._api._chat_api.get_info()

    
    @uilock
    def SendMsg(
            self,
            msg: str,
            who: str=None,
            clear: bool=True,
            at: Union[str, List[str]]=None,
            exact: bool=False,
            allow_foreground: bool=False,
        ) -> WxResponse:
        """发送消息

        Args:
            msg (str): 消息内容
            who (str, optional): 发送对象，不指定则发送给当前聊天对象，**当子窗口时，该参数无效**
            clear (bool, optional): 发送后是否清空编辑框.
            at (Union[str, List[str]], optional): @对象，不指定则不@任何人
            exact (bool, optional): 搜索who好友时是否精确匹配，默认False，**当子窗口时，该参数无效**
            allow_foreground (bool): 是否允许前台操作，默认 False

        Returns:
            WxResponse: 是否发送成功
        """
        return self._api.send_msg(msg, who, clear, at, exact)
    
    @uilock
    def SendFiles(
            self,
            filepath,
            who=None,
            exact=False,
            allow_foreground: bool=False,
        ) -> WxResponse:
        """向当前聊天窗口发送文件

        Args:
            filepath (str|list): 要复制文件的绝对路径
            who (str): 发送对象，不指定则发送给当前聊天对象，**当子窗口时，该参数无效**
            exact (bool, optional): 搜索who好友时是否精确匹配，默认False，**当子窗口时，该参数无效**
            allow_foreground (bool): 是否允许前台操作，默认 False

        Returns:
            WxResponse: 是否发送成功
        """
        return self._api.send_files(filepath, who, exact)
    
    def GetAllMessage(self) -> List['Message']:
        """获取当前聊天窗口的所有消息
        
        Returns:
            List[Message]: 当前聊天窗口的所有消息
        """
        return self._api.get_msgs()
    
    def GetNewMessage(self) -> List['Message']:
        """获取当前聊天窗口的新消息

        Returns:
            List[Message]: 当前聊天窗口的新消息
        """
        if not hasattr(self, '_last_chat'):
            self._last_chat = self.ChatInfo().get('chat_name')
        if (_last_chat := self.ChatInfo().get('chat_name')) != self._last_chat:
            self._last_chat = _last_chat
            self._api._chat_api._update_used_msg_ids()
            return []
        return self._api.get_new_msgs()

    def GetMessageById(self, msg_id) -> Optional['Message']:
        """根据消息 runtime id 获取消息实例"""

        return self._api.get_msg_by_id(msg_id)

    def GetMessageByHash(self, msg_hash: str) -> Optional['Message']:
        """根据消息哈希值获取消息实例"""

        return self._api.get_msg_by_hash(msg_hash)

    def GetLastMessage(self) -> Optional['Message']:
        """获取当前聊天窗口的最后一条消息"""

        return self._api.get_last_msg()

    def GetHistoryMessage(
            self,
            n: int = 50,
            callback: Callable = None,
            interval: float = 0.5,
            speed: int = 1,
            goback: bool = True,
        ) -> List['Message']:
        """向上滚动获取历史消息

        Args:
            n (int): 获取历史消息数量，默认50
            callback (Callable, optional): 每次滚动后的回调，返回True停止
            interval (float): 滚动间隔秒数，默认0.5
            speed (int): 每次滚动行数，默认1
            goback (bool): 完成后是否滚回底部，默认True

        Returns:
            List[Message]: 历史消息列表，按时间正序
        """
        return self._api.get_history_msg(n, callback, interval, speed, goback)

    def Close(self, allow_foreground: bool = False) -> WxResponse:
        """关闭聊天窗口

        Args:
            allow_foreground (bool): 是否允许前台操作，默认 False

        Returns:
            WxResponse

        Note:
            MEDIUM 风险。会关闭窗口。
        """
        if not allow_foreground:
            return WxResponse.failure(
                'foreground required: Close() 需要前台操作',
                data={'method': 'Chat.Close', 'requires_foreground': True, 'risk': 'MEDIUM'},
            )
        self._api.close()
        return WxResponse.success()

    @uilock
    def AtAll(
            self,
            msg: str = '',
            who: Union[str, List[str]] = None,
            exact: bool = False,
            dry_run: bool = True,
            allow_foreground: bool = False,
            require_confirm: bool = True,
        ) -> WxResponse:
        """@所有人

        Args:
            msg (str): 消息内容
            who (str|list, optional): 指定@对象，None 表示@所有人
            exact (bool): 是否精确匹配
            dry_run (bool): 默认 True，不真实执行
            allow_foreground (bool): 默认 False
            require_confirm (bool): 默认 True，需要确认

        Returns:
            WxResponse

        Note:
            HIGH 风险。默认 dry_run=True。
        """
        if dry_run or not allow_foreground:
            return WxResponse.success(
                data={
                    'dry_run': True,
                    'method': 'Chat.AtAll',
                    'would_do': f'@所有人: {msg!r}',
                    'requires_foreground': True,
                    'risk': 'HIGH',
                }
            )
        return WxResponse.failure('not implemented: Chat.AtAll')

    @uilock
    def SendAudio(
            self,
            filepath: str,
            duration: float = None,
            start: float = 0,
            who: str = None,
            exact: bool = False,
            max_retries: int = 3,
            dry_run: bool = True,
            allow_foreground: bool = False,
        ) -> WxResponse:
        """发送语音消息

        Args:
            filepath (str): 语音文件路径
            duration (float, optional): 语音时长（秒）
            start (float): 开始时间
            who (str, optional): 发送对象
            exact (bool): 是否精确匹配
            max_retries (int): 最大重试次数
            dry_run (bool): 默认 True，不真实执行
            allow_foreground (bool): 默认 False

        Returns:
            WxResponse

        Note:
            HIGH 风险。默认 dry_run=True。
        """
        if dry_run or not allow_foreground:
            return WxResponse.success(
                data={
                    'dry_run': True,
                    'method': 'Chat.SendAudio',
                    'would_do': f'发送语音: {filepath}',
                    'requires_foreground': True,
                    'risk': 'HIGH',
                }
            )
        return WxResponse.failure('not implemented: Chat.SendAudio')

    @uilock
    def AddGroupMembers(
            self,
            members: Union[str, List[str]],
            dry_run: bool = True,
            allow_foreground: bool = False,
            require_confirm: bool = True,
        ) -> WxResponse:
        """添加群成员

        Args:
            members (str|list): 要添加的成员
            dry_run (bool): 默认 True，不真实执行
            allow_foreground (bool): 默认 False
            require_confirm (bool): 默认 True，需要确认

        Returns:
            WxResponse

        Note:
            HIGH 风险。默认 dry_run=True。
        """
        if dry_run or not allow_foreground:
            return WxResponse.success(
                data={
                    'dry_run': True,
                    'method': 'Chat.AddGroupMembers',
                    'would_do': f'添加群成员: {members}',
                    'requires_foreground': True,
                    'risk': 'HIGH',
                }
            )
        return WxResponse.failure('not implemented: Chat.AddGroupMembers')

    def _group_setting_stub(self, method_name: str, value: str, dry_run: bool, allow_foreground: bool) -> WxResponse:
        """群设置类方法通用 stub"""
        if dry_run or not allow_foreground:
            return WxResponse.success(
                data={
                    'dry_run': True,
                    'method': f'Chat.{method_name}',
                    'would_do': f'设置为: {value!r}',
                    'requires_foreground': True,
                    'risk': 'HIGH',
                }
            )
        return WxResponse.failure(f'not implemented: Chat.{method_name}')

    @uilock
    def SetGroupName(
            self,
            value: str,
            dry_run: bool = True,
            allow_foreground: bool = False,
            require_confirm: bool = True,
        ) -> WxResponse:
        """设置群名称

        Args:
            value (str): 新群名称
            dry_run (bool): 默认 True，不真实执行
            allow_foreground (bool): 默认 False
            require_confirm (bool): 默认 True，需要确认

        Returns:
            WxResponse

        Note:
            HIGH 风险。默认 dry_run=True。
        """
        return self._group_setting_stub('SetGroupName', value, dry_run, allow_foreground)

    @uilock
    def SetGroupRemark(
            self,
            value: str,
            dry_run: bool = True,
            allow_foreground: bool = False,
            require_confirm: bool = True,
        ) -> WxResponse:
        """设置群备注

        Args:
            value (str): 新群备注
            dry_run (bool): 默认 True，不真实执行
            allow_foreground (bool): 默认 False
            require_confirm (bool): 默认 True，需要确认

        Returns:
            WxResponse

        Note:
            HIGH 风险。默认 dry_run=True。
        """
        return self._group_setting_stub('SetGroupRemark', value, dry_run, allow_foreground)

    @uilock
    def SetGroupAnnouncement(
            self,
            value: str,
            dry_run: bool = True,
            allow_foreground: bool = False,
            require_confirm: bool = True,
        ) -> WxResponse:
        """设置群公告

        Args:
            value (str): 新群公告
            dry_run (bool): 默认 True，不真实执行
            allow_foreground (bool): 默认 False
            require_confirm (bool): 默认 True，需要确认

        Returns:
            WxResponse

        Note:
            HIGH 风险。默认 dry_run=True。
        """
        return self._group_setting_stub('SetGroupAnnouncement', value, dry_run, allow_foreground)

    @uilock
    def SetGroupMyNickname(
            self,
            value: str,
            dry_run: bool = True,
            allow_foreground: bool = False,
            require_confirm: bool = True,
        ) -> WxResponse:
        """设置群内昵称

        Args:
            value (str): 新昵称
            dry_run (bool): 默认 True，不真实执行
            allow_foreground (bool): 默认 False
            require_confirm (bool): 默认 True，需要确认

        Returns:
            WxResponse

        Note:
            HIGH 风险。默认 dry_run=True。
        """
        return self._group_setting_stub('SetGroupMyNickname', value, dry_run, allow_foreground)


class WeChat(Chat, Listener):
    """微信主窗口实例"""

    def __init__(
            self,
            nickname: str = None,
            start_listener: bool = False,
            debug: bool = False,
            resize: bool = True,
            version: str = "微信",
            **kwargs
        ):
        """初始化 WeChat 实例

        Args:
            nickname (str, optional): 微信窗口昵称/标题
            start_listener (bool): 是否启动消息监听
            debug (bool): 是否开启调试模式
            resize (bool): 是否调整窗口大小
            version (str): 微信版本，"微信" 或 "WeChat"
        """
        if version not in ("微信", "WeChat"):
            wxlog.debug(f'不支持的版本: {version}，仅支持 "微信" 和 "WeChat"')
        delete_update_files()
        hwnd = None
        if 'hwnd' in kwargs:
            hwnd = kwargs['hwnd']
        self._api = WeChatMainWnd(nickname, hwnd)
        self.NavigationBox = self._api._navigation_api
        self.SessionBox = self._api._session_api
        self.ChatBox = self._api._chat_api
        self.Moment = Moment(self)
        self.nickname = self._api.nickname
        self.listen = {}
        if start_listener:
            self._listener_start()
        if debug:
            wxlog.set_debug(True)
            wxlog.debug('Debug mode is on')
        
    def _get_listen_messages(self):
        try:
            sys.stdout.flush()
        except:
            pass
        temp_listen = self.listen.copy()
        for who in temp_listen:
            chat, callback = temp_listen.get(who, (None, None))
            try:
                if chat is None or not chat._api.exists():
                    self.RemoveListenChat(who)
                    continue
            except:
                continue
            with self._lock:
                msgs = chat.GetNewMessage()
                for msg in msgs:
                    wxlog.debug(f"[{msg.attr}]获取到新消息：{who} - {msg.content}")
                    self._excutor.submit(self._safe_callback, callback, msg, chat)

    @property
    def path(self):
        return self._api._get_wx_path()
    
    @property
    def dir(self):
        return self._api._get_wx_dir()

    def KeepRunning(self):
        """保持运行"""
        while not self._listener_stop_event.is_set():
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                wxlog.debug(f'wxauto4("{self.nickname}") shutdown')
                self.StopListening(True)
                break
    
    def GetSession(self) -> List['SessionElement']:
        """获取当前会话列表

        Returns:
            List[SessionElement]: 当前会话列表
        """
        return self._api._session_api.get_session()
    
    @uilock
    def ChatWith(
        self, 
        who: str, 
        exact: bool=True,
        force: bool=False,
        force_wait: Union[float, int] = 0.5
    ):
        """打开聊天窗口
        
        Args:
            who (str): 要聊天的对象
            exact (bool, optional): 搜索who好友时是否精确匹配，默认True
            force (bool, optional): 不论是否匹配到都强制切换，若启用则exact参数无效，默认False
                > 注：force原理为输入搜索关键字后，在等待`force_wait`秒后不判断结果直接回车，谨慎使用
            force_wait (Union[float, int], optional): 强制切换时等待时间，默认0.5秒
            
        """
        return self._api.switch_chat(who, exact, force, force_wait)
    
    def GetSubWindow(self, nickname: str) -> 'Chat':
        """获取子窗口实例
        
        Args:
            nickname (str): 要获取的子窗口的昵称
            
        Returns:
            Chat: 子窗口实例
        """
        if subwin := self._api.get_sub_wnd(nickname):
            return Chat(subwin)
        
    def GetAllSubWindow(self) -> List['Chat']:
        """获取所有子窗口实例
        
        Returns:
            List[Chat]: 所有子窗口实例
        """
        return [Chat(subwin) for subwin in self._api.get_all_sub_wnds()]
    
    @uilock
    def AddListenChat(
            self,
            nickname: str,
            callback: Callable[['Message', Chat], None],
        ) -> WxResponse:
        """添加监听聊天，将聊天窗口独立出去形成Chat对象子窗口，用于监听
        
        Args:
            nickname (str): 要监听的聊天对象
            callback (Callable[['Message', Chat], None]): 回调函数，参数为(Message对象, Chat对象)，返回值为None
        """
        if not hasattr(self, '_listener_is_listening') or not self._listener_is_listening:
            wxlog.debug('检测到未开启监听器，开启监听器')
            self._listener_start()
        if nickname in self.listen:
            return WxResponse.failure('该聊天已监听')
        subwin = self._api.open_separate_window(nickname)
        if subwin is None:
            return WxResponse.failure('找不到聊天窗口')
        name = subwin.nickname
        chat = Chat(subwin)
        self.listen[name] = (chat, callback)
        return chat
    
    def StopListening(self, remove: bool = True) -> None:
        """停止监听
        
        Args:
            remove (bool, optional): 是否移除监听对象. Defaults to True.
        """
        while self._listener_thread.is_alive():
            self._listener_stop()
        if remove:
            listen = self.listen.copy()
            for who in listen:
                self.RemoveListenChat(who)

    def StartListening(self) -> None:
        if not self._listener_thread.is_alive():
            self._listener_start()

    @uilock
    def RemoveListenChat(
            self, 
            nickname: str,
            close_window: bool = True
        ) -> WxResponse:
        """移除监听聊天

        Args:
            nickname (str): 要移除的监听聊天对象
            close_window (bool, optional): 是否关闭聊天窗口. Defaults to True.

        Returns:
            WxResponse: 执行结果
        """
        if nickname not in self.listen:
            return WxResponse.failure('未找到监听对象')
        chat, _ = self.listen[nickname]
        if close_window:
            chat.Close()
        del self.listen[nickname]
        return WxResponse.success()

    def SwitchToChat(self) -> None:
        """切换到聊天页面"""
        self._api._navigation_api.chat_icon.Click()

    def SwitchToContact(self) -> None:
        """切换到联系人页面"""
        self._api._navigation_api.contact_icon.Click()

    def SwitchToFavorites(self) -> None:
        """切换到收藏页面"""
        self._api._navigation_api.switch_to_favorites_page()

    def SwitchToFiles(self) -> None:
        """切换到聊天文件页面"""
        self._api._navigation_api.switch_to_files_page()

    def SwitchToMoments(self) -> None:
        """切换到朋友圈页面"""
        self._api._navigation_api.switch_to_moments_page()

    def SwitchToBrowser(self) -> None:
        """切换到搜一搜页面"""
        self._api._navigation_api.switch_to_browser_page()

    def SwitchToVideo(self) -> None:
        """切换到视频号页面"""
        self._api._navigation_api.switch_to_video_page()

    def SwitchToStories(self) -> None:
        """切换到看一看页面"""
        self._api._navigation_api.switch_to_stories_page()

    def SwitchToMiniProgram(self) -> None:
        """切换到小程序面板页面"""
        self._api._navigation_api.switch_to_mini_program_page()

    def SwitchToPhone(self) -> None:
        """切换到手机页面"""
        self._api._navigation_api.switch_to_phone_page()

    def SwitchToSettings(self) -> None:
        """切换到更多设置页面"""
        self._api._navigation_api.switch_to_settings_page()

    def ShutDown(self):
        delete_update_files()
        os.system(f'taskkill /f /pid {self._api.pid}')

    # ===== WeChat-only methods (official API compatibility) =====

    @uilock
    def Moments(self, timeout: int = 3) -> WxResponse:
        """获取朋友圈动态

        Args:
            timeout (int): 超时时间

        Returns:
            WxResponse

        Note:
            MEDIUM 风险。会切换到朋友圈页面。
        """
        return WxResponse.failure('not implemented: WeChat.Moments')

    @uilock
    def PublishMoment(
            self,
            text: str = None,
            media_files: list = None,
            privacy_config: dict = None,
        ) -> WxResponse:
        """发布朋友圈

        Args:
            text (str, optional): 文字内容
            media_files (list, optional): 媒体文件路径列表
            privacy_config (dict, optional): 隐私配置

        Returns:
            WxResponse

        Note:
            HIGH 风险。默认 dry_run=True。
        """
        return WxResponse.success(
            data={
                'dry_run': True,
                'method': 'WeChat.PublishMoment',
                'would_do': f'发布朋友圈: text={text!r}, media={media_files}',
                'requires_foreground': True,
                'risk': 'HIGH',
            }
        )

    @uilock
    def GetNewFriends(
            self,
            acceptable: bool = True,
            roll_times: int = 0,
        ) -> WxResponse:
        """获取新好友请求

        Args:
            acceptable (bool): 是否只获取可接受的请求
            roll_times (int): 滚动次数

        Returns:
            WxResponse

        Note:
            MEDIUM 风险。会切换到新好友页面。
        """
        return WxResponse.failure('not implemented: WeChat.GetNewFriends')

    @uilock
    def AddNewFriend(
            self,
            keywords: str,
            addmsg: str = None,
            remark: str = None,
            tags: Union[str, List[str]] = None,
            permission: str = "朋友圈",
            timeout: int = 5,
            dry_run: bool = True,
            allow_foreground: bool = False,
        ) -> WxResponse:
        """添加新好友

        Args:
            keywords (str): 搜索关键词
            addmsg (str, optional): 验证消息
            remark (str, optional): 备注名
            tags (str|list, optional): 标签
            permission (str): 朋友圈权限
            timeout (int): 超时时间
            dry_run (bool): 默认 True，不真实执行
            allow_foreground (bool): 默认 False

        Returns:
            WxResponse

        Note:
            HIGH 风险。默认 dry_run=True。
        """
        if dry_run or not allow_foreground:
            return WxResponse.success(
                data={
                    'dry_run': True,
                    'method': 'WeChat.AddNewFriend',
                    'would_do': f'添加好友: keywords={keywords!r}, remark={remark!r}',
                    'requires_foreground': True,
                    'risk': 'HIGH',
                }
            )
        return WxResponse.failure('not implemented: WeChat.AddNewFriend')

    @uilock
    def EditFriendInfo(
            self,
            add_tags: Union[str, List[str]] = None,
            remove_tags: Union[str, List[str]] = None,
            remark: str = None,
            tag_wait: float = 0.2,
            dry_run: bool = True,
            allow_foreground: bool = False,
        ) -> WxResponse:
        """编辑好友信息

        Args:
            add_tags (str|list, optional): 添加标签
            remove_tags (str|list, optional): 移除标签
            remark (str, optional): 备注名
            tag_wait (float): 标签操作等待时间
            dry_run (bool): 默认 True，不真实执行
            allow_foreground (bool): 默认 False

        Returns:
            WxResponse

        Note:
            HIGH 风险。默认 dry_run=True。
        """
        if dry_run or not allow_foreground:
            return WxResponse.success(
                data={
                    'dry_run': True,
                    'method': 'WeChat.EditFriendInfo',
                    'would_do': f'编辑好友: add_tags={add_tags}, remove_tags={remove_tags}, remark={remark!r}',
                    'requires_foreground': True,
                    'risk': 'HIGH',
                }
            )
        return WxResponse.failure('not implemented: WeChat.EditFriendInfo')

    def GetNextNewMessage(
            self,
            filter_mute: bool = False,
            callback: Callable = None,
        ) -> List['Message']:
        """获取下一条新消息

        Args:
            filter_mute (bool): 是否过滤免打扰消息
            callback (Callable, optional): 回调函数

        Returns:
            List[Message]: 新消息列表

        Note:
            MEDIUM 风险。需要轮询消息。
        """
        return []

    def GetAllRecentGroups(self) -> List[str]:
        """获取所有最近的群聊

        Returns:
            List[str]: 群聊名称列表

        Note:
            LOW 风险。只读。
        """
        return []

    @uilock
    def SendUrlCard(
            self,
            url: str,
            friends: Union[str, List[str]] = None,
            message: str = None,
            timeout: int = 10,
            dry_run: bool = True,
            allow_foreground: bool = False,
        ) -> WxResponse:
        """发送链接卡片

        Args:
            url (str): 链接地址
            friends (str|list, optional): 发送对象
            message (str, optional): 附加消息
            timeout (int): 超时时间
            dry_run (bool): 默认 True，不真实执行
            allow_foreground (bool): 默认 False

        Returns:
            WxResponse

        Note:
            HIGH 风险。默认 dry_run=True。
        """
        if dry_run or not allow_foreground:
            return WxResponse.success(
                data={
                    'dry_run': True,
                    'method': 'WeChat.SendUrlCard',
                    'would_do': f'发送链接卡片: url={url!r}, friends={friends}',
                    'requires_foreground': True,
                    'risk': 'HIGH',
                }
            )
        return WxResponse.failure('not implemented: WeChat.SendUrlCard')

    @uilock
    def GetFriendDetails(
            self,
            n: int = None,
            timeout: int = 0xFFFFF,
            save_head_image: bool = False,
            save_head_wait: float = 0,
            interval: float = 0,
            callback: Callable = None,
            speed: int = 3,
            max_repeat: int = 10,
        ) -> WxResponse:
        """获取好友详情

        Args:
            n (int, optional): 获取数量
            timeout (int): 超时时间
            save_head_image (bool): 是否保存头像
            save_head_wait (float): 保存头像等待时间
            interval (float): 间隔时间
            callback (Callable, optional): 回调函数
            speed (int): 滚动速度
            max_repeat (int): 最大重复次数

        Returns:
            WxResponse

        Note:
            MEDIUM 风险。会切换到联系人页面。
        """
        return WxResponse.failure('not implemented: WeChat.GetFriendDetails')

    @uilock
    def CreateGroup(
            self,
            contacts: Union[str, List[str]],
            dry_run: bool = True,
            allow_foreground: bool = False,
            require_confirm: bool = True,
        ) -> WxResponse:
        """创建群聊

        Args:
            contacts (str|list): 群成员
            dry_run (bool): 默认 True，不真实执行
            allow_foreground (bool): 默认 False
            require_confirm (bool): 默认 True，需要确认

        Returns:
            WxResponse

        Note:
            HIGH 风险。默认 dry_run=True。
        """
        if dry_run or not allow_foreground:
            return WxResponse.success(
                data={
                    'dry_run': True,
                    'method': 'WeChat.CreateGroup',
                    'would_do': f'创建群聊: members={contacts}',
                    'requires_foreground': True,
                    'risk': 'HIGH',
                }
            )
        return WxResponse.failure('not implemented: WeChat.CreateGroup')

    def IsOnline(self) -> bool:
        """检查是否在线

        Returns:
            bool: 是否在线

        Note:
            LOW 风险。只读。
        """
        try:
            return self._api.is_online()
        except Exception:
            return False

    def GetMyInfo(self) -> dict:
        """获取自己的信息

        Returns:
            dict: 个人信息

        Note:
            LOW 风险。只读。
        """
        try:
            return self._api.get_my_info()
        except Exception:
            return {}

    def GetDialog(self, wait: int = 3) -> WxResponse:
        """获取当前对话框信息

        Args:
            wait (int): 等待时间

        Returns:
            WxResponse

        Note:
            LOW 风险。只读。
        """
        return WxResponse.failure('not implemented: WeChat.GetDialog')

    def GetFriendList(
            self,
            *,
            dry_run: bool = True,
            allow_foreground: bool = False,
            max_scroll: int = 200,
            interval: float = 0.2,
            save_path: str = None,
            include_details: bool = False,
            stop_on_repeat: int = 3,
        ) -> WxResponse:
        """获取完整好友列表

        Args:
            dry_run (bool): 默认 True，只输出执行计划，不真实执行
            allow_foreground (bool): 默认 False，需要前台操作时必须为 True
            max_scroll (int): 最大滚动次数，防止无限滚动
            interval (float): 每次滚动后等待时间（秒）
            save_path (str, optional): 保存联系人列表的 JSON 文件路径
            include_details (bool): 是否包含详细信息（当前未实现）
            stop_on_repeat (int): 连续多少轮无新联系人时停止

        Returns:
            WxResponse: data 包含联系人列表

        Note:
            MEDIUM 风险。需要进入联系人页面并滚动。
            默认 dry_run=True，不会真实执行。
        """
        # Case 1: dry_run → return plan
        if dry_run:
            return WxResponse.success(
                data={
                    'dry_run': True,
                    'method': 'WeChat.GetFriendList',
                    'would_do': [
                        'SwitchToContact',
                        'Locate contact list',
                        'Scroll contact list',
                        'Extract contact names',
                        'Deduplicate contacts',
                    ],
                    'requires_foreground': True,
                    'risk': 'MEDIUM',
                    'message': 'Getting full friend list requires foreground UI scrolling',
                }
            )

        # Case 2: dry_run=False, allow_foreground=False → fail
        if not allow_foreground:
            return WxResponse.failure(
                'foreground required: GetFriendList requires switching to contact page and scrolling'
            )

        # Case 3: dry_run=False, allow_foreground=True, include_details=True → not implemented
        if include_details:
            return WxResponse.failure('not implemented: GetFriendList(include_details=True)')

        # Case 4: dry_run=False, allow_foreground=True, include_details=False → real execution
        if max_scroll is None:
            max_scroll = 200
        if interval < 0.1:
            interval = 0.1

        from wxauto4.ui.contactbox import ContactBox
        try:
            contactbox = ContactBox(self._api)
            result = contactbox.get_all_contacts(
                max_scroll=max_scroll,
                interval=interval,
                stop_on_repeat=stop_on_repeat,
            )
        except Exception as e:
            return WxResponse.failure(f'获取好友列表失败: {e}')

        if not result.is_success:
            return result

        contacts = result.get('data', {}).get('contacts', [])

        # Save to file if requested
        if save_path and contacts:
            import json
            os.makedirs(os.path.dirname(save_path) or '.', exist_ok=True)
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(contacts, f, ensure_ascii=False, indent=2)

        return WxResponse.success(data={'contacts': contacts, 'total': len(contacts)})

    def GetFriends(self, **kwargs) -> WxResponse:
        """获取完整好友列表（GetFriendList 别名）"""
        return self.GetFriendList(**kwargs)

