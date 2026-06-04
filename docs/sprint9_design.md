# SolidiGuard Sprint 9 — 前端漏洞库与误报反馈页面 设计文档

> Source: Sprint 9 指令 + Sprint 3/4 后端 API + Sprint 8 前端代码库
> 每项设计决策标注来源

---

## 1. Gap Analysis

Sprint 4 只提供了 `POST /api/v1/knowledge/sync`（同步），未暴露查询 API。
前端漏洞库浏览页面需要查询接口，因此本 Sprint 补充实现。

来源: Sprint 9 输入说明 — "若漏洞库浏览需要查询 API，则作为本 Sprint 的一部分实现"

---

## 2. Backend Addition: GET /api/v1/vulnerabilities

### Query Parameters
- `search`: optional string，按 title/description 模糊搜索（ILIKE）
- `page`: int, default 1
- `page_size`: int, default 20

### Response
```json
{
  "total": 100,
  "page": 1,
  "page_size": 20,
  "items": [
    {
      "id": 1,
      "swc_id": "SWC-101",
      "title": "Integer Overflow and Underflow",
      "description": "...",
      "severity": "High",
      "code_example": "..."
    }
  ]
}
```

### Implementation
- 新文件 `backend/app/api/vulnerabilities.py`
- 查询 `vulnerability_entries` 表
- 仅返回表中已有字段，不补全未同步数据 (来源: Sprint 9 证据层约束)
- 不涉及 RAG 或审计逻辑 (来源: Sprint 9 第3条)

---

## 3. Frontend: /vulnerabilities Page

### Features
- antd `Table` 展示漏洞列表
- antd `Input.Search` 搜索框（按关键字搜索）
- 点击行展开详情（antd `Descriptions` 或 Expandable Row）
- 显示: SWC ID、标题、严重程度、描述、代码示例

### Route
- `/vulnerabilities` → VulnerabilitiesPage

来源: Sprint 9 第3条

---

## 4. Frontend: Mark False Positive Button

### Location
- 在 `ProjectDetailPage` 的 Slither 结果表格中
- 每行添加"标记误报"按钮（antd `Button` + `Popconfirm`）

### Behavior
- 点击确认后调用 `POST /api/v1/detections/{id}/mark-false-positive`
- 成功后从列表中移除该项（前端过滤）
- 调用签名与 Sprint 3 完全一致 (来源: Sprint 9 证据层约束)

### API
- `POST /api/v1/detections/{detection_id}/mark-false-positive`
- Body: `{}` (无 user_note，简化交互)

来源: Sprint 9 第3条 + Sprint 3 已实现的 API

---

## 5. Navigation Update

在 App.tsx 的 Header 中添加导航菜单：
- Upload
- Vulnerabilities

来源: Sprint 9 第3条 — 用户需要能访问漏洞库页面

---

## 6. Files to Create/Modify

### Backend
| File | Action | Purpose |
|------|--------|---------|
| backend/app/api/vulnerabilities.py | NEW | GET /api/v1/vulnerabilities |
| backend/app/api/router.py | MODIFY | 注册 vulnerabilities 路由 |

### Frontend
| File | Action | Purpose |
|------|--------|---------|
| frontend/src/pages/VulnerabilitiesPage.tsx | NEW | 漏洞库浏览页面 |
| frontend/src/pages/ProjectDetailPage.tsx | MODIFY | 添加"标记误报"按钮 |
| frontend/src/main.tsx | MODIFY | 添加 /vulnerabilities 路由 |
| frontend/src/App.tsx | MODIFY | 添加导航菜单 |

---

## 7. Design Compliance Checklist

| Sprint 9 Requirement | Status |
|----------------------|--------|
| GET /api/v1/vulnerabilities（分页+搜索） | ✅ |
| 仅返回 vulnerability_entries 已有字段 | ✅ |
| 不涉及 RAG 或审计逻辑 | ✅ |
| /vulnerabilities 页面（表格+搜索+详情） | ✅ |
| Slither 结果"标记误报"按钮 | ✅ |
| 调用 Sprint 3 的 API 签名 | ✅ |
| 标记后即时刷新列表 | ✅ |
| 不改变报告生成或分析流程 | ✅ |
| 不添加"添加到自定义规则"按钮 | ✅ |
| 不设计 severity 调整滑条 | ✅ |
| 容器化不做修改 | ✅ |
