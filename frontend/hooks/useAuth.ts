'use client'

import { useEffect, useMemo, useRef, useState } from 'react'
import type { User, Session } from '@supabase/supabase-js'
import { supabase, type Profile } from '@/lib/supabase'

export function useAuth() {
  const [user, setUser] = useState<User | null>(null)
  const [session, setSession] = useState<Session | null>(null)
  const [profile, setProfile] = useState<Profile | null>(null)
  const [loading, setLoading] = useState(true)
  const mounted = useRef(true)

  useEffect(() => {
    mounted.current = true

    const init = async () => {
      const { data } = await supabase.auth.getSession()
      if (!mounted.current) return
      setSession(data.session)
      setUser(data.session?.user ?? null)
      if (data.session?.user) {
        await fetchProfile(data.session.user.id)
      }
      if (mounted.current) setLoading(false)
    }

    init()

    const { data: sub } = supabase.auth.onAuthStateChange(async (_event, newSession) => {
      if (!mounted.current) return
      setSession(newSession)
      setUser(newSession?.user ?? null)
      if (newSession?.user) {
        // Avoid refetch if we already have the same profile loaded
        if (profile?.id !== newSession.user.id) {
          await fetchProfile(newSession.user.id)
        }
      } else {
        setProfile(null)
      }
      if (mounted.current) setLoading(false)
    })

    return () => {
      mounted.current = false
      sub.subscription.unsubscribe()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const fetchProfile = async (userId: string) => {
    try {
      const { data, error } = await supabase
        .from('profiles')
        .select('*')
        .eq('id', userId)
        .single()

      if (error) {
        // If profile doesn't exist, create it
        if (error.code === 'PGRST116') {
          await createProfile(userId)
          return
        }
        console.error('Error fetching profile:', error)
        return
      }
      if (mounted.current) setProfile(data)
    } catch (err) {
      console.error('Error fetching profile:', err)
    }
  }

  const createProfile = async (userId: string) => {
    try {
      // Get user data from auth
      const { data: authUser } = await supabase.auth.getUser()
      
      const profileData = {
        id: userId,
        email: authUser.user?.email || '',
        full_name: authUser.user?.user_metadata?.full_name || null,
        subscription_status: 'free' as const,
        stripe_customer_id: null,
        subscription_ends_at: null,
      }

      const { data, error } = await supabase
        .from('profiles')
        .insert(profileData)
        .select()
        .single()

      if (error) {
        console.error('Error creating profile:', error)
        return
      }

      if (mounted.current) setProfile(data)
    } catch (err) {
      console.error('Error creating profile:', err)
    }
  }

  const signIn = async (email: string, password: string) => {
    const { data, error } = await supabase.auth.signInWithPassword({ email, password })
    return { data, error }
  }

  const signUp = async (email: string, password: string, fullName: string) => {
    const { data, error } = await supabase.auth.signUp({
      email,
      password,
      options: { data: { full_name: fullName } }
    })

    // If signup successful and user is confirmed, create profile
    if (data.user && !error && data.user.email_confirmed_at) {
      await createProfile(data.user.id)
    }

    return { data, error }
  }

  const signOut = async () => {
    const { error } = await supabase.auth.signOut()
    return { error }
  }

  const getJwt = async (): Promise<string> => {
    const { data, error } = await supabase.auth.getSession()
    if (error || !data.session) throw new Error('No active session')
    return data.session.access_token
  }

  return useMemo(() => ({
    user,
    session,
    profile,
    loading,
    signIn,
    signUp,
    signOut,
    getJwt,
    isAuthenticated: !!user,
  }), [user, session, profile, loading])
}