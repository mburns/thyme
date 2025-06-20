import { Clock, Home, LogIn, UserPlus, LogOut, User } from 'lucide-react';
import { ReactNode } from 'react';
import { Link, useLocation } from 'react-router-dom';

import { useAuth } from '@/contexts/AuthContext';

interface LayoutProps {
  children: ReactNode;
}

export default function Layout({ children }: LayoutProps) {
  const { user, logout } = useAuth();
  const location = useLocation();

  const navigation = [
    { name: 'Home', href: '/', icon: Home },
    ...(user ? [{ name: 'Dashboard', href: '/dashboard', icon: Clock }] : []),
    ...(user
      ? []
      : [
          { name: 'Login', href: '/login', icon: LogIn },
          { name: 'Register', href: '/register', icon: UserPlus },
        ]),
  ];

  return (
    <div className='min-h-screen bg-gray-50'>
      <nav className='bg-white shadow-sm border-b border-gray-200'>
        <div className='max-w-7xl mx-auto px-4 sm:px-6 lg:px-8'>
          <div className='flex justify-between h-16'>
            <div className='flex items-center'>
              <Link to='/' className='flex items-center space-x-2'>
                <Clock className='h-8 w-8 text-primary-600' />
                <span className='text-xl font-bold text-gray-900'>Thyme</span>
              </Link>
            </div>

            <div className='flex items-center space-x-4'>
              {navigation.map(item => {
                const Icon = item.icon;
                const isActive = location.pathname === item.href;
                return (
                  <Link
                    key={item.name}
                    to={item.href}
                    className={`flex items-center space-x-2 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                      isActive
                        ? 'bg-primary-100 text-primary-700'
                        : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                    }`}
                  >
                    <Icon className='h-4 w-4' />
                    <span>{item.name}</span>
                  </Link>
                );
              })}

              {user && (
                <div className='flex items-center space-x-4'>
                  <div className='flex items-center space-x-2 text-sm text-gray-600'>
                    <User className='h-4 w-4' />
                    <span>{user.name || user.email}</span>
                  </div>
                  <button
                    onClick={logout}
                    className='flex items-center space-x-2 px-3 py-2 rounded-md text-sm font-medium text-gray-600 hover:text-gray-900 hover:bg-gray-100 transition-colors'
                  >
                    <LogOut className='h-4 w-4' />
                    <span>Logout</span>
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      </nav>

      <main className='max-w-7xl mx-auto py-6 sm:px-6 lg:px-8'>{children}</main>
    </div>
  );
}
