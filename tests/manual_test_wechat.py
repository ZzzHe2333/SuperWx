"""Manual WeChat 4.x UI test — interactive, dry-run by default.

Usage::

    python tests/manual_test_wechat.py
    python tests/manual_test_wechat.py --send "test msg"
    python tests/manual_test_wechat.py --send-file path/to/file
    python tests/manual_test_wechat.py --chat-with "文件传输助手"
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
    parser = argparse.ArgumentParser(description="wxauto4 manual test")
    parser.add_argument("--send", type=str, default=None, help="Send a text message")
    parser.add_argument("--send-file", type=str, default=None, help="Send a file")
    parser.add_argument("--chat-with", type=str, default=None, help="Switch to chat target")
    parser.add_argument("--target", type=str, default=None, help="Target for send operations")
    parser.add_argument("--show-messages", action="store_true", help="Print current messages")
    parser.add_argument("--show-sessions", action="store_true", help="Print session list")
    args = parser.parse_args()

    print("=" * 50)
    print("wxauto4 manual test")
    print("=" * 50)

    # 1. Init
    try:
        wx = WeChat()
    except Exception as e:
        print(f"[FAIL] WeChat init: {e}")
        return 1
    print(f"[OK] WeChat: {wx.nickname}")

    # 2. ChatWith
    if args.chat_with:
        print(f"\n--- ChatWith: {args.chat_with} ---")
        result = wx.ChatWith(args.chat_with)
        if isinstance(result, type(None)):
            print(f"[FAIL] ChatWith returned None")
        else:
            print(f"[OK] ChatWith: {result}")

    # 3. Control status
    print("\n--- 控件状态 ---")
    edit_ok = ctrl_exists(wx.ChatBox.editbox)
    print(f"[{'OK' if edit_ok else 'FAIL'}] editbox")
    wx.ChatBox.refresh_send_button()
    send_ok = ctrl_exists(wx.ChatBox.sendbtn)
    print(f"[{'OK' if send_ok else 'WARN'}] sendbtn ({'OK' if send_ok else '输入文字后出现'})")
    msg_ok = ctrl_exists(wx.ChatBox.msgbox)
    print(f"[{'OK' if msg_ok else 'FAIL'}] msgbox")

    # 4. Sessions
    if args.show_sessions:
        print("\n--- 会话列表 ---")
        sessions = wx.GetSession()
        for s in sessions:
            print(f"  {s.name} (未读 {s.unread_count})")

    # 5. Messages
    if args.show_messages:
        print("\n--- 当前消息 ---")
        msgs = wx.GetAllMessage()
        print(f"  共 {len(msgs)} 条")
        for m in msgs[-10:]:
            print(f"  [{m.attr}] {m.sender}: {m.content[:50]}")

    # 6. Send message
    if args.send:
        print(f"\n--- 发送消息 ---")
        result = wx.SendMsg(args.send, who=args.target)
        print(f"[{'OK' if result.is_success else 'FAIL'}] SendMsg: {result}")

    # 7. Send file
    if args.send_file:
        print(f"\n--- 发送文件 ---")
        result = wx.SendFiles(args.send_file, who=args.target)
        print(f"[{'OK' if result.is_success else 'FAIL'}] SendFiles: {result}")

    # 8. Default: just print summary
    if not any([args.send, args.send_file, args.chat_with, args.show_messages, args.show_sessions]):
        print("\n--- 默认模式 (dry run) ---")
        print(f"  昵称     : {wx.nickname}")
        print(f"  editbox  : {'OK' if edit_ok else 'FAIL'}")
        print(f"  sendbtn  : {'OK' if send_ok else '未出现'}")
        print(f"  msgbox   : {'OK' if msg_ok else 'FAIL'}")
        try:
            msgs = wx.GetAllMessage()
            print(f"  消息数量 : {len(msgs)}")
        except Exception:
            print(f"  消息数量 : 无法读取")
        print("\n  使用 --help 查看可选参数。")

    print("\nDone.")
    return 0


if __name__ == "__main__":
    try:
        code = main()
    except Exception as e:
        print(f"\n运行出错: {e}")
        code = 2
    sys.exit(code)
