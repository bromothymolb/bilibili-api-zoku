"""
bilibili_api.utils.logger

日志功能支持。提供标准库 logging 与第三方库 loguru 的支持。
"""

from collections.abc import Callable
import logging
from typing import Any, Literal, overload

from colorama import Fore

from .settings import bili_settings
from .utils import loguru_apply_anti_tag


def get_logging_loggers(name: str, level: int) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        # initialization
        logger.setLevel(level)
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter(f"[{name}][%(asctime)s][%(levelname)s] %(message)s")
        )
        logger.addHandler(handler)
    return logger


def AsyncEvent_log(name: str, msg: str, level: str, debug: bool) -> None:
    if bili_settings.get_enable_loguru():
        from loguru import logger

        if not debug and level == "debug":
            return
        msg = loguru_apply_anti_tag(msg)
        if level != "error":
            getattr(logger.bind(name=name).opt(colors=True), level)(
                f"<red>{name}</red> | {msg}"
            )  # type: ignore
        else:
            getattr(logger.bind(name=name).opt(colors=True, exception=True), level)(  # type: ignore
                f"<red>{name}</red> | {msg}"
            )  # type: ignore
    else:
        logger = get_logging_loggers(name, logging.DEBUG if debug else logging.INFO)
        getattr(logger, level)(msg)


class _AsyncEventLoggingSupport:
    def __init__(self) -> None:
        self._debug: bool
        self._log: bool

    @property
    def logger(self) -> logging.Logger:
        return get_logging_loggers(
            str(self), logging.DEBUG if self._debug else logging.INFO
        )

    def _log_debug(self, msg: str) -> None:
        if self._log:
            AsyncEvent_log(str(self), msg, "debug", self._debug)

    def _log_info(self, msg: str) -> None:
        if self._log:
            AsyncEvent_log(str(self), msg, "info", self._debug)

    def _log_warning(self, msg: str) -> None:
        if self._log:
            AsyncEvent_log(str(self), msg, "warning", self._debug)

    def _log_error(self, msg: str) -> None:
        if self._log:
            AsyncEvent_log(str(self), msg, "error", self._debug)


class RequestLog:
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
        self.__all_events: list[str] = [
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
        self.__handlers = {}
        self.__ignore_events: list[str] = []
        self.add_event_listener("__ALL__", self.__handle_events)

    def __str__(self) -> str:
        return "request_log"

    def __repr__(self) -> str:
        return "request_log"

    @property
    def logger(self) -> logging.Logger:
        return get_logging_loggers("bilibili-api-request", logging.DEBUG)

    @overload
    def add_event_listener(
        self, name: Literal["__ALL__"], handler: Callable[[str, str, dict], Any]
    ) -> None: ...

    @overload
    def add_event_listener(
        self,
        name: Literal["__TASK_EXCEPTION__"],
        handler: Callable[[str, Exception], Any],
    ) -> None: ...

    @overload
    def add_event_listener(
        self, name: str, handler: Callable[[str, dict], Any]
    ) -> None: ...

    def add_event_listener(self, name: str, handler: Callable) -> None:
        """
        注册事件监听器。

        ``` python
        def handle_request(desc: str, data: dict) -> None:
            # desc: 发起请求
            # data: {'method': 'GET', 'url': 'https://api.bilibili.com/x/web-interface/zone', ...}
            raise ApiException("测试抛出异常")

        request_log.add_event_listener("REQUEST", handle_request)

        def handle_all(name: str, desc: str, data: dict) -> None:
            # name: REQUEST
            # desc: 发起请求
            # data: {'method': 'GET', 'url': 'https://api.bilibili.com/x/web-interface/zone', ...}
            print(data)

        request_log.add_event_listener("__ALL__", handle_all)

        def handle_exception(name: str, exc: Exception) -> None:
            # name: REQUEST
            # exc: ApiException("测试抛出异常")
            print(exc)

        request_log.add_event_listener("__TASK_EXCEPTION__", handle_exception)
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
    ) -> Callable[[Callable[[str, str, dict], Any]], Any]: ...

    @overload
    def on(
        self, event_name: Literal["__TASK_EXCEPTION__"]
    ) -> Callable[[Callable[[str, Exception], Any]], Any]: ...

    @overload
    def on(self, event_name: str) -> Callable[[Callable[[str, dict], Any]], Any]: ...

    def on(self, event_name: str) -> Callable:
        """
        装饰器注册事件监听器。

        ``` python
        @request_log.on("REQUEST")
        def handle_request(desc: str, data: dict) -> None:
            # desc: 发起请求
            # data: {'method': 'GET', 'url': 'https://api.bilibili.com/x/web-interface/zone', ...}
            raise ApiException("测试抛出异常")

        @request_log.on("__ALL__")
        def handle_all(name: str, desc: str, data: dict) -> None:
            # name: REQUEST
            # desc: 发起请求
            # data: {'method': 'GET', 'url': 'https://api.bilibili.com/x/web-interface/zone', ...}
            print(data)

        @request_log.on("__TASK_EXCEPTION__")
        def handle_exception(name: str, exc: Exception) -> None:
            # exc: ApiException("测试抛出异常")
            print(exc)
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

    def get_all_events(self) -> list[str]:
        """
        获取日志支持的所有默认事件列表

        Returns:
            list[str]: 日志支持的所有默认事件列表
        """
        return self.__all_events.copy()

    def register_event(self, name: str) -> None:
        """
        注册请求日志事件

        Args:
            name (str): 请求日志事件
        """
        self.__all_events.append(name)

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

    def dispatch(self, name: str, *args) -> None:
        """
        异步发布事件。

        Args:
            name (str): 事件名。
            args (Any): 要传递给函数的参数。 *args 传递。
        """
        name = name.upper()
        if name in self.__handlers:
            for func in self.__handlers[name]:
                try:
                    func(*args)
                except Exception as e:
                    if name == "__TASK_EXCEPTION__":
                        raise e
                    self.dispatch("__TASK_EXCEPTION__", name, e)
        if name != "__ALL__" and name != "__TASK_EXCEPTION__":
            self.dispatch("__ALL__", name, *args)

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
            logger.bind(name="bilibili-api-request").opt(colors=True).debug(  # type: ignore
                f"<red>bilibili-api-request</red> | {event}"
            )
        else:
            for color in colors.keys():
                event = event.replace(str(color), "")
            self.logger.debug(event)  # type: ignore

    def __handle_events(self, name: str, desc: str, data: dict) -> None:
        if (
            self.__on
            and name in self.get_on_events()
            and name not in self.get_ignore_events()
        ):
            if name == "ANTI_SPIDER":
                self.__log(f"{Fore.GREEN}【{desc}】{Fore.GREEN} {data['msg']}")
                return
            elif not data.get("act_id"):
                self.__log(f"{Fore.GREEN}【{desc}】{Fore.GREEN} {data}")
                return
            act_id = data.pop("act_id")
            client = data.pop("client")
            instance = data.pop("instance")
            loop = data.pop("event_loop")
            backend = {"AsyncIOBackend": "asyncio", "TrioBackend": "trio"}[
                loop.backend_class.__name__
            ]
            info_str = f"#{Fore.CYAN}{act_id}{Fore.CYAN} {Fore.MAGENTA}[{client} / {instance}]{Fore.MAGENTA} {Fore.YELLOW}<{backend} @ {hash(loop)}>{Fore.YELLOW} "
            log_str = ""
            middle_str = " "
            if name.startswith("WS_"):
                ws_id = data.pop("id")
                middle_str += f"WS #{ws_id} "
            elif name.startswith("DWN_"):
                dwn_id = data.pop("id")
                middle_str += f"DWN #{dwn_id} "
            elif name == "DO_PRE_FILTER":
                action = data.pop("action")
                name = data.pop("name")
                priority = data.pop("priority")
                filter_id = data.pop("filter_id")
                log_str = f"{Fore.GREEN}{desc}{Fore.GREEN} [{Fore.CYAN}{filter_id}{Fore.CYAN}] {action}() <- {name} / {Fore.CYAN}{priority}{Fore.CYAN}"
            elif name == "DO_POST_FILTER":
                action = data.pop("action")
                name = data.pop("name")
                priority = data.pop("priority")
                filter_id = data.pop("filter_id")
                log_str = f"{Fore.GREEN}{desc}{Fore.GREEN} [{Fore.CYAN}{filter_id}{Fore.CYAN}] {action}() <- {name} / {Fore.CYAN}{priority}{Fore.CYAN}"
            elif name == "DELEGATE":
                destination_client = data.pop("destination_client")
                destination_instance = data.pop("destination_instance")
                log_str = f"{Fore.GREEN}{desc}{Fore.GREEN} --> [{Fore.MAGENTA}{destination_client} / {destination_instance}{Fore.MAGENTA}]"
            log_str = log_str or f"{Fore.GREEN}{desc}{Fore.GREEN}: {data}"
            self.__log(info_str + middle_str + log_str)


request_log = RequestLog()
"""
请求日志支持，默认支持输出到指定 I/O 对象。

可以添加更多监听器达到更多效果。

Logger: request_log.logger (logging.Logger)

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

Logger: request_log.logger (logging.Logger)

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
