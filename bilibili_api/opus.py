"""
bilibili_api.opus

图文相关
"""

from copy import copy
import html

import yaml

from . import article, dynamic
from .exceptions import ArgsException
from .utils import cache_pool
from .utils.network import Api, Credential
from .utils.picture import Picture
from .utils.utils import get_api, img_auto_scheme

API = get_api("opus")


class Opus:
    """
    图文类。

    Attributes:
        credential (Credential): 凭据类
    """

    def __init__(self, opus_id: int, credential: Credential | None = None) -> None:
        """
        Args:
            opus_id (int): 图文 id
            credential (Credential | None, optional): 凭据类. Defaults to None.
        """
        self.__id = opus_id
        self.__info = None
        self.credential: Credential = credential or Credential()

    def __str__(self) -> str:
        return f"Opus(opus_id={self.__id})"

    def __repr__(self) -> str:
        return f"Opus(opus_id={self.__id})"

    def get_opus_id(self) -> int:
        """
        获取图文 id

        Returns:
            int: 图文 idd
        """
        return self.__id

    async def is_article(self) -> bool:
        """
        获取图文是否同时为专栏

        如果是，则专栏/图文/动态数据共享，可以投币

        Returns:
            bool: 是否同时为专栏
        """
        if cache_pool.dynamic_is_article.get(self.__id) is None:
            await self.get_info()
        return cache_pool.dynamic_is_article[self.__id]

    async def turn_to_article(self) -> "article.Article":
        """
        对专栏图文，转换为专栏（评论、点赞等数据专栏/动态/图文共享）

        如图文无对应专栏将报错。

        Returns:
            article.Article: 专栏类
        """
        # 此处建议先阅读 dynamic.turn_to_article 注释再尝试理解
        if cache_pool.dynamic2article.get(self.__id) is None:
            await self.get_info()
            if not await self.is_article():
                raise ArgsException("提供的动态无对应专栏")
        return article.Article(
            cvid=cache_pool.dynamic2article[self.__id], credential=self.credential
        )

    def turn_to_dynamic(self) -> "dynamic.Dynamic":
        """
        转为动态

        图文完全包含于动态，且图文与专栏 id 数值上一致，因此此函数绝对成功。

        Returns:
            dynamic.Dynamic: 对应的动态类
        """
        return dynamic.Dynamic(dynamic_id=self.__id, credential=self.credential)

    async def get_info(self) -> dict:
        """
        获取图文基本信息

        Returns:
            dict: 调用 API 返回的结果
        """
        if self.__info is None:
            api = API["info"]["detail"]
            params = {
                "timezone_offset": -480,
                "id": self.__id,
                "features": "onlyfansVote,onlyfansAssetsV2,decorationCard,htmlNewStyle,ugcDelete,editable,opusPrivateVisible",
            }
            self.__info = (
                await Api(**api, credential=self.credential)
                .update_params(**params)
                .result
            )
        if self.__info.get("fallback"):
            raise ArgsException("传入的 opus_id 不正确")
        cache_pool.dynamic_is_article[self.__id] = (
            self.__info["item"]["basic"]["comment_type"] == 12
        )
        if cache_pool.dynamic_is_article[self.__id]:
            cache_pool.dynamic2article[self.__id] = int(
                self.__info["item"]["basic"]["rid_str"]
            )
            cache_pool.article2dynamic[cache_pool.dynamic2article[self.__id]] = (
                self.__id
            )
        cache_pool.dynamic_is_opus[self.__id] = True
        return copy(self.__info)

    async def markdown(self) -> str:
        """
        将图文转为 markdown

        Returns:
            str: markdown 内容
        """
        await self.get_info()

        title = {"module_title": {"text": ""}}
        content = {"module_content": {"paragraphs": []}}

        for module in self.__info["item"]["modules"]:  # type: ignore
            if module.get("module_title"):
                title = module
            if module.get("module_content"):
                content = module

        markdown = f"# {title['module_title']['text']}\n\n"

        def parse_node(para: dict) -> str:
            para_raw = ""
            if para["para_type"] in [1, 4]:
                for node in para["text"]["nodes"]:
                    raw = ""
                    if node.get("rich"):
                        url = node["rich"].get("jump_url")
                        if url is None:
                            url = ""
                        if node["rich"].get("emoji"):
                            url = node["rich"]["emoji"]["icon_url"]
                        if node["rich"]["type"] == "RICH_TEXT_NODE_TYPE_AT":
                            uid = node["rich"]["rid"]
                            url = f"https://space.bilibili.com/{uid}"
                        text = node["rich"]["text"]
                        if url.startswith("//"):
                            url = "https:" + url
                        if node["rich"].get("emoji"):
                            raw = f"<img width=50px height=50px src={url}> "
                        else:
                            raw = f"[{text}]({url})"
                    elif node.get("word"):
                        raw = node["word"]["words"]
                        if node["word"].get("style"):
                            if node["word"]["style"].get("bold"):
                                if node["word"]["style"]["bold"]:
                                    if raw.strip():
                                        raw = f"**{raw}**"
                    para_raw += raw + " "
                if para["para_type"] == 4:

                    def quote(origin: str) -> str:
                        txt = origin.strip()
                        return " " * (len(origin) - len(txt)) + "> " + txt

                    para_raw = "\n".join([quote(line) for line in para_raw.split("\n")])
            elif para["para_type"] == 2:
                for pic in para["pic"]["pics"]:
                    url = pic["url"]
                    para_raw += f"![]({url}) \n"
            elif para["para_type"] == 3:
                para_raw = "---"
            elif para["para_type"] == 5:
                for item in para["list"]["items"]:
                    item = {"para_type": 1, "text": item}
                    para_raw += f" - {parse_node(item)}\n"
            elif para["para_type"] == 7:
                lang = para["code"]["lang"].removeprefix("language-")
                content = para["code"]["content"]
                content = html.unescape(content)
                para_raw = f"``` {lang}\n{content}\n```\n\n"
            if para.get("align") == 1:
                para_raw = f'<div style="text-align: center">\n\n{para_raw}\n\n</div>'
            elif para.get("align") == 2:
                para_raw = f'<div style="text-align: right">\n\n{para_raw}\n\n</div>'
            return para_raw

        for para in content["module_content"]["paragraphs"]:
            markdown += f"{parse_node(para)}\n\n"

        meta_yaml = yaml.safe_dump(self.__info, allow_unicode=True)
        content = f"---\n{meta_yaml}\n---\n\n{markdown}"
        return content

    async def get_images_raw_info(self) -> list[dict]:
        """
        获取图文所有图片原始信息

        Returns:
            list[dict]: 图片信息
        """
        await self.get_info()

        result = []
        content = {"module_content": {"paragraphs": []}}

        for module in self.__info["item"]["modules"]:  # type: ignore
            if module.get("module_content"):
                content = module

        for para in content["module_content"]["paragraphs"]:
            if para["para_type"] == 2:
                for pic in para["pic"]["pics"]:
                    result.append(pic)

        return result

    async def get_images(self) -> list["Picture"]:
        """
        获取图文所有图片并转为 Picture 类

        Returns:
            list['Picture']: 图片信息
        """
        result = []
        images_raw_info = await self.get_images_raw_info()
        for image in images_raw_info:
            result.append(await Picture().load_url(url=img_auto_scheme(image["url"])))
        return result

    async def set_like(self, status: bool) -> dict:
        """
        设置图文点赞状态

        Args:
            status (bool): 点赞状态.

        Returns:
            dict: 调用 API 返回的结果
        """
        return await self.turn_to_dynamic().set_like(status)

    async def set_favorite(self, status: bool = True) -> dict:
        """
        设置图文收藏状态

        Args:
            status (bool, optional): 收藏状态. Defaults to True.

        Returns:
            dict: 调用 API 返回的结果
        """
        return await self.turn_to_dynamic().set_favorite(status)

    async def add_coins(self) -> dict:
        """
        给专栏投币，目前只能投一个

        Returns:
            dict: 调用 API 返回的结果
        """
        return await (await self.turn_to_article()).add_coins()

    async def get_reaction(self, offset: str = "") -> dict:
        """
        获取点赞、转发

        Args:
            offset (str, optional): 偏移值（下一页的第一个动态 ID，为该请求结果中的 offset 键对应的值），类似单向链表. Defaults to ''.

        Returns:
            dict: 调用 API 返回的结果
        """
        return await self.turn_to_dynamic().get_reaction(offset=offset)

    async def get_rid(self) -> int:
        """
        获取 rid，以传入 `comment.get_comments_lazy` 等函数 oid 参数对评论区进行操作

        Returns:
            int: rid
        """
        return int((await self.get_info())["item"]["basic"]["rid_str"])
