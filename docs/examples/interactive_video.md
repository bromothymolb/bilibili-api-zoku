# 示例：获取剧情图所有节点

用途：下载所有节点视频信息、获取剧情图结构。

本质上是图上广度优先搜索。

```python
from typing import List
from bilibili_api import interactive_video, sync
import json

BVID = 'BV1Dt411N7LY'

async def main():
    # 初始化
    v = interactive_video.InteractiveVideo(bvid=BVID)

    # 存储顶点信息
    edges_info = {}

    # 使用队列来遍历剧情图，初始为 None 是为了从初始顶点开始
    queue: List[interactive_video.InteractiveNode] = [(await v.get_graph()).get_root_node()]

    def createEdge(edge_id: int):
        """
        创建节点信息到 edges_info
        """
        edges_info[edge_id] = {
            "title": None,
            "cid": None,
            "option": None
        }

    while queue:
        # 出队
        now_node = queue.pop()

        if now_node.get_node_id() in edges_info and edges_info[now_node.get_node_id()]['title'] is not None and edges_info[now_node.get_node_id()]['cid'] is not None:
            # 该情况为已获取到所有信息，说明是跳转到之前已处理的顶点，不作处理
            continue

        # 获取顶点信息，最大重试 3 次
        retry = 3
        while True:
            try:
                node = await now_node.get_info()
                title = node["title"]
                # 打印当前顶点信息
                print(node['edge_id'], node['title'])
                break
            except Exception as e:
                retry -= 1
                if retry < 0:
                    raise e

        # 检查节顶点是否在 edges_info 中，本次步骤得到 title 信息
        if node['edge_id'] not in edges_info:
            # 不在，新建
            createEdge(node['edge_id'])

        # 设置 title
        edges_info[node['edge_id']]['title'] = node['title']

        # 无可达顶点，即不能再往下走了，类似树的叶子节点
        if 'questions' not in node['edges']:
            continue

        # 遍历所有可达顶点
        for n in (await now_node.get_children()):
            # 该步骤获取顶点的 cid（视频分 P 的 ID）
            if n.get_node_id() not in edges_info:
                createEdge(n.get_node_id())

            edges_info[n.get_node_id()]['cid'] = n.get_cid()
            edges_info[n.get_node_id()]['option'] = n.get_self_button().get_text()

            # 所有可达顶点 ID 入队
            queue.insert(0, n)

    json.dump(edges_info, open("interactive_video.json", "w"), indent=2)

sync(main())
```

模块已将上述代码进行包装，可以通过以下方式直接获取所有节点与情节树信息：

``` python
import json

from bilibili_api import interactive_video, sync


async def main() -> None:
    ivideo = interactive_video.InteractiveVideo(bvid="BV1Dt411N7LY")
    graph = await ivideo.get_graph()  # 获取 InteractiveGraph 实例
    async for node in graph.get_all_nodes():  # 遍历获取所有节点的生成器
        print(node.get_node_id(), (await node.get_info())["title"])  # 打印节点信息
    json.dump(await graph.to_json(), open("ivideo.json", "w"), indent=2)  # 保存情节树 JSON


sync(main())
```

保存后的情节树 JSON 可以导入 `interactive_video.InteractiveEmulator` 进行对互动视频流程的模拟：

``` python
import json

from bilibili_api import interactive_video

graph = json.load(open("ivideo.json"))
emulator = interactive_video.InteractiveEmulator(graph=graph)
while True:
    print("current node", emulator.get_current_node())
    print("current cid", emulator.get_current_cid())
    print(
        "current vars",
        " | ".join(
            [
                var.get_name() + ": " + str(var.get_value())
                for var in emulator.get_variables()
            ]
        ),
    )
    options = emulator.get_current_options()
    if options is None:
        break
    if len(options) == 0:
        choice = input("按回车继续：")
    else:
        for option in options:
            print(option[0].get_text())
        choice = input("选择的选项索引：")
    if choice == "back":
        emulator.back()
    else:
        if choice == "":
            choice = 0
        else:
            choice = int(choice)
        emulator.select_option(choice)

# current node 204868
# current cid 109138775
# current vars 
# A 去公园散散步
# B 去网吧继续玩
# 选择的选项索引：0
# current node 204863
# current cid 109138806
# current vars 
# A 换个地方散心
# B 去网吧找彬彬
# 选择的选项索引：1
# current node 204871
# current cid 109138922
# current vars 
# A 赊账，继续玩！
# B 算了，回去吧。
# 选择的选项索引：1
# current node 204872
# current cid 109138984
# current vars 
# A 去
# B 不去
# 选择的选项索引：0
# current node 204873
# current cid 109139089
# current vars 
# A 选啤酒
# B 选壮阳酒
# 选择的选项索引：1
# current node 204875
# current cid 109139187
# current vars 
```

# 示例：下载互动视频

用途：下载 `ivi` 文件，其包含了互动视频情节树信息和所有节点视频，可以通过 `ivitools play ...` 进行本地互动播放

``` python
from bilibili_api import interactive_video as ivideo
import asyncio

BVID = ""

async def main():
  # 实例化下载器
  v = ivideo.InteractiveVideo(bvid = BVID)
  downloader = ivideo.InteractiveVideoDownloader(video = v, out = "test.ivi")
  # 监听事件
  downloader.ignore_event("DOWNLOAD_PART") # 忽略下载部分完成信息
  @downloader.on("__ALL__")
  async def ev(data):
    print(data)
  # 开始下载
  try:
    await downloader.start()
  except Exception as e:
    downloader.abort()

if __name__ == '__main__':
  # 运行
  asyncio.run(main())
```

# 示例：提交情节图

* `best_story.py`

```python
from bilibili_storytree import StoryGraph, ScriptNode

class Oscar:
  def __init__(self, videos: dict, aid: int):
    self.videos = videos
    # Create graph
    self.graph = StoryGraph(aid=aid)

  def gen_simple_graph(self, root_title: str):
    # 建情节树：只有一个分支剧情模块
    root_video = self.videos[root_title] 
    n_root = ScriptNode(node_type="videoNode", isRoot=True)
    n_root.set_video(video=root_video)
    self.graph._update_script_nodes([n_root]) # update graph["script"]["nodes"]
    self.graph._sync_nodes() # create graph["nodes"]
    self.graph._sync_vars() # create graph["regional_vars"]
```

* `ivideo_submit.py`

```python
import os
import asyncio
from bilibili_api import video, interactive_video, Credential
import re
from best_story import Oscar
import json
import time

SESSDATA = "记得填" 
BILI_JCT = "记得填"
BUVID3 = "记得填"

def reform_videos(videos):
  video_objs = {}
  for v in videos:
    video_objs[v["title"]] = v 
  return video_objs

async def save_tree(bvid):
  # 实例化 Credential 类
  credential = Credential(sessdata=SESSDATA, bili_jct=BILI_JCT, buvid3=BUVID3)


  # 查询交互视频信息
  info = await interactive_video.up_get_ivideo_pages(bvid=bvid, credential=credential)
  vobjs = reform_videos(info["videos"])
  aid = info["videos"][0]["aid"]

  # 自定义一个情节树
  g = Oscar(videos=vobjs, aid=aid)
  g.gen_simple_graph(root_title="root") # 记得改 pick one video title 
  g.graph.pretty_print()
  story = json.dumps({"graph": g.graph._serialize()})
  #print(story)
  
  # 上传情节树
  graph_result = await interactive_video.up_submit_story_tree(story_tree=story, credential=credential)
  return graph_result


UPLOAD_CONFIG = {
  "copyright": 1, #"1 自制，2 转载。",
  "source": "", #"str, 视频来源。投稿类型为转载时注明来源，为原创时为空。",
  "desc": "", #"str, 视频简介。",
  "desc_format_id": 0,
  "dynamic": "", #"str, 动态信息。",
  "interactive": 1,
  "open_elec": 0, #"int, 是否展示充电信息。1 为是，0 为否。",
  "no_reprint": 1, #"int, 显示未经作者授权禁止转载，仅当为原创视频时有效。1 为启用，0 为关闭。",
  "subtitles": {
    "lan": "", #"字幕语言，不清楚作用请将该项设置为空",
    "open": 0
  },
  "tag": "学习,测试", #"str, 视频标签。使用英文半角逗号分隔的标签组。示例：标签1,标签2,标签3",
  "tid": 208, #"int, 分区ID。可以使用 channel 模块进行查询。",
  #"title": "jump jump jump", #"视频标题",
  "up_close_danmaku": False, #"bool, 是否关闭弹幕。",
  "up_close_reply": False, #"bool, 是否关闭评论。",
}

async def upload_videos(video_dir, cover_img, title):
  # 上传多P视频到互动视频
  cover = open(cover_img, "r+b")

  videos = []
  for filename in os.listdir(video_dir):
    if filename.endswith(".mp4"): 
      video_file = os.path.join(video_dir, filename)
      print(video_file)
      videos.append(video.VideoUploaderPageObject(video_stream=open(video_file, "r+b"), title=filename.split(".")[0]))

  config = UPLOAD_CONFIG
  config["title"] = title

  credential = Credential(sessdata=SESSDATA, bili_jct=BILI_JCT, buvid3=BUVID3)

  uploader = video.VideoUploader(cover=cover, cover_type="jpg", pages=videos, config=config, credential=credential) 

  info =  await uploader.start()

  return info

if __name__ == '__main__':
  folder = "directory contains video files" # 记得填
  img = "image file path" # 记得填
  title = "interactive video name" # 记得填

  info = asyncio.get_event_loop().run_until_complete(upload_videos(folder, img, title))
  print(info) # {"bvid": "ssssss", "aid": ddddddd}
  bvid = info["bvid"]
  time.sleep(120) # 为了 B 站视频编码的时间, 躺平 2 分钟
  graph_result = asyncio.get_event_loop().run_until_complete(save_tree(bvid))
  print(graph_result) # 成功之后，编辑树会延迟，不超过5分钟。 如果觉得有问题，就再执行一次上个存树的命令, 这时多半立即执行，推测是队列机制。

```

