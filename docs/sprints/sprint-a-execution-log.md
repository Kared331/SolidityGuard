# Sprint A 执行日志

**日期：** 2026-06-09 12:02
**状态：** ✅ 完成 (7/7)

## 修复清单

| Fix | 描述 | 文件 | 状态 |
|-----|------|------|------|
| #3 | 路由前缀冲突 | `projects.py`, `analysis.py`, `llm_audit.py`, `router.py` | ✅ |
| #2 | SSE 认证绕过 | `router.py` | ✅ |
| #1 | Zip Slip/Tar Slip | `upload.py` | ✅ |
| #4 | 报告路径遍历 | `report_service.py` | ✅ |
| #5 | LLM Prompt 注入 | `llm_audit.py` | ✅ |
| #6 | 前端 API Key 泄露 | `client.ts`, `nginx.conf`, `Dockerfile`, `docker-compose.yml` | ✅ |
| #7 | FP 项目作用域 | `feedback.py`, `detection_service.py`, `analysis_service.py`, `report_generator.py`, `010_add_feedback_project_scope.py` | ✅ |

## 详细改动

### Fix #3 — 路由前缀冲突
- `projects.py`: `@router.post("/projects")` → `@router.post("")`
- `projects.py`: `@router.get("/projects/{project_id}/files")` → `@router.get("/{project_id}/files")`
- `analysis.py`: `@router.post("/projects/{project_id}/analyze")` → `@router.post("/{project_id}/analyze")`
- `analysis.py`: `@router.get("/projects/{project_id}/analyses")` → `@router.get("/{project_id}/analyses")`
- `llm_audit.py`: `@router.post("/projects/{project_id}/llm-audit")` → `@router.post("/{project_id}/llm-audit")`
- `llm_audit.py`: `@router.get("/projects/{project_id}/llm-audit-results")` → `@router.get("/{project_id}/llm-audit-results")`

### Fix #2 — SSE 认证绕过
- `router.py`: `events_router` 注册时添加 `dependencies=[Depends(verify_api_key)]`

### Fix #1 — Zip Slip/Tar Slip
- `upload.py`: ZIP 提取从 `zf.extractall()` 改为 `zf.extract(member, project_dir)` 逐个提取
- `upload.py`: TAR 提取从 `tf.extractall()` 改为 `tf.extract(member, project_dir)` 逐个提取
- 每个 member 先通过 `_is_safe_path()` 检查后才提取

### Fix #4 — 报告路径遍历
- `report_service.py`: 添加 `resolved_path.relative_to(reports_base)` 路径校验
- 路径不在 reports 目录内时返回 403 Forbidden

### Fix #5 — LLM Prompt 注入
- `llm_audit.py`: 添加 `_sanitize_source_code()` 函数（截断、去非打印字符）
- 添加 `_INJECTION_PATTERNS` 正则列表检测注入模式
- Prompt 中使用 `<CONTRACT_CODE>` / `<FUNCTION_CODE>` XML 分隔符
- 添加 system role 明确指示 LLM 忽略代码中的指令

### Fix #6 — 前端 API Key 泄露
- `client.ts`: 移除 `VITE_API_KEY` 引用，不再在 JS bundle 中包含 API Key
- `nginx.conf`: 添加 `proxy_set_header X-API-Key "$API_KEY"` 由 nginx 代理注入
- `Dockerfile`: 移除 `VITE_API_KEY` build arg，使用 `envsubst` 在运行时注入
- `docker-compose.yml`: frontend 服务添加 `API_KEY` 环境变量

### Fix #7 — FP 项目作用域
- `feedback.py`: 添加 `project_id` 外键字段（ForeignKey → projects.id）
- `detection_service.py`: 通过 Detection → AnalysisResult → project_id 自动派生 project_id
- `analysis_service.py`: FP 查询添加 `.where(FalsePositiveFeedback.project_id == project_id)`
- `report_generator.py`: FP 查询添加 `.filter(FalsePositiveFeedback.project_id == project_id)`
- `010_add_feedback_project_scope.py`: Alembic 迁移（添加列 + 回填数据 + 创建索引）

## 验证结果

所有 7 项修复均已通过文件内容验证，代码改动符合预期。
