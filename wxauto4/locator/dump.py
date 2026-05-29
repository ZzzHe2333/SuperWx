"""Dump WeChat UI tree for debugging and AI-assisted repair.

Usage::

    from wxauto4.locator.dump import dump_ui_tree
    path = dump_ui_tree(root_control, output_dir=".wxauto4_repair/dumps")
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from wxauto4 import uia
from wxauto4.locator.engine import safe_get


def _walk_control(ctrl, depth: int = 0, max_depth: int = 10) -> Dict[str, Any]:
    """Recursively walk a control tree and return a dict representation."""
    node: Dict[str, Any] = {
        "depth": depth,
        "ControlType": safe_get(ctrl, "ControlTypeName", "?"),
        "ClassName": safe_get(ctrl, "ClassName", ""),
        "AutomationId": safe_get(ctrl, "AutomationId", ""),
        "Name": safe_get(ctrl, "Name", ""),
    }
    rect = safe_get(ctrl, "BoundingRectangle")
    if rect:
        try:
            node["Rect"] = {
                "left": rect.left, "top": rect.top,
                "right": rect.right, "bottom": rect.bottom,
            }
        except Exception:
            pass

    children: List[Dict] = []
    if depth < max_depth:
        try:
            for child in ctrl.GetChildren():
                children.append(_walk_control(child, depth + 1, max_depth))
        except Exception:
            pass
    if children:
        node["children"] = children
    return node


def _flatten_tree(node: Dict, lines: List[str], prefix: str = ""):
    """Convert tree dict to indented text lines."""
    ctrl_type = node.get("ControlType", "?")
    cls = node.get("ClassName", "")
    aid = node.get("AutomationId", "")
    name = node.get("Name", "")
    label = f"{ctrl_type}"
    if cls:
        label += f"  Class={cls}"
    if aid:
        label += f"  AID={aid}"
    if name:
        display = name[:40] + "..." if len(name) > 40 else name
        label += f"  Name={display!r}"
    lines.append(f"{prefix}{label}")
    for child in node.get("children", []):
        _flatten_tree(child, lines, prefix + "  ")


def dump_ui_tree(
    root: uia.Control,
    output_dir: str = ".wxauto4_repair/dumps",
    max_depth: int = 8,
) -> str:
    """Dump the UI tree rooted at `root` to JSON + TXT files.

    Returns the directory path containing the dump files.
    """
    os.makedirs(output_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    tree = _walk_control(root, max_depth=max_depth)

    # JSON
    json_path = os.path.join(output_dir, f"dump_wechat_ui_{ts}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(tree, f, ensure_ascii=False, indent=2)

    # TXT
    lines: List[str] = []
    _flatten_tree(tree, lines)
    txt_path = os.path.join(output_dir, f"dump_wechat_ui_{ts}.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    # Summary
    summary_path = os.path.join(output_dir, f"dump_wechat_ui_{ts}_summary.txt")
    summary = _build_summary(tree)
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(summary)

    return output_dir


def _build_summary(tree: Dict) -> str:
    """Build a short summary of key controls for repair_context."""
    collected: List[str] = []
    _collect_interesting(tree, collected)
    header = "WeChat UI Tree Summary\n"
    header += f"Collected {len(collected)} interesting controls\n\n"
    return header + "\n".join(collected)


def _collect_interesting(node: Dict, out: List[str]):
    """Collect controls that have AutomationId or known class names."""
    aid = node.get("AutomationId", "")
    cls = node.get("ClassName", "")
    name = node.get("Name", "")
    if aid or "mmui::" in cls:
        rect = node.get("Rect", {})
        out.append(
            f"Class={cls:<40s} AID={aid:<40s} Name={name!r:<30s} "
            f"Rect=({rect.get('left','')},{rect.get('top','')},{rect.get('right','')},{rect.get('bottom','')})"
        )
    for child in node.get("children", []):
        _collect_interesting(child, out)
