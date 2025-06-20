export interface User {
  id: string
  email: string
  name?: string
  avatar_url?: string
  created_at: string
  updated_at: string
}

export interface Task {
  id: string
  user_id: string
  title: string
  description?: string
  status: 'pending' | 'in_progress' | 'completed'
  priority: 'low' | 'medium' | 'high'
  due_date?: string
  created_at: string
  updated_at: string
}

export interface Category {
  id: string
  user_id: string
  name: string
  color: string
  created_at: string
}

export interface AuthContextType {
  user: User | null
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, name: string) => Promise<void>
  logout: () => void
  loading: boolean
}

export interface TaskContextType {
  tasks: Task[]
  categories: Category[]
  loading: boolean
  createTask: (task: Omit<Task, 'id' | 'user_id' | 'created_at' | 'updated_at'>) => Promise<void>
  updateTask: (id: string, updates: Partial<Task>) => Promise<void>
  deleteTask: (id: string) => Promise<void>
  createCategory: (category: Omit<Category, 'id' | 'user_id' | 'created_at'>) => Promise<void>
  fetchTasks: () => Promise<void>
  fetchCategories: () => Promise<void>
} 