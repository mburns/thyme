import {
  Plus,
  Search,
  Calendar,
  CheckCircle,
  Clock,
  AlertCircle,
} from 'lucide-react';
import { useState } from 'react';

import { useTasks } from '@/contexts/TaskContext';
import type { Task } from '@/types';

export default function Dashboard() {
  const { tasks, loading, createTask, updateTask, deleteTask } = useTasks();
  const [showNewTask, setShowNewTask] = useState(false);
  const [filter, setFilter] = useState<
    'all' | 'pending' | 'in_progress' | 'completed'
  >('all');
  const [searchTerm, setSearchTerm] = useState('');

  const filteredTasks = tasks.filter(task => {
    const matchesFilter = filter === 'all' || task.status === filter;
    const matchesSearch =
      task.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      task.description?.toLowerCase().includes(searchTerm.toLowerCase());
    return matchesFilter && matchesSearch;
  });

  const getStatusIcon = (status: Task['status']) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className='h-5 w-5 text-green-500' />;
      case 'in_progress':
        return <Clock className='h-5 w-5 text-yellow-500' />;
      default:
        return <AlertCircle className='h-5 w-5 text-gray-400' />;
    }
  };

  const getPriorityColor = (priority: Task['priority']) => {
    switch (priority) {
      case 'high':
        return 'bg-red-100 text-red-800';
      case 'medium':
        return 'bg-yellow-100 text-yellow-800';
      default:
        return 'bg-green-100 text-green-800';
    }
  };

  return (
    <div className='space-y-6'>
      {/* Header */}
      <div className='flex justify-between items-center'>
        <div>
          <h1 className='text-2xl font-bold text-gray-900'>Dashboard</h1>
          <p className='text-gray-600'>Manage your tasks and stay organized</p>
        </div>
        <button onClick={() => setShowNewTask(true)} className='btn-primary'>
          <Plus className='h-4 w-4 mr-2' />
          New Task
        </button>
      </div>

      {/* Filters */}
      <div className='flex flex-col sm:flex-row gap-4'>
        <div className='relative flex-1'>
          <Search className='absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400' />
          <input
            type='text'
            placeholder='Search tasks...'
            value={searchTerm}
            onChange={e => setSearchTerm(e.target.value)}
            className='input pl-10'
          />
        </div>
        <div className='flex gap-2'>
          {(['all', 'pending', 'in_progress', 'completed'] as const).map(
            status => (
              <button
                key={status}
                onClick={() => setFilter(status)}
                className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                  filter === status
                    ? 'bg-primary-100 text-primary-700'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                {status.charAt(0).toUpperCase() +
                  status.slice(1).replace('_', ' ')}
              </button>
            )
          )}
        </div>
      </div>

      {/* Tasks Grid */}
      {loading ? (
        <div className='flex justify-center py-12'>
          <div className='animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600'></div>
        </div>
      ) : filteredTasks.length === 0 ? (
        <div className='text-center py-12'>
          <Clock className='h-12 w-12 text-gray-400 mx-auto mb-4' />
          <h3 className='text-lg font-medium text-gray-900 mb-2'>
            No tasks found
          </h3>
          <p className='text-gray-600'>
            Get started by creating your first task.
          </p>
        </div>
      ) : (
        <div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6'>
          {filteredTasks.map(task => (
            <div key={task.id} className='card'>
              <div className='flex justify-between items-start mb-4'>
                <div className='flex items-center space-x-2'>
                  {getStatusIcon(task.status)}
                  <h3 className='font-semibold text-gray-900'>{task.title}</h3>
                </div>
                <span
                  className={`px-2 py-1 rounded-full text-xs font-medium ${getPriorityColor(
                    task.priority
                  )}`}
                >
                  {task.priority}
                </span>
              </div>

              {task.description && (
                <p className='text-gray-600 text-sm mb-4'>{task.description}</p>
              )}

              {task.due_date && (
                <div className='flex items-center text-sm text-gray-500 mb-4'>
                  <Calendar className='h-4 w-4 mr-1' />
                  {new Date(task.due_date).toLocaleDateString()}
                </div>
              )}

              <div className='flex justify-between items-center'>
                <div className='flex space-x-2'>
                  <button
                    onClick={() => updateTask(task.id, { status: 'completed' })}
                    className='text-sm text-green-600 hover:text-green-700'
                  >
                    Complete
                  </button>
                  <button
                    onClick={() => deleteTask(task.id)}
                    className='text-sm text-red-600 hover:text-red-700'
                  >
                    Delete
                  </button>
                </div>
                <span className='text-xs text-gray-400'>
                  {new Date(task.created_at).toLocaleDateString()}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* New Task Modal */}
      {showNewTask && (
        <NewTaskModal
          onClose={() => setShowNewTask(false)}
          onCreate={createTask}
        />
      )}
    </div>
  );
}

interface NewTaskModalProps {
  onClose: () => void;
  onCreate: (
    task: Omit<Task, 'id' | 'user_id' | 'created_at' | 'updated_at'>
  ) => Promise<void>;
}

function NewTaskModal({ onClose, onCreate }: NewTaskModalProps) {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [priority, setPriority] = useState<Task['priority']>('medium');
  const [dueDate, setDueDate] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      await onCreate({
        title,
        description,
        priority,
        due_date: dueDate || undefined,
        status: 'pending',
      });
      onClose();
    } catch (error) {
      console.error('Failed to create task:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className='fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50'>
      <div className='bg-white rounded-lg p-6 w-full max-w-md'>
        <h2 className='text-xl font-bold mb-4'>Create New Task</h2>

        <form onSubmit={handleSubmit} className='space-y-4'>
          <div>
            <label
              htmlFor='title'
              className='block text-sm font-medium text-gray-700 mb-1'
            >
              Title
            </label>
            <input
              id='title'
              type='text'
              required
              value={title}
              onChange={e => setTitle(e.target.value)}
              className='input'
              placeholder='Enter task title'
            />
          </div>

          <div>
            <label
              htmlFor='description'
              className='block text-sm font-medium text-gray-700 mb-1'
            >
              Description
            </label>
            <textarea
              id='description'
              value={description}
              onChange={e => setDescription(e.target.value)}
              className='input resize-none h-20'
              placeholder='Enter task description'
            />
          </div>

          <div>
            <label
              htmlFor='priority'
              className='block text-sm font-medium text-gray-700 mb-1'
            >
              Priority
            </label>
            <select
              id='priority'
              value={priority}
              onChange={e => setPriority(e.target.value as Task['priority'])}
              className='input'
            >
              <option value='low'>Low</option>
              <option value='medium'>Medium</option>
              <option value='high'>High</option>
            </select>
          </div>

          <div>
            <label
              htmlFor='dueDate'
              className='block text-sm font-medium text-gray-700 mb-1'
            >
              Due Date
            </label>
            <input
              id='dueDate'
              type='date'
              value={dueDate}
              onChange={e => setDueDate(e.target.value)}
              className='input'
            />
          </div>

          <div className='flex justify-end space-x-3 pt-4'>
            <button type='button' onClick={onClose} className='btn-outline'>
              Cancel
            </button>
            <button type='submit' disabled={loading} className='btn-primary'>
              {loading ? 'Creating...' : 'Create Task'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
