// lib/workflowTemplates.ts
export interface WorkflowTemplate {
  id: string
  name: string
  description: string
  category: string
  difficulty: 'beginner' | 'intermediate' | 'advanced'
  estimatedSetupTime: number // minutes
  requiredIntegrations: string[]
  tags: string[]
  icon: string
  useCase: string
  config: {
    trigger: any
    steps: any[]
    settings: any
  }
}

// Pre-built workflow templates
export const WORKFLOW_TEMPLATES: WorkflowTemplate[] = [
  {
    id: 'gmail-ai-responder',
    name: 'Gmail AI Auto Responder',
    description: 'Automatically generate draft replies to incoming emails using AI',
    category: 'email-automation',
    difficulty: 'beginner',
    estimatedSetupTime: 10,
    requiredIntegrations: ['gmail', 'openai'],
    tags: ['email', 'ai', 'productivity'],
    icon: '🤖',
    useCase: 'Save time responding to emails. AI creates professional draft replies that you can review and send.',
    config: {
      trigger: { type: 'gmail_new_email', filter: 'unread' },
      steps: [
        { action: 'analyze_email', ai_enabled: true },
        { action: 'generate_reply', model: 'gpt-4' },
        { action: 'create_draft', destination: 'gmail' },
      ],
      settings: {
        check_interval: '5_minutes',
        temperature: 0.7,
        max_tokens: 500,
        reply_tone: 'professional_friendly',
      },
    },
  },

  // NEW: Gmail Summary Agent
  {
    id: 'gmail-summary',
    name: 'Gmail Summary Automation',
    description: 'Create a daily AI summary of your inbox and highlight important messages',
    category: 'productivity',
    difficulty: 'beginner',
    estimatedSetupTime: 3,
    requiredIntegrations: ['gmail', 'openai'],
    tags: ['email', 'ai', 'productivity'],
    icon: '📧',
    useCase: 'Get a daily summary of your emails with key highlights and action items.',
    config: {
      // Daily at 23:00. Adjust later in UI if needed.
      trigger: { type: 'schedule', cron: '0 23 * * *' },
      steps: [
        { action: 'fetch_emails', query: 'newer_than:1d in:inbox' },
        { action: 'rank_importance', ai_enabled: true },
        { action: 'generate_summary', model: 'gpt-4' },
        { action: 'create_draft', destination: 'gmail', subject: 'Daily Email Summary' },
      ],
      settings: {
        timezone: 'user_timezone',
        include_attachments: false,
        extract_senders: true,
        max_threads: 200,
      },
    },
  },

  {
    id: 'whatsapp-customer-support',
    name: 'WhatsApp Customer Support Bot',
    description: 'Auto-respond to common WhatsApp Business messages with helpful information',
    category: 'customer-service',
    difficulty: 'intermediate',
    estimatedSetupTime: 10,
    requiredIntegrations: ['whatsapp_business'],
    tags: ['customer-service', 'automation', 'messaging'],
    icon: '💬',
    useCase: 'Provide instant responses to common customer questions on WhatsApp Business.',
    config: {
      trigger: { type: 'whatsapp_message' },
      steps: [
        { action: 'analyze_message', ai_enabled: true },
        { action: 'check_knowledge_base' },
        { action: 'send_response', fallback_to_human: true },
      ],
      settings: { auto_response: true, business_hours_only: false },
    },
  },

  {
    id: 'social-media-scheduler',
    name: 'Social Media Content Scheduler',
    description: 'Schedule and post content across multiple social media platforms',
    category: 'marketing',
    difficulty: 'intermediate',
    estimatedSetupTime: 15,
    requiredIntegrations: ['google_sheets', 'twitter', 'linkedin'],
    tags: ['social-media', 'scheduling', 'marketing'],
    icon: '📱',
    useCase: 'Manage your social media presence with automated posting from a content calendar.',
    config: {
      trigger: { type: 'schedule', cron: '0 9,13,17 * * *' },
      steps: [
        { action: 'read_content_calendar', source: 'google_sheets' },
        { action: 'post_to_platforms', platforms: ['twitter', 'linkedin'] },
        { action: 'mark_as_posted' },
      ],
      settings: { timezone: 'user_timezone', skip_weekends: true },
    },
  },

  {
    id: 'expense-tracker',
    name: 'Receipt to Expense Tracker',
    description: 'Automatically process receipt photos and add expenses to your tracking sheet',
    category: 'finance',
    difficulty: 'advanced',
    estimatedSetupTime: 20,
    requiredIntegrations: ['gmail', 'google_sheets', 'ocr_service'],
    tags: ['finance', 'receipts', 'expense-tracking'],
    icon: '🧾',
    useCase: 'Streamline expense reporting by automatically processing receipt emails and photos.',
    config: {
      trigger: { type: 'gmail', filter: 'subject:receipt OR has:attachment' },
      steps: [
        { action: 'extract_attachments' },
        { action: 'ocr_processing' },
        { action: 'parse_expense_data' },
        { action: 'add_to_sheet', sheet_id: 'user_configured' },
      ],
      settings: { currency: 'USD', categorize_expenses: true },
    },
  },

  {
    id: 'meeting-notes-automation',
    name: 'Meeting Notes to Action Items',
    description: 'Convert meeting transcripts into organized action items and follow-ups',
    category: 'productivity',
    difficulty: 'advanced',
    estimatedSetupTime: 12,
    requiredIntegrations: ['google_drive', 'slack', 'calendar'],
    tags: ['meetings', 'productivity', 'ai-processing'],
    icon: '📝',
    useCase: 'Never lose track of meeting decisions. Automatically extract and distribute action items.',
    config: {
      trigger: { type: 'calendar_event', event: 'meeting_ended' },
      steps: [
        { action: 'fetch_meeting_transcript' },
        { action: 'extract_action_items', ai_enabled: true },
        { action: 'create_tasks' },
        { action: 'notify_participants', via: 'slack' },
      ],
      settings: { auto_create_calendar_events: true, reminder_frequency: 'daily' },
    },
  },
]

export function getTemplatesByCategory() {
  const categories = [...new Set(WORKFLOW_TEMPLATES.map((t) => t.category))]
  return categories.reduce((acc, category) => {
    acc[category] = WORKFLOW_TEMPLATES.filter((t) => t.category === category)
    return acc
  }, {} as Record<string, WorkflowTemplate[]>)
}

export function getTemplateById(id: string) {
  return WORKFLOW_TEMPLATES.find((t) => t.id === id)
}
