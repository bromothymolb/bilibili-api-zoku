"""
bilibili_api.utils.sync

同步执行异步函数
"""

import asyncio
from asyncio.futures import Future
from collections.abc import Coroutine
from typing import Any, TypeVar

import anyio

T = TypeVar("T")


def ensure_event_loop() -> asyncio.AbstractEventLoop:
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())
    return asyncio.get_event_loop()


def sync(coroutine: Coroutine[Any, Any, T] | Future[T], backend: str = "asyncio") -> T:
    """
    同步执行异步函数，使用可参考 [同步执行异步代码](https://bromothymolb.github.io/bilibili-api-zoku/#/docs/common/sync-executor)

    Args:
        coroutine (Coroutine[Any, Any, ~T] | Future[~T]): 异步函数
        backend (str, optional): 异步框架，可选 asyncio / trio。Defaults to "asyncio".

    Returns:
        ~T: 该异步函数的返回值
    """

    async def sync_task() -> T:
        return await coroutine

    return anyio.run(sync_task, backend=backend)
