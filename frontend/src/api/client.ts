const API_BASE = import.meta.env.VITE_API_URL || "";

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  token?: string | null
): Promise<T> {
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = headers["Content-Type"] || "application/json";
  }

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, err.detail || "Request failed");
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  register: (data: { email: string; password: string; full_name: string }) =>
    request("/api/v1/auth/register", { method: "POST", body: JSON.stringify(data) }),

  login: (data: { email: string; password: string }) =>
    request<{ access_token: string }>("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  me: (token: string) => request<import("../types").User>("/api/v1/auth/me", {}, token),

  getProjects: (token: string) =>
    request<{ items: import("../types").Project[]; total: number }>(
      "/api/v1/projects",
      {},
      token
    ),

  createProject: (token: string, data: Partial<import("../types").Project>) =>
    request<import("../types").Project>("/api/v1/projects", {
      method: "POST",
      body: JSON.stringify(data),
    }, token),

  getProject: (token: string, id: number) =>
    request<import("../types").Project>(`/api/v1/projects/${id}`, {}, token),

  deleteProject: (token: string, id: number) =>
    request(`/api/v1/projects/${id}`, { method: "DELETE" }, token),

  uploadDocument: (token: string, projectId: number, file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<import("../types").Document>(
      `/api/v1/projects/${projectId}/documents`,
      { method: "POST", body: form },
      token
    );
  },

  getDocuments: (token: string, projectId: number) =>
    request<import("../types").Document[]>(
      `/api/v1/projects/${projectId}/documents`,
      {},
      token
    ),

  startAnalysis: (token: string, projectId: number, documentId: number, apiKey?: string) =>
    request(`/api/v1/projects/${projectId}/analysis/run`, {
      method: "POST",
      body: JSON.stringify({ document_id: documentId, ...(apiKey ? { api_key: apiKey } : {}) }),
    }, token),

  getAnalysisStatus: (token: string, projectId: number) =>
    request<import("../types").AnalysisStatus>(
      `/api/v1/projects/${projectId}/analysis/status`,
      {},
      token
    ),

  getClaims: (token: string, projectId: number) =>
    request<{ items: import("../types").Claim[]; total: number }>(
      `/api/v1/projects/${projectId}/claims`,
      {},
      token
    ),

  getClaim: (token: string, projectId: number, claimId: number) =>
    request<import("../types").Claim>(
      `/api/v1/projects/${projectId}/claims/${claimId}`,
      {},
      token
    ),

  updateClaimCategory: (token: string, projectId: number, claimId: number, category: string) =>
    request<import("../types").Claim>(
      `/api/v1/projects/${projectId}/claims/${claimId}/category`,
      { method: "PATCH", body: JSON.stringify({ category }) },
      token
    ),

  updateEvidenceRelevance: (
    token: string,
    projectId: number,
    claimId: number,
    evidenceId: number,
    is_relevant: boolean
  ) =>
    request<import("../types").Claim>(
      `/api/v1/projects/${projectId}/claims/${claimId}/evidence/${evidenceId}`,
      { method: "PATCH", body: JSON.stringify({ is_relevant }) },
      token
    ),

  getDashboard: (token: string, projectId: number) =>
    request<import("../types").DashboardMetrics>(
      `/api/v1/projects/${projectId}/dashboard`,
      {},
      token
    ),

  downloadReport: (token: string, projectId: number) => {
    const headers: Record<string, string> = { Authorization: `Bearer ${token}` };
    return fetch(`${API_BASE}/api/v1/projects/${projectId}/reports/download`, { headers });
  },

  health: () => request<{ status: string; llm_enabled: boolean }>("/health"),
};

export { ApiError };
