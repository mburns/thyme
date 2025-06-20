import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { tasksAPI, categoriesAPI } from '@/lib/api'
import type { Task, Category, TaskContextType } from '@/types'

const TaskContext = createContext<TaskContextType | undefined>(undefined)

export function TaskProvider({ children }: { children: ReactNode }) {
  const [tasks, setTasks] = useState<Task[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [loading, setLoading] = useState(false)

  const fetchTasks = async () => {
    setLoading(true)
    try {
      const data = await tasksAPI.getAll()
      setTasks(data)
    } catch (error) {
      console.error('Failed to fetch tasks:', error)
    } finally {
      setLoading(false)
    }
  }

  const fetchCategories = async () => {
    try {
      const data = await categoriesAPI.getAll()
      setCategories(data)
    } catch (error) {
      console.error('Failed to fetch categories:', error)
    }
  }

  const createTask = async (task: Omit<Task, 'id' | 'user_id' | 'created_at' | 'updated_at'>) => {
    try {
      const newTask = await tasksAPI.create(task)
      setTasks(prev => [...prev, newTask])
    } catch (error) {
      console.error('Failed to create task:', error)
      throw error
    }
  }

  const updateTask = async (id: string, updates: Partial<Task>) => {
    try {
      const updatedTask = await tasksAPI.update(id, updates)
      setTasks(prev => prev.map(task => task.id === id ? updatedTask : task))
    } catch (error) {
      console.error('Failed to update task:', error)
      throw error
    }
  }

  const deleteTask = async (id: string) => {
    try {
      await tasksAPI.delete(id)
      setTasks(prev => prev.filter(task => task.id !== id))
    } catch (error) {
      console.error('Failed to delete task:', error)
      throw error
    }
  }

  const createCategory = async (category: Omit<Category, 'id' | 'user_id' | 'created_at'>) => {
    try {
      const newCategory = await categoriesAPI.create(category)
      setCategories(prev => [...prev, newCategory])
    } catch (error) {
      console.error('Failed to create category:', error)
      throw error
    }
  }

  useEffect(() => {
    fetchTasks()
    fetchCategories()
  }, [])

  return (
    <TaskContext.Provider value={{
      tasks,
      categories,
      loading,
      createTask,
      updateTask,
      deleteTask,
      createCategory,
      fetchTasks,
      fetchCategories,
    }}>
      {children}
    </TaskContext.Provider>
  )
}

export function useTasks() {
  const context = useContext(TaskContext)
  if (context === undefined) {
    throw new Error('useTasks must be used within a TaskProvider')
  }
  return context
} 