## Sprint 1：LLM 调用稳定性与基础容错

### 目标
修复 Critical 问题，让 LLM 相关调用能容忍临时性故障，杜绝单个 API 失败导致整个审计崩溃，并消除配置缺失造成的运行时崩溃。

### 输入
当前 SolidGuard 代码库（后端 `backend/` 及其子模块）。关键文件实际路径：
- `backend/app/services/llm_client.py`
- `backend/app/services/embedding.py`
- `backend/app/services/engine/llm_audit.py`（审计核心逻辑，`LLMAuditEngine.execute()`）
- `backend/app/tasks/run_llm_audit.py`（Celery 任务入口，委托给 `LLMAuditEngine`）
- `backend/app/services/report_generator.py`
- `backend/app/config.py`

### 实施约束（本 Sprint 通用）
- **前置验证规则**：修改任何文件前，必须先读取该文件确认当前状态。若 Sprint 描述的修改已存在，标记为"已完成"并跳过，不得重复实现。
- **路径自适应规则**：若文档路径与实际不符，以实际项目结构为准，先搜索确认再操作。
- **迁移完整性规则**：将内联代码提取为独立模块时，必须同时移除原内联代码并更新所有引用方。
- **Sprint 间增量修改规则**：修改任何文件前，先确认该文件是否被之前 Sprint 修改过。若已被修改（如 Sprint 2 修改 `embedding.py` 时该文件已含 Sprint 1 的重试逻辑），必须在最新产出上增量修改，绝不可基于原始代码重新实现而导致前序 Sprint 的修改丢失。
- **Sprint 自包含规则**：当前 Sprint 所有任务完成后，项目必须处于可运行状态（应用能启动、现有测试通过、不引入新的 import 错误）。不允许留下"等下一个 Sprint 修复"的半成品。

### 任务清单（必须全部完成）

#### 1. 为 LLM 调用添加重试与断路器（蓝图问题 1, 6, 15, 16）
- **文件**：`backend/app/services/llm_client.py`
- **前置确认**：当前 `chat_completion` 已有 `@retry` 装饰器（参数 min=2, max=30, 条件为 `HTTPStatusError`/`ConnectError`/`ReadTimeout`）。超时 `timeout=120` 已满足蓝图要求，无需修改。
- **修改要求**：
  - 调整现有 `tenacity` 重试装饰器参数以匹配蓝图 5.1：
    - 重试条件增加 `httpx.WriteTimeout`
    - 指数退避参数调整为 min=4 秒, max=60 秒
  - 在模块级实现一个简单的断路器计数器 `_llm_failure_count`，阈值 5。连续失败达阈值后抛出 `RuntimeError("LLM circuit breaker open")`，成功调用后重置计数。
  - 必须记录重试日志（使用标准 `logging`，级别 WARNING）。
  - 移除函数内每次 `httpx.post()` 的做法，改为使用**模块级** `httpx.Client` 属性（在函数外定义 `_client = httpx.Client(timeout=120)`），实现真正的连接复用（蓝图问题 15）。注意：函数体内 `with httpx.Client() as client:` 仍会每次创建新实例，不能达到复用目的。
- **完成标准**：模拟网络故障时，`chat_completion` 能重试并最终成功或熔断；日志可见重试信息。

#### 2. 为 Embedding 调用添加重试与连接复用（蓝图问题 1, 7, 15, 16）
- **文件**：`backend/app/services/embedding.py`
- **前置确认**：当前超时 `timeout=60` 已满足蓝图要求，无需修改。当前无重试机制。
- **修改要求**：
  - 使用 `tenacity` 为 `get_embedding` 函数添加重试（针对 HTTP 错误和连接错误），重试 3 次，指数退避 min=2 秒, max=30 秒。
  - 将 `httpx.post()` 改为模块级 `httpx.Client` 属性（函数外定义），实现连接复用。
  - 不在此 Sprint 添加速率限制（留待 Sprint 2）。
- **完成标准**：embedding 服务临时中断后可自动恢复。

#### 3. 消除无界 LLM 调用（蓝图问题 2, 3）
- **前置确认**：`backend/app/services/engine/llm_audit.py` 的 `LLMAuditEngine.execute()` 已实现按关键函数逐个调用（`for func in key_functions` 循环，约第 198 行），附带 RAG 上下文。**审计阶段无需修改**。本任务仅处理报告润色阶段。
- **文件**：
  - `backend/app/services/report_generator.py`（`polish_with_llm` 函数，约第 111 行）
- **修改要求**：
  - 修改 `polish_with_llm`，不再一次发送所有 findings，而是**分批处理**（每批最多 5 条 finding）。将批次结果拼接。
  - 若任何单次调用失败（已被重试覆盖），不应影响其他批次，最终报告中应标记该部分为"审计失败"。
- **完成标准**：报告润色能分批进行；LLM 调用次数增多但每次 token 可控。

#### 4. 修复配置缺失导致运行时崩溃（蓝图问题 4）
- **文件**：`backend/app/config.py`；新增依赖 `pydantic-settings` 到 `requirements.txt`
- **前置确认**：项目支持 `LLM_PROVIDER=local`（使用本地 sentence-transformers，无需 API Key）。当前 `config.py` 无必填项验证。
- **修改要求**：
  - 引入 `pydantic-settings`，创建 `Settings` 类，定义所有环境变量并提供默认值或条件验证。
    - 必填项：`DATABASE_URL`
    - 条件必填：`LLM_API_KEY` 仅在 `LLM_PROVIDER` 非 `local` 时必填（使用 `model_validator`）
    - 需纳入的现有变量：`EMBEDDING_API_KEY`、`REDIS_URL`、`LLM_MODEL_NAME`、`EMBEDDING_MODEL_NAME`、`APP_PORT`、`MAX_UPLOAD_SIZE_MB`、`CLEANUP_DAYS`、`API_KEY`、`LOG_LEVEL` 等
  - 应用启动时加载配置，缺少必填项立即报错并退出，而不是在具体调用时崩溃。
  - 保留原 `config.py` 中其他合理部分（如日志配置的 `logging.basicConfig`），仅更改环境变量读取方式。
  - 所有引用旧 `from app.config import XXX` 的模块需同步更新为 `from app.config import settings; settings.XXX`。
- **完成标准**：`LLM_PROVIDER` 非 `local` 且不设置 `LLM_API_KEY` 时启动报清晰错误；`LLM_PROVIDER=local` 时无需 API Key 即可启动。

### 输出
修改后的代码库，通过现有测试（如有），且能通过以下验证：
- 模拟网络波动后 LLM/Embedding 调用能恢复。
- 报告润色被分解为分批处理。
- 未配置 API Key 时启动即报错。

### 强制停止规则
**完成以上所有修改后，立即停止生成任何文本。不得输出总结、下一步建议、优化提示或任何形式的前瞻内容。**

### 证据层约束
- 所有重试参数、断路器逻辑必须严格对应蓝图第 5 节提供的模式或问题描述，不自行变更策略。
- 分批大小（5 条）依据蓝图描述，不得随意调整。

### 反推禁止规则
- 禁止在此 Sprint 添加任何速率限制、令牌预算或输入验证代码。
- 禁止为"未来的插件化重试"设计抽象基类或配置项。
- 任何代码修改如果包含"for future use"或类似注释，必须删除。