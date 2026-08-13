# 请求配置

```python
from bilibili_api import request_settings
```

模块支持一系列的请求配置项，这些设置将由模块传递到第三方库的会话中得以应用。

因此，使用部分配置项功能时，亦需要考虑第三方库的实际情况。例如，在 Windows 上启用 `aiohttp` 的代理功能，`asyncio` 需要使用 `SelectorEventLoop`。

## 配置项

| name | type | default | curl_cffi | aiohttp | httpx |
| ---- | ---- | ------- | --------- | ------- | ----- |
| proxy | str | ` ` | ✅ | ✅ | ✅ |
| timeout | float | `30.0` | ✅ | ✅ | ✅ |
| verify_ssl | bool | `True` | ✅ | ✅ | ✅ |
| trust_env | bool | `True` | ✅ | ✅ | ✅ |
| http2 | bool | `False` | ✅ | ❌ | ✅ |
| impersonate | str | ` ` | ✅ | ❌ | ❌ |

## 代理

```python
# 1. 通过 request_settings 设置
request_settings.set_proxy("http://example.com")
# 2. 通过 Credential 传入
cred = Credential(..., proxy="http://example.com")
func(..., credential=cred)
```

## 请求超时设置

```python
request_settings.set_timeout(1.0)
```

## 设置是否验证 ssl / 使用环境变量

> 例如：可以使用环境变量 `HTTP_PROXY` `HTTPS_PROXY` 为应用程序设置代理。

```python
request_settings.set_verify_ssl(False)
request_settings.set_trust_env(True)
```

## 额外设置

针对不同的第三方请求库，模块会有各不相同的额外设置。为了对这些字段进行处理，`request_settings` 提供 `set` 函数。

例如，设置 `curl_cffi` 伪装的浏览器：

``` python
request_settings.set("impersonate", "chrome131")
```

`curl_cffi` `httpx` 可以启用 `http2` 设置，进行 HTTP2 请求：

``` python
request_settings.set("http2", True)
```

`set` 函数同样支持上面出现过的 `proxy` `timeout`。

``` python
# 等价
request_settings.set_proxy("http://example.com")
request_settings.set("proxy", "http://example.com")
```

## 获取设置

``` python
# 获取 proxy
proxy = request_settings.get_proxy()
proxy = request_settings.get("proxy")
proxy = request_settings.all()["proxy"]
# 获取所有设置
all_settings = request_settings.all()
```
