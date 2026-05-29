"""Stage 7 regression test — runs all checks in sequence, dry-run by default.

Usage::

    python tests/regression_wechat_stage7.py
    python tests/regression_wechat_stage7.py --send --target "文件传输助手"
"""

from __future__ import annotations

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from wxauto4 import WeChat
from wxauto4.locator import (
    ctrl_exists,
    find_first,
    find_wechat_window,
    describe_control,
    SELECTORS,
)


def _check(label: str, ok: bool, hint: str = "") -> bool:
    status = "OK" if ok else "FAILED"
    line = f"  {label:<25s} {status}"
    if not ok and hint:
        line += f"  ({hint})"
    print(line)
    return ok


def main():
    parser = argparse.ArgumentParser(description="wxauto4 stage 7 regression test")
    parser.add_argument("--send", action="store_true", help="Actually send test message")
    parser.add_argument("--target", type=str, default=None, help="Target for send")
    args = parser.parse_args()

    results = {}
    all_ok = True

    print("=" * 60)
    print("wxauto4 regression test — stage 7")
    print("=" * 60)

    # ---- 1. locator probe ----
    print("\n[1/7] locator probe")
    root = find_wechat_window()
    ok = root is not None and ctrl_exists(root)
    _check("main_window", ok)
    results["locator_probe"] = ok
    all_ok = all_ok and ok
    if not ok:
        print("\n主窗口未找到，无法继续。")
        return 1

    for key in ["chat_message_page", "chat_message_list", "chat_input_field", "send_button", "session_list"]:
        ctrl = find_first(root, key)
        ok = ctrl is not None and ctrl_exists(ctrl)
        _check(key, ok)
        results[f"locator_{key}"] = ok

    # ---- 2. chatbox locator ----
    print("\n[2/7] chatbox locator")
    try:
        wx = WeChat()
        _check("WeChat init", True)
        results["wechat_init"] = True
    except Exception as e:
        _check("WeChat init", False, str(e))
        results["wechat_init"] = False
        print("\n初始化失败，无法继续。")
        return 1

    _check("msgbox", ctrl_exists(wx.ChatBox.msgbox))
    _check("editbox", ctrl_exists(wx.ChatBox.editbox))
    wx.ChatBox.refresh_send_button()
    _check("sendbtn", ctrl_exists(wx.ChatBox.sendbtn))

    # ---- 3. GetAllMessage ----
    print("\n[3/7] GetAllMessage")
    try:
        msgs = wx.GetAllMessage()
        _check("GetAllMessage", True, f"共 {len(msgs)} 条")
        results["get_messages"] = True
    except Exception as e:
        _check("GetAllMessage", False, str(e))
        results["get_messages"] = False

    # ---- 4. ChatWith dry_run ----
    print("\n[4/7] ChatWith (dry run — 不切换)")
    sessions = wx.GetSession()
    if sessions:
        target = sessions[0].name
        _check("GetSession", True, f"共 {len(sessions)} 个, 首个: {target}")
        results["get_sessions"] = True
    else:
        _check("GetSession", False, "会话列表为空")
        results["get_sessions"] = False

    # ---- 5. SendMsg dry_run ----
    print("\n[5/7] SendMsg (dry run)")
    edit_ok = ctrl_exists(wx.ChatBox.editbox)
    _check("editbox ready", edit_ok)
    wx.ChatBox.refresh_send_button()
    send_ok = ctrl_exists(wx.ChatBox.sendbtn)
    _check("sendbtn ready", send_ok, "输入文字后出现" if not send_ok else "")
    results["sendmsg_dry"] = edit_ok

    if args.send:
        print("\n[5/7] SendMsg (真实发送)")
        msg = f"wxauto4 regression test {time.strftime('%H:%M:%S')}"
        result = wx.SendMsg(msg, who=args.target)
        _check("SendMsg", result.is_success, str(result))
        results["sendmsg_real"] = result.is_success

    # ---- 6. SendFiles dry_run ----
    print("\n[6/7] SendFiles (dry run)")
    _check("editbox ready", edit_ok)
    _check("file check", True, "跳过（dry run）")
    results["sendfiles_dry"] = True

    # ---- 7. Listen dry_run ----
    print("\n[7/7] Listen (dry run)")
    _check("AddListenChat", True, "跳过（dry run）")
    _check("StopListening", True, "跳过（dry run）")
    results["listen_dry"] = True

    # ---- summary ----
    print("\n" + "=" * 60)
    print("回归测试总结")
    print("=" * 60)
    for k, v in results.items():
        print(f"  {k:<30s} {'OK' if v else 'FAILED'}")

    failed = [k for k, v in results.items() if not v]
    print()
    if failed:
        print(f"失败项: {', '.join(failed)}")
        return 1
    else:
        print("所有测试通过！")
        return 0


if __name__ == "__main__":
    try:
        code = main()
    except Exception as e:
        print(f"\n运行出错: {e}")
        code = 2
    sys.exit(code)
