# 快速上手

- [模块安装](#模块安装)
- [使用 `Video`](#使用-video)
- [使用 `rank` `hot`](#使用-rank-hot)
- [使用 `AsyncEvent`](#使用-asyncevent)
- [使用 `login_v2`](#使用-login_v2)
- [下载视频](#下载视频)
- [后端请求转发接口](#后端请求转发接口)

## 模块安装

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

## 使用 `Video`

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

## 使用 `rank` `hot`

承接上文，接下来要介绍的是 `rank` `hot` 模块，用于查询“热门”页面信息。“热门”页面通常是排行榜，还有入站必刷视频的列表。此处模块提供的并非一个个类，而是大量的函数。

打开[哔哩哔哩热门页面](https://www.bilibili.com/v/popular/all?spm_id_from=333.1007.0.0)，可以看到其分为五个部分：综合热门、每周必看、入站必刷、排行榜及全站音乐榜。

先从热门和入站必刷视频看起。对应函数在 `hot` 中，分别是 `get_hot_videos` 和 `get_history_popular_videos`。

### 1. 入站必刷视频

``` python
from bilibili_api import hot, sync


async def main() -> None:
    history = await hot.get_history_popular_videos()
    print(history)


sync(main())
```

以上代码运行后即可输出入站必刷列表的详情，但这个数据是未经处理的接口数据。如果说存在收集全部视频的标题或 bvid 等信息的具体需求，仍需进一步研究返回的数据结构，并对其加以处理。

事实上，大多数情况下调用完模块均需要先分析数据结构，再进一步编写代码实现需求。包括前文的视频信息获取，返回的字典也存在不同字段，表示了不同的信息。除了此处之外，后文[下载视频](#下载视频)处仍需要进行类似的数据结构分析。

其实，这里的数据结构还是相当好理解的，仅需格式化输出 (`pprint.pprint`) 后观察即可。字典 `title` 字段即“入站必刷”，列表在 `list` 字段，每一项是一个字典，对应一个视频，字典的 `aid` `bvid` 字段即 aid 和 bvid，`title` 字段为标题，`pic` 字段为封面图片链接，`stat` 字段又是一个字典，包含了视频播放量、弹幕、投币、评论等信息，`tidv2` `pid_v2` 字段对应视频分区信息，此处分区是已经重构过的新版分区，模块中对应 `video_zone_v2`，可以尝试调用 `video_zone_v2` 函数查询 `tidv2` 对应的分区名称，看看能否和 `tnamev2` 字段对应上。

接口返回的数据结构实际上可以使用类型注解表示，大多数编程语言均支持类型注解，包括 Python，但模块目前基本不提供类型注解，一是接口返回的数据结构十分灵活，不适合大规模跟进与维护，二是 Python 类型检查相对宽松，没有这种必要。但有的时候进行类型注解，可以方便开发者开发、代码的 debug。将来若有可能，bilibili-api 也将引入部分接口返回值的详细类型注解。

目前亦有文档对接口的返回值结构进行了深入的研究，例如 bilibili-API-collect，有需要可以查找对应接口文档以供参考（bilibili-api 部分函数注释中已经附加了 bilibili-API-collect 对应页面链接）。

回到正题，把握了数据结构后就能进行进一步操作了，这边就简单地打印标题分区 bvid 草草了事了。

``` python
from bilibili_api import hot, sync


async def main() -> None:
    history = await hot.get_history_popular_videos()
    for v in history["list"][::-1]:
        print(v["bvid"], "[", v["tnamev2"], "]", v["title"])


sync(main())
```

``` plaintext
BV1es41197hA [ 同人动画 ] 【2016拜年祭单品】婕纶二重奏
BV1Sx411T7L3 [ 原创音乐 ] 【世界版】Blessing【原创PV】
BV1fs411k7Kj [ 音乐现场 ] 感觉身体被掏空by彩虹室内合唱团
BV1tx411P7N4 [ 动漫剪辑 ] 冰雪奇缘X守护者联盟【误解向】Frozen Guardian
BV1Sx41117dD [ 原创音乐 ] 【2017拜年祭单品】万神纪【星尘原创曲】
BV1ts411D7mf [ 演奏 ] 【Animenz】动漫钢琴演奏合集
BV1Kx411y7TJ [ 宅舞 ] 【2017 Bilibili Dancing Festival 主题曲】交织together
BV1Ys411H7QK [ 其他游戏 ] 【敖厂长10】烂尾的游戏冒险(雅达利寻剑)
BV1hx411w7MG [ 翻唱 ] 【拜年祭】【合唱】only my bilibili
BV1es41197ai [ VOCALOID ] 【2016拜年祭单品】九九八十一【乐正绫 feat.洛天依】
BV1dx411P79c [ 射击游戏 ] 【燃向】得入暴雪门，无悔游人生（更新OW归来版）
BV1fx411c7v6 [ 音MAD ] 【BILIBILI大合作】无限循环祭
BV1Mt411D73n [ 影视剪辑 ] 【2018】年度影视混剪 Ready Story 2018
BV1Kt41147o3 [ 街舞 ] 【桃核x麦麥籽】改革春风吹满地！念诗之王x原创编舞x鬼畜第二弹
BV1cb411V7Lm [ 影视解读 ] 《复联4》前21部漫威电影，完整的时间线剧情大串联！
BV1cs411S7DX [ MV ] 燃起来！同步率爆表！当《西游记之大圣归来》MV遇到戴荃老师原创歌曲《悟空》
BV1Fx411w7GK [ 动漫剪辑 ] 【魂】银魂——武士之魂
BV1Ds411m7c5 [ 沙盒类 ] 【国际网骗】模仿7国口音玩H1Z1
BV1YW411n7aW [ 影视剪辑 ] 【高燃/混剪/漫威/1080P】全宇宙最棒的团队：复仇者联盟
BV1nx411F7fM [ MV ] 雪姨迷幻电音首单MV《你有本事抢男人》
BV1Js411Z7Nq [ 翻唱 ] 【北大力南逸峰】我的故事（完整版）
BV11p411o73u [ 影视解读 ] 电影最TOP 100：永远的喜剧之王！星爷周星驰电影全盘点
BV1rs411S736 [ MV ] 【去违和】周杰伦献唱核爆神曲aLIEz 与霍元甲的Mashup版本 aHUOz！
BV1Vs411y7TM [ 影视综合 ] 【小明v老王】大忠若奸
BV1ix411c7Ye [ 动漫剪辑 ] 【穿越】绿光
BV1Bx411c7hB [ 动漫剪辑 ] 危险的黑子
BV1xx411c79H [ 动漫剪辑 ] 【東方】Bad Apple!! ＰＶ【影絵】
BV1Dt411r7Tv [ 动物综合·二创 ] 我不仅开口说话和你吵架，还要把你周围的空气吃干净让你窒息...
BV1nx411F7Jf [ 动漫剪辑 ] 秋山澪与折木奉太郎的爱情故事 // Our Tapes
BV1Xs411X7wh [ 鬼畜调教 ] 【矢泽妮可】妮可酱，给我来一发最带感的Niconiconi！
BV1Js411o76u [ 动漫剪辑 ] 【炮姐/AMV】我永远都会守护在你的身边！
BV1Yx411A7wM [ 鬼畜剧场 ] 【成龙】我的洗发液
BV1px411N7Yd [ 动漫剪辑 ] 【火影忍者】用战斗来祭奠这个世界 ！！
BV1EW41167Yv [ MOBA游戏 ] 【英雄联盟】2018全球总决赛MV—登峰造极境 Rise
BV1Us411d71V [ 鬼畜综合 ] 【全明星Rap】黑喂狗！
BV1zs411S7sz [ VOCALOID ] 洛天依，言和原创《普通DISCO》
BV1hs411Q7zf [ 鬼畜调教 ] 【电音单曲】我是papi酱
BV1Hx411V7n9 [ 翻唱 ] 【三无】病名为爱
BV1GW411g7mc [ 人力VOCALOID ] 【面筋哥×波澜哥】我的烤面筋，融化你的心！
BV1Ls41127sG [ 鬼畜调教 ] 【小明&老王】此物天下绝响
BV1vx411K7jb [ 其他游戏 ] 【散人】大型励志剧 娱乐圈小助理养成计划（20.2.20更新 叶琛番外 程语柔表白遭拒绝）
BV1xx411c7XW [ 动漫剪辑 ] 电磁炮真是太可爱了
BV15W411W7NJ [ 语言类小剧场 ] 千万不要跟声优斗表情包，否则你将毫无胜算
BV1fs411t7EK [ 鬼畜调教 ] 【高能Rap】你从未看过的家有儿女
BV12s411N7g2 [ 单机主机类游戏 ] 史上容量最大的游戏 300GB的游戏长什么样？
BV1gs411B7y4 [ 鬼畜剧场 ] 主播真会玩鬼畜篇01：我是全英雄联盟最骚的骚猪!
BV1js411f7jY [ 沙盒类 ] 惊艳！半年良心作★Minecraft★World of Ansesuta
BV1Ss411o7vY [ 鬼畜调教 ] 【红日】梁逸峰你朗诵这么屌你家里人知道吗？
BV1xx411c7mu [ 鬼畜调教 ] 最终鬼畜蓝蓝路
BV1XW411F7L6 [ 动漫评论 ] 【Lex】B站历史上意义最重大的10部动画！
BV1f4411M7QC [ 手机 ] 【何同学】有多快？5G在日常使用中的真实体验
BV1es411D7sW [ 鬼畜调教 ] 【循环向】跟着雷总摇起来！Are you OK！
BV1Ys41167aL [ 宅舞 ] 【极乐净土】咬人猫/有咩酱/赤九玖❤155小分队o(*≧▽≦)ツ
BV1Sx411T7QQ [ 演奏 ]  【古筝】千本樱——你可见过如此凶残的练习曲
BV1kt411d7Ht [ 健身跟练教学 ] 10分钟改善斜方肌粗大、溜肩圆肩富贵包、背厚、肩颈背疼痛、高低肩！【周六野Zoey】
BV1Jb411U7u2 [ VOCALOID ] 洛天依，原创《勾指起誓》
BV1dW411n7La [ 同人动画 ] 【FGO手书/完结纪念】诀别之时已至，其为放手世界之人
BV1jE41137eu [ 自制发明/设备 ] 【自制】技术宅UP耗时三个月，自制B站最强小电视！【硬核】【3分钟从草图到实物】
BV16Z4y1H7NG [ 短剧短片 ] 相 机 大 战
BV1ht411L72V [ 翻唱 ] 《Bad Guy》沙雕翻拍《Fat Guy》MV，送给正在减肥的自己
BV1mK411V7wY [ 明星剪辑 ] 龍
BV1zp4y1U7Z5 [ 影视解读 ] 一个人，造出让40亿人震碎的夜晚！
BV1UE411y7Wy [ 沙盒类 ] 你被困在2019年10月25日，如何逃出？（三种循环体+随机选项+多结局）
BV1x54y1e7zf [ 单机主机类游戏 ] 游戏科学新作《黑神话：悟空》13分钟实机演示
BV1Yc411h7uQ [ 同人动画 ] 【60帧定格动画】用高达在5分钟内跳完所有MJ的舞蹈
BV1Wb411v7WN [ 射击游戏 ] 【老番茄】史上最骚杀手(第一集)
BV1Nt4y1D7pW [ 摄影摄像 ] 【何同学】我拍了一张600万人的合影...
BV12J411X7cD [ 动漫速读 ] 73分钟看完柯南所有剧情！史上最全时间线整理！
BV1Jb411W7dH [ 影视剪辑 ] 【七代小丑/踩点/混剪/高燃】前方高能！欢乐与惊悚的踩点视觉盛宴！希斯莱杰诞辰40周年纪念。
BV1w7411P7jJ [ 短剧短片 ] 受够了，我真的不行了。好想逃。
BV1tJ411W7hw [ 其他手工 ] 【才浅手工】魔刀千刃制作 究竟什么叫还原？看完你就明白了
BV19E41197Kc [ 摄影摄像 ] 【盛世中华】超燃！数百位8KRAW摄影师联合摄制，10分钟带你看绝美祖国大好河山！
BV1FE411A7Xd [ 科学科普 ] 《 这才叫水视频！》 创意短片
BV1pi4y147tQ [ 鬼畜调教 ] 最 强 法 海
BV1mi4y1b76M [ 沙盒类 ] 【Minecraft】清明上河图 [灯火阑珊处 人在画中游]【国家建筑师】[北宋翰林张择端原本]
BV1PK411L7h5 [ 音乐资讯 ] 鼓乐《兰陵王入阵曲》耳机开最大！来听千军万马！！！
BV1CC4y1a7ee [ 影视解读 ] 【木鱼微剧场】《红楼梦》（全集）
BV1GK411K7Ke [ 影视剪辑 ] 【孙悟空×林黛玉】名著联姻 | 佛度众生不度我 宁负如来不负卿
BV1ti4y1K7uw [ 原创音乐 ] 一段旋律怎么变成一首歌？曝光学生党制作歌曲全过程:)
BV1bz4y1r7Ug [ 人力VOCALOID ] 【罗翔】童话镇
BV1cy4y1k7A2 [ 科技数码综合 ] 【何同学】80年代的电脑能做什么？苹果麦金塔深度体验
BV16X4y1g7wT [ 其他手工 ] 【才浅】15天花20万元用500克黄金敲数万锤纯手工打造三星堆黄金面具
BV1qt411j7fV [ 动漫剪辑 ] 【派大星的独白】一个关于正常人的故事
BV1yt4y1Q7SS [ 鬼畜调教 ] 敢 杀 我 的 马？！
BV1bW411n7fY [ 鬼畜调教 ] 【春晚鬼畜】赵本山：我就是念诗之王！【改革春风吹满地】
BV13X4y1P7z7 [ 同人动画 ] 2021届清华美院动画毕设 |《万华镜》——百年党庆，献礼中华五十六个民族
BV1JD4y1e7Q4 [ 音乐现场 ] 无屏风表演《口技》还原文言文 ！！！
BV1614y197xJ [ 猫 ] 我花了半年时间给猫做了个房子
BV1gF41117fN [ 摄影摄像 ] 300天4万公里传遍中国，漂流相机终于回来了！
BV14U4y1w7fn [ 设计艺术 ] 这才是文化膨胀！！当岩彩画遇上汉服
BV1Rq4y1n7CR [ 剧情演绎 ] 【广场往事】《妇仇者联盟》：枪在手，跟鹅走！
BV1qm4y1r7BB [ 美妆 ] 『从头看她』1920-2020，中国女性发型的百年变迁
BV1ED4y1Y7dc [ 随拍·综合 ] 一位粉丝想看到自己奔跑的样子
BV1ph4y1g75E [ 同人动画 ] 火柴人 VS 数学(Math)
BV1dR4y1F7Aq [ 动漫剪辑 ] ⚡️ 中 国 人 不 蹦 洋 迪 ⚡️
BV1BK411L7DJ [ 应试教育 ] 【罗翔】我们为什么要读书？
BV1AM4y1M71p [ 舞蹈综合 ] 破亿纪念!【猛男版】新宝岛 4K高清重置加强版
BV1MN4y177PB [ 农村生活 ] 回村三天，二舅治好了我的精神内耗
```

### 2、热门页视频

为什么热门页面视频放在入站必刷后面讲，原因可以看看函数的参数，是的，`hot.get_hot_videos` 多出了两个参数 `pn` 和 `ps`。

`pn` 即 page number，页数，`ps` 即 page size，每页的大小，这个接口实际上是懒加载的，即一次不会直接加载所有数据，而是部分部分加载，就和评论的翻页似的。当然现在评论翻页没有了，原来的翻页接口也改掉了，热门这边虽然没有翻页的 ui，但接口确实就是按照翻页去设计的。

至于接口返回值的结构，这和前面入站必刷视频基本一致，代码甚至不用改也能继续用。这边只需要控制好 `pn` `ps` 参数即可。例如需要获取前 100 个热门视频，只需要控制 `ps = 20`，然后让 `pn` 从 1 到 5 遍历即可。

``` python
from bilibili_api import hot, sync


async def main() -> None:
    ps = 20
    for pn in range(1, 6):
        history = await hot.get_hot_videos(pn=pn, ps=ps)
        for v in history["list"]:
            print(v["bvid"], "[", v["tnamev2"], "]", v["title"])


sync(main())
```

`pn` `ps` 在其他一些接口中亦会出现，意义相同。与之类似的还有一种懒加载的模式，即通过 `offset` 进行懒加载。原理是在每一次加载完后，返回一个 `offset`，下次加载传入 `offset` 后，就会从 `offset` 处继续往下加载，类似单向链表。

热门页面上没有 `offset` 设计，此处就使用获取用户动态举例。

``` python
from bilibili_api import user, sync


async def main() -> None:
    u = user.User(uid=2)
    offset = ""  # 初始 offset
    while True:
        dynamics = await u.get_dynamics_new(offset=offset)
        offset = dynamics["offset"]  # 更新 offset
        for item in dynamics["items"]:
            print(item["id_str"])  # 打印动态 id
        if not dynamics["has_more"]:  # 若已到底，退出循环
            break


sync(main())
```

### 3、每周必看

每周必看需要两个接口，一个接口是获取历史上的每周必看列表的，众所周知每周必看一周就会有一次更新，还有一个接口用于获取特定的一周的每周必看列表。前者对应 `hot.get_weekly_hot_videos_list()`，后者对应 `hot.get_weekly_hot_videos()`。

调用前者会发现，返回结果是历史上每周必看的列表，只提供每周的编号 (第 xxx 期) 和当期的标题（例如第 384 期为 “FGO十周年快乐”）等等，没有具体视频的列表。后者调用需要传入参数 `week`，即需要获取第几期的每周必看列表。显然，后者调用所需要的信息可以通过调用前者获得。

可以看到，此处调用每周必看的视频接口，需要先调用每周必看的列表接口。这其实也符合网页端页面的显示逻辑：左上角有一个下拉列表，显示每一期的每周必看概况，选择到具体的一期后，页面刷新，获取当期的视频列表。因此部分时候可以通过网页显示逻辑参考接口调用的逻辑。

全站音乐榜也是同理，此处不过多赘述。以下代码演示获取最新一期每周必看视频的方法：

``` python
from bilibili_api import hot, sync


async def main() -> None:
    weeks = await hot.get_weekly_hot_videos_list()
    videos = await hot.get_weekly_hot_videos(weeks["list"][0]["number"])
    for v in videos["list"]:
        print(v["bvid"], "[", v["tnamev2"], "]", v["title"])


sync(main())
```

### 4、排行榜

排行榜就正儿八经到 `rank` 模块了。排行榜是分区的，例如有番剧、动画、游戏、生活、鬼畜等。向接口传参时，需要同时控制多个参数。为方便调用，模块对此处的参数进行了封装，调用接口时只需要传入一个枚举类型即可。以下拿动画分区举例。

``` python
from bilibili_api import rank, sync


async def main() -> None:
    videos = await rank.get_rank(type_=rank.RankType.Douga)
    for v in videos["list"]:
        print(v["bvid"], "[", v["tnamev2"], "]", v["title"])


sync(main())
```

通过枚举类，只需要使用 `Douga` 就可以表示动画分区，而非 `rid=1005`。模块中将大量出现像这样的枚举类。

## 使用 `AsyncEvent`

`AsyncEvent` 是模块提供的一个基础类，主要实现了发布-订阅模式的异步事件类。其常作用于长过程的异步操作中，例如上传视频、连接直播间以及消息监听。在这些异步过程中，模块将通过 `AsyncEvent` 类的方法发布事件，例如收到弹幕后发布弹幕事件、上传视频汇报进度也可以发布事件。发布事件后，`AsyncEvent` 类将调用用户提供的回调函数，用户即可实现对事件的订阅。回调函数支持同步函数与异步函数，但建议使用异步函数作为回调函数，或是不阻塞的同步函数作为回调函数。

接下来将用模块中的两个典型 `AsyncEvent` 类作演示，分别是 `live.LiveDanmaku` 和 `session.Session`。

### 1. `live.LiveDanmaku`

众所周知，哔哩哔哩网页端通过 WebSocket 和直播服务器连接，`live.LiveDanmaku` 核心功能即调用模块的 WebSocket 连接功能，完成和直播间的交互。交互分发送消息和接收消息，此处发送的消息主要是心跳包，模块会自动发送心跳包，因此使用 `live.LiveDanmaku` 时，只需要关注 WebSocket 收到的消息即可。

收到消息后，模块会对消息进行解码，一般解码后会得到 JSON 格式的数据。约 2025 年 7 月时，直播间发送消息中出现 protobuf 格式数据，此时 `live.LiveDanmaku` 将自动把 protobuf 数据转换为 JSON 格式。总之，最后回调函数拿到的数据，一般是一个 JSON 反序列化后的字典对象，和通过 HTTP 调用 API 接口返回的数据不会有太大差别。

对 `LiveDanmaku` 类来说，回调函数仅需提供一个 `dict` 类型参数即可。为了绑定回调函数，可以使用 `add_event_listener` 方法，亦可使用 `on` 装饰器，如下：

``` python
@dm.on("DANMU_MSG")
async def handle_dm_msg(data: dict) -> None:
    pass
```

通过上述方式即可完成对事件回调的绑定，此操作应该在异步过程启动之前执行。绑定完回调后，即可启动异步过程，对 `live.LiveDanmaku` 来说，即开始连接直播间。

我们使用 `connect` 方法连接直播间，此方法会开始运行连接直播间的主程序，连接完直播间后仍需要持续接收信息，因此该方法是阻塞的，直到主程序结束后才会停止。直播间理论上可以无限地连接，因此主程序需要手动结束，不然程序永远无法退出，可以使用 `disconnect` 方法关闭对直播间的连接。

此处优先考虑终端环境下的演示，故使用 `Ctrl + C` 作为终止信号，只需要加入对 `KeyboardInterrupt` 的异常捕获即可优雅地用 `Ctrl + C` 结束程序。理论上取消直播间连接会在 `await dm.connect()` 处收到 `asyncio.CancelledError`，但模块所有的 `AsyncEvent` 类运行过程中均会主动捕获此异常，此处就不用再捕捉了。

``` python
dm = live.LiveDanmaku(room_display_id=33989, credential=credential)
# 建议加入凭据类连接直播间，否则……可以尝试退出登录后体验一下网页端直播页面
try:
    await dm.connect()
except KeyboardInterrupt:
    await dm.disconnect()
```

可以先尝试不绑定任何回调，运行以上代码，可以发现终端出现了部分日志信息，因为模块在 `live.LiveDanmaku` 中配置了日志，用于输出直播间连接过程中的信息，包括正在连接服务器、认证成功、正在关闭连接等。稍等片刻，不出意外的话，模块将成功连接上服务器，将会显示“认证成功”，此处可以按下 `Ctrl + C`，程序就能优雅地退出了。

```shell
python3 test-trio.py
[33989][2026-08-07 22:47:17,956][INFO] 准备连接直播间 33989
[33989][2026-08-07 22:47:19,121][INFO] 正在尝试连接主机： wss://zj-cn-live-comet.chat.bilibili.com:2245/sub
[33989][2026-08-07 22:47:19,239][INFO] 连接服务器并认证成功
^C%
```

在确认可以正常连接直播间后，即可正式绑定回调函数，开始获取信息（主要是弹幕）。这边假设我们对传入数据结构一无所知，于是在回调函数中，我们只打印传入的数据：

``` python
@dm.on("DANMU_MSG")
def dm_msg(data: dict) -> None:
    print(data)
```

`@dm.on` 的括号中是事件名称，`DANMU_MSG` 即对应了单条弹幕，这些字符串可以在 `live.LiveDanmaku` 的 docstring 中找到，或者，可以翻阅 `live.LiveDanmaku` 类的文档查看。

运行程序，就会发现输出了许多字典对象，此处节选一条弹幕的信息：

``` python
{
    "room_display_id": 33989,
    "room_real_id": 33989,
    "type": "DANMU_MSG",
    "data": {
        "cmd": "DANMU_MSG",
        "dm_v2": "",
        "info": [
            [
                0,
                1,
                25,
                16777215,
                1786114405665,
                1066685255,
                0,
                "f0650ae2",
                0,
                0,
                0,
                "",
                0,
                "{}",
                "{}",
                {
                    "extra": '{"send_from_me":false,"master_player_hidden":false,"mode":0,"color":16777215,"dm_type":0,"font_size":25,"player_mode":1,"show_player_type":0,"content":"大叔好贴这个人脸啊","user_hash":"4033153762","emoticon_unique":"","bulge_display":0,"recommend_score":7,"dm_score":0,"chronos_force_display":0,"main_state_dm_color":"","objective_state_dm_color":"","direction":0,"pk_direction":0,"quartet_direction":0,"anniversary_crowd":0,"yeah_space_type":"","yeah_space_url":"","jump_to_url":"","space_type":"","space_url":"","animation":{},"emots":null,"is_audited":false,"id_str":"30c072a5bdb3ce4239b006fcbd6a75f18805","icon":null,"show_reply":true,"reply_mid":0,"reply_uname":"","reply_uname_color":"","reply_is_mystery":false,"reply_type_enum":0,"hit_combo":0,"esports_jump_url":"","is_mirror":false,"is_collaboration_member":false,"card":{"card_type":0,"oid_str":"","oid_str_1":"","origin_oid_str":"","share_id":"","share_origin":"","from":"","card_content":null},"voice":null,"background_type":0}',
                    "mode": 0,
                    "show_player_type": 0,
                    "user": {
                        "anon": None,
                        "base": {
                            "face": "https://i0.hdslb.com/bfs/face/6d8a0e1bf1e19c3d63ac451875968dd72d48016c.jpg",
                            "is_mystery": False,
                            "name": "姬野家的星奏",
                            "name_color": 0,
                            "name_color_str": "",
                            "official_info": {
                                "desc": "",
                                "role": 0,
                                "title": "",
                                "type": -1,
                            },
                            "origin_info": {
                                "face": "https://i0.hdslb.com/bfs/face/6d8a0e1bf1e19c3d63ac451875968dd72d48016c.jpg",
                                "name": "姬野家的星奏",
                            },
                            "risk_ctrl_info": None,
                        },
                        "guard": None,
                        "guard_leader": None,
                        "medal": {
                            "color": 13081892,
                            "color_border": 13081892,
                            "color_end": 13081892,
                            "color_start": 13081892,
                            "guard_icon": "",
                            "guard_level": 0,
                            "honor_icon": "",
                            "id": 2226,
                            "is_light": 1,
                            "level": 18,
                            "name": "泛团",
                            "ruid": 63231,
                            "score": 1165,
                            "typ": 0,
                            "user_receive_count": 0,
                            "v2_medal_color_border": "#C770A499",
                            "v2_medal_color_end": "#C770A499",
                            "v2_medal_color_level": "#C770A4E6",
                            "v2_medal_color_start": "#C770A499",
                            "v2_medal_color_text": "#FFFFFF",
                        },
                        "title": {"old_title_css_id": "", "title_css_id": ""},
                        "uhead_frame": None,
                        "uid": 67268124,
                        "wealth": None,
                    },
                },
                {"activity_identity": "", "activity_source": 0, "not_show": 0},
                0,
            ],
            "大叔好贴这个人脸啊",
            [67268124, "姬野家的星奏", 0, 0, 0, 10000, 1, ""],
            [
                18,
                "泛团",
                "泛式",
                33989,
                13081892,
                "",
                0,
                13081892,
                13081892,
                13081892,
                0,
                1,
                63231,
            ],
            [13, 0, 6406234, ">50000", 0],
            ["", ""],
            0,
            0,
            None,
            {"ct": "41585B4A", "ts": 1786114405},
            0,
            0,
            None,
            None,
            0,
            260,
            [20],
            None,
        ],
    },
}
```

这坨数据显然也需要进一步处理，此处省略过程，最后可以通过以下键值，获取到单条弹幕的各种信息：

``` python
text = data["data"]["info"][1]  # 弹幕文字
user_info = data["data"]["info"][0][15]  # 发送者信息
user_name = user_info["user"]["base"]["name"]  # 发送者昵称，未登录状态下将变成三*堆
try:  # 以下粉丝牌字段可能存在
    medal_name = user_info["user"]["medal"]["name"]  # 粉丝牌
    medal_level = user_info["user"]["medal"]["level"]  # 粉丝牌等级
    print(f"[{medal_level} {medal_name}] {user_name} : {text}")
except Exception:
    print(f"{user_name} : {text}")  # 没有粉丝牌
```

其实前文代码中的 `try-catch` 可以省去，但程序仍然会正常运行，不会报错（~~可以试试~~），但异常仍然是会有的，只不过模块内部会捕获这个异常。这个异常最终也会抛出，但抛出的方式比较温柔，它们会通过 `__TASK_EXCEPTION__` 事件被发布出来。

``` python
@dm.on("__TASK_EXCEPTION__")
def raise_exception(e: Exception) -> None:
    raise e


# 用以上代码即可将所有错误全部抛出，然后程序可能就中断了
# 显然，在这个回调函数中再有错误抛出，模块就不会再发布 __TASK_EXCEPTION__ 了，而是直接抛出异常。
```

因此若有调试需求，例如此处在报错后，最后的 `print` 不会执行，就会有漏弹幕的情况，就可以考虑对 `__TASK_EXCEPTION__` 进行监听了。

应用上述代码，一个简易的终端弹幕姬就完成了，来看看实战效果：

``` plaintext
[17 泛团] 勃力银梦 : 不要给我看这个口牙！
[14 泛团] 即将精神错乱 : 😭
[14 泛团] 有翡我思存 : cpu
[16 泛团] 萧山_爱阿钳 : 反胃了
[18 泛团] yuyu不是玉玉 : 纯在pua
[28 泛团] 江停晚 : 不要不要
枫少原生 : 简称好事没你份 坏事你背锅
[20 泛团] 一笑冷 : 阿梅真是超级高手
SoucreFimp_YZ : 就在今天
[19 泛团] rakka想不到名字 : 怎么还背后说坏话！
[30 泛团] UESUGl : i熊tv
柴界的梦想 : 为什么要说这么坏心眼的话
[28 泛团] 帝蒂缔谛碲諦 : 这不是左撇子艾伦
[8 泛团] 片道の切符 : 大人的世界
[18 泛团] 晩稚濑 : 一直在被他人摘果子吗
[16 泛团] 萧山_爱阿钳 : 这里是成年直播间吗
[20 泛团] 雾隐余绪 : 不要不要
[15 泛团] 皇珈鬼武士 : 太成人了
```

看着有些单调，终端下弹幕一行行打印出来总有些既不弹又不幕还不姬的感觉。这边就勉为其难多实现一个功能吧，我们尝试复刻用户进入直播间的效果：只需要在监听到进入直播间消息后，在终端进行打印，随后不换行，将光标移到行首 (`\r`)，这样多个人进入直播间后，就会有种“进入直播间那一行在滚动”的感觉，就这么办。

我们再使用打印大法获取一个用户进入直播间消息的示例，这个消息对应的名称为 `INTERACT_WORD_V2`。

``` python
@dm.on("INTERACT_WORD_V2")
def enter(data: dict) -> None:
    print(data)
```

``` python
{
    "room_display_id": 33989,
    "room_real_id": 33989,
    "type": "INTERACT_WORD_V2",
    "data": {
        "cmd": "INTERACT_WORD_V2",
        "data": {
            "dmscore": 10,
            "pb": "CLq62owBEgzmpaDmnKhIb3RhcnUiAgMBKAEwxYkCOP7v19MGQJTT9+z9M0ooCP/tAxAWGgbms5vlm6Igy6hpKMuoaTCSu8oCOMuoaUABYMWJAmj3GmIAeMSQ9uX64+PkGJoBALIBygEIurrajAESWgoM5qWg5pyoSG90YXJ1EkpodHRwczovL2kxLmhkc2xiLmNvbS9iZnMvZmFjZS9lYjliZDBjYjVjMzVmOWM0YzNhYzkyMzNkNTljODMxZTBjMzAxYzc1LmpwZxpgCgbms5vlm6IQFhjLqGkgkrvKAijLqGkwy6hpOLIRSAFQ/+0DYPcaegkjM0ZCNEY2OTmCAQkjM0ZCNEY2OTmKAQkjM0ZCNEY2OTmSAQcjRkZGRkZGmgEJIzNGQjRGNkU2IgIIBTIAugEAwgEA",
        },
    },
}
```

可以说，前面弹幕获取到的数据结构乱，但至少许多字段都看得懂，而这边进入直播间获取到的数据……已经进化到字节数据了（这边服务端已对字节进行了 base64 加密），可谓是一点给人理解的可能性都没有。

其实这就是前文曾经提到过的 protobuf 数据。

> 约 2025 年 7 月时，直播间发送消息中出现 protobuf 格式数据，此时 `live.LiveDanmaku` 将自动把 protobuf 数据转换为 JSON 格式。

好吧，上面的数据其实并非模块传入的数据，模块传入的数据其实长下面这样：

``` python
{
    "room_display_id": 33989,
    "room_real_id": 33989,
    "type": "INTERACT_WORD_V2",
    "data": {
        "cmd": "INTERACT_WORD_V2",
        "data": {
            "dmscore": 10,
            "pb": "CLq62owBEgzmpaDmnKhIb3RhcnUiAgMBKAEwxYkCOP7v19MGQJTT9+z9M0ooCP/tAxAWGgbms5vlm6Igy6hpKMuoaTCSu8oCOMuoaUABYMWJAmj3GmIAeMSQ9uX64+PkGJoBALIBygEIurrajAESWgoM5qWg5pyoSG90YXJ1EkpodHRwczovL2kxLmhkc2xiLmNvbS9iZnMvZmFjZS9lYjliZDBjYjVjMzVmOWM0YzNhYzkyMzNkNTljODMxZTBjMzAxYzc1LmpwZxpgCgbms5vlm6IQFhjLqGkgkrvKAijLqGkwy6hpOLIRSAFQ/+0DYPcaegkjM0ZCNEY2OTmCAQkjM0ZCNEY2OTmKAQkjM0ZCNEY2OTmSAQcjRkZGRkZGmgEJIzNGQjRGNkU2IgIIBTIAugEAwgEA",
            "pb_decoded": {
                "uid": 295083322,
                "uname": "楠木Hotaru",
                "identities": [2],
                "msg_type": 1,
                "room_id": 33989,
                "timestamp": 1786116094,
                "score": 1786129541524,
                "fans_medal_info": {
                    "target_id": 63231,
                    "medal_level": 22,
                    "medal_name": "泛团",
                    "medal_color": 1725515,
                    "medal_color_start": 1725515,
                    "medal_color_end": 5414290,
                    "medal_color_border": 1725515,
                    "is_lighted": 1,
                    "anchor_roomid": 33989,
                    "score": 3447,
                },
                "contribution_info": {},
                "trigger_time": 1786116093433972804,
                "contribution_info_v2": {},
                "user_info": {
                    "uid": 295083322,
                    "base": {
                        "name": "楠木Hotaru",
                        "face": "https://i1.hdslb.com/bfs/face/eb9bd0cb5c35f9c4c3ac9233d59c831e0c301c75.jpg",
                    },
                    "medal": {
                        "name": "泛团",
                        "level": 22,
                        "color_start": 1725515,
                        "color_end": 5414290,
                        "color_border": 1725515,
                        "color": 1725515,
                        "id": 2226,
                        "is_light": 1,
                        "ruid": 63231,
                        "score": 3447,
                        "v2_medal_color_start": "#3FB4F699",
                        "v2_medal_color_end": "#3FB4F699",
                        "v2_medal_color_border": "#3FB4F699",
                        "v2_medal_color_text": "#FFFFFF",
                        "v2_medal_color_level": "#3FB4F6E6",
                    },
                    "wealth": {"level": 5},
                    "guard": {},
                },
                "user_anchor_relation": {},
            },
            "pb_decode_message": "success",
        },
    },
}
```

可以看到已经把 protobuf 数据解密了，变成正常的 JSON 格式了。接下来的处理也就简单了：

``` python
user_info = data["data"]["data"]["pb_decoded"]
user_name = user_info["uname"]
print(f"【进入直播间】 {user_name}", end="\r")  # 此处只显示用户名确实是为了偷懒
```

最后给到源代码和生草的效果图：

``` python
from bilibili_api import Credential, live, sync

credential = Credential(...)


async def main():
    dm = live.LiveDanmaku(room_display_id=33989, credential=credential)

    @dm.on("DANMU_MSG")
    def dm_msg(data: dict) -> None:
        text = data["data"]["info"][1]
        user_info = data["data"]["info"][0][15]
        user_name = user_info["user"]["base"]["name"]
        try:
            medal_name = user_info["user"]["medal"]["name"]
            medal_level = user_info["user"]["medal"]["level"]
            print(f"[{medal_level} {medal_name}] {user_name} : {text}")
        except Exception:
            print(f"{user_name} : {text}")

    @dm.on("INTERACT_WORD_V2")
    def enter(data: dict) -> None:
        user_info = data["data"]["data"]["pb_decoded"]
        user_name = user_info["uname"]
        print(f"【进入直播间】 {user_name}", end="\r")

    try:
        await dm.connect()
    except KeyboardInterrupt:
        await dm.disconnect()


sync(main())
```

![艹艹艹艹艹艹艹艹艹艹艹艹艹艹艹艹艹艹艹](img/live-demonstration.gif)

上面的代码只有两个事件需要监听，也只需要两个函数。但事件一旦多了起来，就需要编写多个函数分别处理事件，有的时候会很麻烦。

因此，模块提供一个奇妙事件 `__ALL__`，它将在除 `__ALL__` 和 `__TASK_EXCEPTION__` 外的其他所有事件发布时，额外发布出来。

``` python
@dm.on("__ALL__")
def on_all(info: dict) -> None:
    event_name = info["name"]
    data = info["data"]
    print(event_name, data)
```

绑定此函数回调后再连接直播间，就能感受到被信息包围的氛围感了。

### 2. `session.Session`

接下来要介绍的是 `session.Session`，用于监听私聊消息的 `AsyncEvent` 类。相较于 `live.LiveDanmaku` 这样核心是 WebSocket 的异步过程来说，这个类的异步过程稍显另类，本质上是一个定时任务，每隔 6 秒钟刷新私聊区信息，拉取新消息。不仅如此，`session.Session` 同时支持消息回复功能，这就允许我们如此部署一个简易的聊天机器人。

事实上，直播间场景下亦可以使用 `live.LiveRoom` 中的函数发送弹幕，即回复弹幕，不过很明显这没有私聊的接发消息来得纯粹。不同于直播间，私聊功能支持多种类型消息，这边我们就只考虑两种基本类型，文字和图片。

前文已提到，私聊中会出现多种类型信息，不但如此，除了信息正文内容外，仍有其他信息的信息，例如发送者、发送时间等等，因此模块使用了 `session.Event` 包装了抓取到的信息。这个类属性很多，此处我们只需要最重要的 `content` 属性，即事件内容。至于事件内容类型的判断，可以使用 `msg_type` 属性，也可以按照下面的方法直接绑定在回调中：

``` python
@session.on(EventType.TEXT)  # 当收到文字信息时触发
async def reply(event: Event):
    pass


@session.on(EventType.PICTURE)  # 当收到图片时触发
async def filter_pic(event: Event):
    pass
```

现在问题来了，`event.content` 当收到文字时为 `str`，毋庸置疑，那收到图片的时候，`event.content` 又是什么呢？答案是模块提供的 `Picture` 类 (`bilibili_api.Picture`)。

`Picture` 类本质上是对 `PIL.Image.Image` 的异步封装（此处假设读者对 `Python Imaging Library` a.k.a. `pillow` 有基本了解），接下来将分别介绍如何初始化一个 `Picture` 类、如何将 `Picture` 类转换为图片内容、文件乃至链接，以及如何对 `Picture` 类包装的 `PIL.Image.Image` 对象进行操作。

初始化 `PIL.Image.Image` 只需要提供一个字节流即可，`Image.open` 不会一次性读取全部内容，模块为此提供 `Picture.from_file` 和 `Picture.from_content` 两个同步函数，可以直接在异步函数中使用。如果需要加载网络图片，使用异步方法 `Picture.load_url`，因为此方法内部已经涉及到网络请求。

`Picture` 对象存在以下属性：`url` 为网络链接或本地文件地址，如果图片为从字节中加载或已经更改过，`url` 属性将设置为 `<bytes>.{extension}`，其中 `extension` 为图片后缀名，也是 `Picture` 对象中存在的属性。此外还有 `width` `height` 属性，表示图片宽度和高度。

初始化 `Picture` 对象后，可以通过异步函数 `Picture.content` 获取图片字节内容，异步函数 `Picture.download` 将图片保存到本地文件，亦可以使用哔哩哔哩动态相关功能，将其上传至服务器，只需要调用 `Picture.upload(credential=Credential(...))` 即可，此时获取 `Picture` 类的 `url` 属性，即可获得上传成功后的链接。

`Picture` 类提供 `Picture.image_call` 对 `PIL.Image.Image` 对象进行操作。例如 `Image.resize((width, height))` 可以调整图片大小，并返回一个新的 `Image` 对象，这个过程可能是阻塞的，因此模块会在一个工作进程中执行此函数，以免阻塞事件循环，在函数执行完成后，`Picture` 类会将其包装的图片设置为返回结果。这就是 `Picture.image_call` 函数在做的事，此处调用 `await Picture.image_call("resize", (width, height))` 即可调整 `Picture` 类对应图片的大小了。

接下来就可以开始编写逻辑了。对文字消息来说，我们只特殊识别两个文本：收到 `/close` 的时候结束轮询，和收到 `/pic` 的时候发送一张图片，其余情况统一回复 `你好`。

说到结束轮询，就不得不提开始轮询了，`session.Session` 类使用 `start` 函数开始异步过程，使用 `close` 函数结束异步过程，注意前者为异步函数，后者为同步函数。收到 `/close` 后，只需要调用 `close` 函数即可。

回复消息可以使用 `session.reply`，其接受两个参数，第一个是需要回复的消息，即回调函数的参数 `event`，第二个是具体内容，如果是文本就直接传入文本，如果是图片就需要使用 `Picture` 类了。先使用 `Picture.from_file("path/to/pic")` 加载本地图片，然后使用异步函数 `upload` 将其上传，随后就可以发送了。

> 如果传入的 `Picture` 类尚未上传，模块大多数情况下将自动上传图片。

于是我们可以完善前文收到消息的回调函数如下：

``` python
@session.on(EventType.TEXT)
async def reply(event: Event):
    if event.content == "/close":
        session.close()
    elif event.content == "/pic":
        img = await Picture.from_file("test.jpg").upload(session.credential)
        await session.reply(event, img)
    else:
        await session.reply(event, "你好")
```

如果收到的是图片，这里实现两个逻辑，首先把图片下载到本地，即调用 `download` 函数，然后给图片加一层滤镜，再发回去，加滤镜可以使用 `Image.Filter` 函数，或是 `Picture.image_call("filter", ...)`，回复图片仍然使用 `reply` 方法。最后回调函数如下：

``` python
@session.on(EventType.PICTURE)
async def save_pic(event: Event):
    await event.content.download(event.content.url.split("/")[-1])  # type: ignore
    # 截取 url 最后一节作文件名，保存在当前目录
    await event.content.image_call("filter", ImageFilter.SMOOTH)  # type: ignore
    # 此处用的滤镜时平滑滤波
    await session.reply(event, event.content)  # type: ignore
```

主程序部分，采用和前文连接直播间相同的写法，当 `Ctrl + C` 时停止轮询。

``` python
try:
    await session.start()
except KeyboardInterrupt:
    session.close()
```

运行即可。完整代码如下：

``` python
from PIL import ImageFilter
from bilibili_api import (
    Credential,
    Picture,
    select_client,
    sync,
)
from bilibili_api.session import Event, EventType, Session

select_client("httpx")
# 调用 select_client 即可指定网络请求库
# 此处使用了 httpx 作为网络请求库，以保证稳定性

credential = Credential(...)

session = Session(credential, debug=True)


@session.on(EventType.TEXT)
async def reply(event: Event):
    if event.content == "/close":
        session.close()
    elif event.content == "/pic":
        img = await Picture.from_file("test.jpg").upload(session.credential)
        await session.reply(event, img)
    else:
        await session.reply(event, "你好")


@session.on(EventType.PICTURE)
async def save_pic(event: Event):
    await event.content.download(event.content.url.split("/")[-1])  # type: ignore
    await event.content.image_call("filter", ImageFilter.SMOOTH)  # type: ignore
    await session.reply(event, event.content)  # type: ignore


async def main():
    try:
        await session.start()
    except KeyboardInterrupt:
        session.close()


sync(main())
```

## 使用 `login_v2`

> Credential 类，又称凭据类，用于向模块传入用户的 cookies。
> 为什么需要 cookies? 凡是涉及需要用户参与的操作，都需要 cookies 鉴权，验证用户身份。

以上节选自 `文档/通用/Credential 类`，这也说明了为什么前文提到的“拷贝 cookies”是一种可行的登录方法。但拷贝 cookies 有时候还是会麻烦一些，有没有其他登录的方法了？有，`login_v2` 模块实现了网页端/TV 端哔哩哔哩的登录流程，如果说登录是完成作业，那么拷贝 cookies 是抄作业，而 `login_v2` 是真正可以做作业的模块。

> `login_v2` 之所以称之为 `login_v2`，不同于 `video_zone_v2` 是哔哩哔哩系统的分区升级，其实际上是 bilibili-api 登录模块的更新换代。在 `v17` 之前，模块的登录功能由 `login` `login_func` 模块提供，但两个模块的逻辑全部是同步逻辑，因此最终被移除。若仍想体验旧的 `login` 模块，可以使用 <https://github.com/luyanci/blapi-port>。

登录方式大致分为两种，第一种是扫码登录，第二种是密码/验证码登录。一般推荐使用第一种，因为第一种稳定性更佳，许多第三方哔哩哔哩应用使用的都是扫码登录。第二种放一起的原因是许多情况下密码输对了也照样要来一遍验证码，某种意义上二者还是挺相像的。

### 1. 扫码登录

目前扫码登录支持网页端扫码登录和 TV 端扫码登录，二维码需要用手机上的哔哩哔哩 APP 去扫，整个扫码登录的生命周期由 `login_v2.QrCodeLogin` 实现。首先需要通过 `QrCodeLogin.generate_qrcode` 获取二维码链接，可以通过 `get_qrcode_picture` 获取二维码图片 `Picture` 对象，或 `get_qrcode_terminal` 在终端打印出二维码。接下来是等待二维码被扫描的轮询过程，这和 `session.Session` 类颇想，但此处轮询过程需要用户来实现，`QrCodeLogin` 提供 `check_state` 函数判断当前扫码状态，返回 `login_v2.QrCodeLoginEvents`。当扫码登录成功后，即可通过 `qr.get_credential()` 获取得到的凭据类。

第一步，先实例化 `QrCodeLogin` 并生成二维码，这边先介绍一下 `get_qrcode_terminal` 函数的用法，其返回一个字符串，只需要打印这个字符串，就能在终端看到二维码了：

``` python
from bilibili_api import login_v2, sync

qr = login_v2.QrCodeLogin()
print(sync(qr.get_qrcode_terminal()))
```

这边我们使用 `get_qrcode_picture`，前文已提及过 `Picture` 类的使用方法，此处我们将目标图片保存到本地文件 `qr.png`：

``` python
qr = login_v2.QrCodeLogin()
# 生成二维码，获取 Picture 类对象，并保存图片
pic = await qr.get_qrcode_picture()
await pic.download("qr.png")
```

前文提到扫码登录支持两种，网页端扫码登录和 TV 端扫码登录，默认使用网页端登录，如需要使用 TV 端登录，只需要在实例化 `QrCodeLogin` 时传入以下参数即可：

``` python
qr = login_v2.QrCodeLogin(platform=login_v2.QrCodeLoginChannel.TV)
# 与之相对的默认情况
qr = login_v2.QrCodeLogin(platform=login_v2.QrCodeLoginChannel.WEB)
```

第二部即为轮询，此处详细介绍轮询可能遇到的几种状态：`QrCodeLoginEvents.SCAN`，即仍未扫描二维码的状态，`QrCodeLoginEvents.DONE`，即登录成功后的状态，`QrCodeLoginEvents.CONF`，即正在确认登录的状态，此状态仅限网页端扫码登录，`QrCodeLoginEvents.TIMEOUT`，此时二维码已过期，需要重新生成一遍二维码。此处设置每 1 秒进行一次查询状态，在轮询的频率上，二维码接口相较于消息接口宽松得多，但仍然需要提醒，不要跑得太快。

``` python
while True:
    state = await qr.check_state()
    # 检查状态
    match state:
        case login_v2.QrCodeLoginEvents.SCAN:
            print("【状态】未扫描二维码", end="\r")
        case login_v2.QrCodeLoginEvents.CONF:
            print("【状态】正在确认登录", end="\r")
        case login_v2.QrCodeLoginEvents.DONE:
            print("【状态】已完成登录：")
            break
        case login_v2.QrCodeLoginEvents.TIMEOUT:
            print("【状态】二维码已过期")
            exit(1)  # 偷个小懒
    await anyio.sleep(1)
```

---

第三步自然是获取凭据类了，使用 `get_credential` 方法即可。获得 `Credential` 后，如需导出 cookies，可以调用 `get_core_cookies` 方法，这将返回所有只有依靠登录过程才能获取的 cookies，包含 `SESSDATA` `bili_jct` `DedeUserID` `DedeUserID__ckMd5` `sid`，同时还有一个重要的辅助数值（虽然其并不属于 cookies），即 `ac_time_value`。这些 cookies 的相关信息可以在 `文档/通用/Credential 类` 中找到。

此处有必要介绍 `get_core_cookies` 函数和 `get_cookies` 函数的区别。区别是前者为同步函数，后者为异步函数。为什么后者为异步函数？因为后者返回值提供了 `buvid3` `buvid4` `bili_ticket` 等风控 cookies，它们无需登录也能获取，`buvid3` `buvid4` 若未在凭据类中提供，模块将自动生成并激活一对新的 `buvid3` 和 `buvid4`。可以看出，在登录过程中，真正有需要的、价值的 cookies，只有 `get_core_cookies` 返回值中的 cookies；然而在实际请求中，仍需要补充其他 cookies，此时就需要 `get_cookies` 函数提供一份完整的 cookies。

`get_core_cookies` 返回值可以保存在 `json` 文件中，随后每次需要使用凭据类时，可以先用 `json.load` 加载，再使用 `Credential.from_cookies` 通过 cookies 字段初始化凭据类。如下所示：

``` python
credential = Credential.from_cookies(json.load(open("cookie.json")))
```

cookies 可能过期，需要刷新，这可以通过 `Credential.check_refresh` 函数确认，刷新过程可以通过 `Credential.refresh` 完成，如下所示：

``` python
if await credential.check_refresh():
    print("正在刷新")
    await credential.refresh()
    print(json.dumps(credential.get_core_cookies()))
else:
    print("无需刷新")
```

自此，即可完成一份本地 cookies 的获取、保存和维护。这份 cookies 的生命周期与浏览器中的 cookies 完全隔离，二者不会互相干扰。

### 2. 密码/验证码登录

接下来是密码/验证码登录，相信日常生活中大部分人都倾向使用这种方式。先问一个问题，在日常登录过程中，什么令你最为印象深刻？

<img src="img/geetest.png" width="300" height="400">

哔哩哔哩也存在人机测试验证码，也是极验的验证码。事先声明，这验证码是不得不完成的，虽然模块没有自动完成验证码的能力，但验证码的人机测试仍然可以被完成。

模块提供 `bilibili_api.Geetest` 类，可以通过 `Geetest.generate_test` 函数生成一个极验验证码，然后使用 `get_info` 获取极验验证码相关信息。其返回的 `GeetestMeta` 类包含两个关键字段：`gt` `challenge`，因为只要有了 `gt` 和 `challenge` 就可以在网页端实例化极验测试了。现在可以打开 <https://kuresaru.github.io/geetest-validator/>，输入 `gt` `challenge`，就可以生成验证码并完成（显然是手动完成）。完成验证码后会得到两个字符串，`validate` 和 `seccode`，或者说，只要获得这两个字符串，极验验证就算完成了。可以通过 `Geetest.complete_test` 传入完成验证码后获得的 `validate` 和 `seccode`。

``` python
gee = Geetest()
await gee.generate_test()
info = gee.get_info()
print("gt:", info.gt, "challenge:", info.challenge)
...
gee.complete_test("validate", "seccode")
```

为方便验证码作答，模块内嵌了 <https://kuresaru.github.io/geetest-validator/>，并允许通过 `http.server.HTTPServer` 开启本地验证码服务。具体用法是，先通过 `start_geetest_server` 开启服务器，然后使用 `get_geetest_server_url` 获取链接，接下来使用 `wait_for_done` 函数等待验证码完成，最后使用 `close_geetest_server` 关闭服务器。代码如下：

``` python
gee = Geetest()
await gee.generate_test()
gee.start_geetest_server()
print("url:", gee.get_geetest_server_url())
# url: http://127.0.0.1:49180/
await gee.wait_for_done()
gee.close_geetest_server()
print(gee.get_result())
# GeetestMeta(gt='ac597a4506fee079629df5d8b66dd4fe',
#             challenge='f9be10572180bdca190c915bdf476a12',
#             token='82a7bef08cc64506b54ca03aa9a9c09e',
#             seccode='bfac3ae1d10a9b811c5cf109a94560d6|jordan',
#             validate='bfac3ae1d10a9b811c5cf109a94560d6')
```

完成极验后，`Geetest` 类即可作为参数，传入密码/验证码登录函数。两个函数分别是 `login_with_password` 和 `send_sms` (发送验证码)。

``` python
# 密码登录
cred = await login_v2.login_with_password(
    username=username, password=password, geetest=gee
)
# 验证码登录
## 1. 初始化 PhoneNumber
phone = login_v2.PhoneNumber("XXXXXXXXXXX", "+86")
## 2. 发送验证码，获得对应的 captcha_id
captcha_id = await login_v2.send_sms(phonenumber=phone, geetest=gee)
## 3. 完成登录
cred = await login_v2.login_with_sms(
    phonenumber=phone, code=code, captcha_id=captcha_id
)
```

上面两个函数成功后直接返回 `Credential` 类。但有时登录会遇到安全验证，此时上面两个函数的返回值不再是 `Credential`，而是 `login_v2.LoginCheck`。登录验证又需要极验验证码，但有一点需要注意，此处的验证码类型，和前面生成的类型不一致，换句话说前面生成的 `Geetest` 类在此处不能使用。因此，调用 `generate_test` 的时候，需要加上参数 `type_=GeetestType.VERIFY`。

``` python
await gee.generate_test(type_=GeetestType.VERIFY)
# 登录时为 GeetestType.LOGIN，为默认值。
await gee.generate_test(type_=GeetestType.LOGIN)
```

然后即可完成登录验证，最终仍然可以拿到 `Credential` 类。

``` python
await check.send_sms(gee)
cred = await check.complete_check(code)
```

最后只需要对 `Credential` 进行后续处理即可。前面扫码登录处已经展开过讨论。

在模块 API 示例的 `login_v2` 部分，文档提供了一段终端登录脚本(密码/验证码)，如下：

``` python
from bilibili_api import Geetest, GeetestType, login_v2, sync


async def main() -> None:
    choice = input("pwd / sms:")

    gee = Geetest()  # 实例化极验测试类
    await gee.generate_test()  # 生成测试
    gee.start_geetest_server()  # 在本地部署网页端测试服务
    print(gee.get_geetest_server_url())  # 获取本地服务链接
    await gee.wait_for_done()  # 等待测试完成
    gee.close_geetest_server()  # 关闭部署的网页端测试服务
    print("result:", gee.get_result())

    # 1. 密码登录
    if choice == "pwd":
        username = input("username:")  # 手机号/邮箱
        password = input("password:")  # 密码
        cred = await login_v2.login_with_password(
            username=username,
            password=password,
            geetest=gee,  # 调用接口登录
        )
    # 2. 验证码登录
    elif choice == "sms":
        phone = login_v2.PhoneNumber(input("phone:"), "+86")  # 实例化手机号类
        captcha_id = await login_v2.send_sms(
            phonenumber=phone, geetest=gee
        )  # 发送验证码
        print("captcha_id:", captcha_id)  # 顺便获得对应的 captcha_id
        code = input("code: ")
        cred = await login_v2.login_with_sms(
            phonenumber=phone,
            code=code,
            captcha_id=captcha_id,  # 调用接口登录
        )
    else:
        exit(1)

    # 安全验证
    if isinstance(cred, login_v2.LoginCheck):
        # 如法炮制 Geetest
        gee = Geetest()  # 实例化极验测试类
        await gee.generate_test(
            type_=GeetestType.VERIFY
        )  # 生成测试 (注意 type_ 为 GeetestType.VERIFY)
        gee.start_geetest_server()  # 在本地部署网页端测试服务
        print(gee.get_geetest_server_url())  # 获取本地服务链接
        await gee.wait_for_done()  # 等待测试完成
        gee.close_geetest_server()  # 关闭部署的网页端测试服务
        print("result:", gee.get_result())
        await cred.send_sms(gee)  # 发送验证码
        code = input("code:")
        cred = await cred.complete_check(code)  # 调用接口登录

    print("cookies:", cred.get_core_cookies())  # 获得 cookies


if __name__ == "__main__":
    sync(main())
```

## 下载视频

最后，我们将尝试下载视频，通过文档的搜索可以发现，模块提供 `Video.get_download_url` 函数。此函数接受两个参数，任选其一即可，一个是分 P 数，一个是 cid。分 P 此处不再过多解释，cid 实际上一一对应了每个视频的每一个分 P，每一个 cid 都对应了一个视频一个分 P 的视频流地址、弹幕池、字幕、播放记录，等等。cid 可以通过 `Video.get_cid` 异步通过视频和分 P 获取，当然此处传入分 P 数即可。

事实上，所有接口支持的参数仅有 cid，模块对分 P 的支持建立在 `get_cid` 上，这个函数规定，分 P 数从 0 开始计数，使用时需注意。

``` python
from bilibili_api import sync, video


async def main() -> None:
    v = video.Video(aid=2)
    download_url = await v.get_download_url(page_index=0)
    print(download_url)


sync(main())
```

运行代码可以得到很长一串返回字典，视频下载 url 就在其中。以下是返回字典格式化输出结果（部分）：

``` python
{
    ...
    "dash": {
        ...
        "video": [
            {
                "id": 32,
                "baseUrl": "https://xy220x202x9x156xy.mcdn.bilivideo.cn:8082/v1/resource/upgcxcode/31/21/62131/62131_da3-1-100110.m4s?agrr=1&build=0&buvid=9A7E608A-EC92-8A1D-7607-9CE215EE6DC310901infoc&bvc=vod&bw=69406&deadline=1785329211&dl=0&e=ig8euxZM2rNcNbdlhoNvNC8BqJIzNbfqXBvEqxTEto8BTrNvN0GvT90W5JZMkX_YN0MvXg8gNEV4NC8xNEV4N03eN0B5tZlqNxTEto8BTrNvNeZVuJ10Kj_g2UB02J0mN0B5tZlqNCNEto8BTrNvNC7MTX502C8f2jmMQJ6mqF2fka1mqx6gqj0eN0B599M%3D&f=u_0_0&gen=playurlv3&lrs=-1&mid=0&nbs=1&nettype=0&og=hw&oi=0x2408823ca615d45439c4b84ea9f34d08&orderid=0%2C3&os=cosbv&platform=pc&qn_dyeid=05801ffafaecdc5c0027b0936a69da1b&sign=6ef1c2&traceid=trcMSmNMthESSn_0_e_N&uipk=5&uparams=e%2Ctrid%2Cuipk%2Cnbs%2Cplatform%2Cgen%2Cos%2Coi%2Cmid%2Cdeadline%2Cog&upsig=0e7c735dc9bac4861476c99b6bc47cc7",
                "base_url": "https://xy220x202x9x156xy.mcdn.bilivideo.cn:8082/v1/resource/upgcxcode/31/21/62131/62131_da3-1-100110.m4s?agrr=1&build=0&buvid=9A7E608A-EC92-8A1D-7607-9CE215EE6DC310901infoc&bvc=vod&bw=69406&deadline=1785329211&dl=0&e=ig8euxZM2rNcNbdlhoNvNC8BqJIzNbfqXBvEqxTEto8BTrNvN0GvT90W5JZMkX_YN0MvXg8gNEV4NC8xNEV4N03eN0B5tZlqNxTEto8BTrNvNeZVuJ10Kj_g2UB02J0mN0B5tZlqNCNEto8BTrNvNC7MTX502C8f2jmMQJ6mqF2fka1mqx6gqj0eN0B599M%3D&f=u_0_0&gen=playurlv3&lrs=-1&mid=0&nbs=1&nettype=0&og=hw&oi=0x2408823ca615d45439c4b84ea9f34d08&orderid=0%2C3&os=cosbv&platform=pc&qn_dyeid=05801ffafaecdc5c0027b0936a69da1b&sign=6ef1c2&traceid=trcMSmNMthESSn_0_e_N&uipk=5&uparams=e%2Ctrid%2Cuipk%2Cnbs%2Cplatform%2Cgen%2Cos%2Coi%2Cmid%2Cdeadline%2Cog&upsig=0e7c735dc9bac4861476c99b6bc47cc7",
                "backupUrl": [
                    "https://upos-sz-mirrorcos.bilivideo.com/upgcxcode/31/21/62131/62131_da3-1-100110.m4s?e=ig8euxZM2rNcNbdlhoNvNC8BqJIzNbfqXBvEqxTEto8BTrNvN0GvT90W5JZMkX_YN0MvXg8gNEV4NC8xNEV4N03eN0B5tZlqNxTEto8BTrNvNeZVuJ10Kj_g2UB02J0mN0B5tZlqNCNEto8BTrNvNC7MTX502C8f2jmMQJ6mqF2fka1mqx6gqj0eN0B599M=&trid=41fee4a83c404181b466435b5671d2eu&uipk=5&nbs=1&platform=pc&gen=playurlv3&os=cosbv&oi=0x2408823ca615d45439c4b84ea9f34d08&mid=0&deadline=1785329211&og=hw&upsig=0e7c735dc9bac4861476c99b6bc47cc7&uparams=e,trid,uipk,nbs,platform,gen,os,oi,mid,deadline,og&bvc=vod&nettype=0&bw=69406&lrs=-1&build=0&dl=0&f=u_0_0&qn_dyeid=05801ffafaecdc5c0027b0936a69da1b&agrr=1&buvid=9A7E608A-EC92-8A1D-7607-9CE215EE6DC310901infoc&orderid=0,3",
                    "https://upos-sz-mirrorcos.bilivideo.com/upgcxcode/31/21/62131/62131_da3-1-100110.m4s?e=ig8euxZM2rNcNbdlhoNvNC8BqJIzNbfqXBvEqxTEto8BTrNvN0GvT90W5JZMkX_YN0MvXg8gNEV4NC8xNEV4N03eN0B5tZlqNxTEto8BTrNvNeZVuJ10Kj_g2UB02J0mN0B5tZlqNCNEto8BTrNvNC7MTX502C8f2jmMQJ6mqF2fka1mqx6gqj0eN0B599M=&og=hw&oi=0x2408823ca615d45439c4b84ea9f34d08&trid=41fee4a83c404181b466435b5671d2eu&uipk=5&mid=0&platform=pc&deadline=1785329211&nbs=1&gen=playurlv3&os=cosbv&upsig=6caf1686d1c1dd0d3245a3e4a9560867&uparams=e,og,oi,trid,uipk,mid,platform,deadline,nbs,gen,os&bvc=vod&nettype=0&bw=69406&lrs=-1&dl=0&f=u_0_0&qn_dyeid=05801ffafaecdc5c0027b0936a69da1b&agrr=1&buvid=9A7E608A-EC92-8A1D-7607-9CE215EE6DC310901infoc&build=0&orderid=1,3",
                ],
                "backup_url": [
                    "https://upos-sz-mirrorcos.bilivideo.com/upgcxcode/31/21/62131/62131_da3-1-100110.m4s?e=ig8euxZM2rNcNbdlhoNvNC8BqJIzNbfqXBvEqxTEto8BTrNvN0GvT90W5JZMkX_YN0MvXg8gNEV4NC8xNEV4N03eN0B5tZlqNxTEto8BTrNvNeZVuJ10Kj_g2UB02J0mN0B5tZlqNCNEto8BTrNvNC7MTX502C8f2jmMQJ6mqF2fka1mqx6gqj0eN0B599M=&trid=41fee4a83c404181b466435b5671d2eu&uipk=5&nbs=1&platform=pc&gen=playurlv3&os=cosbv&oi=0x2408823ca615d45439c4b84ea9f34d08&mid=0&deadline=1785329211&og=hw&upsig=0e7c735dc9bac4861476c99b6bc47cc7&uparams=e,trid,uipk,nbs,platform,gen,os,oi,mid,deadline,og&bvc=vod&nettype=0&bw=69406&lrs=-1&build=0&dl=0&f=u_0_0&qn_dyeid=05801ffafaecdc5c0027b0936a69da1b&agrr=1&buvid=9A7E608A-EC92-8A1D-7607-9CE215EE6DC310901infoc&orderid=0,3",
                    "https://upos-sz-mirrorcos.bilivideo.com/upgcxcode/31/21/62131/62131_da3-1-100110.m4s?e=ig8euxZM2rNcNbdlhoNvNC8BqJIzNbfqXBvEqxTEto8BTrNvN0GvT90W5JZMkX_YN0MvXg8gNEV4NC8xNEV4N03eN0B5tZlqNxTEto8BTrNvNeZVuJ10Kj_g2UB02J0mN0B5tZlqNCNEto8BTrNvNC7MTX502C8f2jmMQJ6mqF2fka1mqx6gqj0eN0B599M=&og=hw&oi=0x2408823ca615d45439c4b84ea9f34d08&trid=41fee4a83c404181b466435b5671d2eu&uipk=5&mid=0&platform=pc&deadline=1785329211&nbs=1&gen=playurlv3&os=cosbv&upsig=6caf1686d1c1dd0d3245a3e4a9560867&uparams=e,og,oi,trid,uipk,mid,platform,deadline,nbs,gen,os&bvc=vod&nettype=0&bw=69406&lrs=-1&dl=0&f=u_0_0&qn_dyeid=05801ffafaecdc5c0027b0936a69da1b&agrr=1&buvid=9A7E608A-EC92-8A1D-7607-9CE215EE6DC310901infoc&build=0&orderid=1,3",
                ],
                "bandwidth": 69367,
                "mimeType": "video/mp4",
                "mime_type": "video/mp4",
                "codecs": "hev1.1.6.L120.90",
                "width": 512,
                "height": 384,
                "frameRate": "15",
                "frame_rate": "15",
                "sar": "1:1",
                "startWithSap": 1,
                "start_with_sap": 1,
                "SegmentBase": {"Initialization": "0-1021", "indexRange": "1022-5985"},
                "segment_base": {
                    "initialization": "0-1021",
                    "index_range": "1022-5985",
                },
                "codecid": 12,
            },
            ...
        ],
        "audio": [
            {
                "id": 30216,
                "baseUrl": "https://xy118x212x136x249xy.mcdn.bilivideo.cn:8082/v1/resource/upgcxcode/31/21/62131/62131_da3-1-30216.m4s?agrr=1&build=0&buvid=9A7E608A-EC92-8A1D-7607-9CE215EE6DC310901infoc&bvc=vod&bw=68667&deadline=1785329211&dl=0&e=ig8euxZM2rNcNbdlhoNvNC8BqJIzNbfqXBvEqxTEto8BTrNvN0GvT90W5JZMkX_YN0MvXg8gNEV4NC8xNEV4N03eN0B5tZlqNxTEto8BTrNvNeZVuJ10Kj_g2UB02J0mN0B5tZlqNCNEto8BTrNvNC7MTX502C8f2jmMQJ6mqF2fka1mqx6gqj0eN0B599M%3D&f=u_0_0&gen=playurlv3&lrs=-1&mid=0&nbs=1&nettype=0&og=hw&oi=0x2408823ca615d45439c4b84ea9f34d08&orderid=0%2C3&os=08cbv&platform=pc&qn_dyeid=05801ffafaecdc5c0027b0936a69da1b&sign=b90abc&traceid=trQSoqSpXhQuHD_0_e_N&uipk=5&uparams=e%2Cnbs%2Cplatform%2Cuipk%2Cmid%2Cgen%2Cos%2Cog%2Cdeadline%2Coi%2Ctrid&upsig=92d981039c13cf9f8b283ca3be6012a4",
                "base_url": "https://xy118x212x136x249xy.mcdn.bilivideo.cn:8082/v1/resource/upgcxcode/31/21/62131/62131_da3-1-30216.m4s?agrr=1&build=0&buvid=9A7E608A-EC92-8A1D-7607-9CE215EE6DC310901infoc&bvc=vod&bw=68667&deadline=1785329211&dl=0&e=ig8euxZM2rNcNbdlhoNvNC8BqJIzNbfqXBvEqxTEto8BTrNvN0GvT90W5JZMkX_YN0MvXg8gNEV4NC8xNEV4N03eN0B5tZlqNxTEto8BTrNvNeZVuJ10Kj_g2UB02J0mN0B5tZlqNCNEto8BTrNvNC7MTX502C8f2jmMQJ6mqF2fka1mqx6gqj0eN0B599M%3D&f=u_0_0&gen=playurlv3&lrs=-1&mid=0&nbs=1&nettype=0&og=hw&oi=0x2408823ca615d45439c4b84ea9f34d08&orderid=0%2C3&os=08cbv&platform=pc&qn_dyeid=05801ffafaecdc5c0027b0936a69da1b&sign=b90abc&traceid=trQSoqSpXhQuHD_0_e_N&uipk=5&uparams=e%2Cnbs%2Cplatform%2Cuipk%2Cmid%2Cgen%2Cos%2Cog%2Cdeadline%2Coi%2Ctrid&upsig=92d981039c13cf9f8b283ca3be6012a4",
                "backupUrl": [
                    "https://upos-sz-mirror08c.bilivideo.com/upgcxcode/31/21/62131/62131_da3-1-30216.m4s?e=ig8euxZM2rNcNbdlhoNvNC8BqJIzNbfqXBvEqxTEto8BTrNvN0GvT90W5JZMkX_YN0MvXg8gNEV4NC8xNEV4N03eN0B5tZlqNxTEto8BTrNvNeZVuJ10Kj_g2UB02J0mN0B5tZlqNCNEto8BTrNvNC7MTX502C8f2jmMQJ6mqF2fka1mqx6gqj0eN0B599M=&nbs=1&platform=pc&uipk=5&mid=0&gen=playurlv3&os=08cbv&og=hw&deadline=1785329211&oi=0x2408823ca615d45439c4b84ea9f34d08&trid=41fee4a83c404181b466435b5671d2eu&upsig=92d981039c13cf9f8b283ca3be6012a4&uparams=e,nbs,platform,uipk,mid,gen,os,og,deadline,oi,trid&bvc=vod&nettype=0&bw=68667&lrs=-1&agrr=1&buvid=9A7E608A-EC92-8A1D-7607-9CE215EE6DC310901infoc&build=0&dl=0&f=u_0_0&qn_dyeid=05801ffafaecdc5c0027b0936a69da1b&orderid=0,3",
                    "https://upos-sz-mirror08c.bilivideo.com/upgcxcode/31/21/62131/62131_da3-1-30216.m4s?e=ig8euxZM2rNcNbdlhoNvNC8BqJIzNbfqXBvEqxTEto8BTrNvN0GvT90W5JZMkX_YN0MvXg8gNEV4NC8xNEV4N03eN0B5tZlqNxTEto8BTrNvNeZVuJ10Kj_g2UB02J0mN0B5tZlqNCNEto8BTrNvNC7MTX502C8f2jmMQJ6mqF2fka1mqx6gqj0eN0B599M=&platform=pc&mid=0&deadline=1785329211&nbs=1&gen=playurlv3&oi=0x2408823ca615d45439c4b84ea9f34d08&trid=41fee4a83c404181b466435b5671d2eu&uipk=5&os=08cbv&og=hw&upsig=14592e6d6e3fb53f2b59838895e827bd&uparams=e,platform,mid,deadline,nbs,gen,oi,trid,uipk,os,og&bvc=vod&nettype=0&bw=68667&lrs=-1&agrr=1&buvid=9A7E608A-EC92-8A1D-7607-9CE215EE6DC310901infoc&build=0&dl=0&f=u_0_0&qn_dyeid=05801ffafaecdc5c0027b0936a69da1b&orderid=1,3",
                ],
                "backup_url": [
                    "https://upos-sz-mirror08c.bilivideo.com/upgcxcode/31/21/62131/62131_da3-1-30216.m4s?e=ig8euxZM2rNcNbdlhoNvNC8BqJIzNbfqXBvEqxTEto8BTrNvN0GvT90W5JZMkX_YN0MvXg8gNEV4NC8xNEV4N03eN0B5tZlqNxTEto8BTrNvNeZVuJ10Kj_g2UB02J0mN0B5tZlqNCNEto8BTrNvNC7MTX502C8f2jmMQJ6mqF2fka1mqx6gqj0eN0B599M=&nbs=1&platform=pc&uipk=5&mid=0&gen=playurlv3&os=08cbv&og=hw&deadline=1785329211&oi=0x2408823ca615d45439c4b84ea9f34d08&trid=41fee4a83c404181b466435b5671d2eu&upsig=92d981039c13cf9f8b283ca3be6012a4&uparams=e,nbs,platform,uipk,mid,gen,os,og,deadline,oi,trid&bvc=vod&nettype=0&bw=68667&lrs=-1&agrr=1&buvid=9A7E608A-EC92-8A1D-7607-9CE215EE6DC310901infoc&build=0&dl=0&f=u_0_0&qn_dyeid=05801ffafaecdc5c0027b0936a69da1b&orderid=0,3",
                    "https://upos-sz-mirror08c.bilivideo.com/upgcxcode/31/21/62131/62131_da3-1-30216.m4s?e=ig8euxZM2rNcNbdlhoNvNC8BqJIzNbfqXBvEqxTEto8BTrNvN0GvT90W5JZMkX_YN0MvXg8gNEV4NC8xNEV4N03eN0B5tZlqNxTEto8BTrNvNeZVuJ10Kj_g2UB02J0mN0B5tZlqNCNEto8BTrNvNC7MTX502C8f2jmMQJ6mqF2fka1mqx6gqj0eN0B599M=&platform=pc&mid=0&deadline=1785329211&nbs=1&gen=playurlv3&oi=0x2408823ca615d45439c4b84ea9f34d08&trid=41fee4a83c404181b466435b5671d2eu&uipk=5&os=08cbv&og=hw&upsig=14592e6d6e3fb53f2b59838895e827bd&uparams=e,platform,mid,deadline,nbs,gen,oi,trid,uipk,os,og&bvc=vod&nettype=0&bw=68667&lrs=-1&agrr=1&buvid=9A7E608A-EC92-8A1D-7607-9CE215EE6DC310901infoc&build=0&dl=0&f=u_0_0&qn_dyeid=05801ffafaecdc5c0027b0936a69da1b&orderid=1,3",
                ],
                "bandwidth": 68646,
                "mimeType": "audio/mp4",
                "mime_type": "audio/mp4",
                "codecs": "mp4a.40.2",
                "width": 0,
                "height": 0,
                "frameRate": "",
                "frame_rate": "",
                "sar": "",
                "startWithSap": 0,
                "start_with_sap": 0,
                "SegmentBase": {"Initialization": "0-932", "indexRange": "933-5908"},
                "segment_base": {"initialization": "0-932", "index_range": "933-5908"},
                "codecid": 0,
            },
            ...
        ],
        "dolby": {"type": 0, "audio": None},
        "flac": None,
    },
    ...
}
```

可以发现，返回结果 `["dash"]["video"]` 和 `["dash"]["audio"]` 两个列表中的字典对象存储了不同的音视频流，对象 `baseUrl` `backup_url` 等键提供了音视频流链接。与此同时，对象 `codecs` 键给出了其格式。深入探究后可以发现，`id` 键的值对应了音视频流的品质。此处 `id = 32` 对应 480P 的视频清晰度，`id = 30216` 对应 64K 的音频清晰度。模块提供 `video.VideoQuality` 和 `video.AudioQuality` 两个枚举类，举个例子，`VideoQuality._480P = 32`，`AudioQuality._64K = 30216`。

针对下载视频，模块同时提供了一个工具类，专门用于处理视频下载地址字典，即 `video.VideoDownloadURLDataDetecter`。其提供 `detect` 和 `detect_best_streams` 方法，这里我们只需要一对清晰度最好的音视频流，使用 `detect_best_streams` 即可。

``` python
from bilibili_api import sync, video


async def main() -> None:
    v = video.Video(aid=2)
    download_url = await v.get_download_url(page_index=0)
    detecter = video.VideoDownloadURLDataDetecter(data=download_url)
    vstream, astream = detecter.detect_best_streams()
    vurl, aurl = vstream.url, astream.url


sync(main())
```

同时，`detect` `detect_best_streams` 函数支持一系列参数，例如 `video_min_quality` 用于限制视频最低清晰度，传入参数为 `video.VideoQuality` 类型，`no_dolby` 可过滤掉杜比视界。`detect_best_streams` 通常情况下返回两个流，一个是视频流，一个是音频流，分别是 `video.VideoStreamDownloadURL` 和 `video.AudioStreamDownloadURL` 实例，通过这些实例我们可以获取有关视频音频流的更多信息，但此处我们只需要 url。

有了 url 就可以下载了。下载的方式不少，从 `curl` 到 `aria2c` 均可。但是，此处的 url 需要加上特定请求头访问，否则会 403。一般只需要加上 `User-Agent` 和 `Referer` 即可正常访问，以下是模块内部使用的请求头：

``` python
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Referer": "https://www.bilibili.com/",
}
```

下载逻辑不光可以在外部程序实现，也可以在原来的 python 代码上追加。这里介绍一种特殊的方式，即调用模块内部使用的会话进行下载。模块并未原生实现网络请求功能，也需要第三方库提供会话，然后调用会话的函数请求。模块使用的会话实例可以通过 `get_session` 函数获取。

``` python
from bilibili_api import get_session, get_selected_client


async def main() -> None:
    ...
    sess = get_session()
    print(get_selected_client(), sess)


sync(main())
```

`get_session` 返回的会话是未经处理的第三方库的会话对象（例如 `curl_cffi.requests.AsyncSession` `aiohttp.ClientSession` `httpx.AsyncClient`），需要看模块此时选择的是哪一个第三方库。这可以通过 `get_selected_client` 查询。模块在允许的条件下，按照 `curl_cffi` `aiohttp` `httpx` 的优先级选择第三方请求库。如果想要指定请求库，可以利用 `select_client` 进行切换。以下是选择 `curl_cffi` 时，上述代码的输出：

``` plaintext
('curl_cffi', <class 'bilibili_api.clients.CurlCFFIClient.CurlCFFIClient'>) <curl_cffi.requests.session.AsyncSession object at 0x120284980>
```

为方便对这些会话实例的调用，模块对不同第三方库的会话进行了统一封装，即使用抽象类 `bilibili_api.BiliAPIClient` 封装需要的网络请求功能。此时调用会话就可以采用统一的一套函数，而不用一一适配兼容了。只需要调用 `get_client` 即可获取 `BiliAPIClient` 实例。借此，我们可以实现以下的简易下载函数。

``` python
import anyio
from bilibili_api import get_bili_headers


async def download(url: str, out: str):
    client = get_client()
    dwn_id = await client.download_create(url=url, headers=get_bili_headers())
    bts = 0
    tot = client.download_content_length(cnt=dwn_id)
    async with await anyio.open_file(out, "wb") as file:
        while True:
            bts += await file.write(await client.download_chunk(cnt=dwn_id))
            print(f"{out} [{bts} / {tot}]", end="\r")
            if bts == tot:
                break
    await client.download_close(cnt=dwn_id)
    print()
```

此处代码使用 `\r` 操作符刷新输出行，打印下载进度。`get_bili_headers` 是模块提供的获取一整套请求头的函数，包括我们需要的 `User-Agent` 和 `Referer`。此处使用了 AnyIO 库进行异步文件 IO，AnyIO 也是模块的依赖之一。

然后就是对 `BiliAPIClient` 函数的具体介绍，虽然这边未使用到，但其最重要的函数是 `request` 函数，用于发起一般网络请求，详情可翻阅文档。此处使用了四个函数，`download_create` 用于创建流式下载的响应，`download_content_length` 用于获取下载文件的长度，`download_chunk` 用于片段下载，`download_close` 用于下载完成后关闭响应。实际上，`BiliAPIClient` 是模块进行网络请求的核心，所有的请求均从这个类中通过，无论是正常的网络请求，还是与服务器连接的 WebSocket，亦或是此处的基本下载功能。

模块已经将以上的下载函数封装为了 `bilibili_api.bili_simple_download`，供日常使用。下面将直接调用此函数。

终于，此处我们使用 `bili_simple_download` 完成了视频下载，接下来到混流了。此处混流直接使用 FFMpeg。这里为防止同步任务堵塞异步事件循环/进程，使用了 `anyio.to_thread.run_sync` 运行 `os.system`，虽然在目前的简单场景下没有这种必要，而且 FFMpeg 没有那么慢，但是，毕竟快速上手不能坏了代码规范。

``` python
import os

import anyio.to_thread
from bilibili_api import bili_simple_download, sync, video


async def main() -> None:
    v = video.Video(aid=2)
    download_url = await v.get_download_url(page_index=0)
    detecter = video.VideoDownloadURLDataDetecter(data=download_url)
    vstream, astream = detecter.detect_best_streams()
    vurl, aurl = vstream.url, astream.url  # type: ignore
    await bili_simple_download(vurl, "video.m4s")
    await bili_simple_download(aurl, "audio.m4s")
    await anyio.to_thread.run_sync(
        os.system,
        "ffmpeg -i video.m4s -i audio.m4s -vcodec copy -acodec copy video.mp4",
    )


sync(main())
```

运行后，在运行目录下即有下载完成视频 `video.mp4`。

## 后端请求转发接口

相信通过上面的示例，读者已鉴赏过了模块不同部分的不同功能和接口类型，实际上，上文介绍的内容已经涵盖了模块约 80% 的功能，包括基本的函数使用、类的使用、`AsyncEvent`、`login_v2` 和简单的 `BiliAPIClient` 的使用。

然后是最后的主题，这绝对是最特殊的一个了。`bilibili-api`，众所周知，是 Python 模块，而实际上，在前端中也可以对其进行使用。~~很简单，自行写一个 `FastAPI` 后端。绑定模块的函数即可。~~这里给到一个将模块快速部署为后端的方式：

```python
# 需要单独安装 fastapi 和 uvicorn

import uvicorn

from bilibili_api.tools.parser import get_fastapi

if __name__ == "__main__":
    uvicorn.run(get_fastapi(), host="0.0.0.0", port=9000)
```

下面的内容就直接引用 `bilibili_api/tools/parser/README.md` 中的内容了。

### 后端转发接口的功能

可以用来开启一个 `uvicorn` 后端，前端不直接访问哔哩哔哩原接口，而是通过这个后端进行请求转发，就不会跨域了。

### 用法

```python
from bilibili_api import user, sync


async def main():
    return await user.User(uid=2).get_user_info()


print(sync(main()))
```

上述代码现在只需要一个链接就能实现。

[http://localhost:9000/user.User(2).get_user_info()](http://localhost:9000/user.User(2).get_user_info())

你也可以使用指名参数。

[http://localhost:9000/user.User(uid=2).get_user_info()](http://localhost:9000/user.User(uid=2).get_user_info())

使用请求参数 `query` 储存值，接着在函数中使用 `type` 作为参数值。

[http://localhost:9000/comment.get_comments(708326075350908930,type,1)?type=comment.CommentResourceType.DYNAMIC](http://localhost:9000/comment.get_comments(708326075350908930,type,1)?type=comment.CommentResourceType.DYNAMIC)

使用 `.key` 的方式对获取的字典结果取值，获得更精细数据，节省带宽。使用 `.index` 的方式对列表结果取元素，例如：

[http://localhost:9000/user.User(2).get_user_info().elec.show_info.list.0.uname](http://localhost:9000/user.User(2).get_user_info().elec.show_info.list.0.uname)

使用 `?max_age=86400` 请求参数设置缓存，这里是 `86400` 秒。

### FAQ

> 为什么要解析函数，直接用 `eval()` 不好吗？

有安全隐患，用解析函数一步一步调用比较安全。

> 参数值除了可以使用数字，还支持什么呢？

常规值支持整数、浮点数 `None` `True` `False` 以及 `"` 或 `'` 开头并结尾的字符串。

[http://localhost:9000/video.Video(bvid="BV1ju411T7so").get_aid()](http://localhost:9000/video.Video(bvid="BV1ju411T7so").get_aid())

此外，你也可以使用一个可被解析的值作为参数值，例如：

[http://localhost:9000/channel_series.ChannelSeries(id_=1845727,uid=148524702,type_=channel_series.ChannelSeriesType.SEASON).get_meta()](http://localhost:9000/channel_series.ChannelSeries(id_=1845727,uid=148524702,type_=channel_series.ChannelSeriesType.SEASON).get_meta())

> 最后，感谢 @Drelf2018 为 bilibili-api 带来后端请求转发接口，~~也算是弥补了模块做不了后端的问题了~~。

---

感谢各位读者耐心读到此处。

写快速上手的本意是更多地介绍模块不同的功能，如果仅看 `README` 中的例子，用户不一定能学会使用其他接口的方法、使用 `AsyncEvent` 等模块提供的工具类的方法。虽说有 API 示例在，但许多示例已经年久失修(笔者正在考虑接下来去修)，有的功能甚至没有配备示例，如果光看 API 文档，估计多数人都无法理解如何使用各种函数和类。

为此，快速上手中挑选的例子多为一些经典的功能，最能体现模块功能多样性的例子，前文也提到过，这里面涉及的内容能占到整个模块功能的 80%，这个比例不会偏高，只可能偏低。因为模块几乎所有功能，都可以归类到快速上手中的具体例子中。

希望读者阅读完后可以有所收获，并可以开始熟练地使用模块。

当然，因为是快速上手，所以有的部分没有深入去写，也不可能把所有内容全部赘述一遍。可以继续阅读 `通用` `子模块相关` `进阶` 部分的文档，以更近一步了解模块。

以上就是快速上手部分的全部内容。
