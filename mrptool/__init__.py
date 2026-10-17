# -*- coding: utf-8 -*-
"""
mrptool —— 斯凯 MRP / Mythroad 平台 (.mrp / .mr / .ext) 逆向工具

    导出:  from mrptool import MrpFile, Chunk
"""

__version__ = "0.1.0"
__all__ = ["MrpFile", "Entry", "Block", "MrpError",
           "Chunk", "Proto", "MrChunkError",
           "disassemble", "Instr", "OPNAMES"]

from .package import MrpFile, Entry, Block, MrpError
from .chunk import Chunk, Proto, MrChunkError
from .disasm import disassemble
from .opcodes import Instr, OPNAMES
