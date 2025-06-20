import { Clock, CheckCircle, Users, Zap } from 'lucide-react';
import { Link } from 'react-router-dom';

import { useAuth } from '@/contexts/AuthContext';

export default function Home() {
  const { user } = useAuth();

  return (
    <div className='relative overflow-hidden'>
      {/* Hero Section */}
      <div className='relative bg-gradient-to-br from-primary-50 to-primary-100 py-20'>
        <div className='max-w-7xl mx-auto px-4 sm:px-6 lg:px-8'>
          <div className='text-center'>
            <div className='flex justify-center mb-6'>
              <div className='p-3 bg-primary-600 rounded-full'>
                <Clock className='h-12 w-12 text-white' />
              </div>
            </div>
            <h1 className='text-4xl font-bold text-gray-900 sm:text-5xl md:text-6xl'>
              Welcome to <span className='text-primary-600'>Thyme</span>
            </h1>
            <p className='mt-6 text-xl text-gray-600 max-w-3xl mx-auto'>
              A modern task management app built with TrailBase. Organize your
              time, track your progress, and achieve your goals with our
              intuitive interface.
            </p>
            <div className='mt-10 flex justify-center space-x-4'>
              {user ? (
                <Link to='/dashboard' className='btn-primary px-8 py-3 text-lg'>
                  Go to Dashboard
                </Link>
              ) : (
                <>
                  <Link
                    to='/register'
                    className='btn-primary px-8 py-3 text-lg'
                  >
                    Get Started
                  </Link>
                  <Link to='/login' className='btn-outline px-8 py-3 text-lg'>
                    Sign In
                  </Link>
                </>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Features Section */}
      <div className='py-20 bg-white'>
        <div className='max-w-7xl mx-auto px-4 sm:px-6 lg:px-8'>
          <div className='text-center mb-16'>
            <h2 className='text-3xl font-bold text-gray-900 sm:text-4xl'>
              Built with TrailBase
            </h2>
            <p className='mt-4 text-lg text-gray-600'>
              Experience the power of a modern, type-safe backend
            </p>
          </div>

          <div className='grid grid-cols-1 md:grid-cols-3 gap-8'>
            <div className='text-center'>
              <div className='flex justify-center mb-4'>
                <Zap className='h-12 w-12 text-primary-600' />
              </div>
              <h3 className='text-xl font-semibold text-gray-900 mb-2'>
                Blazing Fast
              </h3>
              <p className='text-gray-600'>
                Built on Rust, SQLite, and V8 for sub-millisecond latencies
              </p>
            </div>

            <div className='text-center'>
              <div className='flex justify-center mb-4'>
                <CheckCircle className='h-12 w-12 text-primary-600' />
              </div>
              <h3 className='text-xl font-semibold text-gray-900 mb-2'>
                Type Safe
              </h3>
              <p className='text-gray-600'>
                Full TypeScript support with auto-generated type definitions
              </p>
            </div>

            <div className='text-center'>
              <div className='flex justify-center mb-4'>
                <Users className='h-12 w-12 text-primary-600' />
              </div>
              <h3 className='text-xl font-semibold text-gray-900 mb-2'>
                Built-in Auth
              </h3>
              <p className='text-gray-600'>
                Secure authentication with JWT tokens and refresh tokens
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* CTA Section */}
      <div className='bg-primary-600 py-16'>
        <div className='max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center'>
          <h2 className='text-3xl font-bold text-white mb-4'>
            Ready to get started?
          </h2>
          <p className='text-xl text-primary-100 mb-8'>
            Join thousands of users who trust Thyme for their task management
            needs.
          </p>
          {!user && (
            <Link
              to='/register'
              className='bg-white text-primary-600 px-8 py-3 rounded-md font-semibold hover:bg-gray-100 transition-colors'
            >
              Create Your Account
            </Link>
          )}
        </div>
      </div>
    </div>
  );
}
