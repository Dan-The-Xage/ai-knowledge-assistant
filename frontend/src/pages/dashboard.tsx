'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { 
  DocumentDuplicateIcon, 
  ChatBubbleLeftRightIcon, 
  FolderIcon, 
  ClockIcon,
  ArrowRightIcon
} from '@heroicons/react/24/outline';
import { User } from '@/types/api';
import Layout from '@/components/Layout';
import { projectAPI, conversationAPI } from '@/services/api';
import { formatDate } from '@/utils/format';

interface DashboardProps {
  user: User | null;
  onUserChange: (user: User | null) => void;
}

export default function DashboardPage({ user, onUserChange }: DashboardProps) {
  const router = useRouter();
  const [stats, setStats] = useState({
    projects: 0,
    conversations: 0,
    recentActivity: [] as any[]
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user) {
      router.push('/login');
      return;
    }

    const loadStats = async () => {
      try {
        const [projectsRes, conversationsRes] = await Promise.all([
          projectAPI.list(),
          conversationAPI.list()
        ]);
        
        const projects = Array.isArray(projectsRes.data) ? projectsRes.data : (projectsRes.data?.data || []);
        const conversations = Array.isArray(conversationsRes.data) ? conversationsRes.data : (conversationsRes.data?.data || []);
        
        setStats({
          projects: projects.length,
          conversations: conversations.length,
          recentActivity: conversations.slice(0, 5)
        });
      } catch (error) {
        console.error('Failed to load stats', error);
      } finally {
        setLoading(false);
      }
    };

    loadStats();
  }, [user, router]);

  if (!user) return null;

  return (
    <Layout user={user} onUserChange={onUserChange}>
      <div className="space-y-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Welcome back, {user.full_name?.split(' ')[0]}</h1>
          <p className="mt-1 text-sm text-gray-500">Here's what's happening in your knowledge base.</p>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {/* Projects Card */}
          <div className="relative overflow-hidden rounded-xl bg-white p-6 shadow-sm ring-1 ring-gray-900/5 hover:shadow-md transition-shadow">
            <dt>
              <div className="absolute rounded-md bg-dsn-blue p-3">
                <FolderIcon className="h-6 w-6 text-white" aria-hidden="true" />
              </div>
              <p className="ml-16 truncate text-sm font-medium text-gray-500">Active Projects</p>
            </dt>
            <dd className="ml-16 flex items-baseline pb-1 sm:pb-2">
              <p className="text-2xl font-semibold text-gray-900">{stats.projects}</p>
            </dd>
            <div className="mt-4 border-t border-gray-50 pt-4">
              <button 
                onClick={() => router.push('/projects')}
                className="text-sm font-medium text-dsn-blue hover:text-blue-700 flex items-center gap-1"
              >
                View all projects <ArrowRightIcon className="h-4 w-4" />
              </button>
            </div>
          </div>

          {/* Conversations Card */}
          <div className="relative overflow-hidden rounded-xl bg-white p-6 shadow-sm ring-1 ring-gray-900/5 hover:shadow-md transition-shadow">
            <dt>
              <div className="absolute rounded-md bg-dsn-green p-3">
                <ChatBubbleLeftRightIcon className="h-6 w-6 text-white" aria-hidden="true" />
              </div>
              <p className="ml-16 truncate text-sm font-medium text-gray-500">Conversations</p>
            </dt>
            <dd className="ml-16 flex items-baseline pb-1 sm:pb-2">
              <p className="text-2xl font-semibold text-gray-900">{stats.conversations}</p>
            </dd>
            <div className="mt-4 border-t border-gray-50 pt-4">
              <button 
                onClick={() => router.push('/chat')}
                className="text-sm font-medium text-dsn-green hover:text-green-700 flex items-center gap-1"
              >
                Start new chat <ArrowRightIcon className="h-4 w-4" />
              </button>
            </div>
          </div>

          {/* Documents Card */}
          <div className="relative overflow-hidden rounded-xl bg-white p-6 shadow-sm ring-1 ring-gray-900/5 hover:shadow-md transition-shadow">
            <dt>
              <div className="absolute rounded-md bg-dsn-red p-3">
                <DocumentDuplicateIcon className="h-6 w-6 text-white" aria-hidden="true" />
              </div>
              <p className="ml-16 truncate text-sm font-medium text-gray-500">Document Upload</p>
            </dt>
            <dd className="ml-16 flex items-baseline pb-1 sm:pb-2">
              <p className="text-sm text-gray-600 mt-1">Upload files to analyze</p>
            </dd>
            <div className="mt-4 border-t border-gray-50 pt-4">
              <button 
                onClick={() => router.push('/documents/upload')}
                className="text-sm font-medium text-dsn-red hover:text-red-700 flex items-center gap-1"
              >
                Upload documents <ArrowRightIcon className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>

        {/* Recent Activity */}
        <div className="rounded-xl bg-white shadow-sm ring-1 ring-gray-900/5">
          <div className="border-b border-gray-200 px-4 py-5 sm:px-6">
            <h3 className="text-base font-semibold leading-6 text-gray-900">Recent Activity</h3>
          </div>
          <ul role="list" className="divide-y divide-gray-100">
            {stats.recentActivity.length > 0 ? (
              stats.recentActivity.map((activity) => (
                <li key={activity.id} className="relative flex gap-x-6 px-4 py-5 hover:bg-gray-50 sm:px-6">
                  <div className="flex h-10 w-10 flex-none items-center justify-center rounded-lg bg-gray-50 ring-1 ring-gray-200">
                    <ClockIcon className="h-6 w-6 text-gray-600" aria-hidden="true" />
                  </div>
                  <div className="flex-auto">
                    <p className="text-sm font-semibold leading-6 text-gray-900">
                      <a href={`/chat?id=${activity.id}`}>
                        <span className="absolute inset-x-0 -top-px bottom-0" />
                        {activity.title || 'Untitled Conversation'}
                      </a>
                    </p>
                    <p className="mt-1 flex text-xs leading-5 text-gray-500">
                      Started by you • {formatDate(activity.created_at)}
                    </p>
                  </div>
                  <div className="flex items-center gap-x-4">
                    <div className="hidden sm:flex sm:flex-col sm:items-end">
                      <p className="text-sm leading-6 text-gray-900">{activity.message_count} messages</p>
                    </div>
                    <ArrowRightIcon className="h-5 w-5 flex-none text-gray-400" aria-hidden="true" />
                  </div>
                </li>
              ))
            ) : (
              <li className="px-4 py-8 text-center text-gray-500">
                No recent activity found. Start using the platform to see your history here.
              </li>
            )}
          </ul>
        </div>
      </div>
    </Layout>
  );
}
