# SolidiGuard Sprint 4 — 公共漏洞库同步与 Chroma 向量库准备 设计文档

> Source: Sprint 4 指令 + SWC Registry 实际 API 调研 + Sprint 0 代码库
> 每项设计决策标注来源

---

## 1. SWC Registry 数据源调研（实际 API 格式）

经验证，SWC Registry 数据存储在 GitHub 仓库 `SmartContractSecurity/SWC-registry`：
- **条目列表**: `GET https://api.github.com/repos/SmartContractSecurity/SWC-registry/contents/entries/docs`
- **单条目内容**: `GET https://api.github.com/repos/SmartContractSecurity/SWC-registry/contents/entries/docs/SWC-{id}.md`
- **格式**: Markdown 文件，Base64 编码（GitHub API 返回 `content` 字段为 Base64）
- **Markdown 结构**:
  - `# Title` — 漏洞标题
  - `## Relationships` — CWE 等关联
  - `## Description` — 漏洞描述
  - `## Remediation` — 修复建议
  - `## Samples` — 含 Solidity 代码示例（```solidity 代码块）

来源: Sprint 4 第3条 + 实际 API 调研（不得假设不存在的字段）

---

## 2. New Table: vulnerability_entries

| Column | Type | Constraint |
|--------|------|------------|
| id | Integer | PK, autoincrement |
| swc_id | String(20) | not null, unique (e.g. "SWC-101") |
| title | String(500) | not null |
| description | Text | not null |
| severity | String(50) | nullable (SWC 未统一定义 severity，设为 nullable) |
| code_example | Text | nullable |
| created_at | DateTime | server_default=now |
| updated_at | DateTime | server_default=now, onupdate=now |

来源: Sprint 4 第3条 — "新建表 vulnerability_entries：id, swc_id, title, description, severity, code_example, created_at, updated_at"

---

## 3. New Celery Task: sync_swc

### Logic
1. 调用 GitHub API 列出 `entries/docs/` 目录下所有 `SWC-*.md` 文件
2. 对每个文件：
   - 获取文件内容（Base64 解码）
   - 解析 Markdown 提取：`# Title` → title, `## Description` → description, `## Samples` 中的 ```solidity 代码块 → code_example
   - Upsert 到 `vulnerability_entries` 表（基于 swc_id 去重）
3. 遍历所有 `vulnerability_entries`，拼接 `title + description + code_example` 作为文本
4. 调用嵌入模型生成向量
5. 存入 Chroma collection `vulnerability_patterns`

### Embedding 调用
- 从环境变量读取 `EMBEDDING_PROVIDER`（支持 `openai`、`local`）
- 从环境变量读取 `EMBEDDING_API_KEY` 和 `EMBEDDING_BASE_URL`
- 使用 `chromadb` 内置的 embedding function 或通过 HTTP 调用外部 API
- **不得硬编码提供商**（来源: Sprint 4 证据层约束）

---

## 4. Chroma Integration

- 使用 `chromadb` Python 客户端（内嵌模式，无需独立服务）
- Collection 名称: `vulnerability_patterns`
- 存储路径: `./chroma_data/`（可通过环境变量 `CHROMA_PERSIST_DIR` 配置）
- 每条记录: id=swc_id, documents=拼接文本, embeddings=向量

来源: Sprint 4 第3条

---

## 5. New API Endpoint

### POST /api/v1/knowledge/sync
- **Purpose**: 手动触发漏洞库同步
- **Logic**: 派发 Celery `sync_swc` 任务
- **Response**: `{"status": "sync_started"}`

来源: Sprint 4 第3条

---

## 6. Files to Create/Modify

| File | Action | Purpose |
|------|--------|---------|
| backend/app/models.py | MODIFY | 新增 VulnerabilityEntry 模型 |
| backend/app/api/knowledge.py | NEW | POST /api/v1/knowledge/sync |
| backend/app/api/router.py | MODIFY | 注册 knowledge 路由 |
| backend/app/tasks/sync_swc.py | NEW | Celery sync_swc 任务 + Chroma 向量化 |
| backend/app/services/embedding.py | NEW | 嵌入模型抽象层（读取环境变量选择提供商） |
| backend/app/services/chroma_client.py | NEW | Chroma 客户端初始化 + collection 管理 |
| backend/alembic/versions/005_add_vulnerability_entries.py | NEW | 迁移文件 |
| backend/requirements.txt | MODIFY | 添加 chromadb, httpx |
| .env.example | MODIFY | 添加 EMBEDDING_PROVIDER, EMBEDDING_API_KEY, EMBEDDING_BASE_URL, CHROMA_PERSIST_DIR |
| docker/Dockerfile | MODIFY | 安装 chromadb 依赖 |

---

## 7. Design Compliance Checklist

| Sprint 4 Requirement | Status |
|----------------------|--------|
| vulnerability_entries 表 | ✅ |
| sync_swc 任务从 SWC Registry 拉取 | ✅ |
| Chroma collection vulnerability_patterns | ✅ |
| 嵌入模型用户可配置 | ✅ |
| .env.example 添加 EMBEDDING_* 变量 | ✅ |
| POST /api/v1/knowledge/sync | ✅ |
| 不实现检索接口 | ✅ |
| 不与审计逻辑关联 | ✅ |
| Alembic 迁移仅创建 vulnerability_entries | ✅ |
| 未添加 related_swc_ids 等关联字段 | ✅ |
| 嵌入模型不硬编码 | ✅ |
