"""
bilibili_api.clients
"""

ALL_PROVIDED_CLIENTS = [
    (
        "curl_cffi",
        "CurlCFFIClient",
        {
            "proxy": "",
            "timeout": 30.0,
            "verify_ssl": True,
            "trust_env": True,
            "impersonate": "",
            "http2": False,
        },
    ),
    (
        "aiohttp",
        "AioHTTPClient",
        {"proxy": "", "timeout": 30.0, "verify_ssl": True, "trust_env": True},
    ),
    (
        "httpx",
        "HTTPXClient",
        {
            "proxy": "",
            "timeout": 30.0,
            "verify_ssl": True,
            "trust_env": True,
            "http2": False,
        },
    ),
]
