'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { UserIcon, EnvelopeIcon, BriefcaseIcon } from '@heroicons/react/24/outline';
import { User } from '@/types/api';
import Layout from '@/components/Layout';
import { adminAPI } from '@/services/api';
import toast from 'react-hot-toast';

interface TeamPageProps {
  user: User | null;
  onUserChange: (user: User | null) => void;
}

export default function TeamPage({ user, onUserChange }: TeamPageProps) {
  const router = useRouter();
  const [teamMembers, setTeamMembers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user) {
      router.push('/login');
      return;
    }

    const loadTeam = async () => {
      try {
        // Only fetch full user list if admin, otherwise might need a public team endpoint
        // For now, we'll try to fetch users and handle errors gracefully
        const response = await adminAPI.getUsers();
        const users = Array.isArray(response.data) ? response.data : (response.data?.data || []);
        setTeamMembers(users);
      } catch (error) {
        // If not authorized (403), we might just show the current user or a message
        console.error('Failed to load team', error);
      } finally {
        setLoading(false);
      }
    };

    loadTeam();
  }, [user, router]);

  if (!user) return null;

  return (
    <Layout user={user} onUserChange={onUserChange}>
      <div className="space-y-8">
        <div className="md:flex md:items-center md:justify-between">
          <div className="min-w-0 flex-1">
            <h2 className="text-2xl font-bold leading-7 text-gray-900 sm:truncate sm:text-3xl sm:tracking-tight">
              Team Directory
            </h2>
            <p className="mt-1 text-sm text-gray-500">
              Members of the DSN DocuLens platform.
            </p>
          </div>
        </div>

        {loading ? (
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="animate-pulse bg-white p-6 rounded-lg shadow h-32"></div>
            ))}
          </div>
        ) : (
          <ul role="list" className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {teamMembers.length > 0 ? (
              teamMembers.map((member) => (
                <li key={member.id} className="col-span-1 divide-y divide-gray-200 rounded-lg bg-white shadow hover:shadow-md transition-shadow">
                  <div className="flex w-full items-center justify-between space-x-6 p-6">
                    <div className="flex-1 truncate">
                      <div className="flex items-center space-x-3">
                        <h3 className="truncate text-sm font-medium text-gray-900">{member.full_name}</h3>
                        <span className={`inline-flex flex-shrink-0 items-center rounded-full px-1.5 py-0.5 text-xs font-medium ${
                          member.role === 'super_admin' ? 'bg-red-50 text-red-700 ring-1 ring-inset ring-red-600/20' :
                          member.role === 'admin' ? 'bg-purple-50 text-purple-700 ring-1 ring-inset ring-purple-600/20' :
                          'bg-green-50 text-green-700 ring-1 ring-inset ring-green-600/20'
                        }`}>
                          {member.role?.replace('_', ' ')}
                        </span>
                      </div>
                      <p className="mt-1 truncate text-sm text-gray-500">{member.job_title || 'Team Member'}</p>
                      <p className="mt-1 truncate text-xs text-gray-400">{member.department || 'General'}</p>
                    </div>
                    <div className="h-10 w-10 flex-shrink-0 rounded-full bg-gray-200 flex items-center justify-center text-gray-500 font-bold">
                      {member.full_name?.charAt(0).toUpperCase()}
                    </div>
                  </div>
                  <div>
                    <div className="-mt-px flex divide-x divide-gray-200">
                      <div className="flex w-0 flex-1">
                        <a
                          href={`mailto:${member.email}`}
                          className="relative -mr-px inline-flex w-0 flex-1 items-center justify-center gap-x-3 rounded-bl-lg border border-transparent py-4 text-sm font-semibold text-gray-900 hover:text-gray-600"
                        >
                          <EnvelopeIcon className="h-5 w-5 text-gray-400" aria-hidden="true" />
                          Email
                        </a>
                      </div>
                    </div>
                  </div>
                </li>
              ))
            ) : (
              <div className="col-span-full text-center py-12 bg-white rounded-lg shadow">
                <UserIcon className="mx-auto h-12 w-12 text-gray-400" />
                <h3 className="mt-2 text-sm font-semibold text-gray-900">No team members found</h3>
                <p className="mt-1 text-sm text-gray-500">You might not have permission to view the directory.</p>
              </div>
            )}
          </ul>
        )}
      </div>
    </Layout>
  );
}
