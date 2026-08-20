"""
bilibili_api.utils.anti_spider

反爬虫相关算法和工具函数
"""

import base64
import binascii
from functools import reduce
import hashlib
import hmac
import io
import json
from json import scanner
from json.decoder import scanstring  # type: ignore
import os
import random
import re
import struct
import time
from typing import Any
import urllib.parse

from bs4 import BeautifulSoup
import chompjs
from Cryptodome.Cipher import PKCS1_OAEP
from Cryptodome.Hash import SHA256
from Cryptodome.PublicKey import RSA

from .settings import bili_settings

##### 浏览器指纹 & 请求头 #####


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Referer": "https://www.bilibili.com/",
}
browser_fingerprint = None


def get_browser_fingerprint() -> dict:
    global browser_fingerprint
    if browser_fingerprint is None:
        if bili_settings.get_enable_fpgen():
            import fpgen

            browser_fingerprint = fpgen.generate(**bili_settings.get_fpgen_args())
        else:
            with open(
                os.path.abspath(
                    os.path.join(
                        os.path.dirname(__file__),
                        "..",
                        "data",
                        "browser_fingerprint.json",
                    )
                ),
                encoding="utf-8",
            ) as f:
                browser_fingerprint = json.load(f)
    return browser_fingerprint


def get_bili_headers() -> dict:
    """
    获取可供访问 bilibili 链接的伪装请求头。

    部分请求头取自 fpgen 生成的浏览器指纹信息。

    Returns:
        dict: 请求头
    """
    fp = get_browser_fingerprint()
    headers = HEADERS.copy()
    for k, v in fp["headers"].items():
        if v:
            headers[k.title()] = v[0] if v and isinstance(v, list) else str(v)
    return headers


##### Credential 相关 #####


def _get_time() -> int:
    return int(time.time())


def _get_time_milli() -> int:
    return int(time.time() * 1000)


def _gen_b_lsid() -> str:
    return f"{random.randbytes(4).hex().upper()}_{hex(_get_time_milli())[2:].upper()}"


def _gen_uuid_infoc() -> str:
    def gen_part(x: int) -> str:
        return "".join([random.choice(mp) for _ in range(x)])

    t = _get_time_milli() % 100000
    mp = [*list("123456789ABCDEF"), "10"]
    pck = [8, 4, 4, 4, 12]

    return (
        "-".join([gen_part(length) for length in pck]) + str(t).ljust(5, "0") + "infoc"
    )


"""
Cookies 刷新相关

感谢 bilibili-API-collect 提供的刷新 Cookies 的思路

https://socialsisteryi.github.io/bilibili-API-collect/docs/login/cookie_refresh.html
"""


def _getCorrespondPath() -> str:
    key = RSA.importKey(
        """\
-----BEGIN PUBLIC KEY-----
MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDLgd2OAkcGVtoE3ThUREbio0Eg
Uc/prcajMKXvkCKFCWhJYJcLkcM2DKKcSeFpD/j6Boy538YXnR6VhcuUJOhH2x71
nzPjfdTcqMz7djHum0qSZA0AyCBDABUqCrfNgCiJ00Ra7GmRj+YCK1NJEuewlb40
JNrRuoEUXpabUzGB8QIDAQAB
-----END PUBLIC KEY-----"""
    )
    ts = _get_time_milli()
    cipher = PKCS1_OAEP.new(key, SHA256)
    encrypted = cipher.encrypt(f"refresh_{ts}".encode())
    return binascii.b2a_hex(encrypted).decode()


##### buvid #####

"""
思路来源：https://github.com/SocialSisterYi/bilibili-API-collect/issues/933
"""


class _CookieJsonDecoder(json.JSONDecoder):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parse_string = self.cookie_scanstring
        self.scan_once = scanner.py_make_scanner(self)  # pyright: ignore[reportAttributeAccessIssue]

    @staticmethod
    def cookie_scanstring(*args, **kwargs):
        (val, end) = scanstring(*args, **kwargs)

        if val.startswith("getCookie"):
            match = re.match(r"getCookie\('([^']*)'\)", val)
            if match:
                _cookie_name = match.group(1)
                return (None, end)

        return (val, end)


MOD = 1 << 64


def _buvid_rotate_left(x: int, k: int) -> int:
    bin_str = bin(x)[2:].rjust(64, "0")
    return int(bin_str[k:] + bin_str[:k], base=2)


def _buvid_fmix64(k: int) -> int:
    C1 = 0xFF51_AFD7_ED55_8CCD
    C2 = 0xC4CE_B9FE_1A85_EC53
    R = 33
    tmp = k
    tmp ^= tmp >> R
    tmp = tmp * C1 % MOD
    tmp ^= tmp >> R
    tmp = tmp * C2 % MOD
    tmp ^= tmp >> R
    return tmp


def _buvid_murmur3_x64_128(source: io.BufferedIOBase, seed: int) -> int:
    C1 = 0x87C3_7B91_1142_53D5
    C2 = 0x4CF5_AD43_2745_937F
    C3 = 0x52DC_E729
    C4 = 0x3849_5AB5
    R1, R2, R3, M = 27, 31, 33, 5
    h1, h2 = seed, seed
    processed = 0
    while True:
        read = source.read(16)
        processed += len(read)
        if len(read) == 16:
            k1 = struct.unpack("<q", read[:8])[0]
            k2 = struct.unpack("<q", read[8:])[0]
            h1 ^= _buvid_rotate_left(k1 * C1 % MOD, R2) * C2 % MOD
            h1 = ((_buvid_rotate_left(h1, R1) + h2) * M + C3) % MOD
            h2 ^= _buvid_rotate_left(k2 * C2 % MOD, R3) * C1 % MOD
            h2 = ((_buvid_rotate_left(h2, R2) + h1) * M + C4) % MOD
        elif len(read) == 0:
            h1 ^= processed
            h2 ^= processed
            h1 = (h1 + h2) % MOD
            h2 = (h2 + h1) % MOD
            h1 = _buvid_fmix64(h1)
            h2 = _buvid_fmix64(h2)
            h1 = (h1 + h2) % MOD
            h2 = (h2 + h1) % MOD
            return (h2 << 64) | h1
        else:
            k1 = 0
            k2 = 0
            if len(read) >= 15:
                k2 ^= int(read[14]) << 48
            if len(read) >= 14:
                k2 ^= int(read[13]) << 40
            if len(read) >= 13:
                k2 ^= int(read[12]) << 32
            if len(read) >= 12:
                k2 ^= int(read[11]) << 24
            if len(read) >= 11:
                k2 ^= int(read[10]) << 16
            if len(read) >= 10:
                k2 ^= int(read[9]) << 8
            if len(read) >= 9:
                k2 ^= int(read[8])
                k2 = _buvid_rotate_left(k2 * C2 % MOD, R3) * C1 % MOD
                h2 ^= k2
            if len(read) >= 8:
                k1 ^= int(read[7]) << 56
            if len(read) >= 7:
                k1 ^= int(read[6]) << 48
            if len(read) >= 6:
                k1 ^= int(read[5]) << 40
            if len(read) >= 5:
                k1 ^= int(read[4]) << 32
            if len(read) >= 4:
                k1 ^= int(read[3]) << 24
            if len(read) >= 3:
                k1 ^= int(read[2]) << 16
            if len(read) >= 2:
                k1 ^= int(read[1]) << 8
            if len(read) >= 1:
                k1 ^= int(read[0])
            k1 = _buvid_rotate_left(k1 * C1 % MOD, R2) * C2 % MOD
            h1 ^= k1


def _gen_buvid_fp(key: str, seed: int):
    source = io.BytesIO(bytes(key, "utf-8"))
    m = _buvid_murmur3_x64_128(source, seed)
    return f"{hex(m & (MOD - 1))[2:]}{hex(m >> 64)[2:]}"


def _gen_buvid_payload(uuid: str, homepage_html: str) -> str:
    def extract_abtest_dict(html: str) -> dict[str, Any]:
        soup = BeautifulSoup(html, "html.parser")
        scripts = soup.find_all("script")

        for script in scripts:
            js_code = script.string
            if not js_code or "window.abtest" not in js_code:
                continue

            # Isolate the JavaScript object string using a regular expression.
            # This looks for 'window.abtest = {' and captures everything until the matching '};'
            match = re.search(r"window\.abtest\s*=\s*({.*?})\n", js_code, re.DOTALL)
            if not match:
                continue

            js_object_string = match.group(1)

            try:
                return chompjs.parse_js_object(
                    js_object_string, loader_kwargs={"cls": _CookieJsonDecoder}
                )
            except Exception as e:
                print(f"Error parsing JavaScript object: {e}")
                return {}

        return {}

    browser_fingerprint = get_browser_fingerprint()
    plugins = browser_fingerprint["plugins"]
    mime_type_suffix: dict[str, str] | None = (
        {
            mime_type["type"]: mime_type["suffixes"]
            for mime_type in browser_fingerprint["plugins"]["mimeTypes"]
        }
        if plugins
        else None
    )

    def get_param(param_id: int) -> str | int | bool:
        param = browser_fingerprint["webgl"]["params"].get(str(param_id))
        return param["value"] if param["value"] is not None else "null"

    a3c1 = [
        f"extensions:{';'.join(browser_fingerprint['webgl']['supportedExtensions'])}",
        f"webgl aliased line width range:{(get_param(33902))}",
        f"webgl aliased point size range:{get_param(33901)}",
        f"webgl alpha bits:{get_param(3413)}",
        f"webgl antialiasing:{'yes' if browser_fingerprint['webgl']['contextAttributes']['antialias'] else 'no'}",
        f"webgl blue bits:{get_param(3412)}",
        f"webgl depth bits:{get_param(3414)}",
        f"webgl green bits:{get_param(3411)}",
        f"webgl max anisotropy:{get_param(34047)}",
        f"webgl max combined texture image units:{get_param(35661)}",
        f"webgl max cube map texture size:{get_param(34076)}",
        f"webgl max fragment uniform vectors:{get_param(36349)}",
        f"webgl max render buffer size:{get_param(34024)}",
        f"webgl max texture image units:{get_param(34930)}",
        f"webgl max texture size:{get_param(3379)}",
        f"webgl max varying vectors:{get_param(36348)}",
        f"webgl max vertex attribs:{get_param(34921)}",
        f"webgl max vertex texture image units:{get_param(35660)}",
        f"webgl max vertex uniform vectors:{get_param(36347)}",
        f"webgl max viewport dims:{get_param(3386)}",
        f"webgl red bits:{get_param(3410)}",
        f"webgl renderer:{get_param(7937)}",
        f"webgl shading language version:{get_param(35724)}",
        f"webgl stencil bits:{get_param(3415)}",
        f"webgl vendor:{get_param(7936)}",
        f"webgl version:{get_param(7938)}",
    ]

    if (
        "WEBGL_debug_renderer_info"
        in browser_fingerprint["webgl"]["supportedExtensions"]
    ):
        a3c1.append(f"webgl unmasked vendor:{browser_fingerprint['gpu']['vendor']}")
        a3c1.append(f"webgl unmasked renderer:{browser_fingerprint['gpu']['renderer']}")

    shader_precisions = browser_fingerprint["webgl"]["shaderPrecisionFormats"]
    numerics = ["FLOAT", "INT"]
    shader_map = {"VERTEX": 35633, "FRAGMENT": 35632}
    precisions = ["HIGH", "MEDIUM", "LOW"]
    precision_map = {
        "HIGH_FLOAT": 36338,
        "MEDIUM_FLOAT": 36337,
        "LOW_FLOAT": 36336,
        "HIGH_INT": 36341,
        "MEDIUM_INT": 36340,
        "LOW_INT": 36339,
    }

    for ntype_k in numerics:
        for stype_k, stype_v in shader_map.items():
            for ptype_k in precisions:
                precision_type = f"{ptype_k}_{ntype_k}"
                precision_data = next(
                    format
                    for format in shader_precisions
                    if format["precisionType"] == precision_map[precision_type]
                    and format["shaderType"] == stype_v
                )
                for prop in ["precision", "rangeMin", "rangeMax"]:
                    value = precision_data["r"][prop]
                    prop_name = prop
                    if prop != "precision":
                        prop_name = f"precision {prop}"
                    a3c1.append(
                        f"webgl {stype_k.lower()} shader {ptype_k.lower()} {ntype_k.lower()} {prop_name}:{value}"
                    )

    png_suffix = bytes.fromhex("0000000049454E44AE426082")

    content = {
        "3064": 1,
        "5062": str(_get_time_milli()),
        "03bf": "https%3A%2F%2Fwww.bilibili.com%2F",
        "39c8": "333.1007.fp.risk",
        "34f1": "",
        "d402": "",
        "654a": "",
        "6e7c": f"{browser_fingerprint['window']['innerWidth']}x{browser_fingerprint['window']['innerHeight']}",
        "3c43": {
            "2673": 0,
            "5766": browser_fingerprint["screen"]["colorDepth"],
            "6527": 0,
            "7003": 1,
            "807e": 1,
            "b8ce": browser_fingerprint["navigator"]["userAgent"],
            "641c": 0,
            "07a4": browser_fingerprint["intl"]["locale"],
            "1c57": browser_fingerprint["navigator"]["deviceMemory"],
            "0bd0": browser_fingerprint["navigator"]["hardwareConcurrency"],
            "748e": [
                browser_fingerprint["screen"]["width"],
                browser_fingerprint["screen"]["height"],
            ],
            "d61f": [
                browser_fingerprint["screen"]["width"],
                browser_fingerprint["screen"]["height"],
            ],
            "fc9d": -480,
            "6aa9": "Asia/Shanghai",
            "75b8": 1,
            "3b21": 1,
            "8a1c": 0,
            "d52f": "not available",
            "adca": browser_fingerprint["navigator"]["platform"],
            "80c9": (
                [
                    [
                        plugin["name"],
                        plugin["description"],
                        [
                            [mime_type, mime_type_suffix.get(mime_type, "")]
                            for mime_type in plugin["__mimeTypes"]
                        ],
                    ]
                    for plugin in plugins["plugins"]
                ]
                if mime_type_suffix
                else "not available"
            ),
            "13ab": base64.b64encode(
                random.randbytes(random.randrange(15, 20)) + png_suffix
            ).decode(encoding="ascii")[:-20],
            "bfe9": base64.b64encode(
                random.randbytes(random.randrange(40, 50)) + png_suffix
            ).decode(encoding="ascii")[:-50],
            "a3c1": a3c1,
            "6bc5": f"{browser_fingerprint['gpu']['vendor']}~{browser_fingerprint['gpu']['renderer']}",
            "ed31": 0,
            "72bd": 0,
            "097b": 0,
            "52cd": [0, 0, 0],
            "a658": browser_fingerprint["allFonts"],
            "d02f": str(124.043475 + random.random() / 1e6),
        },
        "54ef": json.dumps(
            extract_abtest_dict(homepage_html),
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
        ),
        "8b94": "https%3A%2F%2Fwww.bilibili.com%2F",
        "df35": uuid,
        "07a4": browser_fingerprint["intl"]["locale"],
        "5f45": None,
        "db46": 0,
    }
    return json.dumps(
        {"payload": json.dumps(content, ensure_ascii=False, separators=(",", ":"))},
        ensure_ascii=False,
        separators=(",", ":"),
    )


##### bili_ticket #####

"""
https://github.com/SocialSisterYi/bilibili-API-collect/issues/903
"""


def _gen_bili_ticket_params() -> dict[str, str]:
    def hmac_sha256(key: str, message: str) -> str:
        hmac_obj = hmac.new(
            key.encode("utf-8"), message.encode("utf-8"), hashlib.sha256
        )
        return hmac_obj.digest().hex()

    ts = int(_get_time())
    o = hmac_sha256("XgwSnGZ1p", f"ts{ts}")
    params = {
        "key_id": "ec02",
        "hexsign": o,
        "context[ts]": f"{ts}",
    }
    return params


##### wbi / dm / sign #####

"""
https://github.com/katurahinagiku/bilibili-API-collect/blob/main/docs/misc/sign/wbi.md
"""


OE = list(
    base64.b64decode(
        b"Li8SAjUIFyAPMgofOgMtIxsrBTEhCSoTHRwOJwwmKQ0lMAcQGDcoPRoRAAE8Mx4EFhk2FTg7Bj85PgskFCIsNA=="
    )
)
APPKEY = "4409e2ce8ffd12b8"
APPSEC = "59b43e04ad6965f34319062b478f83dd"


def _gen_mixin_key(wbi_img: dict[str, str]) -> str:
    def split(key):
        return wbi_img.get(key).split("/")[-1].split(".")[0]  # type: ignore

    ae = split("img_url") + split("sub_url")
    le = reduce(lambda s, i: s + (ae[i] if i < len(ae) else ""), OE, "")
    return le[:32]


def _enc_wbi(params: dict, mixin_key: str) -> dict:
    params.pop("w_rid", None)  # 重试时先把原有 w_rid 去除
    params.pop("wts", None)
    params["wts"] = round(_get_time())
    # web_location 没被列入参数可能炸一些接口 比如 video.get_ai_conclusion
    Ae = urllib.parse.urlencode(sorted(params.items()))
    params["w_rid"] = hashlib.md5((Ae + mixin_key).encode(encoding="utf-8")).hexdigest()
    return params


def _enc_dm(params: dict) -> dict:
    def encode_to_base64_substring(raw: str) -> str:
        encoded_bytes = base64.b64encode(raw.encode())
        encoded_string = encoded_bytes.decode("ascii")
        return encoded_string[:-2]

    def get_wh(width: int, height: int) -> list[int]:
        rnd = random.randrange(114)
        return [2 * width + 2 * height + 3 * rnd, 4 * width - height + rnd, rnd]

    def get_of(scroll_top: int, scroll_left: int) -> list[int]:
        rnd = random.randrange(514)
        return [
            3 * scroll_top + 2 * scroll_left + rnd,
            4 * scroll_top - 4 * scroll_left + 2 * rnd,
            rnd,
        ]

    browser_fingerprint = get_browser_fingerprint()
    wh_str = ",".join(
        str(value)
        for value in get_wh(
            browser_fingerprint["window"]["innerWidth"],
            browser_fingerprint["window"]["innerHeight"],
        )
    )
    of_str = ",".join(
        str(value)
        for value in get_of(
            browser_fingerprint["window"]["pageYOffset"],
            0,
        )
    )
    params.update(
        {
            "dm_img_list": "[]",  # 鼠标/键盘操作记录
            "dm_img_str": encode_to_base64_substring(
                browser_fingerprint["webgl"]["params"]["7938"]["value"]
            ),
            "dm_cover_img_str": encode_to_base64_substring(
                browser_fingerprint["gpu"]["renderer"]
            ),
            "dm_img_inter": f'{{"ds":[],"wh":[{wh_str}],"of":[{of_str}]}}',
        }
    )
    return params


def _enc_sign(paramsordata: dict) -> dict:
    paramsordata["appkey"] = APPKEY
    paramsordata = dict(sorted(paramsordata.items()))
    paramsordata["sign"] = hashlib.md5(
        (urllib.parse.urlencode(paramsordata) + APPSEC).encode("utf-8")
    ).hexdigest()
    return paramsordata
