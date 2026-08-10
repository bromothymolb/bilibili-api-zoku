# 模块安装

欢迎来到快速上手！

相较于 README 中的快速上手，此处将更加详细地对模块部分功能进行展开，相信阅读完此部分内容，你将可以对模块拥有大致的理解。

整个快速上手分为了七个部分，这里是快速上手的第一部分，自然是模块的安装部分了，剩下的六个部分则都与模块的使用相关。

那就开始吧。

---

模块目前支持 Python 3.11 及以上的版本，请确保 Python 的版本足够。

模块包体发布在 PyPI 上，使用任意主流包管理器均可安装模块，下面使用 `pip` 进行演示。

```shell
pip3 install bilibili-api-zoku

pip3 install bilibili-api-zoku --pre # 安装预发布版本

pip3 install git+https://github.com/bromothymolb/bilibili-api-zoku.git@dev
```

第三行代码可以拉取模块 `dev` 分支代码安装。模块在遇到问题时往往会先一步将补丁发布在 `dev` 分支，再集中发布到一个版本中，如遇到相关问题且已经解决，可优先拉取 `dev` 分支代码安装，毕竟发布版本的时间没有任何规律可循。

另外，模块强烈建议所有开发者，除非大版本更新外，及时保证模块更新到最新版本。

模块安装完成后，仍需要**自行安装**一个支持异步的第三方请求库，如 `aiohttp` / `httpx` / `curl_cffi`。

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

模块通过抽象第三方请求库的方法，提供了对任意异步网络请求库的支持，因此理论上所有的异步网络请求库，模块都可以正常对其进行调用。模块源代码中已经实现了对 `curl_cffi` `aiohttp` 和 `httpx` 的支持，因此以上三个异步请求库可直接调用。如果需要使用其他网络请求库，你可能需要自行适配，相关文档请阅读 `进阶` 部分中有关 `BiliAPIClient` 的部分。

如果想要指定请求库，可以利用 `select_client` 进行切换。

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

curl_cffi 支持伪装浏览器的 TLS / JA3 / Fingerprint，但需要手动设置。curl_cffi 和 httpx 支持 HTTP2，也需要手动设置。

``` python
from bilibili_api import request_settings

request_settings.set("impersonate", "chrome131") # 第二参数数值参考 curl_cffi 文档
# https://curl-cffi.readthedocs.io/en/latest/impersonate/targets.html
request_settings.set("http2", True) # 打开 HTTP2 功能
```
