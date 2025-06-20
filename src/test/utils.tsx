import React, { ReactElement } from 'react'
import { render, RenderOptions } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { AuthProvider } from '@/contexts/AuthContext'
import { TaskProvider } from '@/contexts/TaskContext'

interface CustomRenderOptions extends Omit<RenderOptions, 'wrapper'> {
  route?: string
}

const AllTheProviders = ({ children }: { children: React.ReactNode }) => {
  return (
    <BrowserRouter>
      <AuthProvider>
        <TaskProvider>{children}</TaskProvider>
      </AuthProvider>
    </BrowserRouter>
  )
}

const customRender = (
  ui: ReactElement,
  options: CustomRenderOptions = {}
) => {
  const { route = '/', ...renderOptions } = options

  window.history.pushState({}, 'Test page', route)

  return render(ui, { wrapper: AllTheProviders, ...renderOptions })
}

export * from '@testing-library/react'
export { customRender as render } 