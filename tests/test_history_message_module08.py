"""Module 08 test: GetHistoryMessage — scroll up and read older messages.

Usage:
    python tests/test_history_message_module08.py              # dry_run: print visible messages only
    python tests/test_history_message_module08.py --n 20       # fetch 20 historical messages
    python tests/test_history_message_module08.py --n 10 --send  # fetch 10 and send a test message
"""
import sys
import os
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def main():
    parser = argparse.ArgumentParser(description="Test GetHistoryMessage (Module 08)")
    parser.add_argument("--n", type=int, default=10, help="Number of historical messages to fetch")
    parser.add_argument("--target", type=str, default=None, help="Switch to a specific chat first")
    parser.add_argument("--send", action="store_true", help="Actually fetch history (not just dry_run)")
    args = parser.parse_args()

    if not args.send:
        print("[DRY RUN] This test will only print visible messages.")
        print("          Pass --send to actually scroll and fetch history.\n")

    from wxauto4 import WeChat

    wx = WeChat()
    print(f"WeChat initialized: {wx.nickname}")

    if args.target:
        result = wx.ChatWith(args.target)
        print(f"Switched to: {args.target} -> {result}")
        import time
        time.sleep(0.5)

    # Show current visible messages
    msgs = wx.GetAllMessage()
    print(f"\nCurrent visible messages ({len(msgs)}):")
    for m in msgs[-10:]:
        print(f"  [{m.attr}] {m.content[:60] if m.content else '(empty)'}")

    if not args.send:
        print("\n[DRY RUN] Done. Pass --send to fetch history.")
        return

    # Actually fetch history
    print(f"\nFetching {args.n} historical messages...")
    history = wx.GetHistoryMessage(n=args.n, interval=0.3, speed=2)
    print(f"Got {len(history)} historical messages:")
    for i, m in enumerate(history):
        content = m.content[:60] if m.content else "(empty)"
        print(f"  {i+1}. [{m.attr}] {content}")

    print("\nDone.")


if __name__ == "__main__":
    main()
