"""
bilibili_api.utils.logger

日志功能支持。提供标准库 logging 与第三方库 loguru 的支持。
"""

import logging

from colorama import Fore

from .AsyncEvent import AsyncEvent
from .settings import bili_settings
from .utils import loguru_apply_anti_tag


def get_logging_loggers(namespace: str, level: int) -> logging.Logger:
    logger = logging.getLogger(namespace)
    logger.setLevel(level)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter(f"[{namespace}][%(asctime)s][%(levelname)s] %(message)s")
        )
        logger.addHandler(handler)
    return logger


def AsyncEvent_log(namespace: str, msg: str, level: str, debug: bool) -> None:
    if bili_settings.get_enable_loguru():
        if not debug and level == "debug":
            return
        from loguru import logger

        msg = loguru_apply_anti_tag(msg)
        if level != "error":
            getattr(logger.opt(colors=True), level)(f"<red>{namespace}</red> | {msg}")
        else:
            getattr(logger.opt(colors=True, exception=True), level)(
                f"<red>{namespace}</red> | {msg}"
            )
    else:
        logger = get_logging_loggers(
            namespace, logging.DEBUG if debug else logging.INFO
        )
        getattr(logger, level)(msg)


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
            "DELEGATE",
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
        colors = {
            Fore.GREEN: ("<green>", "</green>"),
            Fore.MAGENTA: ("<magenta>", "</magenta>"),
            Fore.YELLOW: ("<yellow>", "</yellow>"),
            Fore.CYAN: ("<cyan>", "</cyan>"),
        }
        if bili_settings.get_enable_loguru():
            from loguru import logger

            event = loguru_apply_anti_tag(event)
            for color, color_tags in colors.items():
                end_tag = 0
                while True:
                    color_str = str(color)
                    idx = event.find(color_str)
                    if idx == -1:
                        break
                    event = (
                        event[:idx]
                        + color_tags[end_tag]
                        + event[(idx + len(color_str)) :]
                    )
                    end_tag = 1 - end_tag
            logger.opt(colors=True).debug(f"<red>bilibili-api-request</red> | {event}")
        else:
            for color in colors.keys():
                event = event.replace(str(color), "")
            get_logging_loggers("bilibili-api-request", logging.DEBUG).debug(event)

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
            elif evt == "DELEGATE":
                destination_client = real_data.pop("destination_client")
                destination_instance = real_data.pop("destination_instance")
                log_str = f"{Fore.GREEN}{desc}{Fore.GREEN} --> [{Fore.MAGENTA}{destination_client} / {destination_instance}{Fore.MAGENTA}]"
            log_str = log_str or f"{Fore.GREEN}{desc}{Fore.GREEN}: {real_data}"
            self.__log(info_str + middle_str + log_str)


request_log = RequestLog()
"""
请求日志支持，默认支持输出到指定 I/O 对象。

可以添加更多监听器达到更多效果。

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
- DO_POST_FILTER: 执行后置过滤器。
- DELEGATE: 请求转发。

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
- DO_POST_FILTER: 执行后置过滤器。
- DELEGATE: 请求转发。

CallbackData: 描述 (str) 数据 (dict)

示例：

``` python
@request_log.on("REQUEST")
async def handle(desc: str, data: dict) -> None:
    print(desc, data)
```

默认启用 Api 和 Anti-Spider 相关信息。
"""
