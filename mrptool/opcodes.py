# -*- coding: utf-8 -*-
"""
Lua 5.0.2 指令集定义 —— 逐字对照官方 lopcodes.h / lopcodes.c

    #define SIZE_OP 6      #define SIZE_A  8
    #define SIZE_B  9      #define SIZE_C  9
    #define POS_C  SIZE_OP              (= 6)
    #define POS_B  (POS_C + SIZE_C)     (= 15)
    #define POS_A  (POS_B + SIZE_B)     (= 24)

    位布局:  A[24:32] | B[15:24] | C[6:15] | op[0:6]
"""

SIZE_OP, SIZE_A, SIZE_B, SIZE_C = 6, 8, 9, 9
POS_C = SIZE_OP                 # 6
POS_B = POS_C + SIZE_C          # 15
POS_A = POS_B + SIZE_B          # 24
POS_Bx = POS_C                  # 6
SIZE_Bx = SIZE_B + SIZE_C       # 18

MAXARG_A = (1 << SIZE_A) - 1
MAXARG_B = (1 << SIZE_B) - 1
MAXARG_C = (1 << SIZE_C) - 1
MAXARG_Bx = (1 << SIZE_Bx) - 1
MAXARG_sBx = MAXARG_Bx >> 1

# 逐字来自官方 lopcodes.c :: luaP_opnames[]
OPNAMES = [
    "MOVE", "LOADK", "LOADBOOL", "LOADNIL", "GETUPVAL",
    "GETGLOBAL", "GETTABLE",
    "SETGLOBAL", "SETUPVAL", "SETTABLE",
    "NEWTABLE",
    "SELF",
    "ADD", "SUB", "MUL", "DIV", "POW", "UNM", "NOT",
    "CONCAT",
    "JMP",
    "EQ", "LT", "LE",
    "TEST",
    "CALL", "TAILCALL", "RETURN",
    "FORLOOP",
    "TFORLOOP", "TFORPREP",
    "SETLIST", "SETLISTO",
    "CLOSE", "CLOSURE",
]
NUM_OPCODES = len(OPNAMES)

# 逐字来自官方 lopcodes.h :: OpCode enum 的注释
OPDESC = {
    "MOVE":      "A B   R(A) := R(B)",
    "LOADK":     "A Bx  R(A) := Kst(Bx)",
    "LOADBOOL":  "A B C R(A) := (Bool)B; if (C) PC++",
    "LOADNIL":   "A B   R(A) := ... := R(B) := nil",
    "GETUPVAL":  "A B   R(A) := UpValue[B]",
    "GETGLOBAL": "A Bx  R(A) := Gbl[Kst(Bx)]",
    "GETTABLE":  "A B C R(A) := R(B)[RK(C)]",
    "SETGLOBAL": "A Bx  Gbl[Kst(Bx)] := R(A)",
    "SETUPVAL":  "A B   UpValue[B] := R(A)",
    "SETTABLE":  "A B C R(A)[RK(B)] := RK(C)",
    "NEWTABLE":  "A B C R(A) := {} (size = B,C)",
    "SELF":      "A B C R(A+1) := R(B); R(A) := R(B)[RK(C)]",
    "ADD":       "A B C R(A) := RK(B) + RK(C)",
    "SUB":       "A B C R(A) := RK(B) - RK(C)",
    "MUL":       "A B C R(A) := RK(B) * RK(C)",
    "DIV":       "A B C R(A) := RK(B) / RK(C)",
    "POW":       "A B C R(A) := RK(B) ^ RK(C)",
    "UNM":       "A B   R(A) := -R(B)",
    "NOT":       "A B   R(A) := not R(B)",
    "CONCAT":    "A B C R(A) := R(B).. ... ..R(C)",
    "JMP":       "sBx   PC += sBx",
    "EQ":        "A B C if ((RK(B) == RK(C)) ~= A) then pc++",
    "LT":        "A B C if ((RK(B) <  RK(C)) ~= A) then pc++",
    "LE":        "A B C if ((RK(B) <= RK(C)) ~= A) then pc++",
    "TEST":      "A B C if (R(B) <=> C) then R(A) := R(B) else pc++",
    "CALL":      "A B C R(A),...,R(A+C-2) := R(A)(R(A+1),...,R(A+B-1))",
    "TAILCALL":  "A B C return R(A)(R(A+1),...,R(A+B-1))",
    "RETURN":    "A B   return R(A),...,R(A+B-2)",
    "FORLOOP":   "A sBx R(A)+=R(A+2); if R(A) <?= R(A+1) then PC += sBx",
    "TFORLOOP":  "A C   R(A+2),... := R(A)(R(A+1),R(A+2)); if R(A+2)~=nil then pc++",
    "TFORPREP":  "A sBx if type(R(A))==table then R(A+1):=R(A), R(A):=next; PC+=sBx",
    "SETLIST":   "A Bx  R(A)[Bx-Bx%FPF+i] := R(A+i), 1 <= i <= Bx%FPF+1",
    "SETLISTO":  "A Bx",
    "CLOSE":     "A     close all variables in the stack up to (>=) R(A)",
    "CLOSURE":   "A Bx  R(A) := closure(KPROTO[Bx], R(A),...,R(A+n))",
}

# RK 编码:C 的第 8 位(值 256)是常量标志
def is_k(x):
    return (x & 0x100) != 0


def rk_str(x):
    """把 RK(B)/RK(C) 渲染成可读形式"""
    return f"K({x & 0xFF})" if is_k(x) else f"R({x})"


class Instr:
    """一条解码后的指令"""
    __slots__ = ("raw", "op", "A", "B", "C", "Bx", "sBx")

    def __init__(self, raw):
        self.raw = raw
        self.op = raw & ((1 << SIZE_OP) - 1)
        self.A = (raw >> POS_A) & MAXARG_A
        self.B = (raw >> POS_B) & MAXARG_B
        self.C = (raw >> POS_C) & MAXARG_C
        self.Bx = (raw >> POS_Bx) & MAXARG_Bx
        self.sBx = self.Bx - MAXARG_sBx

    @property
    def name(self):
        return OPNAMES[self.op] if self.op < NUM_OPCODES else f"OP_{self.op}"

    def text(self, k=None, protos=None):
        """渲染成可读的伪代码;k 是常量表,protos 是子函数列表"""
        n = self.name
        A = self.A
        if n in ("MOVE", "UNM", "NOT"):
            return f"R({A}) := {'-' if n=='UNM' else 'not ' if n=='NOT' else ''}R({self.B})"
        if n == "LOADK":
            return f"R({A}) := {self._k(self.Bx, k)}"
        if n == "LOADBOOL":
            return f"R({A}) := {bool(self.B)}" + ("  (skip next)" if self.C else "")
        if n == "LOADNIL":
            return f"R({A})..R({self.B}) := nil"
        if n == "GETUPVAL":
            return f"R({A}) := Upval[{self.B}]"
        if n == "GETGLOBAL":
            return f"R({A}) := _G[{self._k(self.Bx, k)}]"
        if n == "GETTABLE":
            return f"R({A}) := R({self.B})[{rk_str(self.C)}]"
        if n == "SETGLOBAL":
            return f"_G[{self._k(self.Bx, k)}] := R({A})"
        if n == "SETUPVAL":
            return f"Upval[{self.B}] := R({A})"
        if n == "SETTABLE":
            return f"R({A})[{rk_str(self.B)}] := {rk_str(self.C)}"
        if n == "NEWTABLE":
            return f"R({A}) := {{}}  array={self.B} hash={self.C}"
        if n == "SELF":
            return f"R({A+1}) := R({self.B}); R({A}) := R({self.B})[{rk_str(self.C)}]"
        if n in ("ADD", "SUB", "MUL", "DIV", "POW"):
            sym = {"ADD": "+", "SUB": "-", "MUL": "*", "DIV": "/", "POW": "^"}[n]
            return f"R({A}) := {rk_str(self.B)} {sym} {rk_str(self.C)}"
        if n == "CONCAT":
            return f"R({A}) := R({self.B}) .. ... .. R({self.C})"
        if n == "JMP":
            return f"pc += {self.sBx}"
        if n in ("EQ", "LT", "LE"):
            sym = {"EQ": "==", "LT": "<", "LE": "<="}[n]
            inv = "if not " if self.A else "if "
            return f"{inv}({rk_str(self.B)} {sym} {rk_str(self.C)}) then pc++"
        if n == "TEST":
            return f"if R({self.B}) {'is truthy' if self.C else 'is falsy'} then R({A}) := R({self.B}) else pc++"
        if n == "CALL":
            nb = "top" if self.B == 0 else str(self.B - 1)
            nc = "top" if self.C == 0 else str(self.C - 1)
            return f"R({A})..R({A+self.C-1}) := R({A})({nb} args) -> {nc} results"
        if n == "TAILCALL":
            return f"return R({A})({self.B-1} args)"
        if n == "RETURN":
            return f"return R({A})..R({A+self.B-2})" if self.B else f"return R({A})..top"
        if n == "FORLOOP":
            return f"R({A}) += R({A+2}); if R({A}) <= R({A+1}) then pc += {self.sBx}"
        if n == "TFORLOOP":
            return f"R({A+2})..R({A+2+self.C}) := R({A})(R({A+1}), R({A+2})); if R({A+2}) ~= nil then pc++"
        if n == "TFORPREP":
            return f"if type(R({A}))=='table' then R({A+1}):=R({A}); R({A}):=next; pc += {self.sBx}"
        if n == "SETLIST":
            return f"R({A})[...] := R({A}+1)..R({A}+{self.Bx})"
        if n == "CLOSE":
            return f"close upvalues >= R({A})"
        if n == "CLOSURE":
            extra = f"  (proto #{self.Bx}"
            if protos is not None and self.Bx < len(protos):
                p = protos[self.Bx]
                extra += f", line {p.line_defined}, {len(p.code)} insns"
            extra += ")"
            return f"R({A}) := closure(KPROTO[{self.Bx}]){extra}"
        return f"{n}  A={A} B={self.B} C={self.C} Bx={self.Bx}"

    @staticmethod
    def _k(idx, k):
        if k is None or idx >= len(k):
            return f"K({idx})"
        t, v = k[idx]
        if t == "str":
            return repr(v)
        if t == "num":
            return repr(v)
        return "nil"
