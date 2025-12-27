'use client';

import { useState, useCallback, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useDropzone } from 'react-dropzone';
import {
  CloudArrowUpIcon,
  DocumentIcon,
  XMarkIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';
import { User, Project, Document } from '@/types/api';
import { documentAPI, projectAPI } from '@/services/api';
import { handleApiError } from '@/services/api';
import { formatFileSize, getFileIcon } from '@/utils/format';
import Layout from '@/components/Layout';
import toast, { Toaster } from 'react-hot-toast';

interface UploadPageProps {
  user: User | null;
  onUserChange: (user: User | null) => void;
}

interface FileWithPreview {
  file: File;  // Keep original File object
  preview?: string;
  id: string;
  name: string;
  size: number;
  status: 'pending' | 'uploading' | 'completed' | 'failed';
  progress: number;
  error?: string;
  uploadedDocument?: Document;
}

export default function UploadPage({ user, onUserChange }: UploadPageProps) {
  const [files, setFiles] = useState<FileWithPreview[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProject, setSelectedProject] = useState<number | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const router = useRouter();

  // Load projects on mount
  useEffect(() => {
    const loadProjects = async () => {
      try {
        const response = await projectAPI.list();
        const projectList = response.data?.data || response.data || [];
        setProjects(projectList);
        // Auto-select first project if available
        if (projectList.length > 0) {
          setSelectedProject(projectList[0].id);
        }
      } catch (error) {
        toast.error('Failed to load projects');
      }
    };
    loadProjects();
  }, []);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const newFiles: FileWithPreview[] = acceptedFiles.map((file) => ({
      file,  // Keep original File object
      id: `${file.name}-${Date.now()}`,
      name: file.name,
      size: file.size,
      status: 'pending',
      progress: 0,
    }));

    setFiles((prev) => [...prev, ...newFiles]);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'application/msword': ['.doc'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.ms-excel': ['.xls'],
      'text/plain': ['.txt'],
    },
    maxSize: 100 * 1024 * 1024, // 100MB
    multiple: true,
  });

  const removeFile = (fileId: string) => {
    setFiles((prev) => prev.filter((file) => file.id !== fileId));
  };

  const uploadFile = async (fileItem: FileWithPreview) => {
    if (!selectedProject) {
      toast.error('Please select a project first');
      return;
    }

    // Update status
    setFiles((prev) =>
      prev.map((f) => (f.id === fileItem.id ? { ...f, status: 'uploading' as const } : f))
    );

    try {
      const formData = new FormData();
      formData.append('file', fileItem.file);  // Use the original File object

      const response = await documentAPI.upload(formData, selectedProject);
      const result = response.data;

      setFiles((prev) =>
        prev.map((f) =>
          f.id === fileItem.id
            ? { ...f, status: 'completed' as const, progress: 100, uploadedDocument: result.document }
            : f
        )
      );

      toast.success(`"${fileItem.name}" uploaded successfully!`);
    } catch (error: any) {
      const errorMsg = handleApiError(error);
      setFiles((prev) =>
        prev.map((f) =>
          f.id === fileItem.id ? { ...f, status: 'failed' as const, error: errorMsg } : f
        )
      );
      toast.error(`Failed to upload "${fileItem.name}": ${errorMsg}`);
    }
  };

  const uploadAllFiles = async () => {
    if (!selectedProject) {
      toast.error('Please select a project first');
      return;
    }

    setIsUploading(true);
    const pendingFiles = files.filter((file) => file.status === 'pending');

    for (const file of pendingFiles) {
      await uploadFile(file);
    }

    setIsUploading(false);
  };

  const clearCompleted = () => {
    setFiles((prev) => prev.filter((file) => file.status !== 'completed'));
  };

  if (!user) {
    return null;
  }

  return (
    <Layout user={user} onUserChange={onUserChange}>
      <Toaster position="top-right" />
      <div className="px-4 sm:px-6 lg:px-8 py-8">
        <div className="max-w-4xl mx-auto">
          <div className="mb-8">
            <h1 className="text-2xl font-bold text-gray-900">Upload Documents</h1>
            <p className="mt-1 text-sm text-gray-600">
              Upload PDF, Word, Excel, or text files to your knowledge base.
            </p>
          </div>

          {/* Project Selection */}
          <div className="mb-6">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Select Project
            </label>
            <select
              value={selectedProject || ''}
              onChange={(e) => setSelectedProject(e.target.value ? parseInt(e.target.value) : null)}
              className="block w-full max-w-xs px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
            >
              <option value="">Choose a project...</option>
              {projects.map((project) => (
                <option key={project.id} value={project.id}>
                  {project.name}
                </option>
              ))}
            </select>
            {projects.length === 0 && (
              <p className="mt-1 text-sm text-gray-500">
                No projects available.{' '}
                <button
                  onClick={() => router.push('/projects/new')}
                  className="text-primary-600 hover:text-primary-500"
                >
                  Create a project first
                </button>
              </p>
            )}
          </div>

          {/* Dropzone */}
          <div className="mb-6">
            <div
              {...getRootProps()}
              className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
                isDragActive
                  ? 'border-primary-500 bg-primary-50'
                  : 'border-gray-300 hover:border-gray-400'
              }`}
            >
              <input {...getInputProps()} />
              <CloudArrowUpIcon className="mx-auto h-12 w-12 text-gray-400 mb-4" />
              <div className="text-lg font-medium text-gray-900 mb-2">
                {isDragActive ? 'Drop files here...' : 'Drag & drop files here'}
              </div>
              <p className="text-gray-500 mb-4">
                or click to browse files
              </p>
              <p className="text-sm text-gray-400">
                Supported: PDF, Word (.docx, .doc), Excel (.xlsx, .xls), Text (.txt) • Max 100MB each
              </p>
            </div>
          </div>

          {/* File List */}
          {files.length > 0 && (
            <div className="mb-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-medium text-gray-900">
                  Files to Upload ({files.length})
                </h3>
                <div className="space-x-2">
                  <button
                    onClick={uploadAllFiles}
                    disabled={isUploading || !selectedProject}
                    className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {isUploading ? 'Uploading...' : 'Upload All'}
                  </button>
                  <button
                    onClick={clearCompleted}
                    className="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
                  >
                    Clear Completed
                  </button>
                </div>
              </div>

              <div className="space-y-3">
                {files.map((file) => (
                  <div
                    key={file.id}
                    className="flex items-center justify-between p-4 bg-white border border-gray-200 rounded-lg"
                  >
                    <div className="flex items-center space-x-3 flex-1">
                      <div className="flex-shrink-0">
                        {file.status === 'completed' ? (
                          <CheckCircleIcon className="h-8 w-8 text-green-500" />
                        ) : file.status === 'failed' ? (
                          <ExclamationTriangleIcon className="h-8 w-8 text-red-500" />
                        ) : (
                          <span className="text-2xl">{getFileIcon(file.name)}</span>
                        )}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-900 truncate">
                          {file.name}
                        </p>
                        <p className="text-sm text-gray-500">
                          {formatFileSize(file.size)}
                        </p>
                        {file.error && (
                          <p className="text-sm text-red-600 mt-1">{file.error}</p>
                        )}
                      </div>
                    </div>

                    <div className="flex items-center space-x-3">
                      {file.status === 'uploading' && (
                        <div className="flex-1 min-w-0 mr-4">
                          <div className="w-32 bg-gray-200 rounded-full h-2">
                            <div
                              className="bg-primary-600 h-2 rounded-full transition-all duration-300"
                              style={{ width: `${file.progress}%` }}
                            ></div>
                          </div>
                          <p className="text-xs text-gray-500 mt-1">{file.progress}%</p>
                        </div>
                      )}

                      <div className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                        file.status === 'completed'
                          ? 'bg-green-100 text-green-800'
                          : file.status === 'failed'
                          ? 'bg-red-100 text-red-800'
                          : file.status === 'uploading'
                          ? 'bg-blue-100 text-blue-800'
                          : 'bg-gray-100 text-gray-800'
                      }`}>
                        {file.status}
                      </div>

                      {file.status === 'pending' && (
                        <button
                          onClick={() => uploadFile(file)}
                          disabled={!selectedProject}
                          className="text-primary-600 hover:text-primary-500 text-sm font-medium"
                        >
                          Upload
                        </button>
                      )}

                      <button
                        onClick={() => removeFile(file.id)}
                        className="text-gray-400 hover:text-gray-600"
                      >
                        <XMarkIcon className="h-5 w-5" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Instructions */}
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <div className="flex">
              <div className="flex-shrink-0">
                <DocumentIcon className="h-5 w-5 text-blue-400" />
              </div>
              <div className="ml-3">
                <h3 className="text-sm font-medium text-blue-800">
                  Upload Tips
                </h3>
                <div className="mt-2 text-sm text-blue-700">
                  <ul className="list-disc pl-5 space-y-1">
                    <li>Upload documents that contain information you want to query later</li>
                    <li>PDFs, Word docs, and Excel files work best for structured content</li>
                    <li>Large files may take longer to process</li>
                    <li>You can ask questions about uploaded documents immediately after processing</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
}
