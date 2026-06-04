# SolidiGuard Sprint 8 — 前端项目初始化及核心页面 设计文档

> Source: Sprint 8 指令 + Sprint 1-7 后端 API 实际端点
> 每项设计决策标注来源

---

## 1. Available Backend API Endpoints (Sprint 1-7)

| Method | Path | Sprint | Used In Frontend |
|--------|------|--------|-----------------|
| GET | `/health` | 0 | 不使用 |
| POST | `/api/v1/projects` | 1 | 上传页面 |
| GET | `/api/v1/projects/{id}/files` | 1 | 项目详情页 |
| POST | `/api/v1/projects/{id}/analyze` | 2 | 项目详情页 |
| GET | `/api/v1/projects/{id}/analyses` | 2 | 项目详情页 |
| POST | `/api/v1/projects/{id}/fuzz` | 5 | 项目详情页 |
| GET | `/api/v1/projects/{id}/fuzz-results` | 5 | 项目详情页 |
| POST | `/api/v1/projects/{id}/llm-audit` | 6 | 项目详情页 |
| GET | `/api/v1/projects/{id}/llm-audit-results` | 6 | 项目详情页 |
| POST | `/api/v1/projects/{id}/report` | 7 | 报告页面 |
| GET | `/api/v1/reports/{id}/download?format=...` | 7 | 报告页面 |

来源: Sprint 1-7 实际代码审查，不得臆造未实现接口 (来源: Sprint 8 证据层约束)

---

## 2. Tech Stack

- **Vite** + **React 18** + **TypeScript** (来源: 技术栈约束 React 18 + Vite)
- **Ant Design (antd)** 组件库 (来源: Sprint 8 第3条)
- **axios** HTTP 客户端 (来源: Sprint 8 第3条)
- **react-router-dom** 路由 (来源: Sprint 8 第3条)

---

## 3. Page Tree & Routing

```
/ → redirect to /upload
/upload → UploadPage (拖拽上传)
/projects/:id → ProjectDetailPage (文件列表 + 分析触发 + 结果展示)
/projects/:id/report → ReportPage (报告生成 + 下载)
```

来源: Sprint 8 第3条 — 仅三个页面

注意：无误报标记页面、无漏洞库浏览页面 (来源: Sprint 8 第4条 + 反推禁止规则)

---

## 4. Component Architecture

```
frontend/
├── src/
│   ├── main.tsx                    # 入口，React Router 配置
│   ├── App.tsx                     # 布局组件（antd Layout + Menu）
│   ├── api/
│   │   └── client.ts              # axios 实例，基础 URL 可配置
│   ├── pages/
│   │   ├── UploadPage.tsx          # 拖拽上传 → POST /api/v1/projects
│   │   ├── ProjectDetailPage.tsx   # 文件列表 + 3个触发按钮 + 结果展示
│   │   └── ReportPage.tsx          # 生成报告 + 下载按钮
│   └── vite-env.d.ts
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
├── Dockerfile
└── nginx.conf
```

---

## 5. Page Details

### UploadPage (`/upload`)
- antd `Upload.Dragger` 组件
- 支持拖拽或点击上传 `.sol`、`.zip`、`.tar.gz`
- 调用 `POST /api/v1/projects` (multipart/form-data)
- 上传成功后 `navigate(/projects/${id})`
- 显示上传进度

来源: Sprint 8 第3条第1点

### ProjectDetailPage (`/projects/:id`)
- **文件列表**: 调用 `GET /api/v1/projects/{id}/files`，antd `Table` 展示
- **操作按钮**:
  - "Run Slither" → `POST /api/v1/projects/{id}/analyze`
  - "Run Fuzzing" → `POST /api/v1/projects/{id}/fuzz`
  - "Run LLM Audit" → `POST /api/v1/projects/{id}/llm-audit`
- **结果展示** (antd `Tabs`):
  - Tab "Slither Results": 调用 `GET /api/v1/projects/{id}/analyses`，Table 展示
  - Tab "Fuzzing Results": 调用 `GET /api/v1/projects/{id}/fuzz-results`，Table 展示
  - Tab "LLM Results": 调用 `GET /api/v1/projects/{id}/llm-audit-results`，Table 展示
- **轮询**: 触发操作后，定时轮询结果 API 直到有数据出现
- **导航**: "Generate Report" 按钮跳转到 `/projects/:id/report`

来源: Sprint 8 第3条第2点

### ReportPage (`/projects/:id/report`)
- 选择格式: antd `Radio.Group` (HTML / PDF / Word)
- "Generate" 按钮 → `POST /api/v1/projects/{id}/report`
- 生成完成后显示下载链接 → `GET /api/v1/reports/{id}/download?format=...`
- 不实现在线预览 (来源: Sprint 8 第3条第3点)

来源: Sprint 8 第3条第3点

---

## 6. API Client Configuration

- axios 实例，baseURL 从环境变量 `VITE_API_BASE_URL` 读取
- 默认: `http://localhost:8000`
- Vite 代理配置: 开发模式下 proxy `/api` 到后端

来源: Sprint 8 第3条

---

## 7. Docker & Nginx

### frontend/Dockerfile
- Multi-stage build: node:20-alpine 构建 → nginx:alpine 运行
- 构建: `npm install && npm run build`
- 运行: 复制 dist/ 到 nginx html 目录

### frontend/nginx.conf
- 静态文件服务
- `/api` 反向代理到 `api:8000`
- SPA fallback: `try_files $uri $uri/ /index.html`

### docker-compose.yml 更新
- 新增 `frontend` 服务
- 端口: `3000:80`
- 依赖: `api`

来源: Sprint 8 第5条

---

## 8. Design Compliance Checklist

| Sprint 8 Requirement | Status |
|----------------------|--------|
| Vite + React + antd + axios + react-router-dom | ✅ |
| 上传页面 /upload (拖拽) | ✅ |
| 项目详情页 /projects/:id (文件列表+触发+结果) | ✅ |
| 报告页面 /projects/:id/report (生成+下载) | ✅ |
| 统一 axios 实例，baseURL 可配置 | ✅ |
| 不实现误报反馈界面 | ✅ |
| 不实现漏洞库浏览 | ✅ |
| API 端点严格基于 Sprint 1-7 | ✅ |
| UI 组件仅使用 antd 标准组件 | ✅ |
| 前端容器化 (Dockerfile + nginx) | ✅ |
| 更新 docker-compose.yml | ✅ |
| 不预留误报标记路由/菜单 | ✅ |
| 不添加"标记误报"按钮 | ✅ |
