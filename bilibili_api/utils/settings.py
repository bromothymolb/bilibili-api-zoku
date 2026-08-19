"""
bilibili_api.utils.settings

模块相关设置
"""

from typing import Any

from ..exceptions import ArgsException


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
            "enable_loguru": False,
        }
        self.__defaults = {
            "wbi_retry_times": 3,
            "enable_auto_buvid": True,
            "enable_bili_ticket": False,
            "enable_buvid_global_persistence": False,
            "enable_bili_ticket_global_persistence": False,
            "enable_fpgen": False,
            "fpgen_args": {},
            "enable_loguru": False,
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

    def get_enable_loguru(self) -> bool:
        """
        获取是否启用 loguru

        Returns:
            bool: 是否启用 loguru. Defaults to False.
        """
        return self.get("enable_loguru")

    def set_enable_loguru(self, enable_loguru: bool) -> None:
        """
        获取是否启用 loguru

        Args:
            enable_loguru (bool): 是否启用 loguru
        """
        self.set("enable_loguru", enable_loguru)

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
