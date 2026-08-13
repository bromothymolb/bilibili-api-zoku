"""
bilibili_api._pyinstaller.entry_points

Pyinstaller hook support for bilibili_api.
"""

import os


def get_hook_dirs() -> list[str]:
    return [os.path.abspath(os.path.dirname(__file__))]
