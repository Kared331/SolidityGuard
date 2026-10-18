# P4 知识库快照化 · 实施证据

> 日期：2026-10-18
> 环境：worker 容器（本地 all-MiniLM-L6-v2 + Chroma，37 条）
> 结论：**知识库离线可复现、有版本、元数据补齐；但检索质量经实测偏低，P4 不据此调参。**

---

## 1. 改造前

| 问题 | 证据 |
|---|---|
| 每次同步都访问已归档的 GitHub 仓库 | `swc_sync.py` 中 `httpx.get(.../SWC-registry/contents/entries/docs)` |
| 无版本概念 | 无任何 hash / 版本字段 |
| 断网即空 | 拉取失败直接抛异常，知识库无降级路径 |
| **Chroma 文档没有 metadata** | `collection.upsert(ids, documents, embeddings)` 缺 `metadatas` |

最后一条是本次探针才发现的：检索器读 `meta.get("title")`，而 metadata 为空，于是注入 prompt 的每一条 RAG 上下文都写成 `- Unknown: ...`。E2E 里 `rag_hits=5` 看起来正常，实际标题全是 `Unknown`。

---

## 2. 改造后

| 项 | 实现 |
|---|---|
| 离线快照 | `backend/app/services/engine/data/swc_registry.json`，**37 条**，88 KB，随代码入库 |
| 默认离线 | `SWCSyncEngine.execute(refresh=False)` 只读快照，测试用 `httpx.get` 抛异常证明不会联网 |
| 显式刷新 | `POST /knowledge/sync?refresh=true` 才访问上游，且结果必须通过校验（37 条、id 唯一、字段非空） |
| 版本号 | `kb_version = "swc-" + sha256(条目集)[:8]`，实测 `swc-52c82b8a`，写入 `audit_runs.kb_version` |
| 幂等写入 | 按 `swc_id` upsert；实测重复同步后 `vulnerability_entries` 仍为 **37** 行 |
| 元数据 | `metadatas=[{"swc_id", "title", "severity"}]`，重同步后检索标题恢复 |

一次真实同步的 worker 日志：

```
SWC sync completed: 37 entries from snapshot (swc-52c82b8a)
```

新的审计运行也带上了版本：`id=4 | kb_version=swc-52c82b8a | prompt_version=9d15319c | degraded`。

---

## 3. 检索实测（10 条人工构造 query）

环境：本地 `all-MiniLM-L6-v2`（CPU）+ Chroma，`n_results=3`，距离为余弦距离（越小越近）。

| query 意图 | 期望 SWC | top-3 | top-1 距离 |
|---|---|---|---|
| 重入（call 后扣余额） | 107 | 135, 105, 100 | 1.0206 |
| 溢出/下溢 | 101 | 135, 107, 100 | 1.0766 |
| selfdestruct | 106 | **106**, 105, 134 | 1.1080 |
| 弱随机数 | 120 | 130, 111, 100 | 1.4513 |
| delegatecall | 112 | **112**, 115, 100 | 0.9398 |
| tx.origin | 115 | **115**, 124, 118 | 1.2191 |
| 区块 gas DoS | 128 | 129, **128**, 111 | 1.4883 |
| 无权限 setter | 105/122 | **105**, 130, 135 | 1.3424 |
| 浮动 pragma | 103 | 102, **103**, 111 | 1.1705 |
| 未检查返回值 | 104 | 134, 135, 130 | 1.1378 |

**按作者判断**：top-1 命中 **4/10**，top-3 命中 **7/10**。重入、溢出、弱随机数这三个最该命中的全部落空。

典型失败：`reentrancy_call` 的第一名是 `SWC-135 Code With No Effects`——因为两边都含 `call`/`= ` 这类表面词，而 37 条语料每条只有一段通用描述，区分度极低。

---

## 4. 这次测量改变了什么

1. **确认 RAG 的实际能力低于 README 暗示**。之前所有人都以为"注入 SWC 知识能提升识别"，实测是 4/10。P4 不做调参（`topK`、换模型、扩语料都属于 P6 的实验变量），但把这个数字记下来，避免再凭空声明。
2. **`Unknown` 标题是一个静默缺陷**：它不影响 `rag_hits` 计数，也不报错，只是让注入的上下文失去可读标题。现在补了 metadata 与两条单测。
3. **快照 + 版本号让"知识库漂移"变成可检测的**：两次审计的 `kb_version` 不同，就说明知识库变了，结论不可直接比较。

---

## 5. 测试

`tests/test_swc_snapshot.py`（11 条）：

| 组 | 断言 |
|---|---|
| 完整性 | 37 条、id 唯一、必填字段非空 |
| 校验 | 条数不符 / 字段缺失 → `ValueError` |
| 版本 | 稳定；条目改动后变化 |
| 离线 | 默认路径下 `httpx.get` 抛异常也不会被调用 |
| 刷新 | `refresh=True` 使用拉取结果，来源标记为 `refresh` |
| Chroma | metadata 全为字符串且非 None；文档含 title 与 description |
| 幂等 | 新条目 `add`、已有条目只更新不新增 |

---

## 6. 不做的事（与蓝图一致）

| 不做 | 理由 |
|---|---|
| 扩语料 / 换 embedding / 调 topK | 都是 P6 的实验变量；先有基线再谈提升 |
| 对 37 条做人工重写 | 会引入主观性，且无法证明更好 |
| 把检索质量写进 README 优点 | 实测 4/10，不能这么写 |

**范围声明**：P4 交付的是"可复现、有版本、元数据完整"的知识库，不是"更好的知识库"。
