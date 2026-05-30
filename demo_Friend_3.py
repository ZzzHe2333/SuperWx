# -*- coding: utf-8 -*-
"""Demo: 给最新 N 条朋友圈点赞（接入 wxauto4 API）。

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

from wxauto4 import WeChat
from wxauto4.moment import Moment


def like_first_n_posts(n: int = 3):
    wx = WeChat()

    # 切换到朋友圈
    print("[1] 切换到朋友圈...")
    wx.SwitchToMoments()
    time.sleep(2)

    # 使用 Moment.LikeLatest() 点赞
    moment = Moment(wx)
    print(f"[2] 点赞最新 {n} 条...")
    result = moment.LikeLatest(n=n, max_pages=10)

    print(f"    {result['message']}")


if __name__ == "__main__":
    like_first_n_posts(n=3)
