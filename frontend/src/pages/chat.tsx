'use client';

import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import {
  PaperAirplaneIcon,
  PlusIcon,
  FolderIcon,
  DocumentIcon,
  ChatBubbleLeftRightIcon,
  PaperClipIcon,
  XMarkIcon,
  CheckCircleIcon,
} from '@heroicons/react/24/outline';
import { User, Conversation, Message, Project } from '@/types/api';
import { conversationAPI, projectAPI, documentAPI } from '@/services/api';
import { handleApiError } from '@/services/api';
import { formatDate, formatConfidenceScore } from '@/utils/format';
import Layout from '@/components/Layout';
import toast, { Toaster } from 'react-hot-toast';

interface AvailableDocument {
  id: number;
  filename: string;
  title: string;
  uploaded_by: string;
  is_shared: boolean;
  page_count?: number;
  word_count?: number;
}

interface ChatPageProps {
  user: User | null;
  onUserChange: (user: User | null) => void;
}

interface ChatMessage {
  id: number;
  type: 'user' | 'assistant';
  content: string;
  citations?: any[];
  confidence_score?: number;
  timestamp: string;
}

export default function ChatPage({ user, onUserChange }: ChatPageProps) {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [currentConversation, setCurrentConversation] = useState<Conversation | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [newMessage, setNewMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProject, setSelectedProject] = useState<number | null>(null);
  
  // Document selection and upload
  const [availableDocuments, setAvailableDocuments] = useState<{
    shared_documents: AvailableDocument[];
    my_documents: AvailableDocument[];
  }>({ shared_documents: [], my_documents: [] });
  const [selectedDocumentIds, setSelectedDocumentIds] = useState<number[]>([]);
  const [showDocumentSelector, setShowDocumentSelector] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const router = useRouter();

  useEffect(() => {
    if (!user) {
      router.push('/login');
      return;
    }
    loadConversations();
    loadProjects();
    loadAvailableDocuments();
  }, [user, router]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const loadConversations = async () => {
    try {
      const response = await conversationAPI.list();
      // Handle both array response and nested data response
      const data = response.data;
      const convList = Array.isArray(data) ? data : (data?.data || data || []);
      setConversations(convList);
    } catch (error) {
      console.error('Failed to load conversations:', error);
      toast.error('Failed to load conversations');
    }
  };

  const loadProjects = async () => {
    try {
      const response = await projectAPI.list();
      // Handle both array response and nested data response
      const data = response.data;
      const projList = Array.isArray(data) ? data : (data?.data || data || []);
      setProjects(projList);
    } catch (error) {
      console.error('Failed to load projects:', error);
      toast.error('Failed to load projects');
    }
  };

  const loadAvailableDocuments = async () => {
    try {
      const response = await documentAPI.getAvailableForChat();
      setAvailableDocuments({
        shared_documents: response.data.shared_documents || [],
        my_documents: response.data.my_documents || [],
      });
    } catch (error) {
      console.error('Failed to load available documents:', error);
    }
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file || !currentConversation) {
      toast.error('Please select a conversation first');
      return;
    }

    setIsUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await conversationAPI.uploadDocument(currentConversation.id, formData);
      const result = response.data;

      if (result.status === 'completed' || result.status === 'existing') {
        toast.success(`Document "${result.filename}" ready for querying`);
        
        // Add the uploaded document to selected documents
        setSelectedDocumentIds(prev => 
          prev.includes(result.document_id) ? prev : [...prev, result.document_id]
        );
        
        // Refresh available documents
        loadAvailableDocuments();
      } else {
        toast.error('Document processing failed');
      }
    } catch (error: any) {
      toast.error(handleApiError(error));
    } finally {
      setIsUploading(false);
      // Reset file input
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const toggleDocumentSelection = (docId: number) => {
    setSelectedDocumentIds(prev =>
      prev.includes(docId)
        ? prev.filter(id => id !== docId)
        : [...prev, docId]
    );
  };

  const clearSelectedDocuments = () => {
    setSelectedDocumentIds([]);
  };

  const createNewConversation = async () => {
    try {
      const response = await conversationAPI.create({
        title: 'New Chat',
        project_id: selectedProject,
      });
      const newConv = response.data?.data || response.data;
      setConversations([newConv, ...conversations]);
      setCurrentConversation(newConv);
      setMessages([]);
      setSelectedProject(null);
    } catch (error) {
      console.error('Failed to create conversation:', error);
      toast.error('Failed to create conversation');
    }
  };

  const selectConversation = async (conversation: Conversation) => {
    setCurrentConversation(conversation);
    try {
      const response = await conversationAPI.get(conversation.id);
      const convData = response.data;
      // Map API messages to ChatMessage format
      const mappedMessages: ChatMessage[] = (convData.messages || []).map((msg: any) => ({
        id: msg.id,
        type: msg.message_type === 'user' ? 'user' : 'assistant',
        content: msg.content,
        citations: msg.citations,
        confidence_score: msg.confidence_score,
        timestamp: msg.created_at || new Date().toISOString(),
      }));
      setMessages(mappedMessages);
    } catch (error) {
      toast.error('Failed to load conversation');
    }
  };

  const sendMessage = async () => {
    if (!newMessage.trim() || !currentConversation) return;

    const messageContent = newMessage.trim();
    setNewMessage('');
    setIsLoading(true);

    // Add user message to UI
    const userMessage: ChatMessage = {
      id: Date.now(),
      type: 'user',
      content: messageContent,
      timestamp: new Date().toISOString(),
    };
    setMessages(prev => [...prev, userMessage]);

    try {
      const response = await conversationAPI.chat(currentConversation.id, {
        content: messageContent,
        project_id: selectedProject,
        document_ids: selectedDocumentIds.length > 0 ? selectedDocumentIds : undefined,
      });

      const chatResponse = response.data;

      // Update conversation
      setCurrentConversation(chatResponse.conversation);

      // Add assistant message
      const assistantMessage: ChatMessage = {
        id: chatResponse.message.id,
        type: 'assistant',
        content: chatResponse.message.content,
        citations: chatResponse.message.citations,
        confidence_score: chatResponse.message.confidence_score,
        timestamp: chatResponse.message.created_at,
      };
      setMessages(prev => [...prev, assistantMessage]);

      // Update conversations list
      setConversations(prev =>
        prev.map(conv =>
          conv.id === chatResponse.conversation.id ? chatResponse.conversation : conv
        )
      );

    } catch (error: any) {
      toast.error(handleApiError(error));

      // Remove the user message if sending failed
      setMessages(prev => prev.slice(0, -1));
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  if (!user) {
    return null;
  }

  return (
    <Layout user={user} onUserChange={onUserChange}>
      <Toaster position="top-right" />
      <div className="flex h-[calc(100vh-8rem)] bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
        {/* Conversations Sidebar */}
        <div className="w-80 bg-gray-50 border-r border-gray-200 flex flex-col hidden md:flex">
          <div className="p-4 border-b border-gray-200">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-900">Conversations</h2>
              <button
                onClick={createNewConversation}
                className="p-2 text-gray-400 hover:text-gray-600 rounded-full hover:bg-gray-100"
                title="New conversation"
              >
                <PlusIcon className="h-5 w-5" />
              </button>
            </div>

            {/* Project Selector */}
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Search in Project (Optional)
              </label>
              <select
                value={selectedProject || ''}
                onChange={(e) => setSelectedProject(e.target.value ? parseInt(e.target.value) : null)}
                className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
              >
                <option value="">All Projects</option>
                {projects.map((project) => (
                  <option key={project.id} value={project.id}>
                    {project.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Document Selector */}
            <div className="mb-4">
              <button
                onClick={() => setShowDocumentSelector(!showDocumentSelector)}
                className="flex items-center justify-between w-full px-3 py-2 text-sm text-left border border-gray-300 rounded-md hover:bg-gray-50"
              >
                <span className="text-gray-700">
                  Select Documents ({selectedDocumentIds.length} selected)
                </span>
                <DocumentIcon className="h-4 w-4 text-gray-400" />
              </button>
              
              {showDocumentSelector && (
                <div className="mt-2 max-h-60 overflow-y-auto border border-gray-200 rounded-md bg-white">
                  {/* Shared Documents (from Super Admin) */}
                  {availableDocuments.shared_documents.length > 0 && (
                    <div className="p-2">
                      <p className="text-xs font-semibold text-green-600 mb-1 flex items-center">
                        <CheckCircleIcon className="h-3 w-3 mr-1" />
                        Shared Documents
                      </p>
                      {availableDocuments.shared_documents.map((doc) => (
                        <label
                          key={doc.id}
                          className="flex items-center p-2 hover:bg-gray-50 rounded cursor-pointer"
                        >
                          <input
                            type="checkbox"
                            checked={selectedDocumentIds.includes(doc.id)}
                            onChange={() => toggleDocumentSelection(doc.id)}
                            className="h-4 w-4 text-primary-600 rounded border-gray-300"
                          />
                          <span className="ml-2 text-xs text-gray-700 truncate">
                            {doc.title || doc.filename}
                          </span>
                        </label>
                      ))}
                    </div>
                  )}
                  
                  {/* My Documents */}
                  {availableDocuments.my_documents.length > 0 && (
                    <div className="p-2 border-t border-gray-100">
                      <p className="text-xs font-semibold text-blue-600 mb-1">My Documents</p>
                      {availableDocuments.my_documents.map((doc) => (
                        <label
                          key={doc.id}
                          className="flex items-center p-2 hover:bg-gray-50 rounded cursor-pointer"
                        >
                          <input
                            type="checkbox"
                            checked={selectedDocumentIds.includes(doc.id)}
                            onChange={() => toggleDocumentSelection(doc.id)}
                            className="h-4 w-4 text-primary-600 rounded border-gray-300"
                          />
                          <span className="ml-2 text-xs text-gray-700 truncate">
                            {doc.title || doc.filename}
                          </span>
                        </label>
                      ))}
                    </div>
                  )}
                  
                  {availableDocuments.shared_documents.length === 0 && 
                   availableDocuments.my_documents.length === 0 && (
                    <p className="p-4 text-xs text-gray-500 text-center">
                      No documents available. Upload a document to get started.
                    </p>
                  )}

                  {selectedDocumentIds.length > 0 && (
                    <div className="p-2 border-t border-gray-100">
                      <button
                        onClick={clearSelectedDocuments}
                        className="text-xs text-red-600 hover:text-red-800"
                      >
                        Clear selection
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Conversations List */}
          <div className="flex-1 overflow-y-auto">
            {conversations.length === 0 ? (
              <div className="p-4 text-center text-gray-500">
                <ChatBubbleLeftRightIcon className="h-12 w-12 mx-auto mb-4 text-gray-300" />
                <p className="text-sm">No conversations yet</p>
                <p className="text-xs mt-1">Start a new conversation to begin</p>
              </div>
            ) : (
              <div className="divide-y divide-gray-200">
                {conversations.map((conversation) => (
                  <button
                    key={conversation.id}
                    onClick={() => selectConversation(conversation)}
                    className={`w-full p-4 text-left hover:bg-gray-50 focus:outline-none focus:bg-gray-50 ${
                      currentConversation?.id === conversation.id ? 'bg-primary-50 border-r-2 border-primary-500' : ''
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-900 truncate">
                          {conversation.title}
                        </p>
                        <p className="text-xs text-gray-500">
                          {conversation.message_count} messages • {formatDate(conversation.created_at)}
                        </p>
                      </div>
                      {conversation.project_id && (
                        <FolderIcon className="h-4 w-4 text-gray-400 ml-2" />
                      )}
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Chat Area */}
        <div className="flex-1 flex flex-col">
          {currentConversation ? (
            <>
              {/* Chat Header */}
              <div className="bg-white border-b border-gray-200 px-6 py-4">
                <h1 className="text-lg font-semibold text-gray-900">
                  {currentConversation.title}
                </h1>
                {currentConversation.project_id && (
                  <p className="text-sm text-gray-500 mt-1">
                    Searching in project: {projects.find(p => p.id === currentConversation.project_id)?.name}
                  </p>
                )}
              </div>

              {/* Messages */}
              <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
                {messages.length === 0 ? (
                  <div className="flex items-center justify-center h-full text-gray-500">
                    <div className="text-center">
                      <ChatBubbleLeftRightIcon className="h-16 w-16 mx-auto mb-4 text-gray-300" />
                      <h3 className="text-lg font-medium mb-2">Start a conversation</h3>
                      <p className="text-sm">Ask a question about your documents or knowledge base.</p>
                    </div>
                  </div>
                ) : (
                  messages.map((message) => (
                    <div
                      key={message.id}
                      className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
                    >
                      <div
                        className={`max-w-lg lg:max-w-xl xl:max-w-2xl rounded-lg px-4 py-3 ${
                          message.type === 'user'
                            ? 'bg-primary-600 text-white'
                            : 'bg-white border border-gray-200 text-gray-900'
                        }`}
                      >
                        <div className="whitespace-pre-wrap text-sm">
                          {message.content}
                        </div>

                        {message.type === 'assistant' && message.citations && message.citations.length > 0 && (
                          <div className="mt-3 pt-3 border-t border-gray-200">
                            <div className="flex items-center justify-between text-xs text-gray-500 mb-2">
                              <span>Sources:</span>
                              {message.confidence_score && (
                                <span>Confidence: {formatConfidenceScore(message.confidence_score)}</span>
                              )}
                            </div>
                            <div className="space-y-1">
                              {message.citations.map((citation, index) => (
                                <div key={index} className="flex items-center text-xs text-gray-600">
                                  <DocumentIcon className="h-3 w-3 mr-1" />
                                  <span>Document {citation.document_id}</span>
                                  {citation.page_number && (
                                    <span className="ml-1">• Page {citation.page_number}</span>
                                  )}
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        <div className={`text-xs mt-2 ${
                          message.type === 'user' ? 'text-primary-100' : 'text-gray-400'
                        }`}>
                          {formatDate(message.timestamp)}
                        </div>
                      </div>
                    </div>
                  ))
                )}

                {isLoading && (
                  <div className="flex justify-start">
                    <div className="bg-white border border-gray-200 rounded-lg px-4 py-3 max-w-lg">
                      <div className="flex items-center space-x-2">
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary-600"></div>
                        <span className="text-sm text-gray-500">Thinking...</span>
                      </div>
                    </div>
                  </div>
                )}

                <div ref={messagesEndRef} />
              </div>

              {/* Message Input */}
              <div className="bg-white border-t border-gray-200 px-6 py-4">
                {/* Selected Documents Indicator */}
                {selectedDocumentIds.length > 0 && (
                  <div className="flex items-center gap-2 mb-3 flex-wrap">
                    <span className="text-xs text-gray-500">Querying:</span>
                    {selectedDocumentIds.slice(0, 3).map((docId) => {
                      const doc = [...availableDocuments.shared_documents, ...availableDocuments.my_documents]
                        .find(d => d.id === docId);
                      return (
                        <span
                          key={docId}
                          className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-primary-100 text-primary-700"
                        >
                          <DocumentIcon className="h-3 w-3 mr-1" />
                          {doc?.title || doc?.filename || `Doc ${docId}`}
                          <button
                            onClick={() => toggleDocumentSelection(docId)}
                            className="ml-1 hover:text-primary-900"
                          >
                            <XMarkIcon className="h-3 w-3" />
                          </button>
                        </span>
                      );
                    })}
                    {selectedDocumentIds.length > 3 && (
                      <span className="text-xs text-gray-500">
                        +{selectedDocumentIds.length - 3} more
                      </span>
                    )}
                  </div>
                )}

                <div className="flex items-end space-x-4">
                  {/* File Upload Button */}
                  <input
                    type="file"
                    ref={fileInputRef}
                    onChange={handleFileUpload}
                    className="hidden"
                    accept=".pdf,.doc,.docx,.txt,.xls,.xlsx,.csv"
                  />
                  <button
                    onClick={() => fileInputRef.current?.click()}
                    disabled={isUploading || !currentConversation}
                    className="p-3 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-md disabled:opacity-50"
                    title="Upload document"
                  >
                    {isUploading ? (
                      <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-primary-600"></div>
                    ) : (
                      <PaperClipIcon className="h-5 w-5" />
                    )}
                  </button>

                  <div className="flex-1">
                    <textarea
                      value={newMessage}
                      onChange={(e) => setNewMessage(e.target.value)}
                      onKeyPress={handleKeyPress}
                      placeholder={
                        selectedDocumentIds.length > 0
                          ? `Ask about the selected ${selectedDocumentIds.length} document(s)...`
                          : "Ask a question about your documents..."
                      }
                      className="block w-full resize-none rounded-md border border-gray-300 px-4 py-3 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
                      rows={1}
                      disabled={isLoading}
                    />
                  </div>
                  <button
                    onClick={sendMessage}
                    disabled={!newMessage.trim() || isLoading}
                    className="inline-flex items-center px-4 py-3 border border-transparent text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <PaperAirplaneIcon className="h-4 w-4" />
                  </button>
                </div>
              </div>
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center bg-white">
              <div className="text-center max-w-md px-6">
                <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-primary-100 mb-6">
                  <ChatBubbleLeftRightIcon className="h-8 w-8 text-primary-600" />
                </div>
                <h2 className="text-2xl font-bold text-gray-900 mb-3">
                  AI Research Assistant
                </h2>
                <p className="text-gray-500 mb-8 leading-relaxed">
                  Select a conversation from the sidebar to continue your research, or start a new thread to ask questions about your documents.
                </p>
                <button
                  onClick={createNewConversation}
                  className="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-lg text-white bg-primary-600 hover:bg-primary-700 shadow-sm transition-colors"
                >
                  <PlusIcon className="h-5 w-5 mr-2" />
                  New Conversation
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </Layout>
  );
}
