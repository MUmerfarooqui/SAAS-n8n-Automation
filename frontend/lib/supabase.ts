// frontend/lib/supabase.ts
import { createClient } from '@supabase/supabase-js'

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!

export const supabase = createClient(supabaseUrl, supabaseAnonKey)

export async function getSupabaseJwt(): Promise<string> {
  const { data, error } = await supabase.auth.getSession()
  if (error || !data.session) throw new Error('No active session')
  return data.session.access_token
}

// Types for our database
export type Profile = {
  id: string
  email: string
  full_name: string | null
  subscription_status: 'free' | 'pro' | 'cancelled'
  stripe_customer_id: string | null
  subscription_ends_at: string | null
  created_at: string
  updated_at: string
}

export type Workflow = {
  id: string
  user_id: string
  name: string
  description: string | null
  n8n_workflow_id: string | null
  n8n_webhook_url: string | null
  workflow_config: any
  status: 'active' | 'paused'
  created_at: string
  updated_at: string
}

export type Execution = {
  id: string
  workflow_id: string
  user_id: string
  status: 'success' | 'error' | 'running'
  started_at: string
  finished_at: string | null
  error_message: string | null
  execution_data: any
}