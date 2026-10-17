# -*- coding: utf-8 -*-
"""
mrptool 交互式界面 —— 双击「启动工具.bat」即可使用,无需记命令。
"""
import os
import sys
import traceback

from .package import MrpFile, MrpError
from .chunk import Chunk, MrChunkError
from .disasm import disassemble

LINE = "=" * 66


def _init():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stdin.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def _clean(p):
    """处理拖拽进来的路径:去引号、去首尾空格"""
    if not p:
        return ""
    p = p.strip().strip('"').strip("'").strip()
    return p


def _ask_file(prompt="把文件拖到这里,或输入路径:"):
    while True:
        p = _clean(input(f"\n  {prompt}\n  > "))
        if not p:
            return None
        if p.lower() in ("q", "quit", "exit", ":q"):
            return None
        if os.path.isfile(p):
            return p
        print(f"  ✗ 找不到文件: {p}")


def _ask_dir(defname):
    p = _clean(input(f"\n  输出目录(直接回车用默认 {defname}):\n  > "))
    return p or defname


def _pause():
    input("\n  按回车返回菜单...")


# ------------------------------------------------------------------ 1
def do_info():
    f = _ask_file("要查看的 .mrp 文件:")
    if not f:
        return
    try:
        print()
        print(LINE)
        print(f"  {os.path.basename(f)}")
        print(LINE)
        m = MrpFile(f)
        ok = "✓" if m.total_size == len(m.data) else "✗"
        print(f"  应用名        {m.app_name_gbk}")
        print(f"  版本          {m.version}   大小 {len(m.data):,} 字节 {ok}")
        print(f"  条目数        {len(m.entries)}")
        print(f"  索引一致性    {'✓ 两份索引完全吻合' if m.consistent() else '✗ 不一致'}")
        print()
        print(f"  {'#':>3}  {'名称':<24} {'压缩':>9} {'解压':>9}  类型")
        print("  " + "-" * 62)
        for e in m.entries:
            d = e.data(m.data)
            print(f"  {e.index:>3}  {e.name:<24} {e.size:>9,} {len(d):>9,}  {_kind(e.name, d)}")
    except Exception as ex:
        print(f"\n  ✗ 出错: {ex}")
    _pause()


def _kind(name, d):
    n = name.lower()
    if n.endswith(".bmp") and d[:2] == b"BM":
        return "BMP 图片"
    if n.endswith(".ext"):
        return "ARM32 代码" if d[:4] == b"MRPG" else "二进制"
    if n.endswith(".mr"):
        return "Lua 字节码" if d[:1] == b"\x1b" else "二进制"
    if n.endswith(".tsf"):
        return "点阵字库"
    return ""


# ------------------------------------------------------------------ 2
def do_extract():
    f = _ask_file("要解包的 .mrp 文件:")
    if not f:
        return
    out = _ask_dir(os.path.splitext(os.path.basename(f))[0] + "_解包")
    try:
        m = MrpFile(f)
        res = m.extract_to(out)
        print(f"\n  ✓ 已解出 {len(res)} 个文件到:")
        print(f"    {os.path.abspath(out)}\n")
        for name, p, n in res:
            print(f"    {name:<26} {n:>10,} 字节")
    except Exception as ex:
        print(f"\n  ✗ 出错: {ex}")
    _pause()


# ------------------------------------------------------------------ 3
def do_disasm():
    f = _ask_file("要反汇编的 .mr 文件(通常在解包目录里):")
    if not f:
        return
    try:
        data = open(f, "rb").read()
        c = Chunk(f, data)
        c.parse()
        print()
        print(LINE)
        print(f"  {os.path.basename(f)}   {len(data):,} 字节")
        print(f"  头部 {c.hdr_len} 字节({'完整头' if c.hdr_len == 18 else '精简头'})"
              f"   版本 0x{c.version:X}   消耗 {c.consumed:,}/{len(data):,}"
              f" {'✓' if c.consumed == len(data) else '⚠'}")
        print(LINE)
        print()
        txt = disassemble(c)
        # 太长就分段显示
        lines = txt.splitlines()
        if len(lines) > 400:
            print("\n".join(lines[:400]))
            print(f"\n  ...(共 {len(lines)} 行,已省略 {len(lines)-400} 行)")
            print("  想看完整版,请用菜单 4「全流程」,会输出到文件")
        else:
            print(txt)
    except Exception as ex:
        print(f"\n  ✗ 出错: {ex}")
    _pause()


# ------------------------------------------------------------------ 4
def do_dump():
    f = _ask_file("要处理的 .mrp 文件:")
    if not f:
        return
    out = _ask_dir(os.path.splitext(os.path.basename(f))[0] + "_转储")
    try:
        m = MrpFile(f)
        os.makedirs(out, exist_ok=True)
        files_dir = os.path.join(out, "files")
        res = m.extract_to(files_dir)

        rep = [f"# {os.path.basename(f)} 转储报告", "",
               f"- 应用名: {m.app_name_gbk}",
               f"- 版本: {m.version}   大小: {len(m.data):,} 字节",
               f"- 条目 {len(m.entries)} 个   索引一致: {m.consistent()}", ""]

        ok = fail = 0
        for e in m.entries:
            d = e.data(m.data)
            rep.append(f"## {e.name}  ({len(d):,} 字节)")
            if e.name.lower().endswith(".mr") and d[:1] == b"\x1b":
                try:
                    c = Chunk(e.name, d)
                    c.parse()
                    ok += 1
                    rep.append(f"Lua 5.0 chunk,头部 {c.hdr_len} 字节,"
                               f"消耗 {c.consumed:,}/{len(d):,}")
                    rep.append(f"```\n{c.stats()}\n```")
                    names = sorted(c.all_names())
                    if names:
                        rep.append("符号: " + ", ".join(names))
                    rep.append("```lua\n" + disassemble(c, 300) + "\n```")
                except MrChunkError as ex:
                    fail += 1
                    rep.append(f"解析失败: {ex}")
            rep.append("")

        rp = os.path.join(out, "报告.md")
        open(rp, "w", encoding="utf-8").write("\n".join(rep))
        print(f"\n  ✓ 完成")
        print(f"    解出文件  {len(res)} 个  ->  {os.path.abspath(files_dir)}")
        print(f"    .mr 解析  成功 {ok},失败 {fail}")
        print(f"    分析报告  ->  {os.path.abspath(rp)}")
        print(f"\n  (报告是 Markdown,用记事本或 VS Code 打开就能看)")
    except Exception as ex:
        print(f"\n  ✗ 出错: {ex}")
    _pause()


# ------------------------------------------------------------------ 5
def do_verify():
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    d = os.path.join(here, "samples")
    if not os.path.isdir(d):
        d = _ask_dir(os.getcwd())
    print(f"\n  正在验证 {d} ...\n")
    py = sys.executable
    script = os.path.join(here, "tests", "verify_all.py")
    if os.path.exists(script):
        os.system(f'"{py}" "{script}" "{d}"')
    else:
        print("  ✗ 找不到 tests/verify_all.py")
    _pause()


# ---------------------------------------------------------------- main
MENU = """
{line}
   mrptool  ——  斯凯 MRP / Mythroad 逆向工具
   那些 299 块山寨机上的记忆
{line}

   1. 查看 .mrp 包结构      (先看这个,认识一下文件里有什么)
   2. 解包                  (.mrp  ->  一堆文件)
   3. 反汇编 .mr            (看懂里面的 Lua 代码)
   4. 全流程 + 生成报告     (推荐:解包并分析,输出可阅读的报告)
   5. 批量验证样本          (跑一遍自带样本,确认工具正常)
   0. 退出
"""


def main():
    _init()
    while True:
        print(MENU.format(line=LINE))
        c = input("  请输入数字并回车 > ").strip()
        print()
        if c == "0" or c.lower() in ("q", "quit", "exit"):
            print("  再见。\n")
            return 0
        elif c == "1":
            do_info()
        elif c == "2":
            do_extract()
        elif c == "3":
            do_disasm()
        elif c == "4":
            do_dump()
        elif c == "5":
            do_verify()
        else:
            print("  请输入 0-5 之间的数字")
            _pause()
        os.system("cls")


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (KeyboardInterrupt, EOFError):
        print("\n  已退出。\n")
        sys.exit(0)
