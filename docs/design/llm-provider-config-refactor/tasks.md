# Tasks

- [x] Task 1: 新增 JSON 配置文件解析器 `backend/app/llm/config.py`
  - [ ] 1.1 定义 Pydantic 模型：`AppConfig`、`DatabaseConfig`、`RedisConfig`、`RagConfig`、`ModelConfig`、`ProviderConfig`、`SolidGuardConfig`
  - [ ] 1.2 实现 `${ENV_VAR}` 语法解析：递归遍历配置值，将 `${VAR}` 替换为 `os.environ[VAR]`
  - [ ] 1.3 实现 `load_config(path)` 函数：读取 JSON 文件 → 递归解析 `${VAR}` → Pydantic 校验 → 返回配置对象
  - [ ] 1.4 实现配置文件不存在或格式错误时的明确错误提示
  - [ ] 1.5 实现 `get_config()` 单例函数：首次调用时加载，后续返回缓存

- [x] Task 2: 新增 OpenAI Provider 实现 `backend/app/llm/provider/openai_provider.py`
  - [ ] 2.1 继承 `AbstractLLMProvider`，实现 `chat_completion`、`get_model_name`、`health_check`
  - [ ] 2.2 使用 httpx 发送 `/chat/completions` 请求
  - [ ] 2.3 适配 `LLMResponse` 数据结构（content, model, usage）
  - [ ] 2.4 从 ProviderConfig 读取 baseUrl、apiKey、model

- [x] Task 3: 新增 Anthropic Provider 实现 `backend/app/llm/provider/anthropic_provider.py`
  - [ ] 3.1 继承 `AbstractLLMProvider`，实现 `chat_completion`、`get_model_name`、`health_check`
  - [ ] 3.2 使用 httpx 发送 `/messages` 请求，Header 包含 `x-api-key` 和 `anthropic-version: 2023-06-01`
  - [ ] 3.3 将 `system_prompt + user_prompt` 映射为 Anthropic Messages 格式（system 参数 + messages 数组）
  - [ ] 3.4 解析响应：提取 `content[0].text` 和 `usage.input_tokens/output_tokens`
  - [ ] 3.5 适配 `LLMResponse` 数据结构

- [x] Task 4: 重构 ProviderRegistry，启动时从配置文件自动注册
  - [ ] 4.1 修改 `provider_registry.py`，新增 `register_from_config(config)` 方法
  - [ ] 4.2 根据每个 Provider 的 `api` 字段实例化对应的 Provider 类（openai → OpenAIProvider，anthropic-messages → AnthropicProvider）
  - [ ] 4.3 将配置文件中名为 "default" 的 Provider 设为默认
  - [ ] 4.4 移除模块级 `provider_registry` 硬编码单例，改为延迟初始化

- [x] Task 5: 重写 `backend/app/config.py`
  - [ ] 5.1 移除 pydantic-settings 的 `BaseSettings` 继承，改为普通 dataclass 或 Pydantic BaseModel
  - [ ] 5.2 删除所有 LLM/Embedding 相关字段（`LLM_PROVIDER`、`LLM_API_KEY`、`LLM_MODEL_NAME`、`LLM_BASE_URL`、`EMBEDDING_PROVIDER`、`EMBEDDING_API_KEY`、`EMBEDDING_MODEL_NAME`、`EMBEDDING_BASE_URL`）
  - [ ] 5.3 删除 `_validate_api_keys` model_validator
  - [ ] 5.4 删除 `model_config` 中的 `env_file` 配置
  - [ ] 5.5 `Settings` 类改为从 `llm/config.py` 的 `load_config()` 读取配置
  - [ ] 5.6 保持 `settings` 单例和 `get_settings()` 接口不变
  - [ ] 5.7 保持 `logger` 导出不变

- [x] Task 6: 重构 `backend/app/services/llm_client.py`
  - [ ] 6.1 移除所有 `os.environ` 读取（第 55-57 行）
  - [ ] 6.2 `chat_completion` 函数改为从配置文件获取 Provider 配置
  - [ ] 6.3 根据 Provider 的 `api` 字段路由到 OpenAI 或 Anthropic 调用逻辑
  - [ ] 6.4 保持函数签名 `chat_completion(messages, temperature) -> Tuple[str, dict]` 不变
  - [ ] 6.5 保留 circuit breaker、tenacity 重试、httpx 连接复用逻辑

- [x] Task 7: 重构 `backend/app/services/embedding.py`
  - [ ] 7.1 移除所有 `os.environ` 读取（第 47-52 行）
  - [ ] 7.2 `get_embedding` 函数改为从配置文件获取 Embedding Provider 配置
  - [ ] 7.3 保持函数签名 `get_embedding(text) -> list[float]` 不变
  - [ ] 7.4 保留 tenacity 重试、Semaphore 限流、本地模型 fallback 逻辑

- [x] Task 8: 更新 `llm/rag/retriever.py`，移除 `os.environ` 读取
  - [ ] 8.1 将 `CHROMA_DIR` 和 `TOP_K` 从 `os.environ` 改为从 Settings 读取

- [x] Task 9: 创建示例配置文件和更新部署配置
  - [ ] 9.1 创建 `solidguard.json.example`，包含完整配置示例（app、database、redis、rag、providers 含 OpenAI 和 Anthropic）
  - [ ] 9.2 更新 `.env.example`：仅保留 Docker Compose 和前端构建变量（POSTGRES_*、REDIS_PASSWORD、VITE_API_BASE_URL），新增 `SOLIDGUARD_CONFIG=./solidguard.json`
  - [ ] 9.3 更新 `docker-compose.yml`：api 和 worker 服务中移除应用层环境变量，挂载 `solidguard.json`，新增 `SOLIDGUARD_CONFIG` 环境变量

- [x] Task 10: 更新测试
  - [ ] 10.1 更新 `tests/conftest.py`：创建测试用 JSON 配置文件 fixture
  - [ ] 10.2 更新 `tests/test_engines.py`：适配新配置加载方式
  - [ ] 10.3 更新 `tests/test_services.py`：适配新配置加载方式
  - [ ] 10.4 更新 `tests/test_security.py` 和 `tests/test_api.py`：适配新配置加载方式
  - [ ] 10.5 运行测试验证所有改动

# 任务依赖
- Task 1（配置解析器）是 Task 2、3、4、5 的前置
- Task 2（OpenAI Provider）和 Task 3（Anthropic Provider）可并行执行
- Task 4（Registry 重构）依赖 Task 1、2、3
- Task 5（config.py 重写）依赖 Task 1
- Task 6、7（services 重构）依赖 Task 4、5
- Task 8（retriever 更新）依赖 Task 5
- Task 9（部署配置）依赖 Task 1
- Task 10（测试）依赖所有其他任务
