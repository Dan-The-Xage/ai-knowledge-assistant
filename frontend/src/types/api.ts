// API Response Types

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: string;
  department?: string;
  job_title?: string;
  is_active: boolean;
  created_at?: string;
}

export interface Project {
  id: number;
  name: string;
  description?: string;
  is_active: boolean;
  is_private: boolean;
  created_by: string;
  created_at: string;
  member_count: number;
  document_count: number;
}

export interface Document {
  id: number;
  filename: string;
  file_size: number;
  mime_type: string;
  processing_status: string;
  project_id: number;
  uploaded_by: string;
  created_at: string;
  word_count?: number;
  page_count?: number;
  title?: string;
  description?: string;
  tags?: string[];
  metadata?: Record<string, any>;
  is_excel?: boolean;
  sheet_names?: string[];
}

export interface Conversation {
  id: number;
  title: string;
  is_active: string;
  project_id?: number;
  user_id: number;
  created_at: string;
  message_count: number;
}

export interface Message {
  id: number;
  conversation_id: number;
  message_type: 'user' | 'assistant';
  content: string;
  citations?: Citation[];
  confidence_score?: number;
  tokens_used?: number;
  processing_time?: number;
  created_at: string;
}

export interface Citation {
  document_id: number;
  chunk_index: number;
  similarity_score: number;
  page_number?: number;
  section_title?: string;
}

export interface ChatResponse {
  conversation: Conversation;
  message: Message;
  sources_used: Source[];
}

export interface Source {
  content: string;
  metadata: {
    document_id: number;
    chunk_index: number;
    page_number?: number;
    section_title?: string;
  };
  similarity_score: number;
}

// API Request Types

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  full_name: string;
  department?: string;
  job_title?: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface ProjectCreateRequest {
  name: string;
  description?: string;
  is_private?: boolean;
}

export interface ConversationCreateRequest {
  title: string;
  project_id?: number;
}

export interface ChatMessageRequest {
  content: string;
  project_id?: number;
}

// API Response Types

export interface ApiResponse<T> {
  data?: T;
  error?: string;
  message?: string;
}

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

// Health Check Types

export interface HealthStatus {
  status: 'healthy' | 'degraded' | 'unhealthy';
  timestamp: string;
  version: string;
  components: {
    database: ComponentStatus;
    vector_db: ComponentStatus;
    llm_service: ComponentStatus;
  };
}

export interface ComponentStatus {
  status: 'healthy' | 'unhealthy' | 'unknown';
  details: string;
}

// File Upload Types

export interface FileUploadResponse {
  document: Document;
  message: string;
}

// Audit Types

export interface AuditLog {
  id: number;
  timestamp: string;
  user_id?: number;
  user_email?: string;
  action: string;
  resource_type: string;
  resource_id?: number;
  description: string;
  success: 'success' | 'failure';
  error_message?: string;
}
