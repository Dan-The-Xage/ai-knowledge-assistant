'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { ArrowLeftIcon, UserIcon, XMarkIcon } from '@heroicons/react/24/outline';
import { User } from '@/types/api';
import { projectAPI, adminAPI, handleApiError } from '@/services/api';
import Layout from '@/components/Layout';
import toast, { Toaster } from 'react-hot-toast';

interface NewProjectPageProps {
  user: User | null;
  onUserChange: (user: User | null) => void;
}

interface AvailableUser {
  id: number;
  email: string;
  full_name: string;
  role: string;
  department?: string;
}

export default function NewProjectPage({ user, onUserChange }: NewProjectPageProps) {
  const router = useRouter();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [availableUsers, setAvailableUsers] = useState<AvailableUser[]>([]);
  const [selectedMembers, setSelectedMembers] = useState<AvailableUser[]>([]);
  const [formData, setFormData] = useState({
    name: '',
    description: '',
  });

  const isAdmin = user?.role === 'super_admin' || user?.role === 'admin';

  useEffect(() => {
    if (isAdmin) {
      loadAvailableUsers();
    }
  }, [isAdmin]);

  const loadAvailableUsers = async () => {
    try {
      const response = await adminAPI.getUsers();
      const usersData = response.data?.data || response.data || [];
      // Filter out the current user from available users
      const filteredUsers = usersData.filter((u: AvailableUser) => u.id !== user?.id);
      setAvailableUsers(filteredUsers);
    } catch (error) {
      console.error('Failed to load users:', error);
    }
  };

  const toggleMemberSelection = (user: AvailableUser) => {
    setSelectedMembers(prev =>
      prev.find(m => m.id === user.id)
        ? prev.filter(m => m.id !== user.id)
        : [...prev, user]
    );
  };

  const removeMember = (userId: number) => {
    setSelectedMembers(prev => prev.filter(m => m.id !== userId));
  };

  if (!user) {
    router.push('/login');
    return null;
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!formData.name.trim()) {
      toast.error('Project name is required');
      return;
    }

    setIsSubmitting(true);
    try {
      const response = await projectAPI.create({
        name: formData.name.trim(),
        description: formData.description.trim() || undefined,
        member_ids: isAdmin ? selectedMembers.map(m => m.id) : undefined,
      });
      
      toast.success('Project created successfully!');
      
      // Navigate to the new project or projects list
      const projectId = response.data?.id || response.data?.data?.id;
      if (projectId) {
        router.push(`/projects/${projectId}`);
      } else {
        router.push('/projects');
      }
    } catch (error: any) {
      toast.error(handleApiError(error));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Layout user={user} onUserChange={onUserChange}>
      <Toaster position="top-right" />
      <div className="max-w-2xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <button
            onClick={() => router.push('/projects')}
            className="flex items-center text-sm text-gray-500 hover:text-gray-700 mb-4"
          >
            <ArrowLeftIcon className="h-4 w-4 mr-1" />
            Back to Projects
          </button>
          <h1 className="text-2xl font-semibold text-gray-900">Create New Project</h1>
          <p className="mt-2 text-sm text-gray-600">
            Projects help you organize documents and control access for your team.
          </p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="bg-white shadow rounded-lg p-6">
          <div className="space-y-6">
            {/* Project Name */}
            <div>
              <label htmlFor="name" className="block text-sm font-medium text-gray-700">
                Project Name <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                id="name"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                placeholder="e.g., Company Policies, Technical Documentation"
                required
              />
            </div>

            {/* Description */}
            <div>
              <label htmlFor="description" className="block text-sm font-medium text-gray-700">
                Description
              </label>
              <textarea
                id="description"
                rows={4}
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                placeholder="Describe the purpose of this project..."
              />
            </div>

            {/* Team Members - Only for Admin/Super Admin */}
            {isAdmin && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Add Team Members
                </label>

                {/* Selected Members */}
                {selectedMembers.length > 0 && (
                  <div className="mb-4">
                    <p className="text-sm text-gray-600 mb-2">Selected members:</p>
                    <div className="flex flex-wrap gap-2">
                      {selectedMembers.map((member) => (
                        <div
                          key={member.id}
                          className="inline-flex items-center px-3 py-1 rounded-full text-sm bg-primary-100 text-primary-800"
                        >
                          <UserIcon className="h-3 w-3 mr-1" />
                          {member.full_name} ({member.email})
                          <button
                            type="button"
                            onClick={() => removeMember(member.id)}
                            className="ml-1 hover:text-primary-900"
                          >
                            <XMarkIcon className="h-3 w-3" />
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Available Users */}
                <div className="max-h-60 overflow-y-auto border border-gray-200 rounded-md">
                  <div className="p-4">
                    <p className="text-sm text-gray-600 mb-3">
                      Select team members to add to this project:
                    </p>
                    {availableUsers.length === 0 ? (
                      <p className="text-sm text-gray-500">No additional users available</p>
                    ) : (
                      <div className="space-y-2">
                        {availableUsers.map((availableUser) => (
                          <label
                            key={availableUser.id}
                            className="flex items-center p-2 hover:bg-gray-50 rounded cursor-pointer"
                          >
                            <input
                              type="checkbox"
                              checked={selectedMembers.some(m => m.id === availableUser.id)}
                              onChange={() => toggleMemberSelection(availableUser)}
                              className="h-4 w-4 text-primary-600 rounded border-gray-300 focus:ring-primary-500"
                            />
                            <div className="ml-3">
                              <p className="text-sm font-medium text-gray-900">
                                {availableUser.full_name}
                              </p>
                              <p className="text-xs text-gray-500">
                                {availableUser.email} • {availableUser.role} {availableUser.department && `• ${availableUser.department}`}
                              </p>
                            </div>
                          </label>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
                <p className="mt-2 text-xs text-gray-500">
                  Selected members will be added to the project as regular members.
                </p>
              </div>
            )}
          </div>

          {/* Actions */}
          <div className="mt-6 flex items-center justify-end space-x-4">
            <button
              type="button"
              onClick={() => router.push('/projects')}
              className="px-4 py-2 text-sm font-medium text-gray-700 hover:text-gray-900"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isSubmitting ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                  Creating...
                </>
              ) : (
                'Create Project'
              )}
            </button>
          </div>
        </form>
      </div>
    </Layout>
  );
}

