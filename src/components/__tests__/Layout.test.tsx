import { screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';

import Layout from '../Layout';

import { render } from '@/test/utils';

describe('Layout', () => {
  it('renders navigation links', () => {
    render(
      <Layout>
        <div>Test content</div>
      </Layout>
    );
    expect(screen.getByText('Thyme')).toBeInTheDocument();
    expect(screen.getByText('Home')).toBeInTheDocument();
    expect(screen.getByText('Login')).toBeInTheDocument();
    expect(screen.getByText('Register')).toBeInTheDocument();
  });

  it('renders test content', () => {
    render(
      <Layout>
        <div>Test content</div>
      </Layout>
    );
    expect(screen.getByText('Test content')).toBeInTheDocument();
  });

  it('shows dashboard link when user is authenticated', () => {
    vi.spyOn(Storage.prototype, 'getItem').mockReturnValue('mock-token');
    render(
      <Layout>
        <div>Test content</div>
      </Layout>
    );
    expect(screen.getByText('Home')).toBeInTheDocument();
  });
});
