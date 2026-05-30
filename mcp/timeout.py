# -*- coding: utf-8 -*-
"""Timeout configuration and execution wrapper for MCP tool calls."""
from __future__ import annotations

import concurrent.futures
import logging
from typing import Callable, Any

from mcp.cancel import CancelToken

log = logging.getLogger("mcp.timeout")

# Default timeout in seconds
DEFAULT_TIMEOUT: int = 30

# Per-tool timeout overrides (tool_name -> seconds)
TOOL_TIMEOUTS: dict[str, int] = {
    # Read operations — 30s default is fine
    "wechat_init": 15,
    "wechat_status": 5,
    "get_my_info": 10,
    "get_sessions": 10,
    "get_messages": 15,
    "get_new_messages": 10,
    "get_friend_list": 60,
    "get_friend_details": 60,
    "get_recent_groups": 10,
    "is_online": 5,
    "doctor": 30,
    # Write operations — longer timeouts
    "send_message": 30,
    "send_files": 60,
    "switch_chat": 15,
    # Listener operations
    "add_listen_chat": 10,
    "remove_listen_chat": 10,
    "start_listening": 10,
    "stop_listening": 10,
    # History — may need to scroll a lot
    "get_history_message": 120,
}


def get_timeout(tool_name: str, default: int = DEFAULT_TIMEOUT) -> int:
    return TOOL_TIMEOUTS.get(tool_name, default)


def run_with_timeout(
    fn: Callable[..., Any],
    args: tuple = (),
    kwargs: dict = None,
    timeout: int = DEFAULT_TIMEOUT,
    cancel_token: CancelToken = None,
) -> Any:
    """Run a sync function in a thread with timeout and cancellation.

    Args:
        fn: The function to call.
        args: Positional arguments.
        kwargs: Keyword arguments.
        timeout: Max seconds to wait.
        cancel_token: If set, checked before execution.

    Returns:
        The function's return value.

    Raises:
        TimeoutError: If the function exceeds the timeout.
        CancelledError: If the cancel token is set before or during execution.
    """
    if kwargs is None:
        kwargs = {}

    if cancel_token and cancel_token.is_cancelled():
        raise _Cancelled(f"Request {cancel_token.request_id} was cancelled before execution")

    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    try:
        future = executor.submit(fn, *args, **kwargs)

        # Poll for cancellation while waiting
        try:
            return future.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            future.cancel()
            raise TimeoutError(f"Tool call timed out after {timeout}s")

    finally:
        executor.shutdown(wait=False)


class _Cancelled(Exception):
    """Raised when a request is cancelled."""
    pass


CancelledError = _Cancelled
