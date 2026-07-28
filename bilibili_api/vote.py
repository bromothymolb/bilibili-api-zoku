"""
bilibili_api.vote

投票相关操作。

需要 vote_id,获取 vote_id: https://bromothymolb.github.io/bilibili-api-zoku/#/vote_id
"""

from enum import Enum

from .user import fetch_dedeuserid
from .utils.network import Api, Credential
from .utils.picture import Picture
from .utils.utils import get_api

API = get_api("vote")


vote_info = {}


class VoteType(Enum):
    """
    投票类型枚举类

    + TEXT: 文字投票
    + IMAGE: 图片投票
    """

    TEXT = 0
    IMAGE = 1


class VoteChoices:
    """
    投票选项类
    """

    def __init__(self) -> None:
        """ """
        # don't remove this empty docstring
        self.choices = []

    def add_choice(
        self, desc: str, image: str | Picture | None = None
    ) -> "VoteChoices":
        """
        往 VoteChoices 添加选项

        Args:
            desc (str): 选项描述
            image (str | Picture | None, optional): 选项的图片链接，用于图片投票。支持 Picture 类. Defaults to None.

        Returns:
            VoteChoices: `self`
        """
        if isinstance(image, Picture):
            image = image.url
        self.choices.append({"desc": desc, "img_url": image or ""})
        return self

    def remove_choice(self, index: int) -> "VoteChoices":
        """
        从 VoteChoices 移除选项

        Args:
            index (int): 选项索引

        Returns:
            VoteChoices: `self`
        """
        self.choices.remove(index)
        return self

    def get_choices(self) -> dict:
        """
        获取 VoteChoices 的 choices

        Returns:
            dict: choices
        """
        results = {"options": []}
        for i in range(len(self.choices)):
            results["options"].append(
                {
                    "opt_desc": self.choices[i]["desc"],
                    "img_url": self.choices[i]["img_url"],
                }
            )
        return results


class Vote:
    """
    投票类

    Attributes:
        vote_id (int): vote_id, 获取：https://bromothymolb.github.io/bilibili-api-zoku/#/sub/vote_id

        credential (Credential): 凭据类
    """

    def __init__(self, vote_id: int, credential: Credential | None = None) -> None:
        """
        Args:
            vote_id (int): vote_id, 获取：https://bromothymolb.github.io/bilibili-api-zoku/#/sub/vote_id
            credential (Credential | None, optional): 凭据类，非必要. Defaults to None.
        """
        self.__vote_id = vote_id
        self.credential: Credential = credential or Credential()
        self.__info: dict | None = None

    def __str__(self) -> str:
        return f"Vote(vote_id={self.__vote_id})"

    def __repr__(self) -> str:
        return f"Vote(vote_id={self.__vote_id})"

    def get_vote_id(self) -> int:
        """
        获取投票 id

        Returns:
            int: 投票 id
        """
        return self.__vote_id

    async def get_info(self) -> dict:
        """
        获取投票详情

        Returns:
            dict: 调用 API 返回的结果
        """
        if self.__info is None:
            api = API["info"]["vote_info"]
            params = {
                "vote_id": self.get_vote_id(),
                "csrf": self.credential.bili_jct or "",
            }
            info = await Api(**api).update_params(**params).result
            self.__info = info
            return info
        return self.__info

    async def get_title(self) -> str:
        """
        快速获取投票标题

        Returns:
            str: 投票标题
        """
        if vote_info.get(self.get_vote_id()):
            return vote_info[self.get_vote_id()]["title"]
        return (await self.get_info())["vote_info"]["title"]

    async def get_desc(self) -> str:
        """
        获取投票描述

        Returns:
            str: 投票描述
        """
        if vote_info.get(self.get_vote_id()):
            return vote_info[self.get_vote_id()]["desc"]
        return (await self.get_info())["vote_info"]["desc"]

    async def get_choice_cnt(self) -> int:
        """
        获取最多选择选项数目

        Returns:
            int: 最多选择选项数目
        """
        if vote_info.get(self.get_vote_id()):
            return vote_info[self.get_vote_id()]["choice_cnt"]
        return (await self.get_info())["vote_info"]["choice_cnt"]

    async def get_options(self) -> dict:
        """
        获取选项

        Returns:
            dict: 选项数据
        """
        if vote_info.get(self.get_vote_id()):
            return vote_info[self.get_vote_id()]["options"]
        return (await self.get_info())["vote_info"]["options"]

    async def get_duration(self) -> dict:
        """
        获取选项

        Returns:
            dict: 选项数据
        """
        if vote_info.get(self.get_vote_id()):
            return vote_info[self.get_vote_id()]["duration"]
        info = (await self.get_info())["vote_info"]
        return info["end_time"] - info["ctime"]

    async def update_vote(
        self,
        title: str,
        _type: VoteType,
        choice_cnt: int,
        duration: int,
        choices: VoteChoices,
        desc: str | None = None,
    ) -> dict:
        """
        更新投票内容

        Args:
            title (str): 投票标题
            _type (VoteType): 投票类型
            choice_cnt (int): 最多几项
            duration (int): 常用: 三天:259200/七天:604800/三十天:2592000
            choices (vote.VoteChoices): 投票选项
            desc (str | None, optional): 投票描述. Defaults to None.

        Returns:
            dict: 调用 API 返回的结果
        """
        self.credential.raise_for_no_sessdata()
        self.credential.raise_for_no_bili_jct()
        api = API["operate"]["update"]
        params = {"csrf": self.credential.bili_jct}
        data = {
            "title": title,
            "desc": desc,
            "type": _type.value,
            "choice_cnt": choice_cnt,
            "duration": duration,
            "vote_id": self.get_vote_id(),
            "vote_publisher": await fetch_dedeuserid(self.credential),
        }
        data.update(choices.get_choices())
        self.__info = None
        vote_info[self.get_vote_id()] = data
        if choice_cnt > len(choices.choices):
            raise ValueError("choice_cnt 大于 choices 选项数")
        return (
            await Api(**api, credential=self.credential)
            .update_params(**params)
            .update_data(**{"vote_info": data})
            .result
        )

    async def delete_vote(self) -> dict:
        """
        删除投票

        Returns:
            dict: 调用 API 返回的结果
        """
        self.credential.raise_for_no_sessdata()
        self.credential.raise_for_no_bili_jct()
        api = API["operate"]["delete"]
        params = {"csrf": self.credential.bili_jct}
        data = {
            "vote_id": self.get_vote_id(),
            "uid": await fetch_dedeuserid(self.credential),
        }
        return (
            await Api(**api, credential=self.credential)
            .update_params(**params)
            .update_data(**data)
            .result
        )


async def create_vote(
    title: str,
    _type: VoteType,
    choice_cnt: int,
    duration: int,
    choices: VoteChoices,
    credential: Credential,
    desc: str | None = None,
) -> Vote:
    """
    创建投票

    Args:
        title (str): 投票标题
        _type (VoteType): 投票类型
        choice_cnt (int): 最多几项
        duration (int): 投票持续秒数，常用: 三天:259200/七天:604800/三十天:2592000
        choices (vote.VoteChoices): 投票选项
        credential (Credential): Credential
        desc (str | None, optional): 投票描述. Defaults to None.

    Returns:
        vote.Vote: Vote 类
    """
    credential.raise_for_no_sessdata()
    credential.raise_for_no_bili_jct()
    api = API["operate"]["create"]
    params = {"csrf": credential.bili_jct}
    data = {
        "title": title,
        "desc": desc or "",
        "type": _type.value,
        "choice_cnt": choice_cnt,
        "duration": duration,
        "release_scene": "dynamic",
        "vote_publisher": await fetch_dedeuserid(credential),
    }
    data.update(choices.get_choices())
    if choice_cnt > len(choices.choices):
        raise ValueError("choice_cnt 大于 choices 选项数")
    vote_id = (
        await Api(**api, credential=credential)
        .update_params(**params)
        .update_data(**{"vote_info": data})
        .update_headers(Referer="https://t.bilibili.com")
        .result
    )["vote_id"]
    vote_info[vote_id] = data
    return Vote(vote_id=vote_id, credential=credential)
