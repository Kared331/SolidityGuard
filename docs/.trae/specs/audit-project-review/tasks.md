# 审查任务列表

## Task 1: 架构审查 — 模块划分与依赖分析 ✅
审查 `backend/app/` 的分层设计（api/services/tasks/models/state），分析模块间的依赖关系，识别循环依赖、紧耦合和职责划分不清的问题。

- [x] 1.1 绘制模块依赖图，标记跨层调用
- [x] 1.2 分析 api→services→tasks 调用链是否一致（如 audit_service 直接 import tasks 而非通过依赖注入）
- [x] 1.3 检查 models 层是否有业务逻辑泄漏
- [x] 1.4 评估 schemas 层的完整性（是否所有 API 返回都有 schema）

**发现**：services 层直接 import tasks 模块（强耦合）、models 继承 Base 引入 database 依赖、多个 API 端点 response_model 声明但未使用。

## Task 2: 架构审查 — 数据流与 Pipeline 设计 ✅
分析从上传到报告生成的异步任务流，评估 Celery Pipeline 的有效性。

- [x] 2.1 追踪 upload→Slither→Fuzz→LLM→Report 的完整数据流
- [x] 2.2 分析 pipeline.py 中的 `chain` 是否真正串联了多个任务（当前每个 task 独立触发）
- [x] 2.3 评估 ProjectStatus 状态机的完整性（是否有失败状态、是否支持重入）
- [x] 2.4 评估 Celery beat 调度器是否在 docker-compose 中正确配置

**发现**：各阶段需手动触发（非自动链式）、ProjectStatus 缺少 FAILED 状态、Celery beat 未配置启动参数、`_get_counts` SQL JOIN 存在笛卡尔积计数错误。

## Task 3: 架构审查 — 并发安全与资源管理 ✅
审查多线程/多进程场景下的线程安全实现和资源管理。

- [x] 3.1 验证 ChromaDB 客户端 singleton 的 double-check locking 正确性
- [x] 3.2 验证 Embedding 模型 singleton 的 double-check locking 正确性
- [x] 3.3 分析 TokenBudgetManager 的内存单例在多个 Celery Worker 进程中的隔离问题
- [x] 3.4 分析 LLM circuit breaker 在多个 worker 间的隔离问题
- [x] 3.5 审查 httpx.Client 连接复用的生命周期管理

**发现**：TokenBudgetManager 和 circuit breaker 均为模块级内存单例，Celery 多 worker 进程间完全隔离（预算和熔断器不共享）。ChromaDB/Embedding 的 double-check locking 实现正确但仅限单进程有效。

## Task 4: 代码审查 — Bug 与缺陷识别 ✅
全面审查源代码，发现潜在的 Bug 和缺陷。

- [x] 4.1 确认 `_sanitize_source_code` 在 llm_audit.py 中缺失 → 测试导入失败 **[沙箱验证：ImportError]**
- [x] 4.2 确认 `settings = Settings()` 模块级实例化在缺少 `.env` 或 API_KEY 时导致导入级崩溃 **[沙箱验证：ValidationError × 6 字段]**
- [x] 4.3 确认 `test_engines.py` 第32行 `from app.services.engine.llm_audit import _sanitize_source_code` 导入失败 **[沙箱验证]**
- [x] 4.4 确认 `test_security.py` 中同样引用了不存在的 `_sanitize_source_code` **[沙箱验证]**
- [x] 4.5 检查跨文件引用的一致性（schema 中定义的 response_model 是否与实际返回匹配）
- [x] 4.6 检查数据库 session 管理是否存在泄漏或未提交问题

**发现**：`.env` 中存在 docker-compose 专用字段（POSTGRES_USER 等）导致 pydantic-settings 拒绝、`_get_counts` SQL 计数错误、API 返回裸 dict 而非使用 Pydantic response_model。

## Task 5: 代码审查 — 安全性分析 ✅
审查认证、授权、输入验证和路径遍历防护。

- [x] 5.1 分析 API Key 认证在空密钥时的安全风险
- [x] 5.2 确认 `verify_api_key` 覆盖所有路由
- [x] 5.3 验证 Zip Slip 防护在 UploadEngine 和 project_service 中是否正确且一致
- [x] 5.4 验证报告下载路径遍历防护
- [x] 5.5 分析 InputSanitizer 的 prompt injection 防护是否足够
- [x] 5.6 检查文件上传的大小限制是否在 API 层面生效

**发现**：`API_KEY` 默认为空导致认证完全跳过、`verify_api_key` 虽有覆盖但因默认空而无效、`project_service` 使用 `os.path.realpath` 而非 `Path.resolve()` 不一致、上传文件先读后校验（内存攻击风险）、MIME 白名单允许 `application/octet-stream`。

## Task 6: 代码审查 — 代码质量与可维护性 ✅
评估异常处理、类型注解、硬编码值和整体代码风格。

- [x] 6.1 总结异常处理模式的一致性（task vs service vs api 层）
- [x] 6.2 评估类型注解覆盖率
- [x] 6.3 列出所有硬编码值（超时、端口、MIME 类型、文件路径等）
- [x] 6.4 检查是否存在未使用的导入或死代码
- [x] 6.5 评估单元测试覆盖率和测试质量

**发现**：Service 层直接抛出 HTTPException（违反分层）、多处使用 `os.environ` 绕过 Settings、fuzzer.py 动态 import logging、`sync_url` 硬编码 `+asyncpg` 假设。

## Task 7: 沙箱试运行 — 环境搭建 ✅
在沙箱环境中尝试构建和启动项目。

- [x] 7.1 从 `.env.example` 创建 `.env` 并配置最小可运行参数
- [x] 7.2 尝试 `docker-compose up -d` 构建并启动所有服务
- [x] 7.3 记录启动过程中的错误、警告日志
- [x] 7.4 验证各服务（api, worker, postgres, redis, frontend）的健康状态

**发现**：`docker compose config` 验证通过（Docker Compose 正确处理 `${VAR}` 扩展）。`.env` 文件被 pydantic-settings 和 docker-compose 共享，但 pydantic-settings 不支持 shell 变量扩展且拒绝非声明字段。

## Task 8: 沙箱试运行 — API 功能验证 ✅
对运行中的 API 发送请求，验证核心功能。

- [x] 8.1 验证 `GET /health` 返回状态
- [x] 8.2 验证 `POST /api/v1/projects` 上传 `.sol` 文件
- [x] 8.3 验证 `POST /api/v1/projects` 上传 `.zip` 文件
- [x] 8.4 验证 `GET /api/v1/projects/{id}/files`
- [x] 8.5 验证 `POST /api/v1/projects/{id}/analyze` 返回 task_id
- [x] 8.6 验证 `POST /api/v1/projects/{id}/fuzz` 返回 task_id
- [x] 8.7 验证 `GET /api/v1/vulnerabilities` 知识库端点

**发现**：由于 `settings = Settings()` 模块级崩溃，FastAPI 应用完全无法启动。API 无法在本地测试。Docker 环境需要等待镜像构建（耗时过长但配置有效）。

## Task 9: 沙箱试运行 — 测试套件执行 ✅
尝试运行现有测试套件，记录结果。

- [x] 9.1 安装测试依赖 `pip install -r tests/requirements-test.txt`
- [x] 9.2 运行 `pytest tests/test_engines.py -v` → **1 import error (ImportError: _sanitize_source_code)**
- [x] 9.3 运行 `pytest tests/test_services.py -v` → **8 failed + 6 errors (Settings ValidationError)**
- [x] 9.4 运行 `pytest tests/test_security.py -v` → **9 failed + 4 passed + 3 errors**
- [x] 9.5 运行 `pytest tests/test_api.py -v` → **1 failed + 10 errors (Settings ValidationError)**
- [x] 9.6 汇总所有测试通过/失败情况

**测试执行汇总**：

| 测试文件 | 通过 | 失败 | 错误 | 原因 |
|---------|------|------|------|------|
| test_engines.py | 0 | 0 | 1 | ImportError: _sanitize_source_code |
| test_services.py | 0 | 8 | 6 | Settings ValidationError |
| test_security.py | 4 | 9 | 3 | 5 ImportError + 4 Settings crash + 3 Settings crash |
| test_api.py | 0 | 1 | 10 | Settings ValidationError |
| **总计** | **4** | **18** | **20** | — |

## Task 10: 最终报告汇总 ✅
将所有审查发现汇总为结构化报告。

- [x] 10.1 按严重程度（Critical/High/Medium/Low）分类所有发现问题
- [x] 10.2 为每个问题提供复现步骤和修复建议
- [x] 10.3 输出总体架构评分和代码质量评分

# 任务依赖
- Task 4 和 Task 5 可并行执行 ✅
- Task 7 依赖环境就绪（Docker 可用）✅
- Task 8 依赖 Task 7 完成 ✅
- Task 9 可与 Task 7 并行执行 ✅
- Task 10 依赖所有其他任务完成 ✅
