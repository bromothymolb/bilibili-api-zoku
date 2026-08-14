# 使用 `Video`

视频是哔哩哔哩提供的核心功能，也是模块最早出现的功能。目前模块对视频 API 的支持大多基于 `Video` 类。

先按照如下方式初始化 `Video` 类：

``` python
from bilibili_api import video


async def main() -> None:
    # 1. aid
    v = video.Video(aid=2)
    # 2. bvid
    v = video.Video(bvid="BV1xx411c7mD")
```

`Video` 类可以同时通过 aid 或 bvid 初始化，与此类似的还有 `Bangumi` 类，可通过 ssid 或 media_id 初始化。`Video` 类会自动在 bvid 与 aid 之间互相转换，从而同时获得二者。值得注意的是，这一转换过程通过本地算法完成，因此在实例化后，即可通过同步方法 `get_aid`、`get_bvid` 同时获取传入的和推算出的 aid 及 bvid。对于 `Bangumi` 类，ssid 与 media_id 的互相转换需要额外的网络请求（调用接口），因此其 `get_season_id` 和 `get_media_id` 函数均为异步函数。一般来说，模块中某个函数是否为异步，取决于其内部是否包含网络请求；模块在设计上会尽量避免多余的网络请求（毕竟网络请求存在时间开销），同时也会避免无意义地设置异步函数。

不过，如果仅仅需要 bvid 与 aid 的互相转换，则无需 `video.Video(aid=2).get_bvid()` 或 `video.Video(bvid="BV1xx411c7mD")` 这样的写法——模块根目录下已经暴露了工具函数 `aid2bvid` 和 `bvid2aid`，只需 `from bilibili_api import aid2bvid, bvid2aid` 即可。

显然，实例化 `Video` 并非仅仅为了 aid 与 bvid 的转换，我们还可以在此基础上调用接口，例如获取视频信息：

``` python
async def main() -> None:
    ...
    info = await v.get_info()
    print(info)
```

`v.get_info` 即为获取视频信息的函数，它是一个异步函数，调用后会返回一个协程（`Coroutine`）。前面的 `await` 关键字用于等待协程执行完成并获取结果。有关异步编程更详细的信息，可以阅读 [asyncio 文档](https://docs.python.org/zh-cn/3/library/asyncio.html) 或 [trio 文档](https://trio.readthedocs.io/en/stable/)。二者都是 Python 下的异步 IO 后端，其中 asyncio 是 Python 标准库，使用更为广泛，几乎所有异步库都支持它。模块同时兼容 asyncio 与 trio 两个后端，因此二者皆可使用。若追求更好的兼容性，建议选择 asyncio——例如模块官方支持的三个网络请求库中，目前仅 httpx 支持 trio（curl_cffi 正在兼容 trio，但尚未发布正式版本）。

简单来说，调用异步函数获取结果时，需要在前面加上 `await`。还有很重要的一点：`await` 关键字只能在异步函数（即用 `async def` 定义的函数）内使用，普通同步函数中无法调用 `await`！

不过也有一种办法：模块提供了 `sync` 函数，可以在同步代码中执行协程。例如，既可以在主程序里用 `sync` 执行上面的 `main` 函数，也可以直接执行 `v.get_info`，如下：

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

需要注意的是，`sync` 函数不能在异步函数内调用，此时请直接使用 `await` 获取异步函数的结果。换句话说，`await` 本身保证了异步函数内的代码执行顺序与同步函数一致，让异步代码看起来就像同步代码一样。

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

接下来的部分，我们将尝试进行账号操作。当然，账号操作前需要先登录。

这里先介绍一种通用的登录方法——拷贝 cookies。具体方法和说明请参考[获取 Credential 类所需信息](./docs/common/credential.md)。

这里介绍两个关键 cookies：

- `SESSDATA`: 用于普遍的鉴权，识别用户身份。所有登入操作都需要这个 cookie。
- `bili_jct`: 充当 csrf token，用于账号相关**操作**的鉴权，多见于 `POST` 请求。

例如，获取用户个人信息只需 `SESSDATA`，而给视频点赞则 `SESSDATA` 和 `bili_jct` 二者缺一不可。

以给视频点赞为例，自然需要传入 `SESSDATA` 和 `bili_jct` 两个 cookies，而传入方法就是初始化一个 `Credential` 类。

``` python
from bilibili_api import Credential


credential = Credential(sessdata="xxxxxx", bili_jct="xxxxxx")
```

以上内容在[获取 Credential 类所需信息](./docs/common/credential.md)亦有提及，此处不过多赘述。

接下来需要将凭据类传入 `Video` 类，方法很简单，初始化时传入即可。

``` python
v = video.Video(aid=2, credential=credential)
```

模块中几乎所有支持凭据类的类，都通过 `credential` 字段直接存储凭据类。也就是说，也可以在初始化时不传入 `credential`，之后再通过 `v.credential` 进行设置。虽然这也是一种可行的方法，但在部分场合会失效，并产生意料之外的结果。例如在 `LiveDanmaku`（用于连接直播间的类）上这么做：先调用 `LiveDanmaku().connect`（开始连接直播间），再设置凭据类。直播间开始连接时，模块会向服务器发送携带 cookies 的数据，此时凭据类尚未传入，服务器看到的是匿名用户访问；而之后的连接又传入了凭据类，服务器便能识别出用户身份。前后身份不一致，服务器会直接断开连接。因此，非必要情况下请不要在初始化后手动设置凭据类，而应在类初始化时传入。

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

从这些例子中可以看出部分原因。其一，几乎所有视频操作都需要 bvid 和 credential，若逐个作为参数传给一个个函数，未免有些麻烦；其二，在参数处理上，bvid 和 aid 理应都被接受，有时还需要同时作为请求参数传入接口，若每个函数都编写一段 bvid 与 aid 的转换逻辑，未免太过繁琐。使用类可以将一个视频对象具象化，并对其属性（如 bvid 和 aid）进行集中管理，这样既能简化模块架构，又能方便用户使用。这一优势在 `Bangumi` 类上体现得尤为明显。

当然，模块也并非完全采用面向对象设计。部分子模块仍然提供多个函数而非单个类，例如 `video_zone` 就提供了多个函数，用于查询视频分区信息。
