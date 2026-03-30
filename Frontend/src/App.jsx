import React, { useState, useRef, useEffect, useCallback } from 'react';
import Sidebar from './components/Sidebar';
import ChatMessage from './components/ChatMessage';
import TypingIndicator from './components/TypingIndicator';
import WelcomeScreen from './components/WelcomeScreen';

const STORAGE_KEY = 'exotic_sessions_v1';

function loadSessions() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
  } catch { return []; }
}

function saveSessions(sessions) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions));
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
  const [sessions, setSessions]     = useState(loadSessions);
  const [currentId, setCurrentId]   = useState(null);
  const [messages, setMessages]     = useState([]);
  const [input, setInput]           = useState('');
  const [isTyping, setIsTyping]     = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(() => window.innerWidth > 768);
  const [searchQuery, setSearchQuery] = useState('');

  const chatEndRef = useRef(null);
  const textareaRef = useRef(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);

  const persistSession = useCallback((id, msgs) => {
    setSessions(prev => {
      const next = prev.map(s =>
        s.id === id ? { ...s, msgs, time: new Date().toISOString() } : s
      );
      saveSessions(next);
      return next;
    });
  }, []);

  const newChat = useCallback(() => {
    const id = Date.now().toString();
    const session = { id, title: 'แชทใหม่', time: new Date().toISOString(), msgs: [] };
    setSessions(prev => {
      const next = [session, ...prev];
      saveSessions(next);
      return next;
    });
    setCurrentId(id);
    setMessages([]);
    if (window.innerWidth <= 768) setSidebarOpen(false);
    setTimeout(() => textareaRef.current?.focus(), 50);
  }, []);

  const loadChat = useCallback((id) => {
    const s = sessions.find(x => x.id === id);
    if (!s) return;
    setCurrentId(id);
    setMessages(s.msgs || []);
    if (window.innerWidth <= 768) setSidebarOpen(false);
  }, [sessions]);

  const deleteChat = useCallback((id) => {
    setSessions(prev => {
      const next = prev.filter(x => x.id !== id);
      saveSessions(next);
      return next;
    });
    if (currentId === id) { setCurrentId(null); setMessages([]); }
  }, [currentId]);

  const autoTitle = useCallback((id, text) => {
    setSessions(prev => {
      const next = prev.map(s =>
        s.id === id && s.title === 'แชทใหม่'
          ? { ...s, title: text.slice(0, 42) + (text.length > 42 ? '…' : '') }
          : s
      );
      saveSessions(next);
      return next;
    });
  }, []);

  const sendMessage = useCallback(async (textOverride) => {
    const text = (textOverride ?? input).trim();
    if (!text || isTyping) return;

    let chatId = currentId;
    if (!chatId) {
      chatId = Date.now().toString();
      const session = { id: chatId, title: 'แชทใหม่', time: new Date().toISOString(), msgs: [] };
      setSessions(prev => {
        const next = [session, ...prev];
        saveSessions(next);
        return next;
      });
      setCurrentId(chatId);
    }

    const userMsg = { role: 'user', content: text };
    const nextMessages = [...messages, userMsg];

    setMessages(nextMessages);
    setInput('');
    setIsTyping(true);
    autoTitle(chatId, text);

    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: nextMessages.map(m => ({ role: m.role, content: m.content }))
        }),
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Server error');

      const botMsg = { role: 'assistant', content: data.reply };
      const finalMessages = [...nextMessages, botMsg];
      setMessages(finalMessages);
      persistSession(chatId, finalMessages);

    } catch (err) {
      const errMsg = { role: 'assistant', content: 'เกิดข้อผิดพลาดในการเชื่อมต่อกับเซิร์ฟเวอร์ กรุณาลองใหม่อีกครั้ง' };
      setMessages(prev => [...prev, errMsg]);
      console.error(err);
    } finally {
      setIsTyping(false);
      textareaRef.current?.focus();
    }
  }, [input, isTyping, currentId, messages, autoTitle, persistSession]);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const handleInputChange = (e) => {
    setInput(e.target.value);
    e.target.style.height = 'auto';
    e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px';
  };

  const toggleSidebar = () => {
    setSidebarOpen(p => !p);
  };

  return (
    <div className="layout">
      <Sidebar
        isOpen={sidebarOpen}
        sessions={sessions}
        currentId={currentId}
        onNewChat={newChat}
        onLoadChat={loadChat}
        onDeleteChat={deleteChat}
        onToggle={toggleSidebar}
        searchQuery={searchQuery}
        onSearch={setSearchQuery}
      />

      <div className="main">
        {/* Topbar */}
        <header className="topbar">
          <button className="icon-btn" onClick={toggleSidebar} title="เมนู">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="3" y1="6" x2="21" y2="6"/>
              <line x1="3" y1="12" x2="21" y2="12"/>
              <line x1="3" y1="18" x2="21" y2="18"/>
            </svg>
          </button>
          <div className="logo-ring">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10"/>
              <path d="M9 9h.01M15 9h.01"/>
              <path d="M8 14s1.5 2 4 2 4-2 4-2"/>
            </svg>
          </div>
          <div className="topbar-title">
            <h1>ExoticMate</h1>
            <p>Exotic Animal Knowledge Assistant</p>
          </div>
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
            <button className="send-btn" onClick={() => sendMessage()} disabled={isTyping || !input.trim()}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <line x1="22" y1="2" x2="11" y2="13"/>
                <polygon points="22 2 15 22 11 13 2 9 22 2"/>
              </svg>
            </button>
          </div>
          <p className="input-note">ExoticMate ให้ข้อมูลทั่วไป — ปรึกษาสัตวแพทย์สำหรับปัญหาสุขภาพ</p>
        </div>
      </div>
    </div>
  );
}
