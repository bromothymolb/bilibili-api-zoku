# 后端请求转发接口

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

## 功能

可以用来开启一个 `uvicorn` 后端，前端不直接访问哔哩哔哩原接口，而是通过这个后端进行请求转发，就不会跨域了。

## 用法

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

## FAQ

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
