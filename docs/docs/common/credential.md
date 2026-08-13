# Credential 类

Credential 类，又称凭据类，用于向模块传入用户的 cookies。

为什么需要 cookies? 凡是涉及需要用户参与的操作，都需要 cookies 鉴权，验证用户身份。

## 获取 Credential 类所需信息

Credential 类实例化代码如下：

```python
from bilibili_api import Credential

credential = Credential(sessdata="你的 SESSDATA", bili_jct="你的 bili_jct", buvid3="你的 buvid3", dedeuserid="你的 DedeUserID", ac_time_value="你的 ac_time_value")
```

`sessdata` `bili_jct` `buvid3` 和 `dedeuserid` 这四个参数的值均在浏览器的 Cookies 里头，下面说明获取方法。

### 火狐浏览器（Firefox）

1. 按 **F12** 打开开发者工具。

![](https://pic.imgdb.cn/item/6038d30b5f4313ce2533b6d1.jpg)

2. 在工具窗口上方找到 **存储** 选项卡。

![](https://pic.imgdb.cn/item/6038d31d5f4313ce2533c1bd.jpg)

3. 展开左边的 **Cookie** 列表，选中任一b站域名。在右侧找到对应三项即可。

![](https://pic.imgdb.cn/item/6038d3df5f4313ce25344c6a.jpg)

### 谷歌浏览器（Chrome）

1. 按 **F12** 打开开发者工具。

![](https://pic.imgdb.cn/item/6038d4065f4313ce25346335.jpg)

2. 在工具窗口上方找到 **Application** 选项卡。

![](https://pic.imgdb.cn/item/6038d4425f4313ce253484e4.jpg)

3. 在左侧找到 **Storage/Cookies**，并选中任一b站域名，在右侧找到对应三项即可。

![](https://pic.imgdb.cn/item/6038d4ce5f4313ce2534ecb3.jpg)

### 微软 Edge

1. 按 **F12** 打开开发者工具。

![](https://pic.imgdb.cn/item/6038d5125f4313ce25353318.jpg)

2. 在工具窗口上方找到 **应用程序** 选项卡 。

![](https://pic.imgdb.cn/item/6038d5395f4313ce25354c15.jpg)

3. 在左侧找到 **存储/Cookies**，并选中任一b站域名，在右侧找到对应三项即可。

![](https://pic.imgdb.cn/item/6038d5755f4313ce253571bb.jpg)

---

`ac_time_value` 相对特殊，仅用于刷新 Cookies，可以选择不获取，在 localStorage 中的 ac_time_value 字段。

只需要打开 B 站，打开开发者工具，进入控制台，输入`window.localStorage.ac_time_value`即可获取值。

## Cookies 值简介

常见的凭据 (`Credential`) 信息有 Cookie 值

+ `SESSDATA`
+ `bili_jct`
+ `buvid3` / `buvid4`
+ `dedeuserid`

以及 Local Storage 中的

+ `ac_time_value`

下列一一介绍

### `SESSDATA`

`SESSDATA` 用于一般在获取对应用户信息时提供，通常是 `GET` 操作下提供，此类操作一般不会进行操作，仅读取信息

如获取个人简介、获取个人空间信息等情况下需要提供

### `bili_jct`

`bili_jct` 用于进行操作用户数据时提供，通常是 `POST` 操作下提供，此类操作会修改用户数据

如发送评论、点赞三连、上传视频等等情况下需要提供

### `buvid3` / `buvid4`

`buvid3` / `buvid4` 是 [设备验证码](https://github.com/SocialSisterYi/bilibili-API-collect/blob/master/docs/misc/device_identity.md#%E8%AE%BE%E5%A4%87%E5%94%AF%E4%B8%80%E6%A0%87%E8%AF%86-buvid)
  
通常不需要提供，但如放映室内部分接口需要提供，同时与风控有关

### `dedeuserid`

`dedeuserid` 通常为用户 `UID` ，几乎不需要提供

### `ac_time_value`

`ac_time_value` 在登录时获取，登录状态过期后用于刷新 `Cookies`，没有此值则只能重新登录，如不需要凭据刷新则不需要提供

## Cookies 默认携带项一览

接下来给出模块提供的 cookies 项.

重要 cookies: 需要登录获取的 cookies
 - `SESSDATA` (`sessdata`);
 - `bili_jct`;
 - `DedeUserId` (`dedeuserid`);
 - `DedeUserId__ckMd5` (`dedeuserid_ckmd5`);
 - `sid`

本地生成 cookies: 这些 cookies 可以本地生成。以下 cookies 皆会在模块自动生成 buvid 时生成。若用户自行提供 buvid，则会在 \_\_init\_\_ 中生成。
 - `b_nut`;
 - `b_lsid`;
 - `uuid_infoc`;

网络请求生成反爬 cookies: 这些 cookies 有时会作用在风控上，获取需要进行额外的网络请求。
 - `buvid3`;
 - `buvid4`;
 - `buvid_fp`
 - `bili_ticket`;
 - `bili_ticket_expires`

非 cookies:
 - `ac_time_value` (存储在 Local Storage 中) 上文已介绍。

模块提供两个函数获取 cookies：`async get_cookies()` 和 `get_core_cookies()`，前者将上面的所有 cookies 返回，有的 cookies 需要网络请求获取，具体执行便在此函数中，后者会返回上文中的重要 cookies。

```python
import asyncio
import json
from pprint import pprint

from bilibili_api import Credential

credential = Credential.from_cookies(json.load(open("test-cookies.json")))


async def main() -> None:
    pprint(credential.get_core_cookies())
    pprint(await credential.get_cookies())


asyncio.run(main())


# get_core_cookies()
{'DedeUserID': '1145141919810',
 'DedeUserID__ckMd5': '32150285b345c48a',
 'SESSDATA': 'a29rb3JvcHlvbnB5b25tYWNoaWthbmdhZXJ1ZnVyaXNoaXRlbW91Y2hvdHRvY2hpa2F6dWljaGFla2FudGFubmloYW9zaGllbmFpdGtvbm5hbmlzdWtpbmFrb3RvaGFuYWlzaG9uYW5v',
 'ac_time_value': '49dc33bd5a62a991b8d48bf0a8167112',
 'bili_jct': 'a3VydW50dG9oaXR0b21hd2FyaWhvcmFk',
 'sid': 'erw42k1j'}

# async get_cookies()
{'DedeUserID': '1145141919810',
 'DedeUserID__ckMd5': '32150285b345c48a',
 'SESSDATA': 'a29rb3JvcHlvbnB5b25tYWNoaWthbmdhZXJ1ZnVyaXNoaXRlbW91Y2hvdHRvY2hpa2F6dWljaGFla2FudGFubmloYW9zaGllbmFpdGtvbm5hbmlzdWtpbmFrb3RvaGFuYWlzaG9uYW5v',
 '_uuid': '7879DE85-B556-5D88-2B25-CA4D1EDC77AB33820infoc',
 'b_lsid': '5AFE72CB_19BAADA79B6',
 'b_nut': '1768098003',
 'bili_jct': 'a3VydW50dG9oaXR0b21hd2FyaWhvcmFk',
 'browser_resolution': '1280-665',
 'buvid3': '21BB29C4-C8A7-79D0-11CD-71E376A1EC6C03504infoc',
 'buvid4': 'D2B1F405-4EE4-0CA3-30FF-AF38819C71EG03504-026011110-eb91jZuEOVIK9u/OPbfNwtFZ32X61tMSImd/8BHC0uBcJNoPwtdRzIdseJBojUDk',
 'buvid_fp': '312374270cb1e796633eadf1035af7e5',
 'opus-goback': '1',
 'sid': 'erw42k1j'}
```

## 我还有其他 cookies

可以在初始化 Credential 时通过 `kwargs` 传入。例如：`Credential(sessdata="", ..., zhanzhang="bishi")`。

## 刷新 Credential

Credential 中携带的 cookies 需定期刷新保证可用。

通过 `credential.refresh()` 方法刷新 Credential。

必须要有 `ac_time_value` 字段，否则无法刷新。

```python
from bilibili_api import Credential, sync

# 生成一个 Credential 对象
credential = Credential(sessdata="xxx", bili_jct="xxx", ac_time_value="xxx")

# 检查 Credential 是否需要刷新
print(sync(credential.check_refresh()))

# 刷新 Credential
sync(credential.refresh())
```

不需要过于频繁地刷新。

如果需要长期使用此凭据则不应该在浏览器登录账户导致 Cookies 被刷新。
