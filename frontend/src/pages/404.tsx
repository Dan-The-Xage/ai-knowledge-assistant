import Link from 'next/link';

export default function Custom404() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8 text-center">
        <div>
          <h1 className="text-6xl font-bold text-gray-900">404</h1>
          <h2 className="mt-6 text-3xl font-bold text-gray-900">Page Not Found</h2>
          <p className="mt-2 text-sm text-gray-600">
            Sorry, we couldn't find the page you're looking for.
          </p>
        </div>

        <div className="space-y-4">
          <div className="text-left bg-white p-6 rounded-lg shadow">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Available Pages:</h3>
            <ul className="space-y-2 text-sm text-gray-600">
              <li>• <Link href="/" className="text-primary-600 hover:text-primary-500">Home</Link></li>
              <li>• <Link href="/login" className="text-primary-600 hover:text-primary-500">Login</Link></li>
              <li>• <Link href="/register" className="text-primary-600 hover:text-primary-500">Register</Link></li>
              <li>• <Link href="/dashboard" className="text-primary-600 hover:text-primary-500">Dashboard</Link></li>
              <li>• <Link href="/chat" className="text-primary-600 hover:text-primary-500">AI Chat</Link></li>
              <li>• <Link href="/documents/upload" className="text-primary-600 hover:text-primary-500">Upload Documents</Link></li>
            </ul>
          </div>

          <div>
            <Link
              href="/"
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700"
            >
              Go Home
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
