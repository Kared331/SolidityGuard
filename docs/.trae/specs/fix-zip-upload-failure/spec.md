# 修复 ZIP 文件上传失败 规格说明

## Why
审计项目上传模块中，`.zip` 文件上传失败，用户无法通过前端界面上传 ZIP 格式的 Solidity 合约项目包，导致多文件批量审计流程完全不可用。

## What Changes
- 修复前端与后端 FormData 字段名不匹配问题（`file` vs `files`）— **主因**
- 审查 `_verify_magic_bytes` 魔数校验逻辑，确保合法 ZIP 文件不被误拒
- 增强前端错误提示，区分网络错误、服务端校验失败、服务端内部错误

## Impact
- Affected specs: 无
- Affected code:
  - `frontend/src/pages/Upload/UploadPage.tsx` — FormData 字段名修正
  - `backend/app/services/project_service.py` — 魔数校验健壮性（如有必要）
  - `backend/app/api/projects.py` — 错误响应处理（如有必要）

## ADDED Requirements

### Requirement: 前端上传字段名与后端一致
系统 SHALL 确保前端 `FormData` 中的文件字段名与后端 FastAPI 端点声明一致。

#### Scenario: ZIP 文件上传成功
- **WHEN** 用户选择 `.zip` 文件并点击上传
- **THEN** 前端以字段名 `files` 发送 `multipart/form-data` 请求
- **AND** 后端 `POST /api/v1/projects` 正确接收到文件列表
- **AND** 返回 200 及项目信息，状态为 `uploaded`

#### Scenario: 单文件 .sol 上传保持兼容
- **WHEN** 用户选择 `.sol` 文件并点击上传
- **THEN** 前端同样以字段名 `files` 发送请求
- **AND** 后端正确处理并返回 200

### Requirement: 魔数校验不误拒合法 ZIP 文件
系统 SHALL 确保 `_verify_magic_bytes` 对所有合法 ZIP 格式文件（含空 ZIP 和 ZIP64）返回 `True`，仅拒绝明显损坏的文件。

#### Scenario: 合法 ZIP 通过校验
- **WHEN** 用户上传一个有效的 `.zip` 文件（非空，标准格式）
- **THEN** `_verify_magic_bytes` 返回 `True`，文件被接受

#### Scenario: 空 ZIP 文件的合理处理
- **WHEN** 用户上传一个空 `.zip` 文件（0 字节或无有效条目）
- **THEN** 系统不应因魔数校验失败而静默丢弃
- **AND** 应在适当阶段给出友好提示（如 "No .sol files found"）

## MODIFIED Requirements
无

## REMOVED Requirements
无
