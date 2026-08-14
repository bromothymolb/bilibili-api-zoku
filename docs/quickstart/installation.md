# 模块安装

欢迎来到快速上手！

相较于 README 中的快速上手，此处将对模块的部分功能展开更详细的介绍。相信阅读完本部分内容后，你将能对模块有一个大致的了解。

整个快速上手共分为七个部分，这里是第一部分——模块安装，其余六个部分均与模块的使用相关。

那么，让我们开始吧。

---

模块目前支持 Python 3.11 及以上版本，请确保你的 Python 版本满足要求。

模块发布在 PyPI 上，使用任意主流包管理器均可安装，下面以 `pip` 为例进行演示。

```shell
pip3 install bilibili-api-zoku

pip3 install bilibili-api-zoku --pre # 安装预发布版本

pip3 install git+https://github.com/bromothymolb/bilibili-api-zoku.git@dev
```

第三行命令用于拉取模块 `dev` 分支的代码进行安装。当模块遇到问题时，通常会先将补丁发布到 `dev` 分支，待稳定后再集中发布到正式版本中。因此，如果你遇到的相关问题已经修复，可以优先安装 `dev` 分支的代码——毕竟正式版本的发布时间并无规律可循。

另外，模块强烈建议所有开发者及时将模块更新到最新版本（大版本更新除外）。

模块安装完成后，还需要**自行安装**一个支持异步的第三方请求库，如 `aiohttp` / `httpx` / `curl_cffi`。

``` zsh
# aiohttp
$ pip3 install aiohttp
$ pip3 install "aiohttp[speedups]" # faster

# httpx
$ pip3 install httpx
$ pip3 install httpx[http2] # http2 support

# curl_cffi
$ pip3 install "curl_cffi"
```

模块通过对第三方请求库进行抽象，提供了对任意异步网络请求库的支持，理论上所有异步网络请求库均可被模块正常调用。模块源代码中已内置对 `curl_cffi`、`aiohttp` 和 `httpx` 的支持，因此以上三个请求库可直接使用。如需使用其他网络请求库，你可能需要自行适配，相关文档请参阅 `进阶` 部分中关于 `BiliAPIClient` 的介绍。

如需指定请求库，可以利用 `select_client` 进行切换。

``` python
from bilibili_api import select_client

select_client("curl_cffi") # 选择 curl_cffi，支持伪装浏览器的 TLS / JA3 / Fingerprint，支持 http2
select_client("aiohttp") # 选择 aiohttp
select_client("httpx") # 选择 httpx，不支持 WebSocket，支持 http2
```

模块支持代理和请求超时设置：

``` python
from bilibili_api import request_settings

request_settings.set_proxy("...")
request_settings.set_timeout(5.0)  # 设置 5 秒超时
```

curl_cffi 支持伪装浏览器的 TLS / JA3 / Fingerprint，但需要手动设置；curl_cffi 和 httpx 支持 HTTP2，同样需要手动设置。

``` python
from bilibili_api import request_settings

request_settings.set("impersonate", "chrome131") # 第二参数数值参考 curl_cffi 文档
# https://curl-cffi.readthedocs.io/en/latest/impersonate/targets.html
request_settings.set("http2", True) # 打开 HTTP2 功能
```
