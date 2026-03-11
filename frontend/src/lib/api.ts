import axios, { AxiosInstance, AxiosRequestConfig } from "axios";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

class ApiClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: `${API_BASE}/api/v1`,
      headers: { "Content-Type": "application/json" },
    });

    // Attach JWT token to every request
    this.client.interceptors.request.use((config) => {
      if (typeof window !== "undefined") {
        const token = localStorage.getItem("access_token");
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
      }
      return config;
    });

    // Handle 401 globally
    this.client.interceptors.response.use(
      (res) => res,
      (err) => {
        if (err.response?.status === 401 && typeof window !== "undefined") {
          localStorage.removeItem("access_token");
          window.location.href = "/auth/login";
        }
        return Promise.reject(err);
      }
    );
  }

  // Auth
  async register(data: {
    email: string;
    password: string;
    full_name: string;
    organization_name: string;
  }) {
    const res = await this.client.post("/auth/register", data);
    return res.data;
  }

  async login(email: string, password: string) {
    const res = await this.client.post("/auth/login", { email, password });
    const tokens = res.data;
    if (typeof window !== "undefined") {
      localStorage.setItem("access_token", tokens.access_token);
    }
    return tokens;
  }

  async getMe() {
    const res = await this.client.get("/auth/me");
    return res.data;
  }

  async generateApiKey() {
    const res = await this.client.post("/auth/api-key");
    return res.data;
  }

  async revokeApiKey() {
    const res = await this.client.delete("/auth/api-key");
    return res.data;
  }

  // Calls
  async listCalls(params?: {
    limit?: number;
    offset?: number;
    status?: string;
    sentiment?: string;
  }) {
    const res = await this.client.get("/calls/", { params });
    return res.data;
  }

  async getCall(id: string) {
    const res = await this.client.get(`/calls/${id}`);
    return res.data;
  }

  async initiateCall(data: { to_number: string; agent_id: string }) {
    const res = await this.client.post("/calls/initiate", data);
    return res.data;
  }

  // Agents
  async listAgents() {
    const res = await this.client.get("/agents/");
    return res.data;
  }

  async getAgent(id: string) {
    const res = await this.client.get(`/agents/${id}`);
    return res.data;
  }

  async createAgent(data: Record<string, unknown>) {
    const res = await this.client.post("/agents/", data);
    return res.data;
  }

  async updateAgent(id: string, data: Record<string, unknown>) {
    const res = await this.client.patch(`/agents/${id}`, data);
    return res.data;
  }

  async deleteAgent(id: string) {
    const res = await this.client.delete(`/agents/${id}`);
    return res.data;
  }

  // Analytics
  async getDashboardStats() {
    const res = await this.client.get("/analytics/dashboard");
    return res.data;
  }

  async getCallVolume(days: number = 30) {
    const res = await this.client.get("/analytics/call-volume", {
      params: { days },
    });
    return res.data;
  }

  async getSentimentDistribution() {
    const res = await this.client.get("/analytics/sentiment");
    return res.data;
  }

  async getBillingUsage() {
    const res = await this.client.get("/analytics/billing");
    return res.data;
  }

  // Knowledge Base
  async listDocuments() {
    const res = await this.client.get("/knowledge/");
    return res.data;
  }

  async uploadDocument(file: File) {
    const formData = new FormData();
    formData.append("file", file);
    const res = await this.client.post("/knowledge/upload", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    return res.data;
  }

  async addUrl(url: string) {
    const res = await this.client.post("/knowledge/url", { url });
    return res.data;
  }

  async searchKnowledgeBase(query: string, top_k: number = 5) {
    const res = await this.client.post("/knowledge/search", { query, top_k });
    return res.data;
  }

  async deleteDocument(id: string) {
    const res = await this.client.delete(`/knowledge/${id}`);
    return res.data;
  }

  logout() {
    if (typeof window !== "undefined") {
      localStorage.removeItem("access_token");
      window.location.href = "/auth/login";
    }
  }
}

export const api = new ApiClient();
