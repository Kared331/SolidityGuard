import axios from 'axios';
import { useToastStore } from '../stores/useToastStore';

// API key is NOT included in frontend — it is injected by nginx proxy at runtime
// This prevents the API key from being exposed in the JavaScript bundle

const client = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 30000, // P1-3: 全局超时兜底（原无 timeout，网络挂起时请求永久 pending）
});

// P1-3: 全局错误拦截器——状态码 → 中文文案映射，经 toast 提示。
// 约束：拦截器只做兜底，不覆盖业务自定义处理（UploadPage 的 detail 提取保持优先）。
client.interceptors.response.use(
  (response) => response,
  (error) => {
    let message = '请求失败，请稍后重试';

    if (error.code === 'ECONNABORTED' || error.code === 'ETIMEDOUT') {
      message = '请求超时，请检查网络后重试';
    } else if (error.response) {
      const status = error.response.status;
      if (status === 401) {
        message = '认证失败，请检查 API Key 配置';
      } else if (status === 403) {
        message = '无访问权限';
      } else if (status === 408) {
        message = '请求超时，请稍后重试';
      } else if (status === 413) {
        message = '文件大小超出限制';
      } else if (status >= 500) {
        message = '服务端错误，请稍后重试';
      } else if (status === 409) {
        // 409 幂等拦截——业务层已处理，不在此重复弹 toast
        return Promise.reject(error);
      }
    } else if (!error.response) {
      message = '网络连接失败，请确认服务是否运行';
    }

    // 只在未被业务层处理时弹 toast（业务层 catch 后不再走 reject）
    useToastStore.getState().addToast({
      type: 'error',
      message,
      duration: 5000,
    });

    return Promise.reject(error);
  }
);

export default client;
