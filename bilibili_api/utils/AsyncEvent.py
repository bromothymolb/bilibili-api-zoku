"""
bilibili_api.utils.AsyncEvent

发布-订阅模式异步事件类支持。
"""

from asyncio import CancelledError
from collections.abc import AsyncGenerator, Callable, Coroutine
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from enum import Enum
from inspect import iscoroutine
from typing import Any, Literal, TypeVar, overload

from anyio import Event, TaskHandle, create_memory_object_stream, create_task_group
from anyio.abc import TaskGroup

T = TypeVar("T")


class AsyncEventDispatchMode(Enum):
    """
    异步事件分发模式

    - TASK: 创建任务，后台运行 (默认)
    - AWAIT: 等待任务完成
    """

    TASK = "task"
    AWAIT = "await"


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
        self.__dispatch_mode: AsyncEventDispatchMode = AsyncEventDispatchMode.TASK

    def get_dispatch_mode(self) -> AsyncEventDispatchMode:
        """
        获取当前 AsyncEvent 的事件分发模式 (后台任务/等待完成)

        Returns:
            AsyncEventDispatchMode: 事件分发模式
        """
        return self.__dispatch_mode

    def set_dispatch_mode(self, mode: AsyncEventDispatchMode) -> None:
        """
        获取当前 AsyncEvent 的事件分发模式 (后台任务/等待完成)

        Returns:
            AsyncEventDispatchMode: 事件分发模式
        """
        self.__dispatch_mode = mode

    @overload
    def add_event_listener(
        self, name: Literal["__ALL__"], handler: Callable[[str, dict], Any]
    ) -> None: ...

    @overload
    def add_event_listener(
        self,
        name: Literal["__TASK_EXCEPTION__"],
        handler: Callable[[str, Exception], Any],
    ) -> None: ...

    @overload
    def add_event_listener(self, name: str, handler: Callable[[dict], Any]) -> None: ...

    def add_event_listener(self, name: str, handler: Callable) -> None:
        """
        注册事件监听器。

        ``` python
        async def handle_normal(data: dict) -> None:
            # data: 事件数据
            pass

        AsyncEvent.add_event_listener("NORMAL_EVENT", handle_normal)

        async def handle_all(name: str, data: dict) -> None:
            # name: 事件名
            # data: 事件数据
            pass

        AsyncEvent.add_event_listener("__ALL__", handle_normal)

        async def handle_exception(name: str, exc: str) -> None:
            # 处理任务异常
            # name: 抛出异常的任务所属事件
            # exc: 异常
            pass

        AsyncEvent.add_event_listener("__TASK_EXCEPTION__", handle_exception)
        ```

        Args:
            name (str): 事件名。
            handler (Callable): 回调函数。
        """
        name = name.upper()
        if name not in self.__handlers:
            self.__handlers[name] = []
        self.__handlers[name].append(handler)

    @overload
    def on(  # type: ignore
        self, event_name: Literal["__ALL__"]
    ) -> Callable[[Callable[[str, dict], Any]], Any]: ...

    @overload
    def on(
        self, event_name: Literal["__TASK_EXCEPTION__"]
    ) -> Callable[[Callable[[str, Exception], Any]], Any]: ...

    @overload
    def on(self, event_name: str) -> Callable[[Callable[[dict], Any]], Any]: ...

    def on(self, event_name: str) -> Callable:
        """
        装饰器注册事件监听器。

        ``` python
        @AsyncEvent.on("NORMAL_EVENT")
        async def handle_normal(data: dict) -> None:
            # data: 事件数据
            pass

        @AsyncEvent.on("__ALL__")
        async def handle_all(name: str, data: dict) -> None:
            # name: 事件名
            # data: 事件数据
            pass

        @AsyncEvent.on("__TASK_EXCEPTION__")
        async def handle_exception(name: str, exc: Exception) -> None:
            # 处理任务异常
            # name: 抛出异常的任务所属事件
            # exc: 异常
            pass
        ```

        Args:
            event_name (str): 事件名。

        Returns:
            Callable: 装饰器。
        """

        def decorator(func: Callable):
            self.add_event_listener(event_name, func)
            return func

        return decorator

    def remove_all_event_listener(self) -> None:
        """
        移除所有事件监听函数
        """
        self.__handlers = {}

    def remove_event_listener(self, name: str, handler: Callable) -> bool:
        """
        移除事件监听函数。

        Args:
            name (str): 事件名。
            handler (Callable): 要移除的函数。

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

    async def __run_func(self, func: Callable, name: str, *args) -> None:
        try:
            result = func(*args)
            if iscoroutine(result):
                await result
        except Exception as e:
            if name != "__TASK_EXCEPTION__":
                await self.dispatch("__TASK_EXCEPTION__", name, e)
            else:
                raise e

    async def dispatch(self, name: str, *args) -> None:
        """
        异步发布事件。

        Args:
            name (str): 事件名。
            args (Any): 要传递给函数的参数。 *args 传递。
        """
        if name.upper() in self.__ignore_events:
            return
        if len(args) == 0:
            args = [{}]

        name = name.upper()
        if name in self.__handlers:
            match self.get_dispatch_mode():
                case AsyncEventDispatchMode.TASK:
                    for func in self.__handlers[name]:
                        self.task_group.create_task(self.__run_func(func, name, *args))
                case AsyncEventDispatchMode.AWAIT:
                    async with create_task_group() as task:
                        for func in self.__handlers[name]:
                            task.create_task(self.__run_func(func, name, *args))

        if name != "__ALL__" and name != "__TASK_EXCEPTION__":
            await self.dispatch("__ALL__", name, *args)

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

    async def async_event_iter(
        self, start_coro: Coroutine[Any, Any, T]
    ) -> AsyncGenerator[tuple[str, Any]]:
        self.set_dispatch_mode(AsyncEventDispatchMode.AWAIT)
        send_stream, receive_stream = create_memory_object_stream[tuple[str, Any]]()

        @self.on("__ALL__")
        async def yield_event(event: str, data: Any):
            await send_stream.send((event, data))

        async with self.async_event_run(start_coro):
            try:
                async for event, data in receive_stream:
                    yield (event, data)
            except CancelledError:
                self.__exit_event.set()
            finally:
                send_stream.close()
                receive_stream.close()

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

async def close(self) -> ...:
    '''
    结束爬虫
    '''
    self.async_event_cancel()
    # 仍需完成其他清理工作
```
"""
