"""
bilibili_api.utils.picture

Picture 类
"""

from dataclasses import dataclass, field
import inspect
import io
import os

from anyio import TaskHandle, create_task_group, to_thread
from PIL import Image, ImageSequence
from yarl import URL

from ..exceptions import ArgsException
from .network import BiliAPIFile, Credential, get_client


@dataclass
class Picture:
    """
    (@dataclasses.dataclass)

    图片类，包含图片链接、尺寸以及下载操作。

    Attributes:
        height    (int)            : 高度
        width     (int)            : 宽度
        url       (str)            : 图片链接
        extension (str)            : 文件格式
        format    (str)            : 图片格式
        mime_type (str)            : MIME 类型。
        image     (PIL.Image.Image): Image 实例

    可以使用静态类方法 `load_url`, `from_content` 或 `from_file` 加载图片。
    """

    url: str = ""
    extension: str = ""
    format: str = ""
    mime_type: str = ""
    image: Image.Image = field(default_factory=Image.Image)

    _content: bytes | None = None

    @property
    def width(self) -> int:
        return self.image.width

    @property
    def height(self) -> int:
        return self.image.height

    def __str__(self) -> str:
        return f"Picture(height={self.height}, width={self.width}, format='{self.format}', url='{self.url}')"

    def __repr__(self) -> str:
        return f"Picture(height={self.height}, width={self.width}, format='{self.format}', url='{self.url}')"

    def _set_picture_meta(self, raw: bytes, extension: str) -> None:
        content_io = io.BytesIO(raw)
        content_io.seek(0)
        self.image = Image.open(content_io)
        self.extension = extension
        self.format = self.image.format or ""
        self.mime_type = self.image.get_format_mimetype() or ""
        self._content = raw  # cache

    def _set_picture_meta_from_file(self, img_path: str, extension: str) -> None:
        self.image = Image.open(img_path)
        self.extension = extension
        self.format = self.image.format or ""
        self.mime_type = self.image.get_format_mimetype() or ""

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
        obj.url = url
        obj._set_picture_meta(
            resp.raw,
            url.split("/")[-1].split(".")[-1].split("?")[0],
        )
        return obj

    @staticmethod
    def from_file(path: str) -> "Picture":
        """
        加载本地图片

        Args:
            path (str): 图片地址

        Returns:
            Picture: 加载后的图片对象
        """
        obj = Picture()
        obj.url = "file://" + path
        obj._set_picture_meta_from_file(path, os.path.basename(path).split(".")[-1])
        return obj

    @staticmethod
    def from_content(content: bytes, extension: str) -> "Picture":
        """
        加载字节数据

        Args:
            content (bytes): 图片内容
            extension (str): 图片后缀名，如 `webp`, `jpg`, `ico`

        Returns:
            Picture: 加载后的图片对象
        """
        obj = Picture()
        obj.url = f"<bytes>.{format}"
        obj._set_picture_meta(content, extension)
        return obj

    async def to_biliapifile(self) -> BiliAPIFile:
        """
        将图片实例转换为 BiliAPIFile 实例

        Returns:
            BiliAPIFile: BiliAPIFile 实例
        """
        return BiliAPIFile(
            name=f"chiya.{self.format}",
            content=await self.content(),
            mime_type=self.mime_type,
        )

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

    async def download(self, path: str) -> "Picture":
        """
        下载图片至本地。支持自定义文件格式。

        Args:
            path     (str): 下载地址。

        Returns:
            Picture: `self`
        """

        def download():
            self.image.save(
                path,
                save_all=(True if path.split(".")[1] in ["webp", "gif"] else False),
            )

        await to_thread.run_sync(download)
        return self

    async def content(self) -> bytes:
        """
        获取图片内容

        Returns:
            bytes: 图片内容
        """
        if not self._content:

            def fetch_content():
                io_stream = io.BytesIO()
                self.image.save(
                    io_stream,
                    format=self.format,
                    save_all=(True if self.format in ["WEBP", "GIF"] else False),
                )
                return io_stream.getvalue()

            self._content = await to_thread.run_sync(fetch_content)
        return self._content

    def set_extension(self, extension: str) -> "Picture":
        """
        更改图片后缀名

        Args:
            extension (str): 新后缀名

        Returns:
            Picture: `self`
        """
        self.extension = extension
        # copied from PIL source code
        extension = "." + extension
        if not Image._import_plugin_for_extension(extension):
            Image.preinit()
        if extension not in Image.EXTENSION:
            Image.init()
        try:
            self.format = Image.EXTENSION[extension]
        except KeyError as e:
            msg = f"unknown file extension: {extension}"
            raise ValueError(msg) from e
        return self

    async def image_call(self, func: str, *args, **kwargs) -> "Picture":
        """
        调用 PIL.Image.Image 中的返回 Image 的操作函数

        Args:
            func (str): 调用的函数名。如 `resize` 调整大小，`filter` 添加滤镜。
            args (Any): 要传递给函数的参数。 *args 传递。
            kwargs (Any): 要传递给函数的参数。 **kwargs 传递。

        Returns:
            Picture: `self`
        """

        def call(image) -> Image.Image:
            callable = getattr(image, func)
            if inspect.signature(callable).return_annotation != "Image":
                raise ArgsException("不支持返回值不为 Image 的函数调用")
            return callable(*args, **kwargs)

        if self.format not in ["WEBP", "GIF"]:
            self.image = await to_thread.run_sync(call, self.image)
        else:
            images = ImageSequence.all_frames(self.image)
            handles: list[TaskHandle] = []
            async with create_task_group() as tg:
                for image in images:
                    handles.append(tg.create_task(to_thread.run_sync(call, image)))
            results: list[Image.Image] = [handle.return_value for handle in handles]

            def fetch_result():
                io_stream = io.BytesIO()
                results.pop().save(
                    io_stream,
                    format=self.format,
                    append_images=results,
                    save_all=True,
                )
                return io_stream

            self.image = Image.open(await to_thread.run_sync(fetch_result))

        return self
