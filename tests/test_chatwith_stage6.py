"""Stage 6 test — verify ChatWith session switching.

Usage::

    python tests/test_chatwith_stage6.py --name "目标聊天名"
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from wxauto4 import WeChat
from wxauto4.locator import ctrl_exists


def main():
    parser = argparse.ArgumentParser(description="wxauto4 stage 6 ChatWith test")
    parser.add_argument("--name", type=str, required=True, help="Target chat name")
    parser.add_argument("--exact", action="store_true", default=True, help="Exact match (default)")
    parser.add_argument("--no-exact", dest="exact", action="store_false", help="Fuzzy match")
    args = parser.parse_args()

    print("=" * 50)
    print("wxauto4 stage 6 — ChatWith test")
    print("=" * 50)

    # 1. Init
    try:
        wx = WeChat()
    except Exception as e:
        print(f"[FAIL] WeChat init: {e}")
        return 1
    print(f"[OK] WeChat: {wx.nickname}")

    # 2. Switch chat
    print(f"\n--- 切换到: {args.name} ---")
    result = wx.ChatWith(args.name, exact=args.exact)
    if isinstance(result, type(None)):
        print(f"[FAIL] ChatWith returned None — 未找到目标会话")
        return 1
    print(f"[OK] ChatWith returned: {result}")

    # 3. Verify controls after switch
    # Note: ChatBox.control is XSplitterView, its parent is ChatMessagePage.
    parent = wx.ChatBox.control.GetParentControl()
    page_ok = ctrl_exists(parent) and getattr(parent, 'AutomationId', '') == 'chat_message_page'
    print(f"[{'OK' if page_ok else 'FAIL'}] chat_message_page: {page_ok}")

    msg_ok = ctrl_exists(wx.ChatBox.msgbox)
    print(f"[{'OK' if msg_ok else 'FAIL'}] chat_message_list: {msg_ok}")

    edit_ok = ctrl_exists(wx.ChatBox.editbox)
    print(f"[{'OK' if edit_ok else 'FAIL'}] chat_input_field: {edit_ok}")

    # 4. Summary
    print()
    if page_ok and msg_ok and edit_ok:
        print("ChatWith 切换成功，所有控件正常。")
        return 0
    else:
        print("部分控件异常，请检查。")
        return 1


if __name__ == "__main__":
    try:
        code = main()
    except Exception as e:
        print(f"\n运行出错: {e}")
        code = 2
    sys.exit(code)
