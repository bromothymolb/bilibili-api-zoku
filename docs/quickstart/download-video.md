# 下载视频

最后，我们将尝试下载视频，通过文档的搜索可以发现，模块提供 `Video.get_download_url` 函数。此函数接受两个参数，任选其一即可，一个是分 P 数，一个是 cid。分 P 此处不再过多解释，cid 实际上一一对应了每个视频的每一个分 P，每一个 cid 都对应了一个视频一个分 P 的视频流地址、弹幕池、字幕、播放记录，等等。cid 可以通过 `Video.get_cid` 异步通过视频和分 P 获取，当然此处传入分 P 数即可。

事实上，所有接口支持的参数仅有 cid，模块对分 P 的支持建立在 `get_cid` 上，这个函数规定，分 P 数从 0 开始计数，使用时需注意。

``` python
from bilibili_api import sync, video


async def main() -> None:
    v = video.Video(aid=2)
    download_url = await v.get_download_url(page_index=0)
    print(download_url)


sync(main())
```

运行代码可以得到很长一串返回字典，视频下载 url 就在其中。以下是返回字典格式化输出结果（部分）：

``` python
{
    ...
    "dash": {
        ...
        "video": [
            {
                "id": 32,
                "baseUrl": "https://xy220x202x9x156xy.mcdn.bilivideo.cn:8082/v1/resource/upgcxcode/31/21/62131/62131_da3-1-100110.m4s?agrr=1&build=0&buvid=9A7E608A-EC92-8A1D-7607-9CE215EE6DC310901infoc&bvc=vod&bw=69406&deadline=1785329211&dl=0&e=ig8euxZM2rNcNbdlhoNvNC8BqJIzNbfqXBvEqxTEto8BTrNvN0GvT90W5JZMkX_YN0MvXg8gNEV4NC8xNEV4N03eN0B5tZlqNxTEto8BTrNvNeZVuJ10Kj_g2UB02J0mN0B5tZlqNCNEto8BTrNvNC7MTX502C8f2jmMQJ6mqF2fka1mqx6gqj0eN0B599M%3D&f=u_0_0&gen=playurlv3&lrs=-1&mid=0&nbs=1&nettype=0&og=hw&oi=0x2408823ca615d45439c4b84ea9f34d08&orderid=0%2C3&os=cosbv&platform=pc&qn_dyeid=05801ffafaecdc5c0027b0936a69da1b&sign=6ef1c2&traceid=trcMSmNMthESSn_0_e_N&uipk=5&uparams=e%2Ctrid%2Cuipk%2Cnbs%2Cplatform%2Cgen%2Cos%2Coi%2Cmid%2Cdeadline%2Cog&upsig=0e7c735dc9bac4861476c99b6bc47cc7",
                "base_url": "https://xy220x202x9x156xy.mcdn.bilivideo.cn:8082/v1/resource/upgcxcode/31/21/62131/62131_da3-1-100110.m4s?agrr=1&build=0&buvid=9A7E608A-EC92-8A1D-7607-9CE215EE6DC310901infoc&bvc=vod&bw=69406&deadline=1785329211&dl=0&e=ig8euxZM2rNcNbdlhoNvNC8BqJIzNbfqXBvEqxTEto8BTrNvN0GvT90W5JZMkX_YN0MvXg8gNEV4NC8xNEV4N03eN0B5tZlqNxTEto8BTrNvNeZVuJ10Kj_g2UB02J0mN0B5tZlqNCNEto8BTrNvNC7MTX502C8f2jmMQJ6mqF2fka1mqx6gqj0eN0B599M%3D&f=u_0_0&gen=playurlv3&lrs=-1&mid=0&nbs=1&nettype=0&og=hw&oi=0x2408823ca615d45439c4b84ea9f34d08&orderid=0%2C3&os=cosbv&platform=pc&qn_dyeid=05801ffafaecdc5c0027b0936a69da1b&sign=6ef1c2&traceid=trcMSmNMthESSn_0_e_N&uipk=5&uparams=e%2Ctrid%2Cuipk%2Cnbs%2Cplatform%2Cgen%2Cos%2Coi%2Cmid%2Cdeadline%2Cog&upsig=0e7c735dc9bac4861476c99b6bc47cc7",
                "backupUrl": [
                    "https://upos-sz-mirrorcos.bilivideo.com/upgcxcode/31/21/62131/62131_da3-1-100110.m4s?e=ig8euxZM2rNcNbdlhoNvNC8BqJIzNbfqXBvEqxTEto8BTrNvN0GvT90W5JZMkX_YN0MvXg8gNEV4NC8xNEV4N03eN0B5tZlqNxTEto8BTrNvNeZVuJ10Kj_g2UB02J0mN0B5tZlqNCNEto8BTrNvNC7MTX502C8f2jmMQJ6mqF2fka1mqx6gqj0eN0B599M=&trid=41fee4a83c404181b466435b5671d2eu&uipk=5&nbs=1&platform=pc&gen=playurlv3&os=cosbv&oi=0x2408823ca615d45439c4b84ea9f34d08&mid=0&deadline=1785329211&og=hw&upsig=0e7c735dc9bac4861476c99b6bc47cc7&uparams=e,trid,uipk,nbs,platform,gen,os,oi,mid,deadline,og&bvc=vod&nettype=0&bw=69406&lrs=-1&build=0&dl=0&f=u_0_0&qn_dyeid=05801ffafaecdc5c0027b0936a69da1b&agrr=1&buvid=9A7E608A-EC92-8A1D-7607-9CE215EE6DC310901infoc&orderid=0,3",
                    "https://upos-sz-mirrorcos.bilivideo.com/upgcxcode/31/21/62131/62131_da3-1-100110.m4s?e=ig8euxZM2rNcNbdlhoNvNC8BqJIzNbfqXBvEqxTEto8BTrNvN0GvT90W5JZMkX_YN0MvXg8gNEV4NC8xNEV4N03eN0B5tZlqNxTEto8BTrNvNeZVuJ10Kj_g2UB02J0mN0B5tZlqNCNEto8BTrNvNC7MTX502C8f2jmMQJ6mqF2fka1mqx6gqj0eN0B599M=&og=hw&oi=0x2408823ca615d45439c4b84ea9f34d08&trid=41fee4a83c404181b466435b5671d2eu&uipk=5&mid=0&platform=pc&deadline=1785329211&nbs=1&gen=playurlv3&os=cosbv&upsig=6caf1686d1c1dd0d3245a3e4a9560867&uparams=e,og,oi,trid,uipk,mid,platform,deadline,nbs,gen,os&bvc=vod&nettype=0&bw=69406&lrs=-1&dl=0&f=u_0_0&qn_dyeid=05801ffafaecdc5c0027b0936a69da1b&agrr=1&buvid=9A7E608A-EC92-8A1D-7607-9CE215EE6DC310901infoc&build=0&orderid=1,3",
                ],
                "backup_url": [
                    "https://upos-sz-mirrorcos.bilivideo.com/upgcxcode/31/21/62131/62131_da3-1-100110.m4s?e=ig8euxZM2rNcNbdlhoNvNC8BqJIzNbfqXBvEqxTEto8BTrNvN0GvT90W5JZMkX_YN0MvXg8gNEV4NC8xNEV4N03eN0B5tZlqNxTEto8BTrNvNeZVuJ10Kj_g2UB02J0mN0B5tZlqNCNEto8BTrNvNC7MTX502C8f2jmMQJ6mqF2fka1mqx6gqj0eN0B599M=&trid=41fee4a83c404181b466435b5671d2eu&uipk=5&nbs=1&platform=pc&gen=playurlv3&os=cosbv&oi=0x2408823ca615d45439c4b84ea9f34d08&mid=0&deadline=1785329211&og=hw&upsig=0e7c735dc9bac4861476c99b6bc47cc7&uparams=e,trid,uipk,nbs,platform,gen,os,oi,mid,deadline,og&bvc=vod&nettype=0&bw=69406&lrs=-1&build=0&dl=0&f=u_0_0&qn_dyeid=05801ffafaecdc5c0027b0936a69da1b&agrr=1&buvid=9A7E608A-EC92-8A1D-7607-9CE215EE6DC310901infoc&orderid=0,3",
                    "https://upos-sz-mirrorcos.bilivideo.com/upgcxcode/31/21/62131/62131_da3-1-100110.m4s?e=ig8euxZM2rNcNbdlhoNvNC8BqJIzNbfqXBvEqxTEto8BTrNvN0GvT90W5JZMkX_YN0MvXg8gNEV4NC8xNEV4N03eN0B5tZlqNxTEto8BTrNvNeZVuJ10Kj_g2UB02J0mN0B5tZlqNCNEto8BTrNvNC7MTX502C8f2jmMQJ6mqF2fka1mqx6gqj0eN0B599M=&og=hw&oi=0x2408823ca615d45439c4b84ea9f34d08&trid=41fee4a83c404181b466435b5671d2eu&uipk=5&mid=0&platform=pc&deadline=1785329211&nbs=1&gen=playurlv3&os=cosbv&upsig=6caf1686d1c1dd0d3245a3e4a9560867&uparams=e,og,oi,trid,uipk,mid,platform,deadline,nbs,gen,os&bvc=vod&nettype=0&bw=69406&lrs=-1&dl=0&f=u_0_0&qn_dyeid=05801ffafaecdc5c0027b0936a69da1b&agrr=1&buvid=9A7E608A-EC92-8A1D-7607-9CE215EE6DC310901infoc&build=0&orderid=1,3",
                ],
                "bandwidth": 69367,
                "mimeType": "video/mp4",
                "mime_type": "video/mp4",
                "codecs": "hev1.1.6.L120.90",
                "width": 512,
                "height": 384,
                "frameRate": "15",
                "frame_rate": "15",
                "sar": "1:1",
                "startWithSap": 1,
                "start_with_sap": 1,
                "SegmentBase": {"Initialization": "0-1021", "indexRange": "1022-5985"},
                "segment_base": {
                    "initialization": "0-1021",
                    "index_range": "1022-5985",
                },
                "codecid": 12,
            },
            ...
        ],
        "audio": [
            {
                "id": 30216,
                "baseUrl": "https://xy118x212x136x249xy.mcdn.bilivideo.cn:8082/v1/resource/upgcxcode/31/21/62131/62131_da3-1-30216.m4s?agrr=1&build=0&buvid=9A7E608A-EC92-8A1D-7607-9CE215EE6DC310901infoc&bvc=vod&bw=68667&deadline=1785329211&dl=0&e=ig8euxZM2rNcNbdlhoNvNC8BqJIzNbfqXBvEqxTEto8BTrNvN0GvT90W5JZMkX_YN0MvXg8gNEV4NC8xNEV4N03eN0B5tZlqNxTEto8BTrNvNeZVuJ10Kj_g2UB02J0mN0B5tZlqNCNEto8BTrNvNC7MTX502C8f2jmMQJ6mqF2fka1mqx6gqj0eN0B599M%3D&f=u_0_0&gen=playurlv3&lrs=-1&mid=0&nbs=1&nettype=0&og=hw&oi=0x2408823ca615d45439c4b84ea9f34d08&orderid=0%2C3&os=08cbv&platform=pc&qn_dyeid=05801ffafaecdc5c0027b0936a69da1b&sign=b90abc&traceid=trQSoqSpXhQuHD_0_e_N&uipk=5&uparams=e%2Cnbs%2Cplatform%2Cuipk%2Cmid%2Cgen%2Cos%2Cog%2Cdeadline%2Coi%2Ctrid&upsig=92d981039c13cf9f8b283ca3be6012a4",
                "base_url": "https://xy118x212x136x249xy.mcdn.bilivideo.cn:8082/v1/resource/upgcxcode/31/21/62131/62131_da3-1-30216.m4s?agrr=1&build=0&buvid=9A7E608A-EC92-8A1D-7607-9CE215EE6DC310901infoc&bvc=vod&bw=68667&deadline=1785329211&dl=0&e=ig8euxZM2rNcNbdlhoNvNC8BqJIzNbfqXBvEqxTEto8BTrNvN0GvT90W5JZMkX_YN0MvXg8gNEV4NC8xNEV4N03eN0B5tZlqNxTEto8BTrNvNeZVuJ10Kj_g2UB02J0mN0B5tZlqNCNEto8BTrNvNC7MTX502C8f2jmMQJ6mqF2fka1mqx6gqj0eN0B599M%3D&f=u_0_0&gen=playurlv3&lrs=-1&mid=0&nbs=1&nettype=0&og=hw&oi=0x2408823ca615d45439c4b84ea9f34d08&orderid=0%2C3&os=08cbv&platform=pc&qn_dyeid=05801ffafaecdc5c0027b0936a69da1b&sign=b90abc&traceid=trQSoqSpXhQuHD_0_e_N&uipk=5&uparams=e%2Cnbs%2Cplatform%2Cuipk%2Cmid%2Cgen%2Cos%2Cog%2Cdeadline%2Coi%2Ctrid&upsig=92d981039c13cf9f8b283ca3be6012a4",
                "backupUrl": [
                    "https://upos-sz-mirror08c.bilivideo.com/upgcxcode/31/21/62131/62131_da3-1-30216.m4s?e=ig8euxZM2rNcNbdlhoNvNC8BqJIzNbfqXBvEqxTEto8BTrNvN0GvT90W5JZMkX_YN0MvXg8gNEV4NC8xNEV4N03eN0B5tZlqNxTEto8BTrNvNeZVuJ10Kj_g2UB02J0mN0B5tZlqNCNEto8BTrNvNC7MTX502C8f2jmMQJ6mqF2fka1mqx6gqj0eN0B599M=&nbs=1&platform=pc&uipk=5&mid=0&gen=playurlv3&os=08cbv&og=hw&deadline=1785329211&oi=0x2408823ca615d45439c4b84ea9f34d08&trid=41fee4a83c404181b466435b5671d2eu&upsig=92d981039c13cf9f8b283ca3be6012a4&uparams=e,nbs,platform,uipk,mid,gen,os,og,deadline,oi,trid&bvc=vod&nettype=0&bw=68667&lrs=-1&agrr=1&buvid=9A7E608A-EC92-8A1D-7607-9CE215EE6DC310901infoc&build=0&dl=0&f=u_0_0&qn_dyeid=05801ffafaecdc5c0027b0936a69da1b&orderid=0,3",
                    "https://upos-sz-mirror08c.bilivideo.com/upgcxcode/31/21/62131/62131_da3-1-30216.m4s?e=ig8euxZM2rNcNbdlhoNvNC8BqJIzNbfqXBvEqxTEto8BTrNvN0GvT90W5JZMkX_YN0MvXg8gNEV4NC8xNEV4N03eN0B5tZlqNxTEto8BTrNvNeZVuJ10Kj_g2UB02J0mN0B5tZlqNCNEto8BTrNvNC7MTX502C8f2jmMQJ6mqF2fka1mqx6gqj0eN0B599M=&platform=pc&mid=0&deadline=1785329211&nbs=1&gen=playurlv3&oi=0x2408823ca615d45439c4b84ea9f34d08&trid=41fee4a83c404181b466435b5671d2eu&uipk=5&os=08cbv&og=hw&upsig=14592e6d6e3fb53f2b59838895e827bd&uparams=e,platform,mid,deadline,nbs,gen,oi,trid,uipk,os,og&bvc=vod&nettype=0&bw=68667&lrs=-1&agrr=1&buvid=9A7E608A-EC92-8A1D-7607-9CE215EE6DC310901infoc&build=0&dl=0&f=u_0_0&qn_dyeid=05801ffafaecdc5c0027b0936a69da1b&orderid=1,3",
                ],
                "backup_url": [
                    "https://upos-sz-mirror08c.bilivideo.com/upgcxcode/31/21/62131/62131_da3-1-30216.m4s?e=ig8euxZM2rNcNbdlhoNvNC8BqJIzNbfqXBvEqxTEto8BTrNvN0GvT90W5JZMkX_YN0MvXg8gNEV4NC8xNEV4N03eN0B5tZlqNxTEto8BTrNvNeZVuJ10Kj_g2UB02J0mN0B5tZlqNCNEto8BTrNvNC7MTX502C8f2jmMQJ6mqF2fka1mqx6gqj0eN0B599M=&nbs=1&platform=pc&uipk=5&mid=0&gen=playurlv3&os=08cbv&og=hw&deadline=1785329211&oi=0x2408823ca615d45439c4b84ea9f34d08&trid=41fee4a83c404181b466435b5671d2eu&upsig=92d981039c13cf9f8b283ca3be6012a4&uparams=e,nbs,platform,uipk,mid,gen,os,og,deadline,oi,trid&bvc=vod&nettype=0&bw=68667&lrs=-1&agrr=1&buvid=9A7E608A-EC92-8A1D-7607-9CE215EE6DC310901infoc&build=0&dl=0&f=u_0_0&qn_dyeid=05801ffafaecdc5c0027b0936a69da1b&orderid=0,3",
                    "https://upos-sz-mirror08c.bilivideo.com/upgcxcode/31/21/62131/62131_da3-1-30216.m4s?e=ig8euxZM2rNcNbdlhoNvNC8BqJIzNbfqXBvEqxTEto8BTrNvN0GvT90W5JZMkX_YN0MvXg8gNEV4NC8xNEV4N03eN0B5tZlqNxTEto8BTrNvNeZVuJ10Kj_g2UB02J0mN0B5tZlqNCNEto8BTrNvNC7MTX502C8f2jmMQJ6mqF2fka1mqx6gqj0eN0B599M=&platform=pc&mid=0&deadline=1785329211&nbs=1&gen=playurlv3&oi=0x2408823ca615d45439c4b84ea9f34d08&trid=41fee4a83c404181b466435b5671d2eu&uipk=5&os=08cbv&og=hw&upsig=14592e6d6e3fb53f2b59838895e827bd&uparams=e,platform,mid,deadline,nbs,gen,oi,trid,uipk,os,og&bvc=vod&nettype=0&bw=68667&lrs=-1&agrr=1&buvid=9A7E608A-EC92-8A1D-7607-9CE215EE6DC310901infoc&build=0&dl=0&f=u_0_0&qn_dyeid=05801ffafaecdc5c0027b0936a69da1b&orderid=1,3",
                ],
                "bandwidth": 68646,
                "mimeType": "audio/mp4",
                "mime_type": "audio/mp4",
                "codecs": "mp4a.40.2",
                "width": 0,
                "height": 0,
                "frameRate": "",
                "frame_rate": "",
                "sar": "",
                "startWithSap": 0,
                "start_with_sap": 0,
                "SegmentBase": {"Initialization": "0-932", "indexRange": "933-5908"},
                "segment_base": {"initialization": "0-932", "index_range": "933-5908"},
                "codecid": 0,
            },
            ...
        ],
        "dolby": {"type": 0, "audio": None},
        "flac": None,
    },
    ...
}
```

可以发现，返回结果 `["dash"]["video"]` 和 `["dash"]["audio"]` 两个列表中的字典对象存储了不同的音视频流，对象 `baseUrl` `backup_url` 等键提供了音视频流链接。与此同时，对象 `codecs` 键给出了其格式。深入探究后可以发现，`id` 键的值对应了音视频流的品质。此处 `id = 32` 对应 480P 的视频清晰度，`id = 30216` 对应 64K 的音频清晰度。模块提供 `video.VideoQuality` 和 `video.AudioQuality` 两个枚举类，举个例子，`VideoQuality._480P = 32`，`AudioQuality._64K = 30216`。

针对下载视频，模块同时提供了一个工具类，专门用于处理视频下载地址字典，即 `video.VideoDownloadURLDataDetecter`。其提供 `detect` 和 `detect_best_streams` 方法，这里我们只需要一对清晰度最好的音视频流，使用 `detect_best_streams` 即可。

``` python
from bilibili_api import sync, video


async def main() -> None:
    v = video.Video(aid=2)
    download_url = await v.get_download_url(page_index=0)
    detecter = video.VideoDownloadURLDataDetecter(data=download_url)
    vstream, astream = detecter.detect_best_streams()
    vurl, aurl = vstream.url, astream.url


sync(main())
```

同时，`detect` `detect_best_streams` 函数支持一系列参数，例如 `video_min_quality` 用于限制视频最低清晰度，传入参数为 `video.VideoQuality` 类型，`no_dolby` 可过滤掉杜比视界。`detect_best_streams` 通常情况下返回两个流，一个是视频流，一个是音频流，分别是 `video.VideoStreamDownloadURL` 和 `video.AudioStreamDownloadURL` 实例，通过这些实例我们可以获取有关视频音频流的更多信息，但此处我们只需要 url。

有了 url 就可以下载了。下载的方式不少，从 `curl` 到 `aria2c` 均可。但是，此处的 url 需要加上特定请求头访问，否则会 403。一般只需要加上 `User-Agent` 和 `Referer` 即可正常访问，以下是模块内部使用的请求头：

``` python
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Referer": "https://www.bilibili.com/",
}
```

下载逻辑不光可以在外部程序实现，也可以在原来的 python 代码上追加。这里介绍一种特殊的方式，即调用模块内部使用的会话进行下载。模块并未原生实现网络请求功能，也需要第三方库提供会话，然后调用会话的函数请求。模块使用的会话实例可以通过 `get_session` 函数获取。

``` python
from bilibili_api import get_session, get_selected_client


async def main() -> None:
    ...
    sess = get_session()
    print(get_selected_client(), sess)


sync(main())
```

`get_session` 返回的会话是未经处理的第三方库的会话对象（例如 `curl_cffi.requests.AsyncSession` `aiohttp.ClientSession` `httpx.AsyncClient`），需要看模块此时选择的是哪一个第三方库。这可以通过 `get_selected_client` 查询。模块在允许的条件下，按照 `curl_cffi` `aiohttp` `httpx` 的优先级选择第三方请求库。如果想要指定请求库，可以利用 `select_client` 进行切换。以下是选择 `curl_cffi` 时，上述代码的输出：

``` plaintext
('curl_cffi', <class 'bilibili_api.clients.CurlCFFIClient.CurlCFFIClient'>) <curl_cffi.requests.session.AsyncSession object at 0x120284980>
```

为方便对这些会话实例的调用，模块对不同第三方库的会话进行了统一封装，即使用抽象类 `bilibili_api.BiliAPIClient` 封装需要的网络请求功能。此时调用会话就可以采用统一的一套函数，而不用一一适配兼容了。只需要调用 `get_client` 即可获取 `BiliAPIClient` 实例。借此，我们可以实现以下的简易下载函数。

``` python
import anyio
from bilibili_api import get_bili_headers


async def download(url: str, out: str):
    client = get_client()
    dwn_id = await client.download_create(url=url, headers=get_bili_headers())
    bts = 0
    tot = client.download_content_length(cnt=dwn_id)
    async with await anyio.open_file(out, "wb") as file:
        while True:
            bts += await file.write(await client.download_chunk(cnt=dwn_id))
            print(f"{out} [{bts} / {tot}]", end="\r")
            if bts == tot:
                break
    await client.download_close(cnt=dwn_id)
    print()
```

此处代码使用 `\r` 操作符刷新输出行，打印下载进度。`get_bili_headers` 是模块提供的获取一整套请求头的函数，包括我们需要的 `User-Agent` 和 `Referer`。此处使用了 AnyIO 库进行异步文件 IO，AnyIO 也是模块的依赖之一。

然后就是对 `BiliAPIClient` 函数的具体介绍，虽然这边未使用到，但其最重要的函数是 `request` 函数，用于发起一般网络请求，详情可翻阅文档。此处使用了四个函数，`download_create` 用于创建流式下载的响应，`download_content_length` 用于获取下载文件的长度，`download_chunk` 用于片段下载，`download_close` 用于下载完成后关闭响应。实际上，`BiliAPIClient` 是模块进行网络请求的核心，所有的请求均从这个类中通过，无论是正常的网络请求，还是与服务器连接的 WebSocket，亦或是此处的基本下载功能。

模块已经将以上的下载函数封装为了 `bilibili_api.bili_simple_download`，供日常使用。下面将直接调用此函数。

终于，此处我们使用 `bili_simple_download` 完成了视频下载，接下来到混流了。此处混流直接使用 FFMpeg。这里为防止同步任务堵塞异步事件循环/进程，使用了 `anyio.to_thread.run_sync` 运行 `os.system`，虽然在目前的简单场景下没有这种必要，而且 FFMpeg 没有那么慢，但是，毕竟快速上手不能坏了代码规范。

``` python
import os

import anyio.to_thread
from bilibili_api import bili_simple_download, sync, video


async def main() -> None:
    v = video.Video(aid=2)
    download_url = await v.get_download_url(page_index=0)
    detecter = video.VideoDownloadURLDataDetecter(data=download_url)
    vstream, astream = detecter.detect_best_streams()
    vurl, aurl = vstream.url, astream.url  # type: ignore
    await bili_simple_download(vurl, "video.m4s")
    await bili_simple_download(aurl, "audio.m4s")
    await anyio.to_thread.run_sync(
        os.system,
        "ffmpeg -i video.m4s -i audio.m4s -vcodec copy -acodec copy video.mp4",
    )


sync(main())
```

运行后，在运行目录下即有下载完成视频 `video.mp4`。
