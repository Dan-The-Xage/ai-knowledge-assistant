'use client';

import { useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import Link from 'next/link';
import {
  HomeIcon,
  DocumentDuplicateIcon,
  ChatBubbleLeftRightIcon,
  FolderIcon,
  Cog6ToothIcon,
  ArrowRightOnRectangleIcon,
  Bars3Icon,
  XMarkIcon,
  UserGroupIcon,
  QuestionMarkCircleIcon
} from '@heroicons/react/24/outline';
import { User } from '@/types/api';
import { authAPI } from '@/services/api';
import toast from 'react-hot-toast';
import { Logo } from './Logo';

interface LayoutProps {
  children: React.ReactNode;
  user: User | null;
  onUserChange: (user: User | null) => void;
}

const navigation = [
  { name: 'Dashboard', href: '/dashboard', icon: HomeIcon },
  { name: 'Projects', href: '/projects', icon: FolderIcon },
  { name: 'Documents', href: '/documents/upload', icon: DocumentDuplicateIcon },
  { name: 'Chat Assistant', href: '/chat', icon: ChatBubbleLeftRightIcon },
  { name: 'Team', href: '/team', icon: UserGroupIcon },
];

const adminNavigation = [
  { name: 'User Management', href: '/admin/users', icon: Cog6ToothIcon },
];

export default function Layout({ children, user, onUserChange }: LayoutProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const router = useRouter();
  const pathname = usePathname();

  const handleLogout = async () => {
    try {
      authAPI.logout();
      onUserChange(null);
      router.push('/login');
      toast.success('Logged out successfully');
    } catch (error) {
      toast.error('Error logging out');
    }
  };

  const isAdmin = user?.role === 'admin' || user?.role === 'super_admin';

  return (
    <div className="min-h-screen bg-gray-50 flex">
      {/* Mobile sidebar */}
      <div className={`fixed inset-0 z-50 lg:hidden ${sidebarOpen ? 'block' : 'hidden'}`}>
        <div className="fixed inset-0 bg-gray-900/80 backdrop-blur-sm transition-opacity" onClick={() => setSidebarOpen(false)} />
        <div className="fixed inset-y-0 left-0 flex w-full max-w-xs flex-col bg-white shadow-xl transition-transform">
          <div className="flex h-16 flex-shrink-0 items-center justify-between px-6 border-b border-gray-100">
            <Logo />
            <button
              onClick={() => setSidebarOpen(false)}
              className="text-gray-400 hover:text-gray-600 transition-colors"
            >
              <XMarkIcon className="h-6 w-6" />
            </button>
          </div>
          <nav className="flex-1 space-y-1 px-3 py-6 overflow-y-auto">
            {navigation.map((item) => {
              const isActive = pathname?.startsWith(item.href);
              return (
                <Link
                  key={item.name}
                  href={item.href}
                  className={`group flex items-center rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-200 ${
                    isActive 
                      ? 'bg-dsn-blue text-white shadow-md' 
                      : 'text-gray-700 hover:bg-gray-100 hover:text-dsn-blue'
                  }`}
                  onClick={() => setSidebarOpen(false)}
                >
                  <item.icon className={`mr-3 h-5 w-5 flex-shrink-0 ${isActive ? 'text-white' : 'text-gray-400 group-hover:text-dsn-blue'}`} />
                  {item.name}
                </Link>
              );
            })}
            
            {isAdmin && (
              <>
                <div className="mt-6 mb-2 px-3">
                  <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Administration</p>
                </div>
                {adminNavigation.map((item) => {
                   const isActive = pathname?.startsWith(item.href);
                   return (
                    <Link
                      key={item.name}
                      href={item.href}
                      className={`group flex items-center rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-200 ${
                        isActive 
                          ? 'bg-primary-50 text-primary-700 shadow-sm' 
                          : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900'
                      }`}
                      onClick={() => setSidebarOpen(false)}
                    >
                      <item.icon className={`mr-3 h-5 w-5 flex-shrink-0 ${isActive ? 'text-primary-600' : 'text-gray-400 group-hover:text-gray-500'}`} />
                      {item.name}
                    </Link>
                  );
                })}
              </>
            )}
          </nav>
        </div>
      </div>

      {/* Desktop sidebar */}
      <div className="hidden lg:fixed lg:inset-y-0 lg:flex lg:w-72 lg:flex-col">
        <div className="flex flex-col flex-grow bg-white border-r border-gray-200 shadow-[4px_0_24px_-12px_rgba(0,0,0,0.1)]">
          <div className="flex h-20 flex-shrink-0 items-center px-6 border-b border-gray-100">
            <Logo />
          </div>
          <nav className="flex-1 flex flex-col space-y-1 px-4 py-6 overflow-y-auto">
            <div className="space-y-1">
              {navigation.map((item) => {
                const isActive = pathname?.startsWith(item.href);
                return (
                  <Link
                    key={item.name}
                    href={item.href}
                    className={`group flex items-center rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-200 ${
                      isActive 
                        ? 'bg-dsn-blue text-white shadow-md' 
                        : 'text-gray-600 hover:bg-gray-50 hover:text-dsn-blue'
                    }`}
                  >
                    <item.icon className={`mr-3 h-5 w-5 flex-shrink-0 ${isActive ? 'text-white' : 'text-gray-400 group-hover:text-dsn-blue'}`} />
                    {item.name}
                  </Link>
                );
              })}
            </div>

            {isAdmin && (
              <div className="mt-8">
                <div className="px-3 mb-2">
                  <p className="text-xs font-bold text-gray-400 uppercase tracking-wider">Administration</p>
                </div>
                <div className="space-y-1">
                  {adminNavigation.map((item) => {
                    const isActive = pathname?.startsWith(item.href);
                    return (
                      <Link
                        key={item.name}
                        href={item.href}
                        className={`group flex items-center rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-200 ${
                          isActive 
                            ? 'bg-primary-50 text-primary-700 shadow-sm ring-1 ring-primary-100' 
                            : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                        }`}
                      >
                        <item.icon className={`mr-3 h-5 w-5 flex-shrink-0 ${isActive ? 'text-primary-600' : 'text-gray-400 group-hover:text-gray-500'}`} />
                        {item.name}
                      </Link>
                    );
                  })}
                </div>
              </div>
            )}
            
            <div className="mt-auto pt-6 border-t border-gray-100">
              <Link
                href="/help"
                className="group flex items-center rounded-lg px-3 py-2.5 text-sm font-medium text-gray-600 hover:bg-gray-50 hover:text-gray-900"
              >
                <QuestionMarkCircleIcon className="mr-3 h-5 w-5 text-gray-400 group-hover:text-gray-500" />
                Help & Support
              </Link>
            </div>
          </nav>

          {/* User profile section */}
          <div className="p-4 border-t border-gray-200 bg-gray-50/50">
            <div className="flex items-center w-full">
              <div className="flex-shrink-0">
                <div className="h-9 w-9 rounded-full bg-gradient-to-br from-primary-500 to-primary-600 flex items-center justify-center text-white text-sm font-semibold shadow-sm">
                  {user?.full_name?.charAt(0)?.toUpperCase() || 'U'}
                </div>
              </div>
              <div className="ml-3 flex-1 min-w-0">
                <p className="text-sm font-semibold text-gray-900 truncate">
                  {user?.full_name}
                </p>
                <p className="text-xs text-gray-500 truncate">
                  {user?.email}
                </p>
              </div>
              <button
                onClick={handleLogout}
                className="ml-2 p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-md transition-colors"
                title="Logout"
              >
                <ArrowRightOnRectangleIcon className="h-5 w-5" />
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Main content */}
      <div className="lg:pl-72 flex flex-col flex-1 w-full min-w-0 transition-all duration-300">
        {/* Mobile header */}
        <div className="sticky top-0 z-20 flex h-16 flex-shrink-0 bg-white/80 backdrop-blur-md border-b border-gray-200 lg:hidden items-center px-4 justify-between">
          <button
            onClick={() => setSidebarOpen(true)}
            className="text-gray-500 hover:text-gray-700 focus:outline-none"
          >
            <Bars3Icon className="h-6 w-6" />
          </button>
          
          <Logo className="h-6" />
          
          <div className="w-6" /> {/* Spacer for centering */}
        </div>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto bg-gray-50/50 p-4 sm:p-6 lg:p-8">
          <div className="max-w-7xl mx-auto w-full">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
