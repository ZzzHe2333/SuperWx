# -*- coding: utf-8 -*-
"""Demo: 给最新 N 条朋友圈点赞（接入 superwx4 API）。

朋友圈功能当前不稳定，默认不可用。
需要传 _force=True 才能执行。

Run:
    cd e:\\github\\SuperWx
    python demo_Friend_3.py
"""
import sys
import os
import time

CUR = os.path.dirname(os.path.abspath(__file__))
if CUR not in sys.path:
    sys.path.insert(0, CUR)

from superwx4 import WeChat
from superwx4.moment import Moment


def like_first_n_posts(n: int = 3, force: bool = False):
    wx = WeChat()

    # 激活微信窗口
    try:
        wx._api.control.SetFocus()
    except:
        pass
    time.sleep(0.3)

    # 切换到朋友圈
    print("[1] 切换到朋友圈...")
    wx.SwitchToMoments()
    time.sleep(2)

    # 点赞（需要 _force=True）
    moment = Moment(wx, _force=force)
    print(f"[2] 点赞最新 {n} 条...")
    result = moment.LikeLatest(n=n, max_pages=10)
    print(f"    {result['message']}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--force', action='store_true', help='强制执行朋友圈操作')
    parser.add_argument('-n', type=int, default=3, help='点赞条数')
    args = parser.parse_args()

    like_first_n_posts(n=args.n, force=args.force)
