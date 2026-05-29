"""Module 14 test: OpenClaw skill import and schema check.

Usage:
    python tests/test_openclaw_skill_module14.py
"""
import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "openclaw_skill"))


def test_import():
    """Test skill module imports."""
    try:
        from openclaw_skill.skill import (
            configure, initialize, status, get_my_info, get_sessions,
            switch_chat, send_message, send_files, get_messages,
            get_new_messages, add_listen, remove_listen, start_listening,
            stop_listening, doctor, dispatch, INTENT_MAP,
        )
        print("[OK] Skill module imports successfully")
        return True
    except ImportError as e:
        print(f"[FAIL] Cannot import skill module: {e}")
        return False


def test_manifest():
    """Test manifest.json is valid."""
    manifest_path = os.path.join(os.path.dirname(__file__), "..", "openclaw_skill", "manifest.json")
    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert "name" in data
        assert "version" in data
        assert "capabilities" in data
        assert "examples" in data
        print(f"[OK] manifest.json valid, {len(data['capabilities'])} capabilities")
        return True
    except Exception as e:
        print(f"[FAIL] manifest.json: {e}")
        return False


def test_intent_map():
    """Test that intent map covers expected intents."""
    from openclaw_skill.skill import INTENT_MAP
    expected = ["发微信", "查看消息", "新消息", "会话列表", "发送文件", "监听", "doctor"]
    missing = [i for i in expected if i not in INTENT_MAP]
    if missing:
        print(f"[FAIL] Missing intents: {missing}")
        return False
    print(f"[OK] {len(INTENT_MAP)} intents registered")
    return True


def test_functions_exist():
    """Test that all skill functions exist."""
    from openclaw_skill import skill
    expected = [
        "initialize", "status", "get_my_info", "get_sessions",
        "switch_chat", "send_message", "send_files", "get_messages",
        "get_new_messages", "add_listen", "remove_listen",
        "start_listening", "stop_listening", "doctor", "dispatch",
    ]
    missing = [f for f in expected if not hasattr(skill, f)]
    if missing:
        print(f"[FAIL] Missing functions: {missing}")
        return False
    print(f"[OK] All {len(expected)} skill functions exist")
    return True


def main():
    results = [
        test_import(),
        test_manifest(),
        test_intent_map(),
        test_functions_exist(),
    ]
    passed = sum(results)
    total = len(results)
    print(f"\nResults: {passed}/{total} passed")
    if passed < total:
        sys.exit(1)


if __name__ == "__main__":
    main()
