# Sprint B 执行日志

**日期：** 2026-06-09 12:15
**状态：** ✅ 完成 (8/8)

## 修复清单

| Fix | 描述 | 文件 | 状态 |
|-----|------|------|------|
| #6 | 数据库外键索引 | `analysis.py`, `audit.py`, `project.py`, `report.py`, `011_add_foreign_key_indexes.py` | ✅ |
| #7 | 清理任务级联删除 | `cleanup.py` | ✅ |
| #9 | CORS 配置 | `main.py` | ✅ |
| #11 | 速率限制 | `main.py`, `requirements.txt` | ✅ |
| #12 | SSE 轮询优化 | `events.py` | ✅ |
| #13 | 线程安全单例 | `chroma_client.py`, `embedding.py` | ✅ |
| #14 | Embedding 模型名配置化 | `embedding.py` | ✅ |
| #16 | 数据库连接池配置 | `database.py` | ✅ |

## 额外修复

- **str(Exception) bug** — 修复了 6 个 Celery 任务文件中的 `str(Exception)` → `str(e)` 错误

## 详细改动

### Fix #6 — 数据库外键索引
- 所有 FK 列添加 `index=True`: `AnalysisResult.project_id`, `Detection.analysis_result_id`, `FuzzingResult.project_id`, `LLMAuditResult.project_id`, `ProjectFile.project_id`, `Report.project_id`
- Alembic 迁移 `011_add_foreign_key_indexes.py` 创建 6 个索引

### Fix #7 — 清理任务级联删除
- `cleanup.py`: 添加 `AnalysisResult`, `Detection`, `FuzzingResult`, `LLMAuditResult`, `Report`, `FalsePositiveFeedback` 的级联删除
- 按 FK 依赖顺序删除（detections → analysis_results → ... → projects）

### Fix #9 — CORS 配置
- `main.py`: 添加 `CORSMiddleware`，允许来源通过 `CORS_ORIGINS` 环境变量配置

### Fix #11 — 速率限制
- 安装 `slowapi`，添加到 `requirements.txt`
- `main.py`: 添加 `Limiter` 配置，默认 60 req/min，使用 Redis 存储

### Fix #12 — SSE 轮询优化
- `events.py`: 轮询间隔从 1s 提升到 5s（80% 减少）
- 5 个 COUNT 查询合并为 1 个 JOIN 查询
- 添加自适应退避（无变更时逐步增加间隔到最大 30s）

### Fix #13 — 线程安全单例
- `chroma_client.py`: 双重检查锁定 (double-checked locking) 保护 ChromaDB 单例
- `embedding.py`: 同样模式保护 SentenceTransformer 本地模型单例

### Fix #14 — Embedding 模型名配置化
- `embedding.py`: 模型名从硬编码 `text-embedding-3-small` 改为 `EMBEDDING_MODEL_NAME` 环境变量

### Fix #16 — 数据库连接池配置
- `database.py`: 添加 `pool_size`, `max_overflow`, `pool_recycle`, `pool_pre_ping` 参数
- 异步和同步引擎均配置，参数通过环境变量可调

### 额外 — str(Exception) bug 修复
- `process_upload.py`, `generate_report.py`, `run_fuzzer.py`, `run_llm_audit.py`, `run_slither.py`, `sync_swc.py`
- 全部从 `str(Exception)` 修正为 `str(e)`
