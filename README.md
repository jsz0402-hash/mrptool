# mrptool

**斯凯 MRP / Mythroad 平台逆向工具** —— 解开那些 299 块山寨机上的记忆。

[![format](https://img.shields.io/badge/format-reversed-blue)]() [![python](https://img.shields.io/badge/python-3.8%2B-green)]() [![license](https://img.shields.io/badge/license-MIT-lightgrey)]()

---

## 这是什么

**Mythroad(斯凯 / MRP)是国产功能机时代的应用平台。** 从 2005 年前后到 **2013 年 10 月 1 日正式停运**,它让几亿台几百块的山寨机也能装 App、玩游戏、升级 QQ。

平台死后,开发文档几乎失传。有人在 2019 年把自己的老硬盘翻了出来:

> 很遗憾,mrp 时代结束这么多年后才终于将这些资料公开,**可能我是最后一个保留了完整的开发技术的人,留着将来考古用**
>
> **青春如同奔流的江河,一去不回来不及道别**

`mrptool` 把 `.mrp` / `.mr` / `.ext` 三种格式**完整逆向并实现**,让这些文件在今天还能被读懂。

---

## 重大发现:`.mr` 是 Lua 字节码

**Mythroad VM 是一个魔改的 Lua 5.0.2 解释器。**

| 项 | 官方 Lua 5.0.2 | Mythroad |
|---|---|---|
| 签名 | `\033Lua` | **`\033MRP`** |
| 头部长度 | 21 字节 | **6 字节**(砍掉全部自检) |
| `lua_Number` | 8 字节 double | **4 字节**(功能机没有 FPU) |

验证方式是在 **16 组参数组合**中穷举 —— 只有 `(头部 6, size_t 4, number 4)` 能完整解析,且**尾部剩余 0 字节**。

平台后续还演化出**第二种头部**(完整 18 字节,带官方全部 TESTSIZE 自检),同样在 11 组穷举中唯一命中。工具会按版本字节自动识别。

详见 [FORMAT.md](FORMAT.md)。

---

## 验证结果

对 **34 个 `.mrp` 样本**(615 个条目,合计 1.8 MB)跑完整流程:

```
包解析成功        34 / 34      (100%)
条目/区块一致     34 / 34      (100%)   ← 两份冗余索引交叉验证
条目总数          615
.mr 解析成功      64 / 64      (100%)   ← 判据:消耗字节 == 文件大小
.ext (ARM32)      62
.bmp              114
嵌套 .mrp         3
```

**64 个 `.mr` 全部按 Lua 5.0 chunk 完整解析,无一个残留字节。**

解出的中文常量(GBK)全部语义通顺:

```
'冒泡游戏免费下载'   'MM交友'   '经典总排行>>'
'[巡游]刀剑笑之极乐宝鉴'   '[飞虎队]我是特种兵'
'[真人]冒泡棋牌'   '夫妻恩爱姿势大全|移动专区'
'抢注册2元促销第二批>>'
'http://app1x.elevensky.net/|http://www.elevensky.net/|...'
```

`elevensky.net` —— **斯凯网络自己的域名**。这是 2011 年的活化石。

---

## 安装

纯 Python,**零依赖**(反汇编 `.ext` 需要可选的 `capstone`)。

```bash
git clone https://github.com/<你的用户名>/mrptool.git
cd mrptool
pip install -e .            # 可选
pip install capstone        # 可选:反汇编 .ext 用
```

### 获取完整测试样本

本仓库只带 3 个最小的公开测试样本(`helloworld.mrp` / `mr.mrp` / `asm.mrp`)。

完整的 34 个样本请自行下载 —— 它们是**第三方游戏,版权不属于本项目**:

```bash
python tools/get_samples.py
```

脚本会从 [vmrp](https://github.com/vmrp) 的两个公开仓库拉取。详见 [samples/README.md](samples/README.md)。

> 下载完后 `python tests/verify_all.py samples` 应输出 **64/64 全部通过**。

### Windows 一键使用

不用记命令,双击 **`启动工具.bat`** 即可打开中文菜单界面。


## 用法

```bash
# 看包结构
python -m mrptool.cli info samples/helloworld.mrp

# 解包
python -m mrptool.cli extract samples/helloworld.mrp -o out/

# 反汇编 .mr(已解出的 Lua chunk)
python -m mrptool.cli disasm out/00_start.mr

# 全流程:解包 + 反汇编 + 生成报告
python -m mrptool.cli dump samples/helloworld.mrp -o dump/
```

### `info` 输出示例

```
  魔数          b'MRPG'
  版本          287  (0x11F)
  声明大小      8,354   ✓ 一致
  头部长度      240  (0xF0)
  应用名(全)    'Helloworld'   -> GBK: Helloworld
  条目表        2 项,结束于 0x127
  数据区块      2 个,结束于 0x20A2
  条目/区块一致 ✓ 是

    #  名称                             偏移         压缩         解压  类型
    0  start.mr                      312      1,018      2,490  gzip Lua 5.0 字节码
    1  cfunction.ext               1,352      7,002     11,572  gzip ARM32 代码 (CMAP)
```

### `disasm` 输出示例

```
function <@start.mr:0>   params=0 vararg=0 maxstack=9 nups=0 insns=61 consts=26 protos=5
  locals: p_mr_param, param_len
  strings:
    K[0  ] = '_com'
    K[3  ] = '_mr_c_load'
    K[4  ] = 'gc_times'
    K[6  ] = 'dealevent'
  numbers (4字节原始值):
    K[1  ] = 3629
    K[2  ] = 2913
  code:
        0  GETGLOBAL  R(0) := _G['_com']
           ; raw=0x00000005
        1  LOADK      R(1) := 3629
           ; raw=0x01000041
        3  CALL       R(0)..R(0) := R(0)(2 args) -> 0 results
           ; raw=0x00018059
        4  CLOSURE    R(0) := closure(KPROTO[0])  (proto #0, line 40, 18 insns)
           ; raw=0x00000022
        5  SETGLOBAL  _G['_mr_c_load'] := R(0)
           ; raw=0x000000C7
```

---

## 作为库使用

```python
from mrptool import MrpFile, Chunk, disassemble

m = MrpFile("game.mrp")
print(m.app_name_gbk, len(m.entries))

for e in m.entries:
    data = e.data(m.data)          # 自动 gunzip
    if e.name.endswith(".mr"):
        c = Chunk(e.name, data)
        c.parse()
        print(c.stats())
        print(disassemble(c))
```

---

## 三种格式一览

| 格式 | 内容 | 状态 |
|---|---|---|
| `.mrp` | 应用包(240 字节头 + 条目表 + gzip 数据区) | ✅ **完全破译** |
| `.mr` | Lua 5.0 预编译 chunk | ✅ **完全破译** |
| `.ext` | ARM32 原生代码(`MRPGCMAP` + ARM 指令流) | ✅ **魔数与指令集确认** |

---

## 它值得被记住

> 小时候最羡慕有一个能装 app 的手机了,当时自己**硬攒钱(299 元)**买了一个山寨机,
> 能装 mrp 游戏,可玩性挺高的……还能**升级 QQ,好像是 QQ 2010 版本**,
> 当时觉得真高级,**真智能手机啊**。
>
> 小时候没有钱,没有用过诺基亚的手机,等有钱买了已经进入了安卓的时代。

**那是几亿人的第一部"智能手机"。**

---

## 致谢

- [vmrp](https://github.com/vmrp) —— 把老硬盘里的东西公开出来的人
- [mrpoid2018](https://github.com/Yichou/mrpoid2018) —— 安卓上的成熟实现
- [Lua 5.0.2](https://www.lua.org/ftp/lua-5.0.2.tar.gz) —— 官方源码是本次逆向的对照基准

## 许可

**代码与文档:MIT**(见 [LICENSE](LICENSE))。

**样本文件:不适用。** `samples/` 与 `tools/get_samples.py` 涉及的所有 `.mrp` 都是第三方应用与游戏,
全部权利归各自权利人所有,**本项目不再分发、也不授权任何人分发**。

本项目存在的目的只有两个:**数字遗产保存**,和**技术研究**。
请勿用于商业用途或任何侵犯他人权利的用途。

