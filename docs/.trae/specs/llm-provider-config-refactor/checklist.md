# 验收检查清单

## 配置文件解析器

- [x] `llm/config.py` 中定义了 `AppConfig`、`DatabaseConfig`、`RedisConfig`、`RagConfig`、`ModelConfig`、`ProviderConfig`、`SolidGuardConfig` Pydantic 模型
- [x] `load_config(path)` 函数能正确读取和校验 JSON 配置文件
- [x] `${ENV_VAR}` 语法能正确替换为环境变量值
- [x] 递归解析支持嵌套对象和数组中的 `${VAR}` 引用
- [x] 配置文件不存在时抛出明确的 FileNotFoundError
- [x] JSON 格式错误时抛出明确的 ValueError 并包含校验失败原因
- [x] `${VAR}` 引用不存在的环境变量时抛出明确错误
- [x] `get_config()` 单例函数首次调用加载，后续返回缓存

## OpenAI Provider

- [x] `OpenAIProvider` 继承 `AbstractLLMProvider`
- [x] `chat_completion` 使用 httpx POST `/chat/completions` 端点
- [x] 请求 Header 包含 `Authorization: Bearer {api_key}`
- [x] 响应解析正确提取 `choices[0].message.content` 和 `usage`
- [x] `health_check` 能正确检测 Provider 可用性
- [x] `get_model_name` 返回当前配置的模型名

## Anthropic Provider

- [x] `AnthropicProvider` 继承 `AbstractLLMProvider`
- [x] `chat_completion` 使用 httpx POST `/messages` 端点
- [x] 请求 Header 包含 `x-api-key` 和 `anthropic-version: 2023-06-01`
- [x] system_prompt 映射为 Anthropic 的 `system` 参数
- [x] user_prompt 映射为 `messages` 数组中的 user message
- [x] 响应解析正确提取 `content[0].text`
- [x] token 统计正确映射：`input_tokens` + `output_tokens` → `total_tokens`
- [x] `health_check` 能正确检测 Provider 可用性

## ProviderRegistry 重构

- [x] `register_from_config(config)` 方法能根据配置文件注册所有 Provider
- [x] `api` 字段为 `"openai"` 时实例化 `OpenAIProvider`
- [x] `api` 字段为 `"anthropic-messages"` 时实例化 `AnthropicProvider`
- [x] 名为 "default" 的 Provider 设为默认
- [x] 未指定 provider 时使用 default

## config.py 重写

- [x] `Settings` 类不再继承 `pydantic_settings.BaseSettings`
- [x] `Settings` 类从 `llm/config.py` 的 `load_config()` 读取配置
- [x] 不再包含 `LLM_PROVIDER`、`LLM_API_KEY`、`LLM_MODEL_NAME`、`LLM_BASE_URL`
- [x] 不再包含 `EMBEDDING_PROVIDER`、`EMBEDDING_API_KEY`、`EMBEDDING_MODEL_NAME`、`EMBEDDING_BASE_URL`
- [x] 不再包含 `_validate_api_keys` model_validator
- [x] 不再包含 `model_config` 中的 `env_file` 配置
- [x] `settings` 单例和 `get_settings()` 接口保持不变
- [x] `logger` 导出保持不变
- [x] 其他 Settings 字段（DATABASE_URL、REDIS_URL、APP_PORT 等）正确映射

## llm_client.py 重构

- [x] 移除所有 `os.environ` 读取
- [x] `chat_completion(messages, temperature)` 函数签名不变
- [x] 返回值格式 `(str, dict)` 不变（content, usage）
- [x] 从配置文件获取 Provider 配置并路由到对应 API 适配器
- [x] circuit breaker 逻辑保留
- [x] tenacity 重试逻辑保留
- [x] httpx 连接复用保留

## embedding.py 重构

- [x] 移除所有 `os.environ` 读取（除 local 模型路径外）
- [x] `get_embedding(text)` 函数签名不变
- [x] 返回值格式 `list[float]` 不变
- [x] 从配置文件获取 Embedding Provider 配置
- [x] tenacity 重试逻辑保留
- [x] Semaphore 限流逻辑保留
- [x] 本地模型 fallback 逻辑保留

## 部署配置

- [x] `solidguard.json.example` 包含完整配置（app、database、redis、rag、providers 含 OpenAI 和 Anthropic 示例）
- [x] `.env.example` 仅保留 Docker Compose 和前端构建变量
- [x] `.env.example` 包含 `SOLIDGUARD_CONFIG=./solidguard.json`
- [x] `docker-compose.yml` api 服务已移除应用层环境变量
- [x] `docker-compose.yml` worker 服务已移除应用层环境变量
- [x] `docker-compose.yml` 挂载 `solidguard.json` 到容器
- [x] `docker-compose.yml` 设置 `SOLIDGUARD_CONFIG` 环境变量指向容器内配置文件路径

## 测试

- [x] `conftest.py` 包含测试用 JSON 配置文件 fixture
- [x] `test_engines.py` 测试通过
- [x] `test_services.py` 测试通过
- [x] `test_security.py` 测试通过
- [x] `test_api.py` 测试通过
