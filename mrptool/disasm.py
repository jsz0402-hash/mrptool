# -*- coding: utf-8 -*-
"""把 Lua 5.0 chunk 反汇编成可读伪代码"""

from .opcodes import Instr
from .chunk import gbk


def disasm_proto(p, depth=0, max_insns=None):
    """反汇编单个 Proto,返回文本行列表"""
    ind = "  " * depth
    L = []
    a = L.append

    src = p.source or "?"
    a(f"{ind}function <{src}:{p.line_defined}>   "
      f"params={p.numparams} vararg={p.is_vararg} "
      f"maxstack={p.maxstacksize} nups={p.nups} "
      f"insns={len(p.code)} consts={len(p.constants)} protos={len(p.protos)}")
    if p.locals:
        a(f"{ind}  locals: " + ", ".join(n or "?" for n, _, _ in p.locals))
    if p.upvalues:
        a(f"{ind}  upvals: " + ", ".join(u or "?" for u in p.upvalues))

    # 常量
    strs = [(i, v) for i, (t, v) in enumerate(p.constants) if t == "str"]
    nums = [(i, v) for i, (t, v) in enumerate(p.constants) if t == "num"]
    if strs:
        a(f"{ind}  strings:")
        for i, v in strs:
            cn = gbk(v)
            extra = f"   -> GBK: {cn}" if cn else ""
            a(f"{ind}    K[{i:<3}] = {v!r}{extra}")
    if nums:
        a(f"{ind}  numbers (4字节原始值):")
        for i, (iv, fv) in nums:
            a(f"{ind}    K[{i:<3}] = {iv}")

    # 字节码
    a(f"{ind}  code:")
    n = len(p.code)
    limit = n if max_insns is None else min(n, max_insns)
    for pc in range(limit):
        ins = Instr(p.code[pc])
        a(f"{ind}    {pc:>5}  {ins.name:<10} {ins.text(p.constants, p.protos)}")
        a(f"{ind}           ; raw=0x{ins.raw:08X}")
    if limit < n:
        a(f"{ind}    ... 还有 {n-limit} 条")

    for i, sub in enumerate(p.protos):
        a("")
        a(f"{ind}  -- 子函数 #{i} " + "-" * 40)
        L.extend(disasm_proto(sub, depth + 2, max_insns))
    return L


def disassemble(chunk, max_insns=None):
    return "\n".join(disasm_proto(chunk.proto, 0, max_insns))
