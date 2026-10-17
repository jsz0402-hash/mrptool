# MRP / Mythroad 文件格式规范

> 逆向整理自 `vmrp` 系列仓库的样本文件与斯凯官方 SDK 资料,
> 并逐字段对照 **Lua 5.0.2 官方源码**验证。
>
> 平台已于 **2013 年 10 月 1 日**正式停止运营。本文档的目的,是让这套格式不至于随硬盘一起消失。

---

## 0. 背景

| | |
|---|---|
| 官方名称 | **Mythroad 平台** |
| 别名 | mrp 平台、MiniJ 平台 |
| 开发方 | 杭州斯凯网络科技有限公司(2005 前后成立,2010 年在纳斯达克上市) |
| 目标 | *"让每一台普通的手机都可以自由地安装、使用精彩的第三方应用软件和游戏"* |
| 载体 | 国产**功能机 / 山寨机**(MTK、展讯平台) |
| 停运 | 2013-08-01 停止新应用审核,2013-10-01 平台正式停运 |

平台由三部分组成:

```
Mythroad SDK    开发工具包(PC 端,mrpbuilder.exe)
Mythroad VM     虚拟机(移植到 MTK / 展讯 / Symbian S60v3 / PC Windows)
mrp 包          应用分发包(Mythroad Resources Pack)
```

**关键事实:Mythroad VM 是一个魔改的 Lua 5.0.2 解释器。**

---

## 1. `.mrp` 包格式

### 1.1 文件头(固定 0xF0 = 240 字节)

| 偏移 | 大小 | 类型 | 说明 |
|---|---|---|---|
| `0x00` | 4 | char[4] | 魔数 **`MRPG`** |
| `0x04` | 4 | u32 | 版本号(实测 282 / 287 / 507 / 519) |
| `0x08` | 4 | u32 | **文件总大小**(已核验,与磁盘大小一致) |
| `0x0C` | 4 | u32 | **头部长度** = 条目表起始偏移,恒为 `0xF0` |
| `0x10` | 12 | char[12] | 应用名(截断到 12 字节,**可能截断**) |
| `0x1C` | 12 | char[12] | 应用名(完整,**GBK 编码**) |
| `0x28` | 12 | char[12] | 保留(实测全 0) |
| `0x34` | 12 | char[12] | 应用 ID(十六进制字符串) |
| `0x40` | 176 | — | 其余元数据 |

### 1.2 条目表(从 `0xF0` 开始,**紧凑排列,无字节对齐**)

```c
struct Entry {
    uint32_t name_len;        // 含结尾 '\0'
    char     name[name_len];
    uint32_t data_offset;     // 文件内绝对偏移
    uint32_t data_size;       // 压缩后大小
    uint32_t flags;           // 实测恒为 0
};
```

解析终止条件(任一满足):
- `name_len` 不在 `[1, 200]`
- `name` 不以 `'\0'` 结尾
- `data_offset < header_len` 或 `data_offset + data_size > filesize`

### 1.3 数据区(紧跟条目表)

每个数据块**自描述**:

```c
struct Block {
    uint32_t name_len;
    char     name[name_len];
    uint32_t size;
    uint8_t  gzip_data[size];   // 全部为 gzip 流(magic 1F 8B)
};
```

> **重要**:条目表与数据区块是**两份冗余索引**。实测二者在
> `name` / `size` / `offset` 上完全一致,可用于交叉校验解析正确性。

### 1.4 条目类型

| 扩展名 | 内容 |
|---|---|
| `.mr` | **Lua 5.0 预编译字节码**(见第 2 节) |
| `.ext` | **ARM32 原生代码**,魔数 `MRPGCMAP`(见第 3 节) |
| `.bmp` | 24 位 BMP 位图(资源) |
| `.bin` | 点阵字库 / 数据表 |
| `.mrp` | 嵌套 MRP 包 |

---

## 2. `.mr` 格式 —— **Lua 5.0 预编译 chunk**

### 2.1 与官方 Lua 5.0.2 的差异

| 项 | 官方 Lua 5.0.2 | **Mythroad `.mr`** |
|---|---|---|
| 签名 | `\033` + `"Lua"` | **`\033` + `"MRP"`** |
| 头部长度 | 21 字节 | **6 或 18 字节(两种变体)** |
| 头部内容 | version + endian + 7 项 TESTSIZE + TEST_NUMBER | 见下 |
| `sizeof(size_t)` | 4 或 8 | **4** |
| `sizeof(int)` | 4 | 4 |
| `sizeof(Instruction)` | 4 | 4 |
| `lua_Number` | 8(double) | **4(非 IEEE754)** |

### 2.1.1 两种头部变体(由 `head[4]` 版本字节区分)

**变体 A —— 精简头(版本 `0x80`,6 字节)**

```
0x00  1B 4D 52 50     "\033MRP"
0x04  u8              版本 = 0x80
0x05  u8              端序标志(1 = 小端)
```

省掉全部自检。**保留** `lines` 与 `locals` 信息。

**变体 B —— 完整头(版本 `0x50`,18 字节)**

```
0x00  1B 4D 52 50     "\033MRP"
0x04  u8              版本 = 0x50        (= 官方 Lua 5.0 的 VERSION!)
0x05  u8              端序标志(1 = 小端)
0x06  u8              sizeof(int)        = 4     ┐
0x07  u8              sizeof(size_t)     = 4     │
0x08  u8              sizeof(Instruction)= 4     │ 对应官方
0x09  u8              SIZE_OP            = 6     │ LoadHeader 里的
0x0A  u8              SIZE_A             = 8     │ 7 项 TESTSIZE
0x0B  u8              SIZE_B             = 9     │
0x0C  u8              SIZE_C             = 9     ┘
0x0D  4 字节          TEST_NUMBER              (= 官方 TestSize 后的数值校验)
0x11  u8              标志
```

**保留完整的官方自检序列,但 `lines` 和 `locals` 被剥离为 0。**

> 推断:`0x50` 是早期直接沿用官方 Lua 格式的版本,`0x80` 是后期为省空间精简过的版本。

**两种变体都严格沿用 Lua 5.0.2 `lundump.c` 的 `LoadFunction` 结构。**
工具会按版本字节自动选择,并在解析失败时回退到另一种。

### 2.2 LoadFunction 结构(逐字对照官方 `lundump.c`)

```
string   source          // size_t 长度 + 数据(含 '\0'),0 表示继承父级
int32    lineDefined
uint8    nups
uint8    numparams
uint8    is_vararg
uint8    maxstacksize

// LoadLines
int32    n_lines
int32    lines[n_lines]

// LoadLocals
int32    n_locals
{ string varname; int32 startpc; int32 endpc; }[n_locals]

// LoadUpvalues
int32    n_upvalues      // 必须为 0 或等于 nups
string   upvalues[n_upvalues]

// LoadConstants
int32    n_constants
{ uint8 type; value; }[n_constants]
         // type: 0=NIL, 3=NUMBER(4 字节), 4=STRING

// 子函数
int32    n_protos
Proto    protos[n_protos]

// LoadCode
int32    n_code
uint32   code[n_code]    // 每条一个 Instruction
```

### 2.3 指令编码(逐字对照官方 `lopcodes.h`)

```c
#define SIZE_OP 6      #define SIZE_A 8
#define SIZE_B  9      #define SIZE_C 9
#define POS_C  SIZE_OP            // = 6
#define POS_B  (POS_C + SIZE_C)   // = 15
#define POS_A  (POS_B + SIZE_B)   // = 24
#define POS_Bx POS_C              // = 6
#define SIZE_Bx (SIZE_B + SIZE_C) // = 18
```

**位布局:`A[24:32] | B[15:24] | C[6:15] | op[0:6]`**

> ⚠️ 注意:这与 Lua **5.1** 的布局(`op,A,C,B`)不同。用错会得到看似合理但完全错误的反汇编。

指令集共 **35 条**,逐字来自官方 `lopcodes.c :: luaP_opnames[]`:

```
MOVE LOADK LOADBOOL LOADNIL GETUPVAL GETGLOBAL GETTABLE
SETGLOBAL SETUPVAL SETTABLE NEWTABLE SELF
ADD SUB MUL DIV POW UNM NOT CONCAT JMP
EQ LT LE TEST CALL TAILCALL RETURN
FORLOOP TFORLOOP TFORPREP SETLIST SETLISTO CLOSE CLOSURE
```

### 2.4 未解问题:`lua_Number` 的真实语义

`.mr` 里的数值常量是 **4 字节非 IEEE754**。

实测样本中,按小端有符号整数解读得到的值**全部合理**:

| 原始字节 | int32 解读 | float32 解读 |
|---|---|---|
| `2D 0E 00 00` | **3629** | 5.085e-42 |
| `61 0B 00 00` | **2913** | 4.082e-42 |
| `21 03 00 00` | **801** | 1.122e-42 |
| `89 13 00 00` | **5001** | 7.008e-42 |

**推断:Mythroad 把 Lua 的 `double` 换成了 32 位整数或定点数**
(功能机 CPU 普遍没有 FPU)。**具体是整数还是定点,尚未确证** —— 需要结合 VM 的算术指令行为进一步验证。

---

## 3. `.ext` 格式 —— ARM32 原生代码

```
偏移   大小  说明
0x00    8   魔数 "MRPGCMAP"  (Code MAP)
0x08    -   ARM32 指令流(小端,ARM 模式,非 Thumb)
```

**验证**:用 Capstone 以 `CS_ARCH_ARM / CS_MODE_ARM` 反汇编,前 70 条指令**识别率 100%**:

```asm
0x001000  38 40 2d e9   push {r3, r4, r5, lr}
0x001004  0c 41 9f e5   ldr  r4, [pc, #0x10c]     ; GOT 基址
0x001008  04 40 8f e0   add  r4, pc, r4
0x00101c  0f 00 00 1a   bne  #0x1060
0x001028  32 ff 2f e1   blx  r2                   ; 间接调用
```

典型的 **GCC 编译的位置无关代码(PIC)**。

这与平台自述文档的说法一致:

> 我只是一个"编译配置器",所作的仅仅是把编译所需的参数整理好,
> 并整个交给 **ARM 编译器**去编译出 `*.ext`。

---

## 4. 验证方法

### 4.1 Lua 5.0 假设的穷举验证

严格按官方 `lundump.c` 实现解析器,把不确定参数**参数化**,穷举所有组合。

**变体 A(版本 `0x80`)** —— 样本 `start.mr`:

```
头部长度 ∈ {6, 10, 11, 21}
size_t   ∈ {4, 8}
number   ∈ {4, 8}
```

| 头部 | size_t | number | 结果 |
|---|---|---|---|
| **6** | **4** | **4** | ✅ **解析成功,尾部剩余 0 字节** |
| 6 | 4 | 8 | ✗ 非法常量类型 100 |
| 6 | 8 | 4 | ✗ 字符串长度异常 |
| 10/11/21 | 任意 | 任意 | ✗ 全部失败 |

**16 选 1,零字节剩余。**

**变体 B(版本 `0x50`)** —— 样本 `qqlist…/applist.mrp` 的 19 个 `.mr`:

| 头部长度 | 成功数 |
|---|---|
| 6 / 10 / 11 / 14 / 15 / 16 / 17 | 0 / 19 |
| **18** | ✅ **19 / 19** |
| 19 / 21 / 22 | 0 / 19 |

**11 选 1,19 个文件全中。**

### 4.2 全量样本验证

对 **34 个 `.mrp` 样本**(源:vmrp/mythroad + vmrp/vmrp_arm)跑完整流程:

```
包解析成功        34 / 34      (100%)
条目/区块一致     34 / 34      (100%)
条目总数          615
.mr 解析成功      64 / 64      (100%)   ← 判据:消耗字节 == 文件大小
.ext (ARM32)      62
.bmp              114
嵌套 .mrp         3
```

**64 个 `.mr` 全部按 Lua 5.0 chunk 完整解析,无一个残留字节。**

### 4.3 语义交叉验证

反汇编 `start.mr` 的 main 函数,得到语义自洽的 Lua 代码:

```lua
R(0) := _G['_com']            -- 取全局 _com
R(1) := 3629                  -- 参数 1
R(2) := 2913                  -- 参数 2
R(0)(2 args)                  -- 调用 _com(3629, 2913)

R(0) := closure(KPROTO[0])    -- proto #0, line 40, 18 insns
_G['_mr_c_load'] := R(0)      -- 定义 _mr_c_load

R(0) := 0
_G['gc_times'] := R(0)        -- gc_times = 0

R(0) := closure(KPROTO[1])    -- proto #1, line 68, 62 insns
_G['dealevent'] := R(0)
```

- `CLOSURE → SETGLOBAL` 模式重复 5 次,标准的"定义函数并导出"
- 行号 40 → 68 → 98 **单调递增**
- 字符串常量全部是合法标识符

### 4.4 中文常量验证(GBK)

变体 B 的样本解出大量 GBK 中文常量,**全部语义通顺**:

```
K[5 ] = '冒泡游戏免费下载'        K[6 ] = 'MM交友'
K[13] = '经典总排行>>'            K[14] = '[巡游]刀剑笑之极乐宝鉴'
K[21] = '[龙虎门]中华英雄'        K[24] = '[真人]冒泡棋牌'
K[27] = '夫妻恩爱姿势大全|移动专区'
K[29] = '抢注册2元促销第二批>>'
K[12] = 'http://app1x.elevensky.net/|http://www.elevensky.net/|...'
```

**其中 `elevensky.net` 是斯凯网络自己的域名** —— 这是 2011 年的活化石。

---

## 5. VM 暴露的 API 清单

从 `start.mr` 的全局导出与常量表可整理出 VM 的接口面:

| 名字 | 推测用途 |
|---|---|
| `_com` | 核心调用入口(带两个初始化参数) |
| `_mr_c_load` | 加载并绑定 `.ext` 里的 C 函数 |
| `_mr_c_buf` / `_strCom` | 字符串/C 缓冲区桥接 |
| `_mr_param` / `p_mr_param` / `param_len` | 参数传递 |
| `gc_times` / `_gc` | 垃圾回收 |
| `dealevent` / `dealtimer` | 事件循环 / 定时器 |
| `suspend` / `resume` | 挂起 / 恢复 |
| `sysinfo` / `GetSysInfo` / `vmver` | 系统信息 |
| `string` / `subV` / `pack` / `Exit` / `ret` | 工具函数 |

---

## 6. 参考资料

- [vmrp/mythroad](https://github.com/vmrp/mythroad) —— 24 个 `.mrp` 样本("老硬盘里翻出来的东西")
- [vmrp/mrpdev](https://github.com/vmrp/mrpdev) —— SDK + 开发文档(417 MB)
- [vmrp/vmrp_arm](https://github.com/vmrp/vmrp_arm) —— VM 移植实验
- [mrpoid2018](https://github.com/Yichou/mrpoid2018) —— 安卓上的成熟实现
- [Lua 5.0.2 官方源码](https://www.lua.org/ftp/lua-5.0.2.tar.gz) —— `lundump.c` / `ldump.c` / `lopcodes.h`
- [《Mythroad 平台自述》](https://blog.csdn.net/iteye_3277/article/details/82264259)(2011) —— 平台第一人称自述

---

## 7. 未完成的部分

- [ ] `lua_Number` 的确切语义(整数 or 定点)
- [ ] `.ext` 的导出符号表结构(`CMAP` 段)
- [ ] VM 的完整操作码语义(官方 35 条已确认,但 Mythroad 可能增删)
- [ ] 头部 `0x40`–`0xEF` 那 176 字节的具体字段
- [ ] `.tsf` / `.uc2` 点阵字库格式

---

*本文档由逆向分析整理,仅供数字遗产保存与技术研究之用。*
*MRP 平台及其中应用的全部权利归各自权利人所有。*
