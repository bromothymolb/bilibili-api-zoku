"""
bilibili_api.tools.ivitools.__main__
"""

__author__ = "Nemo2011 <yimoxia@outlook.com>"
__license__ = "GPLv3+"

import sys
import warnings

from colorama import Fore

from bilibili_api import sync

from .download import download_interactive_video
from .utils import extract_ivi, touch_ivi


def run_args(command: str, args: list[str]):
    if command == "help":
        print(
            "IVITools - A Simple IVI file manager & toolbox. \n\
\n\
Commands: download, extract, help, play, scan, touch\n\
\n\
ivitools download [BVID] [OUT]\n\
ivitools extract [IVI] [DIR]\n\
ivitools help\n\
ivitools play [IVI] (PyQT6 require)\n\
ivitools touch [IVI]\n\
\n\
Use `--debug` to output full error messages with traceback."
        )
    elif command == "extract":
        extract_ivi(args[0], args[1])
    elif command == "touch":
        touch_ivi(args[0])
    elif command == "download":
        sync(download_interactive_video(args[0], args[1]))
    elif command == "play":
        try:
            import PyQt6  # noqa: F401
        except ImportError:
            warnings.warn(
                "IVITools Built-in Player require PyQt6 but IVITools can't find it. \nYou can install it by `pip3 install PyQt6`. ",
                stacklevel=2,
            )
            return
        from .player import main, prepopen

        if len(args) == 0:
            main()
        else:
            prepopen(args[0])
    else:
        raise ValueError("Command not found. Use `ivitools help` for helps. ")


def main():
    if len(sys.argv) == 1:
        print(Fore.YELLOW + "[WRN]: No arguments. " + Fore.RESET)
        print(Fore.YELLOW + "[WRN]: Use `ivitools help` for helps. " + Fore.RESET)
        return
    args = sys.argv
    try:
        run_args(args[1], args[2:])
    except Exception as e:
        if "--debug" in args:
            raise e
        else:
            print(Fore.RED + "[ERR]: " + str(e) + Fore.RESET)


if __name__ == "__main__":
    main()
