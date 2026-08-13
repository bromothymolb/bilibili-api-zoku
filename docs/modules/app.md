# Module app.py


bilibili_api.app

手机 APP 相关


``` python
from bilibili_api import app
```

- [async def get\_loading\_images()](#async-def-get\_loading\_images)
- [async def get\_loading\_images\_special()](#async-def-get\_loading\_images\_special)

---

## async def get_loading_images()

获取开屏启动画面


| name | type | description |
| - | - | - |
| `mobi_app` | `str, optional` | android / iphone / ipad. Defaults to 'android'. |
| `platform` | `str, optional` | android / ios/ ios. Defaults to 'android'. |
| `height` | `int, optional` | 屏幕高度. Defaults to 1920. |
| `width` | `int, optional` | 屏幕宽度. Defaults to 1080. |
| `build` | `int, optional` | 客户端内部版本号. Defaults to 999999999. |
| `birth` | `str, optional` | 生日日期(四位数，例 0101). Defaults to ''. |
| `credential` | `Credential \| None, optional` | 凭据. Defaults to None. |

**Returns:** `dict`:  调用 API 返回的结果




---

## async def get_loading_images_special()

获取特殊开屏启动画面


| name | type | description |
| - | - | - |
| `mobi_app` | `str, optional` | android / iphone / ipad. Defaults to 'android'. |
| `platform` | `str, optional` | android / ios/ ios. Defaults to 'android'. |
| `height` | `int, optional` | 屏幕高度. Defaults to 1920. |
| `width` | `int, optional` | 屏幕宽度. Defaults to 1080. |
| `credential` | `Credential \| None, optional` | 凭据. Defaults to None. |

**Returns:** `dict`:  调用 API 返回的结果




