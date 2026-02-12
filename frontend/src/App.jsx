import { useState, useEffect, useRef, useCallback } from "react";
import { useAuth } from "./AuthContext";
import LoginPage from "./LoginPage";
import { createAuthWS, apiFetch } from "./api";

/* ─── Inline Icons ────────────────────────────────────────────── */
const Icon = {
  Monitor: (p) => (
    <svg {...p} width={p.size||18} height={p.size||18} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/>
    </svg>
  ),
  Send: (p) => (
    <svg {...p} width={p.size||18} height={p.size||18} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>
    </svg>
  ),
  Mic: (p) => (
    <svg {...p} width={p.size||18} height={p.size||18} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/><line x1="8" y1="23" x2="16" y2="23"/>
    </svg>
  ),
  Eye: (p) => (
    <svg {...p} width={p.size||16} height={p.size||16} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>
    </svg>
  ),
  Pause: () => (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="4" width="4" height="16" rx="1"/><rect x="14" y="4" width="4" height="16" rx="1"/></svg>
  ),
  Play: () => (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21"/></svg>
  ),
  Lock: () => (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>
    </svg>
  ),
  Unlock: () => (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 9.9-1"/>
    </svg>
  ),
  Reset: () => (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"/>
    </svg>
  ),
  Zap: () => (
    <svg width="11" height="11" viewBox="0 0 24 24" fill="currentColor"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
  ),
  Bot: () => (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="11" width="18" height="10" rx="2"/><circle cx="12" cy="5" r="2"/><path d="M12 7v4"/><line x1="8" y1="16" x2="8" y2="16"/><line x1="16" y1="16" x2="16" y2="16"/>
    </svg>
  ),
  Camera: () => (
    <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/><circle cx="12" cy="13" r="4"/>
    </svg>
  ),
  Logout: () => (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/>
    </svg>
  ),
  Download: () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>
    </svg>
  ),
  Wifi: () => (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M5 12.55a11 11 0 0 1 14.08 0"/><path d="M1.42 9a16 16 0 0 1 21.16 0"/><path d="M8.53 16.11a6 6 0 0 1 6.95 0"/><line x1="12" y1="20" x2="12.01" y2="20"/>
    </svg>
  ),
  WifiOff: () => (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="1" y1="1" x2="23" y2="23"/><path d="M16.72 11.06A10.94 10.94 0 0 1 19 12.55"/><path d="M5 12.55a10.94 10.94 0 0 1 5.17-2.39"/><path d="M10.71 5.05A16 16 0 0 1 22.56 9"/><path d="M1.42 9a15.91 15.91 0 0 1 4.7-2.88"/><path d="M8.53 16.11a6 6 0 0 1 6.95 0"/><line x1="12" y1="20" x2="12.01" y2="20"/>
    </svg>
  ),
};

/* ─── Status Dot ──────────────────────────────────────────────── */
function StatusDot({ status }) {
  const c = { live: "bg-emerald-400", paused: "bg-amber-400", disconnected: "bg-red-400", connecting: "bg-blue-400" };
  const pulse = status === "live" || status === "connecting";
  return (
    <span className="relative flex h-2 w-2">
      {pulse && <span className={`absolute inline-flex h-full w-full rounded-full opacity-50 animate-ping ${c[status]}`} />}
      <span className={`relative inline-flex rounded-full h-2 w-2 ${c[status] || c.disconnected}`} />
    </span>
  );
}

/* ─── Thinking Dots ───────────────────────────────────────────── */
function Thinking() {
  return (
    <div className="flex items-start gap-2.5 max-w-[85%]">
      <div className="shrink-0 w-7 h-7 rounded-lg bg-violet-500/15 flex items-center justify-center mt-0.5 text-violet-400">
        <Icon.Bot />
      </div>
      <div className="bg-white/[0.03] border border-white/[0.06] rounded-2xl rounded-tl-md px-4 py-3 flex items-center gap-2">
        {[0, 150, 300].map((d) => (
          <span key={d} className="w-1.5 h-1.5 rounded-full bg-violet-400 animate-bounce" style={{ animationDelay: `${d}ms` }} />
        ))}
        <span className="text-[11px] text-white/25 ml-1">Analyzing...</span>
      </div>
    </div>
  );
}

/* ─── Render message text with minimal markdown ───────────────── */
function RichText({ text }) {
  const parts = text.split(/(```[\s\S]*?```|`[^`]+`|\*\*[^*]+\*\*)/g);
  return parts.map((p, i) => {
    if (p.startsWith("```") && p.endsWith("```")) {
      const code = p.slice(3, -3).replace(/^\w+\n/, "");
      return <pre key={i} className="bg-black/30 rounded-lg p-3 my-2 text-[11px] font-mono overflow-x-auto text-emerald-300/70 leading-relaxed whitespace-pre-wrap">{code}</pre>;
    }
    if (p.startsWith("`") && p.endsWith("`"))
      return <code key={i} className="bg-white/[0.07] px-1.5 py-0.5 rounded text-[11px] font-mono text-violet-300">{p.slice(1,-1)}</code>;
    if (p.startsWith("**") && p.endsWith("**"))
      return <strong key={i} className="font-semibold text-white/90">{p.slice(2,-2)}</strong>;
    return p.split("\n").map((line, j, a) => (
      <span key={`${i}-${j}`}>{line}{j < a.length - 1 && <br/>}</span>
    ));
  });
}

/* ─── Chat Message ────────────────────────────────────────────── */
function Message({ msg }) {
  if (msg.role === "system") {
    return (
      <div className="flex justify-center py-0.5">
        <span className="text-[11px] text-white/20 bg-white/[0.02] px-3 py-1 rounded-full">{msg.text}</span>
      </div>
    );
  }

  if (msg.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[82%] bg-violet-600/25 border border-violet-500/15 rounded-2xl rounded-br-md px-4 py-2.5 text-[13px] text-white/90 leading-relaxed">
          <RichText text={msg.text} />
        </div>
      </div>
    );
  }

  // assistant
  return (
    <div className="flex items-start gap-2.5 max-w-[88%]">
      <div className="shrink-0 w-7 h-7 rounded-lg bg-violet-500/15 flex items-center justify-center mt-0.5 text-violet-400">
        <Icon.Bot />
      </div>
      <div className="min-w-0 flex-1">
        <div className="bg-white/[0.03] border border-white/[0.06] rounded-2xl rounded-tl-md px-4 py-2.5 text-[13px] text-white/80 leading-relaxed">
          <RichText text={msg.text} />
        </div>
        {msg.meta && (
          <div className="flex items-center gap-3 mt-1 px-1">
            {msg.meta.frames > 0 && (
              <span className="text-[10px] text-white/15 flex items-center gap-1"><Icon.Camera /> {msg.meta.frames}</span>
            )}
            {msg.meta.tokens && (
              <span className="text-[10px] text-white/15">{(msg.meta.tokens.input||0)+(msg.meta.tokens.output||0)} tok</span>
            )}
            {msg.meta.actions?.length > 0 && (
              <span className="text-[10px] text-amber-400/40 flex items-center gap-1"><Icon.Zap /> {msg.meta.actions.length} action{msg.meta.actions.length>1?"s":""}</span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

/* ─── Small reusable button ───────────────────────────────────── */
function ToolbarBtn({ onClick, active, danger, children, className="" }) {
  let base = "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-medium transition-all duration-200 border cursor-pointer select-none ";
  if (active) base += "bg-violet-600/20 text-violet-300 border-violet-500/25 ";
  else if (danger) base += "bg-white/[0.03] text-red-400/50 border-white/[0.05] hover:bg-red-500/10 hover:text-red-400 hover:border-red-500/20 ";
  else base += "bg-white/[0.03] text-white/40 border-white/[0.05] hover:bg-white/[0.06] hover:text-white/60 ";
  return <button onClick={onClick} className={base + className}>{children}</button>;
}

/* ─── Agent Not Connected Banner ──────────────────────────────── */
function AgentBanner() {
  return (
    <div className="text-center px-8 py-12">
      <div className="w-16 h-16 rounded-2xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center mx-auto mb-4 text-amber-400/60">
        <Icon.WifiOff />
      </div>
      <h3 className="text-[15px] font-semibold text-white/60 mb-2">Agent Not Connected</h3>
      <p className="text-[13px] text-white/30 mb-4 max-w-xs mx-auto leading-relaxed">
        Download and run the Watchtower Agent on the computer you want to monitor.
      </p>
      <div className="inline-flex items-center gap-2 bg-violet-600/20 border border-violet-500/20 text-violet-300 px-4 py-2 rounded-xl text-[12px] font-medium cursor-pointer hover:bg-violet-600/30 transition-colors">
        <Icon.Download /> Download Agent
      </div>
      <div className="mt-6 text-[11px] text-white/15 space-y-1">
        <p>1. Download the agent (.exe for Windows)</p>
        <p>2. Run it and enter your connection token</p>
        <p>3. Your screen will appear here automatically</p>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════ */
/* ─── Main App ────────────────────────────────────────────────── */
/* ═══════════════════════════════════════════════════════════════ */
export default function App() {
  const { user, loading, isAuthenticated, logout } = useAuth();

  const [conn, setConn]           = useState("connecting");
  const [agentStatus, setAgentStatus] = useState("disconnected");
  const [paused, setPaused]       = useState(false);
  const [actions, setActions]     = useState(false);
  const [thinking, setThinking]   = useState(false);
  const [input, setInput]         = useState("");
  const [recording, setRecording] = useState(false);
  const [showUserMenu, setShowUserMenu] = useState(false);

  const [messages, setMessages] = useState([
    { id: 0, role: "system", text: "Session started — Claude can see your screen in real time." },
  ]);
  const [frame, setFrame]       = useState(null);
  const [fInfo, setFInfo]       = useState({ w: 0, h: 0, n: 0 });
  const [stats, setStats]       = useState({ frames: 0, skipped: 0, ms: 0, turns: 0, tokens: 0 });

  const chatEnd   = useRef(null);
  const inputRef  = useRef(null);
  const screenWs  = useRef(null);
  const chatWs    = useRef(null);
  const recog     = useRef(null);
  const nextId    = useRef(1);
  const retries   = useRef(0);

  // auto-scroll
  useEffect(() => { chatEnd.current?.scrollIntoView({ behavior: "smooth" }); }, [messages, thinking]);

  // helper
  const addMsg = useCallback((role, text, meta) => {
    setMessages(p => [...p, { id: nextId.current++, role, text, meta }]);
  }, []);

  /* ── Screen Stream WebSocket (authenticated) ─────────────────── */
  const openScreenWs = useCallback(() => {
    if (!isAuthenticated) return;
    try {
      const ws = createAuthWS("/ws/stream");
      ws.onopen = () => { setConn("live"); retries.current = 0; };
      ws.onmessage = (e) => {
        const d = JSON.parse(e.data);
        if (d.type === "frame") {
          setFrame(`data:image/jpeg;base64,${d.image_b64}`);
          setFInfo({ w: d.width, h: d.height, n: d.frame_number });
        } else if (d.type === "agent_status") {
          setAgentStatus(d.status || "disconnected");
        }
      };
      ws.onclose = () => {
        setConn("disconnected");
        if (retries.current < 12) {
          setTimeout(openScreenWs, Math.min(1000 * 2 ** retries.current, 30000));
          retries.current++;
        }
      };
      screenWs.current = ws;
    } catch {}
  }, [isAuthenticated]);

  /* ── Chat WebSocket (authenticated) ──────────────────────────── */
  const openChatWs = useCallback(() => {
    if (!isAuthenticated) return;
    try {
      const ws = createAuthWS("/ws/chat");
      ws.onmessage = (e) => {
        const d = JSON.parse(e.data);
        if (d.type === "response") {
          setThinking(false);
          addMsg("assistant", d.text, { frames: d.frame_count, tokens: d.tokens, actions: d.actions });
          if (d.tokens) setStats(s => ({ ...s, tokens: s.tokens + (d.tokens.input||0) + (d.tokens.output||0) }));
        } else if (d.type === "status") {
          if (d.status === "thinking") setThinking(true);
          else if (d.status === "reset") {
            setMessages([{ id: nextId.current++, role: "system", text: "Conversation reset." }]);
            setThinking(false);
          }
        } else if (d.type === "error") {
          setThinking(false);
          addMsg("system", `Error: ${d.message}`);
        }
      };
      ws.onclose = () => setTimeout(openChatWs, 2000);
      chatWs.current = ws;
    } catch {}
  }, [isAuthenticated, addMsg]);

  useEffect(() => {
    if (!isAuthenticated) return;
    openScreenWs();
    openChatWs();
    return () => { screenWs.current?.close(); chatWs.current?.close(); };
  }, [isAuthenticated, openScreenWs, openChatWs]);

  /* ── Send / Describe / Reset ────────────────────────────────── */
  const send = useCallback(() => {
    const t = input.trim();
    if (!t || thinking) return;
    addMsg("user", t);
    setInput("");
    setStats(s => ({ ...s, turns: s.turns + 1 }));
    if (chatWs.current?.readyState === 1)
      chatWs.current.send(JSON.stringify({ type: "chat", message: t, include_screenshot: true }));
  }, [input, thinking, addMsg]);

  const describe = useCallback(() => {
    if (thinking) return;
    addMsg("system", "Asking Claude to describe your screen...");
    if (chatWs.current?.readyState === 1) chatWs.current.send(JSON.stringify({ type: "describe" }));
  }, [thinking, addMsg]);

  const reset = useCallback(() => {
    if (chatWs.current?.readyState === 1) chatWs.current.send(JSON.stringify({ type: "reset" }));
    setStats(s => ({ ...s, tokens: 0, turns: 0 }));
  }, []);

  const togglePause = useCallback(() => {
    const next = !paused;
    setPaused(next);
    setConn(next ? "paused" : "live");
    // Send control message through stream WS
    if (screenWs.current?.readyState === 1)
      screenWs.current.send(JSON.stringify({ type: "control", command: next ? "pause" : "resume" }));
  }, [paused]);

  const toggleActions = useCallback(() => {
    const next = !actions;
    setActions(next);
    // Send control message through stream WS
    if (screenWs.current?.readyState === 1)
      screenWs.current.send(JSON.stringify({ type: "control", command: next ? "enable_actions" : "disable_actions" }));
    addMsg("system", next ? "⚠ Actions enabled — Claude can control mouse & keyboard." : "Actions disabled.");
  }, [actions, addMsg]);

  /* ── Voice ──────────────────────────────────────────────────── */
  const toggleVoice = useCallback(() => {
    if (!("webkitSpeechRecognition" in window || "SpeechRecognition" in window)) {
      addMsg("system", "Voice not supported in this browser."); return;
    }
    if (recording) { recog.current?.stop(); setRecording(false); return; }
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    const r = new SR(); r.continuous = false; r.interimResults = true;
    r.onstart = () => setRecording(true);
    r.onresult = (e) => { let t=""; for (const x of e.results) t += x[0].transcript; setInput(t); };
    r.onend = () => setRecording(false);
    r.onerror = () => setRecording(false);
    recog.current = r; r.start();
  }, [recording, addMsg]);

  const onKey = (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } };
  const label = { live: "Live", paused: "Paused", disconnected: "Disconnected", connecting: "Connecting..." };

  // Auth loading state
  if (loading) {
    return (
      <div className="h-screen w-screen bg-[#0b0d14] flex items-center justify-center">
        <div className="text-white/30 text-[13px]">Loading...</div>
      </div>
    );
  }

  // Not authenticated — show login
  if (!isAuthenticated) {
    return <LoginPage />;
  }

  const agentConnected = agentStatus !== "disconnected";

  /* ── Render ─────────────────────────────────────────────────── */
  return (
    <div className="h-screen w-screen bg-[#0b0d14] text-white flex flex-col overflow-hidden" style={{ fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif" }}>

      {/* ═══ TOP BAR ═══════════════════════════════════════════ */}
      <header className="shrink-0 h-12 flex items-center justify-between px-4 bg-[#0f1119] border-b border-white/[0.06]">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-md bg-gradient-to-br from-violet-500/30 to-violet-600/10 flex items-center justify-center text-violet-300">
              <Icon.Monitor size={14} />
            </div>
            <span className="text-[13px] font-semibold tracking-tight text-white/80">Watchtower AI</span>
          </div>

          {/* Connection status */}
          <div className="flex items-center gap-1.5 bg-white/[0.03] border border-white/[0.05] rounded-full px-2.5 py-1 ml-1">
            <StatusDot status={conn} />
            <span className="text-[10px] text-white/35 font-medium">{label[conn]}</span>
          </div>

          {/* Agent status */}
          <div className={`flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[10px] font-medium ${
            agentConnected
              ? "bg-emerald-500/10 border border-emerald-500/20 text-emerald-400/60"
              : "bg-amber-500/10 border border-amber-500/20 text-amber-400/60"
          }`}>
            {agentConnected ? <Icon.Wifi /> : <Icon.WifiOff />}
            <span className="hidden sm:inline">{agentConnected ? "Agent Online" : "Agent Offline"}</span>
          </div>
        </div>

        <div className="flex items-center gap-1.5">
          <ToolbarBtn onClick={togglePause} active={paused}>
            {paused ? <><Icon.Play /><span className="hidden sm:inline">Resume</span></> : <><Icon.Pause /><span className="hidden sm:inline">Pause</span></>}
          </ToolbarBtn>
          <ToolbarBtn onClick={describe}>
            <Icon.Eye /><span className="hidden sm:inline">Describe</span>
          </ToolbarBtn>
          <ToolbarBtn onClick={toggleActions} active={actions}>
            {actions ? <><Icon.Unlock /><span className="hidden sm:inline">Actions On</span></> : <><Icon.Lock /><span className="hidden sm:inline">Actions Off</span></>}
          </ToolbarBtn>
          <ToolbarBtn onClick={reset} danger>
            <Icon.Reset /><span className="hidden sm:inline">Reset</span>
          </ToolbarBtn>

          {/* User menu */}
          <div className="relative ml-2">
            <button
              onClick={() => setShowUserMenu(!showUserMenu)}
              className="flex items-center gap-1.5 bg-white/[0.04] border border-white/[0.06] rounded-lg px-2.5 py-1.5 text-[11px] text-white/50 hover:text-white/70 transition-colors cursor-pointer"
            >
              <span className="w-5 h-5 rounded-full bg-violet-500/20 flex items-center justify-center text-violet-300 text-[10px] font-bold">
                {(user?.email || "U")[0].toUpperCase()}
              </span>
              <span className="hidden sm:inline max-w-[100px] truncate">{user?.email}</span>
            </button>

            {showUserMenu && (
              <>
                <div className="fixed inset-0 z-40" onClick={() => setShowUserMenu(false)} />
                <div className="absolute right-0 top-full mt-1 z-50 bg-[#1a1d2e] border border-white/[0.08] rounded-xl shadow-xl py-1 min-w-[180px]">
                  <div className="px-3 py-2 border-b border-white/[0.06]">
                    <p className="text-[11px] text-white/60 truncate">{user?.email}</p>
                    <p className="text-[10px] text-white/25 mt-0.5 capitalize">{user?.plan || "free"} plan</p>
                  </div>
                  <button
                    onClick={() => { setShowUserMenu(false); logout(); }}
                    className="w-full text-left px-3 py-2 text-[12px] text-red-400/70 hover:bg-red-500/10 flex items-center gap-2 cursor-pointer transition-colors"
                  >
                    <Icon.Logout /> Sign Out
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      </header>

      {/* ═══ MAIN AREA ═════════════════════════════════════════ */}
      <div className="flex-1 flex min-h-0">

        {/* ── Screen Feed ─────────────────────────────────────── */}
        <div className="flex-1 bg-black relative flex items-center justify-center min-w-0">
          {frame ? (
            <img src={frame} alt="Screen" className="max-w-full max-h-full object-contain" />
          ) : agentConnected ? (
            <div className="text-center px-8">
              <div className="w-14 h-14 rounded-2xl bg-white/[0.02] border border-white/[0.05] flex items-center justify-center mx-auto mb-3 text-white/15">
                <Icon.Monitor size={24} />
              </div>
              <p className="text-[13px] text-white/25 font-medium mb-1">Waiting for screen feed...</p>
              <p className="text-[11px] text-white/12">Agent is connected, frames will appear shortly.</p>
            </div>
          ) : (
            <AgentBanner />
          )}
          {/* badges */}
          <div className="absolute top-3 left-3 flex gap-1.5">
            {fInfo.w > 0 && (
              <span className="text-[9px] text-white/30 bg-black/70 backdrop-blur-sm rounded px-1.5 py-0.5 font-mono">
                {fInfo.w}×{fInfo.h}
              </span>
            )}
            <span className="text-[9px] text-white/30 bg-black/70 backdrop-blur-sm rounded px-1.5 py-0.5 font-mono">
              #{fInfo.n || "—"}
            </span>
          </div>
        </div>

        {/* ── Chat Panel ──────────────────────────────────────── */}
        <div className="w-[380px] xl:w-[420px] shrink-0 flex flex-col bg-[#0f1119] border-l border-white/[0.06] min-h-0">

          {/* Chat header */}
          <div className="shrink-0 flex items-center justify-between px-4 py-2.5 border-b border-white/[0.06]">
            <div className="flex items-center gap-2">
              <div className="w-5 h-5 rounded bg-violet-500/15 flex items-center justify-center text-violet-400"><Icon.Bot /></div>
              <span className="text-[13px] font-semibold text-white/70">Claude</span>
            </div>
            {stats.tokens > 0 && <span className="text-[9px] text-white/15 font-mono">{stats.tokens.toLocaleString()} tok</span>}
          </div>

          {/* Messages (scrollable) */}
          <div className="flex-1 overflow-y-auto min-h-0 px-3 py-3 flex flex-col gap-2.5 scroll-smooth">
            {messages.map(m => <Message key={m.id} msg={m} />)}
            {thinking && <Thinking />}
            <div ref={chatEnd} />
          </div>

          {/* Input area */}
          <div className="shrink-0 px-3 py-2.5 border-t border-white/[0.06]">
            <div className="flex items-end gap-1.5">
              <button
                onClick={toggleVoice}
                className={`shrink-0 w-8 h-8 rounded-lg flex items-center justify-center transition-all duration-200 cursor-pointer ${
                  recording
                    ? "bg-red-500/20 text-red-400 border border-red-500/30 animate-pulse"
                    : "bg-white/[0.03] text-white/25 border border-white/[0.05] hover:text-white/50"
                }`}
                title="Voice input"
              >
                <Icon.Mic size={15} />
              </button>

              <textarea
                ref={inputRef}
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={onKey}
                placeholder="Ask about your screen..."
                rows={1}
                className="flex-1 bg-white/[0.03] border border-white/[0.05] rounded-xl px-3.5 py-2 text-[13px] text-white/85 placeholder-white/15 resize-none outline-none focus:border-violet-500/30 transition-colors leading-relaxed"
                style={{ maxHeight: 100, minHeight: 36 }}
              />

              <button
                onClick={send}
                disabled={!input.trim() || thinking}
                className="shrink-0 w-8 h-8 rounded-lg bg-violet-600 flex items-center justify-center text-white transition-all duration-200 hover:bg-violet-500 disabled:opacity-25 disabled:cursor-not-allowed cursor-pointer"
              >
                <Icon.Send size={14} />
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* ═══ FOOTER ════════════════════════════════════════════ */}
      <footer className="shrink-0 h-8 flex items-center justify-between px-4 bg-[#0f1119] border-t border-white/[0.06] text-[9px] text-white/15 font-mono">
        <div className="flex gap-4">
          <span>Frames <span className="text-white/25">{stats.frames}</span></span>
          <span>Turns <span className="text-white/25">{stats.turns}</span></span>
          <span>Agent <span className={agentConnected ? "text-emerald-400/40" : "text-white/25"}>{agentConnected ? "Connected" : "Offline"}</span></span>
        </div>
        <div className="flex gap-3">
          <span>{user?.plan || "free"}</span>
          <span>Tokens <span className="text-white/25">{stats.tokens.toLocaleString()}</span></span>
        </div>
      </footer>
    </div>
  );
}
