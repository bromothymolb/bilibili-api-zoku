"""
bilibili_api._pyinstaller.hook-bilibili_api

Pyinstaller hook support for bilibili_api.
"""

import importlib

from PyInstaller.utils.hooks import collect_data_files

from bilibili_api.clients import ALL_PROVIDED_CLIENTS

datas: list[tuple[str, str]] = collect_data_files("bilibili_api")

hiddenimports = []

for module, client_name, _ in ALL_PROVIDED_CLIENTS[::-1]:
    try:
        importlib.import_module(module)
    except ModuleNotFoundError:
        continue
    finally:
        hiddenimports.append(module)
        hiddenimports.append(f"bilibili_api.clients.{client_name}")
