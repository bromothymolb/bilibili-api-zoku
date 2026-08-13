"""
bilibili_api.exceptions.LiveException

"""

from .ApiException import ApiException


class LiveException(ApiException):
    """
    直播异常。
    """

    def __init__(self, msg: str):
        """
        Args:
            msg (str):   错误消息。
        """
        super().__init__()
        self.msg = msg
