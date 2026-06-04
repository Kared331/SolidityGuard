# SolidiGuard Sprint 1 — 文件上传与解压服务 设计文档

> Source: MetaGPT output (reviewed & cleaned for Sprint 1 compliance)
> Violations removed: extra fields, excessive status enum, Sprint 2 recommendations

---

## 1. Implementation Approach

基于 Sprint 0 代码库增量添加文件上传功能：
- **FastAPI** multipart 接收文件上传 (来源: Sprint 0 + Sprint 1)
- **SQLAlchemy async** 新增 projects 和 project_files 表 (来源: Sprint 1 第4条)
- **Celery process_upload** 任务处理解压和 .sol 文件识别 (来源: Sprint 1 第3条)
- **本地文件系统** 存储于 `uploads/{project_id}/` (来源: Sprint 1)

---

## 2. Database Models (SQLAlchemy)

### Table: projects
| Column | Type | Constraint |
|--------|------|------------|
| id | Integer | PK, autoincrement |
| name | String(255) | nullable |
| created_at | DateTime | default=now |

### Table: project_files
| Column | Type | Constraint |
|--------|------|------------|
| id | Integer | PK, autoincrement |
| project_id | Integer | FK → projects.id |
| file_path | String(500) | not null |
| status | String(20) | default='pending' |

Status values: `pending` → `ready`

来源: Sprint 1 第4条

---

## 3. API Endpoints

### POST /api/v1/projects
- **Content-Type**: multipart/form-data
- **Fields**: `name` (optional str), `file` (required, multiple allowed)
- **Accepts**: `.sol` 文件, `.zip` 压缩包, `.tar.gz` 压缩包
- **Logic**:
  1. 创建 project 记录
  2. 保存文件到 `uploads/{project_id}/`
  3. 触发 Celery `process_upload` 任务
  4. 返回 `{"id": project_id, "name": name}`
- **Response**: 201 Created

### GET /api/v1/projects/{id}/files
- **Logic**: 查询 project_files WHERE project_id = id
- **Response**: `[{"id": 1, "file_path": "contracts/Token.sol", "status": "ready"}, ...]`

来源: Sprint 1 第3条

---

## 4. Celery Task: process_upload

### Input
- `project_id`: int

### Logic
1. 定位 `uploads/{project_id}/` 目录
2. 遍历目录中所有文件：
   - 如果是 `.zip`：解压到 `uploads/{project_id}/`
   - 如果是 `.tar.gz`：解压到 `uploads/{project_id}/`
   - 解压后删除原始压缩包
3. 扫描目录树，筛选所有 `.sol` 文件
4. 对每个 `.sol` 文件：
   - 计算相对路径
   - 插入 project_files 记录，status='pending'
   - 更新 status 为 'ready'

### Archive Handling
- **zipfile** 模块处理 `.zip`
- **tarfile** 模块处理 `.tar.gz`
- 解压后递归扫描所有子目录

来源: Sprint 1 第3条

---

## 5. File Storage

```
uploads/
└── {project_id}/
    ├── contract1.sol
    ├── contracts/
    │   └── token.sol
    └── (extracted files)
```

- 每个项目独立子目录
- Docker volume 挂载 `./uploads:/app/uploads`

来源: Sprint 1

---

## 6. New Files to Create/Modify

| File | Action | Purpose |
|------|--------|---------|
| backend/app/models.py | NEW | SQLAlchemy models for projects, project_files |
| backend/app/api/ | NEW | API router with projects endpoints |
| backend/app/tasks/ | NEW | Celery process_upload task |
| backend/app/main.py | MODIFY | Include API router |
| backend/alembic/versions/002_add_projects_tables.py | NEW | Migration |

来源: Sprint 0 现有结构 + Sprint 1 需求

---

## 7. Alembic Migration

Single migration adding:
- `projects` table (id, name, created_at)
- `project_files` table (id, project_id, file_path, status)

来源: Sprint 1 第4条

---

## 8. Dependency Changes

No new Python dependencies needed. `zipfile` and `tarfile` are stdlib.

来源: Sprint 1 第6条（隐含）

---

## Design Compliance Checklist

| Sprint 1 Requirement | Status |
|----------------------|--------|
| POST /api/v1/projects | ✅ |
| 支持 .sol, zip, tar.gz | ✅ |
| 保存到 uploads/ 目录 | ✅ |
| Celery process_upload 任务 | ✅ |
| projects 表 (id, name, created_at) | ✅ |
| project_files 表 (id, project_id, file_path, status) | ✅ |
| status 默认 pending，完成后 ready | ✅ |
| GET /api/v1/projects/{id}/files | ✅ |
| Alembic 迁移 | ✅ |
| 无审计/分析逻辑 | ✅ |
| 无额外字段 | ✅ |
