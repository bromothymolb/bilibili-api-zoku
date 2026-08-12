"""
bilibili_api.tools.ivitools.download
"""

import os

from colorama import Fore

from bilibili_api import interactive_video, video


async def download_interactive_video(bvid: str, out: str):
    ivideo = interactive_video.InteractiveVideo(bvid)
    downloader = interactive_video.InteractiveVideoDownloader(
        ivideo,
        out,
        stream_detecting_params={"codecs": [video.VideoCodecs.AVC]},
    )

    @downloader.on("START")
    async def on_start(data):
        print("Start downloading " + bvid + "...")

    @downloader.on("GET")
    async def on_get(data):
        print(f"{Fore.MAGENTA}Get node {data['title']}{Fore.RESET} (node_id: {Fore.CYAN}{data['node_id']}{Fore.RESET}). ")

    @downloader.on("PREPARE_DOWNLOAD")
    async def on_prepare_download(data):
        print(f"Start download the video for cid {Fore.CYAN}{data['cid']}{Fore.RESET} [video/audio]")

    @downloader.on("DOWNLOAD_PART")
    async def on_download_part(data):
        print(f"{Fore.CYAN}{data['done']}{Fore.RESET} / {Fore.CYAN}{data['total']}{Fore.RESET}", end="\r")

    @downloader.on("DOWNLOAD_SUCCESS")
    async def on_download_success(adta):
        print()

    @downloader.on("PACKAGING")
    async def on_packaing(data):
        print(f"{Fore.YELLOW}Packaging your file ...{Fore.RESET}")

    @downloader.on("SUCCESS")
    async def on_success(data):
        print(
            Fore.GREEN
            + "Congratulations! Your IVI file is ready. Check it at "
            + os.path.abspath(out)
            + ". "
            + Fore.RESET
        )

    try:
        await downloader.start()
    except KeyboardInterrupt:
        downloader.abort()
        print(Fore.YELLOW + "[WRN]: Aborted by user. " + Fore.RESET)
    except Exception as e:
        raise e
