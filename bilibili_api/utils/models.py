"""
bilibili_api.utils.models

定义模块底层中出现的模型，包括 BiliAPIClient (请求客户端)、RequestSettings (请求客户端设置) 和过滤器。
"""

from abc import ABC, abstractmethod
from asyncio import AbstractEventLoop
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from enum import Enum
import json
import mimetypes
import os
from types import AsyncGeneratorType, GeneratorType
from typing import Any, TypeVar

from anyio import get_available_backends, open_file
from anyio.lowlevel import EventLoopToken

from ..exceptions import ArgsException
from .utils import raise_for_statement

TRIO_AVAILABLE = "trio" in get_available_backends()

if TRIO_AVAILABLE:
    from trio.lowlevel import TrioToken
else:
    TrioToken = None

T = TypeVar("T")


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


@dataclass
class BiliFilter:
    """
    过滤器对象

    Attributes:
        name (str): 过滤器名称.
        locate (str): 过滤器位置. pre 为前置， post 为后置。
        priority (int, optional): 优先级。优先级越小，越早执行。Defaults to 1.
        function (Callable[[BiliFilterArgs], BiliFilterReturn.Returns | GeneratorType[BiliFilterReturn.Returns]] | None, optional): 同步函数。Defaults to None.
        async_function (Callable[..., Coroutine[Any, Any, BiliFilterReturn.Returns] | AsyncGeneratorType[BiliFilterReturn.Returns]] | None, optional): 异步函数。Defaults to None.
    """

    name: str
    locate: str
    priority: int = 1
    function: (
        Callable[
            [BiliFilterArgs],
            tuple[BiliFilterFlags, Any] | GeneratorType[tuple[BiliFilterFlags, Any]],
        ]
        | None
    ) = None
    async_function: (
        Callable[
            ...,
            Coroutine[Any, Any, tuple[BiliFilterFlags, Any]]
            | AsyncGeneratorType[tuple[BiliFilterFlags, Any]],
        ]
        | None
    ) = None
