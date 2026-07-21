# 验证检查清单

- [x] `UploadPage.tsx` 中 `formData.append` 字段名已从 `'file'` 改为 `'files'`
- [x] 前端 TypeScript 编译无错误
- [x] `_verify_magic_bytes` 对合法 `.zip` 文件返回 `True`
- [x] 空 `.zip` 文件或损坏 `.zip` 文件有明确的日志记录（非静默丢弃）
- [x] 前端对不同 HTTP 错误码（422 / 413 / 5xx）显示对应的中文错误提示
- [x] `useCreateProject` hook 无需修改即可与修正后的字段名配合工作
