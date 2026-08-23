"""
bilibili_api.clients.HTTPXClient

HTTPXClient 实现
"""

from collections.abc import AsyncIterator

import httpx

from ..exceptions import ApiException
from ..utils.network import (
    BiliAPIClient,
    BiliAPIFile,
    BiliAPIResponse,
    BiliWsMsgType,
)
from ..utils.utils import MultiEventLoopLocks


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
        if session:
            self.__session = session
        else:
            self.__session = httpx.AsyncClient(
                timeout=self.__timeout,
                proxy=self.__proxy if self.__proxy != "" else None,
                verify=self.__verify_ssl,
                trust_env=self.__trust_env,
                http2=self.__http2,
            )
        self.__downloads: dict[int, httpx.Response] = {}
        self.__download_iter: dict[int, AsyncIterator] = {}
        self.__download_cnt: int = 0

        self.__need_update_session: bool = False
        self.__session_update_lock = MultiEventLoopLocks()
        self.__down_cnt_lock = MultiEventLoopLocks()

    def get_wrapped_session(self) -> httpx.AsyncClient:
        return self.__session

    def set_proxy(self, proxy: str = "") -> None:
        """
        设置代理地址

        Args:
            proxy (str, optional): 代理地址. Defaults to "".
        """
        self.__proxy = proxy
        self.__need_update_session = True

    def set_timeout(self, timeout: float = 0.0) -> None:
        """
        设置请求超时时间

        Args:
            timeout (float, optional): 请求超时时间. Defaults to 0.0.
        """
        self.__timeout = timeout
        self.__session.timeout = timeout

    def set_verify_ssl(self, verify_ssl: bool = True) -> None:
        """
        设置是否验证 SSL

        Args:
            verify_ssl (bool, optional): 是否验证 SSL. Defaults to True.
        """
        self.__verify_ssl = verify_ssl
        self.__need_update_session = True

    def set_trust_env(self, trust_env: bool = True) -> None:
        """
        设置 `trust_env`

        Args:
            trust_env (bool, optional): `trust_env`. Defaults to True.
        """
        self.__trust_env = trust_env
        self.__need_update_session = True

    async def __auto_update_session(self) -> None:
        if self.__need_update_session:
            async with self.__session_update_lock.get_lock():
                if self.__session_update_lock.check_multithread_state():
                    if self.__need_update_session:
                        await self.__session.aclose()
                        self.__session = httpx.AsyncClient(
                            timeout=self.__timeout,
                            proxy=self.__proxy if self.__proxy != "" else None,
                            verify=self.__verify_ssl,
                            trust_env=self.__trust_env,
                            http2=self.__http2,
                        )
                        self.__need_update_session = False
                    await self.__session_update_lock.done_multithread()
                else:
                    await self.__session_update_lock.wait_multithread()

    def set_http2(self, http2: bool = False) -> None:
        """
        设置是否使用 http2.

        Args:
            http2 (str, optional): 是否使用 http2. Defaults to False.
        """
        self.__http2 = http2
        self.__session = httpx.AsyncClient(
            timeout=self.__timeout,
            proxy=self.__proxy if self.__proxy != "" else None,
            verify=self.__verify_ssl,
            trust_env=self.__trust_env,
            http2=self.__http2,
        )

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
        await self.__auto_update_session()
        if files != {}:
            requests_like_files = {}
            for key, item in files.items():
                requests_like_files[key] = (
                    item.name,
                    item.content,
                    item.mime_type,
                )
            files = requests_like_files
        resp: httpx.Response = await self.__session.request(
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
        await self.__auto_update_session()
        async with self.__down_cnt_lock.get_lock():
            while True:
                if self.__down_cnt_lock.check_multithread_state():
                    self.__download_cnt += 1
                    cnt = self.__download_cnt
                    await self.__down_cnt_lock.done_multithread()
                    break
                else:
                    await self.__down_cnt_lock.wait_multithread()
        req = self.__session.build_request(method="GET", url=url, headers=headers)
        self.__downloads[cnt] = await self.__session.send(
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
        await self.__session.aclose()
        del self.__session

    get_wrapped_session.__doc__ = BiliAPIClient.get_wrapped_session.__doc__
    request.__doc__ = BiliAPIClient.request.__doc__
    download_create.__doc__ = BiliAPIClient.download_create.__doc__
    download_chunk.__doc__ = BiliAPIClient.download_chunk.__doc__
    download_content_length.__doc__ = BiliAPIClient.download_content_length.__doc__
    close.__doc__ = BiliAPIClient.close.__doc__
