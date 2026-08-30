"""
bilibili_api.clients.HTTPXClient

HTTPXClient 实现
"""

from collections.abc import AsyncIterator

from anyio import Lock
from frozendict import frozendict
import httpx

from ..exceptions import ApiException
from ..utils.network import (
    BiliAPIClient,
    BiliAPIFile,
    BiliAPIResponse,
    BiliWsMsgType,
)
from ..utils.utils import Sessions

sessions: Sessions[httpx.AsyncClient] = Sessions(httpx.AsyncClient)


class HTTPXClient(BiliAPIClient):
    """
    httpx 模块请求客户端
    """

    def __init__(
        self,
        proxy: str = "",
        timeout: float = 0.0,
        verify_ssl: bool = True,
        trust_env: bool = True,
        http2: bool = False,
        session: httpx.AsyncClient | None = None,
    ) -> None:
        """
        Args:
            proxy (str, optional): 代理地址. Defaults to "".
            timeout (float, optional): 请求超时时间. Defaults to 0.0.
            verify_ssl (bool, optional): 是否验证 SSL. Defaults to True.
            trust_env (bool, optional): `trust_env`. Defaults to True.
            http2 (bool, optional): 是否使用 HTTP2. Defaults to False.
            session (object, optional): 会话对象. Defaults to None.

        Note: 仅当用户只提供 `session` 参数且用户中途未调用 `set_xxx` 函数才使用用户提供的 `session`。
        """
        self.__proxy = proxy
        self.__timeout = timeout
        self.__verify_ssl = verify_ssl
        self.__trust_env = trust_env
        self.__http2 = http2
        self.__closed = False
        self.__session = session

        self.__downloads: dict[int, httpx.Response] = {}
        self.__download_iter: dict[int, AsyncIterator] = {}
        self.__download_cnt: int = 0
        self.__down_cnt_lock = Lock()

        if not self.__session:
            sessions.init(self._configuration(), self._init_args())
            self.__last_config = self._configuration()
            self.__configs: set[frozendict] = {self._configuration()}

    def _configuration(self) -> frozendict:
        return frozendict(
            {
                "proxy": self.__proxy,
                "timeout": self.__timeout,
                "verify_ssl": self.__verify_ssl,
                "trust_env": self.__trust_env,
                "http2": self.__http2,
            }
        )

    def _init_args(self) -> dict:
        return {
            "timeout": self.__timeout,
            "proxy": self.__proxy if self.__proxy != "" else None,
            "verify": self.__verify_ssl,
            "trust_env": self.__trust_env,
            "http2": self.__http2,
        }

    def _update_session(self) -> None:
        sessions.update(self.__last_config, self._configuration(), self._init_args())
        self.__last_config = self._configuration()
        self.__configs.add(self._configuration())

    async def _close_old_sessions(self) -> None:
        if self.__session:
            return
        self._update_session()
        for config, session in sessions.closed_sessions(list(self.__configs)):
            self.__configs.remove(config)
            await session.aclose()

    def get_wrapped_session(self) -> httpx.AsyncClient:
        if self.__session:
            return self.__session
        self._update_session()
        return sessions.get(self._configuration())

    def set_proxy(self, proxy: str = "") -> None:
        """
        设置代理地址

        Args:
            proxy (str, optional): 代理地址. Defaults to "".
        """
        self.__proxy = proxy

    def set_timeout(self, timeout: float = 0.0) -> None:
        """
        设置请求超时时间

        Args:
            timeout (float, optional): 请求超时时间. Defaults to 0.0.
        """
        self.__timeout = timeout

    def set_verify_ssl(self, verify_ssl: bool = True) -> None:
        """
        设置是否验证 SSL

        Args:
            verify_ssl (bool, optional): 是否验证 SSL. Defaults to True.
        """
        self.__verify_ssl = verify_ssl

    def set_trust_env(self, trust_env: bool = True) -> None:
        """
        设置 `trust_env`

        Args:
            trust_env (bool, optional): `trust_env`. Defaults to True.
        """
        self.__trust_env = trust_env

    def set_http2(self, http2: bool = False) -> None:
        """
        设置是否使用 http2.

        Args:
            http2 (bool, optional): 是否使用 http2. Defaults to False.
        """
        self.__http2 = http2

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
        params = params or {}
        data = data or {}
        files = files or {}
        headers = headers or {}
        cookies = cookies or {}
        await self._close_old_sessions()
        if files != {}:
            requests_like_files = {}
            for key, item in files.items():
                requests_like_files[key] = (
                    item.name,
                    item.content,
                    item.mime_type,
                )
            files = requests_like_files
        resp: httpx.Response = await self.get_wrapped_session().request(
            method=method,
            url=url,
            params=params,
            data=data,  # type: ignore
            files=files,  # type: ignore
            headers=headers,
            cookies=cookies,
            follow_redirects=allow_redirects,
        )
        resp_header_items = resp.headers.multi_items()
        resp_headers = {}
        for item in resp_header_items:
            resp_headers[item[0]] = item[1]
        resp_cookies = {}
        for cookie in resp.cookies.jar:
            resp_cookies[cookie.name] = cookie.value
        bili_api_resp = BiliAPIResponse(
            code=resp.status_code,
            headers=resp_headers,
            cookies=resp_cookies,
            raw=resp.content,
            url=str(resp.url),
        )
        return bili_api_resp

    async def download_create(
        self,
        url: str = "",
        headers: dict | None = None,
        chunk_size: int = 4096,
    ) -> int:
        headers = headers or {}
        await self._close_old_sessions()
        async with self.__down_cnt_lock:
            self.__download_cnt += 1
            cnt = self.__download_cnt
        req = self.get_wrapped_session().build_request(
            method="GET", url=url, headers=headers
        )
        self.__downloads[cnt] = await self.get_wrapped_session().send(
            req, stream=True, follow_redirects=True
        )
        self.__download_iter[cnt] = self.__downloads[cnt].aiter_bytes(chunk_size)
        return cnt

    async def download_chunk(self, cnt: int) -> bytes:
        iter = self.__download_iter[cnt]
        try:
            data = await anext(iter)
        except StopAsyncIteration:
            data = b""
        return data

    async def download_content_length(self, cnt: int) -> int:
        resp = self.__downloads[cnt]
        if resp.headers.get("Content-Length"):
            return int(resp.headers["Content-Length"])
        return int(resp.headers.get("content-length", "0"))

    async def download_close(self, cnt: int) -> None:
        resp = self.__downloads[cnt]
        await resp.aclose()
        del self.__downloads[cnt]
        del self.__download_iter[cnt]

    async def ws_create(
        self, url: str = "", params: dict | None = None, headers: dict | None = None
    ) -> int:
        """
        httpx 库暂未实现 WebSocket。相关讨论：<https://github.com/encode/httpx/issues/304>
        """
        raise ApiException(
            "httpx 库暂未实现 WebSocket。相关讨论：<https://github.com/encode/httpx/issues/304>"
        )

    async def ws_send(self, cnt: int, data: bytes) -> None:
        """
        httpx 库暂未实现 WebSocket。相关讨论：<https://github.com/encode/httpx/issues/304>
        """
        raise ApiException(
            "httpx 库暂未实现 WebSocket。相关讨论：<https://github.com/encode/httpx/issues/304>"
        )

    async def ws_recv(self, cnt: int) -> tuple[bytes, BiliWsMsgType]:
        """
        httpx 库暂未实现 WebSocket。相关讨论：<https://github.com/encode/httpx/issues/304>
        """
        raise ApiException(
            "httpx 库暂未实现 WebSocket。相关讨论：<https://github.com/encode/httpx/issues/304>"
        )

    async def ws_close(self, cnt: int) -> None:
        """
        httpx 库暂未实现 WebSocket。相关讨论：<https://github.com/encode/httpx/issues/304>
        """
        raise ApiException(
            "httpx 库暂未实现 WebSocket。相关讨论：<https://github.com/encode/httpx/issues/304>"
        )

    async def close(self) -> None:
        if self.__closed:
            return
        self.__closed = True
        if self.__session:
            return await self.__session.aclose()
        self._update_session()
        sessions.close(self._configuration())
        for config, session in sessions.closed_sessions(list(self.__configs)):
            self.__configs.remove(config)
            await session.aclose()

    get_wrapped_session.__doc__ = BiliAPIClient.get_wrapped_session.__doc__
    request.__doc__ = BiliAPIClient.request.__doc__
    download_create.__doc__ = BiliAPIClient.download_create.__doc__
    download_chunk.__doc__ = BiliAPIClient.download_chunk.__doc__
    download_content_length.__doc__ = BiliAPIClient.download_content_length.__doc__
    close.__doc__ = BiliAPIClient.close.__doc__
