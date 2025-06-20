import axios from 'axios'
import type { User, Task, Category } from '@/types'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8080'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor to add auth token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Response interceptor to handle token refresh
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      const refreshToken = localStorage.getItem('refresh_token')
      if (refreshToken) {
        try {
          const response = await axios.post(`${API_BASE_URL}/auth/refresh`, {
            refresh_token: refreshToken,
          })
          localStorage.setItem('access_token', response.data.access_token)
          error.config.headers.Authorization = `Bearer ${response.data.access_token}`
          return api.request(error.config)
        } catch (refreshError) {
          localStorage.removeItem('access_token')
          localStorage.removeItem('refresh_token')
          window.location.href = '/login'
        }
      }
    }
    return Promise.reject(error)
  }
)

// Auth endpoints
export const authAPI = {
  login: async (email: string, password: string) => {
    const response = await api.post('/auth/login', { email, password })
    return response.data
  },
  
  register: async (email: string, password: string, name: string) => {
    const response = await api.post('/auth/register', { email, password, name })
    return response.data
  },
  
  me: async (): Promise<User> => {
    const response = await api.get('/auth/me')
    return response.data
  },
}

// Tasks endpoints
export const tasksAPI = {
  getAll: async (): Promise<Task[]> => {
    const response = await api.get('/tables/tasks')
    return response.data.records
  },
  
  create: async (task: Omit<Task, 'id' | 'user_id' | 'created_at' | 'updated_at'>): Promise<Task> => {
    const response = await api.post('/tables/tasks', task)
    return response.data
  },
  
  update: async (id: string, updates: Partial<Task>): Promise<Task> => {
    const response = await api.patch(`/tables/tasks/${id}`, updates)
    return response.data
  },
  
  delete: async (id: string): Promise<void> => {
    await api.delete(`/tables/tasks/${id}`)
  },
}

// Categories endpoints
export const categoriesAPI = {
  getAll: async (): Promise<Category[]> => {
    const response = await api.get('/tables/categories')
    return response.data.records
  },
  
  create: async (category: Omit<Category, 'id' | 'user_id' | 'created_at'>): Promise<Category> => {
    const response = await api.post('/tables/categories', category)
    return response.data
  },
}

export default api 