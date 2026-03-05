import { useEffect, useMemo, useRef, useState } from "react";
import {
  ApiError,
  ChatMessage,
  ChatThread,
  Department,
  GOOGLE_CLIENT_ID,
  Me,
  OrgUser,
  PilotStatus,
  Task,
  TimeEntry,
  UserRole,
  clockIn,
  clockOut,
  createDepartment,
  createDmThread,
  createTask,
  createUser,
  getMe,
  getPilotStatus,
  listDepartments,
  listMessages,
  listMyEntries,
  listTasks,
  listThreads,
  listUsers,
  loginDev,
  loginGoogle,
  logoutSession,
  markTaskDone,
  refreshSession,
  sendMessage,
  unreadCount
} from "./api";

const TENANT_KEY = "ems_tenant_id";

type Tab = "dashboard" | "org" | "users" | "tasks" | "timeclock" | "chat";

function readTenant() {
  return localStorage.getItem(TENANT_KEY) ?? "default";
}

function toMessage(error: unknown) {
  if (error instanceof Error) return error.message;
  return String(error);
}

export default function App() {
  const [tenantId, setTenantId] = useState(readTenant());
  const [me, setMe] = useState<Me | null>(null);
  const [tab, setTab] = useState<Tab>("dashboard");
  const [error, setError] = useState("");
  const [booting, setBooting] = useState(true);

  const isLoggedIn = Boolean(me);

  useEffect(() => {
    localStorage.setItem(TENANT_KEY, tenantId);
  }, [tenantId]);

  useEffect(() => {
    let active = true;

    const bootstrapSession = async () => {
      setBooting(true);
      try {
        const meResponse = await getMe(tenantId);
        if (!active) return;
        setMe(meResponse.me);
        setError("");
      } catch (err) {
        if (err instanceof ApiError && err.status === 401) {
          try {
            await refreshSession(tenantId);
            const meResponse = await getMe(tenantId);
            if (!active) return;
            setMe(meResponse.me);
            setError("");
          } catch (refreshErr) {
            if (!active) return;
            setMe(null);
            if (refreshErr instanceof ApiError && refreshErr.status === 401) {
              setError("");
            } else {
              setError(toMessage(refreshErr));
            }
          }
        } else {
          if (!active) return;
          setMe(null);
          setError(toMessage(err));
        }
      } finally {
        if (active) setBooting(false);
      }
    };

    void bootstrapSession();
    return () => {
      active = false;
    };
  }, [tenantId]);

  const onLogin = (nextMe: Me, nextTenantId: string) => {
    setMe(nextMe);
    setTenantId(nextTenantId);
    setError("");
  };

  const onLogout = async () => {
    try {
      await logoutSession(tenantId);
    } catch {
      // Always clear local UI state for logout UX.
    } finally {
      setMe(null);
      setError("");
    }
  };

  const title = useMemo(() => {
    if (!me) return "EMS Pilot";
    return `EMS Pilot - ${me.full_name} (${me.role})`;
  }, [me]);

  return (
    <div className="page">
      <header className="topbar">
        <h1>{title}</h1>
        {isLoggedIn ? <button onClick={() => void onLogout()}>Logout</button> : null}
      </header>

      {booting ? (
        <div className="card">
          <p>Checking session...</p>
        </div>
      ) : !isLoggedIn ? (
        <LoginView
          onLogin={onLogin}
          tenantId={tenantId}
          onTenantChange={setTenantId}
          error={error}
          setError={setError}
          clearError={() => setError("")}
        />
      ) : (
        <div className="layout">
          <nav className="sidebar">
            <button onClick={() => setTab("dashboard")}>Dashboard</button>
            <button onClick={() => setTab("org")}>Org/Departments</button>
            <button onClick={() => setTab("users")}>Users</button>
            <button onClick={() => setTab("tasks")}>Tasks</button>
            <button onClick={() => setTab("timeclock")}>Timeclock</button>
            <button onClick={() => setTab("chat")}>Chat</button>
          </nav>
          <main className="content">
            {tab === "dashboard" && <DashboardView tenantId={tenantId} />}
            {tab === "org" && <OrgView tenantId={tenantId} />}
            {tab === "users" && <UsersView tenantId={tenantId} />}
            {tab === "tasks" && <TasksView tenantId={tenantId} />}
            {tab === "timeclock" && <TimeclockView tenantId={tenantId} />}
            {tab === "chat" && <ChatView tenantId={tenantId} />}
          </main>
        </div>
      )}
    </div>
  );
}

function LoginView(props: {
  onLogin: (me: Me, tenantId: string) => void;
  tenantId: string;
  onTenantChange: (tenantId: string) => void;
  error: string;
  setError: (message: string) => void;
  clearError: () => void;
}) {
  const [email, setEmail] = useState("superadmin@cossmicrings.com");
  const [fullName, setFullName] = useState("Super Admin");
  const [busy, setBusy] = useState(false);
  const googleButtonRef = useRef<HTMLDivElement | null>(null);

  const doDevLogin = async () => {
    try {
      setBusy(true);
      props.clearError();
      const out = await loginDev(email, fullName, props.tenantId);
      props.onLogin(out.me, props.tenantId);
    } catch (err) {
      props.setError(toMessage(err));
    } finally {
      setBusy(false);
    }
  };

  useEffect(() => {
    const clientId = GOOGLE_CLIENT_ID.trim();
    const buttonEl = googleButtonRef.current;
    if (!clientId || !buttonEl) {
      return;
    }

    const initialize = () => {
      const google = (window as unknown as { google?: any }).google;
      if (!google?.accounts?.id || !googleButtonRef.current) {
        return;
      }
      google.accounts.id.initialize({
        client_id: clientId,
        callback: async (response: { credential?: string }) => {
          if (!response?.credential) {
            props.setError("Google sign-in failed: missing credential.");
            return;
          }
          try {
            setBusy(true);
            props.clearError();
            const out = await loginGoogle(response.credential, props.tenantId);
            props.onLogin(out.me, props.tenantId);
          } catch (err) {
            props.setError(toMessage(err));
          } finally {
            setBusy(false);
          }
        }
      });
      googleButtonRef.current.innerHTML = "";
      google.accounts.id.renderButton(googleButtonRef.current, {
        theme: "outline",
        size: "large",
        text: "signin_with",
        shape: "rectangular"
      });
    };

    if ((window as unknown as { google?: any }).google?.accounts?.id) {
      initialize();
      return;
    }

    const scriptId = "google-gsi-script";
    let script = document.getElementById(scriptId) as HTMLScriptElement | null;
    if (!script) {
      script = document.createElement("script");
      script.id = scriptId;
      script.src = "https://accounts.google.com/gsi/client";
      script.async = true;
      script.defer = true;
      document.head.appendChild(script);
    }

    script.addEventListener("load", initialize);
    return () => {
      script?.removeEventListener("load", initialize);
    };
  }, [props.tenantId, props.onLogin, props.clearError]);

  return (
    <div className="card">
      <h2>Login</h2>
      <label>
        Tenant ID
        <input value={props.tenantId} onChange={(e) => props.onTenantChange(e.target.value)} />
      </label>
      <p className="note">Dev Login (requires ENV=dev and DEV_AUTH_BYPASS=true)</p>
      <label>
        Email
        <input value={email} onChange={(e) => setEmail(e.target.value)} />
      </label>
      <label>
        Full Name
        <input value={fullName} onChange={(e) => setFullName(e.target.value)} />
      </label>
      <button disabled={busy} onClick={doDevLogin}>
        Login (Dev)
      </button>

      <p className="note">Google Login</p>
      {GOOGLE_CLIENT_ID.trim() ? (
        <div ref={googleButtonRef} />
      ) : (
        <p className="error">Set VITE_GOOGLE_CLIENT_ID to enable Google Sign-In.</p>
      )}

      {props.error ? <p className="error">{props.error}</p> : null}
    </div>
  );
}

function DashboardView({ tenantId }: { tenantId: string }) {
  const [status, setStatus] = useState<PilotStatus | null>(null);
  const [error, setError] = useState("");

  const load = async () => {
    try {
      setStatus(await getPilotStatus(tenantId));
      setError("");
    } catch (err) {
      setError(toMessage(err));
    }
  };

  useEffect(() => {
    void load();
  }, []);

  return (
    <div className="card">
      <h2>Dashboard</h2>
      <button onClick={() => void load()}>Refresh</button>
      {error ? <p className="error">{error}</p> : null}
      {status ? <pre>{JSON.stringify(status, null, 2)}</pre> : <p>Loading...</p>}
    </div>
  );
}

function OrgView({ tenantId }: { tenantId: string }) {
  const [rows, setRows] = useState<Department[]>([]);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState("");

  const load = async () => {
    try {
      setRows(await listDepartments(tenantId));
      setError("");
    } catch (err) {
      setError(toMessage(err));
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const submit = async () => {
    if (!name.trim()) return;
    try {
      await createDepartment(tenantId, name.trim(), description.trim());
      setName("");
      setDescription("");
      await load();
    } catch (err) {
      setError(toMessage(err));
    }
  };

  return (
    <div className="card">
      <h2>Org / Departments</h2>
      <div className="row">
        <input placeholder="Department name" value={name} onChange={(e) => setName(e.target.value)} />
        <input placeholder="Description" value={description} onChange={(e) => setDescription(e.target.value)} />
        <button onClick={() => void submit()}>Create</button>
      </div>
      {error ? <p className="error">{error}</p> : null}
      <ul>{rows.map((d) => <li key={d.id}>{d.name} - {d.description}</li>)}</ul>
    </div>
  );
}

function UsersView({ tenantId }: { tenantId: string }) {
  const [users, setUsers] = useState<OrgUser[]>([]);
  const [depts, setDepts] = useState<Department[]>([]);
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [role, setRole] = useState<UserRole>("EMPLOYEE");
  const [departmentId, setDepartmentId] = useState("");
  const [error, setError] = useState("");

  const load = async () => {
    try {
      const [u, d] = await Promise.all([listUsers(tenantId), listDepartments(tenantId)]);
      setUsers(u);
      setDepts(d);
      setError("");
    } catch (err) {
      setError(toMessage(err));
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const submit = async () => {
    try {
      await createUser(tenantId, {
        email,
        full_name: fullName,
        role,
        department_id: departmentId || null,
        manager_id: null
      });
      setEmail("");
      setFullName("");
      await load();
    } catch (err) {
      setError(toMessage(err));
    }
  };

  return (
    <div className="card">
      <h2>Users</h2>
      <div className="row">
        <input placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} />
        <input placeholder="Full name" value={fullName} onChange={(e) => setFullName(e.target.value)} />
        <select value={role} onChange={(e) => setRole(e.target.value as UserRole)}>
          <option>ADMIN</option>
          <option>HOD</option>
          <option>EMPLOYEE</option>
          <option>AI_AGENT</option>
        </select>
        <select value={departmentId} onChange={(e) => setDepartmentId(e.target.value)}>
          <option value="">No Department</option>
          {depts.map((d) => (
            <option key={d.id} value={d.id}>
              {d.name}
            </option>
          ))}
        </select>
        <button onClick={() => void submit()}>Create</button>
      </div>
      {error ? <p className="error">{error}</p> : null}
      <ul>{users.map((u) => <li key={u.id}>{u.email} - {u.role}</li>)}</ul>
    </div>
  );
}

function TasksView({ tenantId }: { tenantId: string }) {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [users, setUsers] = useState<OrgUser[]>([]);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [assignee, setAssignee] = useState("");
  const [error, setError] = useState("");

  const load = async () => {
    try {
      const [t, u] = await Promise.all([listTasks(tenantId), listUsers(tenantId)]);
      setTasks(t);
      setUsers(u);
      setError("");
    } catch (err) {
      setError(toMessage(err));
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const submit = async () => {
    try {
      await createTask(tenantId, {
        title,
        description,
        assignee_user_id: assignee || null
      });
      setTitle("");
      setDescription("");
      await load();
    } catch (err) {
      setError(toMessage(err));
    }
  };

  const done = async (taskId: string) => {
    try {
      await markTaskDone(tenantId, taskId);
      await load();
    } catch (err) {
      setError(toMessage(err));
    }
  };

  return (
    <div className="card">
      <h2>Tasks</h2>
      <div className="row">
        <input placeholder="Title" value={title} onChange={(e) => setTitle(e.target.value)} />
        <input placeholder="Description" value={description} onChange={(e) => setDescription(e.target.value)} />
        <select value={assignee} onChange={(e) => setAssignee(e.target.value)}>
          <option value="">Unassigned</option>
          {users.map((u) => (
            <option key={u.id} value={u.id}>
              {u.email}
            </option>
          ))}
        </select>
        <button onClick={() => void submit()}>Create</button>
      </div>
      {error ? <p className="error">{error}</p> : null}
      <ul>
        {tasks.map((t) => (
          <li key={t.id}>
            {t.title} - {t.status}{" "}
            {t.status !== "DONE" ? <button onClick={() => void done(t.id)}>Mark DONE</button> : null}
          </li>
        ))}
      </ul>
    </div>
  );
}

function TimeclockView({ tenantId }: { tenantId: string }) {
  const [rows, setRows] = useState<{ entries: TimeEntry[] }>({ entries: [] });
  const [error, setError] = useState("");

  const load = async () => {
    try {
      setRows(await listMyEntries(tenantId));
      setError("");
    } catch (err) {
      setError(toMessage(err));
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const handleClockIn = async () => {
    try {
      await clockIn(tenantId);
      await load();
    } catch (err) {
      setError(toMessage(err));
    }
  };

  const handleClockOut = async () => {
    try {
      await clockOut(tenantId);
      await load();
    } catch (err) {
      setError(toMessage(err));
    }
  };

  return (
    <div className="card">
      <h2>Timeclock</h2>
      <div className="row">
        <button onClick={() => void handleClockIn()}>Clock In</button>
        <button onClick={() => void handleClockOut()}>Clock Out</button>
        <button onClick={() => void load()}>Refresh</button>
      </div>
      {error ? <p className="error">{error}</p> : null}
      <pre>{JSON.stringify(rows, null, 2)}</pre>
    </div>
  );
}

function ChatView({ tenantId }: { tenantId: string }) {
  const [users, setUsers] = useState<OrgUser[]>([]);
  const [threads, setThreads] = useState<ChatThread[]>([]);
  const [selectedThread, setSelectedThread] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [messageText, setMessageText] = useState("");
  const [targetUserId, setTargetUserId] = useState("");
  const [unread, setUnread] = useState(0);
  const [error, setError] = useState("");

  const loadThreads = async () => {
    try {
      const [u, t, unreadRes] = await Promise.all([listUsers(tenantId), listThreads(tenantId), unreadCount(tenantId)]);
      setUsers(u);
      setThreads(t);
      setUnread(unreadRes.total_unread);
      setError("");
    } catch (err) {
      setError(toMessage(err));
    }
  };

  const loadMessagesFor = async (threadId: string) => {
    try {
      setMessages(await listMessages(tenantId, threadId));
      setSelectedThread(threadId);
      setError("");
    } catch (err) {
      setError(toMessage(err));
    }
  };

  useEffect(() => {
    void loadThreads();
  }, []);

  const createThread = async () => {
    try {
      const thread = await createDmThread(tenantId, targetUserId);
      await loadThreads();
      await loadMessagesFor(thread.id);
    } catch (err) {
      setError(toMessage(err));
    }
  };

  const postMessage = async () => {
    if (!selectedThread || !messageText.trim()) return;
    try {
      await sendMessage(tenantId, selectedThread, messageText.trim());
      setMessageText("");
      await loadMessagesFor(selectedThread);
      await loadThreads();
    } catch (err) {
      setError(toMessage(err));
    }
  };

  return (
    <div className="card">
      <h2>Chat</h2>
      <p>Total unread: {unread}</p>
      <div className="row">
        <select value={targetUserId} onChange={(e) => setTargetUserId(e.target.value)}>
          <option value="">Select user for DM</option>
          {users.map((u) => (
            <option key={u.id} value={u.id}>
              {u.email}
            </option>
          ))}
        </select>
        <button disabled={!targetUserId} onClick={() => void createThread()}>
          Create / Open DM
        </button>
      </div>
      {error ? <p className="error">{error}</p> : null}
      <div className="chat-layout">
        <ul className="thread-list">
          {threads.map((t) => (
            <li key={t.id}>
              <button onClick={() => void loadMessagesFor(t.id)}>
                {t.title || (t.is_dm ? "DM Thread" : "Group Thread")} ({t.unread_count})
              </button>
            </li>
          ))}
        </ul>
        <div className="message-panel">
          <ul>
            {messages.map((m) => (
              <li key={m.id}>
                <strong>{m.sender_user_id.slice(0, 8)}:</strong> {m.content}
              </li>
            ))}
          </ul>
          <div className="row">
            <input
              placeholder="Type message"
              value={messageText}
              onChange={(e) => setMessageText(e.target.value)}
            />
            <button onClick={() => void postMessage()}>Send</button>
          </div>
        </div>
      </div>
    </div>
  );
}
