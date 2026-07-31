# 快速上手

_Table of Contents_

- [模块安装](#模块安装)
- [使用 `Video`](#使用-video)
- [使用 `rank`](#使用-rank)
- [使用 `AsyncEvent`](#使用-asyncevent)
- [使用 `login_v2`](#使用-login_v2)
- [下载视频](#下载视频)

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

模块通过抽象第三方请求库的方法，提供了对任意异步网络请求库的支持，因此理论上所有的异步网络请求库，模块都可以正常对其进行调用。模块源代码中已经实现了对 `curl_cffi` `aiohttp` 和 `httpx` 的支持，因此以上三个异步请求库可直接调用。如果需要使用其他网络请求库，你可能需要自行适配，相关文档请阅读 `模块二次开发` 下的 `BiliAPIClient 类` 部分内容。

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

---

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

## 使用 `login_v2`

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

运行代码可以得到很长一串返回字典，视频下载 url 就在其中，但这些数据显然不能直接使用，需要进一步处理。事实上，模块许多函数返回的字典都需要这进一步处理的操作。这些操作主要在确认所需数据的访问路径，或者说，找数据。此处自然是要在这个字典中找 url。

以下是返回字典格式化输出结果（部分）：

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

可以发现，返回结果 `["dash"]["video"]` 和 `["dash"]["audio"]` 两个列表中的字典对象存储了不同的音视频流，对象 `baseUrl` `backup_url` 等键提供了音视频流链接。与此同时，对象 `codecs` 键给出了其格式。深入探究后可以发现，`id` 键的值对应了音视频流的品质。此处 `id = 32` 对应 480P 的视频清晰度，`id = 30216` 对应 64K 的音频清晰度。

很多时候，需要获取的信息都能在接口返回值中找到（前提是得找对接口），有的值则会以一种映射的形式体现在接口返回值中，例如视频/音频清晰度。此时需要使用者自行探索数据结构，有时还需要探究数值背后的映射。

幸运的是，部分数值上的映射模块已经内置，例如视频分区对应的 tid，相关信息可以通过 `video_zone` 或 `video_zone_v2`（新版分区，也是近期视频分区搜索功能维护的原因） 两个子模块查询，此处不展开。此处，模块提供 `video.VideoQuality` 和 `video.AudioQuality` 两个枚举类，举个例子，`VideoQuality._480P = 32`，`AudioQuality._64K = 30216`。包括有的接口参数的传入，需要一些令人费解的数值参数，可实际其背后都有意义，模块的函数设计通常会将其封装为枚举类，调用接口时传入枚举类即可。以拉黑用户为例，通过以下代码即可完成操作。

``` python
u = user.User(uid=2, credential=credential)
await u.modify_relation(user.RelationType.BLOCK)
```

更幸运的是，模块提供了一个工具类，专门用于处理视频下载地址字典，即 `video.VideoDownloadURLDataDetecter`。其提供 `detect` 和 `detect_best_streams` 方法，这里我们只需要一对清晰度最好的音视频流，使用 `detect_best_streams` 即可。

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

然后就是对 `BiliAPIClient` 函数的具体介绍，虽然这边未使用到，但其最重要的函数是 `request` 函数，用于发起一般网络请求，详情可翻阅文档。此处使用了四个函数，`download_create` 用于创建流式下载的响应，`download_content_length` 用于获取下载文件的长度，`download_chunk` 用于片段下载，只支持线性下载，且不支持自定义单次获取片段长度，`download_close` 用于下载完成后关闭响应。

下载相关函数槽点确实很多，以下是狡辩。首先，下载功能在模块中应用极少，唯一使用是 `InteractiveVideoDownloader` 需要一个默认下载函数，然后，`download_chunk` 为什么不支持指定片段长度？因为模块最早在兼容第三方请求库的时候，`curl_cffi` 尚未完成对这项功能的支持，不支持指定片段长度，鉴于下载功能确实不重要的情况下，模块设计抽象接口时也未保留片段长度参数。最后是，除了现在的情景以外，用户都无需手动使用 `BiliAPIClient` 的 `download_xxx` 函数。

现在读者大抵能猜到为什么视频下载放在了快速上手最后的部分，因为此部分在为了 `BiliAPIClient` 的醋包了一个下载的饺子。`BiliAPIClient` 是模块进行网络请求的核心，所有的请求均从这个类中通过，无论是正常的网络请求，还是与服务器连接的 WebSocket，亦或是鸡肋的下载功能。幸运的是，读者在此无需使用鸡肋的下载功能，因为模块已经贴心地将以上的下载函数封装为了 `bilibili_api.bili_simple_download`，供日常使用。此部分只需要了解 `BiliAPIClient` 定位与作用即可。

同时还请放心，`BiliAPIClient` 的 `request` 和 WebSocket 相关函数设计相较下载功能来说，还是挺科学与人性化的，前者基本按照 `requests` 设计，后者基本按照 `aiohttp` 设计。

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

运行后，在运行目录下即有下载完成视频 `video.mp4`。此处代码未编写清理中间文件 `video.m4s` 和 `audio.m4s` 的逻辑，就当作是注重简约性吧。

可以发现在模块的封装下，整个下载视频的代码非常简单，遗憾的是，其他功能的封装未必有那么完善，因此本部分提到的一些技巧与方法，仍有必要熟悉，例如处理返回的字典，使用 `BiliAPIClient` 进行适当网络请求，以备更复杂的情景或任务。
