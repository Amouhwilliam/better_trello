const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function getToken(): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(/(?:^|;\s*)bt_token=([^;]*)/);
  return match ? decodeURIComponent(match[1]) : null;
}

export interface User {
  id: string;
  fullname: string;
  email: string;
  created_at: string;
  updated_at: string;
}

export interface CreateUserPayload {
  fullname: string;
  email: string;
  password: string;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getToken();
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(init?.headers ?? {}),
    },
  });
  if (res.status === 401) {
    // Token expired or invalid — clear cookie and redirect to login
    document.cookie = "bt_token=; path=/; max-age=0";
    window.location.href = "/";
    throw new Error("Session expired. Please sign in again.");
  }
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(error.detail ?? `HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export interface Project {
  id: string;
  title: string;
  deadline: string;
  completed: boolean;
  auto_complete: boolean;
  owner_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface CreateProjectPayload {
  title: string;
  deadline: string;
  owner_id?: string;
}

export type TaskStatus = "todo" | "in_progress" | "completed";

export interface Task {
  id: string;
  title: string;
  description: string | null;
  deadline: string;
  status: TaskStatus;
  completed: boolean;
  project_id: string | null;
  assignee_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface CreateTaskPayload {
  title: string;
  deadline: string;
  description?: string;
  project_id?: string;
}

export const api = {
  users: {
    me: () => request<User>("/users/me"),
    list: () => request<User[]>("/users"),
    get: (id: string) => request<User>(`/users/${id}`),
    create: (payload: CreateUserPayload) =>
      request<User>("/users", { method: "POST", body: JSON.stringify(payload) }),
  },
  projects: {
    list: () => request<Project[]>("/projects"),
    get: (id: string) => request<Project>(`/projects/${id}`),
    create: (payload: CreateProjectPayload) =>
      request<Project>("/projects", { method: "POST", body: JSON.stringify(payload) }),
    update: (id: string, payload: Partial<{ title: string; deadline: string; auto_complete: boolean }>) =>
      request<Project>(`/projects/${id}`, { method: "PUT", body: JSON.stringify(payload) }),
    complete: (id: string) =>
      request<Project>(`/projects/${id}/complete`, { method: "PATCH" }),
    tasks: (id: string) => request<Task[]>(`/projects/${id}/tasks`),
  },
  tasks: {
    list: (params?: { completed?: boolean; overdue?: boolean; project_id?: string }) => {
      const qs = new URLSearchParams();
      if (params?.completed !== undefined) qs.set("completed", String(params.completed));
      if (params?.overdue !== undefined) qs.set("overdue", String(params.overdue));
      if (params?.project_id) qs.set("project_id", params.project_id);
      const query = qs.toString();
      return request<Task[]>(`/tasks${query ? `?${query}` : ""}`);
    },
    create: (payload: CreateTaskPayload) =>
      request<Task>("/tasks", { method: "POST", body: JSON.stringify(payload) }),
    update: (taskId: string, payload: Partial<{ title: string; description: string; deadline: string }>) =>
      request<Task>(`/tasks/${taskId}`, { method: "PUT", body: JSON.stringify(payload) }),
    updateStatus: (taskId: string, status: TaskStatus) =>
      request<Task>(`/tasks/${taskId}/status`, { method: "PATCH", body: JSON.stringify({ status }) }),
    assign: (taskId: string, userId: string) =>
      request<Task>(`/tasks/${taskId}/assign/${userId}`, { method: "PATCH" }),
    unassign: (taskId: string) =>
      request<Task>(`/tasks/${taskId}/unassign`, { method: "PATCH" }),
    linkProject: (taskId: string, projectId: string) =>
      request<Task>(`/projects/${projectId}/tasks/${taskId}/link`, { method: "POST" }),
    unlinkProject: (taskId: string, projectId: string) =>
      request<Task>(`/projects/${projectId}/tasks/${taskId}/unlink`, { method: "DELETE" }),
  },
};
