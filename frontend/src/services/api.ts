import axios, { AxiosInstance, AxiosResponse } from 'axios';
import { ApiResponse, PaginatedResponse } from '@/types/api';

// Create axios instance
const api: AxiosInstance = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001/api/v1',
  timeout: 30000, // 30 seconds
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor to handle errors
api.interceptors.response.use(
  (response: AxiosResponse) => {
    return response;
  },
  (error) => {
    if (error.response?.status === 401) {
      // Token expired or invalid
      localStorage.removeItem('access_token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Generic API methods
export const apiService = {
  get: <T>(url: string, params?: any): Promise<AxiosResponse<ApiResponse<T>>> =>
    api.get(url, { params }),

  post: <T>(url: string, data?: any): Promise<AxiosResponse<ApiResponse<T>>> =>
    api.post(url, data),

  put: <T>(url: string, data?: any): Promise<AxiosResponse<ApiResponse<T>>> =>
    api.put(url, data),

  delete: <T>(url: string): Promise<AxiosResponse<ApiResponse<T>>> =>
    api.delete(url),

  patch: <T>(url: string, data?: any): Promise<AxiosResponse<ApiResponse<T>>> =>
    api.patch(url, data),
};

// Auth API
export const authAPI = {
  login: (credentials: { email: string; password: string; account_type: string }) =>
    api.post('/auth/login', credentials),

  register: (userData: any) =>
    api.post('/auth/register', userData),

  refreshToken: () =>
    api.post('/auth/refresh-token'),

  logout: () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
  },
};

// User API
export const userAPI = {
  getProfile: () => api.get('/users/me'),
  updateProfile: (data: any) => api.put('/users/me', data),
};

// Project API
export const projectAPI = {
  create: (data: any) => api.post('/projects', data),
  list: (params?: any) => api.get('/projects', { params }),
  get: (id: number) => api.get(`/projects/${id}`),
  update: (id: number, data: any) => api.put(`/projects/${id}`, data),
  delete: (id: number) => api.delete(`/projects/${id}`),
  getMembers: (id: number) => api.get(`/projects/${id}/members`),
  addMember: (projectId: number, userId: number, role?: string) =>
    api.post(`/projects/${projectId}/members/${userId}`, null, { params: { role } }),
  removeMember: (projectId: number, userId: number) =>
    api.delete(`/projects/${projectId}/members/${userId}`),
};

// Document API
export const documentAPI = {
  upload: (formData: FormData, projectId: number) => {
    const params = new URLSearchParams({ project_id: projectId.toString() });
    return api.post('/documents/upload', formData, {
      params,
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },

  list: (params?: any) => api.get('/documents', { params }),
  get: (id: number) => api.get(`/documents/${id}`),
  download: (id: number) => api.get(`/documents/${id}/download`, { responseType: 'blob' }),
  delete: (id: number) => api.delete(`/documents/${id}`),
  
  // Get documents available for chat (shared + personal)
  getAvailableForChat: () => api.get('/documents/available-for-chat'),
};

// Conversation API
export const conversationAPI = {
  create: (data: any) => api.post('/conversations', data),
  list: (params?: any) => api.get('/conversations', { params }),
  get: (id: number) => api.get(`/conversations/${id}`),
  delete: (id: number) => api.delete(`/conversations/${id}`),
  chat: (conversationId: number, message: any) =>
    api.post(`/conversations/${conversationId}/chat`, message),
  
  // Upload document directly in chat
  uploadDocument: (conversationId: number, formData: FormData) =>
    api.post(`/conversations/${conversationId}/upload-document`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
};

// Admin API
export const adminAPI = {
  getUsers: (params?: any) => api.get('/admin/users', { params }),
  createUser: (data: any) => api.post('/auth/users', data),
  updateUser: (id: number, data: any) => api.put(`/auth/users/${id}`, data),
  deleteUser: (id: number) => api.delete(`/auth/users/${id}`),
  getAuditLogs: (params?: any) => api.get('/admin/audit', { params }),
  getSystemStats: () => api.get('/admin/stats'),
  toggleUserActive: (id: number) => api.patch(`/admin/users/${id}/toggle-active`),
  updateUserRole: (userId: number, roleId: number) =>
    api.patch(`/admin/users/${userId}/role`, null, { params: { role_id: roleId } }),
  getRoles: () => api.get('/admin/roles'),
};

// Health API
export const healthAPI = {
  check: () => api.get('/health'),
  detailed: () => api.get('/health/detailed'),
};

// Utility functions
export const setAuthToken = (token: string) => {
  localStorage.setItem('access_token', token);
};

export const getAuthToken = (): string | null => {
  return localStorage.getItem('access_token');
};

export const isAuthenticated = (): boolean => {
  return !!getAuthToken();
};

// Error handling
export const handleApiError = (error: any): string => {
  const detail = error.response?.data?.detail;
  
  if (detail) {
    // Handle Pydantic validation errors (array of objects with msg field)
    if (Array.isArray(detail)) {
      const messages = detail
        .map((err: any) => err.msg || err.message || JSON.stringify(err))
        .join(', ');
      return messages || 'Validation error';
    }
    // Handle string detail
    if (typeof detail === 'string') {
      return detail;
    }
    // Handle object detail with msg field
    if (typeof detail === 'object' && detail.msg) {
      return detail.msg;
    }
    // Fallback: stringify the detail
    return JSON.stringify(detail);
  }
  
  if (error.response?.data?.message) {
    return error.response.data.message;
  }
  if (error.message) {
    return error.message;
  }
  return 'An unexpected error occurred';
};

export default api;
