import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
  // dev 代理注入 X-API-Key（与生产 nginx proxy_set_header 同款行为）。
  // key 从仓库根 .env 读取，不进前端代码与构建产物。
  const env = loadEnv(mode, process.cwd() + '/..', '');

  return {
    plugins: [react()],
    server: {
      proxy: {
        '/api': {
          target: 'http://localhost:8000',
          changeOrigin: true,
          headers: env.API_KEY ? { 'X-API-Key': env.API_KEY } : undefined,
        },
      },
    },
  };
});
