// Global TypeScript types for AgenticP1

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: "superadmin" | "admin" | "manager" | "viewer";
  organization_id: string;
  has_api_key: boolean;
}

export interface Organization {
  id: string;
  name: string;
  slug: string;
  plan: "starter" | "growth" | "pro" | "enterprise";
  monthly_minutes_limit: number;
  is_active: boolean;
}

export interface AgentConfig {
  id: string;
  organization_id: string;
  name: string;
  description: string;
  industry: string;
  personality: "friendly" | "professional" | "casual";
  custom_prompt: string | null;
  greeting_message: string;
  language: string;
  voice_id: string;
  tools_enabled: Record<string, boolean>;
  escalation_rules: {
    sentiment_threshold: number;
    max_turns_before_escalation: number;
    keywords: string[];
  };
  business_hours: Record<string, { open: string; close: string }> | null;
  faqs: Array<{ question: string; answer: string }> | null;
  phone_number: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Call {
  id: string;
  direction: "inbound" | "outbound";
  caller_number: string | null;
  called_number: string | null;
  status: "initiated" | "active" | "completed" | "failed" | "transferred";
  duration_seconds: number | null;
  sentiment_label: "positive" | "neutral" | "negative" | null;
  sentiment_score: number | null;
  resolution: "resolved" | "escalated" | "abandoned" | null;
  summary: string | null;
  created_at: string;
  transcript_turns?: TranscriptTurn[];
}

export interface TranscriptTurn {
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: string;
}

export interface KnowledgeDocument {
  id: string;
  filename: string;
  source_url: string | null;
  doc_type: "file" | "url";
  status: "processing" | "ready" | "error";
  chunk_count: number;
  error_message: string | null;
  created_at: string;
}

export interface DashboardStats {
  calls_today: number;
  active_calls: number;
  avg_duration_seconds: number;
  resolution_rate_percent: number;
  minutes_used_this_month: number;
}

export interface BillingUsage {
  plan: string;
  plan_price_usd: number;
  minutes_used: number;
  minutes_limit: number;
  minutes_remaining: number;
  overage_minutes: number;
}

export interface CallVolumeData {
  date: string;
  calls: number;
}

export interface SentimentData {
  positive?: number;
  neutral?: number;
  negative?: number;
}

export interface ApiResponse<T> {
  data: T;
  total?: number;
  limit?: number;
  offset?: number;
}

export interface AuthTokens {
  access_token: string;
  token_type: string;
  user_id: string;
  organization_id: string;
  role: string;
}
