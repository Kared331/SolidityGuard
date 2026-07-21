# 架构审查与沙箱试运行 规格说明

## Why
SolidGuard 是一个 Solidity 智能合约审计平台，集成了 Slither 静态分析、Foundry Fuzz 测试和 LLM 深度审计能力。需要全面审查其架构质量、代码安全性、可维护性，并通过沙箱试运行发现运行时问题。

## What Changes
本次为只读审查，不修改生产代码。产出包括：
- 架构层面问题汇总（模块划分、依赖关系、数据流、并发设计）
- 代码层面问题汇总（Bug、安全漏洞、代码质量、测试覆盖）
- 沙箱试运行报告（环境搭建、运行时错误、API 行为验证）
- 风险分级与改进建议

## Impact
- Affected specs: 无（本次为纯审查任务）
- Affected code: 审查覆盖 `backend/app/`（全部模块）、`frontend/src/`、`tests/`、`docker/`、`docker-compose.yml`

## ADDED Requirements

### Requirement: 架构审查
系统 SHALL 对 SolidGuard 项目的整体架构进行全面审查。

#### Scenario: 审查模块划分与依赖关系
- **WHEN** 审查者分析 `backend/app/` 下的模块结构
- **THEN** 应识别出 services→tasks→api 的分层是否合理，跨层依赖是否符合设计原则
- **AND** 应识别循环依赖、紧耦合等架构问题

#### Scenario: 审查数据流设计
- **WHEN** 审查者追踪从用户上传到报告生成的完整数据流
- **THEN** 应评估异步任务链（Celery Chain）设计和状态管理是否满足幂等性、可观测性要求
- **AND** 应评估 Pipeline 是否实际工作（当前各阶段需手动触发，非自动链式执行）

#### Scenario: 审查并发与线程安全
- **WHEN** 审查者分析多线程场景（FastAPI async + Celery workers）
- **THEN** 应识别 ChromaDB 客户端的线程安全实现是否正确
- **AND** 应识别 Embedding 模型加载的 double-check locking 是否正确
- **AND** 应识别 Token Budget Manager 的内存单例在 worker 多进程场景下的问题

### Requirement: 代码审查
系统 SHALL 对 SolidGuard 项目的源代码进行全面审查，识别 Bug、安全漏洞和代码质量问题。

#### Scenario: 发现运行时 Bug
- **WHEN** 审查者检查代码与测试的一致性
- **THEN** 应发现 `_sanitize_source_code` 函数在 llm_audit.py 中缺失，导致 `test_engines.py` 和 `test_security.py` 导入失败（**BUG**）
- **AND** 应发现 `settings` 在 `config.py` 第79行作为模块级单例创建，当 `.env` 缺失或 API_KEY 为空时会在导入阶段直接抛出 `ValueError`，阻止整个应用启动（**BUG**）

#### Scenario: 安全漏洞审查
- **WHEN** 审查者分析输入验证、路径遍历防护、注入防护
- **THEN** 应确认 Zip Slip 防护在 UploadEngine 中正确实现
- **AND** 应确认报告下载的路径遍历防护正确实现
- **AND** 应识别 API Key 认证的潜在绕过风险（空 API_KEY 时完全跳过认证）
- **AND** 应检查 `verify_api_key` 依赖在所有路由上的一致覆盖

#### Scenario: 代码质量审查
- **WHEN** 审查者分析代码规范、错误处理、可测试性
- **THEN** 应评估异常处理是否一致（部分用 try/except，部分任异常传播）
- **AND** 应评估是否有足够的类型注解覆盖
- **AND** 应识别硬编码值（如 `"text/plain"` 作为 Solidity MIME 类型、端口号、超时值）

### Requirement: 沙箱试运行
系统 SHALL 在沙箱环境中尝试运行 SolidGuard 项目，记录所有遇到的问题。

#### Scenario: 环境搭建验证
- **WHEN** 审查者尝试启动项目
- **THEN** 应验证 `docker-compose.yml` 是否可以成功构建和启动所有服务
- **AND** 应验证 `.env` 文件从 `.env.example` 创建后是否需要额外配置
- **AND** 应记录启动过程中的所有错误和警告

#### Scenario: API 功能验证
- **WHEN** 审查者对运行中的服务发送 API 请求
- **THEN** 应验证 `/health` 端点返回正确的健康状态
- **AND** 应验证项目上传（含 `.sol` 文件和 `.zip` 文件）是否正常工作
- **AND** 应验证各分析触发端点是否返回正确的 task_id

#### Scenario: 运行测试套件
- **WHEN** 审查者运行测试
- **THEN** 应验证 `pytest` 可以正常执行（如果环境允许）
- **AND** 应记录测试失败的数量和原因

## MODIFIED Requirements
无（本次为纯审查任务，不修改现有功能）

## REMOVED Requirements
无
