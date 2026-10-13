import axios, { AxiosInstance, AxiosError, InternalAxiosRequestConfig } from 'axios';
import type { Provider, ProviderCreate, ProviderUpdate, ProviderTestResponse, PaginatedResponse, Session, SessionCreate, SessionUpdate, Message, MessageCreate, RequestLog, LogStats, User, HealthResponse, ReadyResponse } from '../types';

const API_BASE_URL = (import.meta as any).env?.VITE_API_BASE_URL || 'http://localhost:8000';

class ApiClient {
  private client: AxiosInstance;
  private accessToken: string | null = null;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        'Content-Type': 'application/json',
      },
      withCredentials: true,
    });

    this.client.interceptors.request.use(
      (config: InternalAxiosRequestConfig) => {
        if (this.accessToken) {
          config.headers.Authorization = `Bearer ${this.accessToken}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    this.client.interceptors.response.use(
      (response) => response,
      async (error: AxiosError) => {
        if (error.response?.status === 401) {
          this.clearToken();
          if (!window.location.pathname.includes('/login')) {
            window.location.href = '/login';
          }
        }
        return Promise.reject(error);
      }
    );
  }

  setToken(token: string | null) {
    this.accessToken = token;
  }

  clearToken() {
    this.accessToken = null;
  }

  getToken(): string | null {
    return this.accessToken;
  }

  async health(): Promise<HealthResponse> {
    const { data } = await this.client.get<HealthResponse>('/health');
    return data;
  }

  async ready(): Promise<ReadyResponse> {
    const { data } = await this.client.get<ReadyResponse>('/ready');
    return data;
  }

  async login(): Promise<{ authorization_url: string; state: string; nonce: string; pkce_verifier: string }> {
    const { data } = await this.client.get('/auth/login');
    return data;
  }

  async demoLogin(): Promise<{ message: string; user: User }> {
    const { data } = await this.client.post('/auth/demo-login');
    return data;
  }

  async logout(): Promise<{ logout_url: string }> {
    const { data } = await this.client.post('/auth/logout');
    return data;
  }

  async me(): Promise<User> {
    const { data } = await this.client.get<User>('/auth/me');
    return data;
  }

  async listProviders(params?: { page?: number; page_size?: number; enabled?: boolean }): Promise<PaginatedResponse<Provider>> {
    const { data } = await this.client.get<PaginatedResponse<Provider>>('/api/v1/providers', { params });
    return data;
  }

  async getProvider(id: string): Promise<Provider> {
    const { data } = await this.client.get<Provider>(`/api/v1/providers/${id}`);
    return data;
  }

  async createProvider(provider: ProviderCreate): Promise<Provider> {
    const { data } = await this.client.post<Provider>('/api/v1/providers', provider);
    return data;
  }

  async updateProvider(id: string, provider: ProviderUpdate): Promise<Provider> {
    const { data } = await this.client.patch<Provider>(`/api/v1/providers/${id}`, provider);
    return data;
  }

  async deleteProvider(id: string): Promise<void> {
    await this.client.delete(`/api/v1/providers/${id}`);
  }

  async getProviderHealth(id: string): Promise<Provider['health']> {
    const { data } = await this.client.get<Provider['health']>(`/api/v1/providers/${id}/health`);
    return data;
  }

  async testProvider(id: string): Promise<ProviderTestResponse> {
    const { data } = await this.client.post<ProviderTestResponse>(`/api/v1/providers/${id}/test`);
    return data;
  }

  async listSessions(params?: { page?: number; page_size?: number }): Promise<PaginatedResponse<Session>> {
    const { data } = await this.client.get<PaginatedResponse<Session>>('/api/v1/sessions', { params });
    return data;
  }

  async getSession(id: string): Promise<Session> {
    const { data } = await this.client.get<Session>(`/api/v1/sessions/${id}`);
    return data;
  }

  async createSession(session: SessionCreate): Promise<Session> {
    const { data } = await this.client.post<Session>('/api/v1/sessions', session);
    return data;
  }

  async updateSession(id: string, session: SessionUpdate): Promise<Session> {
    const { data } = await this.client.patch<Session>(`/api/v1/sessions/${id}`, session);
    return data;
  }

  async deleteSession(id: string): Promise<void> {
    await this.client.delete(`/api/v1/sessions/${id}`);
  }

  async addMessage(sessionId: string, message: MessageCreate): Promise<Message> {
    const { data } = await this.client.post<Message>(`/api/v1/sessions/${sessionId}/messages`, message);
    return data;
  }

  async exportSession(id: string): Promise<Blob> {
    const { data } = await this.client.get(`/api/v1/sessions/${id}/export`, { responseType: 'blob' });
    return data;
  }

  async listLogs(params?: {
    page?: number;
    page_size?: number;
    provider_id?: string;
    session_id?: string;
    status_code?: number;
    error_only?: boolean;
    hours?: number;
  }): Promise<PaginatedResponse<RequestLog>> {
    const { data } = await this.client.get<PaginatedResponse<RequestLog>>('/api/v1/logs', { params });
    return data;
  }

  async getLogStats(hours?: number): Promise<LogStats> {
    const { data } = await this.client.get<LogStats>('/api/v1/logs/stats', { params: { hours } });
    return data;
  }
}

export const api = new ApiClient();