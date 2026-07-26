# Recommend cpython 3.13
# modified from doc_gen.py
# doc_fix.py

import datetime
import inspect
import json
import os
import re
import sys

sys.path.append(os.path.join(os.path.abspath(os.path.dirname(__file__)), ".."))

# os.system("stubgen bilibili_api -o .doc_cache/ --include-docstrings")

all_funcs = []
funcs = []

ignored_classes = [
    "AnchorNode",
    "ArticleCardNode",
    "BangumiCardNode",
    "BlockquoteNode",
    "BoldNode",
    "CodeNode",
    "ColorNode",
    "ComicCardNode",
    "DelNode",
    "FontSizeNode",
    "HeadingNode",
    "ImageNode",
    "ItalicNode",
    "LatexNode",
    "LiNode",
    "LiveCardNode",
    "MusicCardNode",
    "Node",
    "OlNode",
    "ParagraphNode",
    "SeparatorNode",
    "ShopCardNode",
    "TextNode",
    "UlNode",
    "UnderlineNode",
    "VideoCardNode",
    "node_info",
    "ServerThreadModel",
    "Datapack",
]

ignored_funcs = [
    "export_ass_from_json",
    "export_ass_from_srt",
    "export_ass_from_xml",
    "json2srt",
    "app_signature",
    "encrypt",
    "id_",
    "photo",
    "is_destroy",
    "login_key",
    "make_qrcode",
    "parse_credential_url",
    "parse_tv_resp",
    "photo",
    "qrcode_image",
    "update_qrcode_data",
    "update_tv_qrcode_data",
    "verify_tv_login_status",
    "generate_clickPosition",
    "BAD_FOR_YOUNGS",
    "CANNOT_CHARGE",
    "CLICKBAIT",
    "COOPERATE_INFRINGEMENT",
    "COVID_RUMORS",
    "DANGEROUS",
    "DISCOMFORT",
    "GAMBLED_SCAMS",
    "ILLEGAL",
    "ILLEGAL_OTHER",
    "ILLEGAL_POPULARIZE",
    "ILLEGAL_URL",
    "INFRINGEMENT",
    "LEAD_WAR",
    "OTHER",
    "OTHER_NEW",
    "PERSONAL_ATTACK",
    "POLITICAL_RUMORS",
    "PRON",
    "SOCIAL_RUMORS",
    "UNREAL_EVENT",
    "VIDEO_INFRINGEMENT",
    "VIOLENT",
    "VULGAR",
    "set_aid_e",
    "set_bvid_e",
    "get_geetest",
    "get_safecenter_geetest",
    "login_with_key",
    "parse_online_rank_v3",
    "parse_interact_word_v2",
    "parse_user_info",
]

ignored_vars = [
    "API",
    "API_USER",
    "API_video",
    "countries_list",
    "cheese_video_meta_cache",
    "fes_id",
    "credential",
    "API_rank",
    "DATAPACK_TYPE_HEARTBEAT",
    "DATAPACK_TYPE_HEARTBEAT_RESPONSE",
    "DATAPACK_TYPE_NOTICE",
    "DATAPACK_TYPE_VERIFY",
    "DATAPACK_TYPE_VERIFY_SUCCESS_RESPONSE",
    "PROTOCOL_VERSION_BROTLI_JSON",
    "PROTOCOL_VERSION_HEARTBEAT",
    "PROTOCOL_VERSION_RAW_JSON",
    "STATUS_CLOSED",
    "STATUS_CLOSING",
    "STATUS_CONNECTING",
    "STATUS_ERROR",
    "STATUS_ESTABLISHED",
    "STATUS_INIT",
    "err_reason",
    "logger",
    "max_retry",
    "retry_after",
    "room_display_id",
    "app_signature",
    "captcha_key",
    "check_url",
    "geetest_result",
    "tmp_token",
    "yarl_url",
    "captcha_id",
    "API_audio",
    "API_ARTICLE",
    "handler",
    "logger",
    "LINES_INFO",
    "watch_room_bangumi_cache",
]


def parse(data: dict, indent: int = 0, root: bool = False):
    if data.get("cross_ref") and not root:
        return
    elif data.get("cross_ref"):
        file = "/".join(data["cross_ref"].split(".")[:-1])
        jsons = json.load(
            open(
                os.path.join(
                    ".mypy_cache", f"{sys.version_info.major}.{sys.version_info.minor}"
                )
                + "/"
                + file
                + ".data.json"
            )
        )
        parse(jsons["names"][data["cross_ref"].split(".")[-1]], indent, root=True)
        return
    if data["node"][".class"] == "TypeInfo":
        if data["node"]["defn"]["name"] in ignored_classes:
            return
        if not data["node"]["defn"]["name"].startswith("Request"):
            funcs.append(
                [
                    data["node"]["defn"]["name"],
                    data["node"]["defn"]["fullname"],
                    "class",
                    data["node"]["bases"][0],
                    indent,
                ]
            )
            if data["node"]["metadata"].get("dataclass"):
                funcs[-1][3] = "@dataclasses.dataclass"
    elif data["node"][".class"] == "FuncDef":
        if data["node"]["name"] in ignored_funcs:
            return
        funcs.append(
            [
                data["node"]["name"],
                data["node"]["fullname"],
                "async def" if "is_coroutine" in data["node"]["flags"] else "def",
                "",
                indent,
            ]
        )
    elif (
        data["node"][".class"] == "Decorator"
        and "is_static" in data["node"]["func"]["flags"]
    ):
        funcs.append(
            [
                data["node"]["func"]["name"],
                data["node"]["func"]["fullname"],
                (
                    "async def"
                    if "is_coroutine" in data["node"]["func"]["flags"]
                    else "def"
                ),
                "@staticmethod",
                indent,
            ]
        )
    elif (
        data["node"][".class"] == "Var"
        and "is_suppressed_import" not in data["node"]["flags"]
    ):
        if data["node"]["name"] in ignored_vars:
            return
        if indent != 1:
            return
        funcs.append(
            (
                data["node"]["name"],
                data["node"]["fullname"],
                "const",
                "",
                indent,
            )
        )
    else:
        return
    if "names" not in data["node"]:
        return
    if data["node"]["bases"][0] == "enum.Enum":
        return
    for key in data["node"]["names"].keys():
        if (not str(key).startswith("_") and key != ".class") or str(key) == "__init__":
            parse(data["node"]["names"][key], indent + 1)


modules = os.listdir(
    f".mypy_cache/{sys.version_info.major}.{sys.version_info.minor}/bilibili_api"
)
modules.sort()
for module in modules:
    if module.find("settings") != -1:
        continue
    if module.find("data.json") != -1 and module != "__init__.data.json":
        funcs = []
        data = json.load(
            open(
                os.path.join(
                    ".mypy_cache",
                    f"{sys.version_info.major}.{sys.version_info.minor}",
                    "bilibili_api",
                    module,
                )
            )
        )
        funcs.append((module[:-10], "bilibili_api." + module[:-10], "MODULE", 1))
        for key in data["names"].keys():
            if key != ".class" and not key.startswith("_"):
                parse(data["names"][key], 2)
        all_funcs.append(funcs)

funcs = []
funcs.append(("bilibili_api", "bilibili_api", "MODULE", 1))
data = json.load(
    open(
        os.path.join(
            ".mypy_cache",
            f"{sys.version_info.major}.{sys.version_info.minor}",
            "bilibili_api",
            "__init__.data.json",
        )
    )
)
for key in data["names"].keys():
    if key != ".class" and not key.startswith("_"):
        if os.path.exists(
            os.path.join(
                ".mypy_cache",
                f"{sys.version_info.major}.{sys.version_info.minor}",
                "bilibili_api",
                key + ".data.json",
            )
        ):
            continue
        if key == "request_log":
            funcs.append(
                ("request_log", "bilibili_api.request_log", "var", "AsyncEvent", 2)
            )
            parse(
                json.load(
                    open(
                        os.path.join(
                            ".mypy_cache",
                            f"{sys.version_info.major}.{sys.version_info.minor}",
                            "bilibili_api",
                            "utils",
                            "network.data.json",
                        )
                    )
                )["names"]["RequestLog"],
                2,
            )
        elif key == "request_settings":
            funcs.append(
                (
                    "request_settings",
                    "bilibili_api.request_settings",
                    "var",
                    "builtins.object",
                    2,
                )
            )
            parse(
                json.load(
                    open(
                        os.path.join(
                            ".mypy_cache",
                            f"{sys.version_info.major}.{sys.version_info.minor}",
                            "bilibili_api",
                            "utils",
                            "network.data.json",
                        )
                    )
                )["names"]["RequestSettings"],
                2,
            )
        elif key == "HEADERS":
            funcs.append(
                ("HEADERS", "bilibili_api.HEADERS", "var", "builtins.object", 2)
            )
        else:
            parse(data["names"][key], 2, root=True)
all_funcs.append(funcs)


import bilibili_api  # noqa: F401


def handle_annotation(ty: type):
    ret = str(ty)
    ret = ret.replace("'>", "")
    ret = ret.replace("<class '", "")
    ret = ret.replace("<enum '", "")
    ret = ret.replace("bilibili_api.utils.network.", "")
    ret = ret.replace("bilibili_api.utils.AsyncEvent.", "")
    ret = ret.replace("bilibili_api.utils.danmaku.", "")
    ret = ret.replace("bilibili_api.utils.geetest.", "")
    ret = ret.replace("bilibili_api.utils.parse_link.", "")
    ret = ret.replace("bilibili_api.utils.picture.", "")
    ret = ret.replace("bilibili_api.", "")
    ret = ret.replace("typing.", "")
    ret = ret.replace("collections.abc.", "")
    return ret


def handle_doc(doc: str, isp: inspect.Signature):
    doc = doc.lstrip("\n")
    info = ""
    arginfos = {}
    ret = ""
    note = ""
    state = 0
    for line in doc.split("\n"):
        if line.startswith("Attribute") or line.startswith("Args"):
            state = 1
        elif line.startswith("Return"):
            state = 2
        else:
            if state == 0:
                info += line + "\n"
            elif state == 1:
                if line.strip() == "":
                    continue
                if not line.startswith("    ") and line != "Return":
                    state = 3
                    continue
                arginfo = line.split(":")[1].lstrip()
                argname = line.split("(")[0].strip()
                reg = re.compile(r"([Dd]efault[s]? to .*[\\.。])")
                reg_no_comma = re.compile(r"([Dd]efault[s]? to .*)")
                m1 = reg.findall(arginfo)
                m2 = reg_no_comma.findall(arginfo)
                if len(m1):
                    for m in m1:
                        arginfo = arginfo.replace(m, "")
                elif len(m2):
                    for m in m2:
                        arginfo = arginfo.replace(m, "")
                arginfos[argname] = arginfo
            elif state == 2:
                ret += line + "\n"
                state = 3
            else:
                note += line + "\n"
    if ret.replace(" ", "").replace("\n", "") != "":
        retdesc = "".join(ret.split(":")[1:])
    else:
        retdesc = ""
    retdesc = retdesc.strip()
    info = info.strip("\n")
    info = info.strip()
    note = note.strip("\n")
    note = note.strip()
    new_doc = ""
    if len(info):
        new_doc += info
    if len(sig.parameters) and (
        not (len(sig.parameters) == 1 and sig.parameters.get("self"))
    ):
        new_doc += "\n\n"
        new_doc += "Args:"
        for name, para in sig.parameters.items():
            if name == "self":
                continue
            if para.annotation == inspect._empty:
                breakpoint()  # no prividing arg type  # noqa: T100
            new_doc += "\n"
            new_doc += "    "
            if para.default != inspect._empty:
                new_doc += f"{name} ({handle_annotation(para.annotation)}, optional): {arginfos[name]}"
                new_doc = new_doc.rstrip()
                new_doc = new_doc.rstrip(".")
                new_doc = new_doc.rstrip("。")
                if isinstance(para.default, datetime.datetime):
                    new_doc += ". Defaults to datetime.datetime.now()"
                else:
                    new_doc += f". Defaults to {para.default!r}."
            else:
                new_doc += (
                    f"{name} ({handle_annotation(para.annotation)}): {arginfos[name]}"
                )
    if sig.return_annotation == inspect._empty:
        breakpoint()  # no providing return type  # noqa: T100
    if sig.return_annotation is not None and retdesc == "":
        breakpoint()  # no return description  # noqa: T100
    if sig.return_annotation is not None:
        new_doc += "\n\nReturns:\n"
        new_doc += f"    {handle_annotation(sig.return_annotation)}: {retdesc}"
    if note:
        new_doc += "\n\n"
        new_doc += note
    new_doc = new_doc.strip("\n")
    return new_doc


def open_file_lines(file_path: str):
    file = open(f"./bilibili_api/{file_path}.py")
    content = file.read()
    lines = content.split("\n")
    file.close()
    return lines


def write_file_lines(file_path: str, lines: list[str]):
    file = open(f"./bilibili_api/{file_path}.py", "w")
    content = "\n".join(lines)
    file.write(content)
    file.close()


def find_lines(file_path: str, doc: str):
    lines = open_file_lines(file_path)
    doc_lines = doc.split("\n")[1:-1]
    start, end, indent = 0, 0, 0
    for i, line in enumerate(lines):
        if line.strip() == doc_lines[0].strip():
            flag = True
            for j, doc_line in enumerate(doc_lines):
                if lines[i + j].strip() != doc_line.strip():
                    flag = False
                    # print(i, j, str(lines[i + j].strip()), str(doc_line.strip()))
                    break
            if flag:
                start = i
                end = i + len(doc.split("\n")) - 1
                indent = (len(line) - len(line.lstrip())) // 4
                break
    return start, end, indent


def replace_lines(l: list, s: int, e: int, n: list):
    pre = l[:s]
    post = l[e + 1 :]
    return pre + n + post


for module in all_funcs:
    if module[0][0] in ["_pyinstaller", "tools", "exceptions", "clients"]:
        continue
    print("BEGIN", module[0][0])
    last_data_class = -114514
    for idx, func in enumerate(module[1:]):
        if idx == last_data_class + 1:
            # don't show __init__ of dataclass and ApiException
            continue
        if func[1].count("exceptions") == 1:
            func[1] = ".".join(func[1].split(".")[:2] + func[1].split(".")[3:])
        print("PROCESS", func[1])
        if (
            func[3] == "@dataclasses.dataclass"
            or func[1].count("exceptions") == 1
            or func[0].startswith("request_")
        ):
            last_data_class = idx
        if func[0] == "HEADERS":
            continue
        doc = eval(f"{func[1]}.__doc__")
        if len(doc) == 0:
            continue
        if not (func[2] == "class" or func[2] == "var"):
            print("UPDATING")
            if module[0][0] != "bilibili_api":
                path = module[0][0]
                start, end, indent = find_lines(module[0][0], doc)
            else:
                path = ""
                paths = [
                    "utils/aid_bvid_transformer",
                    "utils/AsyncEvent",
                    "utils/danmaku",
                    "utils/geetest",
                    "utils/network",
                    "utils/parse_link",
                    "utils/picture",
                    "utils/short",
                    "utils/sync",
                ]
                start, end, indent = 0, 0, 0
                for p in paths:
                    start, end, indent = find_lines(p, doc)
                    if end != 0:
                        path = p
                        break
            print("on", path, f"[{start} - {end}]", "indent:", indent)
            sig = inspect.signature(eval(func[1]))
            new_doc = handle_doc(doc, sig)
            print("------------------------------")
            print(handle_doc(doc, sig))
            print("------------------------------")
            new_doc = '"""\n' + new_doc + '\n"""'
            new_doc_lines = new_doc.split("\n")
            for i in range(len(new_doc_lines)):
                new_doc_lines[i] = "    " * indent + new_doc_lines[i]
            lines = open_file_lines(path)
            write_file_lines(
                path, replace_lines(lines, start - 1, end - 1, new_doc_lines)
            )

    print("DONE", f"./bilibili_api/{module[0][0]}.py")
