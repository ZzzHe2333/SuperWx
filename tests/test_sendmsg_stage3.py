"""Stage 3 test — verify SendMsg text sending logic.

Usage::

    python tests/test_sendmsg_stage3.py              # dry run (no real send)
    python tests/test_sendmsg_stage3.py --send       # actually send a message
    python tests/test_sendmsg_stage3.py --send --target 好友名
"""

from __future__ import annotations

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from wxauto4 import WeChat
from wxauto4.locator import ctrl_exists


def main():
    parser = argparse.ArgumentParser(description="wxauto4 stage 3 SendMsg test")
    parser.add_argument("--send", action="store_true", help="Actually send a test message")
    parser.add_argument("--target", type=str, default=None, help="Chat target for send")
    args = parser.parse_args()

    print("=" * 50)
    print("wxauto4 stage 3 — SendMsg test")
    print("=" * 50)

    # 1. Init
    try:
        wx = WeChat()
    except Exception as e:
        print(f"[FAIL] WeChat init: {e}")
        return 1
    print(f"[OK] WeChat: {wx.nickname}")

    # 2. Check editbox
    editbox = wx.ChatBox.editbox
    edit_ok = ctrl_exists(editbox)
    print(f"[{'OK' if edit_ok else 'FAIL'}] editbox exists: {edit_ok}")
    if not edit_ok:
        print("  请确认已打开一个聊天窗口。")
        return 1

    # 3. Check send button (may need text first)
    wx.ChatBox.refresh_send_button()
    sendbtn = wx.ChatBox.sendbtn
    send_ok = ctrl_exists(sendbtn)
    print(f"[{'OK' if send_ok else 'WARN'}] send_button exists: {send_ok}")
    if not send_ok:
        print("  send_button 未找到 — 可能需要先输入文字才会出现。")
        print("  dry_run 模式下跳过发送测试。")
        if not args.send:
            return 0

    # 4. Dry run or real send
    if not args.send:
        print("\n--- Dry run 完成 ---")
        print("  editbox  : OK")
        print("  sendbtn  :", "OK" if send_ok else "未出现（输入文字后才会出现）")
        print("  使用 --send 参数可真实发送测试消息。")
        return 0

    # Real send
    msg = f"wxauto4 test {time.strftime('%Y-%m-%d %H:%M:%S')}"
    print(f"\n--- 发送消息: {msg} ---")
    result = wx.SendMsg(msg, who=args.target)
    print(f"[{'OK' if result.is_success else 'FAIL'}] SendMsg: {result}")
    return 0 if result.is_success else 1


if __name__ == "__main__":
    try:
        code = main()
    except Exception as e:
        print(f"\n运行出错: {e}")
        code = 2
    sys.exit(code)
