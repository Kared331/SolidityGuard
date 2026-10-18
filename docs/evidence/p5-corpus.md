# P5 语料测量与 D1 决策 · 实施证据

> 日期：2026-10-18
> 语料：5 个仓库、176 个 `.sol`、1,174,185 B，commit 已锁定
> 结论：**保留关键词过滤，但把被过滤的函数记进账本**——原二选一（删/留）都错。

---

## 1. 语料

不 vendor 第三方源码（许可冲突），只记录仓库 + commit：

| 名称 | 仓库 | commit | 文件 |
|---|---|---|---|
| uniswap-v2-core | Uniswap/v2-core | `6a9e7c978606` | 12 |
| uniswap-v2-periphery | Uniswap/v2-periphery | `ed2499130429` | 23 |
| compound | compound-finance/compound-protocol | `a3214f67b733` | 37 |
| openzeppelin | OpenZeppelin/openzeppelin-contracts | `b04d141ba4fe` | 46 |
| solmate | transmissions11/solmate | `89365b880c4f` | 59 |
| **合计** | | | **176**（去重后 176 个文件、1759 个函数） |

复现：

```powershell
python docs\evidence\fetch_corpus.py          # 读 docs/evidence/corpus.lock.json
python docs\evidence\measure_extraction.py --corpus corpus
```

`fetch_corpus.py` 从 codeload 下载 tarball，SHA 取自 tarball 的 pax header，不依赖被墙的 `api.github.com`。`--refresh` 才会重新解析分支头并改写 lock。

---

## 2. 提取质量（P0 的回归验证）

对 176 个文件：`extracted = 1759 = reference`，**missed 0 / noise 0 / body_mismatch 0**。

这是 P0 解析器在真实 DeFi/库代码上的第一次大规模验证——它没有崩。`ctor=66 / receive=9 / fallback=5` 全部被提取，这些在旧实现里是 0。

---

## 3. 关键词过滤的实际代价

| 仓库 | 单元 | 过滤后送审 | 丢弃率 |
|---|---|---|---|
| uniswap-v2-periphery | 119 | 114 | **4.2%** |
| uniswap-v2-core | 33 | 27 | 18.2% |
| solmate | 843 | 668 | 20.8% |
| compound | 473 | 369 | 22.0% |
| openzeppelin | 291 | 213 | 26.8% |
| **合计** | **1759** | **1391** | **20.9%** |

与预期一致：协议合约（periphery）丢弃率低，库/标准实现（OZ、solmate）丢弃率高。**审计目标从来不是单一类型**，所以 20.9% 是真实区间内的值，不是上界也不是下界。

---

## 4. 决策：两边都不对

原判据：

- < 10% → 删过滤
- ≥ 10% → 保留 + 报告里写"仅审计 X%"

20.9% 落在"保留"一侧。但**保留本身会把 368 个函数变成不存在**：`functions_extracted` 只统计送审集合，报告显示"提取 1391"，而源码里有 1759。P1 花了整整一刀消灭"静默丢函数"，这个过滤又在同一位置把它加回来。

所以实际执行的是第三条路：

**保留过滤（成本不变），但把被过滤的函数写进账本。**

| 改动 | 内容 |
|---|---|
| 单元状态 | 新增 `filtered / keyword_filter`，与 `audited / skipped / failed` 并列 |
| 恒等式 | 由三项改为四项：`extracted = audited + skipped + failed + filtered` |
| 账本 | 新增 `audit_runs.functions_filtered`（迁移 014） |
| 报告 | 覆盖率段新增 "Filtered (keyword)" 行；覆盖率分母改为真实函数数 |
| 删除 | `_extract_key_functions` 适配层（不再有两套统计口径） |

---

## 5. 真实链路验证（项目 #62）

上传一个含"无关键词函数"的合约（`constructor` / `helper` / `withdraw`）：

```
ledger: {status: degraded, files_total: 1, functions_extracted: 3,
         functions_audited: 0, functions_failed: 2, functions_filtered: 1}
identity_U: True          # 3 = 0 + 2 + 0 + 1
```

单元明细（`details_json`）：

```json
{"function": "constructor", "line": 8,  "status": "failed",   "reason": "llm_error"}
{"function": "helper",      "line": 10, "status": "filtered", "reason": "keyword_filter"}
{"function": "withdraw",    "line": 14, "status": "failed",   "reason": "llm_error"}
```

报告渲染：`Filtered (keyword) | 1`。

`helper` 现在会出现在报告里，标明"因关键词过滤未送审"。它仍然没被审，但**用户能看见它没被审**。

---

## 6. 这次测量不能回答什么

`selected/ref` 只说明"丢了多少"，不说明"丢的是不是关键函数"。

要回答后者，需要给 1759 个函数标"是否真含漏洞"，那是 P6 的标注工作。当前数据**不能**被写成"漏报率 20.9%"——过滤丢的是函数，不是漏洞，两者不能等同。

---

## 7. 测试

| 组 | 断言 |
|---|---|
| 恒等式 | 四项在 7 组组合下成立 |
| 引擎 | 含 `helper()` 的合约产出 `filtered/keyword_filter` 单元，且 `audited` 计数不受影响 |
| 报告 | `filtered` 与账本一致；HTML 含 "Filtered (keyword)" |
| 迁移 | head = 014，`014.down_revision = 013` |

全量：**158 passed**（+2）。
