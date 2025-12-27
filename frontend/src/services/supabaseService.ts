/**
 * Supabase Service for Database Operations
 * Handles all database interactions from the frontend
 */

import { createClient, SupabaseClient } from '@supabase/supabase-js';

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: 'super_admin' | 'admin' | 'user' | 'guest';
  department?: string;
  job_title?: string;
  is_active: boolean;
  created_at: string;
}

export interface Document {
  id: string;
  filename: string;
  file_path: string;
  mime_type: string;
  file_size: number;
  uploaded_by: string;
  uploaded_by_email: string;
  project_id?: string;
  processing_status: 'pending' | 'processing' | 'completed' | 'failed';
  extracted_text?: string;
  embedding?: number[];
  created_at: string;
}

export interface Conversation {
  id: string;
  title: string;
  user_id: string;
  project_id?: string;
  is_active: boolean;
  created_at: string;
  message_count?: number;
}

export interface Message {
  id: string;
  conversation_id: string;
  message_type: 'user' | 'assistant';
  content: string;
  created_at: string;
}

class SupabaseService {
  private supabase: SupabaseClient;

  constructor() {
    const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
    const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

    if (!supabaseUrl || !supabaseAnonKey) {
      throw new Error('Supabase configuration missing. Please check environment variables.');
    }

    this.supabase = createClient(supabaseUrl, supabaseAnonKey);
  }

  // ===========================================
  // AUTHENTICATION METHODS
  // ===========================================

  /**
   * Sign up a new user
   */
  async signUp(email: string, password: string, fullName: string, role: string = 'user') {
    try {
      const { data, error } = await this.supabase.auth.signUp({
        email,
        password,
        options: {
          data: {
            full_name: fullName,
            role: role,
          }
        }
      });

      if (error) throw error;

      // Create user profile in database
      if (data.user) {
        await this.supabase
          .from('users')
          .insert({
            id: data.user.id,
            email: data.user.email,
            full_name: fullName,
            role: role,
            is_active: true,
          });
      }

      return { user: data.user, session: data.session };
    } catch (error) {
      console.error('Signup error:', error);
      throw error;
    }
  }

  /**
   * Sign in user
   */
  async signIn(email: string, password: string) {
    try {
      const { data, error } = await this.supabase.auth.signInWithPassword({
        email,
        password,
      });

      if (error) throw error;

      // Get user profile
      const profile = await this.getUserProfile(data.user.id);

      return {
        user: data.user,
        profile,
        session: data.session
      };
    } catch (error) {
      console.error('Signin error:', error);
      throw error;
    }
  }

  /**
   * Sign out user
   */
  async signOut() {
    try {
      const { error } = await this.supabase.auth.signOut();
      if (error) throw error;
    } catch (error) {
      console.error('Signout error:', error);
      throw error;
    }
  }

  /**
   * Get current user
   */
  async getCurrentUser() {
    try {
      const { data: { user }, error } = await this.supabase.auth.getUser();
      if (error) throw error;

      if (user) {
        const profile = await this.getUserProfile(user.id);
        return { user, profile };
      }

      return null;
    } catch (error) {
      console.error('Get current user error:', error);
      return null;
    }
  }

  /**
   * Get user profile from database
   */
  async getUserProfile(userId: string): Promise<User | null> {
    try {
      const { data, error } = await this.supabase
        .from('users')
        .select('*')
        .eq('id', userId)
        .single();

      if (error) throw error;
      return data;
    } catch (error) {
      console.error('Get user profile error:', error);
      return null;
    }
  }

  // ===========================================
  // USER MANAGEMENT METHODS
  // ===========================================

  /**
   * Get all users (admin only)
   */
  async getAllUsers(): Promise<User[]> {
    try {
      const { data, error } = await this.supabase
        .from('users')
        .select('*')
        .order('created_at', { ascending: false });

      if (error) throw error;
      return data || [];
    } catch (error) {
      console.error('Get all users error:', error);
      throw error;
    }
  }

  /**
   * Update user profile
   */
  async updateUserProfile(userId: string, updates: Partial<User>) {
    try {
      const { data, error } = await this.supabase
        .from('users')
        .update({
          full_name: updates.full_name,
          department: updates.department,
          job_title: updates.job_title,
          is_active: updates.is_active,
        })
        .eq('id', userId)
        .select()
        .single();

      if (error) throw error;
      return data;
    } catch (error) {
      console.error('Update user profile error:', error);
      throw error;
    }
  }

  /**
   * Toggle user active status
   */
  async toggleUserActive(userId: string) {
    try {
      // First get current status
      const { data: user, error: getError } = await this.supabase
        .from('users')
        .select('is_active')
        .eq('id', userId)
        .single();

      if (getError) throw getError;

      // Toggle status
      const newStatus = !user.is_active;

      const { data, error } = await this.supabase
        .from('users')
        .update({ is_active: newStatus })
        .eq('id', userId)
        .select()
        .single();

      if (error) throw error;
      return data;
    } catch (error) {
      console.error('Toggle user active error:', error);
      throw error;
    }
  }

  // ===========================================
  // DOCUMENT MANAGEMENT METHODS
  // ===========================================

  /**
   * Upload file to Supabase Storage
   */
  async uploadFile(file: File, userId: string, userEmail: string): Promise<Document> {
    try {
      // Generate unique filename
      const fileExt = file.name.split('.').pop();
      const fileName = `${Date.now()}-${Math.random().toString(36).substring(2)}.${fileExt}`;

      // Upload to storage
      const { data: uploadData, error: uploadError } = await this.supabase.storage
        .from('documents')
        .upload(fileName, file);

      if (uploadError) throw uploadError;

      // Get public URL
      const { data: urlData } = this.supabase.storage
        .from('documents')
        .getPublicUrl(fileName);

      // Create document record
      const { data, error } = await this.supabase
        .from('documents')
        .insert({
          filename: file.name,
          file_path: urlData.publicUrl,
          mime_type: file.type,
          file_size: file.size,
          uploaded_by: userId,
          uploaded_by_email: userEmail,
          processing_status: 'completed', // We'll process text client-side
          created_at: new Date().toISOString(),
        })
        .select()
        .single();

      if (error) throw error;
      return data;
    } catch (error) {
      console.error('Upload file error:', error);
      throw error;
    }
  }

  /**
   * Get user's documents
   */
  async getUserDocuments(userId: string): Promise<Document[]> {
    try {
      const { data, error } = await this.supabase
        .from('documents')
        .select('*')
        .eq('uploaded_by', userId)
        .order('created_at', { ascending: false });

      if (error) throw error;
      return data || [];
    } catch (error) {
      console.error('Get user documents error:', error);
      throw error;
    }
  }

  /**
   * Update document with extracted text and embedding
   */
  async updateDocumentWithAI(
    documentId: string,
    extractedText: string,
    embedding: number[]
  ) {
    try {
      const { data, error } = await this.supabase
        .from('documents')
        .update({
          extracted_text: extractedText,
          embedding: embedding,
          processing_status: 'completed',
        })
        .eq('id', documentId)
        .select()
        .single();

      if (error) throw error;
      return data;
    } catch (error) {
      console.error('Update document with AI error:', error);
      throw error;
    }
  }

  // ===========================================
  // CONVERSATION MANAGEMENT METHODS
  // ===========================================

  /**
   * Create new conversation
   */
  async createConversation(title: string, userId: string): Promise<Conversation> {
    try {
      const { data, error } = await this.supabase
        .from('conversations')
        .insert({
          title,
          user_id: userId,
          is_active: true,
          created_at: new Date().toISOString(),
        })
        .select()
        .single();

      if (error) throw error;
      return data;
    } catch (error) {
      console.error('Create conversation error:', error);
      throw error;
    }
  }

  /**
   * Get user's conversations
   */
  async getUserConversations(userId: string): Promise<Conversation[]> {
    try {
      const { data, error } = await this.supabase
        .from('conversations')
        .select('*')
        .eq('user_id', userId)
        .order('created_at', { ascending: false });

      if (error) throw error;
      return data || [];
    } catch (error) {
      console.error('Get user conversations error:', error);
      throw error;
    }
  }

  /**
   * Add message to conversation
   */
  async addMessage(
    conversationId: string,
    messageType: 'user' | 'assistant',
    content: string
  ): Promise<Message> {
    try {
      const { data, error } = await this.supabase
        .from('messages')
        .insert({
          conversation_id: conversationId,
          message_type: messageType,
          content,
          created_at: new Date().toISOString(),
        })
        .select()
        .single();

      if (error) throw error;
      return data;
    } catch (error) {
      console.error('Add message error:', error);
      throw error;
    }
  }

  /**
   * Get conversation messages
   */
  async getConversationMessages(conversationId: string): Promise<Message[]> {
    try {
      const { data, error } = await this.supabase
        .from('messages')
        .select('*')
        .eq('conversation_id', conversationId)
        .order('created_at', { ascending: true });

      if (error) throw error;
      return data || [];
    } catch (error) {
      console.error('Get conversation messages error:', error);
      throw error;
    }
  }

  // ===========================================
  // ANALYTICS METHODS
  // ===========================================

  /**
   * Get system statistics
   */
  async getSystemStats() {
    try {
      // Get counts from all tables
      const [usersResult, documentsResult, conversationsResult] = await Promise.all([
        this.supabase.from('users').select('id', { count: 'exact', head: true }),
        this.supabase.from('documents').select('id', { count: 'exact', head: true }),
        this.supabase.from('conversations').select('id', { count: 'exact', head: true }),
      ]);

      const activeUsers = await this.supabase
        .from('users')
        .select('id', { count: 'exact', head: true })
        .eq('is_active', true);

      return {
        total_users: usersResult.count || 0,
        active_users: activeUsers.count || 0,
        total_documents: documentsResult.count || 0,
        total_conversations: conversationsResult.count || 0,
        ai_service_status: {
          status: process.env.NEXT_PUBLIC_HF_API_TOKEN ? 'operational' : 'not_configured',
          model: 'Mistral-7B-Instruct-v0.2'
        }
      };
    } catch (error) {
      console.error('Get system stats error:', error);
      throw error;
    }
  }
}

// Export singleton instance
export const supabaseService = new SupabaseService();
export default supabaseService;
