"""Probe WeChat 4.x UI controls and print OK / FAILED for each.

This script is read-only — it does NOT send messages, click buttons,
or modify WeChat state in any way.

Usage::

    python tests/probe_wechat_locator.py

Prerequisites:
    - WeChat must be open and logged in.
    - You must be inside a specific chat window (not the main session list).
    - If send_button shows FAILED, type a few characters in the chat input
      box (do NOT send), then re-run this script.
"""

from __future__ import annotations

import os
import sys

# Allow running from project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from wxauto4.locator import (
    ctrl_exists,
    find_first,
    find_wechat_window,
    describe_control,
    SELECTORS,
)


def _check(label: str, ok: bool, hint: str = "") -> bool:
    """Print a single probe result."""
    status = "OK" if ok else "FAILED"
    line = f"{label:<25s} {status}"
    if not ok and hint:
        line += f"  ({hint})"
    print(line)
    return ok


def main() -> int:
    print("=" * 55)
    print("wxauto4 probe — WeChat 4.x UI control locator test")
    print("=" * 55)
    print()

    all_ok = True

    # 1. main window
    root = find_wechat_window()
    ok = root is not None and ctrl_exists(root)
    _check("main_window", ok, "未找到微信主窗口，请确认微信已登录且可见")
    if not ok:
        print("\n无法继续 — 主窗口未找到。")
        return 1

    print(f"  Name  : {root.Name}")
    print(f"  Class : {root.ClassName}")
    print()

    # 2~8. probe each selector key
    probe_keys = [
        ("chat_message_page", "请确认已打开某个聊天窗口"),
        ("message_view", "请确认已打开某个聊天窗口"),
        ("chat_message_list", "请确认已打开某个聊天窗口"),
        ("input_view", "请确认已打开某个聊天窗口"),
        ("chat_input_field", "请确认已打开某个聊天窗口"),
        ("send_button", "请先在聊天输入框输入几个字（不要发送），然后重新运行"),
        ("session_list", "请确认微信主界面会话列表可见"),
    ]

    for key, hint in probe_keys:
        ctrl = find_first(root, key)
        ok = ctrl is not None and ctrl_exists(ctrl)
        _check(key, ok, hint)
        all_ok = all_ok and ok

    # summary
    print()
    if all_ok:
        print("所有控件检测通过！")
        return 0
    else:
        print("部分控件未找到，请参考上方提示。")
        return 1


if __name__ == "__main__":
    try:
        code = main()
    except Exception as e:
        print(f"\n运行出错: {e}")
        code = 2
    sys.exit(code)
