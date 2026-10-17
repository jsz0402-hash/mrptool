# 样本说明

这里的 `.mrp` 文件是**第三方应用与游戏**,版权归各自权利人所有。

## 本仓库自带的

只包含体积小、来源公开的测试样本,用于验证工具本身:

| 文件 | 说明 |
|---|---|
| `helloworld.mrp` | 官方 SDK 的 Hello World 示例(2 个条目) |
| `mr.mrp` | 最小 MRP 包(1,322 字节) |
| `asm.mrp` | 汇编示例(3,948 字节) |

## 其余样本怎么来

完整样本集请自行下载:

```bash
python tools/get_samples.py
```

脚本会从 [vmrp](https://github.com/vmrp) 的两个公开仓库拉取:

- [vmrp/mythroad](https://github.com/vmrp/mythroad) —— 24 个 `.mrp`
- [vmrp/vmrp_arm](https://github.com/vmrp/vmrp_arm) —— 10 个 `.mrp`

作者公开这些文件时的原话:

> 老硬盘里翻出来的东西,是以前斯凯 mrp 平台的一些备份文件,不知道里面有些什么

## 请勿

- 把这些样本用于商业用途
- 再分发(尊重原作者与权利人的权利)
- 用于任何侵犯他人权利的用途

本项目对这些文件的态度是**保存与研究**,不是传播。
