// app/dashboard/page.tsx
'use client'

import { useAuth } from '@/hooks/useAuth'
import { useWorkflows } from '@/hooks/useWorkflows'
import { useRouter } from 'next/navigation'
import { useEffect, useState } from 'react'
import { WORKFLOW_TEMPLATES, getTemplatesByCategory, type WorkflowTemplate } from '@/lib/workflowTemplates'
import { getSupabaseJwt } from '@/lib/supabase'

type InstallResponse =
  | { needsAuth: true; authUrl: string; state: string; templateId: string }
  | { activated: true; workflowId: number }
  | { error: string }

export default function Dashboard() {
  const { user, profile, loading, signOut } = useAuth()
  const { workflows } = useWorkflows()
  const [selectedCategory, setSelectedCategory] = useState('all')
  const [installingId, setInstallingId] = useState<string | null>(null)
  const router = useRouter()

  const templatesByCategory = getTemplatesByCategory()
  const categories = Object.keys(templatesByCategory)

  useEffect(() => {
    if (!loading && !user) {
      router.push('/login')
    }
  }, [user, loading, router])

  const handleSignOut = async () => {
    await signOut()
    router.push('/login')
  }

  // Option B routing. Switch by template.id and call the namespaced endpoint.
  const handleInstallTemplate = async (template: WorkflowTemplate) => {
    try {
      setInstallingId(template.id)

      const token = await getSupabaseJwt()
      const api = process.env.NEXT_PUBLIC_API_URL
      if (!api) {
        alert('NEXT_PUBLIC_API_URL is not set')
        return
      }

      let url: string | null = null
      switch (template.id) {
        case 'gmail-ai-responder':
          url = `${api}/workflows/gmail-ai-responder/install`
          break
        case 'gmail-summary':
          url = `${api}/workflows/gmail-summary/install`
          break
        default:
          // fallback to generic if you keep it around on the backend
          url = `${api}/workflows/install`
      }

      const res = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        // For namespaced install endpoints we do not need a body
        body: url.endsWith('/install') && !url.endsWith('/workflows/install')
          ? undefined
          : JSON.stringify({ templateId: template.id }),
      })

      const data: InstallResponse = await res.json()

      if (!res.ok) {
        const msg = (data as any)?.error || 'Install failed'
        alert(msg)
        return
      }

      if ('needsAuth' in data && data.needsAuth && data.authUrl) {
        window.location.href = data.authUrl
        return
      }

      if ('activated' in data && data.activated) {
        alert('Workflow installed and activated')
        // router.refresh()
        return
      }

      alert('Unexpected response from server')
    } catch (err) {
      console.error(err)
      alert('Network or auth error')
    } finally {
      setInstallingId(null)
    }
  }

  const filteredTemplates = selectedCategory === 'all'
    ? WORKFLOW_TEMPLATES
    : templatesByCategory[selectedCategory] || []

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-lg">Loading...</div>
      </div>
    )
  }

  if (!user) {
    return null
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">
                SaaS Automation Platform
              </h1>
              <p className="text-gray-600">Welcome back, {profile?.full_name || user.email}</p>
            </div>
            <div className="flex items-center space-x-4">
              <span className="text-sm text-gray-500 bg-gray-100 px-3 py-1 rounded-full">
                Plan: {profile?.subscription_status || 'free'}
              </span>
              <button
                onClick={handleSignOut}
                className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-md text-sm font-medium"
              >
                Sign Out
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <div className="px-4 py-6 sm:px-0">

          {/* Stats Cards */}
          <div className="grid grid-cols-1 gap-5 sm:grid-cols-3 mb-8">
            <div className="bg-white overflow-hidden shadow rounded-lg">
              <div className="p-5">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <div className="w-8 h-8 bg-blue-500 rounded-md flex items-center justify-center">
                      <span className="text-white text-sm font-medium">W</span>
                    </div>
                  </div>
                  <div className="ml-5 w-0 flex-1">
                    <dl>
                      <dt className="text-sm font-medium text-gray-500 truncate">
                        Active Workflows
                      </dt>
                      <dd className="text-lg font-medium text-gray-900">
                        {workflows.filter(w => w.status === 'active').length}
                      </dd>
                    </dl>
                  </div>
                </div>
              </div>
            </div>

            <div className="bg-white overflow-hidden shadow rounded-lg">
              <div className="p-5">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <div className="w-8 h-8 bg-green-500 rounded-md flex items-center justify-center">
                      <span className="text-white text-sm font-medium">T</span>
                    </div>
                  </div>
                  <div className="ml-5 w-0 flex-1">
                    <dl>
                      <dt className="text-sm font-medium text-gray-500 truncate">
                        Available Templates
                      </dt>
                      <dd className="text-lg font-medium text-gray-900">
                        {WORKFLOW_TEMPLATES.length}
                      </dd>
                    </dl>
                  </div>
                </div>
              </div>
            </div>

            <div className="bg-white overflow-hidden shadow rounded-lg">
              <div className="p-5">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <div className="w-8 h-8 bg-purple-500 rounded-md flex items-center justify-center">
                      <span className="text-white text-sm font-medium">P</span>
                    </div>
                  </div>
                  <div className="ml-5 w-0 flex-1">
                    <dl>
                      <dt className="text-sm font-medium text-gray-500 truncate">
                        Plan
                      </dt>
                      <dd className="text-lg font-medium text-gray-900 capitalize">
                        {profile?.subscription_status || 'Free'}
                      </dd>
                    </dl>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* My Workflows Section */}
          {workflows.length > 0 && (
            <div className="bg-white overflow-hidden shadow rounded-lg mb-8">
              <div className="px-4 py-5 sm:p-6">
                <h2 className="text-lg font-medium text-gray-900 mb-6">My Workflows</h2>
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                  {workflows.map((workflow) => (
                    <div
                      key={workflow.id}
                      className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow bg-white"
                    >
                      <div className="flex justify-between items-start mb-3">
                        <h3 className="text-lg font-medium text-gray-900 truncate">
                          {workflow.name}
                        </h3>
                        <span
                          className={`px-2 py-1 text-xs font-medium rounded-full ${
                            workflow.status === 'active'
                              ? 'bg-green-100 text-green-800'
                              : 'bg-gray-100 text-gray-800'
                          }`}
                        >
                          {workflow.status}
                        </span>
                      </div>

                      {workflow.description && (
                        <p className="text-gray-600 text-sm mb-3">
                          {workflow.description}
                        </p>
                      )}

                      <div className="flex justify-between items-center">
                        <span className="text-xs text-gray-500">
                          Created: {new Date(workflow.created_at).toLocaleDateString()}
                        </span>
                        <button className="text-blue-600 hover:text-blue-800 text-sm font-medium">
                          Configure →
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Browse Templates Section */}
          <div className="bg-white overflow-hidden shadow rounded-lg">
            <div className="px-4 py-5 sm:p-6">
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-lg font-medium text-gray-900">Browse Workflow Templates</h2>
                <div className="flex space-x-2">
                  <button
                    onClick={() => setSelectedCategory('all')}
                    className={`px-3 py-1 text-sm rounded-full ${
                      selectedCategory === 'all'
                        ? 'bg-blue-100 text-blue-800'
                        : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                    }`}
                  >
                    All
                  </button>
                  {categories.map((category) => (
                    <button
                      key={category}
                      onClick={() => setSelectedCategory(category)}
                      className={`px-3 py-1 text-sm rounded-full capitalize ${
                        selectedCategory === category
                          ? 'bg-blue-100 text-blue-800'
                          : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                      }`}
                    >
                      {category.replace('-', ' ')}
                    </button>
                  ))}
                </div>
              </div>

              <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
                {filteredTemplates.map((template) => (
                  <div
                    key={template.id}
                    className="border border-gray-200 rounded-lg p-6 hover:shadow-lg transition-shadow bg-white"
                  >
                    <div className="flex items-start justify-between mb-4">
                      <div className="flex items-center space-x-3">
                        <span className="text-2xl">{template.icon}</span>
                        <div>
                          <h3 className="text-lg font-medium text-gray-900">
                            {template.name}
                          </h3>
                          <span
                            className={`inline-block px-2 py-1 text-xs font-medium rounded-full mt-1 ${
                              template.difficulty === 'beginner'
                                ? 'bg-green-100 text-green-800'
                                : template.difficulty === 'intermediate'
                                ? 'bg-yellow-100 text-yellow-800'
                                : 'bg-red-100 text-red-800'
                            }`}
                          >
                            {template.difficulty}
                          </span>
                        </div>
                      </div>
                    </div>

                    <p className="text-gray-600 text-sm mb-4 leading-relaxed">
                      {template.description}
                    </p>

                    <div className="mb-4">
                      <p className="text-gray-700 text-sm font-medium mb-2">Use Case:</p>
                      <p className="text-gray-600 text-sm">{template.useCase}</p>
                    </div>

                    <div className="mb-4">
                      <p className="text-gray-700 text-sm font-medium mb-2">Required Integrations:</p>
                      <div className="flex flex-wrap gap-1">
                        {template.requiredIntegrations.map((integration) => (
                          <span
                            key={integration}
                            className="inline-block bg-blue-50 text-blue-700 px-2 py-1 text-xs rounded"
                          >
                            {integration.replace('_', ' ')}
                          </span>
                        ))}
                      </div>
                    </div>

                    <div className="flex justify-between items-center">
                      <span className="text-xs text-gray-500">
                        Setup: ~{template.estimatedSetupTime} min
                      </span>
                      <button
                        onClick={() => handleInstallTemplate(template)}
                        disabled={installingId === template.id}
                        className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md text-sm font-medium disabled:opacity-60"
                      >
                        {installingId === template.id ? 'Installing...' : 'Install'}
                      </button>
                    </div>
                  </div>
                ))}
              </div>

              {filteredTemplates.length === 0 && (
                <div className="text-center py-8">
                  <p className="text-gray-500">No templates found in this category.</p>
                </div>
              )}
            </div>
          </div>

        </div>
      </main>
    </div>
  )
}
