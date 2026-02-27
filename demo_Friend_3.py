# -*- coding: utf-8 -*-
import sys
import os
import time
import ctypes
from collections import deque

# Demo v2: Like first 3 Moments posts in WeChat.
#
# Why v2:
# - We can reliably locate Like/Comment buttons, but UIA .Click() may not trigger.
# - v2 ALWAYS uses Win32 mouse click at the button center (more reliable for Qt/mmui).
#
# Strategy:
# - Anchor by thin divider: ListItemControl class 'mmui::TimelineCommentCell'
# - Click the "..." hotspot above divider (x_ratio / y_offset_up)
# - Panel appears INSIDE SNSWindow; find controls near click point named: 赞/评论/取消
# - Mouse-click the ButtonControl '赞'
# - Verify by re-scanning near the same click point: '取消' should appear (or '赞' disappears)
#
# Run:
#   cd D:\wxauto4-main
#   python demo_like_first3_v2.py

CUR = os.path.dirname(os.path.abspath(__file__))
if CUR not in sys.path:
    sys.path.insert(0, CUR)

from wxauto4.uia import uiautomation as uia

# ---------------- Win32 mouse helpers ----------------
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

# ---------------- UIA helpers ----------------
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
def is_list_item(c): return ctype(c) == "ListItemControl"

def rect_of(c):
    r = safe_get(c, "BoundingRectangle", None)
    if not r:
        return None
    try:
        return (int(r.left), int(r.top), int(r.right), int(r.bottom))
    except Exception:
        return None

def rect_ok(r):
    if not r:
        return False
    l, t, rr, bb = r
    if rr <= l or bb <= t:
        return False
    if min(l, t, rr, bb) < -1000:
        return False
    if max(l, t, rr, bb) > 10000:
        return False
    return True

def dist_point_to_rect(r, x, y):
    l, t, rr, bb = r
    dx = 0 if l <= x <= rr else (l - x if x < l else x - rr)
    dy = 0 if t <= y <= bb else (t - y if y < t else y - bb)
    return (dx * dx + dy * dy) ** 0.5

def summary(c, max_len=60):
    n = cname(c).replace("\n", " ")
    if len(n) > max_len:
        n = n[:max_len] + "…"
    return f"type={ctype(c)} | name='{n}' | class='{cclass(c)}' | aid='{caid(c)}'"

def bfs_find_all(root, pred, max_nodes=240000, max_hits=1800):
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

# ---------------- WeChat window finders ----------------
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

def focus_window_by_click(win):
    r = rect_of(win)
    if not rect_ok(r):
        return
    l, t, rr, bb = r
    mouse_left_click(l + 20, t + 20)
    time.sleep(0.15)

def scroll_sns(sns, notches=3):
    r = rect_of(sns)
    if not rect_ok(r):
        return False
    l, t, rr, bb = r
    wheel_down_at((l + rr) // 2, (t + bb) // 2, notches=notches)
    return True

# ---------------- Core: separators + like ----------------
def find_comment_separators(sns):
    seps = bfs_find_all(
        sns,
        lambda c: is_list_item(c) and cclass(c) == "mmui::TimelineCommentCell",
        max_nodes=260000,
        max_hits=1800
    )
    good = []
    for s in seps:
        r = rect_of(s)
        if not rect_ok(r):
            continue
        l, t, rr, bb = r
        w, h = rr - l, bb - t
        if h <= 3 and w >= 300:
            good.append((t, l, rr, bb, s))
    good.sort(key=lambda x: x[0])
    return good

def click_three_dots_near_separator(sep_rect, x_ratio=0.92, y_offset_up=16):
    t, l, rr, bb, _ = sep_rect
    x = int(l + (rr - l) * x_ratio)
    y = int(t - y_offset_up)
    mouse_left_click(x, y)
    time.sleep(0.22)
    return x, y

def find_like_controls_near_click_in_scope(scope, click_x, click_y, radius=340):
    hits = []
    q = deque([scope])
    seen = 0
    while q and seen < 200000 and len(hits) < 80:
        cur = q.popleft()
        seen += 1
        try:
            n = cname(cur)
            if n in ("赞", "取消", "评论"):
                r = rect_of(cur)
                if rect_ok(r) and dist_point_to_rect(r, click_x, click_y) <= radius:
                    hits.append(cur)
            for ch in cur.GetChildren():
                q.append(ch)
        except Exception:
            pass
    return hits

def pick_like_button(ctrls):
    for c in ctrls:
        if is_button(c) and cname(c) == "赞" and cclass(c) == "mmui::XButton":
            return c
    for c in ctrls:
        if cname(c) == "赞":
            return c
    return None

def click_center_of(ctrl):
    r = rect_of(ctrl)
    if not rect_ok(r):
        return False
    l, t, rr, bb = r
    mouse_left_click((l + rr)//2, (t + bb)//2)
    return True

def verify_liked(sns, click_x, click_y, radius=340, timeout=0.9):
    end = time.time() + timeout
    while time.time() < end:
        ctrls = find_like_controls_near_click_in_scope(sns, click_x, click_y, radius=radius)
        names = {cname(c) for c in ctrls}
        if "取消" in names:
            return True, "verified_by_取消"
        if "赞" not in names:
            return True, "verified_by_no_赞"
        time.sleep(0.08)
    return False, "verify_timeout"

def like_one_by_separator(sns, sep_rect, x_ratio=0.92, y_offset_up=16, radius=340):
    x, y = click_three_dots_near_separator(sep_rect, x_ratio=x_ratio, y_offset_up=y_offset_up)
    ctrls = find_like_controls_near_click_in_scope(sns, x, y, radius=radius)
    btn = pick_like_button(ctrls)
    if not btn:
        return False, f"panel_found_but_no_like_btn (hits={len(ctrls)})"

    if not click_center_of(btn):
        return False, "like_btn_rect_invalid"

    time.sleep(0.20)
    ok, why = verify_liked(sns, x, y, radius=radius, timeout=0.9)
    return ok, ("liked_" + why) if ok else ("clicked_but_not_verified_" + why)

def like_first_n_posts(n=3, x_ratio=0.92, y_offset_up=16, radius=340):
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
        print("❌ 没找到朋友圈窗口（mmui::SNSWindow）。")
        return

    print("✅ SNSWindow：")
    print(summary(sns))

    focus_window_by_click(sns)
    time.sleep(0.5)

    for _ in range(2):
        scroll_sns(sns, notches=3)
        time.sleep(0.45)

    success = 0
    tried = 0

    for page in range(10):
        seps = find_comment_separators(sns)
        print(f"\n✅ page={page+1} separators={len(seps)}")
        if not seps:
            scroll_sns(sns, notches=6)
            time.sleep(0.9)
            continue

        for sep in seps:
            if success >= n:
                break
            tried += 1
            ok, status = like_one_by_separator(sns, sep, x_ratio=x_ratio, y_offset_up=y_offset_up, radius=radius)
            print(f"  #{tried} -> {status}")
            if ok:
                success += 1
            time.sleep(0.65)

        if success >= n:
            break

        scroll_sns(sns, notches=6)
        time.sleep(0.9)

    print(f"\n完成：成功 {success} 次（目标 {n}），尝试 {tried} 个分割点")

if __name__ == "__main__":
    like_first_n_posts(n=3)
