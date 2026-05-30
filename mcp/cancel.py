# -*- coding: utf-8 -*-
"""Cancellation support for MCP tool calls.

Each in-flight request gets a CancelToken. When the client sends
`notifications/cancelled`, the tracker sets the token so the handler
can abort gracefully at the next safe checkpoint.
"""
from __future__ import annotations

import threading
from typing import Dict, Optional


class CancelToken:
    """Thread-safe flag that signals a tool handler to stop."""

    def __init__(self, request_id: str):
        self.request_id = request_id
        self._cancelled = False
        self._lock = threading.Lock()

    def is_cancelled(self) -> bool:
        with self._lock:
            return self._cancelled

    def cancel(self):
        with self._lock:
            self._cancelled = True

    def __repr__(self):
        state = "cancelled" if self._cancelled else "active"
        return f"CancelToken({self.request_id!r}, {state})"


class RequestTracker:
    """Tracks in-flight requests and their cancel tokens."""

    def __init__(self):
        self._tokens: Dict[str, CancelToken] = {}
        self._lock = threading.Lock()

    def create(self, request_id: str) -> CancelToken:
        token = CancelToken(request_id)
        with self._lock:
            self._tokens[request_id] = token
        return token

    def cancel(self, request_id: str) -> bool:
        with self._lock:
            token = self._tokens.get(request_id)
        if token:
            token.cancel()
            return True
        return False

    def cleanup(self, request_id: str):
        with self._lock:
            self._tokens.pop(request_id, None)

    def cancel_all(self):
        with self._lock:
            for token in self._tokens.values():
                token.cancel()

    @property
    def active_count(self) -> int:
        with self._lock:
            return len(self._tokens)
