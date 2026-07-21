## Sprint 2：输入安全、速率限制与响应校验

### 目标
解决 High 级别问题：注入防御、embedding 速率限制、响应验证、token 感知截断及部分 Medium 问题（贪婪正则），并杜绝静默错误。

### 输入
Sprint 1 产出的代码库（已具备稳定重试、分片调用、配置校验）。

### 实施约束（本 Sprint 通用）
- **前置验证规则**：修改任何文件前，必须先读取该文件确认当前状态。若 Sprint 描述的修改已存在，标记为"已完成"并跳过，不得重复实现。
- **路径自适应规则**：若文档路径与实际不符，以实际项目结构为准，先搜索确认再操作。
- **迁移完整性规则**：当任务要求将内联代码提取为独立模块/类时，必须同时移除原内联代码并在所有引用处更新为新的导入路径。不得产生新旧两套实现并存的情况。
- **Sprint 间增量修改规则**：修改任何文件前，先确认该文件是否被之前 Sprint 修改过。若已被修改（如 `embedding.py` 在 Sprint 1 中已添加重试逻辑），必须在 Sprint 1 的产出上增量修改，绝不可基于原始代码重新实现而导致前序 Sprint 的修改丢失。
- **Sprint 自包含规则**：当前 Sprint 所有任务完成后，项目必须处于可运行状态（应用能启动、现有测试通过、不引入新的 import 错误）。不允许留下"等下一个 Sprint 修复"的半成品。

### 任务清单（必须全部完成）

#### 1. 集成输入验证与注入防御（蓝图问题 5, 8）
- **新增文件**：`backend/app/services/input_sanitizer.py`
- **需移除的旧代码**：`backend/app/services/engine/llm_audit.py` 中的 `_INJECTION_PATTERNS`（第 63-72 行）和 `_sanitize_source_code` 函数（第 75-89 行）。这两处定义在现有代码中：`_INJECTION_PATTERNS` 仅定义未使用（死代码），`_sanitize_source_code` 仅做字符截断+去除非打印字符，未调用注入检测。必须用新的 `InputSanitizer` 替换，而非并存。
- **需修改的调用方**：`backend/app/services/engine/llm_audit.py` 中两处调用 `_sanitize_source_code`（约第 167 行和第 228 行），改为 `from app.services.input_sanitizer import InputSanitizer` 并调用 `InputSanitizer.sanitize_code`。
- **修改要求**：
  - 实现 `InputSanitizer` 类（参考蓝图 7.1），包含预定义注入模式列表（8 种正则，与当前 `_INJECTION_PATTERNS` 一致但须集成到 `sanitize_code` 方法中实际生效）。
  - `sanitize_code` 方法：检测注入模式，若匹配则替换为 `[REDACTED]` 并返回 `injection_detected=True`；同时进行 token 感知截断（约 8000 token，按 4 char/token 估算即 32000 字符），移除不可打印字符。返回 `(str, bool)` 元组。
  - **接入审计流程**：在 `llm_audit.py` 调用 LLM 审计之前，对所有合约源码调用 `InputSanitizer.sanitize_code`。若检测到注入，需在审计结果中增加一条警告记录。
  - 不改变其他模块（如报告生成）的输入。
- **完成标准**：发送包含 "ignore all previous instructions" 的合约，该字符串被替换且审计结果中包含警告；旧的内联 `_sanitize_source_code` 和 `_INJECTION_PATTERNS` 已移除。

#### 2. 为 Embedding 调用添加速率限制（蓝图问题 7）
- **文件**：`backend/app/services/embedding.py`
- **前置确认**：`embedding.py` 支持 `provider="local"` 路径（本地 sentence-transformers），local 模式不需要速率限制。Semaphore 仅包裹 API 调用分支。
- **修改要求**：
  - 在模块级增加 `threading.Semaphore(5)`，限制并发 embedding 调用数（适用于同步代码；若异步则使用 `asyncio.Semaphore`，依据实际情况选择）。
  - 仅在 `provider == "openai"` 分支中获取信号量，`provider == "local"` 分支直接调用。
  - 调用 API 之前获取信号量，调用后释放。
  - 不在此 Sprint 实现全局限流器。
- **完成标准**：并发调用 embedding 时不超过 5 个同时进行；local 模式不受影响。

#### 3. 验证 Embedding 响应（蓝图问题 8）
- **文件**：`backend/app/services/embedding.py`
- **修改要求**：
  - 在 `get_embedding` 返回前，检查响应 JSON 是否包含 `data` 字段且长度 > 0，且 `embedding` 是列表类型。
  - 若不满足，抛出 `ValueError` 并记录详细错误。
  - 仅校验 `provider == "openai"` 分支的 API 响应，不改变 `provider == "local"` 分支。
- **完成标准**：异常响应（如 API 返回空数据）会触发重试或明确失败，而非静默使用错误数据。

#### 4. 修复字符截断为 Token 感知截断（蓝图问题 9, 13）
- **文件**：`backend/app/services/engine/llm_audit.py`（`_parse_llm_json` 函数，约第 48 行 Stage 3 回退正则）
- **前置确认**：Token 感知截断由 Sprint 2 任务 1 的 `InputSanitizer` 统一处理（32000 字符），本任务不再重复修改截断逻辑。
- **修改要求**：
  - **修复贪婪正则**（问题 13）：找到 `_parse_llm_json` 中 Stage 3 的正则 `\[.*\]`（第 48 行），改为非贪婪 `\[.*?\]`。注意 Stage 2（第 38 行）已经是 `\[.*?\]`，仅 Stage 3 需要修改。此外在项目中搜索其他使用 `\[.*\]` 贪婪匹配 JSON 数组的代码一并修改。
- **完成标准**：含多个 JSON 数组的 LLM 响应能被正确解析，不会越界匹配。

#### 5. 收紧异常捕获（蓝图问题 14 部分）
- **范围**：仅在本次修改涉及的文件中，将无意义的 `except Exception` 替换为具体异常（如 `httpx.HTTPError`, `ValueError`, `json.JSONDecodeError`）。不要求全局搜索，只处理 Sprint 2 改动的文件。
- **完成标准**：被修改文件中不再出现裸 `except` 或 `except Exception`（除非有合理理由，如最外层兜底日志）。

### 输出
修改后的代码库，注入防御生效，embedding 调用受控，响应经过校验，截断和正则问题修复。

### 强制停止规则
**以上任务完成后立即停止，不得生成总结、建议或任何前瞻性语句。**

### 证据层约束
- 注入模式必须严格使用蓝图中列出的 8 种，不得自行添加。
- 速率限制值（5）出自蓝图设计，不得更改。
- 任何关于"可配置注入模式"的设计均被禁止。

### 反推禁止规则
- 禁止为了集成 Token 预算而修改本次的代码结构。
- 禁止在输入验证器中添加审计无关的过滤规则（如屏蔽 URL）。
- 禁止将 `InputSanitizer` 设计成插件式以"方便未来扩展"。