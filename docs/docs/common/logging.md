# 日志

```python
from bilibili_api import request_log
```

模块提供基于 `logging` 的请求日志支持，同时支持用户代码对日志信息的监听。

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

## 请求日志是如何工作的？

`request_log` 本质为 `AsyncEvent`，即发布-订阅模式异步事件类，因此可以通过 `AsyncEvent.on` 设置相关事件发送后的回调。

> `request_log` 比较特殊，其**不支持异步函数回调**，也不支持运行**阻塞同步函数**。

在模块中，日志输出信息先经过 `AsyncEvent.dispatch` 发送，再传入到模块的默认回调函数 (`request_log.__handle_events`) 中，回调函数将调用 `request_log.logger` (`logging.Logger` 实例，命名为 `bilibili-api-request`) 输出日志信息。

实际上，`set_on` 设置为 `False` 只会禁用模块的默认回调函数，`set_on_events` 和 `set_ignore_events` 的过滤也是在模块的默认回调函数中进行。因此，对这些选项进行任何的设置，都不会影响到 `AsyncEvent` 与其他回调函数的正常发布-订阅流程。

此处举一个使用 `request_log.on` 进行回调的例子。部分用户使用 `loguru` 作为日志，这里我们就对 `loguru` 进行一下兼容。

``` python
from loguru import logger

# 先把默认的 logging.Logger 输出禁用，这样 logging 就不会打印任何信息了。
# 其实 request_log 默认情况下就是禁用了 logging 日志输出的
request_log.set_on(False)

# 再绑定回调
@request_log.on("__ALL__")
def __handle_events(data: dict) -> None:
    evt = data["name"]
    desc, real_data = data["data"]
    if evt == "ANTI_SPIDER":
        logger.info(f"【{desc}】{real_data['msg']}")
        return
    elif not real_data.get("act_id"):
        logger.info(f"{desc}: {real_data}")
        return
    act_id = real_data.pop("act_id")
    client = real_data.pop("client")
    instance = real_data.pop("instance")
    loop = real_data.pop("event_loop")
    backend = {"AsyncIOBackend": "asyncio", "TrioBackend": "trio"}[
        loop.backend_class.__name__
    ]
    info_str = f"#{act_id} [{client}/{instance}] <{backend}@{hash(loop)}>"
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
        log_str = (
            f"{desc} [{filter_id}] {action}() <- {name}  (priority: {priority})"
        )
    elif evt == "DO_POST_FILTER":
        action = real_data.pop("action")
        name = real_data.pop("name")
        priority = real_data.pop("priority")
        filter_id = real_data.pop("filter_id")
        log_str = (
            f"{desc} [{filter_id}] {action}() -> {name}  (priority: {priority})"
        )
    log_str = log_str or f"{desc}: {real_data}"
    logger.info(info_str + middle_str + log_str)
    # 此处复制了 `request_log.__handle_events` 函数的代码
    # 这样即可完整还原模块默认日志的效果
```
