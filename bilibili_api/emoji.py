"""
bilibili_api.emoji

表情包相关
"""

from .utils.high_level import Api, Credential
from .utils.utils import get_api

API = get_api("emoji")


async def get_emoji_list(
    business: str = "reply", credential: Credential | None = None
) -> dict:
    """
    获取表情包列表

    Args:
        business (str, optional): 使用场景, reply / dynamic. Defaults to 'reply'.
        credential (Credential | None, optional): 登录凭证. Defaults to None.

    Returns:
        dict: 调用 API 返回的结果
    """
    credential = credential or Credential()
    api = API["list"]
    params = {"business": business}
    return await Api(**api, credential=credential).update_params(**params).result


async def get_emoji_detail(id: int | list[int], business: str = "reply") -> dict:
    """
    获取表情包详情

    Args:
        id (int | list[int]): 表情包 id，可通过 `get_emoji_list` 或 `get_all_emoji` 查询。
        business (str, optional): 使用场景, reply / dynamic. Defaults to 'reply'.

    Returns:
        dict: 调用 API 返回的结果
    """
    api = API["detail"]
    params = {
        "ids": ",".join([str(i) for i in id]) if isinstance(id, list) else id,
        "business": business,
    }
    return await Api(**api).update_params(**params).result


async def get_all_emoji(
    business: str = "reply", credential: Credential | None = None
) -> dict:
    """
    获取所有表情包

    Args:
        business (str, optional): 使用场景, reply / dynamic. Defaults to 'reply'.
        credential (Credential | None, optional): 登录凭证. Defaults to None.

    Returns:
        dict: 调用 API 返回的结果
    """
    credential = credential or Credential()
    credential.raise_for_no_sessdata()
    api = API["all"]
    params = {"business": business}
    return await Api(**api, credential=credential).update_params(**params).result


async def add_emoji(package_id: int, credential: Credential | None = None) -> dict:
    """
    添加表情包

    Args:
        package_id (int): 表情包 id，可通过 `get_emoji_list` 或 `get_all_emoji` 查询。
        credential (Credential | None, optional): 登录凭证. Defaults to None.

    Returns:
        dict: 调用 API 返回的结果
    """
    credential = credential or Credential()
    credential.raise_for_no_sessdata()
    api = API["add"]
    params = {
        "package_id": package_id,
        "business": "reply",
        "csrf": credential.bili_jct,
    }
    return await Api(**api, credential=credential).update_params(**params).result
