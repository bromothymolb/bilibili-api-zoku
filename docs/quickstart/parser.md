# 后端请求转发接口

相信通过前面的示例，读者已经领略了模块各部分的功能与接口类型。实际上，上文介绍的内容已经涵盖了模块约 80% 的功能，包括基本函数的使用、类的使用、`AsyncEvent`、`login_v2` 以及简单的 `BiliAPIClient` 使用。

接下来是最后一个主题，也是最为特殊的一个。众所周知，`bilibili-api` 是一个 Python 模块，但实际上，我们也可以在前端中使用它。~~最简单的办法是自己写一个 `FastAPI` 后端，把模块的函数绑定上去。~~这里给出一种将模块快速部署为后端的方式：

```python
# 需要单独安装 fastapi 和 uvicorn

import uvicorn

from bilibili_api.tools.parser import get_fastapi

if __name__ == "__main__":
    uvicorn.run(get_fastapi(), host="0.0.0.0", port=9000)
```

以下内容直接引用自 `bilibili_api/tools/parser/README.md`。

## 功能

可以开启一个 `uvicorn` 后端。前端不再直接访问哔哩哔哩原始接口，而是通过该后端进行请求转发，从而避免跨域问题。

## 用法

```python
from bilibili_api import user, sync


async def main():
    return await user.User(uid=2).get_user_info()


print(sync(main()))
```

上述代码现在只需一个链接即可实现。

[http://localhost:9000/user.User(2).get_user_info()](http://localhost:9000/user.User(2).get_user_info())

也可以使用关键字参数。

[http://localhost:9000/user.User(uid=2).get_user_info()](http://localhost:9000/user.User(uid=2).get_user_info())

使用请求参数 `query` 存储值，接着在函数中使用 `type` 作为参数值。

[http://localhost:9000/comment.get_comments(708326075350908930,type,1)?type=comment.CommentResourceType.DYNAMIC](http://localhost:9000/comment.get_comments(708326075350908930,type,1)?type=comment.CommentResourceType.DYNAMIC)

对返回的字典结果，可以使用 `.key` 的方式取值，以获得更精细的数据、节省带宽；对列表结果，则可以使用 `.index` 的方式取元素，例如：

[http://localhost:9000/user.User(2).get_user_info().elec.show_info.list.0.uname](http://localhost:9000/user.User(2).get_user_info().elec.show_info.list.0.uname)

使用请求参数 `?max_age=86400` 可以设置缓存时长，这里为 `86400` 秒。

## FAQ

> 为什么要解析函数，直接用 `eval()` 不好吗？

直接使用 `eval()` 存在安全隐患，而通过解析函数一步步调用则安全得多。

> 参数值除了可以使用数字，还支持什么呢？

常规参数值支持整数、浮点数、`None`、`True`、`False`，以及以 `"` 或 `'` 开头和结尾的字符串。

[http://localhost:9000/video.Video(bvid="BV1ju411T7so").get_aid()](http://localhost:9000/video.Video(bvid="BV1ju411T7so").get_aid())

此外，你也可以使用一个可被解析的值作为参数值，例如：

[http://localhost:9000/channel_series.ChannelSeries(id_=1845727,uid=148524702,type_=channel_series.ChannelSeriesType.SEASON).get_meta()](http://localhost:9000/channel_series.ChannelSeries(id_=1845727,uid=148524702,type_=channel_series.ChannelSeriesType.SEASON).get_meta())

> 最后，感谢 @Drelf2018 为 bilibili-api 带来后端请求转发接口，~~也算是弥补了模块做不了后端的问题了~~。

---

感谢各位读者耐心读到此处。

编写快速上手的初衷，是更全面地介绍模块的各项功能。如果只参考 `README` 中的示例，用户未必能学会其他接口的用法，也不一定能掌握 `AsyncEvent` 等模块自带工具类的使用方式。虽然模块提供了 API 示例，但许多示例已经年久失修（笔者正在考虑抽空修复），有些功能甚至没有配套示例。如果仅阅读 API 文档，多数人恐怕都难以理解各种函数和类该如何使用。

因此，快速上手中挑选的例子大多是一些经典场景，最能体现模块功能的多样性。如前文所述，这些内容举一反三后可以覆盖整个模块功能的 80%，这个比例不会偏高，只可能偏低——因为模块的几乎所有功能，都可以归入快速上手所展示的具体示例中。

希望读者阅读完后能有所收获，并可以开始熟练地使用模块。

当然，作为快速上手，部分内容未能深入展开，也不可能面面俱到。如需更进一步了解模块，可以继续阅读 `通用`、`进阶` 等部分的文档。

以上就是快速上手部分的全部内容。
