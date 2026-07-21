## Sprint 3：成本控制、ChromaDB 韧性及剩余债务清偿

### 目标
解决 Medium 级别问题：实现令牌预算管理，增强 ChromaDB 容错，验证摘要质量，清理异常处理，并简单改善上下文丢失。

### 输入
Sprint 2 产出的代码库（已具备注入防御、速率限制、响应校验等）。

### 实施约束（本 Sprint 通用）
- **前置验证规则**：修改任何文件前，必须先读取该文件确认当前状态。若 Sprint 描述的修改已存在，标记为"已完成"并跳过，不得重复实现。
- **路径自适应规则**：若文档路径与实际不符，以实际项目结构为准，先搜索确认再操作。
- **迁移完整性规则**：将内联代码提取为独立模块时，必须同时移除原内联代码并更新所有引用方。
- **Sprint 间增量修改规则**：修改任何文件前，先确认该文件是否被之前 Sprint 修改过。若已被修改（如 `llm_client.py` 在 Sprint 1 中已添加断路器，`llm_audit.py` 在 Sprint 2 中已接入 InputSanitizer），必须在最新产出上增量修改，绝不可基于原始代码重新实现而导致前序 Sprint 的修改丢失。
- **Sprint 自包含规则**：当前 Sprint 所有任务完成后，项目必须处于可运行状态（应用能启动、现有测试通过、不引入新的 import 错误）。不允许留下"等下一个 Sprint 修复"的半成品。

### 任务清单（必须全部完成）

#### 1. 实现并接入 Token 预算管理（蓝图问题 2, 3 关联，以及蓝图 6.1）
- **前置步骤 0（本任务的前置依赖）**：当前 `chat_completion()` 仅返回 `str`（文本内容），不返回 token `usage` 信息。Token 预算需要 usage 数据。**必须先修改 `backend/app/services/llm_client.py` 的 `chat_completion` 函数**：
  - 将返回值从 `str` 改为 `tuple[str, dict]`，即 `(content, usage)`，其中 `usage` 为 LLM 响应中的 `"usage"` 字段（含 `prompt_tokens`, `completion_tokens`, `total_tokens`）
  - 若响应中无 `usage` 字段，根据 `max_tokens` 参数估算 usage
  - **同步适配以下 3 处调用方**（解包元组）：
    - `backend/app/services/engine/llm_audit.py` 第 192 行：`summary_text = chat_completion(summary_messages)` → `summary_text, _ = chat_completion(summary_messages)`（摘要生成暂不消耗预算）
    - `backend/app/services/engine/llm_audit.py` 第 257 行：`response_text = chat_completion(audit_messages)` → `response_text, usage = chat_completion(audit_messages)`（审计调用需跟踪预算）
    - `backend/app/services/report_generator.py` 第 123 行：`response_text = chat_completion(messages)` → `response_text, _ = chat_completion(messages)`（报告润色暂不消耗预算，或视需要跟踪）
- **新增文件**：`backend/app/services/token_budget.py`
- **修改文件**：`backend/app/services/engine/llm_audit.py`（实际审计逻辑，`LLMAuditEngine.execute()`）
- **修改要求**：
  - 实现 `TokenBudgetManager` 类（参考蓝图 6.1），跟踪每个项目的 token 消耗和调用次数。支持配置最大 token 数（默认 500,000）和最大调用次数（默认 100）。使用内存字典（单进程）即可。
  - 在审计任务开始时，检查项目预算，若无剩余则终止审计并返回错误信息"Token budget exceeded"。
  - 每次 LLM 调用后，使用 `chat_completion` 返回的 `usage` 更新预算。
  - 预算耗尽时应友好停止，不可导致任务崩溃。
- **完成标准**：模拟大量审计请求，当达到预算后审计任务返回预算超支错误，不影响其他项目。

#### 2. ChromaDB 查询重试与 Fallback（蓝图问题 12）
- **文件**：
  - `backend/app/services/chroma_client.py`（新增 `query_vulnerabilities` 函数）
  - `backend/app/services/engine/llm_audit.py`（修改调用方，约第 211 行）
- **前置确认**：当前 `chroma_client.py` 仅有 `get_chroma_client()` 和 `get_vulnerability_collection()` 两个函数，没有 `query_vulnerabilities`。实际的 `collection.query()` 调用在 `llm_audit.py` 第 211 行。当前已有 fallback（第 217 行），但缺少重试。
- **修改要求**：
  - **在 `chroma_client.py` 中新增 `query_vulnerabilities` 函数**：使用 `tenacity` 添加重试（`chromadb.errors.ChromaError` 及通用 `Exception` 保底），重试 3 次，指数退避 min=1, max=10 秒。
  - 若所有重试失败，或返回结果中无 `documents`，返回安全的空结果结构 `{'documents': [[]], 'metadatas': [[]]}`，并记录警告日志。
  - **修改 `llm_audit.py`**：将第 211 行的直接 `collection.query()` 调用替换为 `from app.services.chroma_client import query_vulnerabilities` 并调用 `query_vulnerabilities(collection, embedding, top_k)`。移除第 217 行的内联 fallback（由 `query_vulnerabilities` 统一处理）。
- **完成标准**：ChromaDB 服务宕机时，审计不会中断，该部分检索结果为空但不报错，且日志可见重试记录。

#### 3. 校验 LLM 生成摘要（蓝图问题 11）
- **文件**：`backend/app/services/engine/llm_audit.py`（`LLMAuditEngine.execute()` 中生成合约摘要的逻辑处，约第 189-193 行）
- **修改要求**：
  - 在获取 LLM 生成的合约摘要后，检查摘要是否为空或长度过短（例如 < 20 字符）。若无效，使用**简单规则生成备选摘要**（如提取合约名 + "合约，包含 N 个函数"），并记录警告。
  - 不重试 LLM 生成摘要（避免额外成本）。
- **完成标准**：LLM 摘要失败时，报告中使用备选摘要，不会出现空白摘要。

#### 4. 全局收紧异常捕获（蓝图问题 14 完成）
- **范围**：搜索项目中所有 `.py` 文件，将 `except Exception` 替换为具体异常或至少添加日志输出，除非明确需要兜底（如顶层 Celery 任务入口的 `try/except Exception`）。
- **重点文件**：`backend/app/services/engine/llm_audit.py`、`backend/app/services/llm_client.py`、`backend/app/services/embedding.py`、`backend/app/tasks/run_llm_audit.py`。彻底消除裸异常吞噬。
- **完成标准**：代码中不再有隐藏的错误吞噬。

#### 5. 轻微改善 Embedding 上下文丢失（蓝图问题 10）
- **文件**：`backend/app/services/engine/llm_audit.py`（`LLMAuditEngine.execute()` 中调用 `get_embedding` 处，约第 201 行）
- **修改要求**：
  - 在为每个函数生成嵌入时，在函数代码前拼接合约名称和继承关系（如 `// Contract: Token, inherits Ownable\n`），使嵌入向量包含合约级别信息。
  - 不改变 RAG 检索逻辑。
- **完成标准**：相同函数在不同合约中可能检索到更相关的漏洞。

### 输出
最终的代码库，具备令牌预算控制、ChromaDB 容错、摘要质量保障、异常透明和上下文增强。

### 强制停止规则
**所有任务完成，整个 LLM 调用链修复系列结束。不得生成总结、未来规划或任何多余内容。**

### 证据层约束
- 令牌预算的默认值必须来自蓝图（500k token, 100 calls），不得自行调整。
- 摘要备选方案必须极简，不能引入新的 LLM 调用。

### 反推禁止规则
- 禁止将预算管理器设计为持久化或分布式版本。
- 禁止为 ChromaDB 添加缓存或高级故障转移策略。
- 禁止因"为未来微服务准备"而改动架构。