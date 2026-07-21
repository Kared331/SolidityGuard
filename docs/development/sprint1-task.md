# Sprint 1 任务：Model 包拆分

## 项目路径
D:\MetaGPT_Project\SolidGuard

## 当前状态
后端所有 Model 定义在单一文件 `backend/app/models.py` 中，包含 9 个类。
Base 类定义在 `backend/app/database.py` 中。

## 任务目标
将 `backend/app/models.py` 拆分为 `backend/app/models/` 包，按业务领域分文件。

## 具体步骤

### 步骤 1：备份并创建包结构
- 将 `backend/app/models.py` 重命名为 `backend/app/models_old.py`（备份）
- 创建 `backend/app/models/` 目录
- 创建空的 `backend/app/models/__init__.py`

### 步骤 2：拆分 Model 文件
从 `models_old.py` 中提取以下类到独立文件，代码原封不动搬入（不修改任何逻辑）：

1. `backend/app/models/project.py` — Project, ProjectFile
2. `backend/app/models/analysis.py` — AnalysisResult, Detection
3. `backend/app/models/audit.py` — FuzzingResult, LLMAuditResult
4. `backend/app/models/feedback.py` — FalsePositiveFeedback
5. `backend/app/models/knowledge.py` — VulnerabilityEntry
6. `backend/app/models/report.py` — Report

每个文件需要：
- 独立的 import 语句（从 models_old.py 中对应类的 import 提取）
- Base 类通过 `from app.database import Base` 引入
- relationship 使用字符串形式引用跨文件类（如 `list["ProjectFile"]`）

### 步骤 3：填充 __init__.py
`backend/app/models/__init__.py` 必须导出全部 9 个类，保持 `from app.models import X` 兼容：

```python
from app.models.project import Project, ProjectFile
from app.models.analysis import AnalysisResult, Detection
from app.models.audit import FuzzingResult, LLMAuditResult
from app.models.feedback import FalsePositiveFeedback
from app.models.knowledge import VulnerabilityEntry
from app.models.report import Report

__all__ = [
    "Project", "ProjectFile",
    "AnalysisResult", "Detection",
    "FuzzingResult", "LLMAuditResult",
    "FalsePositiveFeedback",
    "VulnerabilityEntry",
    "Report",
]
```

### 步骤 4：验证
由于 __init__.py 重新导出了所有类，现有的 `from app.models import X` 写法完全兼容，无需修改任何引用文件的 import 语句。

验证命令：
```bash
cd D:\MetaGPT_Project\SolidGuard\backend
python -c "from app.models import Project, ProjectFile, AnalysisResult, Detection, FuzzingResult, LLMAuditResult, FalsePositiveFeedback, VulnerabilityEntry, Report; print('OK')"
```

## 关键约束
- 表名（__tablename__）、字段名、外键关系 **不变**
- 不修改任何数据库表结构
- 不新增任何字段或关系
- 不修改其他文件的 import 语句
- 不删除 models_old.py（保留备份）

## 禁止事项
- 禁止新增 status 字段到 Project
- 禁止新增 Pydantic Schema
- 禁止修改 API handler
- 禁止修改 Celery Task
- 禁止为"未来 Service 层"预留接口
- 禁止为"未来 Pipeline"预留字段
