# P3 Fuzzer 真实性 · 实施证据

> 日期：2026-10-18
> 环境：worker 容器内 `forge 1.7.1`（宿主未安装 Foundry）
> 结论：**Fuzzer 从"必然假阴性"变成"可失败的最小探针"；范围比原计划窄，已如实收窄。**

---

## 1. 改造前实测（项目 #47，经 API 触发）

```
Compiling 22 files with Solc 0.8.35
Error: Compiler run failed:
Error (7920): Identifier not found or not unique.
 --> test/FuzzTest.t.sol:7:5
  |     VulnerableToken public _vulnerableToken;
```

| 观测 | 值 |
|---|---|
| `contracts_found` / `tests_generated` | 1 / 3 |
| `failures` | `None` |
| 实际结果 | **编译失败**，但对外呈现为"0 失败" |

同时 `uploads/47/` 被 `forge init --force` 污染，多出 `lib/ src/ test/ script/ foundry.toml README.md`（已清理，仅保留用户上传的 `.sol`）。

### 1.1 四个叠加根因

1. 生成的测试**没有 import 合约文件** → `Identifier not found`；
2. `new C()` **不带构造参数** → 即使 import 修好也会编译失败；
3. 一律 `func(x)`，**不看真实签名** → 参数数量/类型不匹配；
4. 编译失败只打印在 `raw_output` 里，**没有 `[FAIL]` 行** → `failures=None`，等于"0 漏洞"。

第 4 条是致命的：前三条可以被日志发现，第 4 条让前三条永远不被发现。

---

## 2. 改造后的规则

| 规则 | 实现 |
|---|---|
| 只在临时副本里跑 | `tempfile.mkdtemp` + `copytree`，`finally` 删除；`uploads/<id>` 不再被写 |
| 生成能失败的测试 | **没有可推导的不变量就不生成测试**，返回 `status=no_invariant_derivable` |
| 构造参数真实化 | 按签名生成 `uint256(1)` / `address(0x1)` / `""` / `hex""` |
| 导入真实路径 | `import "../<相对路径>.sol"` |
| 输出上限 | 64 KB，头部写入 `[fuzz-status] status=...` |
| 失败可映射 | `contract` / `function` / `risk_type` 随失败一起落库 |

**当前唯一的不变量**：ERC-20 供给守恒。触发条件（全部满足才生成）：

1. 存在 `totalSupply()`；
2. 存在余额 getter（`balanceOf(address)` 或 `public balances` 映射）；
3. 存在 `transfer(address,uint256)`；
4. 存在一个单 `uint` 参数的支出型函数（如 `withdraw`）。

生成逻辑：转给一个随机 actor → 以 actor 身份调用支出函数 → 断言
`getter(actor) + getter(this) == totalSupply`。

**第二个污染向量（本轮新发现）**：`forge` 的 `cache/`、`out/` 默认相对**进程 cwd** 解析。worker 里 cwd=/app（挂载到 `backend/`），于是测试跑完在仓库里出现 `backend/cache/fuzz/failures/...`。已同时用 `cwd=<workspace>` 与 `FOUNDRY_CACHE_PATH` / `FOUNDRY_OUT` 固定到临时目录，复测后 `backend/cache` 不再出现。

---

## 3. 实测结果

### 3.1 VulnerableToken（应为阳性）

```
[fuzz-status] status=ok tests=1
[FAIL: assertion failed: 0 != 1; counterexample: calldata=0xb37ba3b7... args=[1797, 3557]]
testFuzz_VulnerableToken_Conservation_withdraw(uint256,uint256)

failures = [{"test_name": "testFuzz_VulnerableToken_Conservation_withdraw",
             "contract": "VulnerableToken", "function": "withdraw",
             "risk_type": "supply_conservation",
             "counterexample": "calldata=0xb37ba3b7... args=[1797, 3557"}]
```

**这是本项目第一次由 fuzzer 产出可复现的失败**：`withdraw` 减少了用户余额却没有减少 `totalSupply`，供给守恒被打破。

### 3.2 SimpleToken（应为阴性）

```
[fuzz-status] status=no_invariant_derivable contracts=1
failures = None
```

`SimpleToken` 只有 `transfer/approve/transferFrom`，没有支出型单参函数，守恒不可能被破坏。**不生成测试**，而不是生成一个恒真的测试。

---

## 4. 范围声明（必须写进 README）

这是 **ERC-20 供给守恒探针**，不是通用漏洞检测器：

| 能发现 | 不能发现 |
|---|---|
| 余额与 `totalSupply` 不一致（销毁/增发/记账错误） | 重入（需要合约特定的攻击者合约） |
| 上述 4 个前提下，支出函数破坏守恒 | 权限缺失、预言机操纵、闪电贷攻击、跨合约逻辑 |

原计划 DoD 写的是"`VulnerableToken.withdraw` 的 SWC-107 能被 fuzz 真实触发"——**这一条没有做到，也不该声称做到**。通用 fuzzer 无法凭空构造重入攻击者；要做那件事，需要按合约生成攻击者，属于下一阶段的研究问题。

---

## 5. 测试

`tests/test_fuzzer.py`（7 条，无需 Foundry）：

| 用例 | 断言 |
|---|---|
| 参数类型归一 | uint/address/bool/bytes32 支持；string/数组拒绝 |
| 构造值 | `uint8` 用 1（避免编译期越界）、string/bytes 可展开 |
| 合约解析 | ctor 1 参、函数集合含 transfer/withdraw、import 路径正确 |
| 生成内容的真实性 | 含 import、`new VulnerableToken(uint256(1))`、`assertEq(`，且**不含** `assertEq(x, x)` |
| 不可推导 | SimpleToken → `no_invariant_derivable`，不写文件 |
| 失败解析 | 去重（forge 会打印两遍）、映射 contract/function/risk_type |

全量：**145 passed**（原 138 + 7）。

---

## 6. 未验证 / 已知局限

1. 只在两个 fixture 上跑过；复杂 DeFi（代理、继承、多合约）未测；
2. 宿主无 Foundry，单元测试不含真实 forge 调用——真实运行只在容器里手工验证（本文档）；
3. `forge init` 在临时目录里仍需联网拉 `forge-std`（首次），离线环境会 `compile_error`；
4. 单测/多实现合约只取文件里第一个 `contract`，其余忽略。
