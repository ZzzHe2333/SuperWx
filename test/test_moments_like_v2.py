
import sys
import os
import time
import ctypes
from collections import deque

# ---------------------------
# Project import
# ---------------------------
CUR = os.path.dirname(os.path.abspath(__file__))
if CUR not in sys.path:
    sys.path.insert(0, CUR)

from wxauto4.uia import uiautomation as uia

# ---------------------------
# Win32 mouse helpers
# ---------------------------
user32 = ctypes.WinDLL("user32", use_last_error=True)
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP   = 0x0004
MOUSEEVENTF_WHEEL    = 0x0800

def set_cursor_pos(x: int, y: int) -> None:
    user32.SetCursorPos(int(x), int(y))

def mouse_left_click(x: int, y: int) -> None:
    set_cursor_pos(x, y)
    time.sleep(0.03)
    user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    time.sleep(0.03)
    user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)

def mouse_wheel(delta: int) -> None:
    user32.mouse_event(MOUSEEVENTF_WHEEL, 0, 0, int(delta), 0)

def wheel_down_at(x: int, y: int, notches: int = 3) -> None:
    set_cursor_pos(x, y)
    time.sleep(0.02)
    for _ in range(notches):
        mouse_wheel(-120)
        time.sleep(0.10)

# ---------------------------
# UIA safe helpers
# ---------------------------
def safe_get(obj, attr, default=None):
    try:
        v = getattr(obj, attr)
        return v if v is not None else default
    except Exception:
        return default

def ctype(c):  return (safe_get(c, "ControlTypeName", "") or "")
def cname(c):  return (safe_get(c, "Name", "") or "")
def cclass(c): return (safe_get(c, "ClassName", "") or "")
def caid(c):   return (safe_get(c, "AutomationId", "") or "")

def is_window(c): return ctype(c) == "WindowControl"
def is_button(c): return ctype(c) == "ButtonControl"
def is_text(c):   return ctype(c) == "TextControl"
def is_list_item(c): return ctype(c) == "ListItemControl"

def rect_of(c):
    r = safe_get(c, "BoundingRectangle", None)
    if not r:
        return None
    try:
        return (int(r.left), int(r.top), int(r.right), int(r.bottom))
    except Exception:
        return None

def summary(c, max_len=70):
    n = cname(c).replace("\n", "\\n")
    if len(n) > max_len:
        n = n[:max_len] + "…"
    return f"type={ctype(c)} | name='{n}' | class='{cclass(c)}' | aid='{caid(c)}'"

def bfs_find(root, pred, max_nodes=25000):
    q = deque([root])
    seen = 0
    while q and seen < max_nodes:
        cur = q.popleft()
        seen += 1
        try:
            if pred(cur):
                return cur
            for ch in cur.GetChildren():
                q.append(ch)
        except Exception:
            pass
    return None

def bfs_find_all(root, pred, max_nodes=80000, max_hits=1200):
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

# ---------------------------
# WeChat windows
# ---------------------------
def find_wechat_main():
    root = uia.GetRootControl()
    for w in root.GetChildren():
        if is_window(w) and cclass(w) == "mmui::MainWindow" and cname(w) == "微信":
            return w
    for w in root.GetChildren():
        if is_window(w) and ("微信" in cname(w) or "WeChat" in cname(w)):
            return w
    return None

def click_tab_moments(main):
    tab = main.ButtonControl(Name="朋友圈")
    if tab and tab.Exists(0, 0):
        tab.Click()
        time.sleep(0.7)
        return True
    for ch in main.GetChildren():
        if is_button(ch) and "朋友圈" in cname(ch):
            ch.Click()
            time.sleep(0.7)
            return True
    return False

def wait_sns_window(timeout=8.0):
    root = uia.GetRootControl()
    end = time.time() + timeout
    while time.time() < end:
        for w in root.GetChildren():
            if not is_window(w):
                continue
            if cclass(w) == "mmui::SNSWindow" or caid(w) == "SNSWindow" or cname(w) == "朋友圈":
                return w
        time.sleep(0.2)
    return None

def scroll_sns(sns, notches=3):
    r = rect_of(sns)
    if not r:
        return False
    l, t, rr, bb = r
    cx = (l + rr) // 2
    cy = (t + bb) // 2
    wheel_down_at(cx, cy, notches=notches)
    return True

# ---------------------------
# Like popup panel (independent window)
# ---------------------------
def find_like_panel(timeout=3.0):
    root = uia.GetRootControl()
    end = time.time() + timeout
    while time.time() < end:
        for w in root.GetChildren():
            if not is_window(w):
                continue
            if cclass(w) in ("mmui::MainWindow", "mmui::SNSWindow"):
                continue
            hit = bfs_find(
                w,
                lambda c: (is_button(c) or is_text(c)) and (
                    cname(c) in ("赞", "取消", "评论", "回复") or ("赞" in cname(c)) or ("评论" in cname(c))
                ),
                max_nodes=18000,
            )
            if hit:
                return w
        time.sleep(0.1)
    return None

def click_like(panel, cancel=False):
    target = "取消" if cancel else "赞"

    btn = bfs_find(panel, lambda c: is_button(c) and cname(c) == target, max_nodes=22000)
    if btn:
        btn.Click()
        time.sleep(0.25)
        return True, f"clicked:{target}"

    txt = bfs_find(panel, lambda c: is_text(c) and cname(c) == target, max_nodes=22000)
    if txt:
        try:
            txt.Click()
            time.sleep(0.25)
            return True, f"clicked_text:{target}"
        except Exception:
            pass

    if not cancel and bfs_find(panel, lambda c: (is_button(c) or is_text(c)) and cname(c) == "取消", max_nodes=22000):
        return False, "already_liked"

    return False, "not_found"

# ---------------------------
# Core strategy: use TimelineCommentCell as anchor
# ---------------------------
def find_comment_separators(sns):
    # Use 1px height ListItemControl: mmui::TimelineCommentCell as "separator/anchor"
    seps = bfs_find_all(
        sns,
        lambda c: is_list_item(c) and cclass(c) == "mmui::TimelineCommentCell",
        max_nodes=120000,
        max_hits=600
    )
    good = []
    for s in seps:
        r = rect_of(s)
        if not r:
            continue
        l, t, rr, bb = r
        w, h = rr - l, bb - t
        if h <= 3 and w >= 300:
            good.append((t, l, rr, bb, s))
    good.sort(key=lambda x: x[0])
    return good

def click_three_dots_near_separator(sep_rect, x_ratio=0.92, y_offset_up=16):
    # Grey line below action bar: click slightly ABOVE the separator near the right side.
    t, l, rr, bb, _ = sep_rect
    width = rr - l
    x = int(l + width * x_ratio)
    y = int(t - y_offset_up)
    mouse_left_click(x, y)
    time.sleep(0.30)
    return (x, y)

def like_first_n(n=3, cancel=False):
    main = find_wechat_main()
    if not main:
        print("❌ 没找到微信主窗口（mmui::MainWindow）。")
        return

    try:
        main.SetFocus()
    except Exception:
        pass

    if not click_tab_moments(main):
        print("❌ 点击“朋友圈”失败（找不到 tab）。")
        return

    sns = wait_sns_window()
    if not sns:
        print("❌ 没找到朋友圈独立窗口（mmui::SNSWindow）。")
        return

    print("✅ 找到朋友圈窗口：")
    print(summary(sns))
    time.sleep(0.9)

    # Pre-scroll a bit to load more posts & separators
    for _ in range(2):
        scroll_sns(sns, notches=3)
        time.sleep(0.45)

    done = 0
    tried = 0

    for page in range(8):
        seps = find_comment_separators(sns)
        if not seps:
            print("⚠️ 没找到 TimelineCommentCell 分割线（请先滚动让多条动态显示出来）。")
            scroll_sns(sns, notches=5)
            time.sleep(0.6)
            continue

        print(f"✅ page={page+1} separators={len(seps)}")

        for sep in seps:
            if done >= n:
                break
            tried += 1

            x, y = click_three_dots_near_separator(sep, x_ratio=0.92, y_offset_up=16)

            panel = find_like_panel(timeout=2.4)
            if not panel:
                # small nudge left, same y
                mouse_left_click(x - 40, y)
                time.sleep(0.25)
                panel = find_like_panel(timeout=1.6)

            if not panel:
                continue

            ok, status = click_like(panel, cancel=cancel)
            if ok:
                done += 1
                print(f"✅ 第{done}次：{status} (click@{x},{y})")
            else:
                print(f"ℹ️ {status} (click@{x},{y})")

            time.sleep(0.55)

        if done >= n:
            break

        scroll_sns(sns, notches=6)
        time.sleep(0.8)

    print(f"\n完成：成功 {done} 次（目标 {n}），尝试 {tried} 个分割点")

if __name__ == "__main__":
    like_first_n(n=3, cancel=False)
