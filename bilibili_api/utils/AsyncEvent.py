"""
bilibili_api.utils.AsyncEvent

发布-订阅模式异步事件类支持。
"""

from asyncio import CancelledError
from collections.abc import AsyncGenerator, Callable, Coroutine
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from inspect import iscoroutinefunction
from typing import Any, TypeVar

from anyio import (
    Event,
    TaskHandle,
    create_task_group,
    to_thread,
)
from anyio.abc import TaskGroup

T = TypeVar("T")


class AsyncEvent:
    """
    发布-订阅模式异步事件类支持。

    特殊事件：\\_\\_ALL\\_\\_ 所有事件均触发；\\_\\_TASK_EXCEPTION\\_\\_ 当订阅任务执行过程中抛出异常时发布的事件，不包含在 \\_\\_ALL\\_\\_ 中，订阅此事件的处理函数不再进行异常处理。

    Attributes:
        task_group (anyio.abc.TaskGroup): 可用于创建 Task 的 TaskGroup 实例。
    """

    def __init__(self):
        """ """
        # don't remove this empty docstring
        self.__handlers = {}
        self.__ignore_events = []
        self.task_group: TaskGroup
        self.__exit_event: Event
        self.__task: TaskHandle

    def add_event_listener(self, name: str, handler: Callable | Coroutine) -> None:
        """
        注册事件监听器。

        Args:
            name (str): 事件名。
            handler (Callable | Coroutine): 回调函数。
        """
        name = name.upper()
        if name not in self.__handlers:
            self.__handlers[name] = []
        self.__handlers[name].append(handler)

    def on(self, event_name: str) -> Callable:
        """
        装饰器注册事件监听器。

        Args:
            event_name (str): 事件名。

        Returns:
            Callable: 装饰器。
        """

        def decorator(func: Callable | Coroutine):
            self.add_event_listener(event_name, func)
            return func

        return decorator

    def remove_all_event_listener(self) -> None:
        """
        移除所有事件监听函数
        """
        self.__handlers = {}

    def remove_event_listener(self, name: str, handler: Callable | Coroutine) -> bool:
        """
        移除事件监听函数。

        Args:
            name (str): 事件名。
            handler (Callable | Coroutine): 要移除的函数。

        Returns:
            bool: 是否移除成功。
        """
        name = name.upper()
        if name in self.__handlers:
            if handler in self.__handlers[name]:
                self.__handlers[name].remove(handler)
                return True
        return False

    def ignore_event(self, name: str) -> None:
        """
        忽略指定事件

        Args:
            name (str): 事件名。
        """
        name = name.upper()
        self.__ignore_events.append(name)

    def remove_ignore_events(self) -> None:
        """
        移除所有忽略事件
        """
        self.__ignore_events = []

    def __run_sync_block(
        self, func: Callable, event_name: str, *args, **kwargs
    ) -> None:
        try:
            func(*args, **kwargs)
        except Exception as e:
            if event_name != "__TASK_EXCEPTION__":
                self.dispatch("__TASK_EXCEPTION__", e)
            else:
                raise e

    async def __run_sync(
        self, func: Callable, event_name: str, *args, **kwargs
    ) -> None:
        try:
            await to_thread.run_sync(
                lambda func: func(*args, **kwargs), func, abandon_on_cancel=True
            )
        except Exception as e:
            if event_name != "__TASK_EXCEPTION__":
                self.dispatch("__TASK_EXCEPTION__", e)
            else:
                raise e

    async def __run_coro(self, coro: Coroutine, event_name: str) -> None:
        """
        执行异步函数，如果任务抛出异常，分发特殊异常事件，避免 `Task exception was never retrieved`。
        """
        try:
            await coro
        except Exception as e:
            if event_name != "__TASK_EXCEPTION__":
                self.dispatch("__TASK_EXCEPTION__", e)
            else:
                raise e

    def dispatch(self, name: str, *args, **kwargs) -> None:
        """
        异步发布事件。

        Args:
            name (str): 事件名。
            args (Any): 要传递给函数的参数。 *args 传递。
            kwargs (Any): 要传递给函数的参数。 **kwargs 传递。
        """
        if len(args) == 0 and len(kwargs.keys()) == 0:
            args = [{}]
        if name.upper() in self.__ignore_events:
            return

        name = name.upper()
        if name in self.__handlers:
            for func in self.__handlers[name]:
                if iscoroutinefunction(func):
                    if not hasattr(self, "task_group"):
                        continue
                    else:
                        self.task_group.create_task(
                            self.__run_coro(func(*args, **kwargs), name)
                        )
                else:
                    if not hasattr(self, "task_group"):
                        self.__run_sync_block(func, name, *args, **kwargs)
                    else:
                        self.task_group.create_task(
                            self.__run_sync(func, name, *args, **kwargs)
                        )

        if name != "__ALL__" and name != "__TASK_EXCEPTION__":
            kwargs.update({"name": name, "data": args})
            self.dispatch("__ALL__", kwargs)

    async def async_event_start(self, coro: Coroutine[Any, Any, T]) -> T | None:
        """
        阻塞启动异步事件类

        Args:
            coro (Coroutine[Any, Any, ~T]): 主程序

        Returns:
            ~T | None: 主程序返回值，若中途取消则返回 None
        """
        self.task_group = create_task_group()
        self.__exit_event = Event()
        ret = None
        try:
            async with self.task_group as task_group:

                async def cancel_handle() -> None:
                    await self.__exit_event.wait()
                    task_group.cancel()

                task_group.start_soon(cancel_handle)
                self.__task = task_group.create_task(coro)
                ret = await self.__task
                self.__exit_event.set()
        except CancelledError:
            self.__exit_event.set()
        del self.task_group
        return ret

    def async_event_run(
        self, start_coro: Coroutine[Any, Any, T]
    ) -> AbstractAsyncContextManager[TaskHandle[T | None]]:
        """
        非阻塞启动异步事件类

        此函数将返回异步上下文管理器。

        Args:
            start_coro (Coroutine[Any, Any, ~T]): 主程序的阻塞启动协程

        Returns:
            AbstractAsyncContextManager[anyio.TaskHandle[~T | None]]: 运行主程序的 TaskHandle，若中途取消则返回 None
        """

        @asynccontextmanager
        async def __run_bg_task() -> AsyncGenerator[TaskHandle[T | None]]:
            async with create_task_group() as btg:
                background_task = btg.create_task(start_coro)
                yield background_task

        return __run_bg_task()

    def async_event_cancel(self) -> None:
        """
        取消异步事件类主任务
        """
        self.__exit_event.set()

    def async_event_running(self) -> bool:
        """
        判断异步事件类主任务是否正在运行

        Returns:
            bool: 异步事件类主任务是否正在运行
        """
        return hasattr(self, "task_group")


"""
使用 anyio.TaskGroup 后编写 AsyncEvent 类相关调用代码，可参考如下写法:

``` python
async def __main(self, ...) -> ...:
    '''
    异步主程序
    '''
    # 此处可直接正常调用 self.task_group
    ...

async def start(self, ...) -> ...:
    '''
    阻塞式异步爬虫
    '''
    # 异常处理：除 asyncio.CancelledError 其他异常均会 raise
    # 如有必要请添加异常处理逻辑
    try:
        return await self.async_event_start(self.__main())
    except Exception as e:
        # 异常处理
        raise e

def run(self, ...) -> ...:
    '''
    非阻塞式异步爬虫
    '''
    return self.async_event_run(self.start(...))

async def close(self) -> ...:
    '''
    结束爬虫
    '''
    self.async_event_cancel()
    # 仍需完成其他清理工作
```
"""
