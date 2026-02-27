import sys
import os
import time
from collections import deque

ROOT = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(ROOT)
if PROJ not in sys.path:
    sys.path.insert(0, PROJ)

from wxauto4.uia import uiautomation as uia


KEYWORDS = [
    "朋友圈", "动态", "朋友", "相机", "拍照", "视频", "发表", "发布", "刷新",
    "赞", "取消", "评论", "更多", "…", "..."
]

def safe_get(obj, attr, default=""):
    try:
        v = getattr(obj, attr)
        return v if v is not None else default
    except Exception:
        return default

def ctype(c): return safe_get(c, "ControlTypeName", "")
def cname(c): return safe_get(c, "Name", "") or ""
def cclass(c): return safe_get(c, "ClassName", "") or ""
def caid(c): return safe_get(c, "AutomationId", "") or ""

def summary(c, max_len=60):
    n = cname(c).replace("\n", "\\n")
    if len(n) > max_len: n = n[:max_len] + "…"
    cls = cclass(c)
    aid = caid(c)
    return f"type={ctype(c)} | name='{n}' | class='{cls}' | aid='{aid}'"

def find_wechat_main():
    root = uia.GetRootControl()
    best = None
    best_score = -1
    for w in root.GetChildren():
        if ctype(w) != "WindowControl":
            continue
        n = cname(w)
        cls = cclass(w)
        if cls == "mmui::MainWindow" or n == "微信" or "WeChat" in n:
            score = 0
            if cls == "mmui::MainWindow": score += 10
            if n == "微信": score += 5
            if "WeChat" in n: score += 3
            if score > best_score:
                best = w
                best_score = score
    return best

def click_tab_moments(main):
    tab = main.ButtonControl(Name="朋友圈")
    if tab and tab.Exists(0, 0):
        tab.Click()
        time.sleep(0.6)
        return True
    # 兜底：遍历找
    for ch in main.GetChildren():
        if ctype(ch) == "ButtonControl" and ("朋友圈" in cname(ch)):
            ch.Click()
            time.sleep(0.6)
            return True
    return False

def keyword_hit(text: str):
    t = (text or "").lower()
    for k in KEYWORDS:
        if k.lower() in t:
            return True
    return False

def score_scope(scope):
    """
    给一个窗口/容器打分：越像朋友圈分越高
    """
    s = 0
    # 窗口本身的 name/class
    if keyword_hit(cname(scope)): s += 8
    if "moment" in cclass(scope).lower(): s += 10
    if "timeline" in cclass(scope).lower(): s += 6
    if "friend" in cclass(scope).lower(): s += 4

    # 扫描子控件（限制数量）
    q = deque([scope])
    seen = 0
    while q and seen < 3000:
        cur = q.popleft()
        seen += 1
        txt = f"{ctype(cur)} {cname(cur)} {cclass(cur)} {caid(cur)}"
        if keyword_hit(txt):
            s += 1
        # 赞/评论/取消 命中权重高
        n = cname(cur)
        if n in ("赞", "取消", "评论"):
            s += 10
        try:
            for ch in cur.GetChildren():
                q.append(ch)
        except Exception:
            pass
    return s

def list_candidate_windows():
    root = uia.GetRootControl()
    wins = []
    for w in root.GetChildren():
        if ctype(w) != "WindowControl":
            continue
        wins.append(w)
    # 打分排序
    scored = [(score_scope(w), w) for w in wins]
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored

def print_hits(scope, max_hits=80):
    """
    打印 scope 内命中关键词的控件（用于你把关键信息贴我）
    """
    print("\n--- 命中关键词的控件（截取）---")
    q = deque([scope])
    seen = 0
    hits = 0
    while q and seen < 12000 and hits < max_hits:
        cur = q.popleft()
        seen += 1
        txt = f"{ctype(cur)} {cname(cur)} {cclass(cur)} {caid(cur)}"
        if keyword_hit(txt):
            print("  " + summary(cur))
            hits += 1
        try:
            for ch in cur.GetChildren():
                q.append(ch)
        except Exception:
            pass
    print(f"--- end (seen={seen}, hits={hits}) ---\n")

if __name__ == "__main__":
    print("请先打开微信主窗口（不要最小化），并登录。\n")
    main = find_wechat_main()
    if not main:
        print("❌ 没找到微信主窗口 mmui::MainWindow")
        sys.exit(1)

    print("✅ 主窗口：")
    print(summary(main))

    ok = click_tab_moments(main)
    if not ok:
        print("❌ 点击“朋友圈”失败")
        sys.exit(1)

    print("✅ 已点击“朋友圈”，开始在所有窗口中探测朋友圈 scope…")
    time.sleep(1.2)

    scored = list_candidate_windows()
    print("\n=== Top 8 窗口候选（按“像朋友圈程度”排序）===\n")
    for i, (s, w) in enumerate(scored[:8], 1):
        print(f"[{i}] score={s:>4}  {summary(w)}")

    # 选第一名打印命中详情
    best_score, best_win = scored[0]
    print(f"\n✅ 选择 score 最高的窗口作为朋友圈 scope：score={best_score}")
    print(summary(best_win))
    print_hits(best_win, max_hits=120)