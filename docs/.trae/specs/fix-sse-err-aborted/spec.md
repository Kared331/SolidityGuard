# SSE ERR_ABORTED 修复 规格说明

## Why
`ProjectDetailPage` 中的 `useTaskProgress` Hook 使用浏览器原生 `EventSource` 连接 SSE 端点 `/api/v1/projects/{id}/events`。当用户快速导航离开页面时，React 卸载组件触发 `es.close()`，但此时 EventSource 的 TCP 连接可能尚未完成握手，浏览器控制台输出 `net::ERR_ABORTED`。此错误不阻塞功能，但污染控制台日志，影响开发体验。

## What Changes
- 修改 `useTaskProgress` Hook 中的 EventSource 创建时机：添加 200ms 延迟
- 添加 `cancelled` flag 防止组件卸载后触发 setState
- 用 `useRef<EventSource>` 管理 EventSource 实例生命周期
- 清理时安全关闭连接，避免 ERR_ABORTED

## Impact
- Affected specs: 无
- Affected code: `frontend/src/hooks/useTaskProgress.ts`

## ADDED Requirements
### Requirement: 安全 EventSource 生命周期管理
系统 SHALL 在 `useTaskProgress` Hook 中以安全的方式管理 EventSource 连接生命周期，避免控制台 `net::ERR_ABORTED` 错误。

#### Scenario: 正常连接与断开
- **WHEN** 组件挂载且 `projectId` 有效
- **THEN** 在 200ms 后建立 EventSource 连接
- **AND** 收到 SSE 事件时更新 `lastEvent` 状态并调用 `onEvent` 回调
- **AND** 连接断开时更新 `connected` 和 `error` 状态

#### Scenario: 快速路由切换
- **WHEN** 组件在 200ms 延迟内卸载
- **THEN** 不创建 EventSource 连接
- **AND** 控制台不输出 ERR_ABORTED

#### Scenario: 组件卸载时清理
- **WHEN** 组件已建立 EventSource 连接后卸载
- **THEN** 安全关闭 EventSource 连接
- **AND** 不触发 setState（避免 React 在已卸载组件上的状态更新警告）
- **AND** 控制台不输出 ERR_ABORTED
