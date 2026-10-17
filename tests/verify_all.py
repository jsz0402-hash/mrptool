#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mrptool 全量验证
----------------
对样本目录下所有 .mrp 跑完整流程,统计:
  1. 包结构解析成功率
  2. 条目表 / 数据区块 交叉一致性
  3. .mr 作为 Lua 5.0 chunk 的解析成功率(判据:消耗字节数 == 文件大小)
  4. 各类条目数量分布
"""
import os
import sys
import glob

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from mrptool import MrpFile, Chunk, MrpError, MrChunkError

SAMPLES = sys.argv[1] if len(sys.argv) > 1 else r"H:\work\mrp\samples"


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    files = sorted(glob.glob(os.path.join(SAMPLES, "*.mrp")))
    if not files:
        print(f"没找到 .mrp 文件: {SAMPLES}")
        return 1

    print("=" * 84)
    print(f"  mrptool 全量验证 —— {len(files)} 个样本")
    print("=" * 84)
    print()

    tot = dict(pkg_ok=0, pkg_fail=0, consistent=0, entries=0,
               mr_ok=0, mr_fail=0, ext=0, bmp=0, other=0, nested=0)

    rows = []
    for p in files:
        name = os.path.basename(p)
        try:
            m = MrpFile(p)
        except Exception as e:
            tot["pkg_fail"] += 1
            rows.append((name, "包解析失败", str(e)[:40], "", "", ""))
            print(f"  [FAIL] {name}: {e}")
            continue

        tot["pkg_ok"] += 1
        cons = m.consistent()
        if cons:
            tot["consistent"] += 1
        tot["entries"] += len(m.entries)

        n_mr = n_mr_ok = n_ext = n_bmp = n_other = n_nested = 0
        mr_left = []
        for e in m.entries:
            try:
                d = e.data(m.data)
            except Exception:
                n_other += 1
                continue
            low = e.name.lower()
            if low.endswith(".mr"):
                n_mr += 1
                try:
                    c = Chunk(e.name, d)
                    c.parse()
                    if c.consumed == len(d):
                        n_mr_ok += 1
                    else:
                        mr_left.append((e.name, len(d) - c.consumed))
                except MrChunkError as ex:
                    mr_left.append((e.name, f"err:{str(ex)[:24]}"))
            elif low.endswith(".ext"):
                n_ext += 1 if d[:4] == b"MRPG" else 0
                if d[:4] != b"MRPG":
                    n_other += 1
            elif low.endswith(".bmp"):
                n_bmp += 1
            elif low.endswith(".mrp"):
                n_nested += 1
            else:
                n_other += 1

        tot["mr_ok"] += n_mr_ok
        tot["mr_fail"] += (n_mr - n_mr_ok)
        tot["ext"] += n_ext
        tot["bmp"] += n_bmp
        tot["nested"] += n_nested
        tot["other"] += n_other

        rows.append((name, len(m.entries), "✓" if cons else "✗",
                     f"{n_mr_ok}/{n_mr}", str(n_ext), str(n_bmp)))
        if mr_left:
            for nm, info in mr_left[:3]:
                print(f"  [!] {name} :: {nm}  残留={info}")

    print()
    print(f"  {'样本':<32} {'条目':>5} {'一致':>5} {'mr ok':>7} {'ext':>5} {'bmp':>5}")
    print("  " + "-" * 70)
    for r in rows:
        if len(r) == 6:
            nm, ne, cs, mr, ex, bm = r
            print(f"  {nm[:32]:<32} {str(ne):>5} {cs:>5} {mr:>7} {ex:>5} {bm:>5}")
        else:
            print(f"  {r[0][:32]:<32} {r[1]}")

    print()
    print("=" * 84)
    print("  总计")
    print("=" * 84)
    print(f"  包解析成功        {tot['pkg_ok']} / {len(files)}")
    print(f"  条目/区块一致     {tot['consistent']} / {tot['pkg_ok']}")
    print(f"  条目总数          {tot['entries']}")
    print(f"  .mr 解析成功      {tot['mr_ok']} / {tot['mr_ok'] + tot['mr_fail']}"
          f"   (判据: 消耗字节 == 文件大小)")
    print(f"  .ext (ARM32)      {tot['ext']}")
    print(f"  .bmp              {tot['bmp']}")
    print(f"  嵌套 .mrp         {tot['nested']}")
    print(f"  其它              {tot['other']}")
    print()
    total_mr = tot["mr_ok"] + tot["mr_fail"]
    if total_mr and tot["mr_ok"] == total_mr:
        print("  ✅ 全部 .mr 文件均按 Lua 5.0 chunk 完整解析,无残留字节")
    elif total_mr:
        print(f"  ⚠️  {tot['mr_fail']} 个 .mr 未能完整解析")
    return 0


if __name__ == "__main__":
    sys.exit(main())
