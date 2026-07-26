"""
ivitools.utils
"""

import json
import os
import zipfile


def touch_ivi(path: str):
    ivi = zipfile.ZipFile(open(path, "rb"))
    info = ivi.open("bilivideo.json").read()
    print(json.loads(info))
    return json.loads(info)


def extract_ivi(path: str, dest: str):
    print("Extracting...")
    if not os.path.exists(dest):
        os.makedirs(dest)
    zipfile.ZipFile(path).extractall(dest)
