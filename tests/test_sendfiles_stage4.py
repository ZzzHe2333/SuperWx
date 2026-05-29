"""Stage 4 test — verify SendFiles logic.

Usage::

    python tests/test_sendfiles_stage4.py                # dry run
    python tests/test_sendfiles_stage4.py --send-file    # actually send
"""

from __future__ import annotations

import argparse
import ctypes
import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from wxauto4 import WeChat
from wxauto4.locator import ctrl_exists


def _create_tmp_file() -> str:
    """Create a temporary txt file for testing."""
    path = os.path.join(os.path.dirname(__file__), 'tmp_wxauto4_file_test.txt')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(f"wxauto4 file test {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    return os.path.abspath(path)


def _activate_window(hwnd: int):
    """Bring WeChat window to foreground."""
    ctypes.windll.user32.ShowWindow(hwnd, 9)  # SW_RESTORE
    time.sleep(0.3)
    ctypes.windll.user32.SetForegroundWindow(hwnd)
    time.sleep(0.5)


def main():
    parser = argparse.ArgumentParser(description="wxauto4 stage 4 SendFiles test")
    parser.add_argument("--send-file", action="store_true", help="Actually send a test file")
    parser.add_argument("--target", type=str, default=None, help="Chat target")
    args = parser.parse_args()

    print("=" * 50)
    print("wxauto4 stage 4 — SendFiles test")
    print("=" * 50)

    # 1. Init
    try:        wx = WeChat()
    except Exception as e:
        print(f"[FAIL] WeChat init: {e}")
        return 1
    print(f"[OK] WeChat: {wx.nickname}")

    # 2. Activate window
    _activate_window(wx._api.HWND)

    # 3. Create temp file
    tmp_file = _create_tmp_file()
    print(f"[OK] temp file: {tmp_file}")
    print(f"     exists: {os.path.exists(tmp_file)}")

    # 4. Switch to target first (for both dry-run and real send)
    if args.target:
        print(f"\n--- 切换到: {args.target} ---")
        result = wx.ChatWith(args.target)
        print(f"[OK] ChatWith: {result}")
        time.sleep(2)
        _activate_window(wx._api.HWND)  # re-activate after switch
        time.sleep(1)
        wx.ChatBox.init()  # re-init to get fresh control references
        time.sleep(0.5)

    # 5. Check editbox (after ChatWith, so we check the correct chat)
    editbox = wx.ChatBox.editbox
    edit_ok = editbox.Exists(2) if editbox else False
    print(f"[{'OK' if edit_ok else 'FAIL'}] editbox exists: {edit_ok}")
    if not edit_ok:
        print("  请确认已打开一个聊天窗口。")
        return 1

    # 6. Check send button
    wx.ChatBox.refresh_send_button()
    sendbtn = wx.ChatBox.sendbtn
    send_ok = sendbtn.Exists(1) if sendbtn else False
    print(f"[{'OK' if send_ok else 'WARN'}] send_button exists: {send_ok}")

    # 7. Dry run or real send
    if not args.send_file:
        print("\n--- Dry run 完成 ---")
        print(f"  文件路径  : {tmp_file}")
        print(f"  文件存在  : {os.path.exists(tmp_file)}")
        print(f"  editbox   : OK")
        print(f"  sendbtn   : {'OK' if send_ok else '未出现'}")
        print("  使用 --send-file 参数可真实发送测试文件。")
        return 0

    # Real send
    print(f"\n--- 发送文件: {tmp_file} ---")
    result = wx.SendFiles(tmp_file)
    print(f"[{'OK' if result.is_success else 'FAIL'}] SendFiles: {result}")

    # Cleanup
    try:
        os.remove(tmp_file)
    except OSError:
        pass

    return 0 if result.is_success else 1


if __name__ == "__main__":
    try:
        code = main()
    except Exception as e:
        print(f"\n运行出错: {e}")
        code = 2
    sys.exit(code)
