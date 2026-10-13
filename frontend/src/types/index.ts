export interface Provider {
  id: string;
  name: string;
  type: 'openai-compatible' | 'anthropic' | 'gemini' | 'ollama';
  base_url: string;
  api_key?: string;
  model?: string;
  enabled: boolean;
  priority: number;
  timeout_seconds: number;
  max_retries: number;
  extra_config?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  health?: ProviderHealth;
}

export interface ProviderHealth {
  provider_id: string;
  healthy: boolean;
  latency_ms?: number;
  error?: string;
  circuit_open: boolean;
  consecutive_failures: number;
  checked_at: string;
}

export interface ProviderCreate {
  name: string;
  type: 'openai-compatible' | 'anthropic' | 'gemini' | 'ollama';
  base_url: string;
  api_key?: string;
  model?: string;
  enabled?: boolean;
  priority?: number;
  timeout_seconds?: number;
  max_retries?: number;
  extra_config?: Record<string, unknown>;
}

export interface ProviderUpdate {
  name?: string;
  type?: 'openai-compatible' | 'anthropic' | 'gemini' | 'ollama';
  base_url?: string;
  api_key?: string;
  model?: string;
  enabled?: boolean;
  priority?: number;
  timeout_seconds?: number;
  max_retries?: number;
  extra_config?: Record<string, unknown>;
}

export interface ProviderTestResponse {
  success: boolean;
  latency_ms?: number;
  error?: string;
  models: string[];
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface Session {
  id: string;
  title?: string;
  user_id: string;
  model?: string;
  provider_id?: string;
  metadata?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  message_count: number;
  messages?: Message[];
}

export interface Message {
  id: string;
  session_id: string;
  role: 'user' | 'assistant' | 'system' | 'tool';
  content: string;
  tool_calls?: Array<Record<string, unknown>>;
  tool_call_id?: string;
  metadata?: Record<string, unknown>;
  created_at: string;
}

export interface SessionCreate {
  title?: string;
  model?: string;
  provider_id?: string;
  metadata?: Record<string, unknown>;
}

export interface SessionUpdate {
  title?: string;
  metadata?: Record<string, unknown>;
}

export interface MessageCreate {
  role: 'user' | 'assistant' | 'system' | 'tool';
  content: string;
  tool_calls?: Array<Record<string, unknown>>;
  tool_call_id?: string;
  metadata?: Record<string, unknown>;
}

export interface RequestLog {
  id: string;
  provider_id?: string;
  provider_name?: string;
  session_id?: string;
  method: string;
  path: string;
  request_body?: Record<string, unknown>;
  response_status?: number;
  response_body?: Record<string, unknown>;
  latency_ms?: number;
  error_message?: string;
  created_at: string;
}

export interface LogStats {
  total_requests: number;
  successful_requests: number;
  failed_requests: number;
  avg_latency_ms: number;
  requests_by_provider: Array<{
    provider_id: string;
    count: number;
    avg_latency_ms: number;
  }>;
  requests_by_status: Array<{
    status: number;
    count: number;
  }>;
  error_rate: number;
}

export interface User {
  sub: string;
  email?: string;
  preferred_username?: string;
  roles: string[];
}

export interface HealthResponse {
  status: string;
  version: string;
  environment: string;
  demo_mode: boolean;
}

export interface ReadyResponse {
  status: string;
  database: boolean;
  providers_loaded: number;
  providers_healthy: number;
}