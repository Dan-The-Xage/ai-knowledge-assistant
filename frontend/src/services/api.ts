// Re-export the new services
export { supabaseService } from './supabaseService';
export { aiService } from './aiService';
export type { User, Document, Conversation, Message } from './supabaseService';

// Legacy API compatibility layer
// This provides backward compatibility while we migrate to the new services

// Import axios for any remaining legacy API calls (if needed)
import axios from 'axios';

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

// Auth API - Now using Supabase
export const authAPI = {
  login: async (credentials: { email: string; password: string; account_type: string }) => {
    try {
      const result = await supabaseService.signIn(credentials.email, credentials.password);
      return {
        data: {
          access_token: result.session?.access_token,
          user: {
            id: result.user.id,
            email: result.user.email,
            full_name: result.profile?.full_name,
            role: result.profile?.role,
            department: result.profile?.department,
            job_title: result.profile?.job_title,
            is_active: result.profile?.is_active,
          }
        }
      };
    } catch (error) {
      throw error;
    }
  },

  register: async (userData: any) => {
    try {
      const result = await supabaseService.signUp(
        userData.email,
        userData.password,
        userData.full_name,
        userData.role || 'user'
      );
      return {
        data: {
          user: {
            id: result.user?.id,
            email: result.user?.email,
            full_name: userData.full_name,
            role: userData.role || 'user',
          }
        }
      };
    } catch (error) {
      throw error;
    }
  },

  refreshToken: async () => {
    // Supabase handles token refresh automatically
    const result = await supabaseService.getCurrentUser();
    return {
      data: {
        user: result?.profile
      }
    };
  },

  logout: async () => {
    await supabaseService.signOut();
  },

  getRoles: async () => {
    // Return static roles for now
    return {
      data: [
        { id: "super_admin", name: "super_admin", description: "Super Administrator" },
        { id: "admin", name: "admin", description: "Administrator" },
        { id: "user", name: "user", description: "Regular User" },
        { id: "guest", name: "guest", description: "Guest User" }
      ]
    };
  },
};

// User API - Now using Supabase
export const userAPI = {
  getProfile: async () => {
    const result = await supabaseService.getCurrentUser();
    return {
      data: result?.profile
    };
  },

  updateProfile: async (data: any) => {
    const user = await supabaseService.getCurrentUser();
    if (!user?.user) throw new Error('Not authenticated');

    const result = await supabaseService.updateUserProfile(user.user.id, data);
    return {
      data: result
    };
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

// Document API - Now using Supabase + AI Service
export const documentAPI = {
  upload: async (formData: FormData, projectId: number) => {
    const file = formData.get('file') as File;
    const user = await supabaseService.getCurrentUser();

    if (!user?.user || !user?.profile) {
      throw new Error('Not authenticated');
    }

    // Upload file to Supabase Storage
    const document = await supabaseService.uploadFile(
      file,
      user.user.id,
      user.profile.email || user.user.email || ''
    );

    // Extract text from file
    const extractedText = await extractTextFromFile(file);

    // Generate embedding using AI service
    const embeddingResult = await aiService.generateEmbeddings(extractedText);

    if (embeddingResult.success) {
      // Update document with AI-processed data
      await supabaseService.updateDocumentWithAI(
        document.id,
        extractedText,
        embeddingResult.data.embedding
      );
    }

    return {
      data: {
        document: {
          ...document,
          extracted_text: extractedText,
          processing_status: 'completed'
        },
        message: 'Document uploaded and processed successfully'
      }
    };
  },

  list: async (params?: any) => {
    const user = await supabaseService.getCurrentUser();
    if (!user?.user) throw new Error('Not authenticated');

    const documents = await supabaseService.getUserDocuments(user.user.id);
    return {
      data: documents
    };
  },

  get: async (id: number) => {
    throw new Error('Get document not implemented yet');
  },

  download: async (id: number) => {
    throw new Error('Download not implemented yet');
  },

  delete: async (id: number) => {
    throw new Error('Delete document not implemented yet');
  },

  // Get documents available for chat (shared + personal)
  getAvailableForChat: async () => {
    const user = await supabaseService.getCurrentUser();
    if (!user?.user) throw new Error('Not authenticated');

    const documents = await supabaseService.getUserDocuments(user.user.id);
    return {
      data: documents
    };
  },
};

// Helper function to extract text from files
async function extractTextFromFile(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();

    reader.onload = async (e) => {
      try {
        const result = e.target?.result;
        if (typeof result === 'string') {
          // Handle different file types
          if (file.type === 'text/plain') {
            resolve(result);
          } else if (file.type === 'application/pdf') {
            // For PDF, we'd need a PDF parsing library in the browser
            // For now, return a placeholder
            resolve("PDF content extraction requires server-side processing. This is a placeholder.");
          } else if (file.type.includes('word') || file.name.endsWith('.docx')) {
            // For Word documents, similar limitation
            resolve("Word document extraction requires server-side processing. This is a placeholder.");
          } else {
            resolve("Unsupported file type for text extraction.");
          }
        } else {
          resolve("Could not read file content.");
        }
      } catch (error) {
        reject(error);
      }
    };

    reader.onerror = () => reject(new Error('Failed to read file'));
    reader.readAsText(file);
  });
}

// Conversation API - Now using Supabase + AI Service
export const conversationAPI = {
  create: async (data: any) => {
    const user = await supabaseService.getCurrentUser();
    if (!user?.user) throw new Error('Not authenticated');

    const conversation = await supabaseService.createConversation(
      data.title || 'New Conversation',
      user.user.id
    );

    return {
      data: conversation
    };
  },

  list: async (params?: any) => {
    const user = await supabaseService.getCurrentUser();
    if (!user?.user) throw new Error('Not authenticated');

    const conversations = await supabaseService.getUserConversations(user.user.id);

    // Add message counts
    for (const conv of conversations) {
      try {
        const messages = await supabaseService.getConversationMessages(conv.id);
        conv.message_count = messages.length;
      } catch (error) {
        conv.message_count = 0;
      }
    }

    return {
      data: conversations
    };
  },

  get: async (id: number) => {
    throw new Error('Get conversation not implemented yet');
  },

  delete: async (id: number) => {
    throw new Error('Delete conversation not implemented yet');
  },

  chat: async (conversationId: string, message: any) => {
    const userMessage = message.content || message.message || '';

    // Save user message
    await supabaseService.addMessage(conversationId, 'user', userMessage);

    // Get conversation context (recent messages and documents)
    let context = '';
    try {
      const messages = await supabaseService.getConversationMessages(conversationId);
      // Get last 5 messages for context
      const recentMessages = messages.slice(-5);
      context = recentMessages.map(m => `${m.message_type}: ${m.content}`).join('\n');
    } catch (error) {
      console.warn('Could not load conversation context:', error);
    }

    // Get relevant documents for context
    try {
      const user = await supabaseService.getCurrentUser();
      if (user?.user) {
        const documents = await supabaseService.getUserDocuments(user.user.id);
        if (documents.length > 0) {
          // Add document context (first document for now)
          const doc = documents[0];
          if (doc.extracted_text) {
            context += `\n\nDocument Context: ${doc.extracted_text.slice(0, 500)}...`;
          }
        }
      }
    } catch (error) {
      console.warn('Could not load document context:', error);
    }

    // Generate AI response
    const aiResponse = await aiService.generateResponse(userMessage, context);

    let responseContent = '';
    if (aiResponse.success) {
      responseContent = aiResponse.data?.response || 'I apologize, but I could not generate a response.';
    } else {
      responseContent = `I apologize, but there was an error: ${aiResponse.error}`;
    }

    // Save AI response
    const aiMessage = await supabaseService.addMessage(conversationId, 'assistant', responseContent);

    return {
      data: {
        conversation: { id: conversationId },
        message: {
          id: aiMessage.id,
          conversation_id: conversationId,
          message_type: 'assistant',
          content: responseContent,
          created_at: aiMessage.created_at
        },
        sources_used: context ? 1 : 0
      }
    };
  },

  // Upload document directly in chat
  uploadDocument: async (conversationId: number, formData: FormData) => {
    throw new Error('Upload document in chat not implemented yet');
  },
};

// Admin API - Now using Supabase
export const adminAPI = {
  getUsers: async (params?: any) => {
    const users = await supabaseService.getAllUsers();
    return {
      data: users
    };
  },

  createUser: async (data: any) => {
    // Admin creating user - would need additional implementation
    throw new Error('Admin user creation not implemented yet');
  },

  updateUser: async (id: number, data: any) => {
    throw new Error('Update user not implemented yet');
  },

  deleteUser: async (id: number) => {
    throw new Error('Delete user not implemented yet');
  },

  getAuditLogs: async (params?: any) => {
    // Audit logs not implemented in this version
    return { data: [] };
  },

  getSystemStats: async () => {
    const stats = await supabaseService.getSystemStats();
    return {
      data: stats
    };
  },

  toggleUserActive: async (id: number) => {
    const result = await supabaseService.toggleUserActive(id.toString());
    return {
      data: result
    };
  },

  updateUserRole: async (userId: number, roleId: number) => {
    throw new Error('Update user role not implemented yet');
  },

  getRoles: async () => {
    return {
      data: [
        { id: 1, name: 'super_admin', description: 'Super Administrator', permissions: ['all'], user_count: 0 },
        { id: 2, name: 'admin', description: 'Administrator', permissions: ['manage_users', 'view_reports'], user_count: 0 },
        { id: 3, name: 'user', description: 'Regular User', permissions: ['upload_documents', 'chat'], user_count: 0 },
        { id: 4, name: 'guest', description: 'Guest User', permissions: ['read_only'], user_count: 0 }
      ]
    };
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
