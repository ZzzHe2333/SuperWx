"""Generate repair_context.md when doctor detects failed controls.

The repair_context.md file is designed to be fed to an AI that will
generate a unified diff patch to fix broken selectors.

Usage::

    from superwx4.locator.repair_context import generate_repair_context
    path = generate_repair_context(failed_controls, dump_dir=".superwx4_repair/dumps")
"""

from __future__ import annotations

import os
import time
from datetime import datetime
from typing import Dict, List, Tuple

from superwx4.locator.selectors import SELECTORS


def generate_repair_context(
    failed_controls: Dict[str, str],
    dump_dir: str = ".superwx4_repair/dumps",
    output_dir: str = ".superwx4_repair/reports",
) -> str:
    """Generate a repair_context.md file for AI-assisted selector repair.

    Args:
        failed_controls: dict of {control_key: hint_string} for controls that failed.
        dump_dir: directory containing UI tree dumps.
        output_dir: directory to write the report.

    Returns:
        Path to the generated repair_context.md.
    """
    os.makedirs(output_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(output_dir, f"repair_context_{ts}.md")

    # Find latest dump file
    dump_summary = _find_latest_dump(dump_dir)

    lines: List[str] = []
    lines.append("# superwx4 Repair Context")
    lines.append("")
    lines.append(f"Generated: {datetime.now().isoformat()}")
    lines.append("")

    # Failed controls
    lines.append("## Failed Controls")
    lines.append("")
    for key, hint in failed_controls.items():
        lines.append(f"### {key}")
        lines.append(f"- Hint: {hint}")
        lines.append(f"- Current selectors:")
        for sel in SELECTORS.get(key, []):
            lines.append(f"  - `{sel}`")
        lines.append("")

    # UI tree summary
    lines.append("## Current UI Tree Summary")
    lines.append("")
    if dump_summary:
        lines.append("```")
        lines.append(dump_summary)
        lines.append("```")
    else:
        lines.append("(No dump file found — run doctor with --dump-on-fail first)")
    lines.append("")

    # Constraints
    lines.append("## Repair Constraints")
    lines.append("")
    lines.append("1. **优先修改 `superwx4/locator/selectors.py`** — 只改 selector，不改业务逻辑。")
    lines.append("2. **不要删除旧 fallback** — 只能新增 fallback 条目。")
    lines.append("3. **不要修改授权/license/auth/网络代码** — `utils/useful.py` 等。")
    lines.append("4. **不要把发送表情/发送文件/发送收藏按钮当作发送消息按钮。**")
    lines.append("5. **不要用 chat_input_field 的 Name 定位** — Name 会随输入内容变化。")
    lines.append("6. **输出 unified diff patch** — 格式：`git diff` 输出。")
    lines.append("")

    # Allowed files
    lines.append("## Allowed Modification Targets")
    lines.append("")
    lines.append("- `superwx4/locator/selectors.py`")
    lines.append("- `superwx4/locator/engine.py`")
    lines.append("- `superwx4/ui/chatbox.py`")
    lines.append("- `superwx4/ui/main.py`")
    lines.append("- `superwx4/ui/sessionbox.py`")
    lines.append("- `tests/`")
    lines.append("")

    # Forbidden files
    lines.append("## Forbidden Modification Targets")
    lines.append("")
    lines.append("- `superwx4/utils/useful.py` (auth/license)")
    lines.append("- Any file containing `eval`, `exec`, `os.system`, dangerous `subprocess`")
    lines.append("- Any file uploading UI tree or chat content to external servers")
    lines.append("")

    # Expected output format
    lines.append("## Expected AI Output")
    lines.append("")
    lines.append("Please output a **unified diff patch** that:")
    lines.append("1. Updates `superwx4/locator/selectors.py` with new/modified selectors.")
    lines.append("2. Keeps existing fallback chains intact.")
    lines.append("3. Can be applied with `git apply`.")
    lines.append("")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    return path


def _find_latest_dump(dump_dir: str) -> str:
    """Read the latest dump summary file."""
    if not os.path.isdir(dump_dir):
        return ""
    summaries = sorted(
        [f for f in os.listdir(dump_dir) if f.endswith("_summary.txt")],
        reverse=True,
    )
    if not summaries:
        return ""
    try:
        with open(os.path.join(dump_dir, summaries[0]), "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""
# 1
