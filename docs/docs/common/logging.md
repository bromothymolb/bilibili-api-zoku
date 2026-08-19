# 日志

```python
from bilibili_api import request_log
```

模块同时提供基于标准库 [logging](https://docs.python.org/3/library/logging.html) 和第三方库 [Loguru](https://loguru.readthedocs.io/en/stable/) 的日志支持，同时支持用户代码对日志信息的监听。

考虑到依赖原因，模块默认使用 `logging` 作为日志库，如需启用 `loguru` 需要提前设置：

``` python
from bilibili_api import bili_settings

bili_settings.set_enable_loguru(True)
```

## 1. 请求日志

### 开启请求日志

```python
request_log.set_on(True)
```

### 设置请求日志

``` python
request_log.set_on_events(["REQUEST"]) # 仅当有 http 请求时打印日志
request_log.set_ignore_events(["API_REQUEST", "API_RESPONSE"]) # 去除 Api 类相关的信息
```

`request_log` 默认只打印以下类型信息：

- API_REQUEST: `Api` 类发起请求，了解 `Api` 类相关信息请前往 `根模块类与函数`。
- API_RESPONSE: `Api` 类获得结果，了解 `Api` 类相关信息请前往 `根模块类与函数`。
- ANTI_SPIDER: 反爬虫相关信息。
- WS_CREATE: WebSocket 开始连接。由 [`BiliAPIClient`](../advance/client.md) 发出。
- WS_RECV: WebSocket 收到信息。由 [`BiliAPIClient`](../advance/client.md) 发出。
- WS_SEND: WebSocket 发送信息。由 [`BiliAPIClient`](../advance/client.md) 发出。
- WS_CLOSE: WebSocket 关闭连接。由 [`BiliAPIClient`](../advance/client.md) 发出。

`request_log` 同时提供以下信息：

- REQUEST: HTTP 请求。由 [`BiliAPIClient`](../advance/client.md) 发出。
- RESPONSE: HTTP 响应。由 [`BiliAPIClient`](../advance/client.md) 发出。
- DWN_CREATE: 新建下载。由 [`BiliAPIClient`](../advance/client.md) 发出。
- DWN_PART: 部分下载。由 [`BiliAPIClient`](../advance/client.md) 发出。
- DWN_CLOSE: 结束下载。由 [`BiliAPIClient`](../advance/client.md) 发出。
- CLOSE: 关闭第三方请求库会话。由 [`BiliAPIClient`](../advance/client.md) 发出。
- DO_PRE_FILTER: 执行前置[过滤器](../advance/filter.md)。
- DO_POST_FILTER: 执行后置[过滤器](../advance/filter.md)。
- DELEGATE: 执行请求转发。(见 [安装与依赖相关](../common/installation.md) 或 [过滤器](../advance/filter.md))

可以通过 `request_log.get_all_events()` 获取所有的信息类型。

模块日志输出基于第三方库 [Loguru](https://loguru.readthedocs.io/en/stable/) 实现，可以使用 Loguru 的功能对模块日志输出加以设置。

``` python
from loguru import logger

log_format: str = (
    "<g>{time:MM-DD HH:mm:ss}</g> "
    "[<lvl>{level}</lvl>] "
    "<c><u>{name}</u></c> | "
    "{message}"
)
logger.remove()
logger.add(sys.stderr, format=log_format)

logger.add("test.log", format=log_format)  # 将日志输出到文件
```

### 请求日志是如何工作的？

`request_log` 本质为 `AsyncEvent`，即发布-订阅模式异步事件类，因此可以通过 `AsyncEvent.on` 设置相关事件发送后的回调。

> `request_log` 比较特殊，其**不支持异步函数回调**，也不支持运行**阻塞同步函数**。

在模块中，日志输出信息先经过 `AsyncEvent.dispatch` 发送，再传入到模块的默认回调函数 (`request_log.__handle_events`) 中，回调函数将调用 `loguru.logger` 输出日志信息。

实际上，`set_on` 设置为 `False` 只会禁用模块的默认回调函数，`set_on_events` 和 `set_ignore_events` 的过滤也是在模块的默认回调函数中进行。因此，对这些选项进行任何的设置，都不会影响到 `AsyncEvent` 与其他回调函数的正常发布-订阅流程。

例如，可以将 `set_on` 设为 `False` 后，绑定以下回调，会发现仍将有日志输出。

``` python
request_log.set_on(False)

@request_log.on("__ALL__")
def log(event: dict) -> None:
    print(event["name"], event["data"])
```

## 2. `AsyncEvent` 日志

模块以下异步事件类提供日志：`live.LiveDanmaku` `session.Session` `video.VideoOnlineMonitor`，这些日志也同时支持 logging 和 loguru。以上三个类均提供初始化参数 `debug`，用于设置是否开启 `debug` 信息。

如果使用 logging，以上三个类将使用名称为 `str(AsyncEvent())` 的日志实例。例如，`dm = live.LiveDanmaku(xxx)` 的日志实例名称为 `str(dm)`，即 `LiveDanmaku(LiveRoom(room_display_id=xxx, real_id=yyy))`，这个名称用于传入 `logging.getLogger` 函数，可获取对应的日志实例。模块将设置日志实例的日志等级，以过滤掉 `DEBUG` 信息，如果参数设置为 `debug=False`。

如果使用 loguru，模块将在日志信息前添加前缀，即 `str(dm)`，用于和其他消息区分，此时模块过滤 `DEBUG` 信息的方法是，检查 `debug` 参数，若其为 `False`，则不会调用 `logger.debug`。

默认情况下，无论如何，上面三个类都将在 `stderr` 输出 `INFO` 日志信息，如果需要关闭输出，可以设置初始参数 `log=False`，原理是不调用任何输出日志的函数，与 loguru 下过滤 `DEBUG` 信息的方法相同。
