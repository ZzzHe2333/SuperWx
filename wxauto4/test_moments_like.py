import sys
import os
import time
from collections import deque

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from wxauto4.uia import uiautomation as uia


def safe_name(c):
    try:
        return c.Name or ""
    except Exception:
        return ""


def safe_class(c):
    try:
        return c.ClassName or ""
    except Exception:
        return ""


def safe_aid(c):
    try:
        return c.AutomationId or ""
    except Exception:
        return ""


def is_button(c):
    try:
        return getattr(c, "ControlTypeName", "") == "ButtonControl"
    except Exception:
        return False


def is_list(c):
    try:
        return getattr(c, "ControlTypeName", "") in ("ListControl", "TableControl")
    except Exception:
        return False


def find_wechat_main():
    root = uia.GetRootControl()
    best = None
    best_score = -1
    for w in root.GetChildren():
        n = safe_name(w)
        cls = safe_class(w)
        if cls == "mmui::MainWindow" or n == "微信" or "WeChat" in n:
            score = 0
            if cls == "mmui::MainWindow":
                score += 10
            if n == "微信":
                score += 5
            if "WeChat" in n:
                score += 3
            if score > best_score:
                best = w
                best_score = score
    return best


def click_tab_moments(main):
    # 你 UI 输出显示：ButtonControl name='朋友圈' class='mmui::XTabBarItem'
    tab = main.ButtonControl(Name="朋友圈")
    if tab and tab.Exists(0, 0):
        tab.Click()
        time.sleep(0.5)
        return True

    # 兜底：遍历找包含“朋友圈”的按钮
    for c in main.GetChildren():
        if is_button(c) and ("朋友圈" in safe_name(c)):
            c.Click()
            time.sleep(0.5)
            return True
    return False


def bfs_find(control, predicate, max_nodes=12000):
    """在 control 子树里 BFS 找第一个满足 predicate 的控件"""
    q = deque([control])
    seen = 0
    while q and seen < max_nodes:
        cur = q.popleft()
        seen += 1
        try:
            if predicate(cur):
                return cur
            for ch in cur.GetChildren():
                q.append(ch)
        except Exception:
            continue
    return None


def bfs_find_all(control, predicate, max_nodes=20000, max_hits=200):
    """BFS 找多个命中"""
    q = deque([control])
    seen = 0
    hits = []
    while q and seen < max_nodes and len(hits) < max_hits:
        cur = q.popleft()
        seen += 1
        try:
            if predicate(cur):
                hits.append(cur)
            for ch in cur.GetChildren():
                q.append(ch)
        except Exception:
            continue
    return hits


def find_moments_feed_list(main):
    """
    找朋友圈动态列表：
    - 不同版本差异大，所以用启发式：
      1) 找 ListControl
      2) 排除聊天的 chat_message_list / session_list
      3) 选“看起来像动态流”的那个（子项多、且 item 里常包含图片/文本按钮等）
    """
    lists = bfs_find_all(
        main,
        lambda c: is_list(c),
        max_nodes=25000,
        max_hits=200
    )

    candidates = []
    for lc in lists:
        aid = safe_aid(lc)
        name = safe_name(lc)
        cls = safe_class(lc)

        # 排除聊天区域
        if aid in ("chat_message_list", "session_list"):
            continue
        if name in ("消息", "会话"):
            continue

        # 粗略评分
        score = 0
        if "Recycler" in cls or "List" in cls or "Table" in cls:
            score += 1
        if "朋友圈" in name or "动态" in name or "时间线" in name:
            score += 3
        if aid:
            score += 1

        # 子项数量（动态列表一般子项不少）
        try:
            child_count = len(lc.GetChildren())
        except Exception:
            child_count = 0
        score += min(child_count, 50) / 10.0  # 最多加 5 分

        candidates.append((score, lc, child_count, name, cls, aid))

    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1] if candidates else None


def open_action_menu_for_item(item):
    """
    对单条动态 item 打开操作菜单：
    常见是 item 内有 “更多/…/操作” 类按钮（名字可能为空，但 class 有规律）
    我们按以下顺序尝试：
    1) Name 包含 “更多/…” 的 Button
    2) class 包含 'More'/'Menu'/'Operation' 或常见 mmui button
    3) 最后：找 item 内“最右侧的一个 Button”尝试点击（兜底）
    """
    # 1) 名称命中
    btn = bfs_find(
        item,
        lambda c: is_button(c) and any(k in safe_name(c) for k in ("更多", "…", "...", "操作", "菜单")),
        max_nodes=4000
    )
    if btn:
        btn.Click()
        time.sleep(0.3)
        return True

    # 2) class 命中（不同版本你可能需要根据 UI 输出再微调这里）
    btn = bfs_find(
        item,
        lambda c: is_button(c) and any(k.lower() in safe_class(c).lower() for k in ("more", "menu", "operation", "actions")),
        max_nodes=4000
    )
    if btn:
        btn.Click()
        time.sleep(0.3)
        return True

    # 3) 兜底：取 item 里第一个 Button 试试（可能误点，建议第一次先 n=1）
    buttons = bfs_find_all(item, lambda c: is_button(c), max_nodes=4000, max_hits=20)
    if buttons:
        buttons[0].Click()
        time.sleep(0.3)
        return True

    return False


def find_like_window_or_panel(main, timeout=2.0):
    """
    你说的“独立小窗”，一般会是单独 WindowControl/ToolWindow。
    我们先在 RootControl 下找最近弹出的含【赞/取消/评论】的窗口。
    若找不到，再在 main 子树里找浮层（有的版本不弹窗）
    """
    end = time.time() + timeout
    root = uia.GetRootControl()

    def has_like_buttons(scope):
        # “赞/取消/评论” 三者出现任意一个，就算找到了操作面板
        for c in bfs_find_all(scope, lambda x: is_button(x), max_nodes=6000, max_hits=80):
            n = safe_name(c)
            if n in ("赞", "取消", "评论") or ("赞" in n) or ("评论" in n):
                return True
        return False

    # 1) 独立窗口
    while time.time() < end:
        for w in root.GetChildren():
            if getattr(w, "ControlTypeName", "") != "WindowControl":
                continue
            # 排除主窗口
            if safe_class(w) == "mmui::MainWindow":
                continue
            if has_like_buttons(w):
                return w
        time.sleep(0.1)

    # 2) 兜底：主窗口内浮层
    if has_like_buttons(main):
        return main

    return None


def click_like_in_panel(panel, cancel=False):
    """
    cancel=False：点“赞”（如果看到的是“取消”则认为已赞）
    cancel=True ：点“取消”（如果没找到则跳过）
    """
    # 优先精确 name
    target = "取消" if cancel else "赞"

    # 先找精确按钮
    btn = bfs_find(panel, lambda c: is_button(c) and safe_name(c) == target, max_nodes=8000)
    if btn:
        btn.Click()
        time.sleep(0.2)
        return True, target

    # 如果要点赞但只找到了“取消”，说明已赞
    if not cancel:
        btn2 = bfs_find(panel, lambda c: is_button(c) and safe_name(c) == "取消", max_nodes=8000)
        if btn2:
            return False, "already_liked"

    return False, "not_found"


def like_first_n_posts(n=3, cancel=False):
    main = find_wechat_main()
    if not main:
        print("❌ 没找到微信主窗口（mmui::MainWindow）。请确认微信已打开且未最小化。")
        return

    # 激活到前台
    try:
        main.SetFocus()
    except Exception:
        pass

    if not click_tab_moments(main):
        print("❌ 找不到“朋友圈”tab，无法切换。")
        return
    print("✅ 已点击“朋友圈”，等待页面加载…")
    time.sleep(0.5)

    feed = find_moments_feed_list(main)
    if not feed:
        print("❌ 没找到朋友圈动态列表（可能还没加载出时间线）。")
        print("   建议：手动点进朋友圈页面，让动态出现后再跑。")
        return

    items = []
    try:
        items = feed.GetChildren()
    except Exception:
        items = []

    # 过滤掉明显不是动态项的控件（可能含 Header/空白）
    def looks_like_post(it):
        cls = safe_class(it)
        n = safe_name(it)
        if not cls and not n:
            return False
        # 常见动态 item 会是 ListItemControl 或 CustomControl
        return True

    post_items = [it for it in items if looks_like_post(it)]
    if not post_items:
        print("❌ 动态列表里没读到子项。可能需要滚动或页面结构不同。")
        return

    print(f"✅ 找到动态列表子项 {len(post_items)} 个，准备处理前 {n} 条…")

    done = 0
    for idx, item in enumerate(post_items[: max(n, 1)]):
        try:
            item.SetFocus()
        except Exception:
            pass

        if not open_action_menu_for_item(item):
            print(f"⚠️ 第 {idx+1} 条：没能打开操作菜单（找不到更多/…按钮）。")
            continue

        panel = find_like_window_or_panel(main, timeout=2.0)
        if not panel:
            print(f"⚠️ 第 {idx+1} 条：没找到赞/评论面板（弹窗或浮层）。")
            continue

        ok, status = click_like_in_panel(panel, cancel=cancel)
        if ok:
            print(f"✅ 第 {idx+1} 条：点击 {status}")
            done += 1
        else:
            print(f"ℹ️ 第 {idx+1} 条：{status}")

        time.sleep(0.4)

    print(f"\n完成：成功点击 {done} 次（目标前 {n} 条）")


if __name__ == "__main__":
    # 这里改你想点赞多少条
    like_first_n_posts(n=3, cancel=False)