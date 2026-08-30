"""
bilibili_api.utils.network

与网络请求相关的模块。能对会话进行管理（复用 TCP 连接）。
"""

from abc import ABC, abstractmethod
from asyncio import AbstractEventLoop
import atexit
from collections.abc import Callable, Coroutine
from contextlib import AbstractContextManager
from copy import deepcopy
from dataclasses import dataclass
from enum import Enum
from functools import cmp_to_key, partial
from inspect import (
    iscoroutine,
    iscoroutinefunction,
    signature,
)
import json
import mimetypes
import os
from threading import Lock as ThreadingLock
from typing import TYPE_CHECKING, Any, TypeVar

from anyio import (
    RunFinishedError,
    create_task_group,
    from_thread,
    get_available_backends,
    open_file,
    to_thread,
)
from anyio._backends._asyncio import AsyncIOBackend
from anyio.lowlevel import EventLoopToken, current_token

from ..exceptions import ArgsException, FilterException
from .logger import request_log
from .utils import MultiContextVariable, raise_for_statement

TRIO_AVAILABLE = "trio" in get_available_backends()

if TYPE_CHECKING:
    from trio.lowlevel import TrioToken
else:
    if TRIO_AVAILABLE:
        from anyio._backends._trio import TrioBackend
        from trio.lowlevel import TrioToken
    else:
        TrioToken = None

T = TypeVar("T")

##### ABC #####


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
            session: object | None = None,
            **settings: dict[str, object],
        ) -> None:
            """
            Args:
                session (object, optional): 会话对象. Defaults to None.
                settings (dict[str, object]): 所有的设置项 (**kwargs 传入)，用于初始化时传入设置。
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
        async def download_content_length(self, cnt: int) -> int:
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
        session: object | None = None,
        **settings: dict[str, object],
    ) -> None:
        """
        Args:
            session (object, optional): 会话对象. Defaults to None.
            settings (dict[str, object]): 所有的设置项 (**kwargs 传入)，用于初始化时传入设置。
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
    async def download_content_length(self, cnt: int) -> int:
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


class BiliFilterFlags(Enum):
    """
    过滤器行为枚举

    - 【NOTE】以下为设置类过滤器行为，可无限叠加（存在顺序）。
    - SET_PARAMS: 设置函数的参数 (仅前置过滤器)
    - SET_RETURN: 设置返回值 (仅后置过滤器)
    - 【NOTE】以下为跳转类过滤器行为，不可叠加，将在设置类过滤器之后执行。
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
        if not self.has_data(key):
            raise ArgsException(f"不存在数据 {key}")
        return self.__data[key]

    def delete_data(self, key: str) -> None:
        """
        删除数据

        Args:
            key (str): 键
        """

        if not self.has_data(key):
            raise ArgsException(f"不存在数据 {key}")
        del self.__data[key]


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


@dataclass
class BiliFilterReturn:
    """
    过滤器返回值

    - flag (BiliFilterFlags): 过滤器返回后行为
    - param (Any, optional): 过滤器返回携带参数，可能存在。Defaults to None.
    """

    flag: BiliFilterFlags
    param: Any = None

    @classmethod
    def continue_exec(cls) -> "BiliFilterReturn":
        """
        继续过滤器执行

        Returns:
            tuple[BiliFilterFlags, None]: 过滤器函数返回值
        """
        return cls(flag=BiliFilterFlags.CONTINUE)

    @classmethod
    def set_params(cls, params: dict) -> "BiliFilterReturn":
        """
        设置函数的参数 (仅前置过滤器)

        Args:
            params (dict): 参数

        Returns:
            tuple[BiliFilterFlags, dict]: 过滤器函数返回值
        """
        return cls(flag=BiliFilterFlags.SET_PARAMS, param=params)

    @classmethod
    def set_return(cls, ret: Any) -> "BiliFilterReturn":
        """
        设置函数的返回值 (仅后置过滤器)

        Args:
            ret (Any): 函数返回值

        Returns:
            tuple[BiliFilterFlags, Any]: 过滤器函数返回值
        """
        return cls(flag=BiliFilterFlags.SET_RETURN, param=ret)

    @classmethod
    def execute_now(cls) -> "BiliFilterReturn":
        """
        直接运行函数 (仅前置过滤器)

        Returns:
            tuple[BiliFilterFlags, None]: 过滤器函数返回值
        """
        return cls(flag=BiliFilterFlags.EXECUTE_NOW)

    @classmethod
    def return_now(cls) -> "BiliFilterReturn":
        """
        直接返回结果，作为待运行函数返回值

        Returns:
            tuple[BiliFilterFlags, None]: 过滤器函数返回值
        """
        return cls(flag=BiliFilterFlags.RETURN_NOW)

    @classmethod
    def goto_idx(cls, idx: int) -> "BiliFilterReturn":
        """
        跳到任意一个过滤器

        Args:
            idx (int): 对应过滤器的下标，可 `get_registered_(pre|post)_filters` 查询

        Returns:
            tuple[BiliFilterFlags, int]: 过滤器函数返回值
        """
        return cls(flag=BiliFilterFlags.GOTO, param=idx)

    @classmethod
    def goto_name(cls, name: str) -> "BiliFilterReturn":
        """
        跳到任意一个过滤器

        Args:
            name (str): 对应过滤器名称

        Returns:
            tuple[BiliFilterFlags, int]: 过滤器函数返回值
        """
        for idx, filt in enumerate(get_registered_filters()):
            if filt.name == name:
                return cls(flag=BiliFilterFlags.GOTO, param=idx)
        raise ArgsException(f"未找到前置过滤器 {name}")


@dataclass
class BiliFilter:
    """
    过滤器对象

    Attributes:
        name (str): 过滤器名称.
        locate (str): 过滤器位置. pre 为前置， post 为后置。
        priority (int, optional): 优先级。优先级越小，越早执行。Defaults to 1.
        function (Callable[[BiliFilterArgs], list[BiliFilterReturn] | BiliFilterReturn] | None, optional): 同步函数。Defaults to None.
        async_function (Callable[..., Coroutine[Any, Any, BiliFilterReturn.Returns] | AsyncGenerator[BiliFilterReturn.Returns]] | None, optional): 异步函数。Defaults to None.
    """

    name: str
    locate: str
    priority: int = 1
    # fmt: off
    function: Callable[[BiliFilterArgs], list[BiliFilterReturn] | BiliFilterReturn | None] | None = None
    async_function: Callable[[BiliFilterArgs], Coroutine[Any, Any, list[BiliFilterReturn] | BiliFilterReturn | None]] | None = None
    # fmt: on


# _BiliAPIClient
client_func_cnt = 0
client_lock = ThreadingLock()
loops: set[EventLoopToken] = set()
# client -> BiliAPIClient class
sessions: dict[str, type["BiliAPIClient"]] = {}
# client -> settings
client_settings: dict[str, list] = {}
client_defaults: dict[str, dict] = {}
# client -> instance
client_groups: dict[str, dict[str, "_BiliAPIClientGroup"]] = {}
# filters
__registered_filters: list[BiliFilter] = []
# selected client / instance
selected_client: MultiContextVariable[str] = MultiContextVariable("bili_client", "")
selected_instance: MultiContextVariable[str] = MultiContextVariable("bili_instance", "")
# global settings
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
        if key.startswith("set_"):
            raise ArgsException(
                "不支持直接调用 set_xxx 函数。请使用 get_settings / get_instance_settings / get_force_settings 间接设置。"
            )

        obj = getattr(self.client, key)
        if not iscoroutinefunction(obj):
            return obj

        if key.startswith("_"):
            return obj

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

        async def run_filter(
            filter: Callable, args: BiliFilterArgs
        ) -> list[BiliFilterReturn]:
            result = filter(args)
            if iscoroutine(result):
                result = await result
            if not result:
                result = BiliFilterReturn.continue_exec()
            if isinstance(result, BiliFilterReturn):
                result = [result]
            return result  # type: ignore

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
                    locate = filt.locate
                    if not skip_pre:
                        request_log.dispatch(
                            f"DO_{log_helper[locate][0]}_FILTER",
                            f"执行{log_helper[locate][1]}过滤器",
                            {
                                "act_id": cnt,
                                "name": filt.name,
                                "priority": filt.priority,
                                "client": self.__client__,
                                "instance": self.__instance__,
                                "action": key,
                                "event_loop": self.__event_loop,
                                "filter_id": i,
                            },
                        )
                    gresult = None
                    if locate == "pre" and skip_pre:
                        pass
                    elif filt.function or filt.async_function:
                        try:
                            results = await run_filter(
                                filt.function or filt.async_function,  # type: ignore
                                BiliFilterArgs(
                                    **filter_args,
                                    params=args.copy(),
                                    ret=deepcopy(ret),
                                    filter_index=i,
                                    filter_locate=locate,
                                ),
                            )
                        except Exception as e:
                            raise FilterException(locate, filt.name, e) from e
                        for result in results:
                            if result.flag == BiliFilterFlags.SET_PARAMS:
                                args = deepcopy(result.param)
                            elif result.flag == BiliFilterFlags.SET_RETURN:
                                ret = deepcopy(result.param)
                            else:
                                if gresult:
                                    raise ArgsException("跳转类行为不可叠加")
                                gresult = result
                    else:
                        i += 1
                        continue
                    if not gresult:
                        gresult = BiliFilterReturn.continue_exec()
                    if gresult.flag == BiliFilterFlags.EXECUTE_NOW:
                        skip_pre = True
                    elif gresult.flag == BiliFilterFlags.RETURN_NOW:
                        return ret
                    elif gresult.flag == BiliFilterFlags.GOTO:
                        raise_for_statement(
                            isinstance(gresult.param, int),
                            "执行 BiliFilterFlasg.GOTO 需同时传入整数值下标",
                        )
                        i = gresult.param
                        continue
                    i += 1
                    if locate == "pre" and (
                        i >= len(filts) or filts[i].locate == "post"
                    ):
                        ret = await async_function(**args)  # type: ignore
                        skip_pre = False
                return ret

            return wrapped_amethod

        return coroutine_wrapper(obj)


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
    if name == "":
        raise ArgsException("名称不能为空。")
    if name in sessions.keys():
        raise ArgsException(f"已注册过请求客户端 {name}")
    settings = settings or {}
    sessions[name] = cls
    client_groups[name] = {}
    client_settings[name] = list(settings.keys())
    client_defaults[name] = settings
    select_client(name)
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


def select_client(name: str) -> None:
    """
    选择模块使用的注册过的请求客户端，可用于用户自定义请求客户端。

    Args:
        name (str): 请求客户端类型名称，用户自定义命名。
    """
    if not sessions.get(name):
        raise ArgsException(f"未注册过 {name}。")
    selected_client.set(name)


def select_client_local_context(name: str) -> AbstractContextManager[None]:
    """
    通过 `ContextVar` 仅在局部上下文选择请求客户端。

    Args:
        name (str): 请求客户端类型名称，用户自定义命名。

    Returns:
        AbstractContextManager[None]: 上下文管理器
    """
    return selected_client.set_local_context(name)


def get_selected_client() -> tuple[str, type[BiliAPIClient]]:
    """
    获取用户选择的请求客户端名称和对应的类

    Returns:
        tuple[str, type[BiliAPIClient]]: 第 0 项为客户端名称，第 1 项为对应的类
    """
    if selected_client.get() != "":
        return selected_client.get(), sessions[selected_client.get()]
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
        name (str): 实例名称，一般情况下已存在默认实例 `default`。
        client (str | None, optional): BiliAPIClient 类型. Defaults to None.
    """
    if name == "":
        raise ArgsException("名称不能为空。")
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
        name (str): 实例名称，一般情况下已存在默认实例 `default`。
        client (str | None, optional): BiliAPIClient 类型. Defaults to None.
    """
    client = client or get_selected_client()[0]
    global client_groups
    try:
        client_groups[client].pop(name)
    except KeyError as e:
        raise ArgsException("未找到指定请求客户端实例。") from e


def select_instance(name: str) -> None:
    """
    选择请求客户端实例

    Args:
        name (str): 实例名称，一般情况下已存在默认实例 `default`。
    """
    selected_instance.set(name)


def select_instance_local_context(name: str) -> AbstractContextManager[None]:
    """
    通过 `ContextVar` 仅在局部上下文选择请求客户端实例。

    Args:
        name (str): 实例名称，一般情况下已存在默认实例 `default`。

    Returns:
        AbstractContextManager[None]: 上下文管理器
    """
    return selected_instance.set_local_context(name)


def get_selected_instance() -> str:
    """
    获取选择的请求客户端实例

    Returns:
        str: 选择的请求客户端实例
    """
    return selected_instance.get()


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
    func: Callable[[BiliFilterArgs], list[BiliFilterReturn] | BiliFilterReturn | None]
    | Callable[
        [BiliFilterArgs],
        Coroutine[Any, Any, list[BiliFilterReturn] | BiliFilterReturn | None],
    ],
    priority: int = 1,
) -> None:
    """
    注册/修改前置过滤器

    执行函数需返回一个元组，第一项为 BiliAPIFlags，第二项为配合 BiliAPIFlags 的值。

    所有当前函数执行的过滤器为 `ins.data[cnt]["pre_filters"]`。

    Args:
        name (str): 名称，若重复则为修改对应过滤器。
        func (Callable): 执行的函数，参数传入 `FilterArgs` 对象.
        priority (int, optional): 优先级，数字越小越优先执行. Defaults to 1.
    """
    global __registered_filters
    args = {
        "name": name,
        "priority": priority,
        "locate": "pre",
    }
    if iscoroutinefunction(func):
        args["async_function"] = func
    else:
        args["function"] = func
    for i, pre in enumerate(__registered_filters):
        if pre.name == name:
            __registered_filters[i] = BiliFilter(**args)
            return
    __registered_filters.append(BiliFilter(**args))


def register_post_filter(
    name: str,
    func: Callable[[BiliFilterArgs], list[BiliFilterReturn] | BiliFilterReturn | None]
    | Callable[
        [BiliFilterArgs],
        Coroutine[Any, Any, list[BiliFilterReturn] | BiliFilterReturn | None],
    ],
    priority: int = 1,
) -> None:
    """
    注册/修改后置过滤器

    执行函数需返回一个元组，第一项为 BiliAPIFlags，第二项为配合 BiliAPIFlags 的值。

    所有当前函数执行的过滤器为 `ins.data[cnt]["post_filters"]`。

    Args:
        name (str): 名称，若重复则为修改对应过滤器。
        func (Callable): 执行的函数，参数传入 `FilterArgs` 对象.
        priority (int, optional): 优先级，数字越小越优先执行. Defaults to 1.
    """
    global __registered_filters
    args = {
        "name": name,
        "priority": priority,
        "locate": "post",
    }
    if iscoroutinefunction(func):
        args["async_function"] = func
    else:
        args["function"] = func
    for i, post in enumerate(__registered_filters):
        if post.name == name:
            __registered_filters[i] = BiliFilter(**args)
            return
    __registered_filters.append(BiliFilter(**args))


def get_registered_filters(in_priority: bool = True) -> list[BiliFilter]:
    """
    获取所有已注册的过滤器

    Args:
        in_priority (bool, optional): 是否排序. Defaults to True.

    Returns:
        list[BiliFilter]: 已注册的前置过滤器
    """
    if in_priority:

        def cmp(filt1: BiliFilter, filt2: BiliFilter) -> int:
            locate = ["pre", "post"]
            if filt1.locate != filt2.locate:
                return locate.index(filt1.locate) - locate.index(filt2.locate)
            return filt1.priority - filt2.priority

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
        if filt.name == name:
            del __registered_filters[i]
            return


@atexit.register
def __clean() -> None:
    """
    程序退出清理操作。
    """
    for loop in loops:
        try:
            from_thread.run(partial(clean_session, token=loop), token=loop)
        except RunFinishedError:
            pass


##### logging #####


def __request_log_pre(args: BiliFilterArgs) -> None:
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
                {"id": args.params["cnt"], "data": args.params["data"]} | running_info,
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


def __request_log_post(args: BiliFilterArgs) -> None:
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


##### delegate #####


class DelegateType(Enum):
    """
    请求转发类型

    - REQUEST: `request` 函数转发
    - WEBSOCKET: `ws_create` `ws_recv` `ws_send` `ws_close` 转发
    - DOWNLOAD: `download_create` `download_chunk` `download_content_length` `download_close` 转发
    """

    REQUEST = "request"
    WEBSOCKET = "ws_"
    DOWNLOAD = "download_"


__delegate: dict[DelegateType, MultiContextVariable[tuple[str, str]]] = {
    DelegateType.REQUEST: MultiContextVariable("bili_delegate_request", ("", "")),
    DelegateType.WEBSOCKET: MultiContextVariable("bili_delegate_websocket", ("", "")),
    DelegateType.DOWNLOAD: MultiContextVariable("bili_delegate_download", ("", "")),
}


def delegate(
    delegate_type: DelegateType,
    destination_client: str | None = None,
    destination_instance: str | None = None,
) -> None:
    """
    将部分类型的请求派发至其他请求客户端。

    Args:
        delegate_type (DelegateType): 转发请求的函数范围，如转发所有 WebSocket 相关函数。
        destination_client (str | None): 目标第三方库。若未指定，模块将选择当前第三方库。Defaults to None.
        destination_instance (str | None): 目标实例。若未指定，模块将选择当前实例名称。Defaults to None.
    """
    __delegate[delegate_type].set(
        (
            destination_client or get_selected_client()[0],
            destination_instance or get_selected_instance(),
        )
    )


def undelegate(delegate_type: DelegateType) -> None:
    """
    取消派发。

    Args:
        delegate_type (DelegateType): 转发请求的函数范围，如转发所有 WebSocket 相关函数。
    """
    delegate(
        delegate_type=delegate_type,
        destination_client="",
        destination_instance="",
    )


def delegate_local_context(
    delegate_type: DelegateType,
    destination_client: str | None = None,
    destination_instance: str | None = None,
) -> AbstractContextManager[None]:
    """
    通过 `ContextVar` 仅在局部上下文设置派发。

    Args:
        delegate_type (DelegateType): 转发请求的函数范围，如转发所有 WebSocket 相关函数。
        destination_client (str | None): 目标第三方库。若未指定，模块将选择当前第三方库。Defaults to None.
        destination_instance (str | None): 目标实例。若未指定，模块将选择当前实例名称。Defaults to None.

    Returns:
        AbstractContextManager[None]: 上下文管理器
    """
    return __delegate[delegate_type].set_local_context(
        (
            destination_client or get_selected_client()[0],
            destination_instance or get_selected_instance(),
        )
    )


def get_delegates() -> dict[DelegateType, tuple[str, str]]:
    """
    获取当前派发情况，键为派发函数范围，值为元组，第一项是第三方库，第二项是具体实例，若二者皆为空则不会进行请求派发。

    Returns:
        dict[DelegateType, tuple[str, str]]: 派发情况
    """
    ret = {}
    for key, item in __delegate.items():
        ret[key] = item.get()
    return ret


async def __request_delegate(
    args: BiliFilterArgs,
) -> BiliFilterReturn | list[BiliFilterReturn]:
    for delegate_type, destination_var in __delegate.items():
        if args.func.startswith(delegate_type.value):
            destination = destination_var.get()
            destination_client = destination[0] or get_selected_client()[0]
            destination_instance = destination[1] or get_selected_instance()
            if (
                destination_client == args.client
                and destination_instance == args.instance
            ):
                break
            running_info = {
                "act_id": args.filter_cnt,
                "client": args.client,
                "instance": args.instance,
                "event_loop": args.event_loop_token,
            }
            request_log.dispatch(
                "DELEGATE",
                "转发请求",
                {
                    "destination_client": destination_client,
                    "destination_instance": destination_instance,
                }
                | running_info,
            )
            delegate_client = get_client(
                client=destination_client, instance=destination_instance
            )
            func = getattr(delegate_client, args.func)
            result = func(**args.params)
            if iscoroutine(result):
                result = await result
            return [BiliFilterReturn.set_return(result), BiliFilterReturn.return_now()]
    return BiliFilterReturn.continue_exec()


register_pre_filter(name="__builtin_log_pre", func=__request_log_pre, priority=919)
register_post_filter(name="__builtin_log_post", func=__request_log_post, priority=0)
register_pre_filter(name="__builtin_delegate", func=__request_delegate, priority=0)
