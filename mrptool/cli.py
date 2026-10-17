# -*- coding: utf-8 -*-
"""mrptool 命令行界面"""

import argparse
import os
import sys

from .package import MrpFile, MrpError
from .chunk import Chunk, MrChunkError
from .disasm import disassemble


def _fix_console():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def _hr(c="=", n=76):
    print(c * n)


# ----------------------------------------------------------------- info
def cmd_info(args):
    m = MrpFile(args.file)
    s = m.stats()
    _hr()
    print(f"  MRP 包: {os.path.basename(args.file)}")
    _hr()
    print(f"  魔数          {m.data[:4]!r}")
    print(f"  版本          {m.version}  (0x{m.version:X})")
    ok = "✓ 一致" if m.total_size == len(m.data) else f"✗ 不一致(实际 {len(m.data)})"
    print(f"  声明大小      {m.total_size:,}   {ok}")
    print(f"  头部长度      {m.header_len}  (0x{m.header_len:X})")
    print(f"  应用名(短)    {m.name_short!r}")
    print(f"  应用名(全)    {m.name_full!r}   -> GBK: {m.app_name_gbk}")
    print(f"  应用 ID       {m.app_id!r}")
    print(f"  条目表        {s['entries']} 项,结束于 0x{s['tabled_end']:X}")
    print(f"  数据区块      {s['blocks']} 个,结束于 0x{s['data_end']:X}")
    print(f"  条目/区块一致 {'✓ 是' if m.consistent() else '✗ 否'}")
    g = m.gaps()
    if g:
        print(f"  未索引区域    {len(g)} 处:")
        for off, ln in g[:8]:
            print(f"                  0x{off:X}  {ln} 字节")
    else:
        print(f"  未索引区域    无(无缝覆盖)")
    print()
    print(f"  {'#':>3}  {'名称':<22} {'偏移':>10} {'压缩':>10} {'解压':>10}  类型")
    _hr("-")
    for e in m.entries:
        d = e.data(m.data)
        kind = "gzip" if e.raw(m.data)[:2] == b"\x1f\x8b" else "raw "
        print(f"  {e.index:>3}  {e.name:<22} {e.offset:>10,} {e.size:>10,} "
              f"{len(d):>10,}  {kind} {_kind(e.name, d)}")
    print()


def _kind(name, d):
    n = name.lower()
    if n.endswith(".bmp") and d[:2] == b"BM":
        import struct as _s
        try:
            w, h = _s.unpack_from("<ii", d, 18)
            bpp = _s.unpack_from("<H", d, 28)[0]
            return f"BMP {w}x{h}x{bpp}"
        except Exception:
            return "BMP"
    if n.endswith(".ext"):
        return "ARM32 代码 (CMAP)" if d[:4] == b"MRPG" else "二进制"
    if n.endswith(".mr"):
        return "Lua 5.0 字节码" if d[:1] == b"\x1b" else "二进制"
    if n.endswith(".tsf"):
        return "点阵字库"
    if n.endswith(".uc2"):
        return "字库"
    return ""


# ---------------------------------------------------------------- list
def cmd_list(args):
    m = MrpFile(args.file)
    for e in m.entries:
        print(f"{e.index}\t{e.name}\t{e.offset}\t{e.size}")


# ------------------------------------------------------------- extract
def cmd_extract(args):
    m = MrpFile(args.file)
    out = args.out or (os.path.splitext(os.path.basename(args.file))[0] + "_out")
    res = m.extract_to(out, args.prefix or "")
    print(f"已导出 {len(res)} 个文件到 {out}")
    for name, p, n in res:
        print(f"  {name:<24} {n:>10,}  ->  {os.path.basename(p)}")


# -------------------------------------------------------------- disasm
def cmd_disasm(args):
    data = open(args.file, "rb").read()
    c = Chunk(args.file, data)
    c.parse()
    st = c.stats()
    _hr()
    print(f"  {os.path.basename(args.file)}   {len(data):,} 字节")
    print(f"  签名 {c.signature!r}  版本 0x{c.version:X}  端序 {c.endian}")
    print(f"  头部 {c.hdr_len} 字节  "
          f"({'完整头' if c.hdr_len == 18 else '精简头'})")
    print(f"  消耗 {c.consumed:,} / {len(data):,} 字节  "
          f"{'✓ 完全解析' if c.consumed == len(data) else '⚠ 有剩余'}")
    print(f"  {st}")
    _hr()
    print()
    print(disassemble(c, args.max_insns))


# ---------------------------------------------------------------- dump
def cmd_dump(args):
    m = MrpFile(args.file)
    base = args.out or (os.path.splitext(os.path.basename(args.file))[0] + "_dump")
    os.makedirs(base, exist_ok=True)
    res = m.extract_to(os.path.join(base, "files"), "")

    report = []
    report.append(f"# {os.path.basename(args.file)}  转储报告\n")
    report.append(f"- 应用名: {m.app_name_gbk}")
    report.append(f"- 版本: {m.version}  大小: {len(m.data):,} 字节")
    report.append(f"- 条目: {len(m.entries)}  区块: {len(m.blocks)}  "
                  f"一致: {m.consistent()}\n")

    ok = fail = 0
    for e in m.entries:
        d = e.data(m.data)
        report.append(f"## {e.name}  ({len(d):,} 字节)\n")
        if e.name.lower().endswith(".mr") and d[:1] == b"\x1b":
            try:
                c = Chunk(e.name, d)
                c.parse()
                st = c.stats()
                ok += 1
                report.append(f"Lua 5.0 chunk —— 消耗 {c.consumed:,}/{len(d):,} "
                              f"{'✓' if c.consumed == len(d) else '⚠'}")
                report.append(f"```\n{st}\n```\n")
                report.append(f"符号: {', '.join(sorted(c.all_names()))}\n")
                report.append("```lua\n" + disassemble(c, 200) + "\n```\n")
            except MrChunkError as ex:
                fail += 1
                report.append(f"解析失败: {ex}\n")
        else:
            report.append("```\n" + _hexdump(d, 128) + "\n```\n")

    txt = "\n".join(report)
    rp = os.path.join(base, "REPORT.md")
    open(rp, "w", encoding="utf-8").write(txt)
    print(f"导出 {len(res)} 个文件 -> {os.path.join(base,'files')}")
    print(f".mr 解析: 成功 {ok}, 失败 {fail}")
    print(f"报告 -> {rp}")


def _hexdump(d, n=128):
    out = []
    for i in range(0, min(n, len(d)), 16):
        c = d[i:i + 16]
        out.append(f"{i:06X}  " + " ".join(f"{b:02X}" for b in c).ljust(48) + "  " +
                   "".join(chr(b) if 32 <= b < 127 else "." for b in c))
    return "\n".join(out)


# ----------------------------------------------------------------- cli
def main(argv=None):
    _fix_console()
    ap = argparse.ArgumentParser(
        prog="mrptool",
        description="斯凯 MRP / Mythroad 平台逆向工具")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("info", help="显示 .mrp 包结构")
    p.add_argument("file"); p.set_defaults(func=cmd_info)

    p = sub.add_parser("list", help="列出条目(TSV)")
    p.add_argument("file"); p.set_defaults(func=cmd_list)

    p = sub.add_parser("extract", help="解包")
    p.add_argument("file"); p.add_argument("-o", "--out")
    p.add_argument("--prefix", default="")
    p.set_defaults(func=cmd_extract)

    p = sub.add_parser("disasm", help="反汇编 .mr (Lua 5.0 chunk)")
    p.add_argument("file"); p.add_argument("-n", "--max-insns", type=int, default=None)
    p.set_defaults(func=cmd_disasm)

    p = sub.add_parser("dump", help="全流程:解包 + 反汇编 + 报告")
    p.add_argument("file"); p.add_argument("-o", "--out")
    p.set_defaults(func=cmd_dump)

    args = ap.parse_args(argv)
    try:
        return args.func(args) or 0
    except (MrpError, MrChunkError) as e:
        print(f"错误: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
