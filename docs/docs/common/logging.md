# 日志

```python
from bilibili_api import request_log
```

模块提供基于 [Loguru](https://loguru.readthedocs.io/en/stable/) 的请求日志支持，同时支持用户代码对日志信息的监听。

## 开启请求日志

```python
request_log.set_on(True)
```

## 设置请求日志

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

## 请求日志是如何工作的？

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
