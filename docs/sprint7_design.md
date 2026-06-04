# SolidiGuard Sprint 7 — 报告生成与导出 设计文档

> Source: Sprint 7 指令 + Sprint 2/3/5/6 代码库现状
> 每项设计决策标注来源

---

## 1. Implementation Approach

聚合 Slither、Fuzzing、LLM 审计三类结果，排除误报条目，经 LLM 润色排版后导出 HTML/PDF/Word：
- Jinja2 模板生成结构化报告草稿 (来源: Sprint 7 第3条)
- LLM 润色排版，补充代码优化建议和 Gas 优化建议 (来源: Sprint 7 第3条)
- WeasyPrint 导出 PDF，python-docx 导出 Word (来源: Sprint 7 第3条 + 技术栈约束)
- 不生成 UI 组件，不设计 React 渲染格式 (来源: Sprint 7 反推禁止规则)

---

## 2. Data Aggregation Strategy

### Sources
1. **Slither detections**: 从 `detections` 表查询，排除 `detection_ref` 存在于 `false_positive_feedbacks` 的条目 (来源: Sprint 3 + Sprint 7 第3条)
2. **Fuzzing failures**: 从 `fuzzing_results` 表查询，提取 `failures_json` 中的失败项 (来源: Sprint 5)
3. **LLM audit findings**: 从 `llm_audit_results` 表查询 (来源: Sprint 6)

### Unified Report Data Structure
```json
{
  "project_name": "...",
  "generated_at": "...",
  "slither_findings": [
    {"check_name": "...", "description": "...", "impact": "...", "confidence": "...", "file_path": "..."}
  ],
  "fuzzing_findings": [
    {"test_name": "...", "counterexample": "...", "raw_output_preview": "..."}
  ],
  "llm_findings": [
    {"contract_name": "...", "function_name": "...", "vulnerability_description": "...", "severity": "...", "suggested_fix": "...", "gas_optimization": "..."}
  ]
}
```

---

## 3. LLM Polish Strategy

### Prompt Template
```
You are a professional smart contract security report writer. 
Given the following audit findings from Slither static analysis, fuzzing, and LLM audit,
polish the report with professional formatting. For each finding, add:
1. Code optimization suggestions
2. Gas optimization suggestions (use existing gas_optimization field if available)

{aggregated_findings_json}

Output a polished JSON report with the same structure but enhanced descriptions.
```

来源: Sprint 7 证据层约束 — "必须基于本 Sprint 已注入的漏洞数据"

---

## 4. Export Formats

### HTML
- Jinja2 模板渲染 (来源: Sprint 7 第3条)
- 内嵌 CSS 样式

### PDF
- 先渲染 HTML，再用 WeasyPrint 转换 (来源: 技术栈约束)

### Word
- 使用 python-docx 从报告内容生成 (来源: 技术栈约束)

---

## 5. New Table: reports

| Column | Type | Constraint |
|--------|------|------------|
| id | Integer | PK, autoincrement |
| project_id | Integer | FK → projects.id |
| title | String(500) | not null |
| content_json | JSONB | not null (润色后的结构化内容) |
| file_paths | JSON | nullable ({"html": "...", "pdf": "...", "word": "..."}) |
| created_at | DateTime | server_default=now |

来源: Sprint 7 第3条

注意：无 user_rating、comment 字段 (来源: Sprint 7 反推禁止规则)

---

## 6. Celery Task: generate_report

### Input
- `project_id`: int
- `output_format`: str ("html" / "pdf" / "word")

### Logic
1. 从三个结果表聚合数据，排除误报
2. 使用 Jinja2 模板生成结构化报告草稿
3. 调用 LLM 润色排版
4. 保存润色后内容到 content_json
5. 根据 format 生成对应文件：
   - html: Jinja2 渲染
   - pdf: HTML → WeasyPrint
   - word: python-docx
6. 存储文件路径到 file_paths，创建 reports 记录

来源: Sprint 7 第3条

---

## 7. API Endpoints

### POST /api/v1/projects/{id}/report
- Body: `{"format": "html" | "pdf" | "word"}`
- 验证 project 存在
- 派发 generate_report 任务
- 返回 `{"status": "report_started", "project_id": id, "format": format}`

### GET /api/v1/reports/{report_id}/download?format=...
- 查询 report 记录
- 从 file_paths 获取对应格式文件路径
- 返回 FileResponse

来源: Sprint 7 第3条

---

## 8. Files to Create/Modify

| File | Action | Purpose |
|------|--------|---------|
| backend/app/models.py | MODIFY | 新增 Report 模型 |
| backend/app/services/report_generator.py | NEW | 报告生成逻辑（聚合+模板+导出） |
| backend/app/services/templates/ | NEW | Jinja2 报告模板目录 |
| backend/app/api/reports.py | NEW | 报告 API 端点 |
| backend/app/api/router.py | MODIFY | 注册 reports 路由 |
| backend/app/tasks/generate_report.py | NEW | 报告生成 Celery 任务 |
| backend/alembic/versions/008_add_reports.py | NEW | 迁移文件 |
| backend/requirements.txt | MODIFY | 添加 jinja2, weasyprint, python-docx |
| docker/Dockerfile | MODIFY | 安装 WeasyPrint 系统依赖 |

---

## 9. Design Compliance Checklist

| Sprint 7 Requirement | Status |
|----------------------|--------|
| 聚合 Slither/Fuzzing/LLM 三类结果 | ✅ |
| 排除误报条目 | ✅ |
| Jinja2 模板生成报告草稿 | ✅ |
| LLM 润色排版 | ✅ |
| 代码优化建议 | ✅ |
| Gas 优化建议 | ✅ |
| 导出 HTML | ✅ |
| 导出 PDF (WeasyPrint) | ✅ |
| 导出 Word (python-docx) | ✅ |
| reports 表 (id, project_id, title, content_json, file_paths, created_at) | ✅ |
| POST /api/v1/projects/{id}/report | ✅ |
| GET /api/v1/reports/{id}/download | ✅ |
| 文件存储在 reports/ 目录 | ✅ |
| 不生成 UI 组件 | ✅ |
| 不设计 React 渲染格式 | ✅ |
| 不添加 user_rating/comment | ✅ |
| LLM 提示基于已注入数据 | ✅ |
| Alembic 迁移仅添加 reports | ✅ |
