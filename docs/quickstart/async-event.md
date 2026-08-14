# 使用 `AsyncEvent`

`AsyncEvent` 是模块提供的一个基础类，实现了发布-订阅模式的异步事件机制，常用于长时间运行的异步操作中，例如上传视频、连接直播间以及消息监听。在这些异步过程中，模块会通过 `AsyncEvent` 的方法发布事件——例如收到弹幕后发布弹幕事件，上传视频时汇报进度也可以发布事件。事件发布后，`AsyncEvent` 会调用用户提供的回调函数，从而实现事件的订阅。回调函数既可以是同步函数，也可以是异步函数，但建议使用异步函数，或至少是不阻塞的同步函数。

接下来将用模块中的两个典型 `AsyncEvent` 类作演示，分别是 `live.LiveDanmaku` 和 `session.Session`。

## 1. `live.LiveDanmaku`

众所周知，哔哩哔哩网页端通过 WebSocket 与直播服务器连接。`live.LiveDanmaku` 的核心功能，就是调用模块的 WebSocket 连接能力完成与直播间的交互。交互分为发送消息与接收消息：这里发送的消息主要是心跳包，模块会自动发送，因此使用 `live.LiveDanmaku` 时，只需关注 WebSocket 收到的消息即可。

收到消息后，模块会对其进行解码，一般会得到 JSON 格式的数据。大约从 2025 年 7 月起，直播间消息中开始出现 protobuf 格式的数据，此时 `live.LiveDanmaku` 会自动将 protobuf 数据转换为 JSON 格式。总之，最终回调函数拿到的数据，一般是一个 JSON 反序列化后的字典对象，与通过 HTTP 调用 API 接口返回的数据不会有太大差别。

对于 `LiveDanmaku` 类，回调函数只需接收一个 `dict` 类型参数即可。绑定回调函数既可以使用 `add_event_listener` 方法，也可以使用 `on` 装饰器，如下：

``` python
@dm.on("DANMU_MSG")
async def handle_dm_msg(data: dict) -> None:
    pass
```

通过上述方式即可完成事件回调的绑定，该操作应在异步过程启动之前执行。绑定完回调后，即可启动异步过程；对 `live.LiveDanmaku` 来说，就是开始连接直播间。

使用 `connect` 方法即可连接直播间，该方法会运行连接直播间的主程序。连接建立后仍需持续接收信息，因此该方法是阻塞的，只有主程序结束后才会返回。直播间理论上可以无限期保持连接，因此主程序需要手动结束，否则程序永远无法退出。可以使用 `disconnect` 方法关闭直播间的连接。

这里以终端环境下的演示为主，因此使用 `Ctrl + C` 作为终止信号，只需捕获 `KeyboardInterrupt` 异常，即可优雅地结束程序。理论上，取消直播间连接会在 `await dm.connect()` 处抛出 `asyncio.CancelledError`，但模块中所有 `AsyncEvent` 类在运行过程中都会主动捕获该异常，因此这里无需再处理。

``` python
dm = live.LiveDanmaku(room_display_id=33989, credential=credential)
# 建议加入凭据类连接直播间，否则……可以尝试退出登录后体验一下网页端直播页面
try:
    await dm.connect()
except KeyboardInterrupt:
    await dm.disconnect()
```

可以先尝试不绑定任何回调直接运行以上代码，会发现终端输出了一些日志信息。这是因为模块在 `live.LiveDanmaku` 中配置了日志，用于输出直播间连接过程中的状态，例如正在连接服务器、认证成功、正在关闭连接等。稍等片刻，如果一切顺利，模块将成功连上服务器并显示「认证成功」。此时按下 `Ctrl + C`，程序就能优雅地退出了。

```shell
python3 test-trio.py
[33989][2026-08-07 22:47:17,956][INFO] 准备连接直播间 33989
[33989][2026-08-07 22:47:19,121][INFO] 正在尝试连接主机： wss://zj-cn-live-comet.chat.bilibili.com:2245/sub
[33989][2026-08-07 22:47:19,239][INFO] 连接服务器并认证成功
^C%
```

确认可以正常连接直播间后，就可以正式绑定回调函数，开始获取信息（主要是弹幕）。这里我们假设对传入数据的结构一无所知，于是先在回调函数中把数据原样打印出来：

``` python
@dm.on("DANMU_MSG")
def dm_msg(data: dict) -> None:
    print(data)
```

`@dm.on` 的括号中是事件名称，`DANMU_MSG` 对应单条弹幕。这些事件名称可以在 `live.LiveDanmaku` 的 docstring 中查到，也可以翻阅 `live.LiveDanmaku` 类的文档查看。

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

这堆数据显然还需要进一步处理，此处省略处理过程，最后可以通过以下键值获取单条弹幕的各种信息：

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

其实，前文代码中的 `try-catch` 可以省去，程序依旧能正常运行、不会中断（~~可以试试~~）。异常仍然是会出现的，只不过会被模块内部捕获——它们最终也会被抛出，但抛出的方式比较温柔：通过 `__TASK_EXCEPTION__` 事件发布出来。

``` python
@dm.on("__TASK_EXCEPTION__")
def raise_exception(e: Exception) -> None:
    raise e


# 用以上代码即可将所有错误全部抛出，然后程序可能就中断了
# 显然，在这个回调函数中再有错误抛出，模块就不会再发布 __TASK_EXCEPTION__ 了，而是直接抛出异常。
```

因此，如果有调试需求——例如这里报错后最后的 `print` 不会执行，导致漏掉弹幕——就可以考虑监听 `__TASK_EXCEPTION__` 事件。

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

这样看着有些单调：终端下弹幕一行行打印出来，总有种既不弹、又不幕、还不姬的感觉。那就勉为其难再多实现一个功能吧——尝试复刻用户进入直播间的效果。做法是：监听到进入直播间的消息后，在终端打印，随后不换行，而是将光标移回行首（`\r`）。这样当多个人陆续进入直播间时，就会有种「进入直播间那一行在滚动」的感觉。就这么办。

我们再用「打印大法」获取一条用户进入直播间的消息示例，该消息对应的事件名称为 `INTERACT_WORD_V2`。

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

可以说，前面弹幕的数据结构虽然杂乱，但至少很多字段还能看懂；而进入直播间获取到的数据……已经「进化」成了字节数据（服务端已对字节进行了 base64 加密），简直不给人留下任何理解的可能。

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

可以看到，protobuf 数据已经被解码成正常的 JSON 格式，接下来的处理也就简单了：

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

![艹艹艹艹艹艹艹艹艹艹艹艹艹艹艹艹艹艹艹](../img/live-demonstration.gif)

上面的代码只需要监听两个事件，也只用到两个函数。但事件一旦多起来，就需要编写多个函数分别处理，有时会相当麻烦。

为此，模块提供了一个奇妙的事件 `__ALL__`：当除 `__ALL__` 与 `__TASK_EXCEPTION__` 之外的任何事件发布时，它都会被额外发布一次。

``` python
@dm.on("__ALL__")
def on_all(info: dict) -> None:
    event_name = info["name"]
    data = info["data"]
    print(event_name, data)
```

绑定该回调后再连接直播间，就能感受到被信息包围的氛围了。

## 2. `session.Session`

接下来要介绍的是 `session.Session`，一个用于监听私聊消息的 `AsyncEvent` 类。与 `live.LiveDanmaku` 这样以 WebSocket 为核心的异步过程不同，它的异步过程稍显另类——本质上是一个定时任务：每隔 6 秒刷新一次私聊信息，拉取新消息。不仅如此，`session.Session` 还支持消息回复功能，这使得我们可以借此部署一个简易的聊天机器人。

事实上，直播间场景下也可以使用 `live.LiveRoom` 中的函数发送弹幕（即回复弹幕），不过显然不如私聊的收发消息来得纯粹。不同于直播间，私聊支持多种类型的消息，这里我们只考虑两种基本类型：文字和图片。

如前文所述，私聊中会出现多种类型的消息；不仅如此，除了消息正文外，还包含其他元信息，例如发送者、发送时间等。因此，模块使用 `session.Event` 类对抓取到的信息进行了包装。这个类的属性很多，这里我们只关心最重要的 `content` 属性，即事件内容。至于事件内容的类型，可以通过 `msg_type` 属性判断，也可以像下面这样直接按类型绑定回调：

``` python
@session.on(EventType.TEXT)  # 当收到文字信息时触发
async def reply(event: Event):
    pass


@session.on(EventType.PICTURE)  # 当收到图片时触发
async def filter_pic(event: Event):
    pass
```

现在问题来了：收到文字时，`event.content` 是 `str`，毋庸置疑；那收到图片时，`event.content` 又是什么呢？答案是模块提供的 `Picture` 类（`bilibili_api.Picture`）。

`Picture` 类本质上是对 `PIL.Image.Image` 的异步封装（此处假设读者对 `Python Imaging Library`，即 `pillow`，有基本了解）。接下来将分别介绍：如何初始化一个 `Picture` 类，如何将其转换为图片内容、文件乃至链接，以及如何对 `Picture` 类包装的 `PIL.Image.Image` 对象进行操作。

初始化 `PIL.Image.Image` 只需要提供一个字节流即可（`Image.open` 不会一次性读取全部内容）。模块为此提供了 `Picture.from_file` 和 `Picture.from_content` 两个同步函数，可以直接在异步函数中使用。如果需要加载网络图片，则使用异步方法 `Picture.load_url`，因为该方法内部涉及网络请求。

`Picture` 对象包含以下属性：`url` 为网络链接或本地文件地址；如果图片是从字节加载的，或已经过修改，`url` 会被设置为 `<bytes>.{extension}`，其中 `extension` 为图片后缀名，也是 `Picture` 对象中的一个属性。此外还有 `width`、`height` 属性，分别表示图片的宽度和高度。

初始化 `Picture` 对象后，可以通过异步函数 `Picture.content` 获取图片的字节内容，通过异步函数 `Picture.download` 将图片保存到本地文件。也可以借助哔哩哔哩动态相关功能将其上传至服务器，只需调用 `Picture.upload(credential=Credential(...))` 即可；上传成功后，读取 `Picture` 的 `url` 属性即可获得链接。

`Picture` 类还提供了 `Picture.image_call` 方法，用于对内部的 `PIL.Image.Image` 对象进行操作。例如，`Image.resize((width, height))` 可以调整图片大小并返回一个新的 `Image` 对象。这一过程可能是阻塞的，因此模块会在一个工作进程中执行该函数，以免阻塞事件循环；函数执行完成后，`Picture` 类会将内部包装的图片更新为返回结果。这正是 `Picture.image_call` 所做的工作。此处调用 `await Picture.image_call("resize", (width, height))`，即可调整 `Picture` 对应图片的大小。

接下来就可以编写逻辑了。对于文字消息，我们只特殊识别两个内容：收到 `/close` 时结束轮询，收到 `/pic` 时发送一张图片，其余情况统一回复「你好」。

说到结束轮询，就不得不提开始轮询。`session.Session` 使用 `start` 函数开始异步过程，使用 `close` 函数结束异步过程——注意前者是异步函数，后者是同步函数。收到 `/close` 后，只需调用 `close` 即可。

回复消息可以使用 `session.reply`，它接受两个参数：第一个是需要回复的消息，即回调函数的参数 `event`；第二个是具体内容——如果是文本，直接传入文本即可；如果是图片，则需要使用 `Picture` 类。可以先用 `Picture.from_file("path/to/pic")` 加载本地图片，再通过异步函数 `upload` 将其上传，随后即可发送。

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

如果收到的是图片，我们实现两个逻辑：先把图片下载到本地（调用 `download` 函数），然后给图片加一层滤镜再发回去。加滤镜可以使用 `Image.filter` 函数，在模块中也可以使用 `Picture.image_call("filter", ...)`（此处已进行针对异步环境的包装）；回复图片仍然使用 `reply` 方法。最终的回调函数如下：

``` python
@session.on(EventType.PICTURE)
async def save_pic(event: Event):
    await event.content.download(event.content.url.split("/")[-1])  # type: ignore
    # 截取 url 最后一节作文件名，保存在当前目录
    await event.content.image_call("filter", ImageFilter.SMOOTH)  # type: ignore
    # 此处用的滤镜时平滑滤波
    await session.reply(event, event.content)  # type: ignore
```

主程序部分沿用前文连接直播间的写法，收到 `Ctrl + C` 时停止轮询。

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
