# 模块的安装与依赖相关

## 模块的安装

模块目前支持 Python 3.11 及以上的版本，请确保 Python 的版本足够。

模块包体发布在 PyPI 上，使用任意主流包管理器均可安装模块，下面使用 `pip` 进行演示。

```shell
pip3 install bilibili-api-zoku

pip3 install bilibili-api-zoku --pre # 安装预发布版本

pip3 install git+https://github.com/bromothymolb/bilibili-api-zoku.git@dev
```

第三行代码可以拉取模块 `dev` 分支代码安装。模块在遇到问题时往往会先一步将补丁发布在 `dev` 分支，再集中发布到一个版本中，如遇到相关问题且已经解决，可优先拉取 `dev` 分支代码安装，毕竟发布版本的时间没有任何规律可循。

模块目前并未锁定任何依赖的版本，以方便依赖的管理。为保证模块正常运行，建议用户将所有依赖模块的大版本号与最新大版本号保持一致。模块所有依赖如下：

``` plaintext
PyJWT
anyio
beautifulsoup4
brotli
chompjs
colorama
frozendict
lxml
pillow
pycryptodomex
pyyaml
qrcode
qrcode_terminal
yarl
```

> 模块稳定性没有保证，建议所有开发者除非大版本更新外，及时保证模块更新到最新版本，甚至，保持本地模块代码和 `dev` 分支代码同步。

## 模块其他依赖的安装

模块默认依赖中未包含网络请求库，需要用户自行安装。模块自带对以下三个网络请求库的支持：`aiohttp` `curl_cffi` 和 `httpx`。

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

如果硬要选择一个请求库，论功能选择 `curl_cffi`，论速度选择 `aiohttp`，论稳定性选择 `httpx`。不妨自行尝试，选择最适合项目的请求库。

如果想要指定请求库，可以利用 `select_client` 进行切换。

``` python
from bilibili_api import select_client

select_client(
    "curl_cffi"
)  # 选择 curl_cffi，支持伪装浏览器的 TLS / JA3 / Fingerprint，支持 http2
select_client("aiohttp")  # 选择 aiohttp
select_client("httpx")  # 选择 httpx，不支持 WebSocket，支持 http2
```

## 请求转发

模块依赖第三方请求库以下功能：http 请求、流式下载和 WebSocket 连接。诸如 `httpx` 等请求库不支持其中的全部功能。这种情况下可以使用请求转发，以保证模块正常运作。

例如 `httpx` 不支持 WebSocket 请求，但 `aiohttp` 支持，通过请求转发，可以让 `httpx` 收到 WebSocket 请求后，把任务交给 `aiohttp` 完成。整个过程会把原来 `httpx` 的任务转发至 `aiohttp`，让 `aiohttp` 代替 `httpx` 进行 WebSocket 连接。

请求转发需要指定目标请求客户端和转发范围，此处以上述情况为例，将 WebSocket 请求转发至 `aiohttp`:

``` python
delegate(delegate_type=DelegateType.WEBSOCKET, destination_client="aiohttp")
```

## 浏览器指纹支持

curl_cffi 支持伪装浏览器的 TLS / JA3 / Fingerprint，但需要手动设置。curl_cffi 和 httpx 支持 HTTP2，也需要手动设置。

``` python
from bilibili_api import request_settings

request_settings.set("impersonate", "chrome131")  # 第二参数数值参考 curl_cffi 文档
# https://curl-cffi.readthedocs.io/en/latest/impersonate/targets.html
request_settings.set("http2", True)  # 打开 HTTP2 功能
```

模块同时支持基于 `fingerprint-generator` 的对浏览器指纹的伪装，可以配合 `curl_cffi` 库对 TLS/JA3 的伪装一同使用。可以通过以下方式对上面两个模块同时进行安装：

``` zsh
$ pip3 install "bilibili-api-zoku[fingerprint]"
# manual installation
$ pip3 install fpgen
$ pip3 install "curl_cffi"
```

使用以下方式即可在模块中启用 `fingerprint-generator`：

``` python
from bilibili_api import bili_settings, get_bili_headers

bili_settings.set_enable_fpgen(True)
bili_settings.set_fpgen_args(
    {
        "strict": True,
        "browser": "Chrome",
        "os": "Windows",
    }
)

# import fpgen

# fpgen.generate(
#     strict=True,
#     browser="Chrome",
#     os="Windows",
# )
```

有关 `fingerprint-generator` 的安装和使用，请参考 <https://github.com/scrapfly/fingerprint-generator>。

> 目前哔哩哔哩风控暂无必要启用浏览器指纹或 TLS/JA3 伪装，可自行考虑是否启用相关功能。
