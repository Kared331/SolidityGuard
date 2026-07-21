# 验收检查清单

## 代码修改
- [x] `useTaskProgress.ts` 中 `esRef` 正确管理 EventSource 实例
- [x] `cancelled` flag 在所有异步回调中检查
- [x] `setTimeout` 延迟 EventSource 创建，快速卸载时不建立连接
- [x] 清理函数中 `clearTimeout(timer)` 和 `esRef.current.close()` 正确调用

## 构建与部署
- [x] 前端 `npm run build` 无 TypeScript 错误
- [x] 新 JS bundle 已通过 nginx 提供服务
- [x] Docker frontend 容器使用最新 dist

## 功能验证
- [x] 打开项目详情页 → SSE 连接正常建立
- [x] 触发分析 → SSE 事件推送 → 前端自动刷新结果
- [x] 从项目详情页导航到其他页面 → 控制台无 `net::ERR_ABORTED`
- [x] 快速连续切换路由 → 控制台无 `net::ERR_ABORTED`
