'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { authAPI, handleApiError, setAuthToken } from '@/services/api';
import toast, { Toaster } from 'react-hot-toast';
import { User } from '@/types/api';
import { Logo } from '@/components/Logo';

interface LoginPageProps {
  onUserChange: (user: User) => void;
}

export default function LoginPage({ onUserChange }: LoginPageProps) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [accountType, setAccountType] = useState('user');
  const [isLoading, setIsLoading] = useState(false);
  const router = useRouter();

  const accountTypes = [
    { id: 'super_admin', label: 'Super Admin' },
    { id: 'admin', label: 'Admin' },
    { id: 'user', label: 'User' },
    { id: 'guest', label: 'Guest' },
  ];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      const response = await authAPI.login({ email, password, account_type: accountType });
      const { access_token, user } = response.data;
      
      setAuthToken(access_token);
      onUserChange(user);
      
      toast.success(`Welcome back, ${user.full_name}!`);
      router.push('/dashboard');
    } catch (error: any) {
      toast.error(handleApiError(error));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8 bg-[url('/grid-pattern.svg')]">
      <Toaster position="top-right" />
      
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <div className="flex justify-center">
          <Logo className="h-16 w-auto scale-110" />
        </div>
        <h2 className="mt-8 text-center text-3xl font-bold tracking-tight text-gray-900">
          Sign in to DocuLens
        </h2>
        <p className="mt-2 text-center text-sm text-gray-600">
          Secure AI-Powered Knowledge Assistant
        </p>
        
        {/* Instruction for user to add logo image */}
        {/* NOTE: Place the official DSN logo at public/dsn-logo.png to use it here */}
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white py-8 px-4 shadow-xl shadow-gray-200/50 sm:rounded-xl sm:px-10 border border-gray-100">
          <form className="space-y-6" onSubmit={handleSubmit}>
            {/* Account Type Selection */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                I am signing in as a:
              </label>
              <div className="grid grid-cols-2 gap-2">
                {accountTypes.map((type) => (
                  <button
                    key={type.id}
                    type="button"
                    onClick={() => setAccountType(type.id)}
                    className={`
                      flex items-center justify-center px-3 py-2.5 text-xs font-bold rounded-md border transition-all duration-200
                      ${accountType === type.id
                        ? 'bg-dsn-blue text-white border-dsn-blue shadow-md ring-1 ring-dsn-blue'
                        : 'bg-white text-gray-600 border-gray-200 hover:bg-gray-50 hover:border-gray-300'
                      }
                    `}
                  >
                    {type.label}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-700">
                Email address
              </label>
              <div className="mt-1">
                <input
                  id="email"
                  name="email"
                  type="email"
                  autoComplete="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="block w-full appearance-none rounded-lg border border-gray-300 px-3 py-2 placeholder-gray-400 shadow-sm focus:border-dsn-blue focus:outline-none focus:ring-dsn-blue sm:text-sm"
                  placeholder="you@dsn.ai"
                />
              </div>
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-700">
                Password
              </label>
              <div className="mt-1">
                <input
                  id="password"
                  name="password"
                  type="password"
                  autoComplete="current-password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="block w-full appearance-none rounded-lg border border-gray-300 px-3 py-2 placeholder-gray-400 shadow-sm focus:border-dsn-blue focus:outline-none focus:ring-dsn-blue sm:text-sm"
                  placeholder="••••••••"
                />
              </div>
            </div>

            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <input
                  id="remember-me"
                  name="remember-me"
                  type="checkbox"
                  className="h-4 w-4 rounded border-gray-300 text-dsn-blue focus:ring-dsn-blue"
                />
                <label htmlFor="remember-me" className="ml-2 block text-sm text-gray-900">
                  Remember me
                </label>
              </div>

              <div className="text-sm">
                <a href="#" className="font-medium text-dsn-blue hover:text-blue-500">
                  Forgot password?
                </a>
              </div>
            </div>

            <div>
              <button
                type="submit"
                disabled={isLoading}
                className="flex w-full justify-center rounded-lg border border-transparent bg-dsn-blue py-2.5 px-4 text-sm font-bold text-white shadow-sm hover:bg-blue-900 focus:outline-none focus:ring-2 focus:ring-dsn-blue focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors uppercase tracking-wide"
              >
                {isLoading ? (
                  <div className="flex items-center">
                    <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent mr-2"></div>
                    Signing in...
                  </div>
                ) : (
                  'Sign in'
                )}
              </button>
            </div>
          </form>
        </div>
        
        <p className="mt-8 text-center text-xs text-gray-500">
          &copy; {new Date().getFullYear()} Data Scientists Network. All rights reserved.
        </p>
      </div>
    </div>
  );
}
