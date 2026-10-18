# CI 触发 · 模拟验证

> 日期：2026-10-18
> 脚本：[`run_ci_simulation.py`](run_ci_simulation.py)
> 结论：**用真实 git 仓库、真实 `git diff`、真接口跑通了 CI 全链路；唯一没验证的是 GitHub runner 本身。**

---

## 1. 模拟了什么

完全照搬 `.github/workflows/solidguard-incremental.yml.example` 的命令序列：

```bash
git init
git add -A && git commit -m base
# 修改 withdraw：插入一行 require(_amount > 0, "zero amount");
git add -A && git commit -m head
git diff --no-color HEAD~1...HEAD -- '*.sol' > patch
# 把工作树打成 zip 上传 → POST /projects
# 全量审计（基线）
# POST /incremental-audit {diff: patch}
# GET /runs/{a}/compare/{b}
```

差异只有一处：**谁执行这些命令**。diff 格式、接口、请求体、网络可达性要求都一样。

刻意用了**插入一行**的语义改动，而不是改注释——这样新文件的行号会整体下移，可以验证映射用的是新文件坐标而不是旧坐标。

---

## 2. 结果

| 项 | 值 |
|---|---|
| patch 文件数 | 1（`contracts/Token.sol`） |
| 运行 A（全量） | 8 个函数全审 |
| 运行 B（增量） | 提取 8、**审 1**、未变 7、findings 5 行 |
| 增量计划 | `changed: ["withdraw"]`，`unchanged: [constructor, transfer, getBalance]`，`hunks: 1`，`whole_file: false` |
| 映射缺失 | `[]` |
| 对比 A→B | `added=0, removed=19, persisted=3` |

`CI_SIMULATION: PASS`。

### 一个值得注意的细节

运行 B 的 `findings` 是 5 行，但对比里 `added+persisted=3`。原因是**对比按 `(合约, 函数, 严重度)` 去重**：同一函数同一等级的多条描述被合并。这是有意的口径——否则换一种措辞就会被算成"新增漏洞"。

---

## 3. 仍未验证的部分

| 未验证 | 原因 | 风险 |
|---|---|---|
| GitHub 托管 runner 能否访问服务 | 它访问不到 localhost，必须 self-hosted | 高——答辩若现场跑 CI，必须提前配 self-hosted runner |
| Artifact/secret 配置 | 需要真实仓库与 secrets | 低 |
| `origin/${{ github.base_ref }}` 的 fetch 行为 | 本地用 `HEAD~1` 代替 | 低——模板已设 `fetch-depth: 0` |
| Webhook 形态（GitHub push payload） | 当前设计是 CI 侧算好 diff 再 POST | 中——如果要"零配置"，需要服务端拉仓库，那会引入凭据问题，本设计有意不做 |

**结论**：CI 的"数据通路"已验证；剩下的是 GitHub 侧的环境配置，属于部署问题，不是代码问题。

---

## 4. 复现

```powershell
docker compose up -d
python docs\evidence\run_ci_simulation.py
```

脚本会在 `.tmp/ci-sim/` 建临时 git 仓库（已 gitignore），上传一个真实 zip，跑全量与增量各一次。
