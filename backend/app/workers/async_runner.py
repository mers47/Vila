"""Persistent asyncio loop for Celery worker processes.

Celery tasks are synchronous callables. Repeated asyncio.run() creates and destroys an
EventLoop for every task, defeating asyncpg/httpx connection pooling. This runner keeps
one loop alive per worker process and submits coroutines onto it.
"""
from __future__ import annotations

import asyncio
import threading
from concurrent.futures import Future
from typing import Coroutine, TypeVar

T = TypeVar("T")

_lock = threading.Lock()
_loop: asyncio.AbstractEventLoop | None = None
_thread: threading.Thread | None = None


def _loop_main(loop: asyncio.AbstractEventLoop) -> None:
    asyncio.set_event_loop(loop)
    try:
        loop.run_forever()
    finally:
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()


def _ensure_loop() -> asyncio.AbstractEventLoop:
    global _loop, _thread
    with _lock:
        if _loop is None or _loop.is_closed() or _thread is None or not _thread.is_alive():
            loop = asyncio.new_event_loop()
            thread = threading.Thread(target=_loop_main, args=(loop,), name="celery-asyncio", daemon=True)
            thread.start()
            _loop, _thread = loop, thread
        return _loop


def run_async(coro: Coroutine[object, object, T], *, timeout: float | None = None) -> T:
    loop = _ensure_loop()
    future: Future[T] = asyncio.run_coroutine_threadsafe(coro, loop)
    try:
        return future.result(timeout=timeout)
    except Exception:
        if not future.cancelled():
            future.cancel()
        raise