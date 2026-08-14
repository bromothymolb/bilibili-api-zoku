"""
bilibili_api.utils.network

与网络请求相关的模块。能对会话进行管理（复用 TCP 连接）。

现在已经变成核心功能大杂烩了 2025.11.25 @Nemo2011

bilibili-api 一切行为的核心即在网络请求上。自然，掌管网络请求的部分是模块的核心，重中之重。

适合改为 bilibili_api.utils.core ，但改起来太麻烦了。

碎碎念到此。network.py 整体由多个部分组成，代码中各个部分用了一条条注释互相分隔。

## 1. AsyncEvent

- `AsyncEvent`

提供发布-订阅模式异步事件类支持。

## 2. Logger

- `request_log` (`RequestLog`)

提供日志支持。整个 network.py 中的功能日志均由此发出。

## 3. Settings

- `bili_settings` (`BiliSettings`)
- `request_settings` (`RequestSettings`)

设置支持。设置分为两类，一类为 `BiliSettings`，一类为 `RequestSettings`。

前者将传入第三方网络请求库应用，自然是网络请求相关的设置。

后者是模块功能设置，此处功能自然是网络请求以外的功能，如 wbi 自动刷新，风控 cookies 自动获取。

## 4. BiliAPIClient

- `BiliAPIClient`
- `BiliAPIResponse`
- `BiliWsMsgType`
- `BiliAPIFile`

此处实现了用于接入第三方请求客户端的抽象类。同时实现了相应帮助类。

## 5. Session Management

### 1. 会话封装 (过滤器相关)

- `BiliFilterFlags`
- `BiliFilterData`
- `BiliFilterArgs`
- `BiliFilterReturn`
- (`_BiliAPIClient`)

### 2. 会话调度 (事件循环相关)

- (`get_loop_lock`)
- (`MultiEventLoopLocks`)
- (`_BiliAPIClientGroup`)

### 3. `client` 管理

- `register_client`
- `unregister_client`
- `select_client`
- `get_selected_client`
- `get_registered_clients`

### 4. `instance` 管理

- `new_instance`
- `remove_instance`
- `select_instance`
- `get_selected_instance`
- `get_instances`
- `get_exist_instances`

### 5. 设置获取

- `get_available_settings`
- `get_registered_available_settings`
- `get_instance_settings`
- `get_force_settings`
- `get_settings`

### 6. 高层级调度管理函数

- `get_client`
- `get_session`
- `set_session`
- `unset_session`
- `clean_session`

此处功能较为复杂，实现了多请求客户端的管理。

为什么需要多个请求客户端?

1. 模块支持不同第三方库，产生不同请求客户端。
2. asyncio 事件循环不唯一时，需要每个事件循环配对一个请求客户端。
3. 用户对多个请求客户端的需求，例如需要设置互不相同的多个请求客户端。

模块将所有请求客户端如下分类：

1. 第一层按第三方请求库，内部使用 `client` 指代此层。
2. 第二层按设置项分类，称每一类请求客户端为一个 `instance`。
3. 第三层，在 `instance` 内部，每一个事件循环匹配一个 `session`。

事实上，`session` `instance` 分别对应 `_BiliAPIClient` `_BiliAPIClientGroup`。

第一二层均通过 `client_groups` 字典进行维护，第三层通过 `_BiliAPIClientGroup` 维护。

`_BiliAPIClientGroup` 负责不同事件循环间的调度。每个事件循环将被编号后维护。

`_BiliAPIClient` 事实上为一个单独 `BiliAPIClient` 的包装，重写了其 getter。

在其 getter 中，模块将完成过滤器功能的执行应用。

对于 `instance` 设置的维护，其采取懒维护策略，仅获取实例时由上到下依次传递、更新并应用。

`_BiliAPIClientGroup` -> `_BiliAPIClient` -> `BiliAPIClient`

`get_instance_settings` `get_force_settings` 获取的均为 `instance` 设置。

`get_settings` 获取全局设置，其将在 `_BiliAPIClientGroup` 中应用。

事实上，如需绕过所有高层级类直接修改设置项，可调用 `session.set_xxx()` 函数直接设置。

模块支持自行设置 `session`，设置需指定对应 `client` `instance` 和事件循环。

## 6. Credential

- `Credential`

此处实现凭据类，用于维护 cookies ，提供网络请求风控 cookies 获取功能以及 cookies 刷新功能。

## 7. Anti-Spider

- `get_browser_fingerprint`
- `get_bili_headers`

反爬虫相关函数，部分需要进行网络请求获取风控参数。

此外，浏览器指纹伪装功能亦在此处应用。

## 8. Builtin-Filters

模块内置的过滤器，提供常用功能。

目前支持过滤器提供功能：

- 请求日志
- 全局凭据类

目前存在以下过滤器：

- `__builtin_log_pre` 前置 `priority=998244353`
- `__builtin_log_post` 后置 `priority=-998244353`

## 9. Credential-AntiSpider

- `ensure_buvid`
- `obtain_buvid`
- `ensure_bili_ticket`
- `obtain_bili_ticket`

此部分负责维护凭据类的 buvid / bili_ticket ，即网络请求风控 cookies。

相关信息请前往此部分开头注释查看。

## 10. Api

- `recalculate_wbi`
- `get_wbi_mixin_key`
- `Api`
- `bili_simple_download`
- `configure_dynamic_fingerprint`

此部分提供真正意义上的高层级 API ，模块 90% 的网络请求直接使用此部分功能发起。

主要为 `Api` 类，提供便捷的参数应用风控选项，如 wbi 风控。

终于写完了，这边代码没有任何说明真的很难看懂啊。希望这段注释对将来的阅览者有所帮助。

2026.07.25 added by @bromothymolb
"""

from abc import ABC, abstractmethod
from asyncio import AbstractEventLoop, CancelledError
import atexit
import base64
import binascii
from collections.abc import AsyncGenerator, Callable, Coroutine
from contextlib import asynccontextmanager
from contextvars import ContextVar
from copy import deepcopy
from dataclasses import dataclass, field
from email.utils import parsedate_to_datetime
from enum import Enum
from functools import cmp_to_key, reduce
import hashlib
import hmac
from inspect import (
    isasyncgen,
    isasyncgenfunction,
    iscoroutinefunction,
    isfunction,
    isgenerator,
    signature,
)
import io
import json
from json import scanner
from json.decoder import scanstring  # type: ignore
import mimetypes
import os
import random
import re
import struct
from threading import Lock as ThreadingLock
import time
from typing import Any, TypeVar
import urllib.parse

from anyio import (
    Event,
    Lock,
    RunFinishedError,
    TaskHandle,
    create_task_group,
    from_thread,
    get_available_backends,
    open_file,
    to_thread,
)
from anyio._backends._asyncio import AsyncIOBackend
from anyio.abc import TaskGroup
from anyio.lowlevel import EventLoopToken, current_token
from bs4 import BeautifulSoup
import chompjs
from colorama import Fore
from Cryptodome.Cipher import PKCS1_OAEP
from Cryptodome.Hash import SHA256
from Cryptodome.PublicKey import RSA
from loguru import logger

from ..exceptions import (
    ArgsException,
    CookiesRefreshException,
    CredentialNoAcTimeValueException,
    CredentialNoBiliJctException,
    CredentialNoBuvid3Exception,
    CredentialNoBuvid4Exception,
    CredentialNoDedeUserIDException,
    CredentialNoSessdataException,
    ExClimbWuzhiException,
    FilterException,
    NetworkException,
    ResponseCodeException,
    WbiRetryTimesExceedException,
)
from .utils import get_api, loguru_apply_anti_tag, raise_for_statement

TRIO_AVAILABLE = "trio" in get_available_backends()

if TRIO_AVAILABLE:
    from anyio._backends._trio import TrioBackend
    from trio.lowlevel import TrioToken
else:
    TrioToken = None

################################################## BEGIN AsyncEvent ##################################################


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

    @asynccontextmanager
    async def async_event_run(
        self, start_coro: Coroutine[Any, Any, T]
    ) -> AsyncGenerator[TaskHandle[T | None]]:
        """
        非阻塞启动异步事件类

        此函数将返回异步上下文管理器。

        Args:
            start_coro (Coroutine[Any, Any, ~T]): 主程序的阻塞启动协程

        Returns:
            AsyncGenerator[anyio.TaskHandle[~T | None]]: 运行主程序的 TaskHandle，若中途取消则返回 None
        """
        async with create_task_group() as btg:
            background_task = btg.create_task(start_coro)
            yield background_task

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


################################################## END AsyncEvent ##################################################


################################################## BEGIN Logger ##################################################


class RequestLog(AsyncEvent):
    def __init__(self) -> None:
        super().__init__()
        self.__on = False
        self.__on_events: list[str] = [
            "API_REQUEST",
            "API_RESPONSE",
            "ANTI_SPIDER",
            "WS_CREATE",
            "WS_RECV",
            "WS_SEND",
            "WS_CLOSE",
        ]
        self.__ignore_events: list[str] = []
        self.add_event_listener("__ALL__", self.__handle_events)

    def get_all_events(self) -> list[str]:
        """
        获取日志支持的所有默认事件列表

        Returns:
            list[str]: 日志支持的所有默认事件列表
        """
        return [
            "REQUEST",
            "RESPONSE",
            "WS_CREATE",
            "WS_RECV",
            "WS_SEND",
            "WS_CLOSE",
            "DWN_CREATE",
            "DWN_PART",
            "DWN_CLOSE",
            "CLOSE",
            "API_REQUEST",
            "API_RESPONSE",
            "ANTI_SPIDER",
            "DO_PRE_FILTER",
            "DO_POST_FILTER",
        ]

    def get_on_events(self) -> list[str]:
        """
        获取日志输出支持的事件类型

        Returns:
            list[str]: 日志输出支持的事件类型
        """
        return self.__on_events

    def set_on_events(self, events: list[str]) -> None:
        """
        设置日志输出支持的事件类型

        Args:
            events (list[str]): 日志输出支持的事件类型
        """
        self.__on_events = events

    def get_ignore_events(self) -> list[str]:
        """
        获取日志输出排除的事件类型

        Returns:
            list[str]: 日志输出排除的事件类型
        """
        return self.__ignore_events

    def set_ignore_events(self, events: list[str]) -> None:
        """
        设置日志输出排除的事件类型

        Args:
            events (list[str]): 日志输出排除的事件类型
        """
        self.__ignore_events = events

    def is_on(self) -> bool:
        """
        获取日志输出是否启用

        Returns:
            bool: 是否启用
        """
        return self.__on

    def set_on(self, status: bool) -> None:
        """
        设置日志输出是否启用

        Args:
            status (bool): 是否启用
        """
        self.__on = status

    def __log(self, event: str) -> None:
        event = loguru_apply_anti_tag(event)
        colors = {
            Fore.GREEN: ("<green>", "</green>"),
            Fore.MAGENTA: ("<magenta>", "</magenta>"),
            Fore.YELLOW: ("<yellow>", "</yellow>"),
            Fore.CYAN: ("<cyan>", "</cyan>"),
        }
        for color, color_tags in colors.items():
            end_tag = 0
            while True:
                color_str = str(color)
                idx = event.find(color_str)
                if idx == -1:
                    break
                event = (
                    event[:idx] + color_tags[end_tag] + event[(idx + len(color_str)) :]
                )
                end_tag = 1 - end_tag
        logger.opt(colors=True).debug(f"<red>bilibili-api-request</red> | {event}")

    def __handle_events(self, data: dict) -> None:
        evt = data["name"]
        desc, real_data = data["data"]
        if (
            self.__on
            and evt in self.get_on_events()
            and evt not in self.get_ignore_events()
        ):
            if evt == "ANTI_SPIDER":
                self.__log(f"{Fore.GREEN}【{desc}】{Fore.GREEN} {real_data['msg']}")
                return
            elif not real_data.get("act_id"):
                self.__log(f"{Fore.GREEN}【{desc}】{Fore.GREEN} {real_data}")
                return
            act_id = real_data.pop("act_id")
            client = real_data.pop("client")
            instance = real_data.pop("instance")
            loop = real_data.pop("event_loop")
            backend = {"AsyncIOBackend": "asyncio", "TrioBackend": "trio"}[
                loop.backend_class.__name__
            ]
            info_str = f"#{Fore.CYAN}{act_id}{Fore.CYAN} {Fore.MAGENTA}[{client} / {instance}]{Fore.MAGENTA} {Fore.YELLOW}<{backend} @ {hash(loop)}>{Fore.YELLOW} "
            log_str = ""
            middle_str = " "
            if evt.startswith("WS_"):
                ws_id = real_data.pop("id")
                middle_str += f"WS #{ws_id} "
            elif evt.startswith("DWN_"):
                dwn_id = real_data.pop("id")
                middle_str += f"DWN #{dwn_id} "
            elif evt == "DO_PRE_FILTER":
                action = real_data.pop("action")
                name = real_data.pop("name")
                priority = real_data.pop("priority")
                filter_id = real_data.pop("filter_id")
                log_str = f"{Fore.GREEN}{desc}{Fore.GREEN} [{Fore.CYAN}{filter_id}{Fore.CYAN}] {action}() <- {name} / {Fore.CYAN}{priority}{Fore.CYAN}"
            elif evt == "DO_POST_FILTER":
                action = real_data.pop("action")
                name = real_data.pop("name")
                priority = real_data.pop("priority")
                filter_id = real_data.pop("filter_id")
                log_str = f"{Fore.GREEN}{desc}{Fore.GREEN} [{Fore.CYAN}{filter_id}{Fore.CYAN}] {action}() <- {name} / {Fore.CYAN}{priority}{Fore.CYAN}"
            log_str = log_str or f"{Fore.GREEN}{desc}{Fore.GREEN}: {real_data}"
            self.__log(info_str + middle_str + log_str)


request_log = RequestLog()
"""
请求日志支持，默认支持输出到指定 I/O 对象。

可以添加更多监听器达到更多效果。

Logger: request_log.logger

Extends: AsyncEvent

Events:

- (模块自带 BiliAPIClient)
- REQUEST:     HTTP 请求。
- RESPONSE:    HTTP 响应。
- WS_CREATE:   新建的 Websocket 请求。
- WS_RECV:     获得到 WebSocket 请求。
- WS_SEND:     发送了 WebSocket 请求。
- WS_CLOSE:    关闭 WebSocket 请求。
- DWN_CREATE:  新建下载。
- DWN_PART:    部分下载。
- DWN_CLOSE:   结束下载。
- CLOSE:       关闭会话。
- (Api)
- API_REQUEST: Api 请求。
- API_RESPONSE: Api 响应。
- (反爬虫)
- ANTI_SPIDER: 反爬虫相关信息。
- (过滤器)
- DO_PRE_FILTER: 执行前置过滤器。
- DO_POST_FILTER: 执行后置过滤器

CallbackData: 描述 (str) 数据 (dict)

示例：

``` python
@request_log.on("REQUEST")
async def handle(desc: str, data: dict) -> None:
    print(desc, data)
```

默认启用 Api 和 Anti-Spider 相关信息。
"""
request_log.__doc__ = """
请求日志支持，默认支持输出到指定 I/O 对象。

可以添加更多监听器达到更多效果。

Logger: request_log.logger

Extends: AsyncEvent

Events:

- (模块自带 BiliAPIClient)
- REQUEST:     HTTP 请求。
- RESPONSE:    HTTP 响应。
- WS_CREATE:   新建的 Websocket 请求。
- WS_RECV:     获得到 WebSocket 请求。
- WS_SEND:     发送了 WebSocket 请求。
- WS_CLOSE:    关闭 WebSocket 请求。
- DWN_CREATE:  新建下载。
- DWN_PART:    部分下载。
- DWN_CLOSE:   结束下载。
- CLOSE:       关闭会话。
- (Api)
- API_REQUEST: Api 请求。
- API_RESPONSE: Api 响应。
- (反爬虫)
- ANTI_SPIDER: 反爬虫相关信息。
- (过滤器)
- DO_PRE_FILTER: 执行前置过滤器。
- DO_POST_FILTER: 执行后置过滤器

CallbackData: 描述 (str) 数据 (dict)

示例：

``` python
@request_log.on("REQUEST")
async def handle(desc: str, data: dict) -> None:
    print(desc, data)
```

默认启用 Api 和 Anti-Spider 相关信息。
"""


################################################## END Logger ##################################################


################################################## BEGIN Settings ##################################################


class BiliSettings:
    def __init__(self):
        self.__settings = {
            "wbi_retry_times": 3,
            "enable_auto_buvid": True,
            "enable_bili_ticket": False,
            "enable_buvid_global_persistence": False,
            "enable_bili_ticket_global_persistence": False,
            "enable_fpgen": False,
            "fpgen_args": {},
        }
        self.__defaults = {
            "wbi_retry_times": 3,
            "enable_auto_buvid": True,
            "enable_bili_ticket": False,
            "enable_buvid_global_persistence": False,
            "enable_bili_ticket_global_persistence": False,
            "enable_fpgen": False,
            "fpgen_args": {},
        }

    def get(self, name: str) -> Any:
        """
        获取某项设置，字段未曾设置过时将返回 None.

        Args:
            name (str): 设置名称

        Returns:
            Any: 设置的值
        """
        if not self.has(name):
            raise ArgsException(f"不存在设置: {name}") from None
        return self.__settings[name]

    def set(self, name: str, value: Any) -> None:
        """
        设置某项设置

        Args:
            name (str): 设置名称
            value (Any): 设置的值
        """
        self.__settings[name] = value

    def has(self, name: str) -> bool:
        """
        判断是否存在某项设置

        Args:
            name (str): 设置名称

        Returns:
            bool: 是否存在某项设置
        """
        return name in self.__settings.keys()

    def all(self) -> dict:
        """
        获取目前所有的设置项

        Returns:
            dict: 所有的设置项
        """
        return self.__settings.copy()

    def defaults(self) -> dict:
        """
        获取此设置项的默认设置。仅实例的基本设置存在默认值。

        Returns:
            dict: 默认设置
        """
        return self.__defaults.copy()

    def get_wbi_retry_times(self) -> int:
        """
        获取设置的 wbi 重试次数

        Returns:
            int: wbi 重试次数. Defaults to 3.
        """
        return self.get("wbi_retry_times")

    def set_wbi_retry_times(self, wbi_retry_times: int) -> None:
        """
        修改设置的 wbi 重试次数

        Args:
            wbi_retry_times (int): wbi 重试次数.
        """
        self.set("wbi_retry_times", wbi_retry_times)

    def get_enable_auto_buvid(self) -> bool:
        """
        获取设置的是否自动生成 buvid

        Returns:
            bool: 是否自动生成 buvid. Defaults to True.
        """
        return self.get("enable_auto_buvid")

    def set_enable_auto_buvid(self, enable_auto_buvid: bool) -> None:
        """
        设置是否自动生成 buvid

        Args:
            enable_auto_buvid (bool): 是否自动生成 buvid.
        """
        self.set("enable_auto_buvid", enable_auto_buvid)

    def get_enable_bili_ticket(self) -> bool:
        """
        获取设置的是否使用 bili_ticket

        Returns:
            bool: 是否使用 bili_ticket. Defaults to False.
        """
        return self.get("enable_bili_ticket")

    def set_enable_bili_ticket(self, enable_bili_ticket: bool) -> None:
        """
        设置是否使用 bili_ticket

        Args:
            enable_bili_ticket (bool): 是否使用 bili_ticket.
        """
        self.set("enable_bili_ticket", enable_bili_ticket)

    def get_enable_buvid_global_persistence(self) -> bool:
        """
        获取设置的是否使用全局可持久化 buvid

        Returns:
            bool: 是否使用全局可持久化 buvid. Defaults to False.
        """
        return self.get("enable_buvid_global_persistence")

    def set_enable_buvid_global_persistence(
        self, enable_buvid_global_persistence: bool
    ) -> None:
        """
        设置是否使用全局可持久化 buvid

        Args:
            enable_buvid_global_persistence (bool): 是否使用全局可持久化 buvid.
        """
        self.set("enable_buvid_global_persistence", enable_buvid_global_persistence)

    def get_enable_bili_ticket_global_persistence(self) -> bool:
        """
        获取设置的是否使用全局可持久化 bili_ticket

        Returns:
            bool: 是否使用全局可持久化 bili_ticket. Defaults to False.
        """
        return self.get("enable_bili_ticket_global_persistence")

    def set_enable_bili_ticket_global_persistence(
        self, enable_bili_ticket_global_persistence: bool
    ) -> None:
        """
        设置是否使用全局可持久化 buvid

        Args:
            enable_bili_ticket_global_persistence (bool): 是否使用全局可持久化 buvid.
        """
        self.set(
            "enable_bili_ticket_global_persistence",
            enable_bili_ticket_global_persistence,
        )

    def get_enable_fpgen(self) -> bool:
        """
        获取是否使用 fpgen

        Returns:
            bool: 是否使用 fpgen. Defaults to False.
        """
        return self.get("enable_fpgen")

    def set_enable_fpgen(self, enable_fpgen: bool) -> None:
        """
        设置是否使用 fpgen

        Args:
            enable_fpgen (bool): 是否使用 fpgen
        """
        self.set("enable_fpgen", enable_fpgen)

    def get_fpgen_args(self) -> dict:
        """
        获取调用 fpgen 的参数

        Returns:
            dict: 调用 fpgen 的参数
        """
        return self.get("fpgen_args")

    def set_fpgen_args(self, fpgen_args: dict) -> None:
        """
        设置调用 fpgen 的参数

        Args:
            fpgen_args (dict): 调用 fpgen 的参数
        """
        self.set("fpgen_args", fpgen_args)

    def gets(self, keys: list[str]) -> dict:
        """
        获取对应设置项的设置

        Args:
            keys (list[str]): 设置项

        Returns:
            dict: 对应设置项的设置
        """
        return {key: self.get(key) for key in keys}

    def sets(self, settings: dict) -> None:
        """
        设置传入的项目

        Args:
            settings (dict): 设置项，键为设置名称，值为设置值。
        """
        self.__settings |= settings

    def register(self, name: str, default: Any) -> None:
        """
        注册设置项

        Args:
            name (str): 设置项名称
            default (Any): 设置项默认值
        """
        if name in self.all().keys():
            raise ArgsException(f"设置项 {name} 已注册。")
        self.__settings[name] = default
        self.__defaults[name] = default


class RequestSettings:
    """
    与请求客户端相关设置

    模块默认有 `proxy` `timeout` `verify_ssl` `trust_env` 四个设置。

    | name | type | default | curl_cffi | aiohttp | httpx |
    | ---- | ---- | ------- | --------- | ------- | ----- |
    | proxy | str | ` ` |  ✅ | ✅ | ✅ |
    | timeout | float | `30.0` | ✅ | ✅ | ✅ |
    | verify_ssl | bool | `True` | ✅ | ✅ | ✅ |
    | trust_env | bool | `True` | ✅ | ✅ | ✅ |
    | http2 | bool | `False` | ✅ | ❌ | ✅ |
    | impersonate | str | ` ` | ✅ | ❌ | ❌ |
    """

    def __init__(self) -> None:
        """ """
        # don't remove this empty docstring
        self.__settings: dict = {}
        self.__lazy: dict = {}  # change diff
        self.__latest_state: dict = {}  # change base
        self.__is_base = False  # base_settings cannot unset
        self.__defaults: dict = {}

    def _set_base(self, defaults: dict) -> None:
        self.__is_base = True
        self.__defaults = defaults.copy()
        self.sets(self.__defaults)

    def _get_lazy(self) -> dict:
        return self.__lazy.copy()

    def _pop_lazy(self) -> dict:
        ret = self.__lazy.copy()
        self.__lazy = {}
        for key, val in self.__latest_state.items():
            if ret.get(key) == val:
                del ret[key]
        self.__latest_state = self.__settings.copy()
        return ret

    def get(self, name: str) -> Any:
        """
        获取某项设置，字段未曾设置过时将返回 None.

        Args:
            name (str): 设置名称

        Returns:
            Any: 设置的值
        """
        if not self.has(name):
            raise ArgsException(f"不存在设置: {name}") from None
        return self.__settings[name]

    def set(self, name: str, value: Any) -> None:
        """
        设置某项设置

        Args:
            name (str): 设置名称
            value (Any): 设置的值
        """
        self.__settings[name] = value
        self.__lazy[name] = value

    def has(self, name: str) -> bool:
        """
        判断是否存在某项设置

        Args:
            name (str): 设置名称

        Returns:
            bool: 是否存在某项设置
        """
        return name in self.__settings.keys()

    def unset(self, name: str) -> None:
        """
        取消设置项

        Args:
            name (str): 设置项
        """
        if self.__is_base:
            raise ArgsException(
                "不可以取消实例的基本设置，仅可以取消全局设置或实例的强制设置。"
            )
        if not self.has(name):
            raise ArgsException(f"不存在设置: {name}") from None
        del self.__settings[name]
        del self.__lazy[name]

    def all(self) -> dict:
        """
        获取目前所有的设置项

        Returns:
            dict: 所有的设置项
        """
        return self.__settings.copy()

    def defaults(self) -> dict:
        """
        获取此设置项的默认设置。仅实例的基本设置存在默认值。

        Returns:
            dict: 默认设置
        """
        return self.__defaults

    def get_proxy(self) -> str:
        """
        获取设置的代理

        Returns:
            str: 代理地址. Defaults to "".
        """
        return self.get("proxy")

    def set_proxy(self, proxy: str) -> None:
        """
        修改设置的代理

        Args:
            proxy (str): 代理地址
        """
        self.set("proxy", proxy)

    def get_timeout(self) -> float:
        """
        获取设置的 web 请求超时时间

        Returns:
            float: 超时时间. Defaults to 5.0.
        """
        return self.get("timeout")

    def set_timeout(self, timeout: float) -> None:
        """
        修改设置的 web 请求超时时间

        Args:
            timeout (float): 超时时间
        """
        self.set("timeout", timeout)

    def get_verify_ssl(self) -> bool:
        """
        获取设置的是否验证 SSL

        Returns:
            bool: 是否验证 SSL. Defaults to True.
        """
        return self.get("verify_ssl")

    def set_verify_ssl(self, verify_ssl: bool) -> None:
        """
        修改设置的是否验证 SSL

        Args:
            verify_ssl (bool): 是否验证 SSL
        """
        self.set("verify_ssl", verify_ssl)

    def get_trust_env(self) -> bool:
        """
        获取设置的 `trust_env`

        Returns:
            bool: `trust_env`. Defaults to True.
        """
        return self.get("trust_env")

    def set_trust_env(self, trust_env: bool) -> None:
        """
        修改设置的 `trust_env`

        Args:
            trust_env (bool): `trust_env`
        """
        self.set("trust_env", trust_env)

    def get_http2(self) -> bool:
        """
        获取设置的 `http2`

        Returns:
            bool: `http2`. Defaults to False.
        """
        return self.get("http2")

    def set_http2(self, http2: bool) -> None:
        """
        修改设置的 `http2`

        Args:
            http2 (bool): `http2`
        """
        self.set("http2", http2)

    def get_impersonate(self) -> str:
        """
        获取设置的 `impersonate`

        Returns:
            str: `impersonate`. Defaults to "".
        """
        return self.get("impersonate")

    def set_impersonate(self, impersonate: str) -> None:
        """
        修改设置的 `impersonate`

        Args:
            impersonate (str): `impersonate`
        """
        self.set("impersonate", impersonate)

    def gets(self, keys: list[str]) -> dict:
        """
        获取对应设置项的设置

        Args:
            keys (list[str]): 设置项

        Returns:
            dict: 对应设置项的设置
        """
        return {key: self.get(key) for key in keys}

    def sets(self, settings: dict) -> None:
        """
        设置传入的项目

        Args:
            settings (dict): 设置项，键为设置名称，值为设置值。
        """
        self.__settings |= settings
        self.__lazy |= settings

    def unsets(self, keys: list[str]) -> None:
        """
        取消设置项

        Args:
            name (str): 设置项
        """
        for key in keys:
            self.unset(key)


bili_settings = BiliSettings()
"""
模块通用设置

| configuration | type | default | description |
| ------------- | ---- | ------- | ----------- |
| `wbi_retry_times` | `int` | `3` | WBI 重试次数 |
| `enable_auto_buvid` | `bool` | `True` | 允许模块自动请求生成 buvid |
| `enable_bili_ticket` | `bool` | `False` | 允许模块自动请求生成 bili_ticket |
| `enable_buvid_global_persistence` | `bool` | `False` | 允许模块使用统一的全局 buvid |
| `enable_bili_ticket_global_persistence` | `bool` | `False` | 允许模块使用统一的全局 bili_ticket |
| `enable_fpgen` | `bool` | `False` | 是否启用 `fpgen` 进行指纹伪装 |
| `fpgen_args` | `dict` | `{}` | 传入 `fpgen.generate` 的 keyword args 参数 |
"""
bili_settings.__doc__ = """
模块通用设置

| configuration | type | default | description |
| ------------- | ---- | ------- | ----------- |
| `wbi_retry_times` | `int` | `3` | WBI 重试次数 |
| `enable_auto_buvid` | `bool` | `True` | 允许模块自动请求生成 buvid |
| `enable_bili_ticket` | `bool` | `False` | 允许模块自动请求生成 bili_ticket |
| `enable_buvid_global_persistence` | `bool` | `False` | 允许模块使用统一的全局 buvid |
| `enable_bili_ticket_global_persistence` | `bool` | `False` | 允许模块使用统一的全局 bili_ticket |
| `enable_fpgen` | `bool` | `False` | 是否启用 `fpgen` 进行指纹伪装 |
| `fpgen_args` | `dict` | `{}` | 传入 `fpgen.generate` 的 keyword args 参数 |
"""


request_settings = RequestSettings()
"""
模块请求客户端的全局设置实例，继承自 `RequestSettings`。

亦可通过 `get_settings` 获取此实例。

相关使用方法请参考 `RequestSettings` 类文档。
"""
request_settings.__doc__ = """
模块请求客户端的全局设置实例，继承自 `RequestSettings`。

亦可通过 `get_settings` 获取此实例。

相关使用方法请参考 `RequestSettings` 类文档。
"""


################################################## END Settings ##################################################


################################################## BEGIN BiliAPIClient ##################################################


@dataclass
class BiliAPIResponse:
    """
    响应对象类。

    Attributes:
        code    (int)            : 响应码
        headers (dict[str, str]) : 响应头
        cookies (dict[str, str]) : 当前状态的 cookies
        raw     (bytes)          : 响应数据
        url     (str)            : 当前 url
    """

    code: int
    headers: dict[str, str]
    cookies: dict[str, str]
    raw: bytes
    url: str

    def utf8_text(self) -> str:
        """
        转为 utf8 文字

        Returns:
            str: utf8 文字
        """
        return self.raw.decode("utf-8")

    def json(self) -> dict[str, Any]:
        """
        解析 json

        Returns:
            dict[str, Any]: 解析后的 json
        """
        return json.loads(self.utf8_text())


class BiliWsMsgType(Enum):
    """
    WebSocket 状态枚举

    - CONTINUATION: 延续
    - TEXT: 文字
    - BINARY: 字节
    - PING: ping
    - PONG: pong
    - CLOSE: 关闭

    - CLOSING: 正在关闭
    - CLOSED: 已关闭
    """

    CONTINUATION = 0x0
    TEXT = 0x1
    BINARY = 0x2
    PING = 0x9
    PONG = 0xA
    CLOSE = 0x8
    CLOSING = 0x100
    CLOSED = 0x101


@dataclass
class BiliAPIFile:
    """
    上传文件类。

    Attributes:
        name      (str)  : 文件名
        content   (bytes): 文件内容
        mime_type (str)  : 文件类型
    """

    name: str
    content: bytes
    mime_type: str

    @staticmethod
    async def open(path: str) -> "BiliAPIFile":
        """
        打开文件

        Args:
            path (str): 文件地址
        """
        async with await open_file(path, "rb") as file:
            content = await file.read()
            name = os.path.basename(path)
            mime_type = mimetypes.guess_type(name)[0] or ""
            return BiliAPIFile(name=name, content=content, mime_type=mime_type)

    def __str__(self) -> str:
        return f"BiliAPIFile(name='{self.name}', mime_type='{self.mime_type}')"

    def __repr__(self) -> str:
        return f"BiliAPIFile(name='{self.name}', mime_type='{self.mime_type}')"


class BiliAPIClient(ABC):
    '''
    请求客户端抽象类。通过对第三方模块请求客户端的封装令模块可对其进行调用。

    ``` python
    class BiliAPIClient(ABC):
        """
        请求客户端抽象类。通过对第三方模块请求客户端的封装令模块可对其进行调用。
        """
        @abstractmethod
        def __init__(
            self,
            proxy: str = "",
            timeout: float = 0.0,
            verify_ssl: bool = True,
            trust_env: bool = True,
            session: object | None = None,
        ) -> None:
            """
            Args:
                proxy (str, optional): 代理地址. Defaults to "".
                timeout (float, optional): 请求超时时间. Defaults to 0.0.
                verify_ssl (bool, optional): 是否验证 SSL. Defaults to True.
                trust_env (bool, optional): `trust_env`. Defaults to True.
                session (object, optional): 会话对象. Defaults to None.

            Note: 仅当用户只提供 `session` 参数且用户中途未调用 `set_xxx` 函数才使用用户提供的 `session`。
            """
            raise NotImplementedError

        @abstractmethod
        def get_wrapped_session(self) -> object:
            """
            获取封装的第三方会话对象

            Returns:
                object: 第三方会话对象
            """
            raise NotImplementedError

        @abstractmethod
        def set_timeout(self, timeout: float = 0.0) -> None:
            """
            设置请求超时时间

            Args:
                timeout (float, optional): 请求超时时间. Defaults to 0.0.
            """
            raise NotImplementedError

        @abstractmethod
        def set_proxy(self, proxy: str = "") -> None:
            """
            设置代理地址

            Args:
                proxy (str, optional): 代理地址. Defaults to "".
            """
            raise NotImplementedError

        @abstractmethod
        def set_verify_ssl(self, verify_ssl: bool = True) -> None:
            """
            设置是否验证 SSL

            Args:
                verify_ssl (bool, optional): 是否验证 SSL. Defaults to True.
            """
            raise NotImplementedError

        @abstractmethod
        def set_trust_env(self, trust_env: bool = True) -> None:
            """
            设置 `trust_env`

            Args:
                trust_env (bool, optional): `trust_env`. Defaults to True.
            """
            raise NotImplementedError

        @abstractmethod
        async def request(
            self,
            method: str = "",
            url: str = "",
            params: dict | None = None,
            data: dict | str | bytes | None = None,
            files: dict[str, BiliAPIFile] | None = None,
            headers: dict | None = None,
            cookies: dict | None = None,
            allow_redirects: bool = True,
        ) -> BiliAPIResponse:
            """
            进行 HTTP 请求

            Args:
                method (str, optional): 请求方法. Defaults to "".
                url (str, optional): 请求地址. Defaults to "".
                params (dict | None, optional): 请求参数. Defaults to None.
                data (dict | str | bytes | None, optional): 请求数据. Defaults to None.
                files (dict[str, BiliAPIFile] | None, optional): 请求文件. Defaults to None.
                headers (dict | None, optional): 请求头. Defaults to None.
                cookies (dict | None, optional): 请求 Cookies. Defaults to None.
                allow_redirects (bool, optional): 是否允许重定向. Defaults to True.

            Returns:
                BiliAPIResponse: 响应对象

            Note: 无需实现 data 为 str 且 files 不为空的情况。
            """
            params = params or {}
            data = data or {}
            files = files or {}
            headers = headers or {}
            cookies = cookies or {}
            raise NotImplementedError

        @abstractmethod
        async def download_create(
            self,
            url: str = "",
            headers: dict | None = None,
            chunk_size: int = 4096,
        ) -> int:
            """
            开始下载文件

            Args:
                url        (str, optional)        : 请求地址. Defaults to "".
                headers    (dict | None, optional): 请求头. Defaults to None.
                chunk_size (int, optional)        : 单次迭代数据大小. Defaults to 4096.

            Returns:
                int: 下载编号，用于后续操作。
            """
            headers = headers or {}
            raise NotImplementedError

        @abstractmethod
        async def download_chunk(self, cnt: int) -> bytes:
            """
            下载部分文件

            Args:
                cnt    (int): 下载编号

            Returns:
                bytes: 字节
            """
            raise NotImplementedError

        @abstractmethod
        def download_content_length(self, cnt: int) -> int:
            """
            获取下载总字节数

            Args:
                cnt    (int): 下载编号

            Returns:
                int: 下载总字节数
            """
            raise NotImplementedError

        @abstractmethod
        async def download_close(self, cnt: int) -> None:
            """
            结束下载

            Args:
                cnt    (int): 下载编号
            """
            raise NotImplementedError

        @abstractmethod
        async def ws_create(
            self, url: str = "", params: dict | None = None, headers: dict | None = None
        ) -> int:
            """
            创建 WebSocket 连接

            Args:
                url (str, optional): WebSocket 地址. Defaults to "".
                params (dict | None, optional): WebSocket 参数. Defaults to None.
                headers (dict | None, optional): WebSocket 头. Defaults to None.

            Returns:
                int: WebSocket 连接编号，用于后续操作。
            """
            params = params or {}
            headers = headers or {}
            raise NotImplementedError

        @abstractmethod
        async def ws_send(self, cnt: int, data: bytes) -> None:
            """
            发送 WebSocket 数据

            Args:
                cnt (int): WebSocket 连接编号
                data (bytes): WebSocket 数据
            """
            raise NotImplementedError

        @abstractmethod
        async def ws_recv(self, cnt: int) -> tuple[bytes, BiliWsMsgType]:
            """
            接受 WebSocket 数据

            Args:
                cnt (int): WebSocket 连接编号

            Returns:
                Tuple[bytes, BiliWsMsgType]: WebSocket 数据和状态

            Note: 建议实现此函数时支持其他线程关闭不阻塞，除基础状态同时实现 CLOSING, CLOSED。
            """
            raise NotImplementedError

        @abstractmethod
        async def ws_close(self, cnt: int) -> None:
            """
            关闭 WebSocket 连接

            Args:
                cnt (int): WebSocket 连接编号
            """
            raise NotImplementedError

        @abstractmethod
        async def close(self) -> None:
            """
            关闭请求客户端，即关闭封装的第三方会话对象
            """
            raise NotImplementedError
    ```
    '''

    @abstractmethod
    def __init__(
        self,
        proxy: str = "",
        timeout: float = 0.0,
        verify_ssl: bool = True,
        trust_env: bool = True,
        session: object | None = None,
    ) -> None:
        """
        Args:
            proxy (str, optional): 代理地址. Defaults to "".
            timeout (float, optional): 请求超时时间. Defaults to 0.0.
            verify_ssl (bool, optional): 是否验证 SSL. Defaults to True.
            trust_env (bool, optional): `trust_env`. Defaults to True.
            session (object, optional): 会话对象. Defaults to None.

        Note: 仅当用户只提供 `session` 参数且用户中途未调用 `set_xxx` 函数才使用用户提供的 `session`。
        """
        raise NotImplementedError

    @abstractmethod
    def get_wrapped_session(self) -> object:
        """
        获取封装的第三方会话对象

        Returns:
            object: 第三方会话对象
        """
        raise NotImplementedError

    @abstractmethod
    def set_timeout(self, timeout: float = 0.0) -> None:
        """
        设置请求超时时间

        Args:
            timeout (float, optional): 请求超时时间. Defaults to 0.0.
        """
        raise NotImplementedError

    @abstractmethod
    def set_proxy(self, proxy: str = "") -> None:
        """
        设置代理地址

        Args:
            proxy (str, optional): 代理地址. Defaults to "".
        """
        raise NotImplementedError

    @abstractmethod
    def set_verify_ssl(self, verify_ssl: bool = True) -> None:
        """
        设置是否验证 SSL

        Args:
            verify_ssl (bool, optional): 是否验证 SSL. Defaults to True.
        """
        raise NotImplementedError

    @abstractmethod
    def set_trust_env(self, trust_env: bool = True) -> None:
        """
        设置 `trust_env`

        Args:
            trust_env (bool, optional): `trust_env`. Defaults to True.
        """
        raise NotImplementedError

    @abstractmethod
    async def request(
        self,
        method: str = "",
        url: str = "",
        params: dict | None = None,
        data: dict | str | bytes | None = None,
        files: dict[str, BiliAPIFile] | None = None,
        headers: dict | None = None,
        cookies: dict | None = None,
        allow_redirects: bool = True,
    ) -> BiliAPIResponse:
        """
        进行 HTTP 请求

        Args:
            method (str, optional): 请求方法. Defaults to "".
            url (str, optional): 请求地址. Defaults to "".
            params (dict | None, optional): 请求参数. Defaults to None.
            data (dict | str | bytes | None, optional): 请求数据. Defaults to None.
            files (dict[str, BiliAPIFile] | None, optional): 请求文件. Defaults to None.
            headers (dict | None, optional): 请求头. Defaults to None.
            cookies (dict | None, optional): 请求 Cookies. Defaults to None.
            allow_redirects (bool, optional): 是否允许重定向. Defaults to True.

        Returns:
            BiliAPIResponse: 响应对象

        Note: 无需实现 data 为 str 且 files 不为空的情况。
        """
        params = params or {}
        data = data or {}
        files = files or {}
        headers = headers or {}
        cookies = cookies or {}
        raise NotImplementedError

    @abstractmethod
    async def download_create(
        self,
        url: str = "",
        headers: dict | None = None,
        chunk_size: int = 4096,
    ) -> int:
        """
        开始下载文件

        Args:
            url        (str, optional)        : 请求地址. Defaults to "".
            headers    (dict | None, optional): 请求头. Defaults to None.
            chunk_size (int, optional)        : 单次迭代数据大小. Defaults to 4096.

        Returns:
            int: 下载编号，用于后续操作。
        """
        headers = headers or {}
        raise NotImplementedError

    @abstractmethod
    async def download_chunk(self, cnt: int) -> bytes:
        """
        下载部分文件

        Args:
            cnt    (int): 下载编号

        Returns:
            bytes: 字节
        """
        raise NotImplementedError

    @abstractmethod
    def download_content_length(self, cnt: int) -> int:
        """
        获取下载总字节数

        Args:
            cnt    (int): 下载编号

        Returns:
            int: 下载总字节数
        """
        raise NotImplementedError

    @abstractmethod
    async def download_close(self, cnt: int) -> None:
        """
        结束下载

        Args:
            cnt    (int): 下载编号
        """
        raise NotImplementedError

    @abstractmethod
    async def ws_create(
        self, url: str = "", params: dict | None = None, headers: dict | None = None
    ) -> int:
        """
        创建 WebSocket 连接

        Args:
            url (str, optional): WebSocket 地址. Defaults to "".
            params (dict | None, optional): WebSocket 参数. Defaults to None.
            headers (dict | None, optional): WebSocket 头. Defaults to None.

        Returns:
            int: WebSocket 连接编号，用于后续操作。
        """
        params = params or {}
        headers = headers or {}
        raise NotImplementedError

    @abstractmethod
    async def ws_send(self, cnt: int, data: bytes) -> None:
        """
        发送 WebSocket 数据

        Args:
            cnt (int): WebSocket 连接编号
            data (bytes): WebSocket 数据
        """
        raise NotImplementedError

    @abstractmethod
    async def ws_recv(self, cnt: int) -> tuple[bytes, BiliWsMsgType]:
        """
        接受 WebSocket 数据

        Args:
            cnt (int): WebSocket 连接编号

        Returns:
            Tuple[bytes, BiliWsMsgType]: WebSocket 数据和状态

        Note: 建议实现此函数时支持其他线程关闭不阻塞，除基础状态同时实现 CLOSING, CLOSED。
        """
        raise NotImplementedError

    @abstractmethod
    async def ws_close(self, cnt: int) -> None:
        """
        关闭 WebSocket 连接

        Args:
            cnt (int): WebSocket 连接编号
        """
        raise NotImplementedError

    @abstractmethod
    async def close(self) -> None:
        """
        关闭请求客户端，即关闭封装的第三方会话对象
        """
        raise NotImplementedError


################################################## END BiliAPIClient ##################################################


################################################## BEGIN Session Management ##################################################


client_func_cnt = 0
client_lock = ThreadingLock()
loops: set[EventLoopToken] = set()


class MultiEventLoopLocks:
    def __init__(self) -> None:
        # helper class for Credential locking
        # for Credential is used by many event loops
        self._locks: dict[EventLoopToken, Lock] = {}
        self._lock: ThreadingLock = ThreadingLock()
        self._running: bool = False
        self._multithread_lock: ThreadingLock = ThreadingLock()
        self._events: dict[EventLoopToken, Event] = {}

    def get_lock(self) -> Lock:
        event_loop = current_token()
        if self._locks.get(event_loop):
            return self._locks[event_loop]
        with self._lock:
            if not self._locks.get(event_loop):
                self._locks[event_loop] = Lock()
        return self._locks[event_loop]

    def check_multithread_state(self) -> bool:
        with self._multithread_lock:
            if not self._running:
                self._running = True
                return True  # the first thread is able to execute
        return False  # other threads won't execute, as duplicated

    async def wait_multithread(self) -> None:
        # this function should be locked in get_lock() while running
        event_loop = current_token()
        while self._running:  # prevent lock releasing in advance
            event = Event()
            self._events[event_loop] = event
            try:
                await event.wait()
            finally:
                if self._events.get(event_loop) is event:
                    del self._events[event_loop]

    async def done_multithread(self) -> None:
        # this function should be run after completing multithread task
        self._running = False

        def stop_waiting_anyio_events():
            for token, event in list(self._events.items()):
                from_thread.run_sync(event.set, token=token)

        await to_thread.run_sync(stop_waiting_anyio_events)


class BiliFilterFlags(Enum):
    """
    过滤器行为枚举

    返回过滤器行为可通过函数 `return` 返回或生成器 `yield` 抛出。

    `return` 只能返回一个行为， `yield` 可以抛出多个行为。

    - 【NOTE】以下过滤器建议配合 `yield` 使用。
    - SET_PARAMS: 设置函数的参数 (仅前置过滤器)
    - SET_RETURN: 设置返回值 (仅后置过滤器)
    - 【NOTE】以下过滤器需要配合 `yield` + `return` 使用。
    - CONTINUE: 继续下一个过滤器
    - EXECUTE_NOW: 直接运行函数 (仅前置过滤器)
    - RETURN_NOW: 直接作为函数返回值返回
    - GOTO: 跳到任意一个过滤器 需通过 `get_registered_filters` 查询对应过滤器的下标
    """

    SET_PARAMS = "SET PARAMS"
    SET_RETURN = "SET RETURN"
    CONTINUE = "GOTO NEXT"
    EXECUTE_NOW = "GOTO EXECUTE"
    RETURN_NOW = "GOTO RETURN"
    GOTO = "GOTO IDX"


class BiliFilterData:
    """
    过滤器存储交换数据使用的实例
    """

    def __init__(self) -> None:
        self.__data: dict[str, Any] = {}

    def set_data(self, key: str, value: Any) -> None:
        """
        设置数据

        Args:
            key (str): 键
            value (Any): 值
        """
        self.__data[key] = value

    def has_data(self, key: str) -> bool:
        """
        是否存在数据

        Args:
            key (str): 键

        Returns:
            bool: 是否存在数据
        """
        return key in self.__data.keys()

    def get_data(self, key: str) -> Any:
        """
        获取数据

        Args:
            key (str): 键

        Returns:
            Any: 值
        """
        return self.__data[key]


@dataclass
class BiliFilterArgs:
    """
    传入过滤器的参数，携带以下信息。

    Attributes:
        client (str): 当前选择的的客户端
        instance (str): 请求所属的实例
        settings (dict): 请求客户端相关设置
        event_loop_token (anyio.lowlevel.EventLoopToken): 请求客户端的事件循环，对应模块内部编号
        sess (BiliAPIClient): 调用的 BiliAPIClient 实例
        func (str): 当前调用的函数
        params (dict): 调用函数的参数
        ret (Any): 函数运行返回结果 (可能存在)
        filter_cnt (int): 过滤器执行编号，一个编号对应一次函数调用
        filter_data (FilterData): 用于数据交换的 FilterData 实例
        filter_index (int): 过滤器在运行列表中的位置下标
        filter_locate (str): 过滤器位置，前置为 `pre`，后置为 `post`。
    """

    # 1. session related
    client: str
    instance: str
    settings: dict
    event_loop_token: EventLoopToken
    # 2. invokation related
    sess: BiliAPIClient
    func: str
    params: dict
    ret: Any
    # 3. filter execution related
    filter_cnt: int
    filter_data: BiliFilterData
    filter_index: int
    filter_locate: str

    def get_event_loop(self) -> AbstractEventLoop:
        """
        获取事件循环 (asyncio.AbstractEventLoop)

        Returns:
            asyncio.AbstractEventLoop: 事件循环
        """
        raise_for_statement(
            self.event_loop_token.backend_class.__name__ == "AsyncIOBackend",
            "当前异步框架并非 asyncio",
        )
        return self.event_loop_token.native_token  # type: ignore

    if TRIO_AVAILABLE:

        def get_trio_token(self) -> TrioToken:  # type: ignore
            """
            获取 TrioToken

            Returns:
                trio.lowlevel.TrioToken: TrioToken
            """
            raise_for_statement(
                self.event_loop_token.backend_class.__name__ == "TrioBackend",
                "当前异步框架并非 trio",
            )
            return self.event_loop_token.native_token  # type: ignore


class BiliFilterReturn:
    """
    用于结束过滤器返回结果的工具类
    """

    Returns = tuple[BiliFilterFlags, Any]

    @staticmethod
    def continue_exec() -> tuple[BiliFilterFlags, None]:
        """
        继续过滤器执行

        Returns:
            tuple[BiliFilterFlags, None]: 过滤器函数返回值
        """
        return BiliFilterFlags.CONTINUE, None

    @staticmethod
    def set_params(params: dict) -> tuple[BiliFilterFlags, dict]:
        """
        设置函数的参数 (仅前置过滤器)

        Args:
            params (dict): 参数

        Returns:
            tuple[BiliFilterFlags, dict]: 过滤器函数返回值
        """
        return BiliFilterFlags.SET_PARAMS, params

    @staticmethod
    def set_return(ret: Any) -> tuple[BiliFilterFlags, Any]:
        """
        设置函数的返回值 (仅后置过滤器)

        Args:
            ret (Any): 函数返回值

        Returns:
            tuple[BiliFilterFlags, Any]: 过滤器函数返回值
        """
        return BiliFilterFlags.SET_RETURN, ret

    @staticmethod
    def execute_now() -> tuple[BiliFilterFlags, None]:
        """
        直接运行函数 (仅前置过滤器)

        Returns:
            tuple[BiliFilterFlags, None]: 过滤器函数返回值
        """
        return BiliFilterFlags.EXECUTE_NOW, None

    @staticmethod
    def return_now() -> tuple[BiliFilterFlags, None]:
        """
        直接返回结果，作为待运行函数返回值

        Returns:
            tuple[BiliFilterFlags, None]: 过滤器函数返回值
        """
        return BiliFilterFlags.RETURN_NOW, None

    @staticmethod
    def goto_idx(idx: int) -> tuple[BiliFilterFlags, int]:
        """
        跳到任意一个过滤器

        Args:
            idx (int): 对应过滤器的下标，可 `get_registered_(pre|post)_filters` 查询

        Returns:
            tuple[BiliFilterFlags, int]: 过滤器函数返回值
        """
        return BiliFilterFlags.GOTO, idx

    @staticmethod
    def goto_name(name: str) -> tuple[BiliFilterFlags, int]:
        """
        跳到任意一个过滤器

        Args:
            name (str): 对应过滤器名称

        Returns:
            tuple[BiliFilterFlags, int]: 过滤器函数返回值
        """
        for idx, fil in enumerate(get_registered_filters()):
            if fil["name"] == name:
                return BiliFilterFlags.GOTO, idx
        raise ArgsException(f"未找到前置过滤器 {name}")


class _BiliAPIClient:
    """
    BiliAPIClient 进一步包装。提供设置支持与过滤器支持。
    """

    def __init__(
        self,
        client_name: str,
        client_instance: str,
        client_settings: RequestSettings,
        client_session: Any,
        event_loop: EventLoopToken,
    ) -> None:
        self.__client__: str = client_name
        self.__instance__: str = client_instance
        if client_session:
            self.client = sessions[self.__client__](session=client_session)
        else:
            self.client = sessions[self.__client__](**client_settings.all())
            client_settings._pop_lazy()  # 所有设置已在 __init__ 中应用
        self.__settings = client_settings
        self.__event_loop = event_loop
        loops.add(self.__event_loop)

    def _sync_settings(self, settings: dict) -> None:
        # this function is invocated by _BiliAPIClientGroup
        self.__settings.sets(
            settings
        )  # sync _BiliAPIClient settings with _BiliAPIClientGroup

    def _get_bili_api_client(self) -> BiliAPIClient:
        # apply settings to BiliAPIClient
        for key, val in self.__settings._pop_lazy().items():
            try:
                getattr(self.client, "set_" + key)(val)
            except AttributeError:
                pass
        return self.client

    def __getattr__(self, key: str) -> Any:
        obj = getattr(self.client, key)
        if not (isfunction(obj) or iscoroutinefunction(obj)):
            return obj

        if key.startswith("_"):
            return obj

        if key.startswith("set_"):
            raise ArgsException(
                "不支持直接调用 set_xxx 函数。请使用 get_settings / get_instance_settings / get_force_settings 间接设置。"
            )

        global client_func_cnt
        with client_lock:
            client_func_cnt += 1
            cnt = client_func_cnt

        def arg_convert(args, kwargs) -> dict[str, Any]:
            # convert args to kwargs
            # functions are not allowed to use *args or **kwargs
            ret: dict = kwargs
            args = list(args)
            sig = signature(obj)
            for name, _ in list(sig.parameters.items()):
                if len(args) == 0:
                    break
                ret[name] = args.pop(0)
            for name, param in list(sig.parameters.items()):
                if name not in ret.keys():
                    ret[name] = param.default
            return ret

        def run_filter(
            filter: Callable[[BiliFilterArgs], Any], args: BiliFilterArgs
        ) -> list[tuple[BiliFilterFlags, Any]]:
            result = filter(args)
            if isgenerator(result):
                return list(result)  # type: ignore
            else:
                if not result:
                    result = BiliFilterReturn.continue_exec()
                return [result]  # type: ignore

        async def arun_filter(
            filter: Callable[[BiliFilterArgs], Any], args: BiliFilterArgs
        ) -> list[tuple[BiliFilterFlags, Any]]:
            result = filter(args)
            if isasyncgen(result):
                ret = []
                async for item in result:
                    ret.append(item)
                return ret
            else:
                result = await result
                if not result:
                    result = BiliFilterReturn.continue_exec()
                return [result]  # type: ignore

        def method_wrapper(method: Callable) -> Callable:
            def wrapped_method(*args, **kwargs) -> Any:
                args = arg_convert(args, kwargs)
                ret = None
                filter_args = {
                    "client": self.__client__,
                    "instance": self.__instance__,
                    "func": key,
                    "sess": self._get_bili_api_client(),
                    "filter_cnt": cnt,
                    "filter_data": BiliFilterData(),
                    "settings": self.__settings.all(),
                    "event_loop_token": self.__event_loop,
                }
                filts = get_registered_filters(in_priority=True)
                skip_pre = False
                log_helper = {"pre": ["PRE", "前置"], "post": ["POST", "后置"]}
                i = 0
                while i < len(filts):
                    filt = filts[i]
                    locate = filt["locate"]
                    if not skip_pre:
                        request_log.dispatch(
                            f"DO_{log_helper[locate][0]}_FILTER",
                            f"执行{log_helper[locate][1]}过滤器",
                            {
                                "act_id": cnt,
                                "name": filt["name"],
                                "priority": filt["priority"],
                                "client": self.__client__,
                                "instance": self.__instance__,
                                "action": key,
                                "event_loop": self.__event_loop,
                                "filter_id": i,
                            },
                        )
                    gflag = BiliFilterFlags.CONTINUE
                    gparam: Any = None
                    if locate == "pre" and skip_pre:
                        pass
                    elif filt.get("function"):
                        try:
                            results = run_filter(
                                filt["function"],
                                BiliFilterArgs(
                                    **filter_args,
                                    params=args.copy(),
                                    ret=deepcopy(ret),
                                    filter_index=i,
                                    filter_locate=locate,
                                ),
                            )
                        except Exception as e:
                            raise FilterException(locate, filt["name"], e) from e
                        for result in results:
                            try:
                                sflag, sparam = result[0], result[1]
                            except Exception:
                                raise ArgsException(
                                    "过滤器返回值/生成值不满足形式 tuple[BiliFilterFlags, Any]。"
                                ) from None
                            if sflag == BiliFilterFlags.SET_PARAMS:
                                args = deepcopy(sparam)
                            elif sflag == BiliFilterFlags.SET_RETURN:
                                ret = deepcopy(sparam)
                            gflag, gparam = sflag, sparam
                    else:
                        i += 1
                        continue
                    if gflag == BiliFilterFlags.EXECUTE_NOW:
                        skip_pre = True
                    elif gflag == BiliFilterFlags.RETURN_NOW:
                        return ret
                    elif gflag == BiliFilterFlags.GOTO:
                        raise_for_statement(
                            isinstance(gparam, int),
                            "执行 BiliFilterFlasg.GOTO 需同时传入整数值下标",
                        )
                        i = gparam
                        continue
                    i += 1
                    if locate == "pre" and (
                        i >= len(filts) or filts[i]["locate"] == "post"
                    ):
                        ret = method(**args)
                        skip_pre = False
                return ret

            return wrapped_method

        def coroutine_wrapper(async_function: Callable) -> Callable:
            async def wrapped_amethod(*args, **kwargs) -> Any:
                args = arg_convert(args, kwargs)
                ret = None
                filter_args = {
                    "client": self.__client__,
                    "instance": self.__instance__,
                    "func": key,
                    "sess": self._get_bili_api_client(),
                    "filter_cnt": cnt,
                    "filter_data": BiliFilterData(),
                    "settings": self.__settings.all(),
                    "event_loop_token": self.__event_loop,
                }
                filts = get_registered_filters(in_priority=True)
                skip_pre = False
                log_helper = {"pre": ["PRE", "前置"], "post": ["POST", "后置"]}
                i = 0
                while i < len(filts):
                    filt = filts[i]
                    locate = filt["locate"]
                    if not skip_pre:
                        request_log.dispatch(
                            f"DO_{log_helper[locate][0]}_FILTER",
                            f"执行{log_helper[locate][1]}过滤器",
                            {
                                "act_id": cnt,
                                "name": filt["name"],
                                "priority": filt["priority"],
                                "client": self.__client__,
                                "instance": self.__instance__,
                                "action": key,
                                "event_loop": self.__event_loop,
                                "filter_id": i,
                            },
                        )
                    gflag = BiliFilterFlags.CONTINUE
                    gparam: Any = None
                    if locate == "pre" and skip_pre:
                        pass
                    elif filt.get("function") or filt.get("async_function"):
                        try:
                            if filt.get("function"):
                                results = await to_thread.run_sync(
                                    run_filter,
                                    filt["function"],
                                    BiliFilterArgs(
                                        **filter_args,
                                        params=args.copy(),
                                        ret=deepcopy(ret),
                                        filter_index=i,
                                        filter_locate=locate,
                                    ),
                                )
                            elif filt.get("async_function"):
                                results = await arun_filter(
                                    filt["async_function"],
                                    BiliFilterArgs(
                                        **filter_args,
                                        params=args.copy(),
                                        ret=deepcopy(ret),
                                        filter_index=i,
                                        filter_locate=locate,
                                    ),
                                )
                            else:
                                results = []
                        except Exception as e:
                            raise FilterException(locate, filt["name"], e) from e
                        for result in results:
                            try:
                                sflag, sparam = result[0], result[1]
                            except Exception:
                                raise ArgsException(
                                    "过滤器返回值/生成值不满足形式 tuple[BiliFilterFlags, Any]。"
                                ) from None
                            if sflag == BiliFilterFlags.SET_PARAMS:
                                args = deepcopy(sparam)
                            elif sflag == BiliFilterFlags.SET_RETURN:
                                ret = deepcopy(sparam)
                            gflag, gparam = sflag, sparam
                    else:
                        i += 1
                        continue
                    if gflag == BiliFilterFlags.EXECUTE_NOW:
                        skip_pre = True
                    elif gflag == BiliFilterFlags.RETURN_NOW:
                        return ret
                    elif gflag == BiliFilterFlags.GOTO:
                        raise_for_statement(
                            isinstance(gparam, int),
                            "执行 BiliFilterFlasg.GOTO 需同时传入整数值下标",
                        )
                        i = gparam
                        continue
                    i += 1
                    if locate == "pre" and (
                        i >= len(filts) or filts[i]["locate"] == "post"
                    ):
                        ret = await async_function(**args)  # type: ignore
                        skip_pre = False
                return ret

            return wrapped_amethod

        if iscoroutinefunction(obj):
            return coroutine_wrapper(obj)
        elif isfunction(obj):
            return method_wrapper(obj)
        return None


class _BiliAPIClientGroup:
    """
    helper class to sync settings among clients in different event loops
    """

    def __init__(self, client: str, name: str) -> None:
        self.__session_pool: dict[EventLoopToken, "_BiliAPIClient"] = {}
        self.__set_session_pool: dict[EventLoopToken, "_BiliAPIClient"] = {}
        self.__base_settings = RequestSettings()
        self.__base_settings._set_base(client_defaults[client])
        self.__force_settings = RequestSettings()
        self.__client__ = client
        self.__instance__ = name
        self.__ensure_locks: dict[EventLoopToken, ThreadingLock] = {}
        self.__loop_record_lock = ThreadingLock()

    def _prepare_settings(self) -> RequestSettings:
        # merge global settings to base settings
        settings = RequestSettings()
        settings._set_base(self.__base_settings.defaults())
        settings.sets(self.__base_settings.all())
        settings.sets(request_settings.all() | self.__force_settings.all())
        return settings

    def _get_loop_lock(self, loop: EventLoopToken | None = None) -> ThreadingLock:
        loop = loop or current_token()
        if self.__ensure_locks.get(loop):
            return self.__ensure_locks[loop]
        with self.__loop_record_lock:
            if not self.__ensure_locks.get(loop):
                self.__ensure_locks[loop] = ThreadingLock()
        return self.__ensure_locks[loop]

    def ensure_client(self, loop: EventLoopToken | None = None) -> _BiliAPIClient:
        loop = loop or current_token()
        with self._get_loop_lock(loop):
            client = self.__session_pool.get(loop)
            if client is None:
                client = _BiliAPIClient(
                    self.__client__,
                    self.__instance__,
                    self._prepare_settings(),  # update base settings
                    None,
                    loop,
                )
                self.__session_pool[loop] = client
            return client

    def set_session(self, session: Any, loop: EventLoopToken | None = None) -> None:
        loop = loop or current_token()
        client = _BiliAPIClient(
            self.__client__,
            self.__instance__,
            RequestSettings(),  # unable to configure
            session,
            loop,
        )
        self.__set_session_pool[loop] = client

    def unset_session(self, loop: EventLoopToken | None = None) -> None:
        loop = loop or current_token()
        if not self.__set_session_pool.get(loop):
            return
        del self.__set_session_pool[loop]

    def get_client(self, loop: EventLoopToken | None = None) -> _BiliAPIClient:
        loop = loop or current_token()
        if self.__set_session_pool.get(loop):
            client = self.__set_session_pool[loop]
        else:
            if loop == current_token():
                client = self.ensure_client(loop)
            else:
                client = from_thread.run_sync(self.ensure_client, loop, token=loop)
            # sync _BiliAPIClientGroup settings to _BiliAPIClient
            client._sync_settings(self._prepare_settings().all())
        return client

    def get_base_settings(self) -> RequestSettings:
        return self.__base_settings

    def get_force_settings(self) -> RequestSettings:
        return self.__force_settings

    async def clean(self, loop: EventLoopToken | None = None) -> None:
        loop = loop or current_token()
        sess = self.__session_pool.get(loop)
        if sess:
            if loop == current_token():
                await sess.close()
            else:
                await to_thread.run_sync(from_thread.run, sess.close, loop)
        set_sess = self.__set_session_pool.get(loop)
        if set_sess:
            if loop == current_token():
                await set_sess.close()
            else:
                await to_thread.run_sync(from_thread.run, set_sess.close, loop)


sessions: dict[str, type["BiliAPIClient"]] = {}  # client -> BiliAPIClient class
client_settings: dict[str, list] = {}  # client -> settings
client_defaults: dict[str, dict] = {}
client_groups: dict[str, dict[str, _BiliAPIClientGroup]] = {}  # client -> instance
selected_client = ""
selected_instance = ""
selected_client_context: ContextVar[str] = ContextVar("bili_client", default="")
selected_instance_context: ContextVar[str] = ContextVar("bili_instance", default="")
__registered_filters = []


##### client #####


def register_client(name: str, cls: type, settings: dict | None = None) -> None:
    """
    注册请求客户端并切换，可用于用户自定义请求客户端。

    Args:
        name (str): 请求客户端类型名称，用户自定义命名。
        cls (type): 基于 BiliAPIClient 重写后的请求客户端类。
        settings (dict | None, optional): 请求客户端支持的所有设置，键为设置名称，值为设置默认值. Defaults to None.
    """
    global sessions, client_groups
    raise_for_statement(
        issubclass(cls, BiliAPIClient), "传入的类型需要继承 BiliAPIClient"
    )
    if name in sessions.keys():
        raise ArgsException(f"已注册过请求客户端 {name}")
    sessions[name] = cls
    client_groups[name] = {}
    select_client(name)
    settings = settings or {}
    client_settings[name] = list(settings.keys())
    client_defaults[name] = settings
    new_instance("default", name)


def unregister_client(name: str) -> None:
    """
    取消注册请求客户端，可用于用户自定义请求客户端。

    Args:
        name (str): 请求客户端类型名称，用户自定义命名。
    """
    global sessions, client_groups
    try:
        sessions.pop(name)
        client_groups.pop(name)
    except KeyError as e:
        raise ArgsException("未找到指定请求客户端。") from e


def select_client(name: str, local_context: bool = False) -> None:
    """
    选择模块使用的注册过的请求客户端，可用于用户自定义请求客户端。

    Args:
        name (str): 请求客户端类型名称，用户自定义命名。
        local_context (bool): 是否通过 `ContextVar` 仅在局部上下文设置。Defaults to False.
    """
    if not sessions.get(name):
        raise ArgsException(f"未注册过 {name}。")
    if local_context:
        selected_client_context.set(name)
    else:
        global selected_client
        selected_client = name


def get_selected_client() -> tuple[str, type[BiliAPIClient]]:
    """
    获取用户选择的请求客户端名称和对应的类

    Returns:
        tuple[str, type[BiliAPIClient]]: 第 0 项为客户端名称，第 1 项为对应的类
    """
    if selected_client_context.get() != "":
        return selected_client_context.get(), sessions[selected_client_context.get()]
    if selected_client != "":
        return selected_client, sessions[selected_client]
    raise ArgsException(
        "尚未安装第三方请求库或未注册自定义第三方请求库。\n$ pip3 install (curl_cffi|httpx|aiohttp)"
    )


def get_registered_clients() -> dict[str, type[BiliAPIClient]]:
    """
    获取所有注册过的 BiliAPIClient

    Returns:
        dict[str, type[BiliAPIClient]]: 注册过的 BiliAPIClient
    """
    return sessions


##### instance #####


def new_instance(name: str, client: str | None = None) -> None:
    """
    创建新的请求客户端实例并选择

    Args:
        name (str): 名称
        client (str | None, optional): BiliAPIClient 类型. Defaults to None.
    """
    client = client or get_selected_client()[0]
    global client_groups
    if name in client_groups[client].keys():
        raise ArgsException(f"已存在 {client} 的实例 {name}")
    client_groups[client][name] = _BiliAPIClientGroup(client, name)
    select_instance(name)


def remove_instance(name: str, client: str | None = None) -> None:
    """
    移除请求客户端实例

    Args:
        name (str): 名称
        client (str | None, optional): BiliAPIClient 类型. Defaults to None.
    """
    client = client or get_selected_client()[0]
    global client_groups
    try:
        client_groups[client].pop(name)
    except KeyError as e:
        raise ArgsException("未找到指定请求客户端实例。") from e


def select_instance(name: str, local_context: bool = False) -> None:
    """
    选择请求客户端实例

    Args:
        name (str): 名称
        local_context (bool): 是否通过 `ContextVar` 仅在局部上下文设置。Defaults to False.
    """
    if local_context:
        selected_instance_context.set(name)
    else:
        global selected_instance
        selected_instance = name


def get_selected_instance() -> str:
    """
    获取选择的请求客户端实例

    Returns:
        str: 选择的请求客户端实例
    """
    return selected_instance_context.get() or selected_instance


def get_instances(client: str | None = None) -> list[str]:
    """
    获取已创建的请求客户端实例

    Args:
        client (str | None, optional): 请求客户端类型. Defaults to None.

    Returns:
        list[str]: 请求客户端实例名称列表
    """
    client = client or get_selected_client()[0]
    return list(client_groups[client].keys())


def get_exist_instances() -> dict[str, list[str]]:
    """
    获取已创建的请求客户端实例

    Returns:
        dict[str, list[str]]: 请求客户端实例字典，
    """
    return {k: list(v.keys()) for k, v in client_groups.items()}


##### settings #####


def get_available_settings(client: str | None = None) -> list[str]:
    """
    获取支持的设置项

    Args:
        client (str | None, optional): 请求客户端类型. Defaults to None.

    Returns:
        list[str]: 支持的设置项名称
    """
    client = client or get_selected_client()[0]
    return client_settings[client]


def get_registered_available_settings() -> dict[str, list[str]]:
    """
    获取所有注册过的 BiliAPIClient 所支持的设置项

    Returns:
        dict[str, list[str]]: 所有注册过的 BiliAPIClient 所支持的设置项
    """
    return client_settings


def get_instance_settings(
    client: str | None = None, instance: str | None = None
) -> RequestSettings:
    """
    获取模块正在使用的请求客户端的设置

    Args:
        client (str | None, optional): 请求客户端类型. Defaults to None.
        instance (str | None, optional): 请求客户端实例名称. Defaults to None.

    Returns:
        RequestSettings: 设置类
    """
    client = client or get_selected_client()[0]
    instance = instance or get_selected_instance()
    try:
        group = client_groups[client][instance]
    except KeyError as e:
        raise ArgsException("未找到对应请求客户端实例") from e
    return group.get_base_settings()


def get_force_settings(
    client: str | None = None, instance: str | None = None
) -> RequestSettings:
    """
    获取模块正在使用的请求客户端的强制设置

    Args:
        client (str | None, optional): 请求客户端类型. Defaults to None.
        instance (str | None, optional): 请求客户端实例名称. Defaults to None.

    Returns:
        RequestSettings: 设置类
    """
    client = client or get_selected_client()[0]
    instance = instance or get_selected_instance()
    try:
        group = client_groups[client][instance]
    except KeyError as e:
        raise ArgsException("未找到对应请求客户端实例") from e
    return group.get_force_settings()


def get_settings() -> RequestSettings:
    """
    获取模块设置对象，通过对此对象函数调用可以访问与设置相关设置项。

    Returns:
        RequestSettings: 设置类
    """
    return request_settings


##### get_client() / get_session() / set_session() / unset_session() / clean_session() #####


def get_client(
    client: str | None = None,
    instance: str | None = None,
    loop: AbstractEventLoop | TrioToken | None = None,  # type: ignore
    token: EventLoopToken | None = None,
) -> BiliAPIClient:
    """
    获取模块正在使用的请求客户端

    Args:
        client (str | None, optional): 请求客户端类型. Defaults to None.
        instance (str | None, optional): 请求客户端实例名称. Defaults to None.
        loop (asyncio.AbstractEventLoop | trio.lowlevel.TrioToken | None): 事件循环，不提供则采用当前事件循环. Defaults to None.
        token (anyio.lowlevel.EventLoopToken | None, optional): anyio 事件循环令牌，不提供则使用 loop 参数. Defaults to None.

    Returns:
        BiliAPIClient: 请求客户端
    """
    if not token:
        if isinstance(loop, AbstractEventLoop):
            token = EventLoopToken(backend_class=AsyncIOBackend, native_token=loop)
        elif TRIO_AVAILABLE and isinstance(loop, TrioToken):  # type: ignore
            token = EventLoopToken(backend_class=TrioBackend, native_token=loop)  # type: ignore
        else:
            token = current_token()
    client = client or get_selected_client()[0]
    instance = instance or get_selected_instance()
    try:
        group = client_groups[client][instance]  # type: ignore
    except KeyError as e:
        raise ArgsException("未找到对应请求客户端实例") from e
    return group.get_client(token)  # type: ignore


def get_session(
    client: str | None = None,
    instance: str | None = None,
    loop: AbstractEventLoop | TrioToken | None = None,  # type: ignore
    token: EventLoopToken | None = None,
) -> object:
    """
    在当前事件循环下获取请求客户端的会话对象。

    Args:
        client (str | None, optional): 请求客户端类型. Defaults to None.
        instance (str | None, optional): 请求客户端实例名称. Defaults to None.
        loop (asyncio.AbstractEventLoop | trio.lowlevel.TrioToken | None): 事件循环，不提供则采用当前事件循环. Defaults to None.
        token (anyio.lowlevel.EventLoopToken | None, optional): anyio 事件循环令牌，不提供则使用 loop 参数. Defaults to None.

    Returns:
        object: 会话对象
    """
    client = client or get_selected_client()[0]
    instance = instance or get_selected_instance()
    return get_client(client, instance, loop, token).get_wrapped_session()


def set_session(
    session: object,
    client: str | None = None,
    instance: str | None = None,
    loop: AbstractEventLoop | TrioToken | None = None,  # type: ignore
    token: EventLoopToken | None = None,
) -> None:
    """
    设置请求客户端的会话对象。

    Args:
        session (object): 会话对象
        client (str | None, optional): 请求客户端类型. Defaults to None.
        instance (str | None, optional): 请求客户端实例名称. Defaults to None.
        loop (asyncio.AbstractEventLoop | trio.lowlevel.TrioToken | None): 事件循环，不提供则采用当前事件循环. Defaults to None.
        token (anyio.lowlevel.EventLoopToken | None, optional): anyio 事件循环令牌，不提供则使用 loop 参数. Defaults to None.
    """
    if not token:
        if isinstance(loop, AbstractEventLoop):
            token = EventLoopToken(backend_class=AsyncIOBackend, native_token=loop)
        elif TRIO_AVAILABLE and isinstance(loop, TrioToken):  # type: ignore
            token = EventLoopToken(backend_class=TrioBackend, native_token=loop)  # type: ignore
        else:
            token = current_token()
    client = client or get_selected_client()[0]
    instance = instance or get_selected_instance()
    try:
        group = client_groups[client][instance]
    except KeyError as e:
        raise ArgsException("未找到对应请求客户端实例") from e
    group.set_session(session, token)


def unset_session(
    client: str | None = None,
    instance: str | None = None,
    loop: AbstractEventLoop | TrioToken | None = None,  # type: ignore
    token: EventLoopToken | None = None,
) -> None:
    """
    取消设置请求客户端的会话对象。

    Args:
        client (str | None, optional): 请求客户端类型. Defaults to None.
        instance (str | None, optional): 请求客户端实例名称. Defaults to None.
        loop (asyncio.AbstractEventLoop | trio.lowlevel.TrioToken | None): 事件循环，不提供则采用当前事件循环. Defaults to None.
        token (anyio.lowlevel.EventLoopToken | None, optional): anyio 事件循环令牌，不提供则使用 loop 参数. Defaults to None.
    """
    if not token:
        if isinstance(loop, AbstractEventLoop):
            token = EventLoopToken(backend_class=AsyncIOBackend, native_token=loop)
        elif TRIO_AVAILABLE and isinstance(loop, TrioToken):  # type: ignore
            token = EventLoopToken(backend_class=TrioBackend, native_token=loop)  # type: ignore
        else:
            token = current_token()
    client = client or get_selected_client()[0]
    instance = instance or get_selected_instance()
    try:
        group = client_groups[client][instance]
    except KeyError as e:
        raise ArgsException("未找到对应请求客户端实例") from e
    group.unset_session(token)


async def clean_session(
    loop: AbstractEventLoop | TrioToken | None = None,  # type: ignore
    token: EventLoopToken | None = None,
) -> None:
    """
    关闭所有请求客户端的会话对象。

    Args:
        loop (asyncio.AbstractEventLoop | trio.lowlevel.TrioToken | None): 事件循环，不提供则采用当前事件循环. Defaults to None.
        token (anyio.lowlevel.EventLoopToken | None, optional): anyio 事件循环令牌，不提供则使用 loop 参数. Defaults to None.
    """
    if not token:
        if isinstance(loop, AbstractEventLoop):
            token = EventLoopToken(backend_class=AsyncIOBackend, native_token=loop)
        elif TRIO_AVAILABLE and isinstance(loop, TrioToken):  # type: ignore
            token = EventLoopToken(backend_class=TrioBackend, native_token=loop)  # type: ignore
        else:
            token = current_token()
    async with create_task_group() as tg:
        for client in client_groups.keys():
            for instance in client_groups[client].keys():
                tg.create_task(client_groups[client][instance].clean(token))


##### filter #####


def register_pre_filter(
    name: str,
    func: Callable | None = None,
    priority: int = 0,
) -> None:
    """
    注册/修改前置过滤器

    执行函数需返回一个元组，第一项为 BiliAPIFlags，第二项为配合 BiliAPIFlags 的值。

    所有当前函数执行的过滤器为 `ins.data[cnt]["pre_filters"]`。

    Args:
        name (str): 名称，若重复则为修改对应过滤器。
        func (Callable | None, optional): 执行的函数，参数传入 `FilterArgs` 对象. Defaults to None.
        priority (int, optional): 优先级，数字越小越优先执行. Defaults to 0.
    """
    global __registered_filters
    filt = {
        "name": name,
        "priority": priority,
        "locate": "pre",
    }
    if iscoroutinefunction(func):
        filt["async_function"] = func
    elif isasyncgenfunction(func):
        filt["async_function"] = func
    else:
        filt["function"] = func
    for i, pre in enumerate(__registered_filters):
        if pre["name"] == name:
            __registered_filters[i] = filt
            return
    __registered_filters.append(filt)


def register_post_filter(
    name: str,
    func: Callable | None = None,
    priority: int = 0,
) -> None:
    """
    注册/修改后置过滤器

    执行函数需返回一个元组，第一项为 BiliAPIFlags，第二项为配合 BiliAPIFlags 的值。

    所有当前函数执行的过滤器为 `ins.data[cnt]["post_filters"]`。

    Args:
        name (str): 名称，若重复则为修改对应过滤器。
        func (Callable | None, optional): 执行的函数，参数传入 `FilterArgs` 对象. Defaults to None.
        priority (int, optional): 优先级，数字越小越优先执行. Defaults to 0.
    """
    global __registered_filters
    filt = {
        "name": name,
        "priority": priority,
        "locate": "post",
    }
    if iscoroutinefunction(func):
        filt["async_function"] = func
    elif isasyncgenfunction(func):
        filt["async_function"] = func
    else:
        filt["function"] = func
    for i, post in enumerate(__registered_filters):
        if post["name"] == name:
            __registered_filters[i] = filt
            return
    __registered_filters.append(filt)


def get_registered_filters(in_priority: bool = True) -> list[dict]:
    """
    获取所有已注册的过滤器

    Args:
        in_priority (bool, optional): 是否排序. Defaults to True.

    Returns:
        list[dict]: 已注册的前置过滤器
    """
    if in_priority:

        def cmp(filt1: dict, filt2: dict) -> int:
            locate = ["pre", "post"]
            if filt1["locate"] != filt2["locate"]:
                return locate.index(filt1["locate"]) - locate.index(filt2["locate"])
            return filt1["priority"] - filt2["priority"]

        return sorted(__registered_filters, key=cmp_to_key(cmp))
    return __registered_filters


def unregister_filter(name: str) -> None:
    """
    取消注册前置过滤器

    Args:
        name (str): 过滤器名称
    """
    global __registered_filters
    for i, filt in enumerate(__registered_filters):
        if filt["name"] == name:
            del __registered_filters[i]
            return


@atexit.register
def __clean() -> None:
    """
    程序退出清理操作。
    """
    for loop in loops:
        try:
            from_thread.run(clean_session, loop, token=loop)
        except RunFinishedError:
            pass


################################################## END Session Management ##################################################


################################################## BEGIN Credential ##################################################


def _get_time_milli() -> int:
    return int(time.time() * 1000)


def _gen_b_lsid() -> str:
    return f"{random.randbytes(4).hex().upper()}_{hex(_get_time_milli())[2:].upper()}"


def _gen_uuid_infoc() -> str:
    def gen_part(x: int) -> str:
        return "".join([random.choice(mp) for _ in range(x)])

    t = _get_time_milli() % 100000
    mp = [*list("123456789ABCDEF"), "10"]
    pck = [8, 4, 4, 4, 12]

    return (
        "-".join([gen_part(length) for length in pck]) + str(t).ljust(5, "0") + "infoc"
    )


class Credential:
    """
    凭据类，用于各种请求操作的验证。

    以下字段获取方式见 https://bromothymolb.github.io/bilibili-api-zoku/#/docs/common/credential?id=获取-credential-类所需信息

    重要 cookies:
     - `SESSDATA` (`sessdata`);
     - `bili_jct`;
     - `DedeUserId` (`dedeuserid`);
     - `DedeUserId__ckMd5` (`dedeuserid_ckmd5`);
     - `sid`

    本地生成 cookies:
     - `b_nut`;
     - `b_lsid`;
     - `uuid_infoc`

    网络请求生成反爬 cookies:
     - `buvid3`;
     - `buvid4`;
     - `buvid_fp`;
     - `bili_ticket`;
     - `bili_ticket_expires`

    非 cookies:
     - `ac_time_value` (存储在 Local Storage 中)

    维护 buvid / bili_ticket 遵循以下规则：
    1. `global` 为模块初始化时定义的独一无二的凭据类。
    2. `blank` 为 `get_core_cookies` 字段全为 `None` 的凭据类，即 `Credential()`。可通过 `check_blank()` 检查凭据类是否为 `blank`。
    3. 其余凭据类均为 `normal`，即使传入 `sessdata="", bili_jct=""` 亦视为 `normal`。
    4. `get_xxx` 函数拆分为 `ensure_xxx` 和 `obtain_xxx`，接受凭据类传入。
        1. `ensure` 保证 `buvid` / `bili_ticket` 存在且可用，只有凭据类中的 `buvid` 和 `bili_ticket` 不可用才进行 `obtain`。`ensure` 在已有 cookies 情况下不会修改 cookies。
        2. `obtain` 总是发起网络请求获取新的 `buvid` / `bili_ticket`。
    5. `blank` 或在 `global_persistence` 下，凭据类进行 `ensure` 或 `obtain` 将先 `ensure global` 或 `obtain global`，再复制 `global` 相关字段，称此复制过程为同步。
    6. `get_cookies` 中直接调用 `ensure`，不会直接调用 `obtain`。在禁用 `buvid` 与 `bili_ticket` 自动获取时只同步不请求。
    7. `ensure` 与 `obtain` 若没有传入凭据类，将创建一个新的 `blank` 作为凭据类带入。因此获取 `global` 字段直接不带参调用 `ensure`，更新 `global` 字段直接不带参调用 `obtain`。
    """

    b_nut: str | None = None
    b_lsid: str | None = None
    uuid_infoc: str | None = None
    buvid_fp: str | None = None

    def __init__(
        self,
        sessdata: str | None = None,
        bili_jct: str | None = None,
        buvid3: str | None = None,
        buvid4: str | None = None,
        dedeuserid: str | None = None,
        dedeuserid_ckmd5: str | None = None,
        sid: str | None = None,
        bili_ticket: str | None = None,
        bili_ticket_expires: str | None = None,
        ac_time_value: str | None = None,
        **kwargs: Any,
    ) -> None:
        """
        各字段获取方式查看：https://bromothymolb.github.io/bilibili-api-zoku/#/docs/common/credential.md

        Args:
            sessdata (str | None, optional): 浏览器 Cookies 中的 SESSDATA 字段值. Defaults to None.
            bili_jct (str | None, optional): 浏览器 Cookies 中的 bili_jct 字段值. Defaults to None.
            buvid3 (str | None, optional): 浏览器 Cookies 中的 buvid3 字段值. Defaults to None.
            buvid4 (str | None, optional): 浏览器 Cookies 中的 buvid4 字段值. Defaults to None.
            dedeuserid (str | None, optional): 浏览器 Cookies 中的 DedeUserID 字段值. Defaults to None.
            dedeuserid_ckmd5 (str | None, optional): 浏览器 Cookies 中的 DedeUserID__ckMd5 字段值. Defaults to None.
            sid (str | None, optional): 浏览器 Cookies 中的 sid 字段值. Defaults to None.
            bili_ticket (str | None, optional): 浏览器 Cookies 中的 bili_ticket 字段值. Defaults to None.
            bili_ticket_expires (str | None, optional): 浏览器 Cookies 中的 bili_ticket_expires 字段值. Defaults to None.
            ac_time_value (str | None, optional): 浏览器 localStorage 中的 ac_time_value 字段值. Defaults to None.
            kwargs (Any): 其他用户可自行添加的 cookies。通过 **kwargs 传入。

        buvid3 和 buvid4 建议配合食用，bili_ticket 和 bili_ticket_expires 亦建议配合食用。
        """
        # core cookies
        self.sessdata = (
            None
            if sessdata is None
            else (
                sessdata if sessdata.find("%") != -1 else urllib.parse.quote(sessdata)
            )
        )
        self.bili_jct = bili_jct
        self.dedeuserid = dedeuserid
        self.dedeuserid_ckmd5 = dedeuserid_ckmd5
        self.sid = sid
        self.ac_time_value = ac_time_value

        # buvid3 & buvid4
        self.buvid3 = buvid3
        self.buvid4 = buvid4

        self._gen_local_cookies()

        # bili_ticket
        if bili_ticket_expires and not bili_ticket_expires.isnumeric():
            raise ArgsException("bili_ticket_expires 应为整数时间戳")

        self.bili_ticket = bili_ticket
        self.bili_ticket_expires = bili_ticket_expires

        # extra cookies
        self.extra_cookies = {k: str(v) for k, v in kwargs.items()}

        # locks
        self._refresh_locks = MultiEventLoopLocks()
        self._buvid_locks = MultiEventLoopLocks()
        self._bili_ticket_locks = MultiEventLoopLocks()

    def _gen_local_cookies(self) -> None:
        """
        生成部分用于 buvid 激活的本地 cookies
        """
        self.b_nut = str(int(time.time()))
        self.b_lsid = _gen_b_lsid()
        self.uuid_infoc = _gen_uuid_infoc()

    def check_blank(self) -> bool:
        """
        检查是否为空白凭据类 (`Credential()`)

        Returns:
            bool: 是否为空白凭据类
        """
        return (
            self.sessdata is None
            and self.bili_jct is None
            and self.dedeuserid is None
            and self.dedeuserid_ckmd5 is None
            and self.sid is None
            and self.ac_time_value is None
        )

    def is_buvid_generated(self) -> bool:
        """
        buvid3 / buvid4 是否已生成

        Returns:
            bool: buvid3 / buvid4 是否已生成
        """
        return bool(self.buvid3 and self.buvid4)

    def is_bili_ticket_valid(self) -> bool:
        """
        bili_ticket 是否可用

        Returns:
            bool: bili_ticket 是否可用
        """
        if self.bili_ticket_expires and not self.bili_ticket_expires.isnumeric():
            raise ArgsException("bili_ticket_expires 应为整数时间戳")
        return bool(
            self.bili_ticket
            and self.bili_ticket_expires
            and time.time() <= int(self.bili_ticket_expires)
        )

    def clear_buvid(self) -> None:
        """
        清除 buvid。若未开启全局可持久化则将生成新的 buvid，否则将与全局 buvid 同步。
        """
        self.buvid3 = None
        self.buvid4 = None

    def clear_bili_ticket(self) -> None:
        """
        清除 bili_ticket。若未开启全局可持久化则将生成新的 bili_ticket，否则将与全局 bili_ticket 同步。
        """
        self.bili_ticket = None
        self.bili_ticket_expires = None

    async def get_cookies(self) -> dict[str, str]:
        """
        获取请求 Cookies 字典，同时处理 buvid / bili_ticket。

        Returns:
            dict[str, str]: 请求 Cookies 字典
        """
        # buvid ensuring
        if bili_settings.get_enable_auto_buvid():
            await ensure_buvid(self)
        elif self.check_blank() or (
            not self.is_buvid_generated()
            and bili_settings.get_enable_buvid_global_persistence()
        ):
            _credential = get_global_credential()
            (
                self.buvid3,
                self.buvid4,
                self.buvid_fp,
                self.b_lsid,
                self.b_nut,
                self.uuid_infoc,
            ) = (
                _credential.buvid3,
                _credential.buvid4,
                _credential.buvid_fp,
                _credential.b_lsid,
                _credential.b_nut,
                _credential.uuid_infoc,
            )
        # bili_ticket ensuring
        if bili_settings.get_enable_bili_ticket():
            await ensure_bili_ticket(self)
        elif self.check_blank() or (
            not self.is_bili_ticket_valid()
            and bili_settings.get_enable_bili_ticket_global_persistence()
        ):
            _credential = get_global_credential()
            (
                self.bili_ticket,
                self.bili_ticket_expires,
            ) = (
                _credential.bili_ticket,
                _credential.bili_ticket_expires,
            )

        browser_fingerprint = get_browser_fingerprint()

        _cookies: dict[str, str | None] = {
            "buvid3": self.buvid3,
            "b_nut": self.b_nut,
            "b_lsid": self.b_lsid,
            "_uuid": self.uuid_infoc,
            "buvid4": self.buvid4,
            "bili_ticket": self.bili_ticket,
            "bili_ticket_expires": self.bili_ticket_expires,
            "buvid_fp": self.buvid_fp,
            "SESSDATA": self.sessdata,
            "bili_jct": self.bili_jct,
            "DedeUserID": self.dedeuserid,
            "DedeUserID__ckMd5": self.dedeuserid_ckmd5,
            "sid": self.sid,
            "browser_resolution": f"{browser_fingerprint['window']['innerWidth']}-{browser_fingerprint['window']['innerHeight']}",
            "opus-goback": "1",  # 确保需要旧版的时候可以跳转到旧版页面
        }

        cookies: dict[str, str] = {k: v for k, v in _cookies.items() if v is not None}
        cookies.update(self.extra_cookies)

        return cookies

    def get_core_cookies(self) -> dict[str, str | None]:
        """
        返回部分核心 cookies，需要登录获取，可用于复制 Credential 对象

        包含 SESSDATA, bili_jct, sid, DedeUserID, ac_time_value

        Returns:
            dic[str, str | None]: 核心 cookies
        """
        return {
            "SESSDATA": self.sessdata,
            "bili_jct": self.bili_jct,
            "DedeUserID": self.dedeuserid,
            "DedeUserID__ckMd5": self.dedeuserid_ckmd5,
            "sid": self.sid,
            "ac_time_value": self.ac_time_value,
        }

    def has_dedeuserid(self) -> bool:
        """
        是否提供 dedeuserid。

        Returns:
            bool: 是否提供 dedeuserid。
        """
        return self.dedeuserid is not None and self.dedeuserid != ""

    def has_sessdata(self) -> bool:
        """
        是否提供 sessdata。

        Returns:
            bool: 是否提供 sessdata。
        """
        return self.sessdata is not None and self.sessdata != ""

    def has_bili_jct(self) -> bool:
        """
        是否提供 bili_jct。

        Returns:
            bool: 是否提供 bili_jct。
        """
        return self.bili_jct is not None and self.bili_jct != ""

    def has_buvid3(self) -> bool:
        """
        是否提供 buvid3

        Returns:
            bool: 是否提供 buvid3
        """
        return self.buvid3 is not None and self.buvid3 != ""

    def has_buvid4(self) -> bool:
        """
        是否提供 buvid4

        Returns:
            bool: 是否提供 buvid4
        """
        return self.buvid4 is not None and self.buvid4 != ""

    def has_ac_time_value(self) -> bool:
        """
        是否提供 ac_time_value

        Returns:
            bool: 是否提供 ac_time_value
        """
        return self.ac_time_value is not None and self.ac_time_value != ""

    def raise_for_no_sessdata(self) -> None:
        """
        没有提供 sessdata 则抛出异常。
        """
        if not self.has_sessdata():
            raise CredentialNoSessdataException()

    def raise_for_no_bili_jct(self) -> None:
        """
        没有提供 bili_jct 则抛出异常。
        """
        if not self.has_bili_jct():
            raise CredentialNoBiliJctException()

    def raise_for_no_buvid3(self) -> None:
        """
        没有提供 buvid3 时抛出异常。
        """
        if not self.has_buvid3():
            raise CredentialNoBuvid3Exception()

    def raise_for_no_buvid4(self) -> None:
        """
        没有提供 buvid4 时抛出异常。
        """
        if not self.has_buvid4():
            raise CredentialNoBuvid4Exception()

    def raise_for_no_dedeuserid(self) -> None:
        """
        没有提供 DedeUserID 时抛出异常。
        """
        if not self.has_dedeuserid():
            raise CredentialNoDedeUserIDException()

    def raise_for_no_ac_time_value(self) -> None:
        """
        没有提供 ac_time_value 时抛出异常。
        """
        if not self.has_ac_time_value():
            raise CredentialNoAcTimeValueException()

    async def check_valid(self) -> bool:
        """
        检查 cookies 是否有效

        Returns:
            bool: cookies 是否有效
        """
        return await _check_valid(self)

    async def check_refresh(self) -> bool:
        """
        检查是否需要刷新 cookies

        Returns:
            bool: cookies 是否需要刷新
        """
        return await _check_cookies(self)

    async def refresh(self) -> None:
        """
        刷新 cookies
        """
        new_cred: Credential = await _refresh_cookies(self)
        self.sessdata = new_cred.sessdata
        self.bili_jct = new_cred.bili_jct
        self.dedeuserid = new_cred.dedeuserid
        self.dedeuserid_ckmd5 = new_cred.dedeuserid_ckmd5
        self.ac_time_value = new_cred.ac_time_value
        self.sid = new_cred.sid

    async def update(self) -> None:
        """
        判断并更新 cookies
        """
        async with self._refresh_locks.get_lock():
            if self._refresh_locks.check_multithread_state():
                if await self.check_refresh():
                    await self.refresh()
                await self._refresh_locks.done_multithread()
            else:
                await self._refresh_locks.wait_multithread()

    async def _get_buvid(self) -> None:
        # helper function for ensure_buvid
        async with self._buvid_locks.get_lock():
            if self._buvid_locks.check_multithread_state():
                if not self.is_buvid_generated():
                    await obtain_buvid(self)
                await self._buvid_locks.done_multithread()
            else:
                await self._buvid_locks.wait_multithread()

    async def _get_bili_ticket(self) -> None:
        # helper function for ensure_bili_ticket
        async with self._bili_ticket_locks.get_lock():
            if self._bili_ticket_locks.check_multithread_state():
                if not self.is_bili_ticket_valid():
                    await obtain_bili_ticket(self)
                await self._bili_ticket_locks.done_multithread()
            else:
                await self._bili_ticket_locks.wait_multithread()

    def copy(self) -> "Credential":
        """
        复制凭据类

        Returns:
            Credential: 复制后的凭据类
        """
        c = Credential()
        c.sessdata = self.sessdata
        c.bili_jct = self.bili_jct
        c.buvid3 = self.buvid3
        c.buvid4 = self.buvid4
        c.dedeuserid = self.dedeuserid
        c.dedeuserid_ckmd5 = self.dedeuserid_ckmd5
        c.ac_time_value = self.ac_time_value
        c.b_lsid = self.b_lsid
        c.b_nut = self.b_nut
        c.uuid_infoc = self.uuid_infoc
        c.bili_ticket = self.bili_ticket
        c.bili_ticket_expires = self.bili_ticket_expires
        c.buvid_fp = self.buvid_fp
        c.extra_cookies = self.extra_cookies
        return c

    @classmethod
    def from_cookies(
        cls, cookies: dict, ac_time_value: str | None = None
    ) -> "Credential":
        """
        从 cookies 新建 Credential

        Args:
            cookies (dict): Cookies.
            ac_time_value (str, optional): ac_time_value.

        Returns:
            Credential: 凭据类
        """
        c = cls(sessdata="_", bili_jct="_")
        c.sessdata = cookies.get("SESSDATA")
        c.bili_jct = cookies.get("bili_jct")
        c.buvid3 = cookies.get("buvid3")
        c.buvid4 = cookies.get("buvid4")
        c.dedeuserid = cookies.get("DedeUserID")
        c.dedeuserid_ckmd5 = cookies.get("DedeUserID__ckMd5")
        c.ac_time_value = cookies.get("ac_time_value") or ac_time_value
        c.b_lsid = cookies.get("b_lsid")
        c.b_nut = cookies.get("b_nut")
        c.uuid_infoc = cookies.get("_uuid")
        c.bili_ticket = cookies.get("bili_ticket")
        c.bili_ticket_expires = cookies.get("bili_ticket")
        c.buvid_fp = cookies.get("buvid_fp")

        for key, value in cookies.items():
            if key not in [
                "SESSDATA",
                "bili_jct",
                "buvid3",
                "buvid4",
                "DedeUserID",
                "DedeUserID__ckMd5",
                "ac_time_value",
                "b_lsid",
                "b_nut",
                "_uuid",
                "bili_ticket",
                "bili_ticket_expires",
                "buvid_fp",
            ]:
                c.extra_cookies[key] = value

        return c

    def __str__(self):
        return f"SESSDATA: {self.sessdata}; bili_jct: {self.bili_jct}; buvid3: {self.buvid3}; buvid4: {self.buvid4}; DedeUserID: {self.dedeuserid}; ac_time_value: {self.ac_time_value}"

    def __repr__(self):
        return f"Credential({self.__str__()})"


"""
Cookies 刷新相关

感谢 bilibili-API-collect 提供的刷新 Cookies 的思路

https://socialsisteryi.github.io/bilibili-API-collect/docs/login/cookie_refresh.html
"""


async def _check_valid(credential: Credential) -> bool:
    api = API["info"]["valid"]
    return (await Api(**api, credential=credential).result)["isLogin"]


async def _check_cookies(credential: Credential) -> bool:
    api = API["info"]["check_cookies"]
    return (await Api(**api, credential=credential).result)["refresh"]


def _getCorrespondPath() -> str:
    key = RSA.importKey(
        """\
-----BEGIN PUBLIC KEY-----
MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDLgd2OAkcGVtoE3ThUREbio0Eg
Uc/prcajMKXvkCKFCWhJYJcLkcM2DKKcSeFpD/j6Boy538YXnR6VhcuUJOhH2x71
nzPjfdTcqMz7djHum0qSZA0AyCBDABUqCrfNgCiJ00Ra7GmRj+YCK1NJEuewlb40
JNrRuoEUXpabUzGB8QIDAQAB
-----END PUBLIC KEY-----"""
    )
    ts = round(time.time() * 1000)
    cipher = PKCS1_OAEP.new(key, SHA256)
    encrypted = cipher.encrypt(f"refresh_{ts}".encode())
    return binascii.b2a_hex(encrypted).decode()


async def _get_refresh_csrf(credential: Credential) -> str:
    correspond_path = _getCorrespondPath()
    api = API["operate"]["get_refresh_csrf"]
    cookies = await credential.get_cookies()
    client = get_client()
    resp = await client.request(
        method="GET",
        url=api["url"].replace("{correspondPath}", correspond_path),
        cookies=cookies,
        headers=get_bili_headers(),
    )
    if resp.code == 404:
        raise CookiesRefreshException("correspondPath 过期或错误。")
    elif resp.code == 200:
        text = resp.utf8_text()
        refresh_csrf = re.findall('<div id="1-name">(.+?)</div>', text)[0]
        return refresh_csrf
    else:
        raise CookiesRefreshException("获取刷新 Cookies 的 csrf 失败。")


async def _refresh_cookies(credential: Credential) -> Credential:
    api = API["operate"]["refresh_cookies"]
    credential.raise_for_no_bili_jct()
    credential.raise_for_no_ac_time_value()
    refresh_csrf = await _get_refresh_csrf(credential)
    data = {
        "csrf": credential.bili_jct,
        "refresh_csrf": refresh_csrf,
        "refresh_token": credential.ac_time_value,
        "source": "main_web",
    }
    cookies = await credential.get_cookies()
    client = get_client()
    resp = await client.request(
        method="POST",
        url=api["url"],
        cookies=cookies,
        data=data,
        headers=get_bili_headers(),
    )
    if resp.code != 200 or resp.json()["code"] != 0:
        raise CookiesRefreshException("刷新 Cookies 失败")
    new_credential = Credential(
        sessdata=resp.cookies["SESSDATA"],
        bili_jct=resp.cookies["bili_jct"],
        dedeuserid=resp.cookies["DedeUserID"],
        dedeuserid_ckmd5=resp.cookies["DedeUserID__ckMd5"],
        sid=resp.cookies["sid"],
        ac_time_value=resp.json()["data"]["refresh_token"],
    )
    await _confirm_refresh(credential, new_credential)
    return new_credential


async def _confirm_refresh(
    old_credential: Credential, new_credential: Credential
) -> None:
    api = API["operate"]["confirm_refresh"]
    data = {
        "csrf": new_credential.bili_jct,
        "refresh_token": old_credential.ac_time_value,
    }
    await Api(**api, credential=new_credential).update_data(**data).result


################################################## END Credential ##################################################


################################################## BEGIN Anti-Spider ##################################################


OE = list(
    base64.b64decode(
        b"Li8SAjUIFyAPMgofOgMtIxsrBTEhCSoTHRwOJwwmKQ0lMAcQGDcoPRoRAAE8Mx4EFhk2FTg7Bj85PgskFCIsNA=="
    )
)
APPKEY = "4409e2ce8ffd12b8"
APPSEC = "59b43e04ad6965f34319062b478f83dd"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Referer": "https://www.bilibili.com/",
}
API = get_api("credential")

browser_fingerprint = None


def get_browser_fingerprint() -> dict:
    global browser_fingerprint
    if browser_fingerprint is None:
        if bili_settings.get_enable_fpgen():
            import fpgen

            browser_fingerprint = fpgen.generate(**bili_settings.get_fpgen_args())
        else:
            with open(
                os.path.abspath(
                    os.path.join(
                        os.path.dirname(__file__),
                        "..",
                        "data",
                        "browser_fingerprint.json",
                    )
                ),
                encoding="utf-8",
            ) as f:
                browser_fingerprint = json.load(f)
    return browser_fingerprint


def get_bili_headers(fpgen_fp: bool = True) -> dict:
    """
    获取可供访问 bilibili 链接的伪装请求头。

    部分请求头取自 fpgen 生成的浏览器指纹信息。

    Args:
        fpgen_fp (bool, optional): 是否使用 fpgen 生成的浏览器指纹信息. Defaults to True.

    Returns:
        dict: 请求头
    """
    fp = get_browser_fingerprint()
    headers = HEADERS.copy()
    if fpgen_fp:
        for k, v in fp["headers"].items():
            if v:
                headers[k.title()] = v[0] if v and isinstance(v, list) else str(v)
    return headers


async def _get_spi_buvid() -> tuple[dict, str]:
    api = API["info"]["spi"]
    client = get_client()
    response = await client.request(
        method="GET",
        url=api["url"],
        headers=get_bili_headers(),
    )
    date = response.headers.get("date", None)
    if not date:
        date = response.headers["Date"]
    return (
        (response).json()["data"],
        str(int(parsedate_to_datetime(date).timestamp())),
    )


"""
思路来源：https://github.com/SocialSisterYi/bilibili-API-collect/issues/933
"""


class _CookieJsonDecoder(json.JSONDecoder):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parse_string = self.cookie_scanstring
        self.scan_once = scanner.py_make_scanner(self)  # pyright: ignore[reportAttributeAccessIssue]

    @staticmethod
    def cookie_scanstring(*args, **kwargs):
        (val, end) = scanstring(*args, **kwargs)

        if val.startswith("getCookie"):
            match = re.match(r"getCookie\('([^']*)'\)", val)
            if match:
                _cookie_name = match.group(1)
                return (None, end)

        return (val, end)


async def _gen_buvid_fp(
    buvid3: str, buvid4: str, credential: Credential
) -> tuple[str, str]:
    MOD = 1 << 64

    def rotate_left(x: int, k: int) -> int:
        bin_str = bin(x)[2:].rjust(64, "0")
        return int(bin_str[k:] + bin_str[:k], base=2)

    def gen_buvid_fp(key: str, seed: int):
        source = io.BytesIO(bytes(key, "utf-8"))
        m = murmur3_x64_128(source, seed)
        return f"{hex(m & (MOD - 1))[2:]}{hex(m >> 64)[2:]}"

    def murmur3_x64_128(source: io.BufferedIOBase, seed: int) -> int:
        C1 = 0x87C3_7B91_1142_53D5
        C2 = 0x4CF5_AD43_2745_937F
        C3 = 0x52DC_E729
        C4 = 0x3849_5AB5
        R1, R2, R3, M = 27, 31, 33, 5
        h1, h2 = seed, seed
        processed = 0
        while True:
            read = source.read(16)
            processed += len(read)
            if len(read) == 16:
                k1 = struct.unpack("<q", read[:8])[0]
                k2 = struct.unpack("<q", read[8:])[0]
                h1 ^= rotate_left(k1 * C1 % MOD, R2) * C2 % MOD
                h1 = ((rotate_left(h1, R1) + h2) * M + C3) % MOD
                h2 ^= rotate_left(k2 * C2 % MOD, R3) * C1 % MOD
                h2 = ((rotate_left(h2, R2) + h1) * M + C4) % MOD
            elif len(read) == 0:
                h1 ^= processed
                h2 ^= processed
                h1 = (h1 + h2) % MOD
                h2 = (h2 + h1) % MOD
                h1 = fmix64(h1)
                h2 = fmix64(h2)
                h1 = (h1 + h2) % MOD
                h2 = (h2 + h1) % MOD
                return (h2 << 64) | h1
            else:
                k1 = 0
                k2 = 0
                if len(read) >= 15:
                    k2 ^= int(read[14]) << 48
                if len(read) >= 14:
                    k2 ^= int(read[13]) << 40
                if len(read) >= 13:
                    k2 ^= int(read[12]) << 32
                if len(read) >= 12:
                    k2 ^= int(read[11]) << 24
                if len(read) >= 11:
                    k2 ^= int(read[10]) << 16
                if len(read) >= 10:
                    k2 ^= int(read[9]) << 8
                if len(read) >= 9:
                    k2 ^= int(read[8])
                    k2 = rotate_left(k2 * C2 % MOD, R3) * C1 % MOD
                    h2 ^= k2
                if len(read) >= 8:
                    k1 ^= int(read[7]) << 56
                if len(read) >= 7:
                    k1 ^= int(read[6]) << 48
                if len(read) >= 6:
                    k1 ^= int(read[5]) << 40
                if len(read) >= 5:
                    k1 ^= int(read[4]) << 32
                if len(read) >= 4:
                    k1 ^= int(read[3]) << 24
                if len(read) >= 3:
                    k1 ^= int(read[2]) << 16
                if len(read) >= 2:
                    k1 ^= int(read[1]) << 8
                if len(read) >= 1:
                    k1 ^= int(read[0])
                k1 = rotate_left(k1 * C1 % MOD, R2) * C2 % MOD
                h1 ^= k1

    def fmix64(k: int) -> int:
        C1 = 0xFF51_AFD7_ED55_8CCD
        C2 = 0xC4CE_B9FE_1A85_EC53
        R = 33
        tmp = k
        tmp ^= tmp >> R
        tmp = tmp * C1 % MOD
        tmp ^= tmp >> R
        tmp = tmp * C2 % MOD
        tmp ^= tmp >> R
        return tmp

    def get_payload(uuid: str, homepage_html: str) -> str:
        def extract_abtest_dict(html: str) -> dict[str, Any]:
            soup = BeautifulSoup(html, "html.parser")
            scripts = soup.find_all("script")

            for script in scripts:
                js_code = script.string
                if not js_code or "window.abtest" not in js_code:
                    continue

                # Isolate the JavaScript object string using a regular expression.
                # This looks for 'window.abtest = {' and captures everything until the matching '};'
                match = re.search(r"window\.abtest\s*=\s*({.*?})\n", js_code, re.DOTALL)
                if not match:
                    continue

                js_object_string = match.group(1)

                try:
                    return chompjs.parse_js_object(
                        js_object_string, loader_kwargs={"cls": _CookieJsonDecoder}
                    )
                except Exception as e:
                    print(f"Error parsing JavaScript object: {e}")
                    return {}

            return {}

        browser_fingerprint = get_browser_fingerprint()
        plugins = browser_fingerprint["plugins"]
        mime_type_suffix: dict[str, str] | None = (
            {
                mime_type["type"]: mime_type["suffixes"]
                for mime_type in browser_fingerprint["plugins"]["mimeTypes"]
            }
            if plugins
            else None
        )

        def get_param(param_id: int) -> str | int | bool:
            param = browser_fingerprint["webgl"]["params"].get(str(param_id))
            return param["value"] if param["value"] is not None else "null"

        a3c1 = [
            f"extensions:{';'.join(browser_fingerprint['webgl']['supportedExtensions'])}",
            f"webgl aliased line width range:{(get_param(33902))}",
            f"webgl aliased point size range:{get_param(33901)}",
            f"webgl alpha bits:{get_param(3413)}",
            f"webgl antialiasing:{'yes' if browser_fingerprint['webgl']['contextAttributes']['antialias'] else 'no'}",
            f"webgl blue bits:{get_param(3412)}",
            f"webgl depth bits:{get_param(3414)}",
            f"webgl green bits:{get_param(3411)}",
            f"webgl max anisotropy:{get_param(34047)}",
            f"webgl max combined texture image units:{get_param(35661)}",
            f"webgl max cube map texture size:{get_param(34076)}",
            f"webgl max fragment uniform vectors:{get_param(36349)}",
            f"webgl max render buffer size:{get_param(34024)}",
            f"webgl max texture image units:{get_param(34930)}",
            f"webgl max texture size:{get_param(3379)}",
            f"webgl max varying vectors:{get_param(36348)}",
            f"webgl max vertex attribs:{get_param(34921)}",
            f"webgl max vertex texture image units:{get_param(35660)}",
            f"webgl max vertex uniform vectors:{get_param(36347)}",
            f"webgl max viewport dims:{get_param(3386)}",
            f"webgl red bits:{get_param(3410)}",
            f"webgl renderer:{get_param(7937)}",
            f"webgl shading language version:{get_param(35724)}",
            f"webgl stencil bits:{get_param(3415)}",
            f"webgl vendor:{get_param(7936)}",
            f"webgl version:{get_param(7938)}",
        ]

        if (
            "WEBGL_debug_renderer_info"
            in browser_fingerprint["webgl"]["supportedExtensions"]
        ):
            a3c1.append(f"webgl unmasked vendor:{browser_fingerprint['gpu']['vendor']}")
            a3c1.append(
                f"webgl unmasked renderer:{browser_fingerprint['gpu']['renderer']}"
            )

        shader_precisions = browser_fingerprint["webgl"]["shaderPrecisionFormats"]
        numerics = ["FLOAT", "INT"]
        shader_map = {"VERTEX": 35633, "FRAGMENT": 35632}
        precisions = ["HIGH", "MEDIUM", "LOW"]
        precision_map = {
            "HIGH_FLOAT": 36338,
            "MEDIUM_FLOAT": 36337,
            "LOW_FLOAT": 36336,
            "HIGH_INT": 36341,
            "MEDIUM_INT": 36340,
            "LOW_INT": 36339,
        }

        for ntype_k in numerics:
            for stype_k, stype_v in shader_map.items():
                for ptype_k in precisions:
                    precision_type = f"{ptype_k}_{ntype_k}"
                    precision_data = next(
                        format
                        for format in shader_precisions
                        if format["precisionType"] == precision_map[precision_type]
                        and format["shaderType"] == stype_v
                    )
                    for prop in ["precision", "rangeMin", "rangeMax"]:
                        value = precision_data["r"][prop]
                        prop_name = prop
                        if prop != "precision":
                            prop_name = f"precision {prop}"
                        a3c1.append(
                            f"webgl {stype_k.lower()} shader {ptype_k.lower()} {ntype_k.lower()} {prop_name}:{value}"
                        )

        png_suffix = bytes.fromhex("0000000049454E44AE426082")

        content = {
            "3064": 1,
            "5062": str(_get_time_milli()),
            "03bf": "https%3A%2F%2Fwww.bilibili.com%2F",
            "39c8": "333.1007.fp.risk",
            "34f1": "",
            "d402": "",
            "654a": "",
            "6e7c": f"{browser_fingerprint['window']['innerWidth']}x{browser_fingerprint['window']['innerHeight']}",
            "3c43": {
                "2673": 0,
                "5766": browser_fingerprint["screen"]["colorDepth"],
                "6527": 0,
                "7003": 1,
                "807e": 1,
                "b8ce": browser_fingerprint["navigator"]["userAgent"],
                "641c": 0,
                "07a4": browser_fingerprint["intl"]["locale"],
                "1c57": browser_fingerprint["navigator"]["deviceMemory"],
                "0bd0": browser_fingerprint["navigator"]["hardwareConcurrency"],
                "748e": [
                    browser_fingerprint["screen"]["width"],
                    browser_fingerprint["screen"]["height"],
                ],
                "d61f": [
                    browser_fingerprint["screen"]["width"],
                    browser_fingerprint["screen"]["height"],
                ],
                "fc9d": -480,
                "6aa9": "Asia/Shanghai",
                "75b8": 1,
                "3b21": 1,
                "8a1c": 0,
                "d52f": "not available",
                "adca": browser_fingerprint["navigator"]["platform"],
                "80c9": (
                    [
                        [
                            plugin["name"],
                            plugin["description"],
                            [
                                [mime_type, mime_type_suffix.get(mime_type, "")]
                                for mime_type in plugin["__mimeTypes"]
                            ],
                        ]
                        for plugin in plugins["plugins"]
                    ]
                    if mime_type_suffix
                    else "not available"
                ),
                "13ab": base64.b64encode(
                    random.randbytes(random.randrange(15, 20)) + png_suffix
                ).decode(encoding="ascii")[:-20],
                "bfe9": base64.b64encode(
                    random.randbytes(random.randrange(40, 50)) + png_suffix
                ).decode(encoding="ascii")[:-50],
                "a3c1": a3c1,
                "6bc5": f"{browser_fingerprint['gpu']['vendor']}~{browser_fingerprint['gpu']['renderer']}",
                "ed31": 0,
                "72bd": 0,
                "097b": 0,
                "52cd": [0, 0, 0],
                "a658": browser_fingerprint["allFonts"],
                "d02f": str(124.043475 + random.random() / 1e6),
            },
            "54ef": json.dumps(
                extract_abtest_dict(homepage_html),
                ensure_ascii=False,
                allow_nan=False,
                separators=(",", ":"),
            ),
            "8b94": "https%3A%2F%2Fwww.bilibili.com%2F",
            "df35": uuid,
            "07a4": browser_fingerprint["intl"]["locale"],
            "5f45": None,
            "db46": 0,
        }
        return json.dumps(
            {"payload": json.dumps(content, ensure_ascii=False, separators=(",", ":"))},
            ensure_ascii=False,
            separators=(",", ":"),
        )

    client = get_client()
    headers = get_bili_headers()
    homepage_html = await client.request(
        method="GET",
        url="https://www.bilibili.com",
        headers=headers,
        cookies={
            "buvid3": buvid3,
            "buvid4": buvid4,
            "b_nut": credential.b_nut,
            "b_lsid": credential.b_lsid,
            "_uuid": credential.uuid_infoc,
        },
    )
    payload = get_payload(credential.uuid_infoc, homepage_html.utf8_text())  # type: ignore
    return gen_buvid_fp(payload, 31), payload


async def _active_buvid(
    buvid3: str, buvid4: str, buvid_fp: str, payload: str, credential: Credential
) -> None:
    api = API["operate"]["active"]
    client = get_client()
    headers = get_bili_headers()
    headers["Content-Type"] = "application/json"
    resp = await client.request(
        method="POST",
        url=api["url"],
        data=payload,
        headers=headers,
        cookies={
            "buvid3": buvid3,
            "buvid4": buvid4,
            "buvid_fp": buvid_fp,
            "b_nut": credential.b_nut,
            "b_lsid": credential.b_lsid,
            "_uuid": credential.uuid_infoc,
        },
    )
    data = resp.json()
    if data["code"] != 0:
        raise ExClimbWuzhiException(data["code"], data["message"])


async def _get_nav(credential: Credential | None = None) -> dict:
    credential = credential or Credential()
    api = API["info"]["valid"]
    client = get_client()
    return (
        await client.request(
            method="GET",
            url=api["url"],
            headers=get_bili_headers(),
            cookies=await credential.get_cookies(),
        )
    ).json()["data"]


async def _get_mixin_key(credential: Credential | None = None) -> str:
    data = await _get_nav(credential=credential)
    wbi_img: dict[str, str] = data["wbi_img"]

    def split(key):
        return wbi_img.get(key).split("/")[-1].split(".")[0]  # type: ignore

    ae = split("img_url") + split("sub_url")
    le = reduce(lambda s, i: s + (ae[i] if i < len(ae) else ""), OE, "")
    return le[:32]


def _enc_wbi(params: dict, mixin_key: str) -> dict:
    params.pop("w_rid", None)  # 重试时先把原有 w_rid 去除
    params.pop("wts", None)
    params["wts"] = round(time.time())
    # web_location 没被列入参数可能炸一些接口 比如 video.get_ai_conclusion
    Ae = urllib.parse.urlencode(sorted(params.items()))
    params["w_rid"] = hashlib.md5((Ae + mixin_key).encode(encoding="utf-8")).hexdigest()
    return params


def _enc_dm(params: dict) -> dict:
    def encode_to_base64_substring(raw: str) -> str:
        encoded_bytes = base64.b64encode(raw.encode())
        encoded_string = encoded_bytes.decode("ascii")
        return encoded_string[:-2]

    def get_wh(width: int, height: int) -> list[int]:
        rnd = random.randrange(114)
        return [2 * width + 2 * height + 3 * rnd, 4 * width - height + rnd, rnd]

    def get_of(scroll_top: int, scroll_left: int) -> list[int]:
        rnd = random.randrange(514)
        return [
            3 * scroll_top + 2 * scroll_left + rnd,
            4 * scroll_top - 4 * scroll_left + 2 * rnd,
            rnd,
        ]

    browser_fingerprint = get_browser_fingerprint()
    wh_str = ",".join(
        str(value)
        for value in get_wh(
            browser_fingerprint["window"]["innerWidth"],
            browser_fingerprint["window"]["innerHeight"],
        )
    )
    of_str = ",".join(
        str(value)
        for value in get_of(
            browser_fingerprint["window"]["pageYOffset"],
            0,
        )
    )
    params.update(
        {
            "dm_img_list": "[]",  # 鼠标/键盘操作记录
            "dm_img_str": encode_to_base64_substring(
                browser_fingerprint["webgl"]["params"]["7938"]["value"]
            ),
            "dm_cover_img_str": encode_to_base64_substring(
                browser_fingerprint["gpu"]["renderer"]
            ),
            "dm_img_inter": f'{{"ds":[],"wh":[{wh_str}],"of":[{of_str}]}}',
        }
    )
    return params


def _enc_sign(paramsordata: dict) -> dict:
    paramsordata["appkey"] = APPKEY
    paramsordata = dict(sorted(paramsordata.items()))
    paramsordata["sign"] = hashlib.md5(
        (urllib.parse.urlencode(paramsordata) + APPSEC).encode("utf-8")
    ).hexdigest()
    return paramsordata


"""
算法来源：https://github.com/SocialSisterYi/bilibili-API-collect/issues/903
"""


async def _get_bili_ticket(credential: Credential) -> tuple[str, int]:
    def hmac_sha256(key: str, message: str) -> str:
        hmac_obj = hmac.new(
            key.encode("utf-8"), message.encode("utf-8"), hashlib.sha256
        )
        return hmac_obj.digest().hex()

    ts = int(time.time())
    o = hmac_sha256("XgwSnGZ1p", f"ts{ts}")
    api = API["info"]["ticket"]
    params = {
        "key_id": "ec02",
        "hexsign": o,
        "context[ts]": f"{ts}",
        "csrf": credential.bili_jct or "",
    }
    client = get_client()
    resp = (
        await client.request(
            method="POST",
            url=api["url"],
            params=params,
            headers=get_bili_headers(),
            cookies={
                "buvid3": credential.buvid3,
                "b_nut": credential.b_nut,
                "b_lsid": credential.b_lsid,
                "_uuid": credential.uuid_infoc,
                "buvid4": credential.buvid4,
            },
        )
    ).json()
    if resp["code"] != 0:
        raise ResponseCodeException(
            resp["code"], resp.get("message", "获取 bili_ticket 失败。")
        )
    return (resp["data"]["ticket"], resp["data"]["created_at"] + resp["data"]["ttl"])


################################################## END Anti-Spider ##################################################


################################################## BEGIN Builtin-Filters ##################################################


def __register_builtin_log_filters():
    def log_pre(args: BiliFilterArgs):
        running_info = {
            "act_id": args.filter_cnt,
            "client": args.client,
            "instance": args.instance,
            "event_loop": args.event_loop_token,
        }
        match args.func:
            case "request":
                request_log.dispatch(
                    "REQUEST",
                    "发起请求",
                    args.params | running_info,
                )
            case "ws_send":
                request_log.dispatch(
                    "WS_SEND",
                    "发送 WebSocket 请求",
                    {"id": args.params["cnt"], "data": args.params["data"]}
                    | running_info,
                )
            case "ws_close":
                request_log.dispatch(
                    "WS_CLOSE",
                    "关闭 WebSocket 请求",
                    {"id": args.params["cnt"]} | running_info,
                )
            case "download_close":
                request_log.dispatch(
                    "DWN_CLOSE",
                    "结束下载",
                    {"id": args.params["cnt"]} | running_info,
                )
            case "close":
                request_log.dispatch(
                    "CLOSE",
                    "关闭会话",
                    running_info,
                )
        return BiliFilterReturn.continue_exec()

    def log_post(args: BiliFilterArgs):
        running_info = {
            "act_id": args.filter_cnt,
            "client": args.client,
            "instance": args.instance,
            "event_loop": args.event_loop_token,
        }
        match args.func:
            case "request":
                request_log.dispatch(
                    "RESPONSE",
                    "获得响应",
                    {
                        "code": args.ret.code,
                        "headers": args.ret.headers,
                        "cookies": args.ret.cookies,
                        "data": args.ret.raw,
                        "url": args.ret.url,
                    }
                    | running_info,
                )
            case "ws_create":
                args.params["id"] = args.ret
                request_log.dispatch(
                    "WS_CREATE",
                    "开始 WebSocket 连接",
                    args.params | running_info,
                )
            case "download_create":
                args.params["id"] = args.ret
                request_log.dispatch(
                    "DWN_CREATE",
                    "开始下载",
                    args.params | running_info,
                )
            case "download_chunk":
                request_log.dispatch(
                    "DWN_PART",
                    "收到部分下载数据",
                    {"id": args.params["cnt"], "data": args.ret} | running_info,
                )
            case "ws_recv":
                request_log.dispatch(
                    "WS_RECV",
                    "收到 WebSocket 数据",
                    {
                        "id": args.params["cnt"],
                        "data": args.ret[0],
                        "flags": args.ret[1].value,
                    }
                    | running_info,
                )
        return BiliFilterReturn.continue_exec()

    register_pre_filter(name="__builtin_log_pre", func=log_pre, priority=998244353)
    register_post_filter(name="__builtin_log_post", func=log_post, priority=-998244353)


__register_builtin_log_filters()


################################################## END Builtin-Filters ##################################################


################################################## BEGIN Credential-AntiSpider ##################################################

# Credential 维护 buvid / bili_ticket 遵循以下规则：
# 1. `global` 为模块初始化时定义的独一无二的凭据类。
# 2. `blank` 为 `get_core_cookies` 字段全为 `None` 的凭据类，即 `Credential()`。可通过 `check_blank()` 检查凭据类是否为 `blank`。
# 3. 其余凭据类均为 `normal`，即使传入 `sessdata="", bili_jct=""` 亦视为 `normal`。
# 4. `get_xxx` 函数拆分为 `ensure_xxx` 和 `obtain_xxx`，接受凭据类传入。
#     1. `ensure` 保证 `buvid` / `bili_ticket` 存在且可用，只有凭据类中的 `buvid` 和 `bili_ticket` 不可用才进行 `obtain`。`ensure` 在已有 cookies 情况下不会修改 cookies。
#     2. `obtain` 总是发起网络请求获取新的 `buvid` / `bili_ticket`。
# 5. `blank` 或在 `global_persistence` 下，凭据类进行 `ensure` 或 `obtain` 将先 `ensure global` 或 `obtain global`，再复制 `global` 相关字段，称此复制过程为同步。
# 6. `get_cookies` 中直接调用 `ensure`，不会直接调用 `obtain`。在禁用 `buvid` 与 `bili_ticket` 自动获取时只同步不请求。
# 7. `ensure` 与 `obtain` 若没有传入凭据类，将创建一个新的 `blank` 作为凭据类带入。因此获取 `global` 字段直接不带参调用 `ensure`，更新 `global` 字段直接不带参调用 `obtain`。


class GlobalCredential(Credential):
    """
    全局凭据类，用于储存全局使用的反爬虫字段
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


global_credential = GlobalCredential(
    sessdata="ujimatsu", bili_jct="chiya", dedeuserid="919"
)


def get_global_credential() -> GlobalCredential:
    """
    返回 `global` 凭据类，以供 `blank` 凭据类获取反爬 cookies

    此函数与 bili_settings.get_global_credential() 无关

    Returns:
        GlobalCredential: _description_
    """
    return global_credential


async def ensure_buvid(credential: Credential | None = None) -> tuple[str, str, str]:
    """
    确认凭据类的 buvid3 与 buvid4，若未提供则生成新 buvid3 与 buvid4 并设置相关字段。

    若不提供凭据类则将返回全局生成的 buvid3 与 buvid4。

    Args:
        credential (Credential | None, optional): 凭据类. Defaults to None.

    Returns:
        tuple[str, str, str]: 第 0 项为 buvid3，第 1 项为 buvid4，第 2 项为 buvid_fp。
    """
    credential = credential or Credential()

    if credential.is_buvid_generated():
        return (credential.buvid3, credential.buvid4, credential.buvid_fp)  # type: ignore

    if credential.check_blank() or (
        bili_settings.get_enable_buvid_global_persistence()
        and not isinstance(credential, GlobalCredential)
    ):
        _credential = get_global_credential()
        await ensure_buvid(_credential)
        (
            credential.buvid3,
            credential.buvid4,
            credential.buvid_fp,
            credential.b_lsid,
            credential.b_nut,
            credential.uuid_infoc,
        ) = (
            _credential.buvid3,
            _credential.buvid4,
            _credential.buvid_fp,
            _credential.b_lsid,
            _credential.b_nut,
            _credential.uuid_infoc,
        )
        return (credential.buvid3, credential.buvid4, credential.buvid_fp)  # type: ignore

    await credential._get_buvid()

    return (credential.buvid3, credential.buvid4, credential.buvid_fp)  # type: ignore


async def obtain_buvid(credential: Credential | None = None) -> tuple[str, str, str]:
    """
    获取新的 buvid3 与 buvid4，若已有 buvid3 或 buvid4 则将覆盖原来的值。

    若不提供凭据类则将刷新全局 buvid3 与 buvid4 并返回。

    Args:
        credential (Credential | None, optional): 凭据类. Defaults to None.

    Returns:
        tuple[str, str, str]: 第 0 项为 buvid3，第 1 项为 buvid4，第 2 项为 buvid_fp。
    """
    credential = credential or Credential()

    if credential.check_blank() or (
        bili_settings.get_enable_buvid_global_persistence()
        and not isinstance(credential, GlobalCredential)
    ):
        _credential = get_global_credential()
        await obtain_buvid(_credential)
        (
            credential.buvid3,
            credential.buvid4,
            credential.buvid_fp,
            credential.b_lsid,
            credential.b_nut,
            credential.uuid_infoc,
        ) = (
            _credential.buvid3,
            _credential.buvid4,
            _credential.buvid_fp,
            _credential.b_lsid,
            _credential.b_nut,
            _credential.uuid_infoc,
        )
        return (credential.buvid3, credential.buvid4, credential.buvid_fp)  # type: ignore

    credential._gen_local_cookies()
    spi, b_nut = await _get_spi_buvid()
    credential.b_nut = b_nut
    credential.buvid3 = spi["b_3"]
    credential.buvid4 = spi["b_4"]
    credential.buvid_fp, payload = await _gen_buvid_fp(
        credential.buvid3, credential.buvid4, credential
    )
    await _active_buvid(
        credential.buvid3,
        credential.buvid4,
        credential.buvid_fp,
        payload,
        credential,
    )
    request_log.dispatch(
        "ANTI_SPIDER",
        "反爬虫",
        {
            "msg": f"激活 buvid3 / buvid4 成功: 3 [{credential.buvid3}] 4 [{credential.buvid4}] fp [{credential.buvid_fp}]"
        },
    )
    return (credential.buvid3, credential.buvid4, credential.buvid_fp)  # type: ignore


async def ensure_bili_ticket(
    credential: Credential | None = None,
) -> tuple[str, str]:
    """
    确保 bili_ticket 可用，自动刷新 bili_ticket，若提供凭据类将自动在 credential 中设置相关字段。

    若不提供凭据类则将返回全局生成的 bili_ticket。

    Args:
        credential (Credential | None, optional): 凭据. Defaults to None.

    Returns:
        tuple[str, str]: bili_ticket, bili_ticket_expires
    """
    credential = credential or Credential()

    if credential.is_bili_ticket_valid():
        return credential.bili_ticket, credential.bili_ticket_expires  # type: ignore

    if credential.check_blank() or (
        bili_settings.get_enable_bili_ticket_global_persistence()
        and not isinstance(credential, GlobalCredential)
    ):
        _credential = get_global_credential()
        await ensure_bili_ticket(_credential)
        (
            credential.bili_ticket,
            credential.bili_ticket_expires,
        ) = (
            _credential.bili_ticket,
            _credential.bili_ticket_expires,
        )
        return credential.bili_ticket, credential.bili_ticket_expires  # type: ignore

    await credential._get_bili_ticket()

    return credential.bili_ticket, credential.bili_ticket_expires  # type: ignore


async def obtain_bili_ticket(
    credential: Credential | None = None,
) -> tuple[str, str]:
    """
    获取新的 bili_ticket，若已有将覆盖原有的 bili_ticket，若提供凭据类将自动在 credential 中设置相关字段。

    若不提供凭据类则将刷新全局 bili_ticket 并返回。

    Args:
        credential (Credential | None, optional): 凭据. Defaults to None.

    Returns:
        tuple[str, str]: bili_ticket, bili_ticket_expires
    """
    credential = credential or Credential()

    if credential.check_blank() or (
        bili_settings.get_enable_bili_ticket_global_persistence()
        and not isinstance(credential, GlobalCredential)
    ):
        _credential = get_global_credential()
        await obtain_bili_ticket(_credential)
        (
            credential.bili_ticket,
            credential.bili_ticket_expires,
        ) = (
            _credential.bili_ticket,
            _credential.bili_ticket_expires,
        )
        return credential.bili_ticket, credential.bili_ticket_expires  # type: ignore

    resp = await _get_bili_ticket(credential)
    credential.bili_ticket, credential.bili_ticket_expires = resp[0], str(resp[1])
    request_log.dispatch(
        "ANTI_SPIDER",
        "反爬虫",
        {
            "msg": f"获取 bili_ticket 成功: [{credential.bili_ticket}] expires [{credential.bili_ticket_expires}]"
        },
    )
    return credential.bili_ticket, credential.bili_ticket_expires


################################################## END Credential-AntiSpider ##################################################


################################################## BEGIN Api ##################################################


__wbi_mixin_key: str | None = None


def recalculate_wbi() -> None:
    """
    重新计算 wbi 的参数
    """
    global __wbi_mixin_key
    __wbi_mixin_key = None


async def get_wbi_mixin_key(credential: Credential | None = None) -> str:
    """
    获取 wbi mixin key

    Args:
        credential (Credential, optional): 凭据. Defaults to None.

    Returns:
        str: wbi mixin key
    """
    global __wbi_mixin_key
    if __wbi_mixin_key is None:
        __wbi_mixin_key = await _get_mixin_key(credential)
        request_log.dispatch(
            "ANTI_SPIDER",
            "反爬虫",
            {"msg": f"获取 wbi mixin key: [{__wbi_mixin_key}]"},
        )
    return __wbi_mixin_key


@dataclass
class Api:
    """
    用于请求的 Api 类，几乎所有 http 请求皆由此发出。

    Args:
        url (str): 请求地址

        method (str): 请求方法

        comment (str, optional): 注释. Defaults to "".

        wbi (bool, optional): 是否使用 wbi 鉴权 (`w_rid` / `wts`). Defaults to False.

        dm (bool, optional): 是否使用参数进一步的 wbi 鉴权 (`dm_xxx`)，有关鼠标/键盘操作记录. Defaults to False.

        verify (bool, optional): 是否验证凭据. Defaults to False.

        no_csrf (bool, optional): 是否不使用 csrf. Defaults to False.

        json_body (bool, optional): 是否使用 json 作为载荷. Defaults to False.

        ignore_code (bool, optional): 是否忽略返回值 code 的检验. Defaults to False.

        sign (bool, optional): 是否使用 APP 鉴权. Defaults to False.

        data (dict, optional): 请求载荷. Defaults to {}.

        params (dict, optional): 请求参数. Defaults to {}.

        files (dict[str, BiliAPIFile], optional): 附带文件. Defaults to {}.

        headers (dict, optional): 自定义的请求头. Defaults to {}.

        credential (Credential, optional): 凭据. Defaults to Credential().
    """

    url: str
    method: str
    comment: str = ""
    wbi: bool = False
    dm: bool = False
    verify: bool = False
    no_csrf: bool = False
    json_body: bool = False
    ignore_code: bool = False
    sign: bool = False
    data: dict = field(default_factory=dict)
    params: dict = field(default_factory=dict)
    files: dict[str, BiliAPIFile] = field(default_factory=dict)
    headers: dict = field(default_factory=dict)
    credential: Credential = field(default_factory=Credential)

    def __post_init__(self) -> None:
        self.method = self.method.upper()
        self.original_data = self.data.copy()
        self.original_params = self.params.copy()
        self.data = dict.fromkeys(self.data.keys(), "")
        self.params = dict.fromkeys(self.params.keys(), "")
        self.files = dict.fromkeys(
            self.files.keys(), BiliAPIFile(name="", content=b"", mime_type="")
        )
        self.headers = dict.fromkeys(self.headers.keys(), "")
        self.credential = self.credential or Credential()

    def update_data(self, **kwargs) -> "Api":
        """
        更新 data

        Returns:
            Api: 返回自身
        """
        self.data = kwargs
        return self

    def update_params(self, **kwargs) -> "Api":
        """
        更新 params

        Returns:
            Api: 返回自身
        """
        self.params = kwargs
        return self

    def update_files(self, **kwargs) -> "Api":
        """
        更新 files

        Returns:
            Api: 返回自身
        """
        self.files = kwargs
        return self

    def update_headers(self, **kwargs) -> "Api":
        """
        更新 headers

        Returns:
            Api: 返回自身
        """
        self.headers = kwargs
        return self

    async def _prepare_request(self) -> dict:
        # 处理 bool
        new_params, new_data = {}, {}
        for key, value in self.params.items():
            if isinstance(value, bool):
                new_params[key] = int(value)
            elif value is not None:
                new_params[key] = value
        for key, value in self.data.items():
            if isinstance(value, bool):
                new_params[key] = int(value)
            elif value is not None:
                new_data[key] = value
        self.params, self.data = new_params, new_data
        # 如果接口需要 Credential 且未传入 sessdata 鉴权则报错
        if self.verify:
            self.credential.raise_for_no_sessdata()
        # 请求为非 GET 且 no_csrf 不为 True 时要求 bili_jct
        if self.method != "GET" and not self.no_csrf:
            self.credential.raise_for_no_bili_jct()
        # jsonp
        if self.params.get("jsonp") == "jsonp":
            self.params["callback"] = "callback"
        # 鼠标移动 wbi 风控 (这东西不放在前面工作不了)
        # (https://github.com/Nemo2011/bilibili-api/issues/595)
        if self.dm:
            self.params = _enc_dm(self.params)
        # 普遍存在的 wbi 鉴权
        if self.wbi:
            self.params = _enc_wbi(
                self.params, await get_wbi_mixin_key(self.credential)
            )
        # 自动添加 csrf
        if (
            not self.no_csrf
            and self.verify
            and self.method in ["POST", "DELETE", "PATCH"]
        ) and isinstance(self.data, dict):
            self.data["csrf"] = self.credential.bili_jct
            self.data["csrf_token"] = self.credential.bili_jct
        # 处理 cookies
        cookies = await self.credential.get_cookies()
        # APP 鉴权
        if self.sign:
            if self.method in ["POST", "DELETE", "PATCH"]:
                self.data = _enc_sign(self.data)
            else:
                self.params = _enc_sign(self.params)
        # 初步 params
        config = {
            "method": self.method,
            "url": self.url,
            "params": self.params,
            "data": self.data,
            "files": self.files,
            "cookies": cookies,
            "headers": get_bili_headers() | self.headers,
        }
        # json_body
        if self.json_body:
            config["headers"]["Content-Type"] = "application/json"
            config["data"] = json.dumps(config["data"], ensure_ascii=False)

        return config

    def _process_response(
        self, resp: BiliAPIResponse, raw: bool = False
    ) -> int | str | dict | None:
        # 检查状态码
        if resp.code != 200:
            raise NetworkException(resp.code, resp.utf8_text())
        # 检查响应头 Content-Length
        content_length = resp.headers.get("content-length")
        if content_length and int(content_length) == 0:
            return None
        # 提取 json
        resp_text = resp.utf8_text()
        if "callback" in self.params:
            # JSONP 请求
            resp_data: dict = json.loads(
                re.match("^.*?({.*}).*$", resp_text, re.DOTALL).group(1)  # type: ignore
            )
        else:
            # JSON
            resp_data: dict = json.loads(resp_text)
        if raw:
            return resp_data
        # 检查状态
        OK = resp_data.get("OK")
        if not self.ignore_code:
            if OK is None:
                code = resp_data.get("code")
                if code is None:
                    raise ResponseCodeException(
                        -1, "API 返回数据未含 code 字段", resp_data
                    )
                if code != 0:
                    msg = resp_data.get("msg")
                    if msg is None:
                        msg = resp_data.get("message")
                    if msg is None:
                        msg = "接口未返回错误信息"
                    raise ResponseCodeException(code, msg, resp_data)
            elif OK != 1:
                raise ResponseCodeException(-1, "API 返回数据 OK 不为 1", resp_data)
        # 自动提取 data / result 字段
        real_data = resp_data
        if OK is None:
            real_data = resp_data.get("data")
            if real_data is None:
                real_data = resp_data.get("result")
        return real_data

    async def _request(
        self, raw: bool = False, byte: bool = False, bili_res: bool = False
    ) -> Any:
        request_log.dispatch(
            "API_REQUEST",
            "Api 发起请求",
            self.__dict__,
        )

        config: dict = await self._prepare_request()
        client: BiliAPIClient = get_client()
        resp: BiliAPIResponse = await client.request(**config)
        ret: int | str | dict | bytes | BiliAPIResponse | None

        if byte:
            ret = resp.raw
        elif bili_res:
            ret = resp
        else:
            ret = self._process_response(resp=resp, raw=raw)

        request_log.dispatch(
            "API_RESPONSE",
            "Api 获得响应",
            {"result": ret},
        )
        return ret

    async def request(
        self, raw: bool = False, byte: bool = False, bili_res: bool = False
    ) -> Any:
        """
        向接口发送请求。

        Args:
            raw  (bool, optional): 是否不提取 data 或 result 字段。 Defaults to False.
            byte (bool, optional): 是否直接返回字节数据。 Defaults to False.
            bili_res (bool, optional): 是否直接返回 BiliAPIResponse 对象。 Defaults to False.

        Returns:
            int | str | dict | bytes | None: 接口未返回数据时，返回 None，否则返回该接口提供的 data 或 result 字段的数据。
        """
        times = bili_settings.get_wbi_retry_times()
        loop = times
        while loop != 0:
            if loop != times:
                request_log.dispatch(
                    "ANTI_SPIDER",
                    "反爬虫",
                    {"msg": f"wbi 第 {times - loop} 次重试"},
                )
            loop -= 1
            try:
                return await self._request(raw=raw, byte=byte, bili_res=bili_res)
            except ResponseCodeException as e:
                # -403 时尝试重新获取 wbi_mixin_key 可能过期了
                if e.code in [-403, -352, -509] and self.wbi:
                    recalculate_wbi()
                    continue
                # 不是 -403 错误直接报错
                raise e
            except Exception as e:
                raise e
        raise WbiRetryTimesExceedException()

    @property
    async def result(self) -> Any:
        """
        获取请求结果
        """
        return await self.request()


async def bili_simple_download(
    url: str, out: str, intro: str = "bili-simple-download", chunk: int = 4096
) -> None:
    """
    适用于下载 bilibili 链接的简易终端下载函数

    默认会携带 HEADERS 访问链接，避免 403

    用途举例：下载 video.get_download_url 返回结果中的链接

    Args:
        url (str): 链接
        out (str): 输出地址
        intro (str, optional): 下载简述. Defaults to 'bili-simple-download'.
        chunk (int, optional): 单次下载流拉取数据量. Defaults to 4096.
    """
    client = get_client()
    dwn_id = await client.download_create(
        url=url, headers=get_bili_headers(), chunk_size=chunk
    )
    bts = 0
    tot = client.download_content_length(cnt=dwn_id)
    if tot == 0:
        raise ArgsException("Unsupported link.")
    async with await open_file(out, "wb") as file:
        while True:
            bts += await file.write(await client.download_chunk(cnt=dwn_id))
            print(f"{intro} - {out} [{bts} / {tot}]", end="\r")
            if bts == tot:
                break
    await client.download_close(cnt=dwn_id)
    print()


async def bili_fast_download(
    url: str,
    out: str,
    intro: str = "bili-fast-download",
    chunk: int = 4096,
    part_size: int = 16 * 1024 * 1024,
    part_max: int = 128,
) -> None:
    """
    更快的 bili_simple_download

    Args:
        url (str): 链接
        out (str): 输出地址
        intro (str, optional): 下载简述. Defaults to 'bili-fast-download'.
        chunk (int, optional): 单次下载流拉取数据量. Defaults to 4096.
        part_size (int, optional): 单个文件分块大小. Defaults to 16\\*1024\\*1024.
        part_max (int, optional): 最大文件分块数. Defaults to 128.
    """
    client = get_client()
    head_id = await client.download_create(url=url, headers=get_bili_headers())
    length = client.download_content_length(cnt=head_id)
    if length == 0:
        raise ArgsException("Unsupported link.")
    await client.download_close(cnt=head_id)

    if length / part_size > part_max:
        part_size = int(length / part_max) + 1
    else:
        part_size = min(length, part_size)
    parts = [
        (start, min(start + part_size, length)) for start in range(0, length, part_size)
    ]

    file = await open_file(out, "wb")
    flock = Lock()

    async def download_part(start: int, end: int):
        dwn_id = await client.download_create(
            url=url,
            headers=get_bili_headers() | {"Range": f"bytes={start}-{end}"},
            chunk_size=chunk,
        )
        raw = bytes(0)
        tot = client.download_content_length(cnt=dwn_id)
        while True:
            raw += await client.download_chunk(cnt=dwn_id)
            print(
                f"{intro} - {out} [{len(raw)} / {tot}] <{start}-{end}>"
                + " " * 2 * len(str(length)),
                end="\r",
            )
            if len(raw) == tot:
                break
        await client.download_close(cnt=dwn_id)
        async with flock:
            await file.seek(start)
            await file.write(raw)
        print(
            f"{intro} - {out} [{len(raw)} / {tot}] <{start}-{end}>"
            + " " * 2 * len(str(length))
        )

    async with create_task_group() as tg:
        for start, end in parts:
            tg.create_task(download_part(start, end))


def configure_dynamic_fingerprint(os: str, browser: str, version: int) -> None:
    """
    快速设置 curl_cffi + fpgen 浏览器模拟

    Args:
        os (str): 系统
        browser (str): 浏览器
        version (int): 浏览器版本
    """
    select_client("curl_cffi")
    request_settings.set("impersonate", browser.lower() + str(version))
    fpgen_args = {
        "strict": True,
        "browser": browser.title(),
        "os": os,
        "languages": ["zh-CN", "zh"],
        "location": {"country": "CN"},
        "client": {"browser": {"major": version}},
    }
    bili_settings.set_enable_fpgen(True)
    bili_settings.set_fpgen_args(fpgen_args)


################################################## END Api ##################################################
