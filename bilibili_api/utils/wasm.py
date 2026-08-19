"""
bilibili_api.utils.wasm

简单 wasm 运行支持
"""

from collections.abc import Callable
from enum import Enum
import os
import struct
import time
from typing import Any

from Cryptodome.Random import get_random_bytes
from frozendict import frozendict
from wasmtime import Func, FuncType, Instance, Memory, Module, Store, ValType

from .high_level import get_browser_fingerprint


class SpecificObjects(Enum):
    globalThis = "114514"
    this = "1919810"
    anything = "anything"
    undefined = "undefined"
    true = "true"
    false = "false"
    empty_dict = "empty_dict"


class Go:
    def __init__(self):
        self.argv = ["js"]
        self.env = {}
        self.exit = lambda code: print("exit code:", code) if code else None
        self._pendingEvent = None
        self._scheduledTimeouts = {}
        self._nextCallbackTimeoutID = 1
        self.mem: Memory
        self._values = [
            float("nan"),
            0,
            None,
            True,
            False,
            SpecificObjects.globalThis,
            SpecificObjects.this,
        ]  # type: ignore
        self._goRefCounts = [0] * len(self._values)  # type: ignore
        self._ids = {
            0: 1,
            None: 2,
            SpecificObjects.true: 3,
            SpecificObjects.false: 4,
            SpecificObjects.globalThis: 5,
            SpecificObjects.this: 6,
        }
        self._idPool = []
        self._result = {}

    def loadValue(self, addr: int) -> object:
        f = struct.unpack("<d", self.mem.read(self._store)[addr : addr + 8])[0]
        if f == 0:
            return SpecificObjects.undefined
        if str(f) != "nan":
            return f
        id = struct.unpack("<I", self.mem.read(self._store)[addr : addr + 4])[0]
        return self._values[id]

    def loadValueRetId(self, addr: int) -> int:
        f = struct.unpack("<d", self.mem.read(self._store)[addr : addr + 8])[0]
        if f == 0:
            return SpecificObjects.undefined  # type: ignore
        if str(f) != "nan":
            return f
        id = struct.unpack("<I", self.mem.read(self._store)[addr : addr + 4])[0]
        return id

    def storeValue(self, addr: int, v: object) -> None:
        nanHead = 0x7FF80000
        if (isinstance(v, int) or isinstance(v, float)) and v != 0:
            if str(v) == "nan":
                self.mem.write(self._store, struct.pack("<I", nanHead), addr + 4)
                self.mem.write(self._store, struct.pack("<I", 0), addr)
                return
            self.mem.write(self._store, struct.pack("<d", v), addr)
            return
        if v == SpecificObjects.undefined:
            self.mem.write(self._store, struct.pack("<d", 0.0), addr)
            return
        id = self._ids.get(v)
        if id is None:
            if len(self._idPool):
                id = self._idPool.pop()
            else:
                id = len(self._values)
            self._values.append(v)
            self._goRefCounts.append(0)
            self._ids[v] = id
        self._goRefCounts[id] += 1
        typeFlag = 0
        if isinstance(v, str):
            typeFlag = 2
        elif isinstance(v, Callable):
            typeFlag = 4
        else:
            if v is not None:
                typeFlag = 1
        self.mem.write(self._store, struct.pack("<I", nanHead | typeFlag), addr + 4)
        self.mem.write(self._store, struct.pack("<I", id), addr)

    def loadSlice(self, addr: int) -> tuple[int, int]:
        array = struct.unpack("<q", self.mem.read(self._store)[addr : addr + 8])[0]
        len = struct.unpack("<q", self.mem.read(self._store)[addr + 8 : addr + 16])[0]
        return array, len

    def loadSliceOfValues(self, addr: int) -> list:
        array = struct.unpack("<q", self.mem.read(self._store)[addr : addr + 8])[0]
        len = struct.unpack("<q", self.mem.read(self._store)[addr + 8 : addr + 16])[0]
        a = []
        for i in range(len):
            a.append(self.loadValue(array + i * 8))
        return a

    def loadString(self, addr: int) -> str:
        saddr = struct.unpack("<q", self.mem.read(self._store)[addr : addr + 8])[0]
        len = struct.unpack("<q", self.mem.read(self._store)[addr + 8 : addr + 16])[0]
        return bytes(self.mem.read(self._store)[saddr : saddr + len]).decode("utf-8")

    def runtime_wasmExit(self, sp: int) -> None:
        if sp < 0:
            sp += 1 << 32
        code = struct.unpack("<i", self.mem.read(self._store)[sp + 8 : sp + 12])[0]
        self.exited = True
        del self._inst
        del self._values
        del self._goRefCounts
        del self._ids
        del self._idPool
        self.exit(code)

    def runtime_resetMemoryDataView(self, sp: int) -> None:
        if sp < 0:
            sp += 1 << 32
        mem: Memory = self._inst.exports(self._store)["mem"]  # type: ignore
        self.mem = mem

    def runtime_nanotime1(self, sp: int) -> None:
        if sp < 0:
            sp += 1 << 32
        self.mem.write(self._store, struct.pack("<q", time.time_ns()), sp + 8)

    def runtime_walltime(self, sp: int) -> None:
        if sp < 0:
            sp += 1 << 32
        msec = int(time.time() * 1000)
        self.mem.write(self._store, struct.pack("<q", msec // 1000), sp + 8)
        self.mem.write(self._store, struct.pack("<i", (msec % 1000) * 1000000), sp + 16)

    def runtime_getRandomData(self, sp: int) -> None:
        if sp < 0:
            sp += 1 << 32
        start, len = self.loadSlice(sp + 8)
        self.mem.write(self._store, get_random_bytes(len), start)

    def syscall_js_finalizeRef(self, sp: int) -> None:
        if sp < 0:
            sp += 1 << 32
        id = struct.unpack("<I", self.mem.read(self._store)[sp + 8 : sp + 12])[0]
        self._goRefCounts[id] -= 1
        if self._goRefCounts[id] == 0:
            v = self._values[id]
            del self._values[id]
            del self._ids[v]
            self._idPool.append(id)

    def syscall_js_stringVal(self, sp: int) -> None:
        if sp < 0:
            sp += 1 << 32
        self.storeValue(sp + 24, self.loadString(sp + 8))

    def syscall_js_valueGet(self, sp: int) -> None:
        if sp < 0:
            sp += 1 << 32
        a = self.loadValue(sp + 8)
        b = self.loadString(sp + 16)
        if a == SpecificObjects.globalThis:
            if b == "fs":
                result = frozendict(
                    {
                        "constants": frozendict(
                            {
                                "O_WRONLY": -1,
                                "O_RDWR": -1,
                                "O_CREAT": -1,
                                "O_TRUNC": -1,
                                "O_APPEND": -1,
                                "O_EXCL": -1,
                                "O_DIRECTORY": -1,
                            }
                        ),
                        "writeSync": lambda a, b: None,
                    }
                )
            elif b == "Object":
                result = lambda: SpecificObjects.empty_dict  # noqa: E731
            else:
                result = SpecificObjects.undefined
        elif a == SpecificObjects.this:
            if b == "_pendingEvent":
                result = self._pendingEvent
            else:
                result = None
        else:
            result = a[b]  # type: ignore
            if result == SpecificObjects.undefined:
                result = None
        sp = self._inst.exports(self._store)["getsp"](self._store)  # type: ignore
        if sp < 0:
            sp += 1 << 32
        self.storeValue(sp + 32, result)

    def syscall_js_valueSet(self, sp: int) -> None:
        if sp < 0:
            sp += 1 << 32
        a = self.loadValueRetId(sp + 8)
        b = self.loadString(sp + 16)
        c = self.loadValue(sp + 32)
        if self._values[a] == SpecificObjects.globalThis:
            self._function = c
        elif b == "_pendingEvent":
            self._pendingEvent = None
        elif self._values[a] == SpecificObjects.empty_dict:
            self._result[b] = c
        else:
            self._pendingEvent = frozendict({"result": self._result})  # type: ignore

    def syscall_js_valueIndex(self, sp: int) -> None:
        if sp < 0:
            sp += 1 << 32
        a = self.loadValue(sp + 8)
        b = struct.unpack("<q", self.mem.read(self._store)[sp + 16 : sp + 24])[0]
        self.storeValue(sp + 24, a[b])  # type: ignore

    def syscall_js_valueCall(self, sp: int) -> None:
        if sp < 0:
            sp += 1 << 32
        try:
            self.loadValue(sp + 8)
            self.loadString(sp + 16)
            self.loadSliceOfValues(sp + 32)
            result = self._makeFuncWrapper(1)
            sp = self._inst.exports(self._store)["getsp"](self._store)  # type: ignore
            if sp < 0:
                sp += 1 << 32
            self.storeValue(sp + 56, result)
            self.mem.write(self._store, struct.pack("<H", 1), sp + 64)
        except Exception as e:
            sp = self._inst.exports(self._store)["getsp"](self._store)  # type: ignore
            if sp < 0:
                sp += 1 << 32
            self.storeValue(sp + 56, e)
            self.mem.write(self._store, struct.pack("<H", 0), sp + 64)

    def syscall_js_valueNew(self, sp: int) -> None:
        if sp < 0:
            sp += 1 << 32
        try:
            self.loadValue(sp + 8)
            self.loadSliceOfValues(sp + 16)
            result = SpecificObjects.empty_dict
            sp = self._inst.exports(self._store)["getsp"](self._store)  # type: ignore
            if sp < 0:
                sp += 1 << 32
            self.storeValue(sp + 40, result)
            self.mem.write(self._store, struct.pack("<H", 1), sp + 48)
        except Exception as e:
            sp = self._inst.exports(self._store)["getsp"](self._store)  # type: ignore
            if sp < 0:
                sp += 1 << 32
            self.storeValue(sp + 40, e)
            self.mem.write(self._store, struct.pack("<H", 0), sp + 48)

    def syscall_js_valueLength(self, sp: int) -> None:
        if sp < 0:
            sp += 1 << 32
        val = self.loadValue(sp + 8)
        self.mem.write(self._store, struct.pack("<q", len(val)), sp + 16)  # type: ignore

    def syscall_js_valuePrepareString(self, sp: int) -> None:
        if sp < 0:
            sp += 1 << 32
        string = self.loadValue(sp + 8)
        bts = str(string).encode("utf-8")
        self.storeValue(sp + 16, bts)
        self.mem.write(self._store, struct.pack("<q", len(bts)), sp + 24)

    def syscall_js_valueLoadString(self, sp: int) -> None:
        if sp < 0:
            sp += 1 << 32
        string = self.loadValue(sp + 8)
        start, len = self.loadSlice(sp + 16)
        self.mem.write(self._store, string[:len], start)  # type: ignore

    def _resume(self):
        if self.exited:
            raise Exception("Go program has already exited")
        self._inst.exports(self._store)["resume"](self._store)  # type: ignore

    def _makeFuncWrapper(self, id: int) -> Callable:
        def function(*args) -> dict:
            event = frozendict(
                {
                    "id": id,
                    "this": SpecificObjects.undefined,
                    "args": args,
                    "result": None,
                }
            )
            self._pendingEvent = event
            self._resume()
            return event["result"]

        return function

    def run(self, instance: Instance, store: Store) -> None:
        self._inst = instance
        self._store = store
        mem: Memory = self._inst.exports(self._store)["mem"]  # type: ignore
        self.mem = mem
        self._values = [
            float("nan"),
            0,
            None,
            True,
            False,
            SpecificObjects.globalThis,
            SpecificObjects.this,
        ]  # type: ignore
        self._goRefCounts = [0] * len(self._values)  # type: ignore
        self._ids = {
            0: 1,
            None: 2,
            SpecificObjects.true: 3,
            SpecificObjects.false: 4,
            SpecificObjects.globalThis: 5,
            SpecificObjects.this: 6,
        }
        self._idPool = []
        self.exited = False
        self.offset = 4096

        def strPtr(string: str) -> int:
            ptr = self.offset
            bts = (string + "\0").encode("utf-8")
            self.mem.write(self._store, bts, self.offset)
            self.offset += len(bts)
            if self.offset % 8 != 0:
                self.offset += 8 - (self.offset % 8)
            return ptr

        argc = len(self.argv)
        argvPtrs = []
        for argv in self.argv:
            argvPtrs.append(strPtr(argv))
        argvPtrs.append(0)
        keys = list(self.env.keys())
        keys.sort()
        for key in keys:
            argvPtrs.append(strPtr(f"{key}={self.env[key]}"))
        argvPtrs.append(0)
        argv = self.offset
        for ptr in argvPtrs:
            self.mem.write(self._store, struct.pack("<I", ptr), self.offset)
            self.mem.write(self._store, struct.pack("<I", 0), self.offset + 4)
            self.offset += 8
        wasmMinDataAddr = 4096 + 8192
        if self.offset >= wasmMinDataAddr:
            raise Exception(
                "total length of command line and environment variables exceeds limit"
            )
        self._inst.exports(self._store)["run"](self._store, argc, argv)  # type: ignore


__instances: dict[str, Go] = {}


def get_instance(route: str, go_class: type[Go] = Go) -> Go:
    if not __instances.get(route):
        path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "data", route)
        )
        go = go_class()
        with open(path, "rb") as file:
            bts = file.read()
        store = Store()
        module = Module(store.engine, bts)
        # fmt: off
        imports = [
            Func(store, FuncType([ValType.i32()], []), lambda x: None),
            Func(store, FuncType([ValType.i32()], []), lambda x: None),
            Func(store, FuncType([ValType.i32()], []), go.runtime_resetMemoryDataView),
            Func(store, FuncType([ValType.i32()], []), lambda x: None),
            Func(store, FuncType([ValType.i32()], []), go.runtime_getRandomData),
            Func(store, FuncType([ValType.i32()], []), go.runtime_nanotime1),
            Func(store, FuncType([ValType.i32()], []), go.runtime_wasmExit),
            Func(store, FuncType([ValType.i32()], []), go.runtime_walltime),
            Func(store, FuncType([ValType.i32()], []), go.syscall_js_finalizeRef),
            Func(store, FuncType([ValType.i32()], []), go.syscall_js_stringVal),
            Func(store, FuncType([ValType.i32()], []), go.syscall_js_valueGet),
            Func(store, FuncType([ValType.i32()], []), go.syscall_js_valueSet),
            Func(store, FuncType([ValType.i32()], []), go.syscall_js_valueIndex),
            Func(store, FuncType([ValType.i32()], []), lambda x: None),
            Func(store, FuncType([ValType.i32()], []), go.syscall_js_valueLength),
            Func(store, FuncType([ValType.i32()], []), go.syscall_js_valueCall),
            Func(store, FuncType([ValType.i32()], []), go.syscall_js_valueNew),
            Func(store, FuncType([ValType.i32()], []), go.syscall_js_valuePrepareString),
            Func(store, FuncType([ValType.i32()], []), go.syscall_js_valueLoadString),
            Func(store, FuncType([ValType.i32()], []), lambda x: None),
        ]
        # fmt: on
        instance = Instance(store, module, imports)
        go.run(instance, store)
        __instances[route] = go
    return __instances[route]


def call_wasm_function(route: str, *args, **kwargs) -> Any:
    get_instance(route)._function(*args, **kwargs)  # type: ignore


def get_wasm_result(route: str, key: str = "_result") -> Any:
    return getattr(get_instance(route), key)


class M2Go(Go):
    def __init__(self):
        super().__init__()
        self._eval_cnt = 0

    # override valueCall to enable globalThis.eval
    def syscall_js_valueCall(self, sp: int) -> None:
        if sp < 0:
            sp += 1 << 32
        try:
            self.loadValue(sp + 8)
            b = self.loadString(sp + 16)
            self.loadSliceOfValues(sp + 32)
            if b == "eval":
                match self._eval_cnt % 7:
                    case 0:
                        result = '{"bilibili_0":1}'
                    case 1:
                        result = "C.de.1|C.ga.1|C.pa.1|C.ca.1|H.cm.1|H.tb.1|H.tL.1|H.tn.1|H.gt.1|O.tp.1|O.gt.1|O.de.1|O.ga.1|O.pa.1|O.ca.1|W.rs.1|W.gr.1|W.gn.1|W2.rs.1|W2.gr.1|W2.gn.1|U.cL.1|U.rL.1|w.Bb.1|H.ss.1|H.sg.1"
                    case 2:
                        fp = get_browser_fingerprint()
                        ua = fp["navigator"].get("userAgent", "#")
                        lang = ",".join(fp["navigator"].get("languages", []))
                        scr_width = fp["navigator"].get("width", 0)
                        scr_height = fp["navigator"].get("height", 0)
                        scr_color_depth = fp["navigator"].get("colorDepth", 0)
                        scr_pixel_depth = fp["navigator"].get("pixelDepth", 0)
                        screen = f"x{scr_width}y{scr_height}c{scr_color_depth}p{scr_pixel_depth}"
                        device_memory = fp["navigator"].get("deviceMemory", "#")
                        hardware_concurrency = fp["navigator"].get(
                            "hardwareConcurrency", "#"
                        )
                        vendor = fp["navigator"].get("vendor", "#")
                        platform = fp["navigator"].get("platform", "#")
                        vendor_flavors = "#"
                        vendor_sub = "#"
                        time_zone = fp["intl"].get("timeZone", "#")
                        match_media = "false|false"
                        apple_pay = "#"
                        browser_resolution = (
                            f"{fp['window']['innerWidth']}-{fp['window']['innerHeight']}",
                        )
                        other_data = (
                            "false|#|data:image/png;base64,iVBORw0KGgoAAAANS"
                            "UhEUgAAAGQAAABkCAYAAABw4pVUAAAGTElEQVR4AeyYachV"
                            "VRSGj2U0KREN0mBlgQaVQZbRiNAEZYX0Q6MSxCJBiSIsgig"
                            "akNAISitpojkw8kcDGWWESYFlZIQ/yiY0y8IGB0QcPp/3cs"
                            "/lfnrv/s7d9+5zlrpkvd/aZw9rr/2+Z++zrwdk/s8UAy6IK"
                            "TmyzAVxQYwxYCwd3yEuiDEGjKXjO8QFMcaAsXR8h7ggxhgw"
                            "lk6aHWJskXtTOi6IMbVcEBfEGAPG0vEd4oIYY8BYOr5DXBB"
                            "jDBhLx3eIC2KMAWPp7E07xBh1adJxQdLwGh3VBYmmLs1AFy"
                            "QNr9FRXZBo6tIMdEHS8Bod1QWJpi7NQBckDa/RUV2QaOrSD"
                            "HRB0vAaHdUFiaYuzUAXJA2v0VFdkGjq0gx0QdLwGh3VBYmm"
                            "Ls1AFyQNr9FRXZBo6tIMLCxIX5a9AfoK4H2lSr914CeVQ6B"
                            "PoX6hGGrrVRzFigU5DAa3g2NjYxQWhAm+Be814QfKMvnm+m"
                            "Wq3E8xi3XPB0NBlBUWZFCWzQHX5WC2J4Bsfl5X9w+rsgMcT"
                            "9+RoFvrVZxu8ogWIp+0sCD5gE492/dasARsAEvB9N1ivM3z"
                            "66BmtJ8EXgWrgcZ8ib8XDK51aP+nV3Ey5poEFoE8h2WUZ4K"
                            "2OdA2l9RuArIFPM9WQaA8GiwEOp4FlUerLQdttXWnFuRUJn"
                            "wXDAM68i7Cz2PyKfjcVDdWD9RrwR9TvgX8Bt4BivEYfg4IW"
                            "U/ikMP9TPIWuBB8AZT3eXgRfBe+nf1Dw/9A9jd//gMS93L8"
                            "CjABrAGfAJVXMNellNWnse7Ugmg+HXWjOM40+Q2qANeAVnY"
                            "WlTq+XqL/xUDCnU7dRjCVBShxigNaVBziH0bke4BsJPNPBM"
                            "r7ClWA60FLo9+DNNQuNPjpPM8i3kGUnway8dSNAdpF56oCz"
                            "KXPgfhGvmUI8igT5vZRvaAE6sV+Ln/DriTRCWAIC/iXHieD"
                            "Iylvxxex2Dg7CD4e6GX4E5/bz/VCp98IrVMv2Dfk/kE9RkZ"
                            "5OeXPgY6tEfhGvqkF+YvJNzBhzShvpqBtqzeRYn+jXQt/md"
                            "oTwUKwEVEW4bXFi+4OLTgqDvNvZS4RNZR5ZwN9R9ZRl1/fC"
                            "+fAGJmOW/lziKXvUQNUXgJkpzBvI9/UgmzSjB1iKv11tC3A"
                            "66i6Cv8iWMyiDsYXtY7jEF98vMkEH4KZ4AzwKZgBYmxIfZB"
                            "+Gujb0Qy9eILWqG61fJWAHkwAQg4lkTPBZ7w1E/FHgcuAdp"
                            "U+2udTHtC6iHMBwSeB78AIchgObqSsGxwu63SH/KJBYC1xp"
                            "jSDuoeAjvPlzfmaEoQEbwa6kShZHT3bWITe0PxjeTjtRSw2"
                            "zqh68MXM+2u9LKcPsfxAguTfuEPUGXwPZOMgXd8KlXWrOpq"
                            "CRF+FPw408rUmiIjXFp7BAp4Dk4F+gE4jadUvwRex2Dh6GR"
                            "T/Vua9G+hi8RQVygGXHUMdWqnYErWrLi262t9Jx/WU7wMy/"
                            "Rabxnj9DtPlRheEO+izmsZGvt0IspNAstyr3BVI7g8CXA1W"
                            "gtvAK0B3/6/wujLqUkAxbLFxGKfbj+b9kRkeB7pY6OicTFn"
                            "nvUgcQ7mdKV99oMfRIf8fC/1+kQhHUPcsmAe00x7A61knQW"
                            "Pd0YKQ/PNgEHiSwHsY9cPAabs3UKdzeXhez3O/fjwvpU3fE"
                            "f2Y1EdVV9+x1Iskmlob7b2K8wKxRLpyPIGy4r6G1zdA6/26"
                            "dQaZiF1FP61ZR5LyV91O6p7JskyC6PaomGdT9wjIjzj1q60"
                            "7KAhBKjES7QO6Mq/EF9oVrRJlbHQcxq4Ba1vFHaiOcevBlu"
                            "Z+PCuX3/FtY9LWZ1KQ5oXsb2UXxJjiLogLYowBY+n4DnFBj"
                            "DFgLB3fIS6IMQaMpeM7xAUxxoCxdHyHuCDGGDCWju8QF8QY"
                            "A8bS8R3ighhjwFg6vkNcEGMMGEvHd4gLkoaBfSWq7xBjSro"
                            "gLogxBoyl4zvEBTHGgLF0fIe4IMYYMJaO7xAXxBgDxtLxHR"
                            "IUpPxGF6R8zoMzuiBBespvdEHK5zw4owsSpKf8RhekfM6DM"
                            "7ogQXrKb3RByuc8OKMLEqSn/EYXpHzOgzO6IEF60jSGorog"
                            "IXYqaHNBKiA9NKULEmKngjYXpALSQ1O6ICF2KmhzQSogPTS"
                            "lCxJip4I2F6QC0kNT7gIAAP///a+q6AAAAAZJREFUAwCdgm"
                            "zYWrnjtAAAAABJRU5ErkJggg==|2|2|30430|0"
                        )
                        result = "|".join(
                            [
                                str(x)
                                for x in [
                                    ua,
                                    lang,
                                    screen,
                                    device_memory,
                                    hardware_concurrency,
                                    vendor,
                                    platform,
                                    vendor_flavors,
                                    vendor_sub,
                                    time_zone,
                                    match_media,
                                    apple_pay,
                                    browser_resolution,
                                    other_data,
                                ]
                            ]
                        )
                    case 3:
                        result = "Error|at eval|at eval|at eval|at Object.<anonymous>|    at https://s1.hdslb.com/bfs/manga-static/manga-pc/static/js/vendors.6bf71f38f4.js:2:507610|at Object.next|    at https://s1.hdslb.com/bfs/manga-static/manga-pc/static/js/vendors.6bf71f38f4.js:2:506607|at new Promise|    at https://s1.hdslb.com/bfs/manga-static/manga-pc/static/js/vendors.6bf71f38f4.js:2:506344|at Object.isOpen"
                    case 4:
                        result = "r|v"
                    case 5:
                        result = "0｜0｜0｜1｜0｜"
                    case 6:
                        result = SpecificObjects.undefined
                    case _:
                        result = "#"
                self._eval_cnt += 1
            else:
                result = self._makeFuncWrapper(1)
            sp = self._inst.exports(self._store)["getsp"](self._store)  # type: ignore
            if sp < 0:
                sp += 1 << 32
            self.storeValue(sp + 56, result)
            self.mem.write(self._store, struct.pack("<H", 1), sp + 64)
        except Exception as e:
            sp = self._inst.exports(self._store)["getsp"](self._store)  # type: ignore
            if sp < 0:
                sp += 1 << 32
            self.storeValue(sp + 56, e)
            self.mem.write(self._store, struct.pack("<H", 0), sp + 64)

    def syscall_js_valueSet(self, sp: int) -> None:
        if sp < 0:
            sp += 1 << 32
        a = self.loadValueRetId(sp + 8)
        b = self.loadString(sp + 16)
        c = self.loadValue(sp + 32)
        if self._values[a] == SpecificObjects.globalThis:
            self._function = c
        elif b == "_pendingEvent":
            self._pendingEvent = None
        elif isinstance(self._values[a], frozendict):
            if not self._pendingEvent:
                self._pendingEvent = {}
            self._pendingEvent["result"] = c
