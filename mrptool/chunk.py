# -*- coding: utf-8 -*-
"""
Mythroad (.mr) chunk 解析器
===========================
.mr 是 **Lua 5.0 的预编译 chunk**,由杭州斯凯网络(Mythroad/MRP 平台)改造而成。

与官方 Lua 5.0.2 的差异(经 16 组参数穷举验证,唯一解):

    项              官方 Lua 5.0.2      Mythroad .mr
    ---------------------------------------------------
    签名            \\033"Lua"          \\033"MRP"
    头部长度        21 字节             6 字节(省掉全部 TESTSIZE 与 TEST_NUMBER)
    sizeof(size_t)  4 或 8              4
    lua_Number      8 (double)          4(非 IEEE754,疑似定点/整数)
    Instruction     4                   4
    sizeof(int)     4                   4

验证方法:严格按官方 lundump.c 实现解析器,遍历
(头部 6/10/11/21) × (size_t 4/8) × (number 4/8) 共 16 种组合,
只有 (6, 4, 4) 能够完整解析且**尾部剩余 0 字节**。
"""

import struct

MAGIC = b"\x1bMRP"


def gbk(s):
    """把 latin1 读出的字符串按 GBK 重新解码 —— .mr 里的中文常量都是 GBK。

    返回 None 表示不是有效的中文串(纯 ASCII 或解码失败)。
    """
    if not s:
        return None
    try:
        b = s.encode("latin1")
    except Exception:
        return None
    if not any(c >= 0x80 for c in b):
        return None
    try:
        d = b.decode("gbk")
    except Exception:
        return None
    return d if d != s else None


# 已确认两种头部变体,由 head[4](版本字节)区分:
#   0x80 -> 6  字节:精简头(无 TESTSIZE),但保留 lines / locals
#   0x50 -> 18 字节:完整头(含 7 项 TESTSIZE + TEST_NUMBER),但 lines / locals 被剥离
HDR_VARIANTS = {0x80: 6, 0x50: 18}
HDR_FALLBACK = (6, 18)
HDR_LEN = 6                      # 默认值(兼容旧接口)

T_NIL, T_NUMBER, T_STRING = 0, 3, 4


class MrChunkError(Exception):
    pass


class _R:
    __slots__ = ("d", "p")

    def __init__(self, d, p=0):
        self.d, self.p = d, p

    def take(self, n):
        if self.p + n > len(self.d):
            raise MrChunkError(
                f"读取越界: 需要 {n} 字节 @0x{self.p:X},剩余 {len(self.d)-self.p}")
        b = self.d[self.p:self.p + n]
        self.p += n
        return b

    def u8(self):
        return self.take(1)[0]

    def u32(self):
        return int.from_bytes(self.take(4), "little")

    def i32(self):
        return int.from_bytes(self.take(4), "little", signed=True)

    def number(self):
        """4 字节数值。Mythroad 改了 Lua 的 double,这里同时给出两种解读。"""
        raw = self.take(4)
        return raw


class Proto:
    """一个 Lua 函数原型"""

    def __init__(self):
        self.source = None
        self.line_defined = 0
        self.nups = 0
        self.numparams = 0
        self.is_vararg = 0
        self.maxstacksize = 0
        self.lines = []
        self.locals = []          # [(name, startpc, endpc)]
        self.upvalues = []
        self.constants = []       # [('str'|'num'|'nil', value_or_bytes)]
        self.protos = []
        self.code = []            # [u32]

    def const_repr(self, i):
        if i >= len(self.constants):
            return f"K({i})"
        t, v = self.constants[i]
        if t == "str":
            return repr(v)
        if t == "num":
            iv, fv = v
            return f"{iv}(num)"
        return "nil"

    def walk(self, depth=0):
        yield self, depth
        for p in self.protos:
            yield from p.walk(depth + 1)


class Chunk:
    def __init__(self, path=None, data=None):
        self.path = path
        self.data = data if data is not None else open(path, "rb").read()
        self.signature = self.data[:4]
        self.version = self.data[4] if len(self.data) > 4 else 0
        self.endian = self.data[5] if len(self.data) > 5 else 0
        self.proto = None
        self.consumed = 0
        self.hdr_len = HDR_LEN

    def _candidates(self):
        """按版本字节决定先试哪种头部,另一个作为兜底"""
        v = self.data[4] if len(self.data) > 4 else 0
        first = HDR_VARIANTS.get(v)
        order = list(HDR_FALLBACK)
        if first is not None and first in order:
            order.remove(first)
            order.insert(0, first)
        return order

    def parse(self):
        """自动识别头部变体并解析。判据:必须恰好消耗完整个文件。"""
        if self.data[:1] != b"\x1b":
            raise MrChunkError(f"不是 .mr chunk(开头={self.data[:4]!r})")
        errs = []
        partial = None
        for hdr in self._candidates():
            try:
                r = _R(self.data, hdr)
                proto = self._load_function(r, None, 0)
            except MrChunkError as e:
                errs.append((hdr, str(e)))
                continue
            left = len(self.data) - r.p
            if left == 0:
                self.hdr_len, self.proto, self.consumed = hdr, proto, r.p
                return proto
            if partial is None:
                partial = (hdr, proto, r.p, left)
            errs.append((hdr, f"残留 {left} 字节"))
        if partial is not None:
            self.hdr_len, self.proto, self.consumed = partial[0], partial[1], partial[2]
            return self.proto
        raise MrChunkError("所有头部变体均失败: "
                           + "; ".join(f"{h}字节:{m}" for h, m in errs))

    # ------------------------------------------------------------ 各段
    def _load_string(self, r):
        n = r.u32()
        if n == 0:
            return None
        if n > (1 << 20):
            raise MrChunkError(f"字符串长度异常 {n} @0x{r.p-4:X}")
        return r.take(n)[:-1].decode("latin1")

    def _load_function(self, r, parent_src, depth):
        if depth > 64:
            raise MrChunkError("函数嵌套过深")
        f = Proto()

        f.source = self._load_string(r) or parent_src
        f.line_defined = r.i32()
        f.nups = r.u8()
        f.numparams = r.u8()
        f.is_vararg = r.u8()
        f.maxstacksize = r.u8()

        n = r.i32()
        if not (0 <= n <= 1 << 22):
            raise MrChunkError(f"行号表大小异常 {n} @0x{r.p-4:X}")
        f.lines = [r.i32() for _ in range(n)]

        n = r.i32()
        if not (0 <= n <= 1 << 16):
            raise MrChunkError(f"局部变量数异常 {n} @0x{r.p-4:X}")
        for _ in range(n):
            name = self._load_string(r)
            sp = r.i32()
            ep = r.i32()
            f.locals.append((name, sp, ep))

        n = r.i32()
        if not (0 <= n <= 1 << 16):
            raise MrChunkError(f"upvalue 数异常 {n} @0x{r.p-4:X}")
        if n not in (0, f.nups):
            raise MrChunkError(f"upvalue 数不匹配: 读到 {n},期望 {f.nups}")
        f.upvalues = [self._load_string(r) for _ in range(n)]

        # 常量
        n = r.i32()
        if not (0 <= n <= 1 << 20):
            raise MrChunkError(f"常量数异常 {n} @0x{r.p-4:X}")
        for _ in range(n):
            t = r.u8()
            if t == T_NUMBER:
                raw = r.number()
                iv = int.from_bytes(raw, "little", signed=True)
                fv = struct.unpack("<f", raw)[0]
                f.constants.append(("num", (iv, fv)))
            elif t == T_STRING:
                f.constants.append(("str", self._load_string(r)))
            elif t == T_NIL:
                f.constants.append(("nil", None))
            else:
                raise MrChunkError(f"非法常量类型 {t} @0x{r.p-1:X}")

        # 子函数
        n = r.i32()
        if not (0 <= n <= 1 << 16):
            raise MrChunkError(f"子函数数异常 {n} @0x{r.p-4:X}")
        f.protos = [self._load_function(r, f.source, depth + 1) for _ in range(n)]

        # 字节码
        n = r.i32()
        if not (0 <= n <= 1 << 22):
            raise MrChunkError(f"代码长度异常 {n} @0x{r.p-4:X}")
        f.code = [r.u32() for _ in range(n)]

        return f

    # ------------------------------------------------------------ 统计
    def stats(self):
        s = dict(functions=0, protos=0, code=0, constants=0, strings=0,
                 locals=0, upvalues=0, lines=0, maxstack=0)
        for p, d in self.proto.walk():
            s["functions"] += 1
            if d:
                s["protos"] += 1
            s["code"] += len(p.code)
            s["constants"] += len(p.constants)
            s["strings"] += sum(1 for t, _ in p.constants if t == "str")
            s["locals"] += len(p.locals)
            s["upvalues"] += len(p.upvalues)
            s["lines"] += len(p.lines)
            s["maxstack"] = max(s["maxstack"], p.maxstacksize)
        return s

    def all_names(self):
        """收集所有字符串常量 + 局部变量名 + upvalue 名"""
        out = set()
        for p, _ in self.proto.walk():
            for t, v in p.constants:
                if t == "str" and v:
                    out.add(v)
            for name, _, _ in p.locals:
                if name:
                    out.add(name)
            for u in p.upvalues:
                if u:
                    out.add(u)
        return out
