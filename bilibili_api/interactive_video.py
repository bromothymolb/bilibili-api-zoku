"""
bilibili_api.interactive_video

互动视频相关操作
"""

from collections.abc import AsyncGenerator, Coroutine
import copy
import enum
import json
import os
from random import random
import shutil
import time
from urllib import parse
import zipfile

import anyio
import anyio.to_thread

from .exceptions import ArgsException
from .utils.AsyncEvent import AsyncEvent
from .utils.high_level import Api, Credential, get_bili_headers
from .utils.network import get_client
from .utils.utils import get_api
from .video import Video, VideoDownloadURLDataDetecter

API = get_api("interactive_video")


def safe_eval(statement: str) -> int | float:
    for char in statement:
        if ord(char) not in list(range(48, 58)) + [
            ord(x) for x in ".+-*/&|( )[=]{!}<%>"
        ]:
            raise ArgsException("suspicious statement: " + statement)
    statement = statement.replace("&&", " and ")
    statement = statement.replace("||", " or ")
    statement = statement.replace("!", " not ")
    return eval(statement)


class InteractiveButtonAlign(enum.Enum):
    """
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
    """

    DEFAULT = 0
    TEXT_UP = 1
    TEXT_RIGHT = 2
    TEXT_DOWN = 3
    TEXT_LEFT = 4


class InteractiveNodeJumpingType(enum.Enum):
    """
    对下一节点的跳转的方式

    - ASK    : 选择
    - DEFAULT: 跳转到默认节点
    - READY  : 选择(只有一个选择)
    """

    READY = 1
    DEFAULT = 0
    ASK = 2


class InteractiveVariable:
    """
    互动节点的变量
    """

    def __init__(
        self,
        name: str,
        var_id: str,
        var_value: int | float,
        show: bool = False,
        random: bool = False,
    ) -> None:
        """
        Args:
            name (str): 变量名
            var_id (str): 变量 id
            var_value (int | float): 变量的值
            show (bool, optional): 是否显示. Defaults to False.
            random (bool, optional): 是否为随机值(1-100). Defaults to False.
        """
        self.__var_id = var_id
        self.__var_value = var_value
        self.__name = name
        self.__is_show = show
        self.__random = random

    def __str__(self) -> str:
        return f"InteractiveVariable(id='{self.__var_id}', value={self.__var_value}, random={self.__random})"

    def __repr__(self) -> str:
        return f"InteractiveVariable(id='{self.__var_id}', value={self.__var_value}, random={self.__random})"

    def get_id(self) -> str:
        """
        获取变量 id

        Returns:
            str: 变量 id
        """
        return self.__var_id

    def refresh_value(self) -> None:
        """
        刷新变量数值
        """
        if self.is_random():
            self.__var_value = int(random() * 100) + 1

    def get_value(self) -> int | float:
        """
        获取变量对应的值

        Returns:
            int | float: 变量对应的值
        """
        return self.__var_value

    def is_show(self) -> bool:
        """
        变量是否显示

        Returns:
            bool: 变量是否显示
        """
        return self.__is_show

    def is_random(self) -> bool:
        """
        变量是否随机生成

        Returns:
            bool: 变量是否随机生成
        """
        return self.__random

    def get_name(self) -> str:
        """
        获取变量的名字

        Returns:
            str: 变量的名字
        """
        return self.__name


class InteractiveButton:
    """
    互动视频节点按钮类
    """

    def __init__(
        self,
        text: str,
        x: int,
        y: int,
        align: InteractiveButtonAlign | int = InteractiveButtonAlign.DEFAULT,
    ) -> None:
        """
        Args:
            text (str): 文字
            x (int): x 轴
            y (int): y 轴
            align (interactive_video.InteractiveButtonAlign | int, optional): 按钮的文字在按钮中的位置. Defaults to InteractiveButtonAlign.DEFAULT.
        """
        self.__text = text
        self.__pos = (x, y)
        if isinstance(align, InteractiveButtonAlign):
            align = align.value
        self.__align = align

    def __str__(self) -> str:
        return f"InteractiveButton(text='{self.__text}', pos={self.__pos})"

    def __repr__(self) -> str:
        return f"InteractiveButton(text='{self.__text}', pos={self.__pos})"

    def get_text(self) -> str:
        """
        获取按钮文字

        Returns:
            str: 按钮文字
        """
        return self.__text

    def get_align(self) -> int:
        """
        获取按钮文字布局

        Returns:
            int: 按钮文字布局
        """
        return self.__align  # type: ignore

    def get_pos(self) -> tuple[int, int]:
        """
        获取按钮位置

        Returns:
            tuple[int, int]: 按钮位置
        """
        return self.__pos


class InteractiveJumpingCondition:
    """
    节点跳转的公式，只有公式成立才会跳转
    """

    def __init__(
        self, var: list[InteractiveVariable] | None = None, condition: str = "True"
    ) -> None:
        """
        Args:
            var (list[interactive_video.InteractiveVariable] | None, optional): 所有变量. Defaults to None.
            condition (str, optional): 公式. Defaults to 'True'.
        """
        self.__vars = var or []
        self.__command = condition

    def __str__(self) -> str:
        return f"InteractiveJumpingCondition(command='{self.__command}')"

    def __repr__(self) -> str:
        return f"InteractiveJumpingCondition(command='{self.__command}')"

    def get_vars(self) -> list[InteractiveVariable]:
        """
        获取公式中的变量

        Returns:
            list[interactive_video.InteractiveVariable]: 变量
        """
        return copy.copy(self.__vars)

    def get_condition(self) -> str:
        """
        获取表达式

        Returns:
            str: 表达式
        """
        return self.__command

    def used_variables(self) -> list[InteractiveVariable]:
        """
        获取公式中出现的变量

        Returns:
            list[InteractiveVariable]: 公式中出现的变量
        """
        ret = []
        for var in self.__vars:
            if var.get_id() in self.__command:
                ret.append(var)
        return ret

    def is_never(self) -> bool:
        """
        判断公式是否永远不会成立

        Returns:
            bool: 是否永远不会成立
        """
        has_random = False
        for var in self.used_variables():
            if var.is_random():
                has_random = True
        return (not self.get_result()) and (not has_random)

    def get_result(self) -> bool:
        """
        计算公式获得结果

        Returns:
            bool: 是否成立
        """
        if self.__command == "":
            return True
        command = copy.copy(self.__command)
        for var in self.__vars:
            var_name = var.get_id()
            var_value = var.get_value()
            command = command.replace(var_name, str(var_value))
        command = command.replace("===", "==")
        command = command.replace("!==", "!=")
        command = command.replace("true", "1")
        command = command.replace("false", "0")
        return bool(safe_eval(command))


class InteractiveJumpingCommand:
    """
    节点跳转对变量的操作
    """

    def __init__(
        self, var: list[InteractiveVariable] | None = None, command: str = ""
    ) -> None:
        """
        Args:
            var (list[interactive_video.InteractiveVariable] | None, optional): 所有变量. Defaults to None.
            command (str, optional): 公式. Defaults to ''.
        """
        self.__vars = var or []
        self.__command = command

    def __str__(self) -> str:
        return f"InteractiveJumpingCommand(command='{self.__command}')"

    def __repr__(self) -> str:
        return f"InteractiveJumpingCommand(command='{self.__command}')"

    def get_vars(self) -> list[InteractiveVariable]:
        """
        获取公式中的变量

        Returns:
            list[interactive_video.InteractiveVariable]: 变量
        """
        return copy.copy(self.__vars)

    def used_variables(self) -> list[InteractiveVariable]:
        """
        获取公式中出现的变量

        Returns:
            list[InteractiveVariable]: 公式中出现的变量
        """
        ret = []
        for var in self.__vars:
            if var.get_id() in self.__command:
                ret.append(var)
        return ret

    def get_command(self) -> str:
        """
        获取表达式

        Returns:
            str: 表达式
        """
        return self.__command

    def run_command(self) -> list["InteractiveVariable"]:
        """
        执行操作

        Returns:
            list['InteractiveVariable']: 所有变量的最终值
        """
        if self.__command == "":
            return self.__vars
        for code in self.__command.split(";"):
            changed_var = code.split("=")[0].rstrip()
            var_new_value = code.split("=")[1]
            for var in self.__vars:
                var_name = var.get_id()
                var_value = var.get_value()
                var_new_value = var_new_value.replace(var_name, str(var_value))
            var_new_value_calc = safe_eval(var_new_value)
            for idx, var in enumerate(self.__vars):
                if var.get_id() == changed_var:
                    self.__vars[idx] = InteractiveVariable(
                        name=var.get_name(),
                        var_id=var.get_id(),
                        var_value=var_new_value_calc,
                        show=var.is_show(),
                        random=var.is_random(),
                    )
        return self.__vars


class InteractiveNode:
    """
    互动视频节点类
    """

    def __init__(
        self,
        video: "InteractiveVideo",
        node_id: int,
        cid: int,
        vars: list[InteractiveVariable],
        button: InteractiveButton | None = None,
        condition: InteractiveJumpingCondition | None = None,
        native_command: InteractiveJumpingCommand | None = None,
        is_default: bool = False,
    ) -> None:
        """
        Args:
            video (InteractiveVideo): 视频类
            node_id (int): 节点 id
            cid (int): CID
            vars (list[interactive_video.InteractiveVariable]): 变量
            button (interactive_video.InteractiveButton | None, optional): 对应的按钮. Defaults to None.
            condition (interactive_video.InteractiveJumpingCondition, optional): 跳转公式. Defaults to <bilibili_api.interactive_video.InteractiveJumpingCondition object at 0x1055e34d0>.
            native_command (interactive_video.InteractiveJumpingCommand, optional): 跳转时变量操作. Defaults to <bilibili_api.interactive_video.InteractiveJumpingCommand object at 0x1055e3770>.
            is_default (bool, optional): 是不是默认的跳转的节点. Defaults to False.
        """
        self.__parent = video
        self.__id = node_id
        self.__cid = cid
        self.__button = button
        self.__jumping_command = condition or InteractiveJumpingCondition()
        self.__is_default = is_default
        self.__vars = vars
        self.__command = native_command or InteractiveJumpingCommand()
        self.__vars = self.__command.run_command()
        self.__info = None

    def __str__(self) -> str:
        return f"InteractiveNode(node_id={self.__id})"

    def __repr__(self) -> str:
        return f"InteractiveNode(node_id={self.__id})"

    async def __get_cached_edge_info(self) -> dict:
        if not self.__info:
            self.__info = await self.__parent.get_edge_info(self.__id)
        return self.__info

    def get_jumping_command(self) -> InteractiveJumpingCommand:
        """
        获取跳转时执行的语句，已自动执行，无需手动调用

        Returns:
            interactive_video.InteractiveJumpingCommand: 执行的语句
        """
        return self.__command

    def get_vars(self) -> list[InteractiveVariable]:
        """
        获取节点的所有变量

        Returns:
            list[interactive_video.InteractiveVariable]: 节点的所有变量
        """
        return copy.copy(self.__vars)

    async def get_children(self) -> list["InteractiveNode"]:
        """
        获取节点的所有子节点

        Returns:
            list['InteractiveNode']: 所有子节点
        """
        edge_info = await self.__get_cached_edge_info()
        nodes = []
        if edge_info["edges"].get("questions") is None:
            return []
        for node in edge_info["edges"]["questions"][0]["choices"]:
            node_id = node["id"]
            node_cid = node["cid"]
            if "text_align" in node.keys():
                text_align = node["text_align"]
            else:
                text_align = 0
            if "option" in node.keys():
                node_button = InteractiveButton(
                    node["option"], node.get("x"), node.get("y"), text_align
                )
            else:
                node_button = None
            node_condition = InteractiveJumpingCondition(
                self.get_vars(), node["condition"]
            )
            node_command = InteractiveJumpingCommand(
                self.get_vars(), node["native_action"]
            )
            if "is_default" in node.keys():
                node_is_default = node["is_default"]
            else:
                node_is_default = False
            node_vars = copy.deepcopy(self.get_vars())
            nodes.append(
                InteractiveNode(
                    self.__parent,
                    node_id,
                    node_cid,
                    node_vars,
                    node_button,
                    node_condition,
                    node_command,
                    node_is_default,
                )
            )
        return nodes

    def is_default(self) -> bool:
        """
        节点是否为跳转中默认节点

        Returns:
            bool: 是否为跳转中默认节点
        """
        return self.__is_default

    async def get_jumping_type(self) -> int:
        """
        获取子节点跳转方式 (参考 InteractiveNodeJumpingType)

        Returns:
            int: 子节点跳转方式
        """
        edge_info = await self.__get_cached_edge_info()
        return edge_info["edges"]["questions"][0]["type"]

    def get_node_id(self) -> int:
        """
        获取节点 id

        Returns:
            int: 节点 id
        """
        return self.__id

    def get_cid(self) -> int:
        """
        获取节点 cid

        Returns:
            int: 节点 cid
        """
        return self.__cid

    def get_self_button(self) -> "InteractiveButton":
        """
        获取该节点所对应的按钮

        Returns:
            InteractiveButton: 所对应的按钮
        """
        if self.__button is None:
            return InteractiveButton("", -1, -1)
        return self.__button

    def get_jumping_condition(self) -> "InteractiveJumpingCondition":
        """
        获取跳转条件

        Returns:
            InteractiveJumpingCondition: 跳转条件
        """
        return self.__jumping_command

    def get_video(self) -> "InteractiveVideo":
        """
        获取节点对应视频

        Returns:
            InteractiveVideo: 对应视频
        """
        return self.__parent

    async def get_info(self) -> dict:
        """
        获取节点的简介

        Returns:
            dict: 调用 API 返回的结果
        """
        return await self.__get_cached_edge_info()

    async def to_json(self) -> dict:
        """
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

        Returns:
            dict: JSON
        """

        def var2dict(var: InteractiveVariable):
            return {
                "name": var.get_name(),
                "id": var.get_id(),
                "value": var.get_value(),
                "show": var.is_show(),
                "random": var.is_random(),
            }

        ret = {}
        info = await self.get_info()
        ret["node_id"] = self.get_node_id()
        ret["title"] = info["title"]
        ret["cid"] = self.get_cid()
        ret["vars"] = [var2dict(var) for var in self.get_vars()]
        ret["sub"] = []
        for sub in await self.get_children():
            ret["sub"].append(
                {
                    "id": sub.get_node_id(),
                    "text": sub.get_self_button().get_text(),
                    "align": sub.get_self_button().get_align(),
                    "pos": sub.get_self_button().get_pos(),
                    "condition": sub.get_jumping_condition().get_condition(),  # type: ignore
                    "jump_type": await self.get_jumping_type(),
                    "is_default": sub.is_default(),
                    "command": sub.get_jumping_command().get_command(),  # type: ignore
                }
            )
        return ret


class InteractiveGraph:
    """
    情节树类
    """

    def __init__(self, video: "InteractiveVideo", skin: dict, root_cid: int) -> None:
        """
        Args:
            video (InteractiveVideo): 互动视频类
            skin (dict): 样式
            root_cid (int): 根节点 CID
        """
        self.__parent = video
        self.__skin = skin
        self.__node = InteractiveNode(self.__parent, 0, root_cid, [])
        self.__nodes = []

    def __str__(self) -> str:
        return f"InteractiveGraph(video={self.__parent}, root={self.__node})"

    def __repr__(self) -> str:
        return f"InteractiveGraph(video={self.__parent}, root={self.__node})"

    def get_video(self) -> "InteractiveVideo":
        """
        获取视频

        Returns:
            InteractiveVideo: 视频
        """
        return self.__parent

    def get_skin(self) -> dict:
        """
        获取按钮样式

        Returns:
            dict: 按钮样式
        """
        return self.__skin

    async def get_root_node(self) -> "InteractiveNode":
        """
        获取根节点

        Returns:
            InteractiveNode: 根节点
        """
        if self.__node.get_node_id() != 0:
            return self.__node
        edge_info = await self.__parent.get_edge_info(None)
        if "hidden_vars" in edge_info.keys():
            node_vars = edge_info["hidden_vars"]
        else:
            node_vars = []
        var_list = []
        for var in node_vars:
            var_value = var["value"]
            var_name = var["name"]
            var_show = var["is_show"]
            var_id = var["id_v2"]
            if var["type"] == 2:
                random = True
            else:
                random = False
            var_list.append(
                InteractiveVariable(var_name, var_id, var_value, var_show, random)
            )
        self.__node = InteractiveNode(
            video=self.__parent,
            node_id=edge_info["edge_id"],
            cid=self.__node.get_cid(),
            vars=var_list,
            native_command=InteractiveJumpingCommand(var_list),
        )
        return self.__node

    async def get_children(self) -> list["InteractiveNode"]:
        """
        获取子节点

        Returns:
            list['InteractiveNode']: 子节点
        """
        return await self.__node.get_children()

    async def get_all_nodes(
        self, retry: int = 3
    ) -> AsyncGenerator[InteractiveNode, None]:
        """
        获取所有节点，返回异步生成器。

        Args:
            retry (int, optional): 重试次数. Defaults to 3.

        Returns:
            AsyncGenerator[None, InteractiveNode]: 异步生成器
        """
        if len(self.__nodes) > 0:
            for node in self.__nodes:
                yield node
            return

        queue: list[InteractiveNode] = [await self.get_root_node()]
        node_ids: set[int] = set()

        while queue:
            # 出队
            current_node = queue.pop()
            if current_node.get_node_id() in node_ids:
                # 该情况为已获取到所有信息，说明是跳转到之前已处理的顶点，不作处理
                continue
            yield current_node
            # 获取顶点信息，最大重试 3 次
            while True:
                try:
                    node_info = await current_node.get_info()
                    subs = await current_node.get_children()
                    break
                except Exception as e:
                    retry -= 1
                    if retry < 0:
                        raise e
            # 加入集合
            node_ids.add(current_node.get_node_id())
            # 缓存节点
            self.__nodes.append(current_node)
            # 无可达顶点，即不能再往下走了，类似树的叶子节点
            if "questions" not in node_info["edges"]:
                continue
            # 遍历所有可达顶点
            for sub in subs:
                queue.insert(0, sub)

    async def to_json(self) -> dict:
        """
        导出情节树，导出后可使用 `InteractiveEmulator` 进行交互。

        - `skin`: `dict` 按钮样式相关
        - `nodes`: `dict[str, dict]` 包含所有节点的信息。键为 node_id 对应字符串。
        - `root`: `int` 根节点的 ID
        - `bvid`: `str` 视频 bvid
        - `aid`: `int` 视频 aid

        每个节点信息结构请查看 `InteractiveNode.to_json` 函数。

        Returns:
            dict: 情节树 JSON 数据
        """
        edges_info = {
            "skin": self.get_skin(),
            "nodes": {},
            "root": (await self.get_root_node()).get_node_id(),
            "bvid": self.get_video().get_bvid(),
            "aid": self.get_video().get_aid(),
        }
        async for node in self.get_all_nodes():
            edges_info["nodes"][str(node.get_node_id())] = await node.to_json()
        return edges_info


class InteractiveVideo(Video):
    """
    互动视频类
    """

    def __init__(
        self,
        bvid: str | None = None,
        aid: int | None = None,
        credential: Credential | None = None,
    ) -> None:
        """
        Args:
            bvid (str | None, optional): bvid. Defaults to None.
            aid (int | None, optional): aid. Defaults to None.
            credential (Credential | None, optional): 凭据类. Defaults to None.
        """
        super().__init__(bvid, aid, credential)
        self.__graph = None
        self.__version = None
        self.__edge_infos = {}
        self.__root_node = None

    def __str__(self) -> str:
        return f"InteractiveVideo(bvid='{self.get_bvid()}', aid={self.get_aid()})"

    def __repr__(self) -> str:
        return f"InteractiveVideo(bvid='{self.get_bvid()}', aid={self.get_aid()})"

    async def up_get_ivideo_pages(self) -> dict:
        """
        获取交互视频的分 P 信息。up 主需要拥有视频所有权。

        Returns:
            dict: 调用 API 返回的结果
        """
        credential = self.credential or Credential()
        api = API["info"]["videolist"]
        params = {"bvid": self.get_bvid()}
        return await Api(**api, credential=credential).update_params(**params).result

    async def up_submit_story_tree(self, story_tree: str) -> dict:
        """
        上传交互视频的情节树。up 主需要拥有视频所有权。

        Args:
            story_tree (str): 情节树的描述，参考 bilibili_storytree.StoryGraph, 需要 Serialize 这个结构

        Returns:
            dict: 调用 API 返回的结果
        """
        credential = self.credential or Credential()
        api = API["operate"]["savestory"]
        form_data = {"preview": "0", "data": story_tree, "csrf": credential.bili_jct}
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
            "Referer": "https://member.bilibili.com",
            "Content-Encoding": "gzip, deflate, br",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json, text/plain, */*",
        }
        data = parse.urlencode(form_data)
        client = get_client()
        return (
            await client.request(
                method="POST",
                url=api["url"],
                data=data,
                cookies=await credential.get_cookies(),
                headers=headers,
            )
        ).json()["data"]

    async def get_graph_version(self) -> int:
        """
        获取剧情图版本号，仅供 `get_edge_info()` 使用。

        Returns:
            int: 剧情图版本号
        """
        if not self.__version:
            # 取得初始顶点 cid
            cid = await self.get_cid()

            # 获取剧情图版本号
            url = "https://api.bilibili.com/x/player/v2"
            params = {"bvid": self.get_bvid(), "cid": cid}

            resp = (
                await Api(method="GET", url=url, credential=self.credential)
                .update_params(**params)
                .result
            )
            self.__version = resp["interaction"]["graph_version"]
        return self.__version

    async def get_edge_info(self, edge_id: int | None = None) -> dict:
        """
        获取剧情图节点信息

        Args:
            edge_id (int | None, optional): 节点 ID，为 None 时获取根节点信息. Defaults to None.

        Returns:
            dict: 调用 API 返回的结果
        """
        if edge_id is None and self.__root_node:
            edge_id = self.__root_node
        if self.__edge_infos.get(edge_id):
            return self.__edge_infos[edge_id]

        aid = self.get_aid()
        credential = self.credential if self.credential is not None else Credential()

        api = API["info"]["edge_info"]
        params = {
            "aid": aid,
            "graph_version": (await self.get_graph_version()),
            "portal": 0,
            "screen": 0,
            "platform": "pc",
            "choices": "",
            "buvid": (await credential.get_cookies()).get("buvid3"),
        }
        if edge_id is not None:
            params["edge_id"] = edge_id

        ret = await Api(**api, credential=credential).update_params(**params).result
        if edge_id is not None:
            self.__root_node = edge_id
            edge_id = ret["edge_id"]
        self.__edge_infos[edge_id] = ret
        return ret

    async def mark_score(self, score: int = 5) -> int:
        """
        为互动视频打分

        Args:
            score (int, optional): 互动视频分数. Defaults to 5.

        Returns:
            int: 调用 API 返回的结果
        """
        self.credential.raise_for_no_sessdata()
        self.credential.raise_for_no_bili_jct()
        api = API["operate"]["mark_score"]
        data = {"mark": score, "bvid": self.get_bvid()}
        return await Api(**api, credential=self.credential).update_data(**data).result

    async def get_cid(self) -> int:  # type: ignore
        """
        获取稿件 cid

        Returns:
            int: cid
        """
        return await super().get_cid(0)

    async def get_graph(self) -> InteractiveGraph:
        """
        获取稿件情节树

        Returns:
            interactive_video.InteractiveGraph: 情节树
        """
        if not self.__graph:
            edge_info = await self.get_edge_info(None)
            cid = await self.get_cid()
            self.__graph = InteractiveGraph(self, edge_info["edges"]["skin"], cid)
        return self.__graph


class InteractiveEmulator:
    """
    互动视频模拟支持
    """

    def __init__(self, graph: dict) -> None:
        """
        Args:
            graph (dict): 情节树 JSON
        """
        self.__graph = graph
        self.__current_node = graph["root"]
        self.__skin = graph["skin"]
        self.__node_info: dict[int, dict] = {}
        for node in self.__graph["nodes"].keys():
            self.__node_info[int(node)] = self.__graph["nodes"][node]
        self.__variables: list[InteractiveVariable] = []
        for var in self.__node_info[self.__current_node]["vars"]:
            self.__variables.append(
                InteractiveVariable(
                    var["name"], var["id"], var["value"], var["show"], var["random"]
                )
            )
        self.__logs: list[tuple[int, list[InteractiveVariable]]] = []
        self.__current_options: list[list[tuple[int, str, str]]] = []

    def get_current_node(self) -> int:
        """
        获取当前所在节点

        Returns:
            int: 当前所在节点
        """
        return self.__current_node

    def get_skin(self) -> dict:
        """
        获取按钮样式

        Returns:
            dict: 按钮样式
        """
        return self.__skin

    def get_current_cid(self) -> int:
        """
        获取当前节点视频的 cid

        Returns:
            int: 当前节点视频的 cid
        """
        return self.__node_info[self.__current_node]["cid"]

    def get_current_options(self) -> list[list[InteractiveButton]] | None:
        """
        获取当前视频播放完后的按钮选项。

        返回列表，列表每一项为一个列表，提供若干个同一个位置的按钮选项。

        同一个位置的按钮选项通常出现在概率跳转上，点击其中一种情况的按钮，另一种情况的按钮也将触发。

        选择按钮后需记录对应的按钮组在列表中的索引（从 0 开始）。

        部分情况视频播放完毕后直接跳转，此时返回空列表，索引亦记为 0。

        Returns:
            list[list[tuple[int, InteractiveButton]]] | None: 按钮选项，若互动视频已结束则返回 None
        """
        current_info = self.__node_info[self.__current_node]
        children = current_info["sub"]
        # 已结束播放
        if len(children) == 0:
            return None
        # 自动跳转
        if children[0]["jump_type"] == InteractiveNodeJumpingType.DEFAULT.value:
            self.__current_options = [[]]
            for node in children:
                self.__current_options[0].append(
                    (node["id"], node["condition"], node["command"])
                )
            return []
        # 选择跳转
        self.__current_options = []
        btns: list[list[InteractiveButton]] = []
        for idx, child in enumerate(children):
            condition = InteractiveJumpingCondition(
                self.__variables, child["condition"]
            )
            if condition.is_never():
                continue
            btn = InteractiveButton(
                text=child["text"],
                x=child["pos"][0] or -1,
                y=child["pos"][1] or -1,
                align=child["align"],
            )
            # 判断是否与上一个按钮同一个位置（即概率按钮）
            same_pos = False
            if idx != 0:
                cur_pos = child["pos"]
                cur_text = child["text"]
                previous_pos = children[idx - 1]["pos"]
                previous_text = children[idx - 1]["text"]
                if (
                    cur_pos[0]
                    and (abs(cur_pos[0] - previous_pos[0]) <= 5)
                    and (abs(cur_pos[1] - previous_pos[1]) <= 5)
                ):  # 相同位置
                    same_pos = True
                elif cur_text[2:] == previous_text[2:]:  # 去除 A/B/C/D 后文字相同
                    same_pos = True
            if not same_pos:
                btns.append([btn])
                self.__current_options.append(
                    [(child["id"], child["condition"], child["command"])]
                )
            else:
                btns[-1].append(btn)
                self.__current_options[-1].append(
                    (child["id"], child["condition"], child["command"])
                )
        return btns

    def select_option(self, idx: int) -> None:
        """
        选择按钮选项，并跳转。

        Args:
            idx (int): 索引。参考 `get_current_options`
        """
        try:
            selected_btns = self.__current_options[idx]
        except IndexError as e:
            raise ArgsException(f"所有选项中不存在索引 {idx}") from e
        # 刷新随机数值
        for i in range(len(self.__variables)):
            self.__variables[i].refresh_value()
        for node_id, condition_str, command_str in selected_btns:
            # 判断跳转
            condition = InteractiveJumpingCondition(self.__variables, condition_str)
            if not condition.get_result():
                continue
            # 保存当前节点记录
            self.__logs.append((self.__current_node, copy.copy(self.__variables)))
            # 执行跳转
            native_command = InteractiveJumpingCommand(self.__variables, command_str)
            self.__variables = native_command.run_command()
            self.__current_node = node_id
            return
        raise ArgsException("没有任何节点可以跳转。请检查情节树。")

    def get_variables(self) -> list[InteractiveVariable]:
        """
        获取变量

        Returns:
            list[InteractiveVariable]: 变量列表
        """
        return [var for var in self.__variables if var.is_show()]

    def back(self) -> None:
        """
        退回到上一个节点
        """
        state = self.__logs.pop()
        self.__current_node = state[0]
        self.__variables = state[1]


class InteractiveVideoDownloaderEvents(enum.Enum):
    """
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
    """

    START = "START"
    GET = "GET"
    DOWNLOAD_START = "DOWNLOAD_START"
    DOWNLOAD_PART = "DOWNLOAD_PART"
    DOWNLOAD_SUCCESS = "DOWNLOAD_SUCCESS"
    PACKAGING = "PACKAGING"
    SUCCESS = "SUCCESS"
    ABORTED = "ABORTED"
    FAILED = "FAILED"


class InteractiveVideoDownloaderMode(enum.Enum):
    """
    互动视频下载模式

    - IVI: 下载可播放的 ivi 文件
    - NODE_VIDEOS: 下载所有节点的所有视频并存放在某个文件夹，每一个节点的视频命名为 `{节点 id} {节点标题 (自动去除敏感字符)}.mp4`
    - DOT_GRAPH: 下载 dot 格式的情节树图表
    - NO_PACKAGING: 前面按照 ivi 文件下载步骤进行下载，但是最终不会打包成为 ivi 文件，所有文件将存放于一个文件夹中。互动视频数据将存放在一个文件夹中，里面的文件命名/含义与拆包后的 ivi 文件完全相同。
    - JSON: 获取 json 格式情节树，不下载视频。
    """

    IVI = "ivi"
    NODE_VIDEOS = "videos"
    DOT_GRAPH = "dot"
    NO_PACKAGING = "no_pack"
    JSON = "json"


class InteractiveVideoDownloader(AsyncEvent):
    """
    互动视频下载类
    """

    def __init__(
        self,
        video: InteractiveVideo,
        out: str,
        self_download_func: Coroutine | None = None,
        downloader_mode: InteractiveVideoDownloaderMode = InteractiveVideoDownloaderMode.IVI,
        stream_detecting_params: dict | None = None,
        fetching_nodes_retry_times: int = 3,
        download_retry_times: int = 3,
        download_wait_time: int = 3,
    ) -> None:
        """
        Args:
            video (interactive_video.InteractiveVideo): 互动视频类
            out (str): 输出文件地址 (如果模式为 NODE_VIDEOS/NO_PACKAGING 则此参数表示所有节点视频的存放目录)
            self_download_func (Coroutine | None, optional): 自定义下载函数（需 async 函数）. Defaults to None.
            downloader_mode (InteractiveVideoDownloaderMode, optional): 下载模式. Defaults to InteractiveVideoDownloaderMode.IVI.
            stream_detecting_params (dict | None, optional): `VideoDownloadURLDataDetecter` 提取最佳流时传入的参数，可控制视频及音频品质. Defaults to None.
            fetching_nodes_retry_times (int, optional): 获取节点时的最大重试次数. Defaults to 3.
            download_retry_times (int, optional): 下载时的最大重试次数. Defaults to 3.
            download_wait_time (int, optional): 下载之间间隔时间. Defaults to 3.

        为保证视频能被成功下载，请在自定义下载函数请求的时候加入 `bilibili_api.get_bili_headers()` 头部。
        """
        super().__init__()
        self.__video = video
        self.__download_func = self_download_func or self.__download
        self.__out = out
        self.__mode = downloader_mode
        self.__detect_params = stream_detecting_params or {}
        self.__fetching_nodes_retry_times = fetching_nodes_retry_times
        self.__download_retry_times = download_retry_times
        self.__download_wait_time = download_wait_time

    async def __download(self, url: str, out: str) -> None:
        client = get_client()

        dwn_id = await client.download_create(url=url, headers=get_bili_headers())

        if os.path.exists(out):
            os.remove(out)

        parent = os.path.dirname(out)
        if not os.path.exists(parent):
            os.mkdir(parent)

        self.dispatch("DOWNLOAD_START", {"url": url, "out": out})

        bts = 0
        tot = client.download_content_length(cnt=dwn_id)
        start_time = time.perf_counter()

        async with await anyio.open_file(out, "wb") as f:
            while True:
                bts += await f.write(await client.download_chunk(cnt=dwn_id))
                self.dispatch(
                    "DOWNLOAD_PART",
                    {
                        "done": bts,
                        "total": tot,
                        "time": int(time.perf_counter() - start_time),
                    },
                )
                if bts == tot:
                    break

        await client.download_close(cnt=dwn_id)

        self.dispatch("DOWNLOAD_SUCCESS")

    async def __fetch_edges(self) -> dict:
        graph = await self.__video.get_graph()
        async for node in graph.get_all_nodes(retry=self.__fetching_nodes_retry_times):
            info = await node.get_info()
            self.dispatch(
                "GET",
                {
                    "title": info["title"],
                    "node_id": info["edge_id"],
                    "cid": node.get_cid(),
                },
            )
        return await graph.to_json()

    async def __download_videos(self, edges_info: dict, tmp_dir: str) -> None:
        cid_set = set()
        for _, item in edges_info["nodes"].items():
            cid = item["cid"]
            if cid not in cid_set:
                self.dispatch("PREPARE_DOWNLOAD", {"cid": item["cid"]})
                cid_set.add(cid)
                url = await self.__video.get_download_url(cid=cid)
                streams = VideoDownloadURLDataDetecter(url).detect_best_streams(
                    **self.__detect_params
                )
                if streams[0]:
                    retry = self.__download_retry_times
                    while True:
                        try:
                            await anyio.sleep(self.__download_wait_time)
                            await self.__download_func(
                                streams[0].url,
                                tmp_dir + "/" + str(cid) + ".video.mp4",
                            )  # type: ignore
                            break
                        except Exception as e:
                            retry -= 1
                            if retry < 0:
                                raise e
                if streams[1]:
                    retry = self.__download_retry_times
                    while True:
                        try:
                            await anyio.sleep(self.__download_wait_time)
                            await self.__download_func(
                                streams[1].url,
                                tmp_dir + "/" + str(cid) + ".audio.mp4",
                            )  # type: ignore
                            break
                        except Exception as e:
                            retry -= 1
                            if retry < 0:
                                raise e

    async def __main(self) -> None:
        # 初始化
        self.dispatch("START")
        if self.__out == "":
            self.__out = self.__video.get_bvid() + ".ivi"
        if self.__out.endswith(".ivi"):
            self.__out = self.__out.removesuffix(".ivi")
        if os.path.exists(self.__out + ".ivi"):
            os.remove(self.__out + ".ivi")
        tmp_dir = self.__out + ".tmp"
        if not os.path.exists(tmp_dir):
            os.mkdir(tmp_dir)

        edges_info = await self.__fetch_edges()

        async with await anyio.open_file(
            tmp_dir + "/ivideo.json", "w+", encoding="utf-8"
        ) as f:
            await f.write(json.dumps(edges_info, indent=2))

        bvideo_info = await self.__video.get_info()

        async with await anyio.open_file(
            tmp_dir + "/bilivideo.json", "w+", encoding="utf-8"
        ) as f:
            await f.write(json.dumps(bvideo_info, indent=2))

        await self.__download_videos(edges_info, tmp_dir)

        self.dispatch("PACKAGING")

        def package_zip():
            zip = zipfile.ZipFile(
                open(self.__out + ".ivi", "wb+"),
                mode="w",
                compression=zipfile.ZIP_DEFLATED,
            )
            for path, _, filenames in os.walk(tmp_dir):
                fpath = path.replace(tmp_dir, "")
                for filename in filenames:
                    zip.write(
                        os.path.join(path, filename), os.path.join(fpath, filename)
                    )
            zip.close()
            shutil.rmtree(tmp_dir)

        await anyio.to_thread.run_sync(package_zip)

        self.dispatch("SUCCESS")

    async def __node_videos_main(self) -> None:
        self.dispatch("START")
        tmp_dir = self.__out
        if not os.path.exists(tmp_dir):
            os.mkdir(tmp_dir)

        edges_info = await self.__fetch_edges()

        await self.__download_videos(edges_info, tmp_dir)

        self.dispatch("SUCCESS")

    async def __dot_graph_main(self) -> None:
        self.dispatch("START")
        if not self.__out.endswith(".dot"):
            self.__out += ".dot"

        class node_info:
            node_id: int
            subs: list[int]
            cid: int
            title: str

            def __eq__(self, info: object):
                if not isinstance(info, node_info):
                    return False
                self.subs.sort()
                info.subs.sort()
                return (
                    (info.subs == self.subs)
                    and (info.title == self.title)
                    and (info.cid == self.cid)
                )

            def __lt__(self, info: "node_info"):
                return self.cid < info.cid

            def __gt__(self, info: "node_info"):
                return self.cid > info.cid

        fetched_nodes_info: list[node_info] = []
        node_info_dict = {}
        scripts = []
        graph = await self.__video.get_graph()
        queue: list[InteractiveNode] = [await graph.get_root_node()]
        while queue:
            queue_backup = copy.copy(queue)
            queue = []
            for cur_node in queue_backup:
                cur_node_info = await cur_node.get_info()
                cur_node_children = await cur_node.get_children()
                self.dispatch(
                    "GET",
                    {
                        "title": cur_node_info["title"],
                        "node_id": cur_node.get_node_id(),
                    },
                )
                cur_node_info_class = node_info()
                cur_node_info_class.node_id = cur_node.get_node_id()
                cur_node_info_class.cid = cur_node.get_cid()
                cur_node_info_class.subs = [n.get_node_id() for n in cur_node_children]
                cur_node_info_class.title = cur_node_info["title"]
                back_to_pre = False
                back_to_node_title = -1
                for fetched_info in fetched_nodes_info:
                    if fetched_info == cur_node_info_class:
                        back_to_pre = True
                        back_to_node_title = fetched_info.title
                if not back_to_pre:
                    node_info_dict[cur_node.get_node_id()] = cur_node_info_class
                    for cur_node_child in cur_node_children:
                        script_label = ""
                        if cur_node_child.get_jumping_condition().get_condition() != "":  # type: ignore
                            script_label = (
                                script_label
                                + "Condition: ["
                                + cur_node_child.get_jumping_condition().get_condition()
                                + "]"
                            )  # type: ignore
                            if cur_node_child.get_jumping_command().get_command() != "":  # type: ignore
                                script_label = (
                                    script_label
                                    + "\nNative Command: ["
                                    + cur_node_child.get_jumping_command().get_command()
                                    + "]"
                                )  # type: ignore
                        elif cur_node_child.get_jumping_command().get_command() != "":  # type: ignore
                            script_label = (
                                script_label
                                + "\nNative Command: ["
                                + cur_node_child.get_jumping_command().get_command()
                                + "]"
                            )  # type: ignore
                        scripts.append(
                            {
                                "from": cur_node.get_node_id(),
                                "to": cur_node_child.get_node_id(),
                                "label": script_label,
                            }
                        )
                        queue.append(cur_node_child)
                    fetched_nodes_info.append(cur_node_info_class)
                else:
                    node_info_dict[cur_node.get_node_id()] = (
                        f"跳转至 {back_to_node_title}"
                    )
        graph_content = "digraph {\n"
        for script in scripts:
            graph_content += f"\t{script['from']} -> {script['to']}"
            if script["label"] != "":
                graph_content += f' [label="{script["label"]}"]\n'
            else:
                graph_content += "\n"
        for node_info_key, node_info_item in node_info_dict.items():
            if isinstance(node_info_item, node_info):
                graph_content += f'\t{node_info_key} [label="{node_info_item.title}"]\n'
            else:
                graph_content += f'\t{node_info_key} [label="{node_info_item}"]\n'
        vars_string = "Variables: "
        for var in (await graph.get_root_node()).get_vars():
            var_attribute = ""
            if var.is_random():
                var_attribute = "Random"
            else:
                if var.is_show():
                    var_attribute = "Normal"
                else:
                    var_attribute = "Hide"
            vars_string += f"[{var.get_id()} -> {var.get_name()} = {var.get_value()}, {var_attribute}]\n"
        graph_content += f'\tlabel="{vars_string}"'
        graph_content += "}"
        async with await anyio.open_file(
            self.__out, "w+", encoding="utf-8"
        ) as dot_file:
            await dot_file.write(graph_content)
        self.dispatch("SUCCESS")

    async def __no_packaging_main(self) -> None:
        # 初始化
        self.dispatch("START")
        tmp_dir = self.__out
        if not os.path.exists(tmp_dir):
            os.mkdir(tmp_dir)

        edges_info = await self.__fetch_edges()

        async with await anyio.open_file(
            tmp_dir + "/ivideo.json", "w+", encoding="utf-8"
        ) as f:
            await f.write(json.dumps(edges_info, indent=2))

        bvideo_info = await self.__video.get_info()

        async with await anyio.open_file(
            tmp_dir + "/bilivideo.json", "w+", encoding="utf-8"
        ) as f:
            await f.write(json.dumps(bvideo_info, indent=2))

        await self.__download_videos(edges_info, tmp_dir)

        self.dispatch("SUCCESS")

    async def __json_main(self) -> None:
        self.dispatch("START")
        if not self.__out.endswith(".json"):
            self.__out += ".json"
        async with await anyio.open_file(self.__out, "w+", encoding="utf-8") as f:
            await f.write(json.dumps(await self.__fetch_edges()))
        self.dispatch("SUCCESS")

    async def __start(self) -> None:
        if self.__mode.value == "ivi":
            return await self.__main()
        elif self.__mode.value == "dot":
            return await self.__dot_graph_main()
        elif self.__mode.value == "no_pack":
            return await self.__no_packaging_main()
        elif self.__mode.value == "videos":
            return await self.__node_videos_main()
        elif self.__mode.value == "json":
            return await self.__json_main()
        else:
            return

    async def start(self) -> None:
        """
        开始下载
        """
        try:
            return await self.async_event_start(self.__start())
        except Exception as e:
            self.dispatch("FAILED", {"err": e})
            raise e

    def abort(self) -> None:
        """
        中断下载
        """
        self.async_event_cancel()
        self.dispatch("ABORTED", None)
