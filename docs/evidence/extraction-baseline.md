# 提取器实测基线（2026-10-18）

> 性质：只读测量，未修改任何生产代码
> 改造前被测代码：`backend/app/services/engine/llm_audit.py` @ `0543f51`，`_extract_key_functions` L207-L275
> 刀 1 后：提取逻辑迁至 `backend/app/services/engine/solidity_units.py`，§6 为改造后复测
> 复现：`venv\Scripts\python.exe docs\evidence\measure_extraction.py`

---

## 1. 为什么要有这份基线

设计文档 [`spec.md`](../design/audit-integrity/spec.md) 的初稿是**按"理论上应该防什么"写的**：完整词法分析、interface 语义、modifier 识别、`extra="forbid"` 校验……这些防御都没有证据支撑。

这份基线先回答"代码实际怎么表现"，再决定改什么。方法是：拿现成语料跑当前实现，与一个"掩码 + 括号配对"的参考扫描器对比，把差异归因到具体机制。

---

## 2. 语料与方法

**语料**：`uploads/` 下所有 `.sol`，按内容哈希去重后 **57 个文件 / 1,118,988 B**。构成：

- `forge-std` 全量库（`src/`、`test/`、`interfaces/`，含 `Vm.sol` 161 KB、`safeconsole.sol` 409 KB）——工业级真实代码，函数多、声明多、注释多；
- 两个 DeFi fixture：`VulnerableToken.sol`、`SimpleToken.sol`（各 1 个 constructor + 3 个业务函数）。

**参考实现**：先把注释与字符串字面量掩码为等长空格，再按 `function|constructor|receive|fallback` 定位签名，遇到 `{` 配对大括号、遇到 `;` 判定为声明。它只用于回答"这个位置到底是不是一个带函数体的函数"，不判断漏洞。

**分阶段**：

- 阶段 A（正则）：`function\s+(\w+)\s*\([^)]*\)[^{]*?\{` + 大括号配对；
- 阶段 B（关键词）：body 命中 37 个词之一才保留。

---

## 3. 结果

| 指标 | 数值 |
|---|---|
| 参考真值（带函数体的单元） | **1,896** |
| 阶段 A 匹配数 | 1,905（漏 15 / 噪声 24） |
| 阶段 B 保留数 | **1,491** |
| 保留率（kept / ref） | **78.6%** |
| 关键词丢弃率（dropped / 阶段 A） | **21.7%** |
| 阶段 A 漏报率（missed / ref） | **0.8%** |
| 审计覆盖的文件字节比（函数体 / 全文） | **62.4%** |

关键词损失最重的文件：

| 文件 | 保留 / 参考 |
|---|---|
| `forge-std/src/StdStyle.sol` | 1 / 78 |
| `forge-std/src/StdJson.sol` | 6 / 47 |
| `forge-std/src/StdStorage.sol` | 22 / 59 |
| `forge-std/src/LibVariable.sol` | 5 / 40 |
| `forge-std/test/StdError.t.sol` | 2 / 21 |

---

## 4. 缺陷清单

| 编号 | 缺陷 | 实测频率 | 后果 |
|---|---|---|---|
| **D1** | 关键词过滤丢弃函数 | 414 / 1,905 = **21.7%** | 函数永不送审，且无任何记录 |
| **D2** | interface 声明吞掉下一个 `{`，生成"幻影单元" | 24 个噪声中 22 例 | body 是后续代码；混合文件里整个合约体被当成某个函数的 body |
| **D3** | `constructor` / `receive` / `fallback` 从未被匹配 | 15 / 1,896 = 0.8%（13/1/1） | 部署期与兜底入口完全不在审计范围 |
| **D4** | 注释里的 `function` 被当成真函数 | 2 / 1,905 = 0.1% | 审计对象是注释文本 |
| **D5** | 字符串里的 `}` 使 body 静默截断 | 语料 0 例，合成用例复现 | 同一函数的后半段被丢掉（合成用例：16 B vs 21 B） |
| **D6** | 覆盖率不透明 | 62.4% 的文件字节进入审计 | 用户无法知道剩下 37.6% 是什么 |

### 4.1 三条与直觉相反的结论

1. **正则阶段本身够用**：单元边界准确率 99.2%，15 个漏报全部是 D3（ctor/receive/fallback），没有一例是"嵌套大括号 / 多行签名 / returns 子句"导致的解析失败。→ **不需要重写 Solidity 解析器**，初稿的 14 条解析器测试里至少 6 条是为不存在的问题写的。
2. **关键词过滤不是"形同虚设"**：`docs/solidityguard-code-review.md` L116–L131 判断该表"含 add/set/update 等高频词 → 几乎任何函数都会命中"。实测证伪：DeFi fixture 上命中率 100%（丢弃 0），但库代码上丢弃 21.7%，`StdStyle.sol` 高达 98.7%。结论应改为**"语料相关"**，而不是"无效"或"有效"。
3. **最危险的不是漏报，是幻影单元**：`function balanceOf(...) external returns (uint256);` 这类声明会让正则把下一个 `{` 当作它的 body，于是系统会拿"合约体"去当"balanceOf"审计。漏报至少是"没审"，幻影是"审错了还标着名字"。

### 4.2 合成用例复现

| 用例 | 现状 | 参考 |
|---|---|---|
| 注释里 `function fake() { require(...) }` | `kept = [fake, real]` | `[real]` |
| `require(ok, "}")` 的函数 | body 16 B（截断） | 21 B |
| constructor + receive + fallback + normal | `kept = [normal]` | 4 个全在 |
| interface 声明 + 同文件实现 | `kept = [transfer, transfer, mint]`（幻影） | `[transfer, mint]` |

---

## 5. 局限（必须声明）

1. **语料有偏**：57 个文件中 55 个来自 `forge-std`，它是开发/测试库，不是 DeFi 协议。D1 的 21.7% 是库语料的上界；DeFi 合约里 `transfer/balance/require` 遍地，丢弃率会低得多（fixture 上是 0%）。要得到"审计目标"上的真实数字，需再跑 ≥ 20 个真实主网合约（本基线没有）。
2. **参考实现未经 solc 交叉验证**：它按构造处理注释/字符串/声明，但可能对抽象合约、内联汇编有偏差。当前只用来做相对比较，不作为绝对真值。
3. **只测覆盖，不测质量**：本基线不回答"审得准不准"，只回答"审了多少"。任何"检出率提升"的说法都不由此数据支持。

---

## 6. 改造结果（刀 1）

`solidity_units.py` 落地后重跑同一语料：

| 指标 | 改造前 | 刀 1 后 |
|---|---|---|
| 提取单元 vs 参考 | 1,905（漏 15 / 噪声 24） | **1,896 = 1,896（漏 0 / 噪声 0）** |
| body 长度不一致 | 合成用例复现 1 例 | **0** |
| ctor / receive / fallback | 15 个缺失 | **13 / 1 / 1，全部提取** |
| 注释被当作函数 | 2 | **0** |
| 送审单元（selected） | 1,491 | 1,494（**78.8%**，D1 未修） |
| 送审函数体字节占比 | 62.4%（含幻影 body，虚高） | **58.2%（真实值）** |

两点说明：

1. **62.4% 掉到 58.2% 不是退化**。旧数字里包含 22 个幻影单元，它们的 body 是"下一个 `{` 到配对 `}`"的内容，在混合文件里是整个合约体，把字节数撑大了。新数字才是真实被审的代码比例。
2. **`selected/ref` 仍停在 78.8%**，因为 D1（关键词过滤）按决策推迟。这是**已知且有意保留**的缺口，不是回归。要让该指标到 99%，只需在 `select_units()` 里删掉 `u.priority > 0` 条件——但那会让 LLM 调用量上升约 27%，属于独立决策。

### 6.1 升级为 solc AST 的触发条件（仍然不满足）

| 条件 | 现状 |
|---|---|
| DeFi 语料上边界噪声 > 5% | 未测（本语料噪声 0） |
| 掩码无法修复的 body 错位 | 0 例 |
| 需要跨函数/跨合约数据流 | 不属于本阶段 |

### 6.2 复现

```powershell
venv\Scripts\python.exe docs\evidence\measure_extraction.py
```

脚本现在**直接 import** `app.services.engine.solidity_units`，不再保存实现副本，因此不会与实际代码漂移。
