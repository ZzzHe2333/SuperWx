"""Patch guard — validate that AI-generated patches only touch allowed files.

Usage::

    from wxauto4.locator.patch_guard import validate_patch
    ok, errors = validate_patch("path/to/patch.diff")
"""

from __future__ import annotations

import os
import re
from typing import List, Tuple


# Files that may be modified by AI patches
ALLOWED_PATH_PREFIXES = [
    "wxauto4/locator/",
    "wxauto4/ui/chatbox.py",
    "wxauto4/ui/main.py",
    "wxauto4/ui/sessionbox.py",
    "tests/",
]

# Files that must never be touched
FORBIDDEN_PATH_PREFIXES = [
    "wxauto4/utils/useful.py",
    "wxauto4/param.py",
]

# Dangerous patterns in added lines
FORBIDDEN_PATTERNS = [
    (r'\beval\s*\(', "eval() call"),
    (r'\bexec\s*\(', "exec() call"),
    (r'\bos\.system\s*\(', "os.system() call"),
    (r'\bsubprocess\.call\s*\(', "subprocess.call() — use subprocess.run instead"),
    (r'\brequests\.post\s*\(.*https?://', "requests.post() to external URL"),
    (r'\burllib\.request\.urlopen\s*\(', "urllib request to external URL"),
    (r'\b__import__\s*\(', "dynamic __import__"),
]


def validate_patch(patch_path: str) -> Tuple[bool, List[str]]:
    """Validate a unified diff patch file.

    Returns (ok, list_of_errors).
    """
    if not os.path.exists(patch_path):
        return False, [f"Patch file not found: {patch_path}"]

    with open(patch_path, "r", encoding="utf-8") as f:
        content = f.read()

    errors: List[str] = []
    modified_files = _extract_modified_files(content)

    for fpath in modified_files:
        # Check forbidden
        for forbidden in FORBIDDEN_PATH_PREFIXES:
            if fpath.startswith(forbidden) or fpath == forbidden:
                errors.append(f"Forbidden file modified: {fpath}")

        # Check not in allowed list
        allowed = any(fpath.startswith(p) or fpath == p for p in ALLOWED_PATH_PREFIXES)
        if not allowed:
            errors.append(f"File not in allowed list: {fpath}")

    # Check for dangerous patterns in added lines
    added_lines = _extract_added_lines(content)
    for line_no, line in added_lines:
        for pattern, desc in FORBIDDEN_PATTERNS:
            if re.search(pattern, line):
                errors.append(f"Line {line_no}: {desc} — {line.strip()[:80]}")

    return len(errors) == 0, errors


def _extract_modified_files(content: str) -> List[str]:
    """Extract file paths from unified diff headers (--- a/... +++ b/...)."""
    files = []
    for match in re.finditer(r'^\+\+\+ b/(.+)$', content, re.MULTILINE):
        files.append(match.group(1).strip())
    return files


def _extract_added_lines(content: str) -> List[Tuple[int, str]]:
    """Extract lines that start with + (added lines) with line numbers."""
    result = []
    line_no = 0
    for line in content.splitlines():
        line_no += 1
        if line.startswith('+') and not line.startswith('+++'):
            result.append((line_no, line[1:]))
    return result


def guard_report(patch_path: str) -> str:
    """Run validation and return a human-readable report string."""
    ok, errors = validate_patch(patch_path)
    lines = ["Patch Guard Report"]
    lines.append(f"Patch: {patch_path}")
    lines.append(f"Result: {'PASS' if ok else 'FAIL'}")
    if errors:
        lines.append("")
        lines.append("Errors:")
        for e in errors:
            lines.append(f"  - {e}")
    return "\n".join(lines)
