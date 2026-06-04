# SolidiGuard Sprint 5 — Fuzzing 集成（Foundry） 设计文档

> Source: Sprint 5 指令 + Foundry 官方 CLI 文档 + Sprint 1 代码库
> 每项设计决策标注来源

---

## 1. Implementation Approach

基于 Sprint 1 代码库增量添加 Foundry fuzzing 集成：
- Celery 任务调用 `forge test` CLI（subprocess），捕获输出 (来源: Sprint 5 第3条)
- 自动初始化 Foundry 项目（若不存在 `foundry.toml`）(来源: Sprint 5 第3条)
- 结果原样存储到 fuzzing_results 表 (来源: Sprint 5 第3条)
- 不与 Slither 结果交叉验证，不生成定制化测试 (来源: Sprint 5 强制停止规则)

---

## 2. New Table: fuzzing_results

| Column | Type | Constraint |
|--------|------|------------|
| id | Integer | PK, autoincrement |
| project_id | Integer | FK → projects.id |
| raw_output | Text | not null |
| failures_json | JSONB | nullable |
| created_at | DateTime | server_default=now |

来源: Sprint 5 第3条

注意：无 severity、is_false_positive 字段 (来源: Sprint 5 反推禁止规则)

---

## 3. Celery Task: run_fuzzer

### Input
- `project_id`: int

### Logic
1. 定位项目目录 `uploads/{project_id}/`
2. 检查 `foundry.toml` 是否存在
3. 若不存在：
   a. 执行 `forge init --no-git --force <project_dir>`（`--no-git` 避免 git init 冲突，`--force` 允许非空目录）
   b. 扫描项目中已有的 .sol 文件，识别第一个合约名
   c. 生成基础 fuzz 测试文件到 `test/FuzzTest.t.sol`（使用 Foundry 官方 minimal fuzz 模板）
4. 执行 `forge test -vvv`，捕获 stdout + stderr
5. 解析输出，提取失败信息（Foundry 输出格式：`[FAIL]` 标记的测试，含反例参数）
6. 存入 fuzzing_results 表
7. 清理：删除 `forge init` 创建的 `lib/` 目录（避免重复安装依赖）

### Foundry Output Parsing
Foundry 测试输出格式示例：
```
[PASS] testAdd(uint256,uint256) (runs: 256, μ: 12345, ~: 12345)
[FAIL] testFuzz(uint256) (runs: 64, μ: 0, ~: 0)
  Counterexample: calldata=0x..., args=[100]
```
提取 `[FAIL]` 行及其后续的 Counterexample 行。

来源: Sprint 5 第3条 + Foundry 官方 CLI 文档

---

## 4. Fuzz Test Template

使用 Foundry 官方推荐的 minimal fuzz 测试：

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "forge-std/Test.sol";

contract FuzzTest is Test {
    function testFuzz_basic(uint256 x) public pure {
        assertEq(x, x);
    }
}
```

来源: Sprint 5 证据层约束 — "只能是 Foundry 文档推荐的 minimal 示例"

---

## 5. API Endpoints

### POST /api/v1/projects/{id}/fuzz
- 验证 project 存在
- 派发 Celery `run_fuzzer` 任务
- 返回 `{"status": "fuzz_started", "project_id": id}`

### GET /api/v1/projects/{id}/fuzz-results
- 查询 fuzzing_results WHERE project_id = id
- 返回列表：`[{id, created_at, failures_count, raw_output_preview}, ...]`

来源: Sprint 5 第3条

---

## 6. Files to Create/Modify

| File | Action | Purpose |
|------|--------|---------|
| backend/app/models.py | MODIFY | 新增 FuzzingResult 模型 |
| backend/app/api/fuzz.py | NEW | fuzz API 端点 |
| backend/app/api/router.py | MODIFY | 注册 fuzz 路由 |
| backend/app/tasks/run_fuzzer.py | NEW | Foundry Celery 任务 |
| backend/alembic/versions/006_add_fuzzing_results.py | NEW | 迁移文件 |
| docker/Dockerfile | MODIFY | 安装 Foundry |

---

## 7. Design Compliance Checklist

| Sprint 5 Requirement | Status |
|----------------------|--------|
| Celery run_fuzzer 任务 | ✅ |
| 自动 forge init（若需要） | ✅ |
| 生成基础 fuzz 测试模板 | ✅ |
| 执行 forge test | ✅ |
| 解析失败信息 | ✅ |
| fuzzing_results 表 (id, project_id, raw_output, failures_json, created_at) | ✅ |
| POST /api/v1/projects/{id}/fuzz | ✅ |
| GET /api/v1/projects/{id}/fuzz-results | ✅ |
| 不与 Slither 交叉验证 | ✅ |
| 不生成定制化测试 | ✅ |
| 不添加 severity/is_false_positive | ✅ |
| 不预留多分析器统一格式 | ✅ |
| Alembic 迁移仅添加 fuzzing_results | ✅ |
