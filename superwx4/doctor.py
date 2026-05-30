"""superwx4 doctor — health check for WeChat 4.x UI controls.

Usage::

    python -m superwx4 doctor
    python -m superwx4 doctor --report
    python -m superwx4 doctor --dump-on-fail

Outputs OK / FAILED for each core control, plus window metadata.
Optionally writes a TXT report and dumps UI tree on failure.
"""

from __future__ import annotations

import os
import sys
import time
from typing import Dict, List, Tuple

from superwx4.locator import (
    ctrl_exists,
    find_first,
    find_wechat_window,
    describe_control,
    SELECTORS,
)


def _check(label: str, ok: bool, hint: str = "") -> bool:
    status = "OK" if ok else "FAILED"
    line = f"{label:<25s} {status}"
    if not ok and hint:
        line += f"  ({hint})"
    print(line)
    return ok


def run_doctor(report_path: str = None, dump_on_fail: bool = False) -> int:
    """Probe all core UI controls. Returns 0 on success, 1 on any failure.

    Args:
        report_path: Optional path to write TXT report.
        dump_on_fail: If True, dump UI tree and generate repair_context on failure.
    """
    lines: List[str] = []
    _log = lambda s="": (print(s), lines.append(s))

    _log("=" * 60)
    _log("superwx4 doctor — WeChat 4.x UI health check")
    _log("=" * 60)
    _log()

    failed_controls: Dict[str, str] = {}
    all_ok = True

    # 1. main window
    root = find_wechat_window()
    ok = root is not None and ctrl_exists(root)
    _check("main_window", ok, "未找到微信主窗口，请确认微信已登录且可见")
    if not ok:
        failed_controls["main_window"] = "未找到微信主窗口"
        _log("\n无法继续 — 主窗口未找到。")
        _write_report(lines, report_path)
        if dump_on_fail:
            _auto_dump(root, failed_controls)
        return 1

    info = describe_control(root)
    _log(f"  Name       : {info.get('Name', '?')}")
    _log(f"  ClassName  : {info.get('ClassName', '?')}")
    rect = info.get("BoundingRectangle", {})
    _log(f"  Rect       : left={rect.get('left','?')} top={rect.get('top','?')} right={rect.get('right','?')} bottom={rect.get('bottom','?')}")
    _log()

    # 2~8. probe each selector
    probe_keys = [
        ("chat_message_page", "请确认已打开某个聊天窗口"),
        ("message_view", "请确认已打开某个聊天窗口"),
        ("chat_message_list", "请确认已打开某个聊天窗口"),
        ("input_view", "请确认已打开某个聊天窗口"),
        ("chat_input_field", "请确认已打开某个聊天窗口"),
        ("send_button", "请先在聊天输入框输入几个字（不要发送），然后重新运行 doctor"),
        ("session_list", "请确认微信主界面会话列表可见"),
    ]

    for key, hint in probe_keys:
        ctrl = find_first(root, key)
        ok = ctrl is not None and ctrl_exists(ctrl)
        _check(key, ok, hint)
        all_ok = all_ok and ok

        if not ok:
            failed_controls[key] = hint

        # Print selector info for each control
        if ok:
            info = describe_control(ctrl)
            _log(f"  -> Name={info.get('Name','')!r} Class={info.get('ClassName','')!r} AID={info.get('AutomationId','')!r}")

    # summary
    _log()
    if all_ok:
        _log("所有控件检测通过！")
    else:
        _log("部分控件未找到，请参考上方提示。")

    _write_report(lines, report_path)

    # Auto-dump on failure
    if dump_on_fail and failed_controls:
        _auto_dump(root, failed_controls)

    return 0 if all_ok else 1


def _auto_dump(root, failed_controls: Dict[str, str]):
    """Dump UI tree and generate repair_context when doctor fails."""
    if root is None:
        print("\n无法 dump — 主窗口未找到。")
        return

    from superwx4.locator.dump import dump_ui_tree
    from superwx4.locator.repair_context import generate_repair_context

    print("\n--- 自动 dump UI 树 ---")
    try:
        dump_dir = dump_ui_tree(root, output_dir=".superwx4_repair/dumps")
        print(f"UI 树已保存到: {dump_dir}")
    except Exception as e:
        print(f"dump 失败: {e}")
        dump_dir = ".superwx4_repair/dumps"

    print("\n--- 生成修复上下文 ---")
    try:
        ctx_path = generate_repair_context(failed_controls, dump_dir=dump_dir)
        print(f"repair_context 已保存到: {ctx_path}")
        print(f"\n请将 {ctx_path} 喂给 AI，让它生成修复 patch。")
    except Exception as e:
        print(f"生成 repair_context 失败: {e}")


def _write_report(lines: List[str], path: str = None):
    if not path:
        return
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        print(f"\n报告已保存: {path}")
    except Exception as e:
        print(f"\n保存报告失败: {e}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="superwx4 doctor")
    parser.add_argument("--report", nargs="?", const="superwx4_doctor_report.txt", help="Save TXT report")
    parser.add_argument("--dump-on-fail", action="store_true", help="Dump UI tree and generate repair_context on failure")
    args = parser.parse_args()

    try:
        code = run_doctor(report_path=args.report, dump_on_fail=args.dump_on_fail)
    except Exception as e:
        print(f"\n运行出错: {e}")
        code = 2
    sys.exit(code)


if __name__ == "__main__":
    main()
# 1
