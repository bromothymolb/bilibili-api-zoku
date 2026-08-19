"""
bilibili_api.utils.high_level

模块高层级网络请求功能，包括凭据类、反爬虫与 Api 类。
"""

import base64
import binascii
from dataclasses import dataclass, field
from email.utils import parsedate_to_datetime
from functools import reduce
import hashlib
import hmac
import io
import json
from json import scanner
from json.decoder import scanstring  # type: ignore
import os
import random
import re
import struct
import time
from typing import Any
import urllib.parse

from anyio import Lock, create_task_group, open_file
from bs4 import BeautifulSoup
import chompjs
from Cryptodome.Cipher import PKCS1_OAEP
from Cryptodome.Hash import SHA256
from Cryptodome.PublicKey import RSA

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
    NetworkException,
    ResponseCodeException,
    WbiRetryTimesExceedException,
)
from .logger import request_log
from .network import (
    BiliAPIClient,
    BiliAPIFile,
    BiliAPIResponse,
    get_client,
    request_settings,
    select_client,
)
from .settings import bili_settings
from .utils import MultiEventLoopLocks, get_api


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


def get_bili_headers() -> dict:
    """
    获取可供访问 bilibili 链接的伪装请求头。

    部分请求头取自 fpgen 生成的浏览器指纹信息。

    Returns:
        dict: 请求头
    """
    fp = get_browser_fingerprint()
    headers = HEADERS.copy()
    for k, v in fp["headers"].items():
        if v:
            headers[k.title()] = v[0] if v and isinstance(v, list) else str(v)
    return headers


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
