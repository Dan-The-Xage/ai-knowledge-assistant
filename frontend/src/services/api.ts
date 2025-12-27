import axios, { AxiosInstance, AxiosResponse } from 'axios';
import { ApiResponse, PaginatedResponse } from '@/types/api';

// Create axios instance for Appwrite functions
const api: AxiosInstance = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'https://cloud.appwrite.io/v1',
  timeout: 30000, // 30 seconds
});

// Appwrite project configuration
const APPWRITE_PROJECT_ID = process.env.NEXT_PUBLIC_APPWRITE_PROJECT_ID || '';

// Helper function to call Appwrite functions
const callAppwriteFunction = async (functionId: string, method: string = 'POST', data?: any, headers?: any) => {
  const url = `/functions/${functionId}/executions`;
  const requestData = {
    data: JSON.stringify(data || {}),
    method: method,
    headers: {
      'Content-Type': 'application/json',
      ...headers,
    },
    path: `/${functionId}`,
  };

  return api.post(url, requestData, {
    headers: {
      'X-Appwrite-Project': APPWRITE_PROJECT_ID,
    },
  });
};

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
  login: async (credentials: { email: string; password: string; account_type: string }) => {
    const response = await callAppwriteFunction('auth', 'POST', credentials);
    return response.data.response;
  },

  register: async (userData: any) => {
    const response = await callAppwriteFunction('users', 'POST', userData);
    return response.data.response;
  },

  refreshToken: async () => {
    const response = await callAppwriteFunction('auth', 'POST', {}, { path: '/refresh-token' });
    return response.data.response;
  },

  logout: () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
  },

  getRoles: async () => {
    const response = await callAppwriteFunction('auth', 'GET', {}, { path: '/roles' });
    return response.data.response;
  },
};

// User API
export const userAPI = {
  getProfile: async () => {
    const response = await callAppwriteFunction('auth', 'GET', {}, { path: '/me' });
    return response.data.response;
  },

  updateProfile: async (data: any) => {
    const response = await callAppwriteFunction('auth', 'PUT', data, { path: '/me' });
    return response.data.response;
  },
};

// Project API - Simplified for Appwrite (projects not implemented yet)
export const projectAPI = {
  create: async (data: any) => {
    // Placeholder - projects not implemented in Appwrite version yet
    throw new Error('Projects not implemented in Appwrite version yet');
  },

  list: async (params?: any) => {
    // Placeholder - projects not implemented in Appwrite version yet
    return { data: [] };
  },

  get: async (id: number) => {
    // Placeholder - projects not implemented in Appwrite version yet
    throw new Error('Projects not implemented in Appwrite version yet');
  },

  update: async (id: number, data: any) => {
    // Placeholder - projects not implemented in Appwrite version yet
    throw new Error('Projects not implemented in Appwrite version yet');
  },

  delete: async (id: number) => {
    // Placeholder - projects not implemented in Appwrite version yet
    throw new Error('Projects not implemented in Appwrite version yet');
  },

  getMembers: async (id: number) => {
    // Placeholder - projects not implemented in Appwrite version yet
    return { data: [] };
  },

  addMember: async (projectId: number, userId: number, role?: string) => {
    // Placeholder - projects not implemented in Appwrite version yet
    throw new Error('Projects not implemented in Appwrite version yet');
  },

  removeMember: async (projectId: number, userId: number) => {
    // Placeholder - projects not implemented in Appwrite version yet
    throw new Error('Projects not implemented in Appwrite version yet');
  },
};

// Document API
export const documentAPI = {
  upload: async (formData: FormData, projectId: number) => {
    // Convert FormData to the format expected by Appwrite functions
    const file = formData.get('file') as File;
    const reader = new FileReader();

    return new Promise((resolve, reject) => {
      reader.onload = async () => {
        try {
          const base64Data = reader.result?.toString().split(',')[1]; // Remove data URL prefix
          const uploadData = {
            filename: file.name,
            mime_type: file.type,
            file_data: base64Data,
            project_id: projectId
          };

          const response = await callAppwriteFunction('documents', 'POST', uploadData, { path: '/upload' });
          resolve(response.data.response);
        } catch (error) {
          reject(error);
        }
      };

      reader.onerror = () => reject(new Error('Failed to read file'));
      reader.readAsDataURL(file);
    });
  },

  list: async (params?: any) => {
    const response = await callAppwriteFunction('documents', 'GET', params || {});
    return response.data.response;
  },

  get: async (id: number) => {
    // Not implemented in Appwrite version yet
    throw new Error('Get document not implemented in Appwrite version yet');
  },

  download: async (id: number) => {
    // Not implemented in Appwrite version yet
    throw new Error('Download not implemented in Appwrite version yet');
  },

  delete: async (id: number) => {
    // Not implemented in Appwrite version yet
    throw new Error('Delete document not implemented in Appwrite version yet');
  },

  // Get documents available for chat (shared + personal)
  getAvailableForChat: async () => {
    const response = await callAppwriteFunction('documents', 'GET', {});
    return response.data.response;
  },
};

// Conversation API
export const conversationAPI = {
  create: async (data: any) => {
    const response = await callAppwriteFunction('conversations', 'POST', data);
    return response.data.response;
  },

  list: async (params?: any) => {
    const response = await callAppwriteFunction('conversations', 'GET', params || {});
    return response.data.response;
  },

  get: async (id: number) => {
    // Not implemented in Appwrite version yet
    throw new Error('Get conversation not implemented in Appwrite version yet');
  },

  delete: async (id: number) => {
    // Not implemented in Appwrite version yet
    throw new Error('Delete conversation not implemented in Appwrite version yet');
  },

  chat: async (conversationId: number, message: any) => {
    const response = await callAppwriteFunction('conversations', 'POST', message, { path: `/${conversationId}/chat` });
    return response.data.response;
  },

  // Upload document directly in chat
  uploadDocument: async (conversationId: number, formData: FormData) => {
    // Not implemented in Appwrite version yet
    throw new Error('Upload document in chat not implemented in Appwrite version yet');
  },
};

// Admin API
export const adminAPI = {
  getUsers: async (params?: any) => {
    const response = await callAppwriteFunction('admin', 'GET', params || {}, { path: '/users' });
    return response.data.response;
  },

  createUser: async (data: any) => {
    const response = await callAppwriteFunction('users', 'POST', data);
    return response.data.response;
  },

  updateUser: async (id: number, data: any) => {
    // Not implemented in Appwrite version yet
    throw new Error('Update user not implemented in Appwrite version yet');
  },

  deleteUser: async (id: number) => {
    // Not implemented in Appwrite version yet
    throw new Error('Delete user not implemented in Appwrite version yet');
  },

  getAuditLogs: async (params?: any) => {
    // Not implemented in Appwrite version yet
    return { data: [] };
  },

  getSystemStats: async () => {
    const response = await callAppwriteFunction('admin', 'GET', {}, { path: '/stats' });
    return response.data.response;
  },

  toggleUserActive: async (id: number) => {
    const response = await callAppwriteFunction('admin', 'PATCH', { user_id: id }, { path: '/toggle-active' });
    return response.data.response;
  },

  updateUserRole: async (userId: number, roleId: number) => {
    // Not implemented in Appwrite version yet
    throw new Error('Update user role not implemented in Appwrite version yet');
  },

  getRoles: async () => {
    const response = await callAppwriteFunction('admin', 'GET', {}, { path: '/roles' });
    return response.data.response;
  },
};

// Health API
export const healthAPI = {
  check: async () => {
    const response = await callAppwriteFunction('health', 'GET', {});
    return response.data.response;
  },

  detailed: async () => {
    // Detailed health not implemented in Appwrite version yet
    const response = await callAppwriteFunction('health', 'GET', {});
    return response.data.response;
  },
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
