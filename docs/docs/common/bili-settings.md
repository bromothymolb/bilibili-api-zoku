# 模块配置

```python
from bilibili_api import bili_settings
```

模块配置和请求配置类似，但模块配置具体实现由模块完成，而非第三方请求库完成。

| configuration | type | default | description |
| ------------- | ---- | ------- | ----------- |
| `wbi_retry_times` | `int` | `3` | WBI 重试次数 |
| `enable_auto_buvid` | `bool` | `True` | 允许模块自动请求生成 buvid |
| `enable_bili_ticket` | `bool` | `False` | 允许模块自动请求生成 bili_ticket |
| `enable_buvid_global_persistence` | `bool` | `False` | 允许模块使用统一的全局 buvid |
| `enable_bili_ticket_global_persistence` | `bool` | `False` | 允许模块使用统一的全局 bili_ticket |
| `enable_fpgen` | `bool` | `False` | 是否启用 `fpgen` 进行指纹伪装 |
| `fpgen_args` | `dict` | `{}` | 传入 `fpgen.generate` 的 keyword args 参数 |

## 设置 `wbi` 请求重试次数上限

> `wbi` 为 B 站对用户相关 API 采取的一个反爬虫措施，需要传入一些经过加密的参数，否则请求可能会被驳回。每次计算此参数的之后，这个值有失效可能，届时模块会 **自动重新计算** 这个参数新的值，进行重试。当重试次数超过一定次数 (`settings.wbi_retry_times`) 后，模块将发出报错。
> 手动重新计算可用 `recalculate_wbi`

```python
bili_settings.set_wbi_retry_times(10) # defaults to 3

from bilibili_api import recalculate_wbi
recalculate_wbi() # 重新计算 wbi 参数
```

## 设置 `buvid` 自动生成

> `buvid` 是访问 B 站时可能需要提供的 cookie 系列，分为 `buvid3` 和 `buvid4` 字段。如果不提供部分接口可能受限。模块在用户未提供 credential 或 credential 中无 `buvid3` 或 `buvid4` 字段时，会自动生成一组 `buvid`，但过程中需要进行网络请求，此功能可通过这项设置关闭。

```python
bili_settings.set_enable_auto_buvid(False)
```

## 设置 `bili_ticket` 自动生成

> `bili_ticket` 是访问 B 站时可能需要提供的 cookie 系列，分为 `bili_ticket` 和 `bili_ticket_expires` 字段。提供 `bili_ticket` 有时可以达到一些玄学效果。默认禁用，可以通过此项设置启用。
> `bili_ticket` 过期后模块会 **自动重新计算**。

```python
bili_settings.set_enable_bili_ticket(True)
```

## 全局反爬虫 cookies

模块中对 `buvid` 和 `bili_ticket` 的维护过程在 `Credential` 类中进行。即，对每一个 `Credential` 来说，其 `buvid` 和 `bili_ticket` 是和其他对象完全独立的。例如，如果你有 2 个凭据类，最终就会获得两份不同的 `buvid` 和 `bili_ticket`。

而在模块 v18 之前，所有未提供相关 cookies 的凭据类共享一份全局的 `buvid` 和 `bili_ticket`。这样即使有 2 个凭据类，也会共享一份 `buvid` 和 `bili_ticket`。在 v18 之后，只需要使用下面的设置即可回到 v18 以前的模式：

``` python
bili_settings.set_enable_buvid_global_persistence(True)
bili_settings.set_enable_bili_ticket_global_persistence(True)
```

## `fingerprint-generator` 相关

可以使用 `enable_fpgen` 启用模块对 `fpgen` 的支持：

``` python
bili_settings.set_enable_fpgen(True)
```

模块将调用 `fpgen.generate` 生成浏览器指纹，参数使用 `bili_settings.get_fpgen_args`。显然，此处的参数可以使用 `set_fpgen_args` 设置。

``` python
bili_settings.set_fpgen_args({...})
```
