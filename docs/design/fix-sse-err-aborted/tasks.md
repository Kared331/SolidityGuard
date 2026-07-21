# 任务列表

## Task 1: 修复 useTaskProgress Hook 的 EventSource 生命周期 ✅
修改 `frontend/src/hooks/useTaskProgress.ts`，修复 EventSource 在快速路由切换时产生 `ERR_ABORTED` 的问题。

- [x] 1.1 新增 `esRef` (useRef<EventSource>) 管理 ES 实例
- [x] 1.2 新增 `cancelled` flag 防止卸载后回调 setState
- [x] 1.3 用 `setTimeout(200ms)` 延迟 EventSource 创建
- [x] 1.4 在所有 `onopen`/`onmessage`/`onerror` 回调中检查 `cancelled`
- [x] 1.5 清理函数中清除 timer 并安全关闭 EventSource

## Task 2: 构建并部署前端
重新构建前端 bundle，确保 Docker nginx 加载最新 JS。

- [x] 2.1 运行 `npm run build`
- [x] 2.2 验证新 JS bundle hash 已变化
- [x] 2.3 重启 frontend 容器加载新 bundle

## Task 3: 验证修复效果
在浏览器中验证 ERR_ABORTED 不再出现。

- [x] 3.1 打开项目详情页，确认 SSE 正常工作
- [x] 3.2 快速导航到其他页面，检查控制台无 ERR_ABORTED
- [x] 3.3 验证 SSE 事件推送功能正常（Slither/Fuzz 完成后前端自动刷新）

# 任务依赖
- Task 2 依赖 Task 1
- Task 3 依赖 Task 2
