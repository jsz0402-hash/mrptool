# -*- coding: utf-8 -*-
"""
MRP 包 (.mrp) 解析器
====================
Mythroad Resources Pack —— 杭州斯凯网络功能机平台的应用包格式。

格式(逆向所得,在 6 个样本上验证):

    偏移    大小  说明
    ---------------------------------------------------------------
    0x00     4   魔数 "MRPG"
    0x04     4   u32 版本号
    0x08     4   u32 文件总大小
    0x0C     4   u32 头部长度(条目表起点),通常 0xF0
    0x10    12   应用名(截断到 12 字节)
    0x1C    12   应用名(完整,GBK)
    0x28    12   保留
    0x34    12   应用 ID
    0x40   176   其余元数据
    0xF0     -   条目表
                 每项: u32 namelen | char name[namelen] | u32 offset | u32 size | u32 flags
                 紧凑排列,无字节对齐
    数据区   -   一系列自描述块:
                 u32 namelen | char name[namelen] | u32 size | byte gzip[size]
"""

import os
import struct
import zlib

MAGIC = b"MRPG"
HDR_LEN = 0xF0


class MrpError(Exception):
    pass


class Entry:
    __slots__ = ("index", "name", "offset", "size", "flags", "_data")

    def __init__(self, index, name, offset, size, flags):
        self.index = index
        self.name = name
        self.offset = offset
        self.size = size
        self.flags = flags
        self._data = None

    def raw(self, blob):
        return blob[self.offset:self.offset + self.size]

    def data(self, blob):
        """取出并解压。gzip 优先,失败则原样返回。"""
        if self._data is not None:
            return self._data
        b = self.raw(blob)
        if b[:2] == b"\x1f\x8b":
            try:
                self._data = zlib.decompress(b, 16 + zlib.MAX_WBITS)
                return self._data
            except zlib.error:
                pass
        self._data = b
        return b

    @property
    def is_gzip(self):
        return self._data is not None and False  # 由调用方判断

    def __repr__(self):
        return f"<Entry#{self.index} {self.name!r} @0x{self.offset:X} {self.size}B>"


class Block:
    """数据区里的自描述块"""
    __slots__ = ("name", "offset", "size", "data_offset")

    def __init__(self, name, offset, size, data_offset):
        self.name = name
        self.offset = offset          # 块头起始
        self.size = size              # gzip 数据长度
        self.data_offset = data_offset  # gzip 数据起始


class MrpFile:
    def __init__(self, path=None, data=None):
        self.path = path
        self.data = data if data is not None else open(path, "rb").read()
        self.entries = []
        self.blocks = []
        self._parse()

    # ------------------------------------------------------------------
    def _parse(self):
        d = self.data
        if len(d) < HDR_LEN or d[:4] != MAGIC:
            raise MrpError(f"不是 MRP 包(魔数={d[:4]!r})")

        self.version, self.total_size, self.header_len = struct.unpack_from("<III", d, 4)

        def slot(i):
            raw = d[0x10 + 12 * i: 0x1C + 12 * i]
            return raw.split(b"\0")[0].decode("latin1")

        self.name_short = slot(0)
        self.name_full = slot(1)
        self.reserved = slot(2)
        self.app_id = slot(3)
        self.hdr_raw = d[0x40:HDR_LEN]

        # --- 条目表 ---
        pos = self.header_len
        idx = 0
        while pos + 4 <= len(d):
            namelen = struct.unpack_from("<I", d, pos)[0]
            if not (1 <= namelen <= 200):
                break
            nend = pos + 4 + namelen
            if nend + 12 > len(d):
                break
            nb = d[pos + 4:nend]
            if not nb.endswith(b"\0"):
                break
            off, size, flags = struct.unpack_from("<III", d, nend)
            if off == 0 or off + size > len(d) or off < self.header_len:
                break
            self.entries.append(
                Entry(idx, nb[:-1].decode("latin1"), off, size, flags))
            idx += 1
            pos = nend + 12
        self.table_end = pos

        # --- 数据区块(自描述) ---
        p = self.table_end
        while p + 8 <= len(d):
            namelen = struct.unpack_from("<I", d, p)[0]
            if not (1 <= namelen <= 200):
                break
            nend = p + 4 + namelen
            if nend + 4 > len(d):
                break
            nb = d[p + 4:nend]
            if not nb.endswith(b"\0"):
                break
            size = struct.unpack_from("<I", d, nend)[0]
            dstart = nend + 4
            if size == 0 or dstart + size > len(d):
                break
            self.blocks.append(
                Block(nb[:-1].decode("latin1"), p, size, dstart))
            p = dstart + size
        self.data_end = p

    # ------------------------------------------------------------------
    @property
    def app_name_gbk(self):
        try:
            return self.name_full.encode("latin1").decode("gbk")
        except Exception:
            return self.name_full

    def consistent(self):
        """条目表 与 数据区块 是否一一对应"""
        if len(self.entries) != len(self.blocks):
            return False
        for e, b in zip(self.entries, self.blocks):
            if e.name != b.name or e.size != b.size or e.offset != b.data_offset:
                return False
        return True

    def gaps(self):
        out, cur = [], self.table_end
        for e in sorted(self.entries, key=lambda x: x.offset):
            if e.offset > cur:
                out.append((cur, e.offset - cur))
            cur = max(cur, e.offset + e.size)
        if cur < len(self.data):
            out.append((cur, len(self.data) - cur))
        return out

    def stats(self):
        return dict(entries=len(self.entries), blocks=len(self.blocks),
                    total=len(self.data), header=self.header_len,
                    tabled_end=self.table_end, data_end=self.data_end)

    def extract_to(self, outdir, prefix=""):
        """把所有条目解压导出到目录"""
        os.makedirs(outdir, exist_ok=True)
        result = []
        for e in self.entries:
            d = e.data(self.data)
            safe = "".join(c if c.isalnum() or c in "._-" else "_" for c in e.name)
            fn = f"{prefix}{e.index:02d}_{safe}"
            p = os.path.join(outdir, fn)
            with open(p, "wb") as f:
                f.write(d)
            result.append((e.name, p, len(d)))
        return result
