const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

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
  const res = await fetch(`${API_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
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
    tasks: (id: string) => request<Task[]>(`/projects/${id}/tasks`),
  },
  tasks: {
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
  },
};
