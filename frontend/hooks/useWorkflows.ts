// hooks/useWorkflows.ts
'use client'

import { useState, useEffect } from 'react'
import { supabase, type Workflow } from '@/lib/supabase'
import { useAuth } from './useAuth'

export function useWorkflows() {
  const [workflows, setWorkflows] = useState<Workflow[]>([])
  const [loading, setLoading] = useState(true)
  const { user } = useAuth()

  useEffect(() => {
    if (user) {
      fetchWorkflows()
    }
  }, [user])

  const fetchWorkflows = async () => {
    try {
      setLoading(true)
      const { data, error } = await supabase
        .from('workflows')
        .select('*')
        .order('created_at', { ascending: false })

      if (error) {
        console.error('Error fetching workflows:', error)
        return
      }

      setWorkflows(data || [])
    } catch (error) {
      console.error('Error fetching workflows:', error)
    } finally {
      setLoading(false)
    }
  }

  const createWorkflow = async (name: string, description: string) => {
    if (!user) return { error: 'Not authenticated' }

    try {
      const { data, error } = await supabase
        .from('workflows')
        .insert({
          user_id: user.id,
          name,
          description,
          status: 'active'
        })
        .select()
        .single()

      if (error) {
        console.error('Error creating workflow:', error)
        return { error }
      }

      // Add to local state
      setWorkflows(prev => [data, ...prev])
      return { data }
    } catch (error) {
      console.error('Error creating workflow:', error)
      return { error }
    }
  }

  const updateWorkflow = async (id: string, updates: Partial<Workflow>) => {
    try {
      const { data, error } = await supabase
        .from('workflows')
        .update(updates)
        .eq('id', id)
        .select()
        .single()

      if (error) {
        console.error('Error updating workflow:', error)
        return { error }
      }

      // Update local state
      setWorkflows(prev => 
        prev.map(w => w.id === id ? { ...w, ...data } : w)
      )
      return { data }
    } catch (error) {
      console.error('Error updating workflow:', error)
      return { error }
    }
  }

  const deleteWorkflow = async (id: string) => {
    try {
      const { error } = await supabase
        .from('workflows')
        .delete()
        .eq('id', id)

      if (error) {
        console.error('Error deleting workflow:', error)
        return { error }
      }

      // Remove from local state
      setWorkflows(prev => prev.filter(w => w.id !== id))
      return { success: true }
    } catch (error) {
      console.error('Error deleting workflow:', error)
      return { error }
    }
  }

  return {
    workflows,
    loading,
    createWorkflow,
    updateWorkflow,
    deleteWorkflow,
    refetch: fetchWorkflows
  }
}