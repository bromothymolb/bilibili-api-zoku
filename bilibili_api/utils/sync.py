"""
bilibili_api.utils.sync

同步执行异步函数
"""

from asyncio.futures import Future
from collections.abc import Coroutine
from typing import Any, TypeVar

import anyio

from .network import bili_settings, ensure_event_loop

T = TypeVar("T")


def sync(coroutine: Coroutine[Any, Any, T] | Future) -> T:
    """
    同步执行异步函数，使用可参考 [同步执行异步代码](https://bromothymolb.github.io/bilibili-api-zoku/#/sync-executor)

    Args:
        coroutine (Coroutine | Future): 异步函数

    Returns:
        ~T: 该异步函数的返回值
    """
    if bili_settings.get_enable_trio():

        async def sync_task() -> T:
            return await coroutine

        return anyio.run(sync_task, backend="trio")
    loop = ensure_event_loop()
    return loop.run_until_complete(coroutine)
