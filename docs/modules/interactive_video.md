# Module interactive_video.py


bilibili_api.interactive_video

互动视频相关操作


``` python
from bilibili_api import interactive_video
```

- [class InteractiveButton()](#class-InteractiveButton)
  - [def \_\_init\_\_()](#def-\_\_init\_\_)
  - [def get\_align()](#def-get\_align)
  - [def get\_pos()](#def-get\_pos)
  - [def get\_text()](#def-get\_text)
- [class InteractiveButtonAlign()](#class-InteractiveButtonAlign)
- [class InteractiveEmulator()](#class-InteractiveEmulator)
  - [def \_\_init\_\_()](#def-\_\_init\_\_)
  - [def back()](#def-back)
  - [def get\_current\_cid()](#def-get\_current\_cid)
  - [def get\_current\_node()](#def-get\_current\_node)
  - [def get\_current\_options()](#def-get\_current\_options)
  - [def get\_skin()](#def-get\_skin)
  - [def get\_variables()](#def-get\_variables)
  - [def select\_option()](#def-select\_option)
- [class InteractiveGraph()](#class-InteractiveGraph)
  - [def \_\_init\_\_()](#def-\_\_init\_\_)
  - [async def get\_all\_nodes()](#async-def-get\_all\_nodes)
  - [async def get\_children()](#async-def-get\_children)
  - [async def get\_root\_node()](#async-def-get\_root\_node)
  - [def get\_skin()](#def-get\_skin)
  - [def get\_video()](#def-get\_video)
  - [async def to\_json()](#async-def-to\_json)
- [class InteractiveJumpingCommand()](#class-InteractiveJumpingCommand)
  - [def \_\_init\_\_()](#def-\_\_init\_\_)
  - [def get\_command()](#def-get\_command)
  - [def get\_vars()](#def-get\_vars)
  - [def run\_command()](#def-run\_command)
  - [def used\_variables()](#def-used\_variables)
- [class InteractiveJumpingCondition()](#class-InteractiveJumpingCondition)
  - [def \_\_init\_\_()](#def-\_\_init\_\_)
  - [def get\_condition()](#def-get\_condition)
  - [def get\_result()](#def-get\_result)
  - [def get\_vars()](#def-get\_vars)
  - [def is\_never()](#def-is\_never)
  - [def used\_variables()](#def-used\_variables)
- [class InteractiveNode()](#class-InteractiveNode)
  - [def \_\_init\_\_()](#def-\_\_init\_\_)
  - [async def get\_children()](#async-def-get\_children)
  - [def get\_cid()](#def-get\_cid)
  - [async def get\_info()](#async-def-get\_info)
  - [def get\_jumping\_command()](#def-get\_jumping\_command)
  - [def get\_jumping\_condition()](#def-get\_jumping\_condition)
  - [async def get\_jumping\_type()](#async-def-get\_jumping\_type)
  - [def get\_node\_id()](#def-get\_node\_id)
  - [def get\_self\_button()](#def-get\_self\_button)
  - [def get\_vars()](#def-get\_vars)
  - [def get\_video()](#def-get\_video)
  - [def is\_default()](#def-is\_default)
  - [async def to\_json()](#async-def-to\_json)
- [class InteractiveNodeJumpingType()](#class-InteractiveNodeJumpingType)
- [class InteractiveVariable()](#class-InteractiveVariable)
  - [def \_\_init\_\_()](#def-\_\_init\_\_)
  - [def get\_id()](#def-get\_id)
  - [def get\_name()](#def-get\_name)
  - [def get\_value()](#def-get\_value)
  - [def is\_random()](#def-is\_random)
  - [def is\_show()](#def-is\_show)
  - [def refresh\_value()](#def-refresh\_value)
- [class InteractiveVideo()](#class-InteractiveVideo)
  - [def \_\_init\_\_()](#def-\_\_init\_\_)
  - [async def get\_cid()](#async-def-get\_cid)
  - [async def get\_edge\_info()](#async-def-get\_edge\_info)
  - [async def get\_graph()](#async-def-get\_graph)
  - [async def get\_graph\_version()](#async-def-get\_graph\_version)
  - [async def mark\_score()](#async-def-mark\_score)
  - [async def up\_get\_ivideo\_pages()](#async-def-up\_get\_ivideo\_pages)
  - [async def up\_submit\_story\_tree()](#async-def-up\_submit\_story\_tree)
- [class InteractiveVideoDownloader()](#class-InteractiveVideoDownloader)
  - [def \_\_init\_\_()](#def-\_\_init\_\_)
  - [async def abort()](#async-def-abort)
  - [async def start()](#async-def-start)
- [class InteractiveVideoDownloaderEvents()](#class-InteractiveVideoDownloaderEvents)
- [class InteractiveVideoDownloaderMode()](#class-InteractiveVideoDownloaderMode)

---

## class InteractiveButton()

互动视频节点按钮类




### def \_\_init\_\_()


| name | type | description |
| - | - | - |
| `text` | `str` | 文字 |
| `x` | `int` | x 轴 |
| `y` | `int` | y 轴 |
| `align` | `interactive_video.InteractiveButtonAlign \| int, optional` | 按钮的文字在按钮中的位置. Defaults to InteractiveButtonAlign.DEFAULT. |


### def get_align()

获取按钮文字布局



**Returns:** `int`:  按钮文字布局




### def get_pos()

获取按钮位置



**Returns:** `tuple[int, int]`:  按钮位置




### def get_text()

获取按钮文字



**Returns:** `str`:  按钮文字




---

## class InteractiveButtonAlign()

> Extend: `enum.Enum`

按钮的文字在按钮中的位置


``` text
-----
|xxx|----o (TEXT_LEFT)
-----

     -----
o----|xxx| (TEXT_RIGHT)
     -----

----------
|XXXXXXXX| (DEFAULT)
----------
```

- DEFAULT
- TEXT_UP
- TEXT_RIGHT
- TEXT_DOWN
- TEXT_LEFT




---

## class InteractiveEmulator()

互动视频模拟支持




### def \_\_init\_\_()


| name | type | description |
| - | - | - |
| `graph` | `dict` | 情节树 JSON |


### def back()

退回到上一个节点






### def get_current_cid()

获取当前节点视频的 cid



**Returns:** `int`:  当前节点视频的 cid




### def get_current_node()

获取当前所在节点



**Returns:** `int`:  当前所在节点




### def get_current_options()

获取当前视频播放完后的按钮选项。

返回列表，列表每一项为一个列表，提供若干个同一个位置的按钮选项。

同一个位置的按钮选项通常出现在概率跳转上，点击其中一种情况的按钮，另一种情况的按钮也将触发。

选择按钮后需记录对应的按钮组在列表中的索引（从 0 开始）。

部分情况视频播放完毕后直接跳转，此时返回空列表，索引亦记为 0。



**Returns:** `list[list[tuple[int, InteractiveButton]]] | None`:  按钮选项，若互动视频已结束则返回 None




### def get_skin()

获取按钮样式



**Returns:** `dict`:  按钮样式




### def get_variables()

获取变量



**Returns:** `list[InteractiveVariable]`:  变量列表




### def select_option()

选择按钮选项，并跳转。


| name | type | description |
| - | - | - |
| `idx` | `int` | 索引。参考 `get_current_options` |




---

## class InteractiveGraph()

情节树类




### def \_\_init\_\_()


| name | type | description |
| - | - | - |
| `video` | `InteractiveVideo` | 互动视频类 |
| `skin` | `dict` | 样式 |
| `root_cid` | `int` | 根节点 CID |


### async def get_all_nodes()

获取所有节点，返回异步生成器。


| name | type | description |
| - | - | - |
| `retry` | `int, optional` | 重试次数. Defaults to 3. |

**Returns:** `AsyncGenerator[None, InteractiveNode]`:  异步生成器




### async def get_children()

获取子节点



**Returns:** `list['InteractiveNode']`:  子节点




### async def get_root_node()

获取根节点



**Returns:** `InteractiveNode`:  根节点




### def get_skin()

获取按钮样式



**Returns:** `dict`:  按钮样式




### def get_video()

获取视频



**Returns:** `InteractiveVideo`:  视频




### async def to_json()

导出情节树，导出后可使用 `InteractiveEmulator` 进行交互。

- `skin`: `dict` 按钮样式相关
- `nodes`: `dict[str, dict]` 包含所有节点的信息。键为 node_id 对应字符串。
- `root`: `int` 根节点的 ID
- `bvid`: `str` 视频 bvid
- `aid`: `int` 视频 aid

每个节点信息结构请查看 `InteractiveNode.to_json` 函数。



**Returns:** `dict`:  情节树 JSON 数据




---

## class InteractiveJumpingCommand()

节点跳转对变量的操作




### def \_\_init\_\_()


| name | type | description |
| - | - | - |
| `var` | `list[interactive_video.InteractiveVariable] \| None, optional` | 所有变量. Defaults to None. |
| `command` | `str, optional` | 公式. Defaults to ''. |


### def get_command()

获取表达式



**Returns:** `str`:  表达式




### def get_vars()

获取公式中的变量



**Returns:** `list[interactive_video.InteractiveVariable]`:  变量




### def run_command()

执行操作



**Returns:** `list['InteractiveVariable']`:  所有变量的最终值




### def used_variables()

获取公式中出现的变量



**Returns:** `list[InteractiveVariable]`:  公式中出现的变量




---

## class InteractiveJumpingCondition()

节点跳转的公式，只有公式成立才会跳转




### def \_\_init\_\_()


| name | type | description |
| - | - | - |
| `var` | `list[interactive_video.InteractiveVariable] \| None, optional` | 所有变量. Defaults to None. |
| `condition` | `str, optional` | 公式. Defaults to 'True'. |


### def get_condition()

获取表达式



**Returns:** `str`:  表达式




### def get_result()

计算公式获得结果



**Returns:** `bool`:  是否成立




### def get_vars()

获取公式中的变量



**Returns:** `list[interactive_video.InteractiveVariable]`:  变量




### def is_never()

判断公式是否永远不会成立



**Returns:** `bool`:  是否永远不会成立




### def used_variables()

获取公式中出现的变量



**Returns:** `list[InteractiveVariable]`:  公式中出现的变量




---

## class InteractiveNode()

互动视频节点类




### def \_\_init\_\_()


| name | type | description |
| - | - | - |
| `video` | `InteractiveVideo` | 视频类 |
| `node_id` | `int` | 节点 id |
| `cid` | `int` | CID |
| `vars` | `list[interactive_video.InteractiveVariable]` | 变量 |
| `button` | `interactive_video.InteractiveButton \| None, optional` | 对应的按钮. Defaults to None. |
| `condition` | `interactive_video.InteractiveJumpingCondition, optional` | 跳转公式. Defaults to <bilibili_api.interactive_video.InteractiveJumpingCondition object at 0x1055e34d0>. |
| `native_command` | `interactive_video.InteractiveJumpingCommand, optional` | 跳转时变量操作. Defaults to <bilibili_api.interactive_video.InteractiveJumpingCommand object at 0x1055e3770>. |
| `is_default` | `bool, optional` | 是不是默认的跳转的节点. Defaults to False. |


### async def get_children()

获取节点的所有子节点



**Returns:** `list['InteractiveNode']`:  所有子节点




### def get_cid()

获取节点 cid



**Returns:** `int`:  节点 cid




### async def get_info()

获取节点的简介



**Returns:** `dict`:  调用 API 返回的结果




### def get_jumping_command()

获取跳转时执行的语句，已自动执行，无需手动调用



**Returns:** `interactive_video.InteractiveJumpingCommand`:  执行的语句




### def get_jumping_condition()

获取跳转条件



**Returns:** `InteractiveJumpingCondition`:  跳转条件




### async def get_jumping_type()

获取子节点跳转方式 (参考 InteractiveNodeJumpingType)



**Returns:** `int`:  子节点跳转方式




### def get_node_id()

获取节点 id



**Returns:** `int`:  节点 id




### def get_self_button()

获取该节点所对应的按钮



**Returns:** `InteractiveButton`:  所对应的按钮




### def get_vars()

获取节点的所有变量



**Returns:** `list[interactive_video.InteractiveVariable]`:  节点的所有变量




### def get_video()

获取节点对应视频



**Returns:** `InteractiveVideo`:  对应视频




### def is_default()

节点是否为跳转中默认节点



**Returns:** `bool`:  是否为跳转中默认节点




### async def to_json()

将节点通过 JSON 的方式保存

- `node_id` (`int`: 节点 ID)
- `title` (`str`: 标题)
- `cid` (`int`: CID)
- `sub` (`list`: 子节点列表)
    - `text` (`str`: 按钮文字)
    - `align` (`int`: 按钮文字相对于定位的位置，有上左下右中五种，可以参考 `interactive_video.InteractiveButtonAlign`，里面有详细注释)
    - `pos` (`list[int]`: 按钮位置信息 (如果所有按钮都照正常布局，那么此数据的值为 `[null, null]`))
        - `0`: X 坐标
        - `1`: Y 坐标
    - `condition` (`str`: 节点跳转必须符合的表达式，默认为 `""`。为 `javascript` 语言。主要作用为实现随机跳转。)
    - `jump_type` (`int`: 跳转方式，有直接跳转和选择跳转两种，可查看 `interactive_video.InteractiveJumpingType`)
    - `is_default` (`bool`: 是否为默认节点，如果是直接跳转则会跳转至默认节点，或者是定时选择后直接跳转至默认节点(定时选择后直接跳转目前不支持))
    - `command` (`str`: 跳转成功后需要对变量做的操作。为 `javascript` 语言。)
- `vars` (`list[dict]`: 初始化时的变量设置)
    - `name` (`str`: 变量名)
    - `id` (`str`: 变量 id，为变量在 `command` 和 `condition` 中出现时使用的变量名)
    - `value` (`int`: 变量数值)
    - `show` (`bool`: 变量是否展示，有的变量需要时刻展示给观看者，例如 `循环编号`, `分数` 等)
    - `random` (`bool`: 变量是否随机值。随机变量配上跳转公式是实现随机跳转的重要部分，这里说明：随机值取值范围为 `0-100`。)



**Returns:** `dict`:  JSON




---

## class InteractiveNodeJumpingType()

> Extend: `enum.Enum`

对下一节点的跳转的方式

- ASK    : 选择
- DEFAULT: 跳转到默认节点
- READY  : 选择(只有一个选择)




---

## class InteractiveVariable()

互动节点的变量




### def \_\_init\_\_()


| name | type | description |
| - | - | - |
| `name` | `str` | 变量名 |
| `var_id` | `str` | 变量 id |
| `var_value` | `int \| float` | 变量的值 |
| `show` | `bool, optional` | 是否显示. Defaults to False. |
| `random` | `bool, optional` | 是否为随机值(1-100). Defaults to False. |


### def get_id()

获取变量 id



**Returns:** `str`:  变量 id




### def get_name()

获取变量的名字



**Returns:** `str`:  变量的名字




### def get_value()

获取变量对应的值



**Returns:** `int | float`:  变量对应的值




### def is_random()

变量是否随机生成



**Returns:** `bool`:  变量是否随机生成




### def is_show()

变量是否显示



**Returns:** `bool`:  变量是否显示




### def refresh_value()

刷新变量数值






---

## class InteractiveVideo()

> Extend: `bilibili_api.video.Video`

互动视频类




### def \_\_init\_\_()


| name | type | description |
| - | - | - |
| `bvid` | `str \| None, optional` | bvid. Defaults to None. |
| `aid` | `int \| None, optional` | aid. Defaults to None. |
| `credential` | `Credential \| None, optional` | 凭据类. Defaults to None. |


### async def get_cid()

获取稿件 cid



**Returns:** `int`:  cid




### async def get_edge_info()

获取剧情图节点信息


| name | type | description |
| - | - | - |
| `edge_id` | `int \| None, optional` | 节点 ID，为 None 时获取根节点信息. Defaults to None. |

**Returns:** `dict`:  调用 API 返回的结果




### async def get_graph()

获取稿件情节树



**Returns:** `interactive_video.InteractiveGraph`:  情节树




### async def get_graph_version()

获取剧情图版本号，仅供 `get_edge_info()` 使用。



**Returns:** `int`:  剧情图版本号




### async def mark_score()

为互动视频打分


| name | type | description |
| - | - | - |
| `score` | `int, optional` | 互动视频分数. Defaults to 5. |

**Returns:** `int`:  调用 API 返回的结果




### async def up_get_ivideo_pages()

获取交互视频的分 P 信息。up 主需要拥有视频所有权。



**Returns:** `dict`:  调用 API 返回的结果




### async def up_submit_story_tree()

上传交互视频的情节树。up 主需要拥有视频所有权。


| name | type | description |
| - | - | - |
| `story_tree` | `str` | 情节树的描述，参考 bilibili_storytree.StoryGraph, 需要 Serialize 这个结构 |

**Returns:** `dict`:  调用 API 返回的结果




---

## class InteractiveVideoDownloader()

> Extend: `bilibili_api.utils.AsyncEvent.AsyncEvent`

互动视频下载类




### def \_\_init\_\_()

为保证视频能被成功下载，请在自定义下载函数请求的时候加入 `bilibili_api.get_bili_headers()` 头部。


| name | type | description |
| - | - | - |
| `video` | `interactive_video.InteractiveVideo` | 互动视频类 |
| `out` | `str` | 输出文件地址 (如果模式为 NODE_VIDEOS/NO_PACKAGING 则此参数表示所有节点视频的存放目录) |
| `self_download_func` | `Coroutine \| None, optional` | 自定义下载函数（需 async 函数）. Defaults to None. |
| `downloader_mode` | `InteractiveVideoDownloaderMode, optional` | 下载模式. Defaults to InteractiveVideoDownloaderMode.IVI. |
| `stream_detecting_params` | `dict \| None, optional` | `VideoDownloadURLDataDetecter` 提取最佳流时传入的参数，可控制视频及音频品质. Defaults to None. |
| `fetching_nodes_retry_times` | `int, optional` | 获取节点时的最大重试次数. Defaults to 3. |
| `download_retry_times` | `int, optional` | 下载时的最大重试次数. Defaults to 3. |
| `download_wait_time` | `int, optional` | 下载之间间隔时间. Defaults to 3. |


### async def abort()

中断下载






### async def start()

开始下载






---

## class InteractiveVideoDownloaderEvents()

> Extend: `enum.Enum`

互动视频下载器事件枚举

| event | meaning | IVI mode | NODE_VIDEOS mode | DOT_GRAPH or JSON mode | NO_PACKAGING mode | Is Built-In downloader event |
| ----- | ------- | -------- | ---------------- | -------------- | ----------------- | ------------------------- |
| START | 开始下载 | [x] | [x] | [x] | [x] | [ ] |
| GET | 获取到节点信息 | [x] | [x] | [x] | [x] | [ ] |
| PREPARE_DOWNLOAD | 准备下载单个节点 | [x] | [x] | [ ] | [x] | [ ] |
| DOWNLOAD_START | 开始下载单个文件 | Unknown | Unknown | [ ] | Unknown | [x] |
| DOWNLOAD_PART | 文件分块部分完成 | Unknown | Unknown | [ ] | Unknown | [x] |
| DOWNLOAD_SUCCESS | 完成下载 | Unknown | Unknown | [ ] | Unknown | [x] |
| PACKAGING | 正在打包 | [x] | [ ] | [ ] | [ ] | [ ] |
| SUCCESS | 下载成功 | [x] | [x] | [x] | [x] | [ ] |
| ABORTED | 用户暂停 | [x] | [x] | [x] | [x] | [ ] |
| FAILED | 下载失败 | [x] | [x] | [x] | [x] | [ ] |




---

## class InteractiveVideoDownloaderMode()

> Extend: `enum.Enum`

互动视频下载模式

- IVI: 下载可播放的 ivi 文件
- NODE_VIDEOS: 下载所有节点的所有视频并存放在某个文件夹，每一个节点的视频命名为 `{节点 id} {节点标题 (自动去除敏感字符)}.mp4`
- DOT_GRAPH: 下载 dot 格式的情节树图表
- NO_PACKAGING: 前面按照 ivi 文件下载步骤进行下载，但是最终不会打包成为 ivi 文件，所有文件将存放于一个文件夹中。互动视频数据将存放在一个文件夹中，里面的文件命名/含义与拆包后的 ivi 文件完全相同。
- JSON: 获取 json 格式情节树，不下载视频。




