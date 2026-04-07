import React, { useState, useRef, useEffect, useCallback } from 'react';
import Sidebar        from './components/Sidebar';
import ChatMessage    from './components/ChatMessage';
import TypingIndicator from './components/TypingIndicator';
import WelcomeScreen  from './components/WelcomeScreen';
import AuthModal      from './components/AuthModal';
import LoginPage      from './pages/LoginPage';
import RegisterPage   from './pages/RegisterPage';
import './auth.css';

const LOCAL_KEY = 'exotic_sessions_v1';
const API       = 'http://localhost:5000';

// ── localStorage helpers (guest mode) ─────────────────────────────────
function loadLocalSessions() {
  try { return JSON.parse(localStorage.getItem(LOCAL_KEY) || '[]'); } catch { return []; }
}
function saveLocalSessions(sessions) {
  localStorage.setItem(LOCAL_KEY, JSON.stringify(sessions));
}

const CHIP_PROMPTS = [
  'สัตว์ exotic ที่เลี้ยงได้โดยไม่ต้องมีใบอนุญาต',
  'Leopard Gecko',
  'Tarantula ชนิดแนะนำ',
  'Ball Python กฎหมายไทย',
  'Axolotl การดูแล',
  'กฎหมาย CITES ในไทย',
  'สัตว์เลื้อยคลานเหมาะกับมือใหม่',
];

export default function App() {
  // ── Auth state ────────────────────────────────────────────────────
  const [user,      setUser]      = useState(() => {
    try { return JSON.parse(localStorage.getItem('exotic_user') || 'null'); } catch { return null; }
  });
  const [token,     setToken]     = useState(() => localStorage.getItem('exotic_token') || null);
  const [showAuth,  setShowAuth]  = useState(false);
  const [authPage,  setAuthPage]  = useState(null); // null | 'login' | 'register'

  // ── Session / chat state ──────────────────────────────────────────
  const [sessions,     setSessions]     = useState([]);
  const [currentId,    setCurrentId]    = useState(null);   // MongoDB _id (login) or timestamp (guest)
  const [messages,     setMessages]     = useState([]);
  const [input,        setInput]        = useState('');
  const [isTyping,     setIsTyping]     = useState(false);
  const [sidebarOpen,  setSidebarOpen]  = useState(() => window.innerWidth > 768);
  const [searchQuery,  setSearchQuery]  = useState('');

  const chatEndRef  = useRef(null);
  const textareaRef = useRef(null);

  // ── Auto-scroll ───────────────────────────────────────────────────
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);

  // ── Load sessions on mount / when auth changes ────────────────────
  useEffect(() => {
    if (user && token) {
      fetchSessions();
    } else {
      setSessions(loadLocalSessions());
    }
    // Clear current chat when switching auth state
    setCurrentId(null);
    setMessages([]);
  }, [user, token]);   // eslint-disable-line

  // ── Verify token on page load ────────────────────────────────────
  useEffect(() => {
    if (!token) return;
    fetch(`${API}/auth/me`, { headers: { Authorization: `Bearer ${token}` } })
      .then(r => r.ok ? r.json() : Promise.reject())
      .then(u => { setUser(u); localStorage.setItem('exotic_user', JSON.stringify(u)); })
      .catch(() => { handleLogout(); });
  }, []);  // eslint-disable-line

  // ── Auth handlers ─────────────────────────────────────────────────
  const handleAuth = (newUser, newToken) => {
    setUser(newUser);
    setToken(newToken);
    setAuthPage(null);
    setShowAuth(false);
  };

  const handleLogout = () => {
    localStorage.removeItem('exotic_token');
    localStorage.removeItem('exotic_user');
    setUser(null);
    setToken(null);
    setCurrentId(null);
    setMessages([]);
    setSessions(loadLocalSessions());
  };

  // ── Fetch sessions from API (logged-in) ──────────────────────────
  const fetchSessions = useCallback(async () => {
    try {
      const res  = await fetch(`${API}/sessions`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      const data = await res.json();
      setSessions(Array.isArray(data) ? data : []);
    } catch { setSessions([]); }
  }, [token]);

  // ── Gemini history format ─────────────────────────────────────────
  const geminiHistory = messages.map(m => ({
    role:  m.role === 'user' ? 'user' : 'model',
    parts: [{ text: m.content }],
  }));

  // ── New chat ──────────────────────────────────────────────────────
  const newChat = useCallback(() => {
    setCurrentId(null);
    setMessages([]);
    if (window.innerWidth <= 768) setSidebarOpen(false);
    setTimeout(() => textareaRef.current?.focus(), 50);
  }, []);

  // ── Load chat ─────────────────────────────────────────────────────
  const loadChat = useCallback(async (id) => {
    if (user && token) {
      // Load from MongoDB
      try {
        const res  = await fetch(`${API}/sessions/${id}`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        const data = await res.json();
        if (data.msgs) {
          setCurrentId(id);
          setMessages(data.msgs);
        }
      } catch { console.error('Failed to load session'); }
    } else {
      // Load from localStorage
      const s = sessions.find(x => x.id === id);
      if (!s) return;
      setCurrentId(id);
      setMessages(s.msgs || []);
    }
    if (window.innerWidth <= 768) setSidebarOpen(false);
  }, [user, token, sessions]);

  // ── Delete chat ───────────────────────────────────────────────────
  const deleteChat = useCallback(async (id) => {
    if (user && token) {
      await fetch(`${API}/sessions/${id}`, {
        method:  'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
      setSessions(prev => prev.filter(x => x.id !== id));
    } else {
      setSessions(prev => {
        const next = prev.filter(x => x.id !== id);
        saveLocalSessions(next);
        return next;
      });
    }
    if (currentId === id) { setCurrentId(null); setMessages([]); }
  }, [user, token, currentId]);

  // ── Send message ──────────────────────────────────────────────────
  const sendMessage = useCallback(async (textOverride) => {
    const text = (textOverride ?? input).trim();
    if (!text || isTyping) return;

    const userMsg      = { role: 'user', content: text };
    const nextMessages = [...messages, userMsg];

    setMessages(nextMessages);
    setInput('');
    setIsTyping(true);
    if (textareaRef.current) textareaRef.current.style.height = 'auto';

    try {
      const headers = { 'Content-Type': 'application/json' };
      if (user && token) headers['Authorization'] = `Bearer ${token}`;

      const body = {
        message:    text,
        history:    geminiHistory,
        session_id: (user && token) ? currentId : undefined,
      };

      const res  = await fetch(`${API}/chat`, {
        method: 'POST', headers, body: JSON.stringify(body),
      });
      const data = await res.json();

      const botMsg       = { role: 'assistant', content: data.reply };
      const finalMessages = [...nextMessages, botMsg];
      setMessages(finalMessages);

      if (user && token) {
        // Update session ID (จาก backend ถ้าเป็น session ใหม่)
        const newSessionId = data.session_id || currentId;
        setCurrentId(newSessionId);

        // Refresh session list จาก API
        const titleIsNew = !currentId;
        if (titleIsNew) {
          // เพิ่ม session ใหม่เข้า list โดยไม่ต้อง refetch ทั้งหมด
          const newSession = {
            id:    newSessionId,
            title: text.slice(0, 42) + (text.length > 42 ? '…' : ''),
            time:  new Date().toISOString(),
          };
          setSessions(prev => [newSession, ...prev]);
        } else {
          // Update timestamp ของ session ปัจจุบัน
          setSessions(prev => prev.map(s =>
            s.id === newSessionId ? { ...s, time: new Date().toISOString() } : s
          ));
        }
      } else {
        // Guest mode → save to localStorage
        let chatId = currentId;
        if (!chatId) {
          chatId = Date.now().toString();
          const newSession = {
            id:    chatId,
            title: text.slice(0, 42) + (text.length > 42 ? '…' : ''),
            time:  new Date().toISOString(),
            msgs:  [],
          };
          setSessions(prev => {
            const next = [newSession, ...prev];
            saveLocalSessions(next);
            return next;
          });
          setCurrentId(chatId);
        }
        setSessions(prev => {
          const next = prev.map(s =>
            s.id === chatId
              ? { ...s, msgs: finalMessages, time: new Date().toISOString() }
              : s
          );
          saveLocalSessions(next);
          return next;
        });
      }

    } catch (err) {
      setMessages(prev => [
        ...prev,
        { role: 'assistant', content: 'เกิดข้อผิดพลาดในการเชื่อมต่อ กรุณาลองใหม่อีกครั้ง' },
      ]);
      console.error(err);
    } finally {
      setIsTyping(false);
      textareaRef.current?.focus();
    }
  }, [input, isTyping, currentId, messages, user, token]); // eslint-disable-line

  // ── Keyboard / textarea ───────────────────────────────────────────
  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
  };
  const handleInputChange = (e) => {
    setInput(e.target.value);
    e.target.style.height = 'auto';
    e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px';
  };

  // ── Render ────────────────────────────────────────────────────────
  return (
    <div className="layout">
      <Sidebar
        isOpen={sidebarOpen}
        sessions={sessions}
        currentId={currentId}
        onNewChat={newChat}
        onLoadChat={loadChat}
        onDeleteChat={deleteChat}
        onToggle={() => setSidebarOpen(p => !p)}
        searchQuery={searchQuery}
        onSearch={setSearchQuery}
        user={user}
        onShowAuth={() => setAuthPage('login')}
        onLogout={handleLogout}
      />

      <div className="main">
        {/* Topbar */}
        <header className="topbar">
          <button className="icon-btn" onClick={() => setSidebarOpen(p => !p)} title="เมนู">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none"
              stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="3" y1="6"  x2="21" y2="6"/>
              <line x1="3" y1="12" x2="21" y2="12"/>
              <line x1="3" y1="18" x2="21" y2="18"/>
            </svg>
          </button>
          <div className="logo-ring">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none"
              stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10"/>
              <path d="M9 9h.01M15 9h.01"/>
              <path d="M8 14s1.5 2 4 2 4-2 4-2"/>
            </svg>
          </div>
          <div className="topbar-title">
            <h1>ExoticMate</h1>
            <p>Exotic Animal Knowledge Assistant</p>
          </div>

          {/* Auth button in topbar */}
          {/* {user ? (
            <div className="topbar-user">
              <div className="topbar-avatar">{user.username.slice(0,2).toUpperCase()}</div>
              <span className="topbar-username">{user.username}</span>
            </div>
          ) : (
            <button className="topbar-login-btn" onClick={() => setAuthPage('login')}>
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none"
                stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"/>
                <polyline points="10 17 15 12 10 7"/>
                <line x1="15" y1="12" x2="3" y2="12"/>
              </svg>
              เข้าสู่ระบบ
            </button>
          )} */}

          <span className="badge-online"><i/>Online</span>
        </header>

        {/* Chips */}
        <div className="chips-bar">
          {CHIP_PROMPTS.map((q, i) => (
            <div key={i} className="chip" onClick={() => sendMessage(q)}>{q}</div>
          ))}
        </div>

        {/* Chat area */}
        <div className="chat-area">
          {messages.length === 0 ? (
            <WelcomeScreen onQuickSend={sendMessage} />
          ) : (
            messages.map((m, i) => (
              <ChatMessage key={i} role={m.role} content={m.content} />
            ))
          )}
          {isTyping && <TypingIndicator />}
          <div ref={chatEndRef} />
        </div>

        {/* Input */}
        <div className="input-bar">
          <div className="input-wrap">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={handleInputChange}
              onKeyDown={handleKeyDown}
              placeholder="ถามเกี่ยวกับสัตว์ exotic..."
              rows={1}
              disabled={isTyping}
            />
            <button
              className="send-btn"
              onClick={() => sendMessage()}
              disabled={isTyping || !input.trim()}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
                stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <line x1="22" y1="2" x2="11" y2="13"/>
                <polygon points="22 2 15 22 11 13 2 9 22 2"/>
              </svg>
            </button>
          </div>
          <p className="input-note">
            {user
              ? `บันทึกประวัติการสนทนาแล้ว • ${user.username}`
              : 'เข้าสู่ระบบเพื่อบันทึกประวัติการสนทนา'
            }
          </p>
        </div>
      </div>

      {/* Auth Modal (legacy, keep for compatibility) */}
      {showAuth && (
        <AuthModal
          onClose={() => setShowAuth(false)}
          onAuth={handleAuth}
        />
      )}

      {/* Login Page */}
      {authPage === 'login' && (
        <LoginPage
          onAuth={handleAuth}
          onGoRegister={() => setAuthPage('register')}
          onBack={() => setAuthPage(null)}
        />
      )}

      {/* Register Page */}
      {authPage === 'register' && (
        <RegisterPage
          onAuth={handleAuth}
          onGoLogin={() => setAuthPage('login')}
          onBack={() => setAuthPage(null)}
        />
      )}
    </div>
  );
}