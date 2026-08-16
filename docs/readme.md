![bilibili-api logo](img/logo.png)

<div align="center">

[![API 数量](https://img.shields.io/badge/API%20数量-400+-blue)][api.json]
[![LICENSE](https://img.shields.io/badge/LICENSE-GPLv3+-red)][LICENSE]
[![Python](https://img.shields.io/badge/python-3.10+-blue)](https://www.python.org)
[![Stable Version](https://img.shields.io/github/v/release/bromothymolb/bilibili-api-zoku?label=stable)][pypi]
[![Pre-release Version](https://img.shields.io/github/v/release/bromothymolb/bilibili-api-zoku?label=pre-release&include_prereleases&sort=semver)][pypi]
[![STARS](https://img.shields.io/github/stars/bromothymolb/bilibili-api-zoku?color=yellow&label=Github%20Stars)][stargazers]
[![Docs](https://img.shields.io/badge/Docs-Site-green)][docs]
[![Docs](https://img.shields.io/badge/Docs-Github-green)][docs-github]

## 欢迎来到 bilibili-api-zoku v18.0.0.b0 文档！ヾ(ﾟ∀ﾟゞ)

</div>

### 简介

这是一个用 Python 写的调用 [Bilibili](https://www.bilibili.com) 各种 API 的库，
范围涵盖视频、音频、直播、动态、专栏、用户、番剧等。

`bilibili-api-zoku` 是原 `bilibili-api` 的接续，项目名称来源于日语『続』（<ruby>ぞ<rp>(</rp><rt>zo</rt><rp>)</rp>く<rp>(</rp><rt>ku</rt><rp>)</rp></ruby>），即汉字“续”。

如果你是首次接触模块，可以从 `快速上手` 开始。

进一步了解模块，可以阅读 `文档/通用` `文档/进阶` 中的内容。

模块根目录下不同的子模块提供了不同方面的功能，例如 `video.py` 提供了视频相关功能，`user.py` 提供了用户相关功能。以上子模块提供所有函数与类的相关文档，配有部分常用示例代码可供参考。

> API 示例部分内容尚为稀缺，欢迎补充更多示例！

寻找功能请前往对应子模块下寻找：

| 子模块 | 说明 | 链接 |
| ----- | --- | ---- |
| `activity` | 活动 | [文档](modules/activity.md) - [示例](examples/activity.md) |
| `app` | 应用程序 | [文档](modules/app.md) - [示例](examples/app.md) |
| `article_category` | 专栏分类 | [文档](modules/article_category.md) - [示例](examples/article_category.md) |
| `article` | 专栏 | [文档](modules/article.md) - [示例](examples/article.md) |
| `ass` | 字幕 | [文档](modules/ass.md) - [示例](examples/ass.md) |
| `audio_uploader` | 音频上传 | [文档](modules/audio_uploader.md) - [示例](examples/audio_uploader.md) |
| `audio` | 音频 | [文档](modules/audio.md) - [示例](examples/audio.md) |
| `bangumi` | 番剧 | [文档](modules/bangumi.md) - [示例](examples/bangumi.md) |
| `black_room` | 小黑屋 | [文档](modules/black_room.md) - [示例](examples/black_room.md) |
| `channel_series` | 合集与列表 | [文档](modules/channel_series.md) - [示例](examples/channel_series.md) |
| `cheese` | 课程 | [文档](modules/cheese.md) - [示例](examples/cheese.md) |
| `client` | 终端 | [文档](modules/client.md) - [示例](examples/client.md) |
| `comment` | 评论 | [文档](modules/comment.md) - [示例](examples/comment.md) |
| `creative_center` | 创作中心 | [文档](modules/creative_center.md) - [示例](examples/creative_center.md) |
| `dynamic` | 动态 | [文档](modules/dynamic.md) - [示例](examples/dynamic.md) |
| `emoji` | 表情包 | [文档](modules/emoji.md) - [示例](examples/emoji.md) |
| `favorite_list` | 收藏夹 | [文档](modules/favorite_list.md) - [示例](examples/favorite_list.md) |
| `festival` | 节日 | [文档](modules/festival.md) - [示例](examples/festival.md) |
| `game` | 游戏 | [文档](modules/game.md) - [示例](examples/game.md) |
| `garb` | 装扮/收藏集 | [文档](modules/garb.md) - [示例](examples/garb.md) |
| `homepage` | 主页 | [文档](modules/homepage.md) - [示例](examples/homepage.md) |
| `hot` | 热门 | [文档](modules/hot.md) - [示例](examples/hot.md) |
| `interactive_video` | 互动视频 | [文档](modules/interactive_video.md) - [示例](examples/interactive_video.md) |
| `live_area` | 直播分区 | [文档](modules/live_area.md) - [示例](examples/live_area.md) |
| `live` | 直播 | [文档](modules/live.md) - [示例](examples/live.md) |
| `login_v2` | 登录 | [文档](modules/login_v2.md) - [示例](examples/login_v2.md) |
| `manga` | 漫画 | [文档](modules/manga.md) - [示例](examples/manga.md) |
| `music` | 音乐 | [文档](modules/music.md) - [示例](examples/music.md) |
| `note` | 笔记 | [文档](modules/note.md) - [示例](examples/note.md) |
| `opus` | 图文 | [文档](modules/opus.md) - [示例](examples/opus.md) |
| `rank` | 排行 | [文档](modules/rank.md) - [示例](examples/rank.md) |
| `search` | 搜索 | [文档](modules/search.md) - [示例](examples/search.md) |
| `session` | 会话 | [文档](modules/session.md) - [示例](examples/session.md) |
| `show` | 展出 | [文档](modules/show.md) - [示例](examples/show.md) |
| `topic` | 话题 | [文档](modules/topic.md) - [示例](examples/topic.md) |
| `user` | 用户 | [文档](modules/user.md) - [示例](examples/user.md) |
| `video_tag` | 视频标签 | [文档](modules/video_tag.md) - [示例](examples/video_tag.md) |
| `video_uploader` | 视频上传 | [文档](modules/video_uploader.md) - [示例](examples/video_uploader.md) |
| `video_zone` | 视频分区 | [文档](modules/video_zone.md) - [示例](examples/video_zone.md) |
| `video_zone_v2` | 新版视频分区 | [文档](modules/video_zone_v2.md) - [示例](examples/video_zone_v2.md) |
| `video` | 视频 | [文档](modules/video.md) - [示例](examples/video.md) |
| `vote` | 投票 | [文档](modules/vote.md) - [示例](examples/vote.md) |
| `watchroom` | 放映室 | [文档](modules/watchroom.md) - [示例](examples/watchroom.md) |

模块部分类与函数直接绑定在 `bilibili_api` 包下，例如 `bilibili_api.sync` `bilibili_api.select_client`，诸如此类函数和类的文档，请参考 [根模块文档](modules/bilibili_api.md)

部分功能在文档中有进一步说明，可在侧边栏选择相应页面阅读。

如果实在找不到想要的功能，可以前往 Discussion 区发 Q/A。需要注意，模块并非万能的，亦和和哔哩哔哩官方无任何关系，存在不支持或不可用（失效）的功能是正常现象。

## 致谢

bilibili-api 发展到今天，离不开以下项目的直接或间接支持：

- `MoyuScript/bilibili-api`<sup>1</sup>: 模块最早的仓库。
- `Nemo2011/bilibili-api`<sup>2</sup>: 模块第二个仓库。
- `SocialSisterYi/bilibili-API-collect`<sup>2</sup>:: bilibili API 社区文档。
- `kuresaru/geetest-validator`: 模块极验验证码页面支持。
- `m13253/danmaku2ass`: 模块 ASS 字幕支持。

1: 仓库已删除。
2: 仓库已被 _Cease and Desist Letter_ 后删档。

另外，模块 aid 与 bvid 转换逻辑参考了 <https://www.zhihu.com/question/381784377/answer/1099438784> 这篇回答。

最后，感谢所有贡献者对 bilibili-api 作出的贡献：

<a href="https://github.com/bromothymolb/bilibili-api-zoku/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=bromothymolb/bilibili-api-zoku&max=1000" alt="contributors" />
</a>

也感谢所有曾经的或现在的模块使用者们！

## 使用前须知

> 您开始使用本项目即默认您已阅读、认同并将遵守下列内容：
>
> &emsp;&emsp;本项目仅供学习交流目的的使用。若使用者使用此项目进行包括但不限于以下行为：违反法律（《中华人民共和国民法典》《中华人民共和国反不正当竞争法》《中华人民共和国网络安全法》等）或道德的行为；未授权的数据访问、资源抓取及其他不当利用行为；其他增加了哔哩哔哩平台资源滥用及数据安全风险或严重妨碍了哔哩哔哩平台合法技术服务的正常运行与安全保障机制的有效性的行为，项目维护者不负任何法律责任。
>
> &emsp;&emsp;使用、修改、再分法本项目时，应遵循 [`GNU General Public License v3`](./LICENSE)。
>
> &emsp;&emsp;本项目与 `Nemo2011/bilibili-api` `MoyuScript/bilibili-api` 和哔哩哔哩官方无从属关系。

[docs]: https://bromothymolb.github.io/bilibili-api-zoku
[docs-github]: https://github.com/bromothymolb/bilibili-api-zoku/tree/main/docs
[api.json]: https://github.com/bromothymolb/bilibili-api-zoku/tree/main/bilibili_api/data/api
[license]: https://github.com/bromothymolb/bilibili-api-zoku/tree/main/LICENSE
[stargazers]: https://github.com/bromothymolb/bilibili-api-zoku/stargazers
[issues-new]: https://github.com/bromothymolb/bilibili-api-zoku/issues/new/choose
[get-credential]: https://bromothymolb.github.io/bilibili-api-zoku/#/docs/common/credential.md
[pypi]: https://pypi.org/project/bilibili-api-zoku
[aiohttp]: https://github.com/aio-libs/aiohttp
[httpx]: https://github.com/encode/httpx
[curl_cffi]: https://github.com/lexiforest/curl_cffi
[fpgen]: https://github.com/scrapfly/fingerprint-generator
[trio]: https://github.com/python-trio/trio
[anyio]: https://github.com/agronholm/anyio
