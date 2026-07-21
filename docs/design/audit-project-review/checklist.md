# 审查验收检查清单

## 架构审查

- [x] 模块划分与依赖关系分析已完成，识别出所有架构问题
- [x] 跨层依赖问题（如 service 直接 import tasks）已记录并有改进建议
- [x] models 层业务逻辑泄漏情况已识别
- [x] schemas 层完整性已验证，所有 API 返回都有对应 schema
- [x] 异步任务数据流（upload→Slither→Fuzz→LLM→Report）完整追踪
- [x] Pipeline 链式执行问题（当前各阶段独立触发）已识别
- [x] ProjectStatus 状态机缺陷（缺少失败状态、重入支持）已分析
- [x] Celery beat 调度器配置已检查

## 并发与线程安全

- [x] ChromaDB singleton double-check locking 正确性已验证
- [x] Embedding 模型 singleton double-check locking 正确性已验证
- [x] TokenBudgetManager 多进程隔离问题已识别
- [x] LLM circuit breaker 多 worker 隔离问题已识别
- [x] httpx.Client 生命周期管理已审查

## Bug 与缺陷

- [x] `_sanitize_source_code` 缺失导致测试导入失败已确认 **[沙箱验证]**
- [x] `settings = Settings()` 模块级实例化导入时崩溃问题已确认 **[沙箱验证]**
- [x] 跨文件 schema/response 一致性已验证
- [x] 数据库 session 管理泄漏风险已检查

## 安全性

- [x] 空 API_KEY 导致认证完全跳过的风险已分析
- [x] verify_api_key 路由覆盖完整性已验证
- [x] Zip Slip 防护（UploadEngine + project_service 双层）正确性已验证
- [x] 报告下载路径遍历防护正确性已验证
- [x] InputSanitizer prompt injection 防护充分性已评估
- [x] 文件上传大小限制在 API 层面已验证

## 代码质量

- [x] 异常处理模式一致性已评估
- [x] 类型注解覆盖率已评估
- [x] 所有硬编码值已列出
- [x] 未使用导入/死代码已检查
- [x] 测试覆盖率和质量已评估

## 沙箱试运行

- [x] `docker compose config` 配置验证通过
- [x] Docker 环境可用（Docker v29.6.1 + Compose v5.2.0）
- [x] 本地 Python 环境无法启动（Settings 模块级崩溃）
- [x] `.env` 与 pydantic-settings 不兼容问题已记录
- [x] 测试套件执行结果已记录（4 通过 / 18 失败 / 20 错误）

## 最终报告

- [x] 所有问题按严重程度分类汇总
- [x] 每个问题包含复现步骤和修复建议
- [x] 总体架构评分和代码质量评分已给出
