# SolidiGuard Sprint 6 — LLM 审计 Worker（含 RAG 检索增强） 设计文档

> Source: Sprint 6 指令 + Sprint 4 Chroma 集成 + 现有代码库
> 每项设计决策标注来源

---

## 1. Implementation Approach

基于 Sprint 1 文件上传 + Sprint 4 Chroma 向量集合，增量添加 LLM 审计功能：
- 统一 LLM 客户端支持 OpenAI/Anthropic/本地模型 (来源: Sprint 6 第3条)
- Celery 任务执行合约摘要 + 关键函数提取 + RAG 检索 + LLM 审计 (来源: Sprint 6 第3条)
- 结果存入 llm_audit_results 表 (来源: Sprint 6 第3条)
- 不生成报告文件，不导出，不排版 (来源: Sprint 6 强制停止规则)

---

## 2. LLM Client Abstraction (统一 LLM 接口)

### Environment Variables
- `LLM_PROVIDER`: `openai` | `anthropic` | `local` (来源: Sprint 6 第3条)
- `LLM_API_KEY`: API key for the provider
- `LLM_MODEL_NAME`: model identifier (e.g. `gpt-4o`, `claude-3-5-sonnet-20241022`)
- `LLM_BASE_URL`: base URL override (for OpenAI-compatible local models)

### Implementation
- 使用 httpx HTTP 调用，不直接引用特定 SDK (来源: Sprint 6 第4条)
- 统一接口: `chat_completion(messages: list[dict], temperature: float = 0.2) -> str`
- OpenAI: POST `{base_url}/chat/completions`
- Anthropic: POST `https://api.anthropic.com/v1/messages` (带 `x-api-key` header)
- Local: 同 OpenAI 格式（兼容接口）

---

## 3. New Table: llm_audit_results

| Column | Type | Constraint |
|--------|------|------------|
| id | Integer | PK, autoincrement |
| project_id | Integer | FK → projects.id |
| contract_name | String(200) | not null |
| function_name | String(200) | nullable |
| vulnerability_description | Text | not null |
| severity | String(50) | not null |
| suggested_fix | Text | nullable |
| gas_optimization | Text | nullable |
| created_at | DateTime | server_default=now |

来源: Sprint 6 第3条 — "新建表 llm_audit_results"

注意：无 report_id 外键、无 exported 状态字段 (来源: Sprint 6 反推禁止规则)

---

## 4. Celery Task: run_llm_audit

### Input
- `project_id`: int

### Logic

#### Step 1: 获取合约文件
- 从 project_files 表获取所有 .sol 文件路径
- 读取每个文件内容

#### Step 2: 生成合约摘要（调用 LLM）
- 对每个合约，调用 LLM 生成结构化摘要：
  - 接口说明
  - 状态变量
  - 函数签名与功能描述
- Prompt 模板:
  ```
  Analyze this Solidity contract and provide a structured summary:
  1. Interface description
  2. State variables
  3. Function signatures and descriptions
  
  Contract: {contract_content}
  
  Output JSON: {"interface": "...", "state_variables": [...], "functions": [...]}
  ```

#### Step 3: 提取关键函数
- 使用正则匹配函数定义
- 筛选包含以下关键词的函数体: `transfer`, `call`, `delegatecall`, `selfdestruct`, `send`, `approve`, `transferFrom`
- 提取函数名 + 函数体代码

#### Step 4: RAG 检索
- 对每个关键函数代码，调用 get_embedding() 生成向量
- 查询 Chroma collection `vulnerability_patterns`，Top-K=5（可配置，环境变量 RAG_TOP_K）
- 获取相似漏洞的 title + description + code_example

#### Step 5: 构造审计 Prompt 并调用 LLM
- Prompt 模板:
  ```
  You are a smart contract security auditor. Analyze this function for vulnerabilities.
  
  Contract Summary: {summary}
  
  Function: {function_name}
  Code:
  {function_code}
  
  Similar known vulnerabilities:
  {retrieved_vulnerabilities}
  
  Identify potential vulnerabilities, risk severity (high/medium/low/informational), 
  and provide fix suggestions. Also suggest gas optimizations if applicable.
  
  Output JSON: [{"vulnerability": "...", "severity": "...", "fix": "...", "gas_optimization": "..."}]
  ```

#### Step 6: 存储结果
- 解析 LLM 输出 JSON
- 对每个发现，创建 llm_audit_results 记录

来源: Sprint 6 第3条

---

## 5. API Endpoints

### POST /api/v1/projects/{id}/llm-audit
- 验证 project 存在
- 派发 Celery `run_llm_audit` 任务
- 返回 `{"status": "audit_started", "project_id": id}`

### GET /api/v1/projects/{id}/llm-audit-results
- 查询 llm_audit_results WHERE project_id = id
- 返回列表

来源: Sprint 6 第3条

---

## 6. Files to Create/Modify

| File | Action | Purpose |
|------|--------|---------|
| backend/app/models.py | MODIFY | 新增 LLMAuditResult 模型 |
| backend/app/services/llm_client.py | NEW | 统一 LLM 客户端 |
| backend/app/api/llm_audit.py | NEW | LLM 审计 API 端点 |
| backend/app/api/router.py | MODIFY | 注册 llm_audit 路由 |
| backend/app/tasks/run_llm_audit.py | NEW | LLM 审计 Celery 任务 |
| backend/alembic/versions/007_add_llm_audit_results.py | NEW | 迁移文件 |
| .env.example | MODIFY | 添加 LLM_* 变量 |
| docker-compose.yml | MODIFY | 添加 LLM_* 环境变量 |

---

## 7. Design Compliance Checklist

| Sprint 6 Requirement | Status |
|----------------------|--------|
| 统一 LLM 客户端 (OpenAI/Anthropic/local) | ✅ |
| .env.example 添加 LLM_* 变量 | ✅ |
| Celery run_llm_audit 任务 | ✅ |
| 合约摘要生成 | ✅ |
| 关键函数提取 (transfer/call/delegatecall/selfdestruct) | ✅ |
| RAG 检索 Chroma vulnerability_patterns Top-K | ✅ |
| 审计 Prompt 构造 | ✅ |
| llm_audit_results 表 | ✅ |
| POST /api/v1/projects/{id}/llm-audit | ✅ |
| GET /api/v1/projects/{id}/llm-audit-results | ✅ |
| 不直接引用特定 SDK | ✅ |
| 使用 httpx HTTP 调用 | ✅ |
| 不生成报告文件 | ✅ |
| 不导出功能 | ✅ |
| 不排版 | ✅ |
| Chroma 使用 Sprint 4 已创建的 collection | ✅ |
| 不预留 report_id / exported 字段 | ✅ |
| 不设计通用漏洞仪表板结构 | ✅ |
| Alembic 迁移仅添加 llm_audit_results | ✅ |
