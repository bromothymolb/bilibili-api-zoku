# FA♂Q

此处收集了部分常见问题，内容相较于 README 中会更加丰富、更加全面。

## Q: 关于 API 调用的正确姿势是什么？

A: 所有 API 调用，请尽量使用 **指名方式** 传参，
因为 API 较多，可能不同函数的传参顺序不一样，例子：

```python
# 推荐
video.get_info(bvid="BV1uv411q7Mv")

# 当然也可以这样
kwargs = {
    "bvid": "BV1uv411q7Mv"
}
video.get_info(**kwargs)

# 不推荐
video.get_info("BV1uv411q7Mv")
```

## Q: 为什么会提示 412 Precondition Failed ？

A: 你的请求速度太快了。造成请求速度过快的原因可能是你写了高并发的代码。

这种情况下，你的 IP 会暂时被封禁而无法使用，你可以设置代理绕过。

```python
from bilibili_api import request_settings

request_settings.set_proxy("http://your-proxy.com") # 里头填写你的代理地址

request_settings.set_proxy("http://username:password@your-proxy.com") # 如果需要用户名、密码
```
