import axios from 'axios';

// @ts-ignore
const API_BASE_URL = import.meta.env.VITE_API_STR || '/api';

// Axios实例
const apiClient = axios.create({
    baseURL: API_BASE_URL,
});

// 请求拦截器 - 自动添加认证token
apiClient.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem('token');
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
    },
    (error) => Promise.reject(error)
);

// 响应拦截器 - 统一错误处理
apiClient.interceptors.response.use(
    (response) => response,
    (error) => {
        // 增强错误信息提取
        if (error.response && error.response.data) {
            const data = error.response.data;
            // 检查常见的错误信息字段
            const detail = data.detail || (data.error && data.error.message) || data.message || JSON.stringify(data);
            // 将提取或格式化的信息统一放到 detail 字段，方便前端统一处理
            error.response.data.detail = detail;
        }

        if (error.response?.status === 401) {
            // Token过期或无效，跳转登录
            localStorage.removeItem('token');
            window.location.href = '/login';
        }
        return Promise.reject(error);
    }
);

export { API_BASE_URL };
export default apiClient;
