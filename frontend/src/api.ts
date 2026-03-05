export type UserRole = "SUPERADMIN" | "ADMIN" | "HOD" | "EMPLOYEE" | "AI_AGENT";

export type Me = {
  id: string;
  tenant_id: string;
  email: string;
  full_name: string;
  role: UserRole;
  employee_type: string;
};

export type MeResponse = {
  me: Me;
};

export type SessionAuthResponse = {
  ok: boolean;
  expires_in: number;
  me: Me;
};

export type Department = {
  id: string;
  tenant_id: string;
  name: string;
  description: string;
  parent_id: string | null;
};

export type OrgUser = {
  id: string;
  tenant_id: string;
  email: string;
  full_name: string;
  role: UserRole;
  department_id: string | null;
  manager_id: string | null;
  is_active: boolean;
};

export type Task = {
  id: string;
  title: string;
  description: string;
  status: string;
  assignee_user_id: string | null;
};

export type TimeEntry = {
  id: string;
  work_date: string;
  check_in_at: string | null;
  check_out_at: string | null;
  total_worked_minutes: number;
  ot_minutes: number;
};

export type ChatThread = {
  id: string;
  title: string | null;
  is_dm: boolean;
  participant_ids: string[];
  unread_count: number;
};

export type ChatMessage = {
  id: string;
  sender_user_id: string;
  content: string;
  created_at: string;
};

export type PilotStatus = {
  users: number;
  departments: number;
  tasks: number;
  chat_threads: number;
  chat_messages: number;
  time_entries: number;
  active_today: number;
};

const API_BASE =
  ((import.meta as unknown as { env?: Record<string, string> }).env?.VITE_API_BASE_URL as string | undefined) ??
  "http://localhost:8000";
export const GOOGLE_CLIENT_ID =
  ((import.meta as unknown as { env?: Record<string, string> }).env?.VITE_GOOGLE_CLIENT_ID as string | undefined) ??
  "";
const API_PREFIX = "/api/v1";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

type RequestOptions = {
  tenantId?: string;
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  body?: unknown;
  prefixed?: boolean;
};

async function request<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  const prefixed = opts.prefixed ?? true;
  const url = `${API_BASE}${prefixed ? API_PREFIX : ""}${path}`;
  const headers: Record<string, string> = {
    "Content-Type": "application/json"
  };
  if (opts.tenantId) headers["X-Tenant-ID"] = opts.tenantId;

  const res = await fetch(url, {
    method: opts.method ?? "GET",
    headers,
    credentials: "include",
    body: opts.body === undefined ? undefined : JSON.stringify(opts.body)
  });

  if (!res.ok) {
    let message = `Request failed (${res.status})`;
    try {
      const payload = await res.json();
      if (typeof payload?.detail === "string") {
        message = payload.detail;
      }
    } catch {
      const text = await res.text();
      if (text) message = text;
    }
    throw new ApiError(res.status, message);
  }
  return (await res.json()) as T;
}

export async function loginDev(email: string, fullName: string, tenantId: string) {
  return request<SessionAuthResponse>("/auth/dev/login", {
    method: "POST",
    tenantId,
    body: { email, full_name: fullName }
  });
}

export async function loginGoogle(idToken: string, tenantId: string) {
  return request<SessionAuthResponse>("/auth/google/login", {
    method: "POST",
    tenantId,
    body: { id_token: idToken }
  });
}

export async function refreshSession(tenantId: string) {
  return request<SessionAuthResponse>("/auth/refresh", {
    method: "POST",
    tenantId
  });
}

export async function logoutSession(tenantId: string) {
  return request<{ ok: boolean }>("/auth/logout", {
    method: "POST",
    tenantId
  });
}

export async function getMe(tenantId: string) {
  return request<MeResponse>("/auth/me", { tenantId });
}

export async function getPilotStatus(tenantId: string) {
  return request<PilotStatus>("/ops/pilot-status", { tenantId, prefixed: false });
}

export async function listDepartments(tenantId: string) {
  return request<Department[]>("/org/departments", { tenantId });
}

export async function createDepartment(tenantId: string, name: string, description: string) {
  return request<Department>("/org/departments", {
    tenantId,
    method: "POST",
    body: { name, description }
  });
}

export async function listUsers(tenantId: string) {
  return request<OrgUser[]>("/org/users", { tenantId });
}

export async function createUser(
  tenantId: string,
  payload: {
    email: string;
    full_name: string;
    role: UserRole;
    department_id: string | null;
    manager_id: string | null;
  }
) {
  return request<OrgUser>("/admin/users", {
    tenantId,
    method: "POST",
    body: {
      ...payload,
      tools_allowed: [],
      is_active: true,
      employee_type: payload.role === "AI_AGENT" ? "AGENT" : "HUMAN"
    }
  });
}

export async function listTasks(tenantId: string) {
  return request<Task[]>("/tasks", { tenantId });
}

export async function createTask(
  tenantId: string,
  payload: { title: string; description: string; assignee_user_id: string | null }
) {
  return request<Task>("/tasks", {
    tenantId,
    method: "POST",
    body: {
      title: payload.title,
      description: payload.description,
      status: "TODO",
      assignee_user_id: payload.assignee_user_id,
      due_at: null
    }
  });
}

export async function markTaskDone(tenantId: string, taskId: string) {
  return request<Task>(`/tasks/${taskId}`, {
    tenantId,
    method: "PATCH",
    body: { status: "DONE" }
  });
}

export async function clockIn(tenantId: string) {
  return request("/timeclock/clock-in", {
    tenantId,
    method: "POST",
    body: { source: "frontend", notes: "clock-in from frontend" }
  });
}

export async function clockOut(tenantId: string) {
  return request("/timeclock/clock-out", {
    tenantId,
    method: "POST",
    body: { notes: "clock-out from frontend" }
  });
}

export async function listMyEntries(tenantId: string) {
  return request<{ entries: TimeEntry[] }>("/timeclock/entries", { tenantId });
}

export async function listThreads(tenantId: string) {
  return request<ChatThread[]>("/chat/threads", { tenantId });
}

export async function createDmThread(tenantId: string, userId: string) {
  return request<ChatThread>("/chat/threads", {
    tenantId,
    method: "POST",
    body: { is_group: false, user_id: userId, member_ids: [], title: null }
  });
}

export async function listMessages(tenantId: string, threadId: string) {
  return request<ChatMessage[]>(`/chat/threads/${threadId}/messages?limit=100`, { tenantId });
}

export async function sendMessage(tenantId: string, threadId: string, content: string) {
  return request<ChatMessage>(`/chat/threads/${threadId}/messages`, {
    tenantId,
    method: "POST",
    body: { content }
  });
}

export async function unreadCount(tenantId: string) {
  return request<{ total_unread: number }>("/chat/unread", { tenantId });
}
