import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import { BrainCircuit, FileText, Plus, Send, Paperclip, Menu, ExternalLink, LoaderCircle, Copy, Check, UserRound, LogOut } from "lucide-react";

const API = import.meta.env.DEV
  ? ""
  : (import.meta.env.VITE_API_URL || "").trim().replace(/\/+$/, "");
const AUTH_KEY = "omniresearch_auth";

function AuthScreen({ onAuth }) {
  const [mode, setMode] = useState("login");
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setBusy(true);

    try {
      const endpoint = mode === "login" ? "/api/auth/login" : "/api/auth/signup";
      const payload = mode === "login"
        ? { email: form.email, password: form.password }
        : { name: form.name, email: form.email, password: form.password };

      const res = await fetch(`${API}${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Authentication failed.");
      }

      localStorage.setItem(AUTH_KEY, JSON.stringify({ token: data.token, user: data.user }));
      onAuth(data.user, data.token);
    } catch (err) {
      setError(err.message || "Authentication failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-shell">
      <div className="auth-card">
        <div className="brand-block">
          <div className="brand-icon"><BrainCircuit /></div>
          <h1>OmniResearch AI</h1>
        </div>

        <div className="auth-tabs">
          <button className={mode === "login" ? "tab active" : "tab"} onClick={() => setMode("login")}>Login</button>
          <button className={mode === "signup" ? "tab active" : "tab"} onClick={() => setMode("signup")}>Sign up</button>
        </div>

        <form onSubmit={handleSubmit} className="auth-form">
          {mode === "signup" && (
            <label>
              Full name
              <input required autoComplete="name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Jane Smith" />
            </label>
          )}

          <label>
            Email
            <input required autoComplete="email" type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} placeholder="name@example.com" />
          </label>

          <label>
            Password
            <input required minLength={6} autoComplete={mode === "login" ? "current-password" : "new-password"} type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} placeholder="Minimum 6 characters" />
          </label>

          {error && <div className="error-box">{error}</div>}

          <button className="primary-button" disabled={busy} type="submit">
            {busy ? "Please wait..." : mode === "login" ? "Login" : "Create account"}
          </button>
        </form>
      </div>
    </div>
  );
}

export default function App() {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState("");
  const [mode, setMode] = useState("auto");
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState([]);
  const [busy, setBusy] = useState(false);
  const [docs, setDocs] = useState([]);
  const [selectedDocs, setSelectedDocs] = useState([]);
  const [error, setError] = useState("");
  const [sidebar, setSidebar] = useState(true);
  const [copied, setCopied] = useState(-1);
  const [history, setHistory] = useState([]);
  const [showHistory, setShowHistory] = useState(false);
  const [showAuthActivity, setShowAuthActivity] = useState(false);
  const [authEvents, setAuthEvents] = useState([]);
  const fileRef = useRef(null);
  const inputRef = useRef(null);
  const bottomRef = useRef(null);

  useEffect(() => {
    const saved = localStorage.getItem(AUTH_KEY);
    if (!saved) return;
    try {
      const parsed = JSON.parse(saved);
      if (parsed?.token && parsed?.user) {
        setUser(parsed.user);
        setToken(parsed.token);
      }
    } catch {
      localStorage.removeItem(AUTH_KEY);
    }
  }, []);

  useEffect(() => {
    if (!token) return;
    loadDocs();
    fetch(`${API}/api/auth/me`, { headers: { Authorization: `Bearer ${token}` } })
      .then(async (res) => {
        if (res.status === 401) {
          // A saved token can expire between visits. Drop it and return to login.
          localStorage.removeItem(AUTH_KEY);
          setToken("");
          setUser(null);
          return null;
        }
        return res.ok ? res.json() : null;
      })
      .then((data) => { if (data?.user) setUser(data.user); })
      .catch(() => {});
  }, [token]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, busy]);

  function logout() {
    fetch(`${API}/api/auth/logout`, { method: "POST", headers: { Authorization: `Bearer ${token}` } }).catch(() => {});
    localStorage.removeItem(AUTH_KEY);
    setToken("");
    setUser(null);
    setMessages([]);
    setDocs([]);
    setSelectedDocs([]);
  }

  async function loadDocs() {
    try {
      const res = await fetch(`${API}/api/documents`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!res.ok) return;
      const data = await res.json();
      setDocs(data.documents || []);
    } catch {
      // ignore for now
    }
  }

  async function upload(file) {
    if (!file) return;
    setError("");
    const form = new FormData();
    form.append("file", file);

    try {
      const res = await fetch(`${API}/api/upload`, {
        method: "POST",
        body: form,
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      const data = await res.json();
      if (!res.ok) throw Error(data.detail || "Upload failed");
      await loadDocs();
      setSelectedDocs((prev) => [...prev, data.document_id]);
      setMode("pdf");
      setMessages((prev) => [...prev, { role: "assistant", content: `**${data.filename}** uploaded and indexed into ${data.chunks} text chunks. Ask a question about it.` }]);
    } catch (err) {
      setError(err.message || "Upload failed.");
    }
  }

  async function send(text = message) {
    const value = text.trim();
    if (!value || busy) return;
    setError("");
    setMessages((prev) => [...prev, { role: "user", content: value }]);
    setMessage("");
    setBusy(true);

    try {
      const match = value.match(/https?:\/\/(?:www\.)?(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/shorts\/)[^\s]+/i);
      const res = await fetch(`${API}/api/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          message: value,
          task: mode,
          youtube_url: mode === "youtube" && match ? match[0].replace(/[),.]+$/, "") : null,
          document_ids: selectedDocs,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw Error(data.detail || "Request failed");
      setMessages((prev) => [...prev, { role: "assistant", content: data.answer, task: data.task, sources: data.sources || [] }]);
    } catch (err) {
      setError(err.message || "Could not reach the backend.");
    } finally {
      setBusy(false);
    }
  }

  async function copy(text, index) {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(index);
      setTimeout(() => setCopied(-1), 1200);
    } catch {
      setError("Clipboard is unavailable in this browser.");
    }
  }

  async function toggleHistory() {
    if (showHistory) { setShowHistory(false); return; }
    setShowAuthActivity(false);
    try {
      const res = await fetch(`${API}/api/history`, { headers: { Authorization: `Bearer ${token}` } });
      const data = await res.json();
      if (!res.ok) throw Error(data.detail || "Could not load chat history.");
      setHistory(data.history || []);
      setShowHistory(true);
    } catch (err) { setError(err.message); }
  }

  async function showActivity() {
    setShowHistory(false);
    setError("");
    try {
      const res = await fetch(`${API}/api/developer/auth-events`, { headers: { Authorization: `Bearer ${token}` } });
      const data = await res.json();
      if (!res.ok) throw Error(data.detail || "Could not load sign-in activity.");
      setAuthEvents(data.events || []);
      setShowAuthActivity(true);
    } catch (err) { setError(err.message); }
  }

  if (!token || !user) {
    return <AuthScreen onAuth={(authUser, authToken) => { setUser(authUser); setToken(authToken); }} />;
  }

  return (
    <div className="app">
      {sidebar && (
        <aside className="sidebar">
          <div className="brand">
            <div className="brand-icon"><BrainCircuit /></div>
            <div>
              <b>OmniResearch</b>
              <small>AI WORKSPACE</small>
            </div>
          </div>

          <div className="documents">
            <p className="label">YOUR DOCUMENTS</p>
            {!docs.length ? <small className="muted">Uploaded PDFs will appear here.</small> : docs.map((d) => (
              <label className="doc" key={d.document_id}>
                <input
                  type="checkbox"
                  checked={selectedDocs.includes(d.document_id)}
                  onChange={(e) => setSelectedDocs((prev) => e.target.checked ? [...prev, d.document_id] : prev.filter((x) => x !== d.document_id))}
                />
                <FileText size={14} />
                <span>{d.filename}</span>
              </label>
            ))}
          </div>

          <div className="profile">
            <div className="profile-icon">{user.name?.[0]?.toUpperCase() || "U"}</div>
            <div>
              <b>{user.name}</b>
              <small>{user.email}</small>
            </div>
            <button className="logout-button" onClick={logout} title="Logout"><LogOut size={15} /></button>
          </div>
        </aside>
      )}

      <main className="main">
        <header className="topbar">
          <div className="left">
            <button className="toggle" onClick={() => setSidebar(!sidebar)}><Menu size={18} /></button>
            <span>Workspace</span>
          </div>
          <div className="topbar-actions">
            <button className="history-top" onClick={() => { setMessages([]); setShowHistory(false); setShowAuthActivity(false); setError(""); setMessage(""); }}><Plus size={14} /> New chat</button>
            <button className="history-top" onClick={toggleHistory}>Chat history</button>
            {user.is_developer && <button className="history-top" onClick={showActivity}>Auth events</button>}
            <button className="top-logout" onClick={logout}><LogOut size={15} /> Log out</button>
          </div>
        </header>

        <section className={`conversation ${messages.length === 0 ? "welcome" : ""}`}>
          {showAuthActivity ? (
            <div className="activity-view">
              <div className="activity-heading"><div><span className="activity-kicker">DEVELOPER CONSOLE</span><h2>Authentication events</h2><p>Recent account creation, login, and logout events across users.</p></div><button className="history-top" onClick={() => setShowAuthActivity(false)}>Back to workspace</button></div>
              {authEvents.length ? <div className="activity-table-wrap"><table className="activity-table"><thead><tr><th>User</th><th>Email</th><th>Event</th><th>Status</th><th>Date and time</th></tr></thead><tbody>{authEvents.map((event) => <tr key={event.id}><td className="event-cell"><span className={`event-mark ${event.event_type}`}>{event.event_type === "logout" ? <LogOut size={15} /> : <UserRound size={15} />}</span><b>{event.name}</b></td><td>{event.email}</td><td>{event.event_type === "signup" ? "Account created" : event.event_type === "login" ? "Login" : "Log out"}</td><td><span className="event-status">Completed</span></td><td>{new Date(`${event.created_at.replace(" ", "T")}Z`).toLocaleString()}</td></tr>)}</tbody></table></div> : <p className="muted activity-empty">No authentication events recorded yet.</p>}
            </div>
          ) : showHistory ? (
            <div className="history-view"><h2>Your chat history</h2>{history.length ? history.map((item) => <button className="history-item" key={item.id} onClick={() => { setMessages([{role:"user", content:item.message}, {role:"assistant", content:item.answer, task:item.task}]); setMode(item.task === "chat" ? "auto" : item.task); setShowHistory(false); }}><b>{item.message}</b><small>{item.task} · {item.created_at}</small><span>{item.answer}</span></button>) : <p className="muted">No saved conversations yet.</p>}</div>
          ) : messages.length === 0 ? (
            <div className="hero">
              <h1>How can I help you?</h1>
              <p className="subtitle">Start a chat, or choose a tool below when you need it.</p>
            </div>
          ) : (
            <div className="message-list">
              {messages.map((m, i) => (
                <article className={`message ${m.role}`} key={i}>
                  <div className={`msg-icon ${m.role}`}>{m.role === "user" ? <UserRound size={17} /> : <BrainCircuit size={18} />}</div>
                  <div className="msg-body">
                    <div className="msg-head">
                      <b>{m.role === "user" ? "You" : "OmniResearch AI"}</b>
                      {m.task && <span>{m.task}</span>}
                    </div>
                    <div className="markdown"><ReactMarkdown>{m.content}</ReactMarkdown></div>
                    {!!m.sources?.length && (
                      <div className="sources">
                        <p>SOURCES · {m.sources.length}</p>
                        {m.sources.map((s, n) => (
                          <a className="source" href={s.url || undefined} target={s.url ? "_blank" : undefined} rel="noreferrer" key={n}>
                            <span>{n + 1}</span>
                            <div>
                              <b>{s.title || "Document source"}{s.page ? ` · page ${s.page}` : ""}</b>
                              {s.snippet && <small>{s.snippet}</small>}
                              {s.url && <small className="url">{s.url}</small>}
                            </div>
                            <ExternalLink size={14} />
                          </a>
                        ))}
                      </div>
                    )}
                    {m.role === "assistant" && (
                      <button className="copy" onClick={() => copy(m.content, i)}>
                        {copied === i ? <Check size={13} /> : <Copy size={13} />} {copied === i ? "Copied" : "Copy answer"}
                      </button>
                    )}
                  </div>
                </article>
              ))}

              {busy && (
                <div className="message assistant">
                  <div className="msg-icon assistant"><BrainCircuit size={18} /></div>
                  <div className="msg-body">
                    <b>OmniResearch AI</b>
                    <p className="loading"><LoaderCircle className="spin" size={17} /> Researching and preparing your answer…</p>
                  </div>
                </div>
              )}
              <div ref={bottomRef} />
            </div>
          )}
        </section>

        <div className="composer-area">
          {error && <div className="error">{error}<button onClick={() => setError("")}>Dismiss</button></div>}
          <div className="composer">
            <textarea
              ref={inputRef}
              rows={2}
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }}
              placeholder={mode === "pdf" ? "Ask about your uploaded PDF…" : "Ask anything…"}
            />
            <div className="composer-bottom">
              <div className="tools">
                <button className="attach" onClick={() => fileRef.current?.click()}><Paperclip size={15} /> Attach PDF</button>
              </div>
              <button className="send" disabled={!message.trim() || busy} onClick={() => send()}>
                {busy ? <LoaderCircle className="spin" size={17} /> : <Send size={17} />}
              </button>
            </div>
          </div>
          <p className="disclaimer">AI can make mistakes. Verify important information using sources. Generated code is not executed.</p>
        </div>

        <input ref={fileRef} hidden type="file" accept=".pdf,application/pdf" onChange={(e) => { upload(e.target.files?.[0]); e.target.value = ""; }} />
      </main>
    </div>
  );
}
