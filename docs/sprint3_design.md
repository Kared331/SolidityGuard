# SolidiGuard Sprint 3 — 误报反馈与基础过滤 设计文档

> Source: Sprint 3 指令 + Sprint 2 代码库现状
> 每项设计决策标注来源

---

## 1. Implementation Approach

基于 Sprint 2 代码库增量添加误报标记与过滤功能：
- 从 Slither 结果中提取单个检测项存入 `detections` 表 (来源: Sprint 3 第3条 — "新增一个 detections 表来拆分单个检测项")
- 用户标记误报时，在 `false_positive_feedbacks` 表中创建记录 (来源: Sprint 3 第3条)
- 查询分析结果时，过滤掉已有误报标记的检测项 (来源: Sprint 3 第3条 — "默认不返回被标记为误报的条目")

---

## 2. New Tables

### Table: detections
| Column | Type | Constraint |
|--------|------|------------|
| id | Integer | PK, autoincrement |
| analysis_result_id | Integer | FK → analysis_results.id |
| detection_ref | String(500) | not null, indexed |
| check_name | String(200) | not null |
| description | Text | not null |
| impact | String(50) | |
| confidence | String(50) | |
| element_json | JSON | 原始 element 数据 |

**detection_ref 生成规则**: `"{check}:{first_element_source_mapping}"` 例如 `"reentrancy-eth:contract.sol#10-20"`

来源: Sprint 3 第3条 — "可使用 Slither 输出的 check + element 组合"

### Table: false_positive_feedbacks
| Column | Type | Constraint |
|--------|------|------------|
| id | Integer | PK, autoincrement |
| detection_ref | String(500) | not null, indexed |
| user_note | Text | nullable |
| created_at | DateTime | server_default=now |

来源: Sprint 3 第3条 — "新建表 false_positive_feedbacks：id, detection_ref, user_note, created_at"

---

## 3. Modified/Existing Behavior Changes

### run_slither task 增强
- Slither 结果存入 analysis_results 后，额外解析 `results.detectors` 数组
- 对每个 detector，提取 check、description、impact、confidence、elements
- 生成 detection_ref = `f"{check}:{first_element_source_mapping}"`
- 插入 detections 表

来源: Sprint 3 第3条 — "每个 detector 结果应有一个唯一标识"

### GET /api/v1/projects/{id}/analyses 修改
- 原来返回 analysis 级别的摘要
- 修改为返回 detection 级别的列表，过滤掉 detection_ref 出现在 false_positive_feedbacks 中的条目
- 返回: `[{id, analysis_result_id, detection_ref, check_name, description, impact, confidence}, ...]`

来源: Sprint 3 第3条 — "过滤掉已有误报标记的检测项"

---

## 4. New API Endpoints

### POST /api/v1/detections/{detection_id}/mark-false-positive
- **Body**: `{"user_note": "optional note"}`
- **Logic**:
  1. 查找 detection by id
  2. 获取 detection_ref
  3. 插入 false_positive_feedbacks 记录
  4. 返回 `{"status": "marked", "detection_ref": "..."}`
- **Response**: 201 Created

来源: Sprint 3 第3条

---

## 5. Files to Create/Modify

| File | Action | Purpose |
|------|--------|---------|
| backend/app/models.py | MODIFY | 新增 Detection + FalsePositiveFeedback 模型 |
| backend/app/api/analysis.py | MODIFY | 修改 GET analyses 为 detection 级别 + 过滤误报 |
| backend/app/api/detections.py | NEW | POST mark-false-positive |
| backend/app/api/router.py | MODIFY | 注册 detections 路由 |
| backend/app/tasks/run_slither.py | MODIFY | 提取 detections 并存入表 |
| backend/alembic/versions/004_add_detections_and_feedbacks.py | NEW | 迁移文件 |

---

## 6. Alembic Migration (004)

- 创建 `detections` 表 (id, analysis_result_id FK, detection_ref, check_name, description, impact, confidence, element_json)
- 创建 `false_positive_feedbacks` 表 (id, detection_ref, user_note, created_at)
- 创建索引: detections.detection_ref, false_positive_feedbacks.detection_ref

来源: Sprint 3 第5条

---

## 7. Design Compliance Checklist

| Sprint 3 Requirement | Status |
|----------------------|--------|
| detections 表拆分单个检测项 | ✅ |
| false_positive_feedbacks 表 | ✅ |
| detection_ref 基于 Slither check + element | ✅ |
| POST /api/v1/detections/{id}/mark-false-positive | ✅ |
| GET analyses 过滤误报 | ✅ |
| 不实现置信度自动调整 | ✅ |
| 不实现机器学习 | ✅ |
| 不实现重分类 severity | ✅ |
| Alembic 迁移仅新增两张表 + 索引 | ✅ |
| detection_ref 仅依赖 Slither 输出结构 | ✅ |
