# 配置驱动化重构 Spec

## Why

当前 SolidGuard 的配置体系存在以下问题：
1. **配置分散**：`.env` 环境变量 + `pydantic-settings` + 代码中 `os.environ` 直读，三层配置来源混乱
2. **无法支持多 Provider**：环境变量只能表达单一 LLM/Embedding Provider，无法动态切换
3. **无法记录模型元数据**：contextWindow、maxTokens、reasoning 能力等信息无处存放
4. **代码绕过 Settings**：`llm_client.py` 和 `embedding.py` 直接用 `os.environ` 读取，绕过 pydantic Settings
5. **旧代码未接入新体系**：项目中已存在 `backend/app/llm/` 模块（ProviderRegistry、AbstractLLMProvider 等抽象），但旧的 `services/llm_client.py` 和 `services/embedding.py` 未接入

需要统一配置入口，将所有应用配置从 `.env` 环境变量迁移到 JSON 配置文件驱动。Docker Compose 和前端构建专用变量（`POSTGRES_*`、`REDIS_PASSWORD`、`VITE_API_BASE_URL`）保留在 `.env` 中。

## What Changes

- **BREAKING**：`config.py` 中 `Settings` 类从 pydantic-settings 环境变量读取改为从 JSON 配置文件读取
- **BREAKING**：删除 `Settings` 中所有 LLM/Embedding 相关字段
- **BREAKING**：删除 `_validate_api_keys` model_validator
- **BREAKING**：删除 `model_config` 中的 `env_file` 配置
- 重写 `backend/app/config.py`：从 JSON 配置文件加载全部应用配置
- 新增 `backend/app/llm/config.py`：JSON 配置文件解析器，支持 `${ENV_VAR}` 语法引用环境变量（仅用于敏感信息如 API Key）
- 新增 `backend/app/llm/provider/openai_provider.py`：OpenAI 兼容 Provider 实现
- 新增 `backend/app/llm/provider/anthropic_provider.py`：Anthropic Messages API Provider 实现
- 重构 `backend/app/services/llm_client.py`：从 `os.environ` 切换为读取配置文件，按 `api` 字段路由到对应 Provider
- 重构 `backend/app/services/embedding.py`：从 `os.environ` 切换为读取配置文件
- 重构 `backend/app/llm/provider/provider_registry.py`：启动时从配置文件自动注册 Provider
- 更新 `.env.example`：仅保留 Docker Compose 和前端构建变量
- 更新 `docker-compose.yml`：移除应用层环境变量传递，挂载 JSON 配置文件
- 创建 `solidguard.json.example`：完整示例配置文件
- 更新测试文件：适配新的配置加载方式

## Impact

- Affected specs: 无（新功能）
- Affected code:
  - `backend/app/config.py` — 重写配置加载逻辑
  - `backend/app/services/llm_client.py` — 核心重写
  - `backend/app/services/embedding.py` — 核心重写
  - `backend/app/llm/config.py` — 新增
  - `backend/app/llm/provider/openai_provider.py` — 新增
  - `backend/app/llm/provider/anthropic_provider.py` — 新增
  - `backend/app/llm/provider/provider_registry.py` — 重构
  - `backend/app/llm/rag/retriever.py` — 移除 `os.environ` 读取
  - `.env.example` — 更新
  - `docker-compose.yml` — 更新
  - `solidguard.json.example` — 新增
  - `tests/` — 适配

## JSON 配置文件结构

```json
{
  "app": {
    "apiKey": "${API_KEY}",
    "port": 8000,
    "maxUploadSizeMb": 50,
    "cleanupDays": 30,
    "logLevel": "INFO",
    "corsOrigins": "http://localhost:3000,http://localhost:5173",
    "rateLimit": "60/minute"
  },
  "database": {
    "url": "${DATABASE_URL}",
    "poolSize": 10,
    "maxOverflow": 20,
    "poolRecycle": 3600
  },
  "redis": {
    "url": "${REDIS_URL}"
  },
  "rag": {
    "chromaPersistDir": "./chroma_data",
    "topK": 5
  },
  "providers": {
    "default": {
      "apiKey": "${LLM_API_KEY}",
      "baseUrl": "https://api.openai.com/v1",
      "api": "openai",
      "models": [
        {
          "id": "gpt-4o",
          "name": "GPT-4o",
          "maxTokens": 4096,
          "contextWindow": 128000
        }
      ]
    },
    "xiaomi": {
      "apiKey": "${XIAOMI_API_KEY}",
      "baseUrl": "https://api.xiaomi.com/v1",
      "api": "anthropic-messages",
      "models": [
        {
          "id": "mimo-v2.5-pro",
          "name": "Mimo V2.5 Pro",
          "reasoning": true,
          "input": ["text"],
          "maxTokens": 32000,
          "contextWindow": 1048576
        }
      ]
    }
  }
}
```

**配置文件路径**：通过环境变量 `SOLIDGUARD_CONFIG` 指定，默认 `./solidguard.json`

## ADDED Requirements

### Requirement: JSON 配置文件驱动

系统 SHALL 通过 JSON 配置文件管理所有应用配置和 LLM/Embedding Provider 配置。

#### Scenario: 配置文件加载
- **WHEN** 应用启动时
- **THEN** 系统读取 `SOLIDGUARD_CONFIG` 环境变量指定的 JSON 配置文件（默认 `./solidguard.json`）
- **AND** 解析所有配置节（app、database、redis、rag、providers）
- **AND** 支持 `${ENV_VAR}` 语法在敏感字段中引用环境变量

#### Scenario: 配置文件不存在
- **WHEN** 配置文件不存在或路径无效
- **THEN** 系统抛出明确的启动错误，指示用户创建配置文件

#### Scenario: 配置文件格式错误
- **WHEN** JSON 语法错误或缺少必需字段
- **THEN** 系统抛出明确的启动错误，包含具体的校验失败原因

### Requirement: 多 Provider 支持

系统 SHALL 支持在配置文件中定义多个 LLM Provider，并通过名称动态选择。

#### Scenario: Provider 路由
- **WHEN** LLM 调用指定 provider_name
- **THEN** 系统从注册表中查找对应 Provider 并执行调用
- **AND** 未指定 provider_name 时使用配置文件中标记为 default 的 Provider

#### Scenario: API 格式路由
- **WHEN** Provider 配置了 `api` 字段
- **THEN** 系统根据 `api` 值选择对应的 API 适配器：
  - `"openai"` → OpenAI Chat Completions API (`/chat/completions`)
  - `"anthropic-messages"` → Anthropic Messages API (`/messages`)

### Requirement: Anthropic Messages API 支持

系统 SHALL 支持 Anthropic Messages API 格式的 LLM 调用。

#### Scenario: Anthropic API 调用
- **WHEN** Provider 的 `api` 字段为 `"anthropic-messages"`
- **THEN** 系统使用 Anthropic Messages API 格式发送请求：
  - Header: `x-api-key: {api_key}`, `anthropic-version: 2023-06-01`
  - Body: `{"model": "...", "max_tokens": ..., "messages": [...]}`
- **AND** 从响应中提取 `content[0].text` 作为内容
- **AND** 从响应中提取 `usage.input_tokens` 和 `usage.output_tokens` 作为 token 统计

### Requirement: 向后兼容

系统 SHALL 保持与现有功能的向后兼容。

#### Scenario: 现有调用接口不变
- **WHEN** 现有代码调用 `chat_completion(messages, temperature)` 或 `get_embedding(text)`
- **THEN** 函数签名和返回值格式不变
- **AND** 内部实现从配置文件读取 Provider 信息

## MODIFIED Requirements

### Requirement: Settings 配置类

`config.py` 中的 `Settings` 类 SHALL 从 pydantic-settings 环境变量读取改为从 JSON 配置文件读取。

**删除字段**：`LLM_PROVIDER`、`LLM_API_KEY`、`LLM_MODEL_NAME`、`LLM_BASE_URL`、`EMBEDDING_PROVIDER`、`EMBEDDING_API_KEY`、`EMBEDDING_MODEL_NAME`、`EMBEDDING_BASE_URL`

**保留字段（从 JSON 配置文件读取）**：`DATABASE_URL`、`REDIS_URL`、`APP_PORT`、`API_KEY`、`MAX_UPLOAD_SIZE_MB`、`CLEANUP_DAYS`、`CHROMA_PERSIST_DIR`、`RAG_TOP_K`、`LOG_LEVEL`、`CORS_ORIGINS`、`RATE_LIMIT`、`DB_POOL_SIZE`、`DB_MAX_OVERFLOW`、`DB_POOL_RECYCLE`

## REMOVED Requirements

### Requirement: 环境变量驱动的应用配置
**Reason**: 环境变量无法表达多 Provider、多模型、模型元数据等结构化信息，且配置分散在多处
**Migration**: 全部迁移到 JSON 配置文件 `solidguard.json`

### Requirement: pydantic-settings 作为配置源
**Reason**: 删除 `model_config` 中的 `env_file` 配置，Settings 不再从 `.env` 文件读取
**Migration**: Settings 改为从 JSON 配置文件实例化
