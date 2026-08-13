# 使用 `rank` `hot`

承接上文，接下来要介绍的是 `rank` `hot` 模块，用于查询“热门”页面信息。“热门”页面通常是排行榜，还有入站必刷视频的列表。此处模块提供的并非一个个类，而是大量的函数。

打开[哔哩哔哩热门页面](https://www.bilibili.com/v/popular/all?spm_id_from=333.1007.0.0)，可以看到其分为五个部分：综合热门、每周必看、入站必刷、排行榜及全站音乐榜。

先从热门和入站必刷视频看起。对应函数在 `hot` 中，分别是 `get_hot_videos` 和 `get_history_popular_videos`。

## 1. 入站必刷视频

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

## 2、热门页视频

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

## 3、每周必看

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

## 4、排行榜

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
