# 任务列表

## Task 1: 修复前端 FormData 字段名不匹配（主因修复）✅
修改 `UploadPage.tsx` 中 `handleUpload` 的 `formData.append('file', file)` 为 `formData.append('files', file)`，确保与后端 `projects.py` 中 `files: List[UploadFile]` 声明一致。

- [x] 1.1 打开 `frontend/src/pages/Upload/UploadPage.tsx`
- [x] 1.2 将第 69 行 `formData.append('file', file)` 改为 `formData.append('files', file)`
- [x] 1.3 确认 `useCreateProject` hook（`useProjects.ts`）无需修改（已正确发送 FormData）

**验证**：前端构建无 TS 错误，逻辑上字段名与后端匹配。

## Task 2: 审查魔数校验 `_verify_magic_bytes` 的 ZIP 兼容性 ✅
审查 `backend/app/services/project_service.py` 中 `_verify_magic_bytes` 的 ZIP 校验分支，确认不会误拒合法 ZIP 文件。

- [x] 2.1 确认 ZIP 文件魔数 `PK\x03\x04` 覆盖标准 ZIP、ZIP64 格式
- [x] 2.2 检查空 ZIP 文件（0 字节）是否被静默拒绝并给出日志
- [x] 2.3 如有必要，增加日志区分"魔数不匹配"和"文件为空"场景

**验证**：用标准 `.zip` 文件（含 `.sol` 内容）走通 `_verify_magic_bytes` 逻辑。

## Task 3: 增强前端上传错误提示 ✅
修改 `UploadPage.tsx` 错误处理，区分不同失败场景，提供更有意义的错误信息。

- [x] 3.1 在 `handleUpload` 的 `catch` 块中解析 HTTP 响应体，提取 `detail` 信息
- [x] 3.2 对 422 错误提示"文件格式不支持或请求参数有误"
- [x] 3.3 对 413 错误提示"文件大小超过限制（最大 50MB）"
- [x] 3.4 对 5xx 错误提示"服务端错误，请稍后重试"
- [x] 3.5 保留网络连接失败等通用错误提示

**验证**：模拟不同错误场景，确认前端显示对应的中文提示。

# 任务依赖
- Task 2 可与 Task 1 并行执行（互不阻塞）
- Task 3 依赖 Task 1 完成（需要先修复上传才能测试错误场景）
