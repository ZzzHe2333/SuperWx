"""朋友圈（Moments）相关接口实现。

本模块提供了 :class:`Moment` 类用于访问微信朋友圈时间线，并能将
UIA 控件解析为结构化数据对象。由于朋友圈界面为动态生成，代码
通过一系列启发式方法定位控件并提取信息，力求在不同语言环境
下保持稳定。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional

import re
import time

from wxauto4 import uia
from wxauto4.languages import MOMENTS
from wxauto4.logger import wxlog
from wxauto4.param import WxParam, WxResponse
from wxauto4.ui.base import BaseUISubWnd
from wxauto4.utils.tools import find_all_windows_from_root
from wxauto4.utils import win32


def _rect_of(ctrl: uia.Control):
    """返回控件屏幕矩形 (l,t,r,b)，失败则 None。"""
    try:
        r = ctrl.BoundingRectangle
        return int(r.left), int(r.top), int(r.right), int(r.bottom)
    except Exception:
        return None


def _rect_ok(rect) -> bool:
    if not rect:
        return False
    l, t, r, b = rect
    if r <= l or b <= t:
        return False
    # 过滤异常坐标
    if min(l, t, r, b) < -1000:
        return False
    if max(l, t, r, b) > 100000:
        return False
    return True


def _dist_point_to_rect(rect, x: int, y: int) -> float:
    l, t, r, b = rect
    dx = 0 if l <= x <= r else (l - x if x < l else x - r)
    dy = 0 if t <= y <= b else (t - y if y < t else y - b)
    return (dx * dx + dy * dy) ** 0.5


def _bfs_find_all(root: uia.Control, pred, max_nodes: int = 260000, max_hits: int = 2000):
    """轻量 BFS：返回满足 pred 的控件列表。"""
    from collections import deque

    q = deque([root])
    seen = 0
    hits = []
    while q and seen < max_nodes and len(hits) < max_hits:
        cur = q.popleft()
        seen += 1
        try:
            if pred(cur):
                hits.append(cur)
            for ch in cur.GetChildren():
                q.append(ch)
        except Exception:
            pass
    return hits


def _lang(key: str) -> str:
    """根据当前语言环境返回朋友圈相关文案。

    Args:
        key: `languages.MOMENTS` 中的键名。

    Returns:
        str: 对应语言的字符串，若不存在则返回原始 key。
    """

    data = MOMENTS.get(key)
    if not data:
        return key
    return data.get(WxParam.LANGUAGE, data.get('cn', key))


def _is_time_line(text: str) -> bool:
    """粗略判断一行文本是否为时间信息。"""

    if not text:
        return False
    patterns = [
        r"\d{4}年\d{1,2}月\d{1,2}日",
        r"\d{2}-\d{2}",
        r"\d{1,2}:\d{2}",
        r"昨[天日]",
        r"星期[一二三四五六日天]",
    ]
    return any(re.search(pattern, text) for pattern in patterns)


def _split_like_names(text: str) -> List[str]:
    """解析点赞字符串。"""

    if not text:
        return []

    like_prefix = _lang('赞')
    text = text.strip()
    if text.startswith(like_prefix):
        text = text[len(like_prefix):].lstrip('：: ')

    sep = _lang('分隔符_点赞')
    if sep:
        parts = [part.strip() for part in text.split(sep) if part.strip()]
    else:
        parts = [name.strip() for name in re.split(r'[,:，]', text) if name.strip()]
    return parts


@dataclass
class MomentComment:
    """朋友圈评论数据结构。"""

    author: str
    content: str
    reply_to: Optional[str] = None
    raw: str = ''

    @classmethod
    def from_text(cls, text: str) -> 'MomentComment':
        text = text.strip()
        reply_to = None
        author = ''
        content = text

        # 格式示例："张三 回复 李四：你好" 或 "张三: 哈喽"
        match = re.match(r'^(?P<author>[^：:]+?)\s*(?:回复\s*(?P<reply>[^：:]+?)\s*)?[：:](?P<content>.*)$', text)
        if match:
            author = match.group('author').strip()
            reply_to = match.group('reply')
            if reply_to:
                reply_to = reply_to.strip()
            content = match.group('content').strip()
        else:
            author = ''
            content = text.strip()

        return cls(author=author, content=content, reply_to=reply_to, raw=text)


class MomentItem(BaseUISubWnd):
    """朋友圈单条动态。"""

    def __init__(self, control: uia.Control, parent: 'MomentList'):
        self.control = control
        self.parent = parent
        self.root = parent.root
        self._parsed = False
        self.nickname: str = ''
        self.content: str = ''
        self.location: Optional[str] = None
        self.time: str = ''
        self.likes: List[str] = []
        self.comments: List[MomentComment] = []
        self.image_count: int = 0
        self.is_advertisement: bool = False
        self._comment_controls: Dict[str, uia.Control] = {}

    # ----------------------------------------------------------------------------------------------
    # 数据解析
    # ----------------------------------------------------------------------------------------------

    def _ensure_parsed(self) -> None:
        if self._parsed:
            return

        raw_text = self.control.Name or ''
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]

        if lines:
            self.nickname = lines[0]

        body_lines = lines[1:]
        content_lines: List[str] = []
        comment_lines: List[str] = []
        likes_line: Optional[str] = None

        for line in body_lines:
            if not line:
                continue

            if re.search(_lang('re_图片数'), line):
                count = re.findall(r'\d+', line)
                if count:
                    self.image_count = int(count[0])
                continue

            if line.startswith(_lang('赞')):
                likes_line = line
                continue

            if line == _lang('评论'):
                # 后续均为评论
                comment_lines.extend(body_lines[body_lines.index(line) + 1:])
                break

            if _lang('广告') in line:
                self.is_advertisement = True
                continue

            if not self.time and _is_time_line(line):
                self.time = line
                continue

            content_lines.append(line)

        # 若未在循环中捕获评论，则继续检查剩余行
        if not comment_lines:
            collecting = False
            for line in body_lines:
                if line == _lang('评论'):
                    collecting = True
                    continue
                if collecting:
                    comment_lines.append(line)

        if likes_line:
            self.likes = _split_like_names(likes_line)

        self.content = '\n'.join(content_lines).strip()
        self.comments = [MomentComment.from_text(line) for line in comment_lines if line.strip()]

        # 记录可用于回复的控件
        for child in self.control.GetChildren():
            if child.ControlTypeName == 'TextControl':
                text = (child.Name or '').strip()
                if text:
                    self._comment_controls.setdefault(text, child)

        self._parsed = True

    # ----------------------------------------------------------------------------------------------
    # 对外属性访问
    # ----------------------------------------------------------------------------------------------

    @property
    def publisher(self) -> str:
        self._ensure_parsed()
        return self.nickname

    @property
    def text(self) -> str:
        self._ensure_parsed()
        return self.content

    @property
    def timestamp(self) -> str:
        self._ensure_parsed()
        return self.time

    @property
    def like_users(self) -> List[str]:
        self._ensure_parsed()
        return list(self.likes)

    @property
    def comment_list(self) -> List[MomentComment]:
        self._ensure_parsed()
        return list(self.comments)

    # ----------------------------------------------------------------------------------------------
    # 工具方法
    # ----------------------------------------------------------------------------------------------

    def find_comment(self, author: str) -> Optional[MomentComment]:
        self._ensure_parsed()
        for comment in self.comments:
            if comment.author == author:
                return comment
        return None

    def get_comment_control(self, comment: MomentComment) -> Optional[uia.Control]:
        self._ensure_parsed()
        key_candidates = [comment.raw, f"{comment.author}: {comment.content}", f"{comment.author}：{comment.content}"]
        for key in key_candidates:
            if key and key in self._comment_controls:
                return self._comment_controls[key]
        # fallback: 遍历匹配
        for text, ctrl in self._comment_controls.items():
            if comment.author and text.startswith(comment.author):
                if comment.content in text:
                    return ctrl
        return None


class MomentList(BaseUISubWnd):
    """朋友圈时间线列表。"""

    def __init__(self, parent: 'Moment'):
        self.parent = parent
        self.root = parent.root
        self.control = self._locate_list(parent)
        self._items: Optional[List[MomentItem]] = None

    def _locate_list(self, parent: 'Moment') -> Optional[uia.Control]:
        wxlog.debug('尝试定位朋友圈列表控件')
        # 首先尝试通过常用 className 定位
        candidates: Iterable[uia.Control] = []
        try:
            candidates = parent._api.control.GetChildren()
        except Exception:
            candidates = []

        queue = list(candidates)
        visited = set()

        while queue:
            ctrl = queue.pop(0)
            if ctrl in visited:
                continue
            visited.add(ctrl)

            class_name = getattr(ctrl, 'ClassName', '') or ''
            automation_id = getattr(ctrl, 'AutomationId', '') or ''
            if ctrl.ControlTypeName == 'ListControl' and ('Moment' in class_name or 'moment' in automation_id.lower()):
                wxlog.debug(f'找到疑似朋友圈列表控件：{class_name}')
                return ctrl

            # 朋友圈列表一般会包含“评论”按钮
            children = []
            try:
                children = ctrl.GetChildren()
            except Exception:
                children = []

            if ctrl.ControlTypeName == 'ListControl':
                for child in children:
                    try:
                        if getattr(child, 'Name', '') == _lang('评论'):
                            wxlog.debug('通过子元素匹配到朋友圈列表控件')
                            return ctrl
                    except Exception:
                        continue

            queue.extend(children)

        wxlog.debug('未能定位到朋友圈列表控件')
        return None

    def exists(self, wait: float = 0) -> bool:  # type: ignore[override]
        if not self.control:
            return False
        try:
            return self.control.Exists(wait)
        except Exception:
            return False

    def refresh(self) -> None:
        self._items = None

    def get_items(self, refresh: bool = False) -> List[MomentItem]:
        if refresh or self._items is None:
            self._items = []
            if not self.control:
                return self._items

            try:
                children = self.control.GetChildren()
            except Exception:
                children = []

            for child in children:
                try:
                    if child.ControlTypeName in {'ListItemControl', 'CustomControl'}:
                        text = getattr(child, 'Name', '') or ''
                        if text.strip():
                            self._items.append(MomentItem(child, self))
                except Exception:
                    continue
        return list(self._items)


class Moment:
    """朋友圈接口封装。"""

    def __init__(self, wx_obj):
        self._wx = wx_obj
        self._api = wx_obj._api
        self.root = wx_obj._api
        self._list: Optional[MomentList] = None

    # ------------------------------------------------------------------------------------------
    # 内部工具
    # ------------------------------------------------------------------------------------------

    def _ensure_list(self) -> Optional[MomentList]:
        if self._list and self._list.exists(0):
            return self._list

        try:
            self._wx.SwitchToMoments()
            time.sleep(0.2)
        except Exception:
            wxlog.debug('切换到朋友圈页面失败')
            return None

        self._list = MomentList(self)
        if not self._list.control:
            return None
        return self._list

    # ------------------------------------------------------------------------------------------
    # 对外接口
    # ------------------------------------------------------------------------------------------

    def GetMoments(self, refresh: bool = False) -> List[MomentItem]:
        """获取朋友圈动态列表。

        Args:
            refresh: 是否强制刷新控件缓存。

        Returns:
            List[MomentItem]: 朋友圈动态对象列表。
        """

        moment_list = self._ensure_list()
        if not moment_list:
            return []
        return moment_list.get_items(refresh)

    def FindMomentByPublisher(self, nickname: str, refresh: bool = False) -> Optional[MomentItem]:
        """根据发布者昵称查找朋友圈动态。"""

        nickname = nickname.strip()
        for item in self.GetMoments(refresh=refresh):
            if item.publisher == nickname:
                return item
        return None

    # ------------------------------------------------------------------------------------------
    # 点赞与评论（部分功能依赖 UI 结构，尽量保证稳健）
    # ------------------------------------------------------------------------------------------

    def _invoke_action_menu(self, item: MomentItem) -> Optional['MomentActionMenu']:
        action_button = None
        try:
            for child in item.control.GetChildren():
                if child.ControlTypeName == 'ButtonControl':
                    action_button = child
                    break
        except Exception:
            action_button = None

        if action_button:
            action_button.Click()
        else:
            try:
                item.control.RightClick()
            except Exception:
                return None

        menu = MomentActionMenu(item)
        if not menu.exists(0.5):
            return None
        return menu

    def Like(self, item: MomentItem, cancel: bool = False) -> WxResponse:
        menu = self._invoke_action_menu(item)
        if not menu:
            return WxResponse.failure('未能打开朋友圈操作菜单')
        try:
            return menu.like(cancel)
        finally:
            menu.close()

    def Comment(self, item: MomentItem, content: str, reply_to: Optional[str] = None) -> WxResponse:
        if reply_to:
            comment = item.find_comment(reply_to)
            if not comment:
                return WxResponse.failure('未找到需要回复的评论')
            ctrl = item.get_comment_control(comment)
            if not ctrl:
                return WxResponse.failure('未定位到评论控件')
            ctrl.Click()
        else:
            menu = self._invoke_action_menu(item)
            if not menu:
                return WxResponse.failure('未能打开朋友圈操作菜单')
            try:
                result = menu.comment()
            finally:
                menu.close()
            if not result:
                return result

        dialog = MomentCommentDialog(self)
        if not dialog.exists(0.5):
            return WxResponse.failure('未弹出评论窗口')
        return dialog.send(content)


    # ------------------------------------------------------------------------------------------
    # 新版朋友圈：点赞（SNSWindow 内嵌“赞/评论”浮层）
    #
    # 适配你这版微信的 UIA 结构：
    # - 朋友圈是独立窗口：class='mmui::SNSWindow' aid='SNSWindow'
    # - 每条动态底部有一条“很浅的灰线”（UIA 中表现为 ListItemControl: mmui::TimelineCommentCell，高度 1~3px）
    # - 点灰线附近的“...”热点后，会在 SNSWindow 内出现 ButtonControl(name='赞') / ButtonControl(name='评论')
    #
    # 注意：Qt/mmui 的 ButtonControl.Click() 有时不会触发，因此这里默认走 Win32 真实鼠标点击。
    # ------------------------------------------------------------------------------------------

    def _find_sns_window(self, timeout: float = 5.0) -> Optional[uia.Control]:
        """获取朋友圈独立窗口（SNSWindow）。"""
        t0 = time.time()
        while time.time() - t0 <= timeout:
            wins = find_all_windows_from_root(pid=self._api.pid)
            for w in wins:
                try:
                    if getattr(w, 'ControlTypeName', '') != 'WindowControl':
                        continue
                    if getattr(w, 'ClassName', '') == 'mmui::SNSWindow' or getattr(w, 'AutomationId', '') == 'SNSWindow' or getattr(w, 'Name', '') == _lang('朋友圈'):
                        return w
                except Exception:
                    continue
            time.sleep(0.1)
        return None

    def _find_comment_separators(self, sns: uia.Control):
        """找灰色分割线（TimelineCommentCell）。返回 [(y, l, t, r, b, ctrl), ...]"""
        seps = _bfs_find_all(
            sns,
            lambda c: getattr(c, 'ControlTypeName', '') == 'ListItemControl' and getattr(c, 'ClassName', '') == 'mmui::TimelineCommentCell',
            max_nodes=260000,
            max_hits=2000,
        )
        out = []
        for s in seps:
            rect = _rect_of(s)
            if not _rect_ok(rect):
                continue
            l, t, r, b = rect
            w, h = r - l, b - t
            if w >= 280 and h <= 3:
                out.append((t, l, t, r, b, s))
        out.sort(key=lambda x: x[0])
        return out

    def _click_more_hotspot(self, sep_row, x_ratio: float = 0.92, y_offset_up: int = 16):
        """点击“...”热点（靠右，略高于灰线）。返回 (x,y)"""
        _, l, t, r, _, _ = sep_row
        x = int(l + (r - l) * x_ratio)
        y = int(t - y_offset_up)
        win32.Click(uia.Rect(x, y, x + 1, y + 1))  # 复用 win32.Click：传一个 1x1 的 rect
        time.sleep(0.22)
        return x, y

    def _find_like_panel_controls_near(self, sns: uia.Control, click_x: int, click_y: int, radius: int = 340):
        """在 SNSWindow 内，找点击点附近出现的 赞/取消/评论 控件。"""
        hits = []
        q = [sns]
        seen = 0
        while q and seen < 200000 and len(hits) < 80:
            cur = q.pop(0)
            seen += 1
            try:
                n = (getattr(cur, 'Name', '') or '').strip()
                if n in (_lang('赞'), _lang('取消'), _lang('评论')):
                    rect = _rect_of(cur)
                    if _rect_ok(rect) and _dist_point_to_rect(rect, click_x, click_y) <= radius:
                        hits.append(cur)
                q.extend(cur.GetChildren())
            except Exception:
                pass
        return hits

    def _pick_like_button(self, ctrls: List[uia.Control], cancel: bool = False) -> Optional[uia.Control]:
        """优先找 ButtonControl(name='赞'|'取消', class='mmui::XButton')。"""
        target = _lang('取消') if cancel else _lang('赞')
        for c in ctrls:
            try:
                if getattr(c, 'ControlTypeName', '') == 'ButtonControl' and getattr(c, 'Name', '') == target and getattr(c, 'ClassName', '') == 'mmui::XButton':
                    return c
            except Exception:
                continue
        for c in ctrls:
            try:
                if getattr(c, 'Name', '') == target:
                    return c
            except Exception:
                continue
        return None

    def _click_control_center_win32(self, ctrl: uia.Control) -> bool:
        rect = _rect_of(ctrl)
        if not _rect_ok(rect):
            return False
        l, t, r, b = rect
        cx, cy = (l + r) // 2, (t + b) // 2
        win32.Click(uia.Rect(cx, cy, cx + 1, cy + 1))
        return True

    def _verify_after_like(self, sns: uia.Control, click_x: int, click_y: int, radius: int = 340, timeout: float = 1.0) -> bool:
        """点完赞后验证：附近出现“取消”（已赞）或“赞”消失。"""
        end = time.time() + timeout
        while time.time() < end:
            ctrls = self._find_like_panel_controls_near(sns, click_x, click_y, radius=radius)
            names = {getattr(c, 'Name', '') for c in ctrls}
            if _lang('取消') in names:
                return True
            if _lang('赞') not in names:
                return True
            time.sleep(0.08)
        return False

    def LikeLatest(self, n: int = 1, cancel: bool = False, max_pages: int = 10) -> WxResponse:
        """给最新 n 条朋友圈点赞（或取消赞）。

        说明：此方法适配你这版“SNSWindow 内嵌赞/评论浮层”。

        Args:
            n: 目标条数。
            cancel: True 则点“取消”，用于取消已赞。
            max_pages: 最多翻页次数（滚动加载）。

        Returns:
            WxResponse
        """

        try:
            self._wx.SwitchToMoments()
            time.sleep(0.2)
        except Exception:
            pass

        sns = self._find_sns_window(timeout=6.0)
        if not sns:
            return WxResponse.failure('未找到朋友圈窗口（SNSWindow）')

        # 轻微滚动，确保动态控件生成
        try:
            rect = _rect_of(sns)
            if _rect_ok(rect):
                l, t, r, b = rect
                cx, cy = (l + r) // 2, (t + b) // 2
                win32.set_cursor_pos(cx, cy)
                time.sleep(0.05)
                # 复用 win32api 的滚轮（如果你环境没装 pywin32，会在 win32 模块里报错；wxauto4 本身依赖它）
                try:
                    import win32api, win32con
                    for _ in range(2):
                        win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, -120 * 3, 0)
                        time.sleep(0.2)
                except Exception:
                    pass
        except Exception:
            pass

        success = 0
        tried = 0

        for _page in range(max_pages):
            seps = self._find_comment_separators(sns)
            if not seps:
                # 继续滚动加载
                try:
                    import win32api, win32con
                    win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, -120 * 6, 0)
                except Exception:
                    pass
                time.sleep(0.6)
                continue

            for sep in seps:
                if success >= n:
                    break
                tried += 1
                click_x, click_y = self._click_more_hotspot(sep)
                ctrls = self._find_like_panel_controls_near(sns, click_x, click_y, radius=340)
                btn = self._pick_like_button(ctrls, cancel=cancel)
                if not btn:
                    continue
                if not self._click_control_center_win32(btn):
                    continue
                time.sleep(0.22)
                if self._verify_after_like(sns, click_x, click_y, radius=340, timeout=1.0):
                    success += 1
                time.sleep(0.55)

            if success >= n:
                break

            # 下一页
            try:
                import win32api, win32con
                win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, -120 * 6, 0)
            except Exception:
                pass
            time.sleep(0.7)

        if success <= 0:
            return WxResponse.failure(f'点赞失败（success=0, tried={tried}）')
        return WxResponse.success(f'操作成功（success={success}/{n}, tried={tried}）')


class MomentActionMenu(BaseUISubWnd):
    """朋友圈点赞/评论菜单。"""

    _win_cls_name: str = 'Qt51514QWindowToolSaveBits'

    def __init__(self, parent: MomentItem, timeout: float = 1.0):
        self.parent = parent
        self.root = parent.root
        self.control = self._locate(timeout)

    def _locate(self, timeout: float) -> Optional[uia.Control]:
        t0 = time.time()
        while time.time() - t0 <= timeout:
            wins = find_all_windows_from_root(classname=self._win_cls_name, pid=self.root.pid)
            for win in wins:
                try:
                    children = win.GetChildren()
                except Exception:
                    children = []
                for child in children:
                    name = getattr(child, 'Name', '')
                    if name in {_lang('赞'), _lang('取消'), _lang('评论')}:
                        return win
            time.sleep(0.05)
        return None

    def exists(self, wait: float = 0) -> bool:  # type: ignore[override]
        if not self.control:
            return False
        try:
            return self.control.Exists(wait)
        except Exception:
            return False

    def _find_button(self, names: Iterable[str]) -> Optional[uia.Control]:
        if not self.control:
            return None
        target_names = list(names)
        try:
            children = self.control.GetChildren()
        except Exception:
            children = []
        for child in children:
            if child.ControlTypeName != 'ButtonControl':
                continue
            name = getattr(child, 'Name', '')
            if name in target_names:
                return child
        return None

    def like(self, cancel: bool = False) -> WxResponse:
        target_names = [_lang('赞')]
        if cancel:
            target_names.insert(0, _lang('取消'))

        button = self._find_button(target_names)
        if not button:
            return WxResponse.failure('未找到点赞按钮')
        button.Click()
        return WxResponse.success('操作成功')

    def comment(self) -> WxResponse:
        button = self._find_button([_lang('评论')])
        if not button:
            return WxResponse.failure('未找到评论按钮')
        button.Click()
        return WxResponse.success('已触发评论')

    def close(self) -> None:
        if not self.control:
            return
        try:
            self.control.SendKeys('{Esc}')
        except Exception:
            pass


class MomentCommentDialog(BaseUISubWnd):
    """朋友圈评论输入窗口。"""

    _win_cls_name: str = 'Qt51514QWindowToolSaveBits'

    def __init__(self, parent: Moment):
        self.parent = parent
        self.root = parent.root
        self.control = self._locate()
        if self.control:
            self._init_controls()

    def _locate(self) -> Optional[uia.Control]:
        wins = find_all_windows_from_root(classname=self._win_cls_name, pid=self.root.pid)
        for win in wins:
            try:
                children = win.GetChildren()
            except Exception:
                children = []
            for child in children:
                if child.ControlTypeName == 'ButtonControl' and getattr(child, 'Name', '') == _lang('发送'):
                    return win
        return None

    def _init_controls(self) -> None:
        self.edit: Optional[uia.Control] = None
        self.send_button: Optional[uia.Control] = None
        try:
            children = self.control.GetChildren()
        except Exception:
            children = []
        for child in children:
            if child.ControlTypeName == 'EditControl' and self.edit is None:
                self.edit = child
            elif child.ControlTypeName == 'ButtonControl' and getattr(child, 'Name', '') == _lang('发送'):
                self.send_button = child

    def exists(self, wait: float = 0) -> bool:  # type: ignore[override]
        if not self.control:
            return False
        try:
            return self.control.Exists(wait)
        except Exception:
            return False

    def send(self, content: str) -> WxResponse:
        if not self.exists(0):
            return WxResponse.failure('评论窗口不存在')

        if not content:
            return WxResponse.failure('评论内容不能为空')

        if not self.edit or not self.edit.Exists(0):
            return WxResponse.failure('未找到评论输入框')

        try:
            from wxauto4.utils.win32 import SetClipboardText
        except Exception:
            SetClipboardText = None  # type: ignore

        try:
            self.edit.Click()
            self.edit.SendKeys('{Ctrl}a')
            if SetClipboardText:
                SetClipboardText(content)
                self.edit.SendKeys('{Ctrl}v')
            else:
                # 退化方案：直接键入
                for ch in content:
                    self.edit.SendKeys(ch)

            if self.send_button and self.send_button.Exists(0):
                self.send_button.Click()
            else:
                self.edit.SendKeys('{Enter}')
        except Exception as exc:  # pragma: no cover - UI 交互异常仅记录日志
            wxlog.debug(f'发送朋友圈评论失败：{exc}')
            return WxResponse.failure('发送评论失败')

        return WxResponse.success('评论成功')

