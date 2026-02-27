
import sys
import os
import time
import ctypes
from collections import deque

# ==========================================================
# v2: 修复“误把 Edge 当成 like_panel”的探测脚本
# 关键改动：
# - 只接受“靠近点击点”的小浮层窗口（尺寸/位置过滤）
# - 排除 Chrome_WidgetWin_1 / 浏览器等大窗口
# - 若浮层不在顶层窗口，则在 SNSWindow 内部按“靠近点击点”搜索赞/评论
# ==========================================================

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

def rect_ok(r):
    if not r:
        return False
    l, t, rr, bb = r
    # 过滤明显异常（比如 Edge 页面内文本 rect 可能是巨大的负数）
    if min(l, t, rr, bb) < -1000:
        return False
    if max(l, t, rr, bb) > 10000:
        return False
    if rr <= l or bb <= t:
        return False
    return True

def size_of(r):
    l, t, rr, bb = r
    return rr - l, bb - t

def dist_point_to_rect(r, x, y):
    l, t, rr, bb = r
    dx = 0 if l <= x <= rr else (l - x if x < l else x - rr)
    dy = 0 if t <= y <= bb else (t - y if y < t else y - bb)
    return (dx * dx + dy * dy) ** 0.5

def summary(c, max_len=60):
    n = cname(c).replace("\n", "\\n")
    if len(n) > max_len:
        n = n[:max_len] + "…"
    return f"type={ctype(c)} | name='{n}' | class='{cclass(c)}' | aid='{caid(c)}'"

def bfs_find(root, pred, max_nodes=26000):
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

def bfs_find_all(root, pred, max_nodes=160000, max_hits=1200):
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
    return None

def click_tab_moments(main):
    tab = main.ButtonControl(Name="朋友圈")
    if tab and tab.Exists(0, 0):
        tab.Click()
        time.sleep(0.7)
        return True
    for ch in main.GetChildren():
        try:
            if is_button(ch) and "朋友圈" in cname(ch):
                ch.Click()
                time.sleep(0.7)
                return True
        except Exception:
            pass
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
    if not rect_ok(r):
        return False
    l, t, rr, bb = r
    cx = (l + rr) // 2
    cy = (t + bb) // 2
    wheel_down_at(cx, cy, notches=notches)
    return True

# ---------------- Separator anchor ----------------
def find_comment_separators(sns):
    seps = bfs_find_all(
        sns,
        lambda c: is_list_item(c) and cclass(c) == "mmui::TimelineCommentCell",
        max_nodes=200000,
        max_hits=1200
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
    width = rr - l
    x = int(l + width * x_ratio)
    y = int(t - y_offset_up)
    mouse_left_click(x, y)
    time.sleep(0.22)
    return (x, y)

# ---------------- Robust panel detection ----------------
def is_candidate_panel_window(w, click_x, click_y):
    if not is_window(w):
        return False

    cls = cclass(w)
    # 排除主窗口/朋友圈窗口
    if cls in ("mmui::MainWindow", "mmui::SNSWindow"):
        return False
    # 排除浏览器/大窗口
    if cls in ("Chrome_WidgetWin_0", "Chrome_WidgetWin_1"):
        return False

    r = rect_of(w)
    if not rect_ok(r):
        return False

    w0, h0 = size_of(r)
    # 赞/评论浮层一般很小
    if w0 > 520 or h0 > 280:
        return False

    # 必须靠近点击点
    if dist_point_to_rect(r, click_x, click_y) > 220:
        return False

    # 里面要能命中 “赞/评论/取消”
    hit = bfs_find(w, lambda c: (is_button(c) or is_text(c)) and cname(c) in ("赞", "评论", "取消"), max_nodes=20000)
    return hit is not None

def find_like_panel_near_click(click_x, click_y, timeout=1.8):
    root = uia.GetRootControl()
    end = time.time() + timeout
    while time.time() < end:
        cands = []
        for w in root.GetChildren():
            try:
                if is_candidate_panel_window(w, click_x, click_y):
                    r = rect_of(w)
                    d = dist_point_to_rect(r, click_x, click_y)
                    cands.append((d, w))
            except Exception:
                pass
        if cands:
            cands.sort(key=lambda x: x[0])
            return cands[0][1]
        time.sleep(0.08)
    return None

def find_like_controls_near_click_in_scope(scope, click_x, click_y, radius=300):
    hits = []
    q = deque([scope])
    seen = 0
    while q and seen < 140000 and len(hits) < 80:
        cur = q.popleft()
        seen += 1
        try:
            n = cname(cur)
            if n in ("赞", "评论", "取消"):
                r = rect_of(cur)
                if rect_ok(r) and dist_point_to_rect(r, click_x, click_y) <= radius:
                    hits.append(cur)
            for ch in cur.GetChildren():
                q.append(ch)
        except Exception:
            pass
    return hits

def dump_controls(ctrls, title, max_lines=30):
    print(f"  [{title}] hits={len(ctrls)}")
    for c in ctrls[:max_lines]:
        print("   - " + summary(c) + f" rect={rect_of(c)}")

def click_like_from_controls(ctrls, cancel=False):
    target = "取消" if cancel else "赞"
    for c in ctrls:
        if cname(c) == target:
            try:
                c.Click()
                time.sleep(0.18)
                return True, f"clicked:{target}"
            except Exception:
                r = rect_of(c)
                if rect_ok(r):
                    l, t, rr, bb = r
                    mouse_left_click((l + rr) // 2, (t + bb) // 2)
                    time.sleep(0.18)
                    return True, f"clicked_center:{target}"

    if not cancel and any(cname(c) == "取消" for c in ctrls):
        return False, "already_liked"
    return False, "not_found"

# ---------------- Function you asked ----------------
def open_more_and_probe(sns, sep_rect, x_ratio=0.92, y_offset_up=16, auto_click_like=False):
    x, y = click_three_dots_near_separator(sep_rect, x_ratio=x_ratio, y_offset_up=y_offset_up)
    print(f"✅ clicked ... @({x},{y})")

    panel = find_like_panel_near_click(x, y, timeout=1.6)
    if panel:
        print("✅ found panel window near click:")
        print("  " + summary(panel) + f" rect={rect_of(panel)}")
        inner = bfs_find_all(
            panel,
            lambda c: (is_button(c) or is_text(c)) and cname(c) in ("赞", "评论", "取消"),
            max_nodes=30000,
            max_hits=50
        )
        dump_controls(inner, "panel_inner", max_lines=20)
        if auto_click_like:
            ok, status = click_like_from_controls(inner, cancel=False)
            print(f"➡️ auto_click_like: {status}")
        return True

    ctrls = find_like_controls_near_click_in_scope(sns, x, y, radius=300)
    if ctrls:
        print("✅ found like/comment controls inside SNSWindow near click:")
        dump_controls(ctrls, "sns_near_click", max_lines=20)
        if auto_click_like:
            ok, status = click_like_from_controls(ctrls, cancel=False)
            print(f"➡️ auto_click_like: {status}")
        return True

    print("❌ no panel detected (neither top-level nor inside sns).")
    return False

# ---------------- Demo ----------------
def demo(n=3, auto_click_like=False):
    main = find_wechat_main()
    if not main:
        print("❌ main window not found")
        return
    try:
        main.SetFocus()
    except Exception:
        pass

    if not click_tab_moments(main):
        print("❌ click Moments tab failed")
        return

    sns = wait_sns_window()
    if not sns:
        print("❌ SNSWindow not found")
        return

    print("✅ SNSWindow:")
    print(summary(sns))
    time.sleep(0.8)

    for _ in range(2):
        scroll_sns(sns, notches=3)
        time.sleep(0.45)

    handled = 0
    for page in range(5):
        seps = find_comment_separators(sns)
        print(f"\\n✅ page={page+1} separators={len(seps)}")
        if not seps:
            scroll_sns(sns, notches=6)
            time.sleep(0.9)
            continue

        for sep in seps:
            if handled >= n:
                break
            ok = open_more_and_probe(sns, sep, x_ratio=0.92, y_offset_up=16, auto_click_like=auto_click_like)
            handled += 1 if ok else 0
            time.sleep(0.65)

        if handled >= n:
            break
        scroll_sns(sns, notches=6)
        time.sleep(0.9)

if __name__ == "__main__":
    AUTO_CLICK_LIKE = False  # 先探测，确认命中后再改 True
    demo(n=3, auto_click_like=AUTO_CLICK_LIKE)