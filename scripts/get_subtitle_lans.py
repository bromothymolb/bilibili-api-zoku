from bilibili_api import Api, sync
import json


async def main() -> None:
    res = await Api(
        url="https://s1.hdslb.com/bfs/subtitle/subtitle_lan.json", method="GET"
    ).request(raw=True)
    print(json.dumps(res, ensure_ascii=False))


sync(main())
