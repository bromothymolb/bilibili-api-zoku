# 示例：分区名与分区 tid 互换

``` python
from bilibili_api import video_zone_v2

print("动画 ->", video_zone_v2.get_zone_info_by_name_v2("动画")[0]["tid"])
print("1005 ->", video_zone_v2.get_zone_info_by_tid_v2(1005)[0]["name"])

# 注：函数返回值为元组，第一项为查询分区的信息，第二项为分区的父分区的信息。
```
