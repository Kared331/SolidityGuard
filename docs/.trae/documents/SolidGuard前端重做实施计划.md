# SolidGuard 前端及 LLM 模块全面重做实施计划

## 摘要

两项核心改动：

1. **前端重做**：从"Ant Design + 零样式体系"的 Web 页面，重做为基于 TRAE Work 设计系统的**应用式**专业桌面工具（Web SPA，Docker 部署方式不变）。
2. **LLM 调用链重做**：将散落在各处的 LLM 相关代码（Prompt 内联、RAG 耦合、无流式响应）重组为独立的 `llm/` 模块，建立规范的 Prompt 管理、流式 SSE 推送、多 Provider 可观测体系。

后端 API 端点整体不变（仅 LLM 模块内部重构 + 新增流式端点），Docker Compose 部署架构不变。

---

## 一、技术选型决策

### 1.1 保留项

| 技术 | 版本 | 理由 |
|------|------|------|
| React | 18.3 | 成熟稳定，生态完善 |
| TypeScript | 5.6 | strict 模式已开启，类型安全 |
| Vite | 5.4 | 构建性能优秀 |
| react-router-dom | 6.28 | 满足应用路由需求 |
| Axios | 1.7 | HTTP 客户端，保留 |

### 1.2 移除项

| 技术 | 理由 |
|------|------|
| Ant Design 5.22 | 设计诉求与 TRAE Work 矛盾（阴影/蓝白配色/丰富预设 vs 无阴影/Indigo稀缺/精简）；体积 ~1.2MB gzipped vs 自建 < 50KB |
| `@ant-design/icons` | 替换为 TRAE Work 本地 SVG 图标（671 个） |

### 1.3 新增项

| 技术 | 用途 | 理由 |
|------|------|------|
| CSS Modules | 样式方案 | 零运行时、作用域隔离、TypeScript 类型安全、原生支持 CSS Custom Properties |
| Zustand | 客户端状态管理 | ~1KB、无 boilerplate、selector 防重复渲染 |
| @tanstack/react-query | 服务端状态管理 | 自动缓存/refetch/loading/error 状态，消除手写 useEffect 获取数据 |
| ESLint 9 flat config | 代码规范 | TypeScript + React Hooks 规则 |
| Prettier | 格式化 | 统一代码风格 |
| Husky + lint-staged | Git hooks | 提交前自动 lint/format |
| @tanstack/react-table | 表格组件（可选辅助） | 如果自定义 ds-table 的排序/筛选/分页实现过于复杂，可引入此轻量 headless 库辅助 |

### 1.4 不采用项及理由

| 技术 | 理由 |
|------|------|
| Tailwind CSS | 需要维护自定义配置对齐 TRAE Work Token；TRAE Work 约束要求 `.ds-*` CSS 类体系 |
| CSS-in-JS (styled-components/Emotion) | 运行时开销；TRAE Work Design Token 通过 CSS Custom Properties 即可覆盖 |
| Redux / MobX | 状态复杂度不需要；Zustand + React Query 组合已覆盖全部场景 |
| Next.js | 纯 SPA 应用，无 SSR 需求；当前 Docker + Nginx 部署方案无需改动 |
| 任何外部图标库 | TRAE Work 约束明确要求仅使用本地 SVG 图标 |

---

## 二、设计系统落地方案

### 2.1 Design Token 体系

所有 Token 通过 CSS Custom Properties 定义在 `:root`，六个独立文件聚合为 `index.css`：

| Token 文件 | 内容 |
|------------|------|
| `colors.css` | 品牌色 `#4B3FE3`、中性色阶 0-1000、语义色（Critical/High/Medium/Low/Info）、状态色、文本色 |
| `typography.css` | 字体族（SF Pro Text / PingFang SC / SF Mono）、字号 12-32px、行高、字重、基线 body-base 14px/20px |
| `spacing.css` | 4-64px 间距阶梯、页面内边距 24px 32px、最大 shell 宽度 1184px |
| `radius.css` | sm 4px / md 8px（容器）/ lg 12px（卡片）/ full 9999px |
| `border.css` | 边框宽度 1px、边框色（neutral-200/hover neutral-300） |
| `motion.css` | 过渡时长 fast 150ms / normal 200ms / slow 300ms |

### 2.2 TRAE Work 约束合规清单

| 约束 | 合规方式 |
|------|----------|
| 仅 Light 模式 | 不定义 `prefers-color-scheme: dark` |
| 品牌色 `#4B3FE3` 稀缺使用 | 仅用于链接文本、选中态指示、focus ring；按钮 Primary 使用 `#262626` 反转色 |
| 禁止 drop shadows | 所有组件移除 `box-shadow`；Card 用 `border: 1px solid var(--ds-color-neutral-200)` 替代 |
| 禁止品牌色光晕 | 不使用 `box-shadow: 0 0 Xpx #4B3FE3` |
| 禁止装饰性视觉 | 不使用 SVG 背景、渐变 blob、图标簇装饰、假图表 |
| 仅用 TRAE Work 本地图标 | 不引入外部图标库、图标字体、emoji 图标、CDN 图标包 |
| 最大 shell 1184px | Content 区 `max-width: 1184px; margin: 0 auto` |
| 桌面端页边距 32px | `padding: 24px 32px` |
| 圆角体系 | Card 12px、容器/按钮/输入框 8px |
| 排版基线 body-base 14px/20px | 全局字体设置 |
| 动效约束 120-300ms + 无布局偏移 | 过渡 `opacity` + 微小位移（≤4px），组件尺寸不变；尊重 `prefers-reduced-motion` |

### 2.3 组件体系（14 个 `.ds-*` 组件）

**8 个核心组件**（按实现优先级排序）：

| 优先级 | 组件 | CSS 类 | 关键 Props |
|--------|------|--------|------------|
| 1 | ds-tag | `.ds-tag` | variant(neutral/brand/critical/high/medium/low/info/success), size(sm/md) |
| 2 | ds-badge | `.ds-badge` | count, variant, size |
| 3 | ds-button | `.ds-btn` | variant(primary/secondary/ghost/text/brand/danger), size(sm 24px/md 28px/lg 32px), loading, disabled |
| 4 | ds-input | `.ds-input` | type(text/search), placeholder, disabled, prefix/suffix icon |
| 5 | ds-select | `.ds-select` | options, value, onChange, placeholder |
| 6 | ds-spinner | `.ds-spinner` | size(sm/md/lg), overlay(boolean) |
| 7 | ds-card | `.ds-card` | title, extra, hoverable, padding |
| 8 | ds-tabs | `.ds-tabs` | items({key, label, content}), activeKey, onChange |

**6 个辅助组件**：

| 优先级 | 组件 | CSS 类 | 用途 |
|--------|------|--------|------|
| 9 | ds-table | `.ds-table` | 排序、分页、行点击、空状态、loading |
| 10 | ds-drawer | `.ds-drawer` | 侧边滑出面板（审计详情核心交互） |
| 11 | ds-modal | `.ds-modal` | 确认对话框 |
| 12 | ds-tooltip | `.ds-tooltip` | 悬浮提示 |
| 13 | ds-layout | `.ds-layout` | Header/Sidebar/Content 布局容器 |
| 14 | ds-breadcrumb | `.ds-breadcrumb` | 路径导航 |

**每个组件的实现标准**：
- `ComponentName.tsx` — 组件逻辑 + TypeScript Props 类型
- `ComponentName.module.css` — 组件样式（引用 Design Token `var()`）
- `index.ts` — 导出
- 支持 `className` prop 合并，允许外部用 `.ds-*` 类微调

### 2.4 Severity 颜色体系（单一来源）

当前三个页面各自定义 `severityColors`。重做后统一在 `src/utils/severity.ts`：

```typescript
export const SEVERITY_CONFIG = {
  critical:       { color: 'var(--ds-color-critical)', bg: 'var(--ds-color-critical-bg)', label: '严重',   rank: 5 },
  high:           { color: 'var(--ds-color-high)',     bg: 'var(--ds-color-high-bg)',     label: '高危',   rank: 4 },
  medium:         { color: 'var(--ds-color-medium)',   bg: 'var(--ds-color-medium-bg)',   label: '中危',   rank: 3 },
  low:            { color: 'var(--ds-color-low)',      bg: 'var(--ds-color-low-bg)',      label: '低危',   rank: 2 },
  informational:  { color: 'var(--ds-color-info)',     bg: 'var(--ds-color-info-bg)',     label: '信息',   rank: 1 },
} as const;
```

### 2.5 图标集成方案

- TRAE Work 的 671 个 SVG 图标放置在 `public/icons/` 目录下
- 创建 `src/design-system/icons/Icon.tsx`：通用 SVG 图标封装组件，通过 `currentColor` 上色
- 创建 `src/design-system/icons/registry.ts`：图标名称 → 文件路径映射
- 使用方式：`<Icon name="shield-check" size={16} />`
- 默认尺寸 16px，支持 12/14/16/20/24px
- 每个图标占位符预留最终宽高防止布局抖动
- 按需引用，不全局注册所有 671 个图标（避免打包体积膨胀）

---

## 三、项目目录结构

```
frontend/
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
├── eslint.config.mjs
├── .prettierrc
├── nginx.conf
├── Dockerfile
│
├── public/
│   └── icons/                         # TRAE Work SVG icons（按需复制）
│
├── src/
│   ├── main.tsx                       # 入口：QueryClientProvider + BrowserRouter
│   ├── App.tsx                        # 根路由定义（lazy loading 各页面）
│   ├── vite-env.d.ts
│   │
│   ├── design-system/                 # ===== 设计系统 =====
│   │   ├── tokens/
│   │   │   ├── colors.css
│   │   │   ├── typography.css
│   │   │   ├── spacing.css
│   │   │   ├── radius.css
│   │   │   ├── border.css
│   │   │   ├── motion.css
│   │   │   └── index.css              # @import 聚合
│   │   │
│   │   ├── components/
│   │   │   ├── Button/                # Button.tsx + Button.module.css + index.ts
│   │   │   ├── Tag/
│   │   │   ├── Badge/
│   │   │   ├── Input/
│   │   │   ├── Select/
│   │   │   ├── Spinner/
│   │   │   ├── Card/
│   │   │   ├── Tabs/
│   │   │   ├── Table/
│   │   │   ├── Drawer/
│   │   │   ├── Modal/
│   │   │   ├── Tooltip/
│   │   │   ├── Layout/
│   │   │   └── Breadcrumb/
│   │   │
│   │   ├── icons/
│   │   │   ├── Icon.tsx               # SVG 图标封装组件
│   │   │   └── registry.ts            # 图标名 → 路径映射
│   │   │
│   │   └── index.ts                   # 统一导出
│   │
│   ├── api/                           # ===== API 层 =====
│   │   ├── client.ts                  # Axios 实例
│   │   ├── queryKeys.ts               # React Query key 工厂
│   │   ├── types.ts                   # API 响应类型
│   │   └── hooks/
│   │       ├── useProjects.ts         # 项目 CRUD
│   │       ├── useAnalyses.ts         # Slither 分析
│   │       ├── useFuzzResults.ts      # Fuzz 测试
│   │       ├── useAuditResults.ts     # LLM 审计
│   │       ├── useReports.ts          # 报告管理
│   │       └── useVulnerabilities.ts  # 漏洞知识库
│   │
│   ├── stores/                        # ===== Zustand 状态 =====
│   │   ├── useAppStore.ts             # UI 全局状态：sidebar 展开/折叠
│   │   └── useAuditDetailStore.ts     # 审计详情：Drawer 开关 + 当前选中 finding
│   │
│   ├── hooks/                         # ===== 通用 Hooks =====
│   │   └── useSSE.ts                  # SSE 事件流（重构自 useTaskProgress）
│   │
│   ├── utils/
│   │   ├── severity.ts                # Severity 配置（单一来源）
│   │   ├── format.ts                  # 日期/数字/文件大小格式化
│   │   └── constants.ts               # 应用常量
│   │
│   ├── layouts/
│   │   ├── AppShell/
│   │   │   ├── AppShell.tsx           # 主外壳：Header + Sidebar + Outlet
│   │   │   └── AppShell.module.css
│   │   ├── Sidebar/
│   │   │   ├── Sidebar.tsx
│   │   │   └── Sidebar.module.css
│   │   └── Header/
│   │       ├── Header.tsx
│   │       └── Header.module.css
│   │
│   ├── pages/
│   │   ├── Dashboard/                 # 新增：项目仪表盘
│   │   │   ├── DashboardPage.tsx
│   │   │   ├── DashboardPage.module.css
│   │   │   └── ProjectCard.tsx
│   │   │
│   │   ├── Upload/
│   │   │   ├── UploadPage.tsx
│   │   │   └── UploadPage.module.css
│   │   │
│   │   ├── ProjectDetail/
│   │   │   ├── ProjectDetailPage.tsx
│   │   │   ├── ProjectDetailPage.module.css
│   │   │   ├── OperationBar.tsx       # 操作栏（Run Slither/Fuzz/Audit）
│   │   │   ├── FilesPanel.tsx         # 文件列表（可折叠）
│   │   │   ├── AnalysisTab.tsx        # Slither 结果
│   │   │   ├── FuzzingTab.tsx         # Fuzz 结果
│   │   │   ├── LLMAuditTab.tsx        # LLM 审计摘要
│   │   │   └── FindingDetailDrawer.tsx # 共享：漏洞详情抽屉
│   │   │
│   │   ├── LLMAudit/
│   │   │   ├── LLMAuditPage.tsx
│   │   │   ├── LLMAuditPage.module.css
│   │   │   ├── ExecutiveSummary.tsx   # 执行摘要
│   │   │   ├── RiskOverview.tsx       # 风险概览（纯 CSS 柱状图）
│   │   │   ├── DetailedFindings.tsx   # 漏洞发现列表
│   │   │   └── RecommendationsSummary.tsx # 修复建议清单
│   │   │
│   │   ├── Report/
│   │   │   ├── ReportPage.tsx
│   │   │   ├── ReportPage.module.css
│   │   │   ├── FormatSelector.tsx     # 格式选择
│   │   │   └── ReportList.tsx         # 历史报告列表
│   │   │
│   │   └── Vulnerabilities/
│   │       ├── VulnerabilitiesPage.tsx
│   │       ├── VulnerabilitiesPage.module.css
│   │       ├── SearchToolbar.tsx      # 搜索 + severity 筛选
│   │       └── VulnerabilityDetailDrawer.tsx # 漏洞详情抽屉
│   │
│   └── styles/
│       ├── reset.css                  # CSS Reset
│       └── global.css                 # 全局布局样式
```

---

## 四、LLM 调用链重做方案

### 4.1 当前问题诊断

对 `backend/app/services/` 下 9 个 LLM 相关文件进行全面审查后，发现以下结构性问题：

| 问题 | 现状 | 影响 |
|------|------|------|
| Prompt 内联硬编码 | 所有 system/user prompt 以 f-string 散落在 `llm_audit.py`、`report_generator.py` 中 | 修改 Prompt 需要改代码、无法版本管理、难以 A/B 测试 |
| RAG 管道与审计引擎耦合 | `query_vulnerabilities()` 在 `LLMAuditEngine._audit_function()` 内直接调用 | 无法独立测试 RAG 质量、无法替换检索策略 |
| 无流式响应 | 审计结果只在 Celery 任务完成后一次性返回 | 用户等待 2-5 分钟无任何反馈，体验极差 |
| 无 Prompt 版本管理 | Prompt 散落在代码中，无版本标识 | 无法追溯某次审计使用的 Prompt 版本 |
| 无 LLM 调用可观测性 | 仅记录 token 消耗数量，无延迟/成功率/重试次数统计 | 无法评估 LLM Provider 质量，无法定位性能瓶颈 |
| Token 预算硬编码 | `500,000 tokens / 100 calls` 写死在 `token_budget.py` | 无法按需调整配额 |
| 函数提取逻辑脆弱 | 正则匹配 + 50 个关键词硬编码列表 | 误判率高，复杂合约（proxy/delegate/assembly）容易漏检 |
| Embedding/ChromaDB 无健康检查 | 启动时不验证连接，失败时静默降级返回空结果 | 审计结果"看起来正常"但 RAG 实际已失效 |
| 报告润色与审计使用同一 LLM Client | 润色 prompt 和审计 prompt 共享同一个 `chat_completion()` 调用 | 无法为不同场景配置不同模型（如润色用便宜模型） |

### 4.2 目标架构：独立 `llm/` 模块

将 LLM 相关代码从 `app/services/` 中剥离，建立 `app/llm/` 作为独立模块：

```
backend/app/llm/                        # ===== LLM 模块（独立板块）=====
│
├── __init__.py                         # 模块公开 API
│
├── provider/                           # LLM Provider 层
│   ├── __init__.py
│   ├── base.py                         # AbstractLLMProvider 抽象基类
│   ├── openai_provider.py              # OpenAI-compatible provider
│   ├── provider_registry.py            # Provider 注册与发现
│   └── provider_stats.py               # Provider 可观测性（延迟/成功率/重试）
│
├── prompts/                            # Prompt 管理层
│   ├── __init__.py
│   ├── registry.py                     # Prompt 注册表（name → template）
│   ├── templates/                      # Prompt 模板文件
│   │   ├── audit/
│   │   │   ├── contract_summary.yaml   # 合约摘要 prompt
│   │   │   ├── function_audit.yaml     # 函数审计 prompt（含 RAG context slot）
│   │   │   └── report_polish.yaml      # 报告润色 prompt
│   │   └── system_personas.yaml        # System persona 定义
│   └── template_loader.py             # YAML 模板加载器
│
├── rag/                                # RAG 检索子模块
│   ├── __init__.py
│   ├── embedding/
│   │   ├── __init__.py
│   │   ├── base.py                     # AbstractEmbeddingProvider
│   │   ├── openai_embedding.py
│   │   └── local_embedding.py
│   ├── retriever.py                    # 检索器（ChromaDB 查询封装）
│   ├── health_check.py                 # Embedding + ChromaDB 健康检查
│   └── evaluation.py                   # RAG 质量评估（hit rate / MRR）
│
├── pipeline/                           # 审计流水线
│   ├── __init__.py
│   ├── audit_pipeline.py               # 审计流水线编排
│   ├── function_extractor.py           # 函数提取器（AST 替代正则）
│   └── stream.py                       # 流式输出管理器（SSE）
│
├── security/                           # 安全层
│   ├── __init__.py
│   ├── input_sanitizer.py              # 输入清洗（迁移 + 增强）
│   └── output_validator.py             # 输出校验（JSON schema 验证）
│
├── budget/                             # 成本控制
│   ├── __init__.py
│   └── token_budget.py                 # Token 预算（迁移 + 可配置限额）
│
└── schemas/                            # LLM 模块专用 Schema
    ├── __init__.py
    ├── audit_output.py                 # LLM 审计输出 JSON Schema (Pydantic)
    └── prompt_context.py               # Prompt 上下文字段定义
```

### 4.3 Prompt 管理方案

#### 4.3.1 YAML 模板格式

每个 Prompt 以独立 YAML 文件存储，支持变量插槽、版本标识、元数据：

```yaml
# app/llm/prompts/templates/audit/function_audit.yaml
name: function_audit
version: "2.1.0"
description: "审计单个 Solidity 函数的完整 Prompt（含 RAG context）"
model_preference: ["gpt-4o", "claude-sonnet-4"]
temperature: 0.2
max_tokens: 4096

system: |
  You are a senior Solidity security auditor with expertise in:
  - Smart contract vulnerability detection (reentrancy, access control, overflow, etc.)
  - DeFi protocol security patterns
  - EVM internals and gas optimization

  CRITICAL RULES:
  1. Only report vulnerabilities that are EXPLOITABLE — do NOT flag informational observations.
  2. For each finding, provide a concrete PoC attack scenario.
  3. Output MUST be valid JSON matching the specified schema.
  4. If no vulnerability is found, return an empty array [].

user: |
  ## Contract Context
  {contract_summary}

  ## Function to Audit
  ```solidity
  {function_code}
  ```

  ## Similar Vulnerability Patterns (RAG Results)
  {rag_context}

  ## Instructions
  Analyze the function above for security vulnerabilities. 
  Cross-reference with the similar vulnerability patterns provided.
  
  Return a JSON array of findings. Each finding must have:
  - vulnerability_description: detailed explanation
  - severity: "Critical" | "High" | "Medium" | "Low" | "Informational"
  - impact: concrete impact description
  - suggested_fix: code-level fix recommendation
  - gas_optimization: optional gas optimization suggestion
  - confidence: float 0.0-1.0

  Output ONLY the JSON array, no markdown, no explanation.
```

#### 4.3.2 Prompt 注册表

```python
# app/llm/prompts/registry.py
@dataclass
class PromptTemplate:
    name: str
    version: str
    system: str
    user: str
    model_preference: list[str]
    temperature: float
    max_tokens: int

class PromptRegistry:
    """Prompt 注册表：支持按名称加载 + 版本锁定"""
    
    def get(self, name: str, version: str | None = None) -> PromptTemplate: ...
    def render(self, name: str, **variables) -> tuple[str, str]:  # (system, user)
    def list_versions(self, name: str) -> list[str]: ...
```

### 4.4 流式 SSE 推送方案

#### 4.4.1 新增 API 端点

当前审计是"提交任务 → Celery 跑完 → 一次性返回结果"。新增流式端点让前端实时展示审计进度：

```
POST /api/v1/projects/{id}/llm-audit/stream
  → 201 { "stream_id": "uuid" }

GET  /api/v1/projects/{id}/llm-audit/stream/{stream_id}
  → SSE 事件流：
    event: progress     data: {"phase": "parsing", "file": "MyToken.sol", "progress": 0.1}
    event: progress     data: {"phase": "embedding", "function": "withdraw()", "progress": 0.3}
    event: progress     data: {"phase": "rag_retrieval", "function": "withdraw()", "matches": 5, "progress": 0.4}
    event: finding      data: {"function": "withdraw()", "severity": "Critical", "title": "Reentrancy", "confidence": 0.92}
    event: progress     data: {"phase": "auditing", "function": "transfer()", "progress": 0.6}
    event: progress     data: {"phase": "complete", "total_findings": 5, "progress": 1.0}
    event: error        data: {"phase": "rag_retrieval", "message": "ChromaDB connection lost"}
```

#### 4.4.2 流式管道实现

```python
# app/llm/pipeline/stream.py
class AuditStreamManager:
    """管理审计流式输出的生命周期"""
    
    async def start_stream(self, project_id: int) -> str:
        """创建流式会话，返回 stream_id"""
    
    async def emit_progress(self, stream_id: str, phase: str, **data):
        """发送进度事件到 Redis pub/sub → FastAPI SSE"""
    
    async def emit_finding(self, stream_id: str, finding: AuditFinding):
        """实时推送单个 finding"""
```

**架构**：Celery Task → Redis Pub/Sub → FastAPI SSE → 前端 EventSource

### 4.5 函数提取器升级：正则 → AST

当前的 `_extract_key_functions()` 使用正则 + 50 个硬编码关键词列表：

```python
# 当前实现（脆弱）
KEYWORDS = {"transfer", "call", "delegatecall", "owner", "onlyOwner", ...}
# 问题: proxy 合约的函数名完全不含这些关键词，但漏洞风险很高
```

升级为使用 `solc-ast` 或 `solidity-parser` 做 AST 解析：

```python
# app/llm/pipeline/function_extractor.py
class FunctionExtractor:
    """基于 AST 的 Solidity 函数提取"""
    
    def extract(self, source: str) -> list[FunctionInfo]:
        """
        返回所有 public/external 函数，附带：
        - 修饰器列表 (modifiers)
        - 状态可变性 (view/pure/payable/nonpayable)
        - 调用图（call graph）中的下游调用
        - 是否访问 storage 变量
        """
```

**提取策略**：不再依赖关键词过滤，改为提取 **所有 public/external 函数**，依赖 LLM 自行判断是否值得审计。如果合约函数过多（>20），按调用图深度和 storage 访问频率排序，优先审计高风险函数。

### 4.6 可观测性增强

```python
# app/llm/provider/provider_stats.py
@dataclass
class ProviderMetrics:
    provider_name: str
    total_calls: int
    success_count: int
    failure_count: int
    avg_latency_ms: float
    p95_latency_ms: float
    total_tokens_used: int
    retry_count: int
    circuit_breaker_trips: int

class LLMObservability:
    """LLM 调用可观测性：记录每次调用的延迟/结果/token"""
    
    def record_call(self, provider: str, model: str, 
                    latency_ms: int, success: bool, 
                    tokens: int, error: str | None): ...
    
    def get_metrics(self, provider: str, window_minutes: int = 60) -> ProviderMetrics: ...
    
    def health_summary(self) -> dict:
        """返回所有 Provider 的健康状态摘要"""
```

### 4.7 新增后端端点

除重构现有端点外，新增以下 API：

| 方法 | 路径 | 用途 |
|------|------|------|
| POST | `/api/v1/projects/{id}/llm-audit/stream` | 启动流式审计，返回 stream_id |
| GET | `/api/v1/projects/{id}/llm-audit/stream/{stream_id}` | SSE 事件流 |
| GET | `/api/v1/llm/health` | LLM 模块健康检查（Provider + Embedding + ChromaDB） |
| GET | `/api/v1/llm/metrics` | LLM 调用指标（延迟/成功率/token 消耗） |
| GET | `/api/v1/llm/prompts` | 列出可用 Prompt 模板及版本 |

### 4.8 LLM 模块文件迁移映射

| 当前文件 | 目标位置 | 变更 |
|----------|----------|------|
| `services/llm_client.py` | `llm/provider/openai_provider.py` | 重构为 AbstractLLMProvider 子类 |
| `services/embedding.py` | `llm/rag/embedding/` | 拆分为 base + openai + local 三个文件 |
| `services/chroma_client.py` | `llm/rag/retriever.py` | 封装为 Retriever 类，增加健康检查 |
| `services/input_sanitizer.py` | `llm/security/input_sanitizer.py` | 迁移，接口不变 |
| `services/token_budget.py` | `llm/budget/token_budget.py` | 迁移，改为可配置限额 |
| `services/engine/llm_audit.py` | `llm/pipeline/audit_pipeline.py` | 重构为 Pipeline，解耦 Prompt/RAG/Provider |
| `services/report_generator.py` | `llm/pipeline/` + `services/engine/report.py` | 润色逻辑迁移到 llm/pipeline，报告模板渲染保留在 services |
| (新增) | `llm/prompts/` | 所有 Prompt 模板 |
| (新增) | `llm/pipeline/function_extractor.py` | AST 函数提取器 |
| (新增) | `llm/pipeline/stream.py` | 流式输出管理 |
| (新增) | `llm/provider/provider_stats.py` | 可观测性 |
| (新增) | `llm/rag/health_check.py` | 健康检查 |
| (新增) | `llm/rag/evaluation.py` | RAG 质量评估 |
| (新增) | `llm/schemas/` | Pydantic Schema |

### 4.9 Token 预算可配置化

当前硬编码 `500,000 tokens / 100 calls per project`。改为环境变量：

```bash
# .env.example 新增
LLM_TOKEN_BUDGET_PER_PROJECT=500000
LLM_MAX_CALLS_PER_PROJECT=100
LLM_AUDIT_MODEL=gpt-4o          # 审计用模型
LLM_POLISH_MODEL=gpt-4o-mini    # 报告润色用模型（可不同）
```

---

## 五、页面重设计规划

### 5.1 整体布局：AppShell（应用式三栏布局）

```
┌──────────────────────────────────────────────────────────┐
│ Header (48px)                    SolidGuard    [项目选择] │
├────────────┬─────────────────────────────────────────────┤
│  Sidebar   │                                             │
│            │  Content Area                               │
│  📊 项目   │  max-width: 1184px                          │
│  📤 上传   │  padding: 24px 32px                         │
│  📚 漏洞库 │                                             │
│            │                                             │
│  (可折叠   │                                             │
│   至 64px) │                                             │
├────────────┴─────────────────────────────────────────────┤
│ Status Bar  ● SSE Connected    Project #42: MyToken.sol  │
└──────────────────────────────────────────────────────────┘
```

- Header：48px 高度，左侧品牌名，右侧当前项目下拉选择器
- Sidebar：默认展开 200px，可折叠至 64px（仅图标）。三个导航项
- Content：`max-width: 1184px; margin: 0 auto; padding: 24px 32px`
- Status Bar：可选底栏，显示 SSE 连接状态 + 当前项目名

### 5.2 页面 1：Dashboard（项目列表页）-- 新增

**当前无此页面，替代直接跳转 `/upload` 的模式。**

布局：卡片网格（每行 3 列），每卡片显示项目名、状态标签、最近活动时间、Slither/Fuzz/Audit 结果计数。顶部搜索框 + 右上角 `+ 新建上传` 按钮。点击卡片进入 ProjectDetailPage。

### 5.3 页面 2：UploadPage（上传页）

布局：拖拽上传区（HTML5 Drag & Drop API）+ 最近项目快捷入口。拖拽区使用 ds-card 容器，支持 `.sol/.zip/.tar.gz` 格式。下方显示最近 5 个项目卡片快捷跳转。

### 5.4 页面 3：ProjectDetailPage（项目详情/分析面板）

**核心重组**：将原有的扁平淡页面改为专业分析面板，支持行点击查看详情。

```
┌──────────────────────────────────────────────────────────┐
│  ← 返回    Project #42: MyToken.sol              [ready] │
│                                                          │
│  ┌─ 操作栏 ────────────────────────────────────────────┐ │
│  │ [▶ Run Slither] [▶ Run Fuzzing] [▶ Run LLM Audit]  │ │
│  │ [📄 生成报告]                     ● SSE Connected   │ │
│  └────────────────────────────────────────────────────┘ │
│                                                          │
│  ┌─ 文件列表 (可折叠) ──────────────────────────────────┐│
│  │ contracts/MyToken.sol     ✓ ready    234 lines       ││
│  │ contracts/Ownable.sol     ✓ ready     45 lines       ││
│  └──────────────────────────────────────────────────────┘│
│                                                          │
│  ┌─────────────────┬─────────────────┬─────────────────┐ │
│  │ Slither 分析    │ Fuzzing 测试     │ LLM 审计        │ │
│  │ ▼ 12 个发现     │ ▼ 3 次运行       │ ▼ 5 个发现      │ │
│  │                 │                 │                 │ │
│  │ [结果表格]      │ [结果表格]       │ [摘要卡片]      │ │
│  │ 行点击 → Drawer │ 行点击 → Drawer  │ 点击 → 完整报告 │ │
│  └─────────────────┴─────────────────┴─────────────────┘ │
└──────────────────────────────────────────────────────────┘
```

**核心交互 -- 审计结果点击查看详情（Drawer）**：

点击表格中任一行，右侧滑出 420px Drawer 展示完整漏洞详情：

```
主内容区域                    │  Drawer (420px)
                              │
Table View                    │  ┌──────────────────────────┐
                              │  │ [Critical] 重入攻击        │
● row 1 (选中) ─────────────────→ │                          │
○ row 2                       │  │ Contract: MyToken         │
○ row 3                       │  │ Function: withdraw()      │
                              │  │                          │
                              │  │ Description:             │
                              │  │ The withdraw() function   │
                              │  │ calls external transfer   │
                              │  │ before updating the       │
                              │  │ balance state variable... │
                              │  │                          │
                              │  │ Impact:                  │
                              │  │ Attacker can drain all    │
                              │  │ funds from the contract.  │
                              │  │                          │
                              │  │ Suggested Fix:           │
                              │  │ ```solidity              │
                              │  │ balances[msg.sender] = 0; │
                              │  │ msg.sender.transfer(amt);│
                              │  │ ```                      │
                              │  │                          │
                              │  │ Confidence: ████░ 0.85   │
                              │  │                          │
                              │  │ [Mark as False Positive] │
                              │  │               [关闭 ✕]   │
                              │  └──────────────────────────┘
```

Drawer 详情区块（按行业规范排序）：
1. 标题 + Severity Tag
2. 合约名 / 函数名 / 代码行号
3. 漏洞描述
4. 影响分析
5. 修复建议（代码块使用等宽字体，语法高亮）
6. Gas 优化建议（LLM 审计特有）
7. 置信度指示条
8. 操作：Mark as False Positive

### 5.5 页面 4：LLMAuditPage（专业审计报告视图）

**完全按照行业审计报告标准重构**。参考 Trail of Bits / Consensys Diligence / OpenZeppelin 报告格式。

```
┌──────────────────────────────────────────────────────────┐
│  LLM Smart Contract Security Audit Report                │
│  Project #42: MyToken.sol                                │
│  Generated: 2026-07-14 14:30 UTC                        │
│                                                          │
│  ┌─ 1. Executive Summary ──────────────────────────────┐ │
│  │ 本次审计覆盖 MyToken.sol (3 个合约, 850 行代码).     │ │
│  │ 共发现 5 个漏洞: 1 Critical, 2 High, 1 Medium,       │ │
│  │ 1 Informational. 总体风险等级: HIGH                  │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                          │
│  ┌─ Risk Overview (纯 CSS 柱状图) ──────────────────────┐ │
│  │ Critical:  ██ 1                                      │ │
│  │ High:      ████ 2                                    │ │
│  │ Medium:    ██ 1                                      │ │
│  │ Low:       ░░ 0                                      │ │
│  │ Info:      ██ 1                                      │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                          │
│  ┌─ 2. Detailed Findings ──────────────────────────────┐ │
│  │ ┌─ [Critical] CR-01: Reentrancy Attack ── [展开 ▼]─┐ │ │
│  │ │ Contract: Vault  Function: withdraw()              │ │ │
│  │ │ ...详情展开后显示完整漏洞信息...                    │ │ │
│  │ └────────────────────────────────────────────────────┘ │ │
│  │ ┌─ [High] HI-01: Missing Access Control ── [展开 ▼]─┐ │ │
│  │ │ ...                                                │ │ │
│  │ └────────────────────────────────────────────────────┘ │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                          │
│  ┌─ 3. Recommendations Summary ────────────────────────┐ │
│  │ Priority 1: Fix CR-01 (Reentrancy)                   │ │
│  │ Priority 2: Fix HI-01, HI-02 (Access Control)        │ │
│  │ Priority 3: Fix ME-01 (Timestamp Dependency)         │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                          │
│  [🔄 Run New Audit]  [📄 Export as Report]               │
└──────────────────────────────────────────────────────────┘
```

**交互细节**：
- Executive Summary 始终可见（自动生成摘要文字）
- Risk Overview 使用 `<div>` + `width%` 纯 CSS 柱状图（无图表库依赖）
- Detailed Findings 可折叠/展开，每项显示完整详情
- Finding ID 格式：`CR-01` (Critical), `HI-01` (High), `ME-01` (Medium), `LO-01` (Low), `IN-01` (Info)
- 点击 finding 行 → Drawer 展开侧边详情（复用 FindingDetailDrawer）
- Recommendations Summary 按优先级排序

### 5.6 页面 5：ReportPage（报告生成）

布局：格式选择（HTML/PDF/Word）+ 生成按钮 + 历史报告列表。历史报告列表每行显示报告名、时间戳、多格式下载按钮。

### 5.7 页面 6：VulnerabilitiesPage（漏洞知识库）

布局：搜索栏 + severity 筛选下拉 + ds-table 表格。行点击展开 Drawer（Description + Code Example + SWC 规范链接）。支持分页。

---

## 六、分阶段实施步骤

> **双轨并行**：前端重做（轨道 A）与后端 LLM 模块重做（轨道 B）可并行推进，互不阻塞。最终在阶段 4（SSE 集成）合流。

### 轨道 A：前端重做

#### 阶段 A0：基础设施搭建

| 步骤 | 内容 |
|------|------|
| 0.1 | 更新 `package.json`：移除 antd/`@ant-design/icons`，添加 zustand、`@tanstack/react-query`、eslint、prettier、husky、lint-staged |
| 0.2 | 配置 ESLint 9 flat config + Prettier + Husky + lint-staged |
| 0.3 | 创建 6 个 Design Token CSS 文件 + `design-system/tokens/index.css` |
| 0.4 | 创建 `styles/reset.css` + `styles/global.css` |
| 0.5 | 创建 AppShell 布局骨架：Header + Sidebar + Content 占位 |
| 0.6 | 更新 `main.tsx`：挂载 QueryClientProvider + BrowserRouter |
| 0.7 | 验证：`npm run dev` 可看到布局骨架，零报错 |

#### 阶段 A1：设计系统组件实现

**产出物**：14 个 `.ds-*` 组件可用，每个含 `.tsx` + `.module.css` + `index.ts`。

| 步骤 | 组件 | 原因 |
|------|------|------|
| 1.1 | ds-tag, ds-badge | 被几乎所有页面依赖（severity 展示） |
| 1.2 | ds-button | 操作入口 |
| 1.3 | ds-input, ds-select | 搜索/筛选 |
| 1.4 | ds-spinner | 加载态 |
| 1.5 | ds-card | 容器 |
| 1.6 | ds-tabs | ProjectDetailPage 核心 |
| 1.7 | ds-table | 数据展示核心 |
| 1.8 | ds-drawer | 详情查看核心交互 |
| 1.9 | ds-modal, ds-tooltip | 辅助交互 |
| 1.10 | ds-layout, ds-breadcrumb | 导航 |
| 1.11 | Icon 组件 + registry | SVG 图标封装 |

#### 阶段 A2：API 层 + 状态管理

| 步骤 | 内容 |
|------|------|
| 2.1 | 定义 `src/api/types.ts`：所有 API 响应类型 |
| 2.2 | 创建 `src/api/queryKeys.ts`：React Query key 工厂 |
| 2.3 | 实现 6 个 API hook 模块（useProjects, useAnalyses, useFuzzResults, useAuditResults, useReports, useVulnerabilities） |
| 2.4 | 创建 `src/utils/severity.ts`：单一 severity 配置来源 |
| 2.5 | 创建 `src/utils/format.ts` + `src/utils/constants.ts` |
| 2.6 | 创建 `src/stores/useAppStore.ts` + `useAuditDetailStore.ts` |
| 2.7 | 重构 `src/hooks/useSSE.ts`：接收 queryClient，事件 → invalidateQueries |

#### 阶段 A3：页面重写（按依赖顺序）

##### A3.1 UploadPage + DashboardPage（无外部依赖，可并行）

| 步骤 | 内容 |
|------|------|
| 3.1.1 | 重写 UploadPage：ds-card + HTML5 Drag & Drop + 最近项目列表 |
| 3.1.2 | 新建 DashboardPage：项目卡片网格 + 搜索 + 快速上传入口 |
| 3.1.3 | 配置路由：`/` → DashboardPage, `/upload` → UploadPage, `/projects/:id` → ProjectDetailPage 等 |

##### A3.2 VulnerabilitiesPage（独立页面，无项目上下文依赖）

| 步骤 | 内容 |
|------|------|
| 3.2.1 | 重写 VulnerabilitiesPage：SearchToolbar + ds-table + severity 筛选 |
| 3.2.2 | 实现 VulnerabilityDetailDrawer：描述 + Code Example + SWC 链接 |
| 3.2.3 | 连接 React Query hook `useVulnerabilities` |

##### A3.3 ProjectDetailPage（最复杂页面，依赖最多）

| 步骤 | 内容 |
|------|------|
| 3.3.1 | 创建 FilesPanel：ds-card + ds-table，可折叠 |
| 3.3.2 | 创建 OperationBar：ds-button 操作按钮组 + SSE 状态指示 |
| 3.3.3 | 创建 AnalysisTab：Slither 结果表 + 行点击 → Drawer |
| 3.3.4 | 创建 FuzzingTab：Fuzz 结果表 + 行点击 → Drawer |
| 3.3.5 | 创建 LLMAuditTab：审计摘要卡片 + 跳转完整报告入口 |
| 3.3.6 | 实现 FindingDetailDrawer（共享组件）：根据 finding 类型渲染不同区块（描述/影响/修复/置信度/误报标记） |
| 3.3.7 | 组装 ProjectDetailPage + 路由配置 |

##### A3.4 LLMAuditPage（依赖 FindingDetailDrawer）

| 步骤 | 内容 |
|------|------|
| 3.4.1 | 创建 ExecutiveSummary 组件 |
| 3.4.2 | 创建 RiskOverview 组件（纯 CSS 柱状图） |
| 3.4.3 | 创建 DetailedFindings 列表（可折叠 finding 卡片） |
| 3.4.4 | 创建 RecommendationsSummary 组件（优先级排序清单） |
| 3.4.5 | 复用 FindingDetailDrawer（已在 3.3.6 实现） |
| 3.4.6 | 页面组装 + 路由配置 |

##### A3.5 ReportPage（依赖最少，最后实现）

| 步骤 | 内容 |
|------|------|
| 3.5.1 | 创建 FormatSelector：自定义 radio 组 |
| 3.5.2 | 创建 ReportList：历史报告 + 下载按钮组 |
| 3.5.3 | 组装 ReportPage + 路由配置 |

#### 阶段 A4：SSE 实时更新集成

| 步骤 | 内容 |
|------|------|
| 4.1 | useSSE hook 完善：事件类型 → queryClient.invalidateQueries 映射 |
| 4.2 | AppShell 底部添加 SSE 连接状态指示器 |
| 4.3 | 端到端验证：触发分析 → SSE 推送 → 数据自动刷新 |

#### 阶段 A5：工程化完善

| 步骤 | 内容 |
|------|------|
| 5.1 | 页面级 lazy loading（React.lazy + Suspense）优化首屏加载 |
| 5.2 | Vite 生产构建优化：code splitting、CSS 提取 |
| 5.3 | Dockerfile + nginx.conf 构建验证 |
| 5.4 | TRAE Work 约束合规审查：逐条检查 13 项合规清单 |
| 5.5 | 无障碍（a11y）检查：语义化 HTML、focus 管理、ARIA 标签、对比度 |
| 5.6 | 清理旧的 Ant Design 残留代码和类型引用 |

### 轨道 B：LLM 模块重做（后端）

#### 阶段 B0：模块骨架搭建

| 步骤 | 内容 |
|------|------|
| B0.1 | 创建 `backend/app/llm/` 目录结构（`provider/`, `prompts/`, `rag/`, `pipeline/`, `security/`, `budget/`, `schemas/`） |
| B0.2 | 定义 AbstractLLMProvider 抽象基类 + AbstractEmbeddingProvider 抽象基类 |
| B0.3 | 实现 ProviderRegistry 注册机制 |
| B0.4 | 验证：现有 `llm_client.py` 调用可改为通过 ProviderRegistry 获取，功能不变 |

#### 阶段 B1：Prompt 管理层

| 步骤 | 内容 |
|------|------|
| B1.1 | 实现 YAML 模板加载器（`template_loader.py`） |
| B1.2 | 实现 PromptRegistry（注册表 + render 方法） |
| B1.3 | 从现有代码中提取所有 Prompt，写入 YAML 模板文件（`contract_summary.yaml`, `function_audit.yaml`, `report_polish.yaml`, `system_personas.yaml`） |
| B1.4 | 修改 `audit_pipeline.py` 和 `report_generator.py` 改为通过 PromptRegistry 获取 Prompt |
| B1.5 | 验证：运行一次完整审计，确保 Prompt 渲染结果与重构前一致 |

#### 阶段 B2：RAG 子模块重构

| 步骤 | 内容 |
|------|------|
| B2.1 | 拆分 `embedding.py` 为 `base.py` + `openai_embedding.py` + `local_embedding.py` |
| B2.2 | 封装 `retriever.py`：统一 ChromaDB 查询接口 + 健康检查 |
| B2.3 | 实现 `health_check.py`：启动时验证 Embedding 服务和 ChromaDB 连接 |
| B2.4 | 实现 `evaluation.py`：RAG hit rate / MRR 计算（离线评估用） |
| B2.5 | 验证：健康检查端点返回正确的 Provider/Embedding/ChromaDB 状态 |

#### 阶段 B3：审计流水线重构

| 步骤 | 内容 |
|------|------|
| B3.1 | 重构 `llm_audit.py` → `audit_pipeline.py`：解耦 Prompt 加载、RAG 检索、LLM 调用三个阶段 |
| B3.2 | 实现 `function_extractor.py`：AST 解析替代正则（引入 `solidity-parser` 或 `solc-ast`） |
| B3.3 | 实现 `output_validator.py`：Pydantic JSON Schema 校验 LLM 输出 |
| B3.4 | 实现 `provider_stats.py`：可观测性指标记录 |
| B3.5 | Token 预算改为环境变量配置 |
| B3.6 | 修改 Celery 任务 `run_llm_audit.py` 改为调用新 Pipeline |
| B3.7 | 验证：运行完整审计流程，结果与原实现对比一致性 |

#### 阶段 B4：流式 SSE 端点

| 步骤 | 内容 |
|------|------|
| B4.1 | 实现 `stream.py`：AuditStreamManager（Redis Pub/Sub + SSE） |
| B4.2 | 新增 API 端点：`POST .../llm-audit/stream` + `GET .../stream/{stream_id}` |
| B4.3 | Pipeline 中注入进度事件推送（parsing → embedding → rag → auditing → complete） |
| B4.4 | 实现实时 finding 推送（每发现一个漏洞立即推送给前端） |
| B4.5 | 新增管理端点：`GET /api/v1/llm/health`, `GET /api/v1/llm/metrics`, `GET /api/v1/llm/prompts` |
| B4.6 | 验证：`curl` 测试 SSE 事件流，确认所有阶段事件和 finding 事件正确推送 |

#### 阶段 B5：清理与文档

| 步骤 | 内容 |
|------|------|
| B5.1 | 移除 `services/` 中已迁移的旧文件，更新所有 import 路径 |
| B5.2 | 更新 `docker-compose.yml` 环境变量（新增 `LLM_AUDIT_MODEL`, `LLM_POLISH_MODEL` 等） |
| B5.3 | 更新 `.env.example` 所有 LLM 相关配置项 |
| B5.4 | 运行全量回归测试（Slither + Fuzzing + LLM Audit + Report 生成） |

### 合流：SSE 前后端集成

| 步骤 | 内容 |
|------|------|
| C1 | 前端 `useSSE.ts` 支持审计流式事件（progress + finding 事件类型） |
| C2 | ProjectDetailPage 和 LLMAuditPage 接入流式审计：提交后实时展示进度条 + 逐个出现的 finding |
| C3 | AppShell Status Bar 展示 LLM Provider 健康状态（来自 `/api/v1/llm/health`） |
| C4 | 端到端验证：上传合约 → 触发流式审计 → 前端实时展示进度 → finding 逐个出现 |

---

## 七、关键技术决策理由

### 7.1 为什么完全脱离 Ant Design

1. **设计诉求矛盾**：TRAE Work 是 Light-only、无阴影、品牌色稀缺的精简设计哲学；Ant Design 自带阴影、蓝白配色、丰富预设样式，两者审美方向相反
2. **体积差距**：antd ~1.2MB gzipped vs 自建组件 < 50KB
3. **可维护性**：自建组件完全可控，任何设计调整无需与第三方 API 限制抗争

### 7.2 为什么 CSS Modules 而不是 CSS-in-JS 或 Tailwind

1. 零运行时开销，构建时编译为唯一类名
2. 原生支持 `var()` 引用 CSS Custom Properties（Design Token）
3. 文件组织清晰：`ComponentName.module.css` 与 `.tsx` 同目录
4. Tailwind 需要维护自定义配置对齐 TRAE Work Token，增加复杂度

### 7.3 为什么 React Query + Zustand

1. **职责分离**：服务端数据（缓存/refetch/乐观更新）与客户端 UI 状态本质不同
2. **React Query 消除样板代码**：当前每个页面手动 `useState(loading)` + `useEffect(fetch)` + try-catch error handling
3. **Zustand 极简**：只需管理 sidebar 展开、Drawer 选中项等少量 UI 状态

### 7.4 为什么 Drawer 是核心交互模式

专业审计工具（CertiK Skynet、Trail of Bits 平台）的主流交互：
- 主视图展示发现概览（表格/列表）
- 侧边面板展示完整详情
- 不打断主列表上下文，支持快速切换多条记录
- 符合桌面应用的工具式操作习惯

### 7.5 LLM 审计报告结构对标

报告章节...（略，同前）

### 7.6 为什么 LLM 模块要独立成板块

1. **关注点分离**：当前 LLM 代码散落在 `services/` 的 9 个文件中，与其他业务逻辑（Slither、Fuzzing、Report）混在一起。独立模块后，LLM 相关的 Provider、Prompt、RAG、Pipeline、Security、Budget 全部内聚在一个命名空间下。
2. **可测试性**：独立的 `llm/` 模块可以单独进行单元测试和集成测试，不依赖 FastAPI/Celery 基础设施。
3. **可替换性**：如果未来需要切换 LLM Provider（如 OpenAI → Claude → 本地模型），只需修改 `llm/provider/`，不影响审计 Pipeline 逻辑。
4. **Prompt 版本管理**：YAML 文件天然支持 Git diff/版本追踪，方便团队协作调优 Prompt。

### 7.7 为什么采用 YAML Prompt 模板而非 Python 字符串

1. **可读性**：长 Prompt 在 Python f-string 中可读性极差（混合缩进、转义、拼接）。YAML 的多行字符串 `|` 完美解决。
2. **非开发人员可编辑**：安全研究员可以直接修改 YAML 调优 Prompt，不需要懂 Python。
3. **元数据支持**：每个模板可附带 version / model_preference / temperature / max_tokens，Pipeline 运行时自动读取。
4. **A/B 测试**：通过 Prompt 版本号，同一份合约可以用 v2.0 和 v2.1 两个版本的 Prompt 各审计一次，对比效果。

### 7.8 为什么引入流式 SSE 而非 WebSocket

1. **单向性**：审计进度推送是纯服务端→客户端单向数据流，SSE 比 WebSocket 更轻量。
2. **HTTP 兼容**：SSE 走标准 HTTP，不需要升级协议，Nginx 反向代理配置简单（当前 `nginx.conf` 已支持 SSE）。
3. **自动重连**：浏览器 `EventSource` API 自带断线重连，无需手动实现。
4. **与现有体系一致**：当前已有 SSE 端点（`/projects/{id}/events`），新增审计流式端点技术方案一致，前端复用同一个 EventSource 管理逻辑。

---

## 八、假设与前提

1. 后端 API（13 个端点）接口不变，前端仅修改对接方式
2. TRAE Work 的 671 个 SVG 图标文件可从设计库的 `assets/icons/` 目录获取
3. 当前的 SSE 事件格式保持不变，仅重构前端消费方式
4. 浏览器兼容目标：Chrome/Edge/Firefox/Safari 最近两个大版本
5. 不需要国际化（i18n），当前仅中文界面
6. 不需要暗色模式（TRAE Work 约束：仅 Light 模式）
7. Redis 服务可用（LLM 审计流式 SSE 依赖 Redis Pub/Sub）

---

## 九、验证检查点

每个阶段完成后需验证：

### 轨道 A：前端重做

| 阶段 | 验证项 |
|------|--------|
| A0 | `npm run dev` 零报错，AppShell 布局骨架正常渲染 |
| A1 | 所有 14 个 `.ds-*` 组件可交互，样式正确 |
| A2 | React Query Devtools 中可看到 API 数据流正确；SSE 连接可建立 |
| A3.1 | Dashboard + Upload 页面功能完整 |
| A3.2 | 漏洞知识库搜索/筛选/详情 Drawer 正常 |
| A3.3 | ProjectDetailPage：所有 Tab 数据加载、行点击 Drawer 展开、操作栏触发分析 |
| A3.4 | LLMAuditPage：四个报告章节 + finding Drawer 正常 |
| A3.5 | ReportPage：格式选择 + 报告生成 + 历史列表下载 |
| A4 | 触发分析后 SSE 推送 → 数据自动刷新，无手动刷新 |
| A5 | `npm run build` 成功，Docker 构建通过，TRAE Work 合规清单全部通过 |

### 轨道 B：LLM 模块重做

| 阶段 | 验证项 |
|------|--------|
| B0 | `llm/` 模块骨架可 import，ProviderRegistry 能注册和获取 Provider |
| B1 | `PromptRegistry.render("function_audit", ...)` 输出与重构前一致 |
| B2 | `GET /api/v1/llm/health` 返回 Provider/Embedding/ChromaDB 正确状态 |
| B3 | 完整审计流程结果（finding 数量、severity 分布、内容结构）与重构前对比一致 |
| B4 | `curl` SSE 端点可收到 progress + finding 事件流 |
| B5 | 全量回归测试通过（Slither + Fuzzing + LLM Audit + Report） |

### 合流验证

| 阶段 | 验证项 |
|------|--------|
| C | 前端触发流式审计 → 实时进度条 → finding 逐个出现在 Drawer 中，端到端无阻塞 |
