"""
bilibili_api.clients.AioHTTPClient

AioHTTPClient 实现
"""

import asyncio

import aiohttp
from anyio import Lock
from frozendict import frozendict

from ..utils.network import (
    BiliAPIClient,
    BiliAPIFile,
    BiliAPIResponse,
    BiliWsMsgType,
)
from ..utils.utils import Sessions


class AioHTTPClient(BiliAPIClient):
    """
    aiohttp 模块请求客户端
    """

    def __init__(
        self,
        proxy="",
        timeout=0,
        verify_ssl=True,
        trust_env=True,
        session: aiohttp.ClientSession | None = None,
    ):
        self.__args: dict = {
            "proxy": proxy,
            "timeout": timeout,
            "verify_ssl": verify_ssl,
            "trust_env": trust_env,
        }
        self.__session = session
        self.__closed = False

        self.__wss: dict[int, aiohttp.ClientWebSocketResponse[bool]] = {}
        self.__ws_cnt: int = 0
        self.__ws_cnt_lock = Lock()
        self.__downloads: dict[int, aiohttp.ClientResponse] = {}
        self.__download_iter: dict[int, aiohttp.streams.AsyncStreamIterator] = {}
        self.__download_cnt: int = 0
        self.__down_cnt_lock = Lock()

        if not self.__session:
            self.__sessions: Sessions[aiohttp.ClientSession] = Sessions(
                aiohttp.ClientSession
            )
            self.__sessions.init(self._configuration(), self._init_args())
            self.__last_config = self._configuration()

    def _configuration(self) -> frozendict:
        return frozendict(
            {
                "trust_env": self.__args["trust_env"],
                "verify_ssl": self.__args["verify_ssl"],
            }
        )

    def _init_args(self) -> dict:
        return {
            "loop": asyncio.get_event_loop(),
            "trust_env": self.__args["trust_env"],
            "connector": lambda: aiohttp.TCPConnector(
                verify_ssl=self.__args["verify_ssl"]
            ),
        }

    def _update_session(self) -> None:
        self.__sessions.update(
            self.__last_config, self._configuration(), self._init_args()
        )
        self.__last_config = self._configuration()

    async def _close_old_sessions(self) -> None:
        if self.__session:
            return
        self._update_session()
        for _, session in self.__sessions.closed_sessions(self.__sessions.all()):
            await session.close()

    def get_wrapped_session(self) -> aiohttp.ClientSession:
        if self.__session:
            return self.__session
        self._update_session()
        return self.__sessions.get(self._configuration())

    def set_proxy(self, proxy: str = "") -> None:
        """
        设置代理地址

        Args:
            proxy (str, optional): 代理地址. Defaults to "".
        """
        self.__args["proxy"] = proxy

    def set_timeout(self, timeout: float = 0) -> None:
        """
        设置请求超时时间

        Args:
            timeout (float, optional): 请求超时时间. Defaults to 0.0.
        """
        self.__args["timeout"] = timeout

    def set_verify_ssl(self, verify_ssl: bool = True) -> None:
        """
        设置是否验证 SSL

        Args:
            verify_ssl (bool, optional): 是否验证 SSL. Defaults to True.
        """
        self.__args["verify_ssl"] = verify_ssl

    def set_trust_env(self, trust_env: bool = True) -> None:
        """
        设置 `trust_env`

        Args:
            trust_env (bool, optional): `trust_env`. Defaults to True.
        """
        self.__args["trust_env"] = trust_env

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
        if files:
            form = aiohttp.FormData()
            if isinstance(data, str) or isinstance(data, bytes):
                raise NotImplementedError
            for key, value in data.items():
                form.add_field(name=key, value=value)
            for key, value in files.items():
                form.add_field(
                    name=key,
                    value=value.content,
                    content_type=value.mime_type,
                    filename=value.name,
                )
            data = form  # type: ignore
        if not self.__session:
            resp = await self.get_wrapped_session().request(
                method=method,
                url=url,
                params=params,
                data=data,
                headers=headers,
                cookies=cookies,
                allow_redirects=allow_redirects,
                proxy=self.__args["proxy"],
                timeout=aiohttp.ClientTimeout(self.__args["timeout"]),
            )
        else:
            resp = await self.get_wrapped_session().request(
                method=method,
                url=url,
                params=params,
                data=data,
                headers=headers,
                cookies=cookies,
                allow_redirects=allow_redirects,
            )
        resp_code = resp.status
        resp_headers = {}
        for key, item in resp.headers.items():
            resp_headers[key] = item
        resp_cookies = {}
        for key, item in resp.cookies.items():
            resp_cookies[key] = item.value
        bili_api_resp = BiliAPIResponse(
            code=resp_code,
            headers=resp_headers,
            cookies=resp_cookies,
            raw=await resp.read(),
            url=str(resp.url),
        )
        resp.release()
        await resp.wait_for_close()
        return bili_api_resp

    async def download_create(
        self,
        url: str = "",
        headers: dict | None = None,
        chunk_size: int = 4096,
    ) -> int:
        headers = headers or {}
        await self._close_old_sessions()
        await self.__down_cnt_lock.acquire()
        self.__download_cnt += 1
        cnt = self.__download_cnt
        self.__down_cnt_lock.release()
        self.__downloads[cnt] = await self.get_wrapped_session().get(
            url=url, headers=headers
        )
        self.__download_iter[cnt] = self.__downloads[cnt].content.iter_chunked(
            chunk_size
        )
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
        resp.release()
        await resp.wait_for_close()
        del self.__downloads[cnt]
        del self.__download_iter[cnt]

    async def ws_create(
        self, url: str = "", params: dict | None = None, headers: dict | None = None
    ) -> int:
        params = params or {}
        headers = headers or {}
        await self._close_old_sessions()
        await self.__ws_cnt_lock.acquire()
        self.__ws_cnt += 1
        cnt = self.__ws_cnt
        self.__ws_cnt_lock.release()
        self.__wss[cnt] = await self.get_wrapped_session().ws_connect(
            url=url, params=params, headers=headers
        )
        return cnt

    async def ws_recv(self, cnt: int) -> tuple[bytes, BiliWsMsgType]:
        msg = await self.__wss[cnt].receive()
        return msg.data, BiliWsMsgType(msg.type.value)

    async def ws_send(self, cnt: int, data: bytes) -> None:
        return await self.__wss[cnt].send_bytes(data)

    async def ws_close(self, cnt: int) -> None:
        await self.__wss[cnt].close()
        del self.__wss[cnt]

    async def close(self):
        if self.__closed:
            return
        self.__closed = True
        if self.__session:
            return await self.__session.close()
        self._update_session()
        self.__sessions.close(self._configuration())
        for _, session in self.__sessions.closed_sessions(self.__sessions.all()):
            await session.close()

    __init__.__doc__ = BiliAPIClient.__init__.__doc__
    get_wrapped_session.__doc__ = BiliAPIClient.get_wrapped_session.__doc__
    request.__doc__ = BiliAPIClient.request.__doc__
    download_create.__doc__ = BiliAPIClient.download_create.__doc__
    download_chunk.__doc__ = BiliAPIClient.download_chunk.__doc__
    download_content_length.__doc__ = BiliAPIClient.download_content_length.__doc__
    ws_create.__doc__ = BiliAPIClient.ws_create.__doc__
    ws_recv.__doc__ = BiliAPIClient.ws_recv.__doc__
    ws_send.__doc__ = BiliAPIClient.ws_send.__doc__
    ws_close.__doc__ = BiliAPIClient.ws_close.__doc__
    close.__doc__ = BiliAPIClient.close.__doc__
