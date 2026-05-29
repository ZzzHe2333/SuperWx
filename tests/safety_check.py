"""Safety check: scan codebase for dangerous patterns that should never appear.

Usage:
    python tests/safety_check.py
    python tests/safety_check.py --verbose
"""
import sys
import os
import re
import argparse

# Files that MUST NOT be modified by AI patches
PROTECTED_FILES = [
    "wxauto4/utils/useful.py",
    "wxauto4/param.py",
    "wxauto4/utils/__init__.py",
]

# Dangerous patterns (regex)
DANGEROUS_PATTERNS = [
    (r'\beval\s*\(', "eval() call"),
    (r'\bexec\s*\(', "exec() call"),
    (r'\bos\.system\s*\(', "os.system() call"),
    (r'\bos\.popen\s*\(', "os.popen() call"),
    (r'subprocess\.call\s*\(.*shell\s*=\s*True', "subprocess with shell=True"),
    (r'subprocess\.Popen\s*\(.*shell\s*=\s*True', "subprocess with shell=True"),
    (r'requests\.post\s*\([^)]*chat', "uploading chat content via requests"),
    (r'urllib\.request\.urlopen\s*\([^)]*chat', "uploading chat content via urllib"),
]

# Default-send patterns: code that sends real messages without explicit user flag
DEFAULT_SEND_PATTERNS = [
    (r'dry_run\s*=\s*False', "dry_run=False (default real execution)"),
]

# Files to scan
SCAN_DIRS = ["wxauto4", "openclaw_skill", "wxauto4_mcp"]
SCAN_EXTENSIONS = {".py"}


def scan_file(filepath: str, verbose: bool = False) -> list:
    """Scan a single file for dangerous patterns. Returns list of (line_num, pattern_desc, line)."""
    findings = []
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
    except Exception:
        return findings

    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        # Skip regex pattern definitions (strings containing \b, \s, etc.)
        if stripped.startswith("(r'") or stripped.startswith('(r"'):
            continue
        if "FORBIDDEN_PATTERNS" in stripped or "DANGEROUS_PATTERNS" in stripped:
            continue
        for pattern, desc in DANGEROUS_PATTERNS:
            if re.search(pattern, line):
                findings.append((i, desc, stripped))
    return findings


def check_protected_files() -> list:
    """Check if protected files have been modified since last commit."""
    import subprocess
    findings = []
    for pf in PROTECTED_FILES:
        if not os.path.exists(pf):
            continue
        try:
            result = subprocess.run(
                ["git", "diff", "--name-only", "HEAD", "--", pf],
                capture_output=True, text=True, cwd=os.path.dirname(os.path.dirname(__file__)) or "."
            )
            if pf.replace("/", os.sep) in result.stdout or pf in result.stdout:
                findings.append((0, f"Protected file modified: {pf}", ""))
        except Exception:
            pass
    return findings


def scan_directory(dirpath: str, verbose: bool = False) -> list:
    """Recursively scan a directory."""
    # Files that contain os.system etc. as part of original codebase (not new additions)
    KNOWN_SAFE_FILES = {
        "wxauto4/wx.py",  # ShutDown() uses os.system(taskkill) — original code
    }

    all_findings = []
    for root, dirs, files in os.walk(dirpath):
        # Skip __pycache__, .git, node_modules
        dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git", "node_modules", ".wxauto4_repair")]
        for fname in files:
            if not any(fname.endswith(ext) for ext in SCAN_EXTENSIONS):
                continue
            fpath = os.path.join(root, fname)
            rel = os.path.relpath(fpath, os.path.dirname(os.path.dirname(__file__)) or ".")
            if rel.replace(os.sep, "/") in KNOWN_SAFE_FILES:
                continue
            findings = scan_file(fpath, verbose)
            if findings:
                for line_num, desc, line in findings:
                    all_findings.append((f"{rel}:{line_num}", desc, line))
    return all_findings


def main():
    parser = argparse.ArgumentParser(description="Safety check for wxauto4 codebase")
    parser.add_argument("--verbose", action="store_true", help="Show all scanned files")
    args = parser.parse_args()

    print("=" * 60)
    print("wxauto4 Safety Check")
    print("=" * 60)

    all_findings = []

    # 1. Scan for dangerous patterns
    print("\n[1] Scanning for dangerous patterns...")
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for scan_dir in SCAN_DIRS:
        dirpath = os.path.join(base, scan_dir)
        if os.path.isdir(dirpath):
            findings = scan_directory(dirpath, args.verbose)
            all_findings.extend(findings)

    if all_findings:
        print(f"  FOUND {len(all_findings)} potential issue(s):")
        for loc, desc, line in all_findings:
            print(f"    {loc}: {desc}")
            if args.verbose:
                print(f"      -> {line[:80]}")
    else:
        print("  OK - No dangerous patterns found")

    # 2. Check protected files
    print("\n[2] Checking protected files...")
    protected = check_protected_files()
    if protected:
        print(f"  WARNING: {len(protected)} protected file(s) modified:")
        for loc, desc, _ in protected:
            print(f"    {desc}")
    else:
        print("  OK - Protected files unchanged")

    # 3. Check default dry_run
    print("\n[3] Checking dry_run defaults in API routes...")
    api_route = os.path.join(base, "wxauto4", "api", "routes", "wechat.py")
    if os.path.exists(api_route):
        with open(api_route, "r", encoding="utf-8") as f:
            content = f.read()
        if "dry_run" in content:
            print("  OK - dry_run support present in API routes")
        else:
            print("  WARNING - No dry_run in API routes")

    # Summary
    total = len(all_findings) + len(protected)
    print("\n" + "=" * 60)
    if total == 0:
        print("PASSED - No safety issues found")
        return 0
    else:
        print(f"WARNING - {total} issue(s) found, review above")
        return 1


if __name__ == "__main__":
    sys.exit(main())
