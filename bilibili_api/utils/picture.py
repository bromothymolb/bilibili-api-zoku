"""
bilibili_api.utils.picture

Picture 类
"""

from dataclasses import dataclass, field
import io
import os
import tempfile

from anyio import to_thread
from PIL import Image
from yarl import URL

from .network import BiliAPIFile, Credential, get_client


@dataclass
class Picture:
    """
    (@dataclasses.dataclass)

    图片类，包含图片链接、尺寸以及下载操作。

    Args:
        height    (int)  : 高度
        width     (int)  : 宽度
        url       (str)  : 图片链接
        format    (str)  : 格式，例如: png
        mime_type (str)  : MIME 类型。
        content   (bytes): 图片内容
        size      (int)  : 大小。单位 KB

    可以使用静态类方法 `load_url`, `from_content` 或 `from_file` 加载图片。
    """

    height: int = -1
    width: int = -1
    url: str = ""
    format: str = ""
    mime_type: str = ""
    content: bytes = b""
    size: int = 0

    _image_file: Image.Image = field(default_factory=Image.Image)
    _image_path: str = ""

    def __str__(self) -> str:
        return f"Picture(height={self.height}, width={self.width}, format='{self.format}', size~={self.size}KB, url='{self.url}')"

    def __repr__(self) -> str:
        # no content...
        return f"Picture(height={self.height}, width={self.width}, format='{self.format}', size~={self.size}B, url='{self.url}')"

    def _set_picture_meta_from_bytes(self, format: str) -> None:
        tmp_dir = tempfile.gettempdir()
        img_path = os.path.join(tmp_dir, "test." + format)
        with open(img_path, "wb+") as file:
            file.write(self.content)
        self._image_path = img_path
        self._image_file = Image.open(img_path)
        self.height = self._image_file.height
        self.width = self._image_file.width
        self.format = format
        self.mime_type = self._image_file.get_format_mimetype()  # type: ignore
        self.size = int(round(os.path.getsize(img_path) / 1024, 0))

    def _set_picture_meta_from_file(self, img_path: str, format: str) -> None:
        self._image_path = img_path
        self._image_file = Image.open(img_path)
        self.content = self._image_file.fp.read()  # type: ignore
        self.height = self._image_file.height
        self.width = self._image_file.width
        self.format = format
        self.mime_type = self._image_file.get_format_mimetype()  # type: ignore
        self.size = int(round(os.path.getsize(img_path) / 1024, 0))

    @staticmethod
    async def load_url(url: str) -> "Picture":
        """
        加载网络图片。(async 方法)

        Args:
            url (str): 图片链接

        Returns:
            Picture: 加载后的图片对象
        """
        if URL(url).scheme == "":
            url = "https:" + url
        obj = Picture()
        session = get_client()
        resp = await session.request(
            method="GET",
            url=url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36 Edg/116.0.1938.54",
                "Referer": url,
            },
        )
        obj.content = resp.raw
        obj.url = url
        await to_thread.run_sync(
            obj._set_picture_meta_from_bytes,
            url.split("/")[-1].split(".")[-1].split("?")[0],
        )
        return obj

    @staticmethod
    async def load_file(path: str) -> "Picture":
        """
        异步加在本地图片

        Args:
            path (str): 图片地址

        Returns:
            Picture: 加载后的图片对象
        """
        obj = Picture()
        obj.url = "file://" + path
        await to_thread.run_sync(
            obj._set_picture_meta_from_file, path, os.path.basename(path).split(".")[-1]
        )
        return obj

    @staticmethod
    async def from_content(content: bytes, format: str) -> "Picture":
        """
        加载字节数据

        Args:
            content (bytes): 图片内容
            format (str): 图片后缀名，如 `webp`, `jpg`, `ico`

        Returns:
            Picture: 加载后的图片对象
        """
        obj = Picture()
        obj.content = content
        obj.url = "<bytes>"
        await to_thread.run_sync(obj._set_picture_meta_from_bytes, format)
        return obj

    def _to_biliapifile(self) -> BiliAPIFile:
        return BiliAPIFile(path=self._image_path, mime_type=self.mime_type)  # type: ignore

    async def upload(self, credential: Credential) -> "Picture":
        """
        上传图片至 B 站。

        Args:
            credential (Credential): 凭据类。

        Returns:
            Picture: `self`
        """
        from ..dynamic import upload_image

        res = await upload_image(self, credential)
        self.url = res["image_url"]
        return self

    async def upload_by_note(self, credential: Credential) -> "Picture":
        """
        通过笔记接口上传图片至 B 站。

        Args:
            credential (Credential): 凭据类。

        Returns:
            Picture: `self`
        """
        from ..note import upload_image

        res = await upload_image(self, credential)
        self.url = res["location"]
        return self

    async def convert_format(self, new_format: str) -> "Picture":
        """
        将图片转换为另一种格式。

        Args:
            new_format (str): 新的格式。例：`png`, `ico`, `webp`.

        Returns:
            Picture: `self`
        """

        def convert():
            stream = io.BytesIO()
            self._image_file.save(stream, format=new_format)
            self.content = stream.getvalue()
            self.url = "<bytes>"
            self._set_picture_meta_from_bytes(new_format)

        await to_thread.run_sync(convert)
        return self

    async def resize(self, width: int, height: int) -> "Picture":
        """
        调整大小

        Args:
            width (int): 宽度
            height (int): 高度

        Returns:
            Picture: `self`
        """

        def resize():
            self._image_file = self._image_file.resize((width, height))
            stream = io.BytesIO()
            self._image_file.save(stream, format=self.format)
            self.content = stream.getvalue()
            self.url = "<bytes>"
            self._set_picture_meta_from_bytes(self.format)

        await to_thread.run_sync(resize)
        return self

    async def download(self, path: str) -> "Picture":
        """
        下载图片至本地。

        Args:
            path (str): 下载地址。

        Returns:
            Picture: `self`
        """

        def download():
            self._image_file.save(
                path, save_all=(True if self.format in ["webp", "gif"] else False)
            )
            self.url = "file://" + path

        await to_thread.run_sync(download)
        return self

    def to_json(self) -> dict:
        """
        转换为 bilibili api 中的 json 格式，提供图片链接/长宽/大小

        Returns:
            dict: 图片链接/长宽/大小
        """
        return {
            "img_src": self.url,
            "img_width": self.width,
            "img_height": self.height,
            "img_size": self.size,
        }
