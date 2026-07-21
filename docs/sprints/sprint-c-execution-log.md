# Sprint C 执行日志

**日期：** 2026-06-09 12:45
**状态：** ✅ 完成 (8/8)
**执行工具：** OpenCode (xiaomi-token-plan-cn/mimo-v2.5-pro) + --dangerously-skip-permissions

## 修复清单

| Fix | 描述 | 文件 | 状态 |
|-----|------|------|------|
| #17 | LLM JSON 解析加固 | `llm_audit.py` | ✅ |
| #18 | polish_with_llm 验证 | `report_generator.py` | ✅ |
| #19 | 状态机 DB 约束 | `012_add_state_machine_constraints.py` | ✅ |
| #20 | .gitignore 清理 | `.gitignore` | ✅ |
| #21 | 死代码删除 | `models_old.py` 已删除 | ✅ |
| #22 | 健康检查扩展 | `main.py` | ✅ |
| #23 | Docker 文件权限 | `Dockerfile` | ✅ |
| #24 | 优雅停机 | `main.py`, `celery_app.py` | ✅ |

## 详细改动

### Fix #17 — LLM JSON 解析加固
- 添加 `_parse_llm_json()` 辅助函数，4 阶段解析管道：
  1. 直接 `json.loads()`
  2. 从 markdown 代码块提取
  3. 正则回退
  4. 日志警告
- 替换了原来脆弱的纯正则解析

### Fix #18 — polish_with_llm 验证
- 添加 `_EXPECTED_KEYS` 集合验证
- 检查结果是 dict，包含 slither_findings/fuzzing_findings/llm_findings
- 每个 key 必须是 list 类型
- 验证失败时返回原始 findings

### Fix #19 — 状态机 DB 约束
- 新迁移 `012_add_state_machine_constraints.py`
- CHECK 约束限制 projects.status 只允许 uploaded/processing/ready
- 添加 version 列（默认 0）支持乐观锁
- 创建 status 索引

### Fix #20 — .gitignore 清理
- 添加显式 `*.pyc`、`*.pyo`、`*.pyd` 模式

### Fix #21 — 死代码删除
- `backend/app/models_old.py` 已删除

### Fix #22 — 健康检查扩展
- `/health` 现在检查 PostgreSQL + Redis
- 每个检查 3 秒超时
- 返回 `{"status": "ok/degraded", "checks": {"postgres": "ok", "redis": "ok"}}`
- 失败时返回 503

### Fix #23 — Docker 文件权限
- COPY 命令添加 `--chown=appuser:appuser`
- 移除重复的 `chown` 块

### Fix #24 — 优雅停机
- `main.py`: 添加 `shutdown_event()` 处理器，关闭 `async_engine`
- `celery_app.py`: 添加 `worker_shutdown_timeout=30`
