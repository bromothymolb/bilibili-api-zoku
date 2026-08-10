# 使用 `login_v2`

> Credential 类，又称凭据类，用于向模块传入用户的 cookies。
> 为什么需要 cookies? 凡是涉及需要用户参与的操作，都需要 cookies 鉴权，验证用户身份。

以上节选自 `文档/通用/Credential 类`，这也说明了为什么前文提到的“拷贝 cookies”是一种可行的登录方法。但拷贝 cookies 有时候还是会麻烦一些，有没有其他登录的方法了？有，`login_v2` 模块实现了网页端/TV 端哔哩哔哩的登录流程，如果说登录是完成作业，那么拷贝 cookies 是抄作业，而 `login_v2` 是真正可以做作业的模块。

> `login_v2` 之所以称之为 `login_v2`，不同于 `video_zone_v2` 是哔哩哔哩系统的分区升级，其实际上是 bilibili-api 登录模块的更新换代。在 `v17` 之前，模块的登录功能由 `login` `login_func` 模块提供，但两个模块的逻辑全部是同步逻辑，因此最终被移除。若仍想体验旧的 `login` 模块，可以使用 <https://github.com/luyanci/blapi-port>。

登录方式大致分为两种，第一种是扫码登录，第二种是密码/验证码登录。一般推荐使用第一种，因为第一种稳定性更佳，许多第三方哔哩哔哩应用使用的都是扫码登录。第二种放一起的原因是许多情况下密码输对了也照样要来一遍验证码，某种意义上二者还是挺相像的。

## 1. 扫码登录

目前扫码登录支持网页端扫码登录和 TV 端扫码登录，二维码需要用手机上的哔哩哔哩 APP 去扫，整个扫码登录的生命周期由 `login_v2.QrCodeLogin` 实现。首先需要通过 `QrCodeLogin.generate_qrcode` 获取二维码链接，可以通过 `get_qrcode_picture` 获取二维码图片 `Picture` 对象，或 `get_qrcode_terminal` 在终端打印出二维码。接下来是等待二维码被扫描的轮询过程，这和 `session.Session` 类颇想，但此处轮询过程需要用户来实现，`QrCodeLogin` 提供 `check_state` 函数判断当前扫码状态，返回 `login_v2.QrCodeLoginEvents`。当扫码登录成功后，即可通过 `qr.get_credential()` 获取得到的凭据类。

第一步，先实例化 `QrCodeLogin` 并生成二维码，这边先介绍一下 `get_qrcode_terminal` 函数的用法，其返回一个字符串，只需要打印这个字符串，就能在终端看到二维码了：

``` python
from bilibili_api import login_v2, sync

qr = login_v2.QrCodeLogin()
print(sync(qr.get_qrcode_terminal()))
```

这边我们使用 `get_qrcode_picture`，前文已提及过 `Picture` 类的使用方法，此处我们将目标图片保存到本地文件 `qr.png`：

``` python
qr = login_v2.QrCodeLogin()
# 生成二维码，获取 Picture 类对象，并保存图片
pic = await qr.get_qrcode_picture()
await pic.download("qr.png")
```

前文提到扫码登录支持两种，网页端扫码登录和 TV 端扫码登录，默认使用网页端登录，如需要使用 TV 端登录，只需要在实例化 `QrCodeLogin` 时传入以下参数即可：

``` python
qr = login_v2.QrCodeLogin(platform=login_v2.QrCodeLoginChannel.TV)
# 与之相对的默认情况
qr = login_v2.QrCodeLogin(platform=login_v2.QrCodeLoginChannel.WEB)
```

第二部即为轮询，此处详细介绍轮询可能遇到的几种状态：`QrCodeLoginEvents.SCAN`，即仍未扫描二维码的状态，`QrCodeLoginEvents.DONE`，即登录成功后的状态，`QrCodeLoginEvents.CONF`，即正在确认登录的状态，此状态仅限网页端扫码登录，`QrCodeLoginEvents.TIMEOUT`，此时二维码已过期，需要重新生成一遍二维码。此处设置每 1 秒进行一次查询状态，在轮询的频率上，二维码接口相较于消息接口宽松得多，但仍然需要提醒，不要跑得太快。

``` python
while True:
    state = await qr.check_state()
    # 检查状态
    match state:
        case login_v2.QrCodeLoginEvents.SCAN:
            print("【状态】未扫描二维码", end="\r")
        case login_v2.QrCodeLoginEvents.CONF:
            print("【状态】正在确认登录", end="\r")
        case login_v2.QrCodeLoginEvents.DONE:
            print("【状态】已完成登录：")
            break
        case login_v2.QrCodeLoginEvents.TIMEOUT:
            print("【状态】二维码已过期")
            exit(1)  # 偷个小懒
    await anyio.sleep(1)
```

---

第三步自然是获取凭据类了，使用 `get_credential` 方法即可。获得 `Credential` 后，如需导出 cookies，可以调用 `get_core_cookies` 方法，这将返回所有只有依靠登录过程才能获取的 cookies，包含 `SESSDATA` `bili_jct` `DedeUserID` `DedeUserID__ckMd5` `sid`，同时还有一个重要的辅助数值（虽然其并不属于 cookies），即 `ac_time_value`。这些 cookies 的相关信息可以在 `文档/通用/Credential 类` 中找到。

此处有必要介绍 `get_core_cookies` 函数和 `get_cookies` 函数的区别。区别是前者为同步函数，后者为异步函数。为什么后者为异步函数？因为后者返回值提供了 `buvid3` `buvid4` `bili_ticket` 等风控 cookies，它们无需登录也能获取，`buvid3` `buvid4` 若未在凭据类中提供，模块将自动生成并激活一对新的 `buvid3` 和 `buvid4`。可以看出，在登录过程中，真正有需要的、价值的 cookies，只有 `get_core_cookies` 返回值中的 cookies；然而在实际请求中，仍需要补充其他 cookies，此时就需要 `get_cookies` 函数提供一份完整的 cookies。

`get_core_cookies` 返回值可以保存在 `json` 文件中，随后每次需要使用凭据类时，可以先用 `json.load` 加载，再使用 `Credential.from_cookies` 通过 cookies 字段初始化凭据类。如下所示：

``` python
credential = Credential.from_cookies(json.load(open("cookie.json")))
```

cookies 可能过期，需要刷新，这可以通过 `Credential.check_refresh` 函数确认，刷新过程可以通过 `Credential.refresh` 完成，如下所示：

``` python
if await credential.check_refresh():
    print("正在刷新")
    await credential.refresh()
    print(json.dumps(credential.get_core_cookies()))
else:
    print("无需刷新")
```

自此，即可完成一份本地 cookies 的获取、保存和维护。这份 cookies 的生命周期与浏览器中的 cookies 完全隔离，二者不会互相干扰。

## 2. 密码/验证码登录

接下来是密码/验证码登录，相信日常生活中大部分人都倾向使用这种方式。先问一个问题，在日常登录过程中，什么令你最为印象深刻？

<img src="../img/geetest.png" width="300" height="400">

哔哩哔哩也存在人机测试验证码，也是极验的验证码。事先声明，这验证码是不得不完成的，虽然模块没有自动完成验证码的能力，但验证码的人机测试仍然可以被完成。

模块提供 `bilibili_api.Geetest` 类，可以通过 `Geetest.generate_test` 函数生成一个极验验证码，然后使用 `get_info` 获取极验验证码相关信息。其返回的 `GeetestMeta` 类包含两个关键字段：`gt` `challenge`，因为只要有了 `gt` 和 `challenge` 就可以在网页端实例化极验测试了。现在可以打开 <https://kuresaru.github.io/geetest-validator/>，输入 `gt` `challenge`，就可以生成验证码并完成（显然是手动完成）。完成验证码后会得到两个字符串，`validate` 和 `seccode`，或者说，只要获得这两个字符串，极验验证就算完成了。可以通过 `Geetest.complete_test` 传入完成验证码后获得的 `validate` 和 `seccode`。

``` python
gee = Geetest()
await gee.generate_test()
info = gee.get_info()
print("gt:", info.gt, "challenge:", info.challenge)
...
gee.complete_test("validate", "seccode")
```

为方便验证码作答，模块内嵌了 <https://kuresaru.github.io/geetest-validator/>，并允许通过 `http.server.HTTPServer` 开启本地验证码服务。具体用法是，先通过 `start_geetest_server` 开启服务器，然后使用 `get_geetest_server_url` 获取链接，接下来使用 `wait_for_done` 函数等待验证码完成，最后使用 `close_geetest_server` 关闭服务器。代码如下：

``` python
gee = Geetest()
await gee.generate_test()
gee.start_geetest_server()
print("url:", gee.get_geetest_server_url())
# url: http://127.0.0.1:49180/
await gee.wait_for_done()
gee.close_geetest_server()
print(gee.get_result())
# GeetestMeta(gt='ac597a4506fee079629df5d8b66dd4fe',
#             challenge='f9be10572180bdca190c915bdf476a12',
#             token='82a7bef08cc64506b54ca03aa9a9c09e',
#             seccode='bfac3ae1d10a9b811c5cf109a94560d6|jordan',
#             validate='bfac3ae1d10a9b811c5cf109a94560d6')
```

完成极验后，`Geetest` 类即可作为参数，传入密码/验证码登录函数。两个函数分别是 `login_with_password` 和 `send_sms` (发送验证码)。

``` python
# 密码登录
cred = await login_v2.login_with_password(
    username=username, password=password, geetest=gee
)
# 验证码登录
## 1. 初始化 PhoneNumber
phone = login_v2.PhoneNumber("XXXXXXXXXXX", "+86")
## 2. 发送验证码，获得对应的 captcha_id
captcha_id = await login_v2.send_sms(phonenumber=phone, geetest=gee)
## 3. 完成登录
cred = await login_v2.login_with_sms(
    phonenumber=phone, code=code, captcha_id=captcha_id
)
```

上面两个函数成功后直接返回 `Credential` 类。但有时登录会遇到安全验证，此时上面两个函数的返回值不再是 `Credential`，而是 `login_v2.LoginCheck`。登录验证又需要极验验证码，但有一点需要注意，此处的验证码类型，和前面生成的类型不一致，换句话说前面生成的 `Geetest` 类在此处不能使用。因此，调用 `generate_test` 的时候，需要加上参数 `type_=GeetestType.VERIFY`。

``` python
await gee.generate_test(type_=GeetestType.VERIFY)
# 登录时为 GeetestType.LOGIN，为默认值。
await gee.generate_test(type_=GeetestType.LOGIN)
```

然后即可完成登录验证，最终仍然可以拿到 `Credential` 类。

``` python
await check.send_sms(gee)
cred = await check.complete_check(code)
```

最后只需要对 `Credential` 进行后续处理即可。前面扫码登录处已经展开过讨论。

在模块 API 示例的 `login_v2` 部分，文档提供了一段终端登录脚本(密码/验证码)，如下：

``` python
from bilibili_api import Geetest, GeetestType, login_v2, sync


async def main() -> None:
    choice = input("pwd / sms:")

    gee = Geetest()  # 实例化极验测试类
    await gee.generate_test()  # 生成测试
    gee.start_geetest_server()  # 在本地部署网页端测试服务
    print(gee.get_geetest_server_url())  # 获取本地服务链接
    await gee.wait_for_done()  # 等待测试完成
    gee.close_geetest_server()  # 关闭部署的网页端测试服务
    print("result:", gee.get_result())

    # 1. 密码登录
    if choice == "pwd":
        username = input("username:")  # 手机号/邮箱
        password = input("password:")  # 密码
        cred = await login_v2.login_with_password(
            username=username,
            password=password,
            geetest=gee,  # 调用接口登录
        )
    # 2. 验证码登录
    elif choice == "sms":
        phone = login_v2.PhoneNumber(input("phone:"), "+86")  # 实例化手机号类
        captcha_id = await login_v2.send_sms(
            phonenumber=phone, geetest=gee
        )  # 发送验证码
        print("captcha_id:", captcha_id)  # 顺便获得对应的 captcha_id
        code = input("code: ")
        cred = await login_v2.login_with_sms(
            phonenumber=phone,
            code=code,
            captcha_id=captcha_id,  # 调用接口登录
        )
    else:
        exit(1)

    # 安全验证
    if isinstance(cred, login_v2.LoginCheck):
        # 如法炮制 Geetest
        gee = Geetest()  # 实例化极验测试类
        await gee.generate_test(
            type_=GeetestType.VERIFY
        )  # 生成测试 (注意 type_ 为 GeetestType.VERIFY)
        gee.start_geetest_server()  # 在本地部署网页端测试服务
        print(gee.get_geetest_server_url())  # 获取本地服务链接
        await gee.wait_for_done()  # 等待测试完成
        gee.close_geetest_server()  # 关闭部署的网页端测试服务
        print("result:", gee.get_result())
        await cred.send_sms(gee)  # 发送验证码
        code = input("code:")
        cred = await cred.complete_check(code)  # 调用接口登录

    print("cookies:", cred.get_core_cookies())  # 获得 cookies


if __name__ == "__main__":
    sync(main())
```
