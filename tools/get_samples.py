#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
下载 MRP 测试样本
=================
样本来自 [vmrp](https://github.com/vmrp) 公开的两个仓库:

  - vmrp/mythroad   —— 24 个 .mrp(作者原话:"老硬盘里翻出来的东西")
  - vmrp/vmrp_arm   —— 10 个 .mrp

因为版权原因,本仓库不直接分发这些第三方样本。
运行本脚本可自行下载到 samples/ 目录。

用法:
    python tools/get_samples.py [输出目录]
"""
import base64
import json
import os
import sys
import time
import urllib.parse
import urllib.request

REPOS = ["vmrp/mythroad", "vmrp/vmrp_arm"]
UA = {"User-Agent": "mrptool-sample-fetcher"}


def _get(url, timeout=45):
    req = urllib.request.Request(url, headers=dict(UA, Accept="application/vnd.github+json"))
    with urllib.request.urlopen(req, timeout=timeout) as f:
        return f.read()


def list_mrp(repo):
    data = json.loads(_get(
        f"https://api.github.com/repos/{repo}/git/trees/master?recursive=1"))
    return [x["path"] for x in data.get("tree", [])
            if x["type"] == "blob" and x["path"].lower().endswith(".mrp")]


def fetch(repo, path):
    """先试 raw,失败再用 API(带 base64)"""
    try:
        url = (f"https://raw.githubusercontent.com/{repo}/master/"
               + urllib.parse.quote(path))
        return _get(url, timeout=90)
    except Exception:
        pass
    url = (f"https://api.github.com/repos/{repo}/contents/"
           + urllib.parse.quote(path))
    j = json.loads(_get(url))
    return base64.b64decode(j["content"])


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "samples")
    os.makedirs(out, exist_ok=True)
    print(f"输出目录: {out}\n")

    targets = []
    for repo in REPOS:
        try:
            paths = list_mrp(repo)
            print(f"  {repo}: {len(paths)} 个 .mrp")
            targets += [(repo, p) for p in paths]
        except Exception as e:
            print(f"  {repo}: 列举失败 —— {e}")

    print(f"\n共 {len(targets)} 个待下载\n")
    ok = skip = fail = 0
    for repo, path in targets:
        name = path.replace("/", "__")
        dest = os.path.join(out, name)
        if os.path.exists(dest) and os.path.getsize(dest) > 0:
            skip += 1
            continue
        for attempt in (1, 2):
            try:
                d = fetch(repo, path)
                if d[:4] != b"MRPG":
                    raise ValueError(f"魔数不对: {d[:4]!r}")
                open(dest, "wb").write(d)
                print(f"  [OK]   {name:<38} {len(d):>9,} 字节")
                ok += 1
                break
            except Exception as e:
                if attempt == 2:
                    print(f"  [FAIL] {name:<38} {str(e)[:50]}")
                    fail += 1
                else:
                    time.sleep(1.0)
        time.sleep(0.2)

    print(f"\n完成: 新下载 {ok}, 已存在 {skip}, 失败 {fail}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
