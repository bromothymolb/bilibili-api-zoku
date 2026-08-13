# 使用 `Video`

视频是哔哩哔哩提供的核心功能，也是模块最早出现的功能。目前模块对视频 API 的支持大多数基于 `Video` 类。

先按照如下方式初始化 `Video` 类：

``` python
from bilibili_api import video


async def main() -> None:
    # 1. aid
    v = video.Video(aid=2)
    # 2. bvid
    v = video.Video(bvid="BV1xx411c7mD")
```

此处 `Video` 类可以同时通过 aid 或 bvid 进行初始化，与此类似的还有 `Bangumi` 类，可以通过 ssid 或 media_id 进行初始化。`Video` 类会自动将 bvid 和 aid 互相进行转换，这样即可同时获得 bvid 和 aid，值得注意的是这个过程通过本地算法实现，因此在实例化后可通过调用同步方法 `get_aid` `get_bvid` 同时获取传入的和推算的 aid 及 bvid。如果是 `Bangumi` 类，ssid 和 media_id 互相转换需要额外进行网络请求（调用接口），因此其设计的 `get_season_id` 和 `get_media_id` 函数均为异步函数，模块中异步函数设置一般取决于其内部是否存在网络请求，而模块设计层面也将尽量避免多余的网络请求，毕竟网络请求存在时间开销，当然，也会避免无意义地设置异步函数。

不过，如果单单只需要把 bvid 和 aid 互相转换的话，无需 `video.Video(aid=2).get_bvid()` 或 `video.Video(bvid="BV1xx411c7mD")`，模块根目录下已经暴露了其中的工具函数 `aid2bvid` 和 `bvid2aid`，仅需 `from bilibili_api import aid2bvid, bvid2aid` 即可。

显然，这边实例化 `Video` 并非单单为了 aid 和 bvid 的转化，我们可以在此基础上调用接口，例如获取视频信息：

``` python
async def main() -> None:
    ...
    info = await v.get_info()
    print(info)
```

`v.get_info` 即为获取视频信息的函数，为异步函数，其将返回一个协程(`Coroutine`)。前面的 `await` 关键词用于等待协程执行完成并获取结果。有关异步编程更详细的信息，可以阅读 [asyncio 文档](https://docs.python.org/zh-cn/3/library/asyncio.html) 或 [trio 文档](https://trio.readthedocs.io/en/stable/)，二者都是 Python 下的异步 IO 后端，前者是 Python 标准库，使用更为广泛，几乎所有异步的库都支持 asyncio。模块同时兼容 asyncio 和 trio 两个后端，因此使用哪个都行，建议如果想要追求更好的兼容性，使用 asyncio 是更好的选择，例如模块官方支持的三个网络请求库中，仅 httpx 支持 trio (目前 curl_cffi 正在兼容 trio 中，但尚未发布正式版本)。

简单来说，就是调用异步函数获取结果，前面要加上 `await`，还有个很重要的一点是，`await` 关键词仅限异步函数内使用，就是使用 `async def` 定义的函数，正常同步函数内无法调用 `await`！

不过有一种方法，模块提供 `sync` 函数，可以在同步代码中执行协程，例如可以在主程序中用 `sync` 执行上面的 `main` 函数，亦可直接执行上面的 `v.get_info` 函数，如下：

``` python
from bilibili_api import sync


# 1. 执行 main 函数
async def main() -> None: ...


if __name__ == "__main__":
    sync(main())

# 2. 执行上面的 v.get_info
v = video.Video(aid=2)
info = sync(v.get_info())
print(info)
```

当然，如果你已经看过了 asyncio 的文档，就会发现下列语句和 `sync` 函数有同样的效果：

``` python
import asyncio


async def main() -> None: ...


if __name__ == "__main__":
    asyncio.run(main())
```

需要注意的是，`sync` 函数不能在异步函数内调用，请直接使用 `await` 语句获取异步函数结果。或者说，`await` 语句本身就承担了保证异步函数内代码执行顺序和同步函数一致的功能，或是说，让异步函数看着像同步代码一样。

最后附上完整代码：

``` python
import asyncio
from bilibili_api import video


async def main() -> None:
    # 实例化 Video 类
    v = video.Video(bvid="BV1uv411q7Mv")
    # 获取信息
    info = await v.get_info()
    # 打印信息
    print(info)


if __name__ == "__main__":
    asyncio.run(main())
```

---

接下来的部分，我们将尝试账号操作，自然，账号操作前需要登录。

这里先介绍一种普遍的登录方法，即拷贝 cookies。方法和说明请参考[获取 Credential 类所需信息](./docs/common/credential.md)。

这边介绍两个关键 cookies：

- `SESSDATA`: 用于普遍的鉴权，识别用户身份。所有登入操作都需要这个 cookie。
- `bili_jct`: 充当 csrf token，用于账号相关**操作**的鉴权，多见于 `POST` 请求。

例如获取用户个人信息，只需要 `SESSDATA` 即可，而给视频点赞，则 `SESSDATA` 和 `bili_jct` 都需要。

以为视频点赞举例，此处自然需要传入 `SESSDATA` 和 `bili_jct` 两个 cookies，传入方法即为初始化一个 `Credential` 类。

``` python
from bilibili_api import Credential


credential = Credential(sessdata="xxxxxx", bili_jct="xxxxxx")
```

以上内容在[获取 Credential 类所需信息](./docs/common/credential.md)亦有提及，此处不过多赘述。

接下来需要将凭据类传入 `Video` 类，方法很简单，初始化时传入即可。

``` python
v = video.Video(aid=2, credential=credential)
```

模块几乎所有的类，凡是支持凭据类的，都存在 `credential` 字段直接存储凭据类，也就是说，亦可以在初始化的时候不传入 `credential`，而后使用 `v.credential` 设置凭据类。诚然这是一种方法，但是在部分场合这种方法会失效，产生一些意料之外的结果。例如在 `LiveDanmaku` (用于连接直播间的类) 上这么做，先 `LiveDanmaku().connect` (开始连接直播间) 再设置凭据类，直播间开始连接时会向服务器发送数据，会携带 cookies，此时没有传入凭据类，因此服务器看到的实际上是匿名用户访问，之后的连接传入了凭据类，服务器上又能识别到用户访问，这种情况下服务器会直接断开连接。因此，非必要请不要手动设置凭据类，而是在类初始化时传入。

只要传入了凭据类，剩下的一切都很简单，仅需调用异步方法 `v.like`。

``` python
await v.like(True)
# 传入参数控制预期点赞状态，True 为点赞，False 为取消点赞
```

完整代码如下：

``` python
import asyncio
from bilibili_api import video, Credential


async def main() -> None:
    # 实例化 Credential 类
    credential = Credential(sessdata=SESSDATA, bili_jct=BILI_JCT)
    # 实例化 Video 类
    v = video.Video(bvid="BVxxxxxxxx", credential=credential)
    info = await v.get_info()
    print(info)
    # 给视频点赞
    await v.like(True)


if __name__ == "__main__":
    asyncio.run(main())
```

此处可以思考，为什么模块会使用类进行视频相关操作，而非直接提供一个个函数？

从这些例子中可以看出部分原因，一是几乎所有视频操作都需要 bvid 和 credential，一个个作为参数传入一个个函数还是有些麻烦。二是对传入参数的处理，bvid 和 aid 理应都被接受，有时也都需要作为请求参数传入接口，此时若每一个函数都编写一段逻辑，处理 bvid 和 aid 的转化，未免太过繁琐。使用类，可以将一个视频对象具像化，也可以将其属性，如 bvid 和 aid 进行集中的管理，这样既能简化模块架构，又能方便用户使用。这种优势在 `Bangumi` 类上体现得尤为明显。

当然，模块也并非完全像 `Video` 类一样面向对象设计，部分子模块仍然提供多个函数，而非一个类，例如 `video_zone` 就是提供多个函数，用于查询视频分区信息。
