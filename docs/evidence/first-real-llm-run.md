# 第一次真实 LLM 运行 · 证据

> 日期：2026-10-18
> 模型：DeepSeek（`deepseek-chat`，服务端实际返回 `deepseek-flash`）
> 结论：**第一次真实调用就暴露了一个 100% 假阴性缺陷；账本让它在 20 秒内现形。**

---

## 1. 环境

| 项 | 值 |
|---|---|
| key | 已写入 `.env`（gitignored），`solidguard.json` 仍是 `${LLM_API_KEY}` 占位符 |
| provider | `https://api.deepseek.com` / `deepseek-chat`（OpenAI 兼容） |
| 连通性 | `POST /chat/completions` → 200，`usage.total_tokens=10` |
| embedding | 仍是本地 `all-MiniLM-L6-v2`（无外部 key） |

注意：`docker compose restart` **不会**重新读取 `.env`；必须 `up -d --force-recreate`，否则容器里还是空 key。这一点差点被误判为"key 无效"。

---

## 2. 第一次运行：完成，0 漏洞

项目 #47（`VulnerableToken.sol`，标注 2 个漏洞）：

```
ledger: {status: completed, functions_extracted: 4, functions_audited: 4,
         functions_failed: 0, invalid_findings: 10, model: deepseek-chat}
findings: 0
```

`status=completed`、`functions_audited=4`、`findings=0`——如果只看这三项，结论是"这个合约很干净"。

**账本里的 `invalid_findings=10` 是唯一破绽**：模型返回了 10 条 finding，全部被丢弃。

### 根因

`AuditFindingSchema` 把 `impact` 和 `confidence` 标为必填，而审计 prompt 从来没要求模型输出这两个字段：

```python
impact: str = Field(..., description="...")        # required
confidence: float = Field(..., ge=0.0, le=1.0)     # required
```

```text
Return a JSON array of objects: [{"vulnerability_description": "...",
 "severity": "...", "suggested_fix": "...", "gas_optimization": "..."}]
```

于是每一条 finding 都在校验时被拒，`continue` 掉。**没有 key 时这条路径永远走不到**：之前所有运行都在 `llm_error` 分支结束，`invalid_findings` 一直是 0。P2 的 E2E 也验证不了它。

---

## 3. 修复

| 改动 | 内容 |
|---|---|
| schema | `impact` / `suggested_fix` 默认 `""`，`confidence` 默认 `None`；只有 `vulnerability_description` 与 `severity` 必填 |
| prompt | 明确要求 `severity` 枚举、`impact`、`confidence`，与 schema 对齐 |
| 测试 | 新增回归：缺 `impact`/`confidence` 的 finding 必须被接受，且 `invalid_findings == 0` |

修复后同一合约：

```
ledger: {status: completed, functions_extracted: 4, functions_audited: 4,
         functions_failed: 0, invalid_findings: 0}
findings: 9
```

---

## 4. 审出了什么

| 函数 | 严重度 | 描述（截断） |
|---|---|---|
| withdraw | **Critical** | Reentrancy (SWC-107): external call to `msg.sender` via `call{value:...}` |
| withdraw | High | Unprotected Ether Withdrawal / missing access control |
| withdraw | High | Unchecked low-level call return value / forwards all gas |
| withdraw | Low | DoS with failed call |
| transfer | **Critical** | Integer underflow in the balance check |
| transfer | Low | Missing return value / effect-free code risk |
| constructor | Informational | Constructor body explanation |
| constructor | Low | Supply assigned to `msg.sender` without cap |
| getBalance | Informational | "read-only getter, contains no security issue" |

**召回**：标注的两个漏洞中，SWC-107 重入被 Critical 命中。SWC-101（整数溢出）在 0.8 下被编译器保护，模型报的是"下溢发生在 `require` 里"——这个判断本身是对的（`balances[msg.sender] - _value` 在 0.8 会先 revert），但把它列为 Critical 偏高。

**精确度**：9 条里至少有 3 条是噪声（constructor 两条、getBalance 一条明确说"无问题"却仍产出 finding）。按"明确真阳性"算 1/9；按"包含合理判断"算 2–3/9。**样本只有 1 个合约，不能当指标用。**

---

## 5. 这次运行的真正意义

1. **账本证明了价值**：`invalid_findings=10` 是唯一能区分"没漏洞"与"没审出来"的信号。没有 P1，这次运行会以"completed, 0 findings"被当成成功。
2. **"测试全绿"不等于"能力有效"**：159 条单测在修复前全绿，因为所有测试都 mock 了 LLM；只有真实调用能暴露 prompt/schema 不一致。
3. **首次有真实质量信号**：1 个合约、1 个已知漏洞被命中。距离"可声明的检出率"还很远，但这是第一个非 mock 的数据点。

---

## 6. 尚未解决

| 问题 | 说明 |
|---|---|
| 噪声 | 干净函数也会产出 Informational finding；报告里会显得"每条都有问题" |
| 无置信度 | schema 允许 `confidence`，但 prompt 只是建议，模型不一定给 |
| 单点样本 | n=1，不能算 recall/precision |
| 成本 | 本次 4 个函数 + 1 次 summary ≈ 12k tokens，DeepSeek 成本可忽略 |

**下一步**：6B 需要标注集（建议 SmartBugs-curated 子集），且需先补匿名 fallback（`function() public payable {}`）的提取——否则老合约会系统性漏函数。
