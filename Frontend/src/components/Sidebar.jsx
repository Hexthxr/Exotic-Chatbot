import React, { useEffect, useState } from 'react';

function timeLbl(iso) {
  const d = new Date(iso), now = new Date();
  const diff = Math.floor((now - d) / 86400000);
  if (diff === 0) return 'วันนี้';
  if (diff === 1) return 'เมื่อวาน';
  if (diff < 7) return `${diff} วันที่แล้ว`;
  return d.toLocaleDateString('th-TH', { day: 'numeric', month: 'short' });
}

function groupByDate(sessions) {
  const groups = {};
  sessions.forEach(s => {
    const lbl = timeLbl(s.time);
    if (!groups[lbl]) groups[lbl] = [];
    groups[lbl].push(s);
  });
  return groups;
}

export default function Sidebar({ isOpen, sessions, currentId, onNewChat, onLoadChat, onDeleteChat, onToggle, searchQuery, onSearch }) {
  const [isMobile, setIsMobile] = useState(window.innerWidth <= 768);

  useEffect(() => {
    const handler = () => setIsMobile(window.innerWidth <= 768);
    window.addEventListener('resize', handler);
    return () => window.removeEventListener('resize', handler);
  }, []);

  const filtered = searchQuery
    ? sessions.filter(s => s.title.toLowerCase().includes(searchQuery.toLowerCase()))
    : sessions;

  const groups = groupByDate(filtered);

  return (
    <>
      {isMobile && isOpen && (
        <div className="sidebar-overlay show" onClick={onToggle} />
      )}

      <aside className={`sidebar ${isOpen ? 'open' : 'collapsed'}`}>

        <div className="sb-header">
          <div className="sb-logo">
            <div className="sb-logo-mark">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2z"/>
                <path d="M8 12c0-2.21 1.79-4 4-4s4 1.79 4 4-1.79 4-4 4-4-1.79-4-4z"/>
                <path d="M12 8V6M12 18v-2M8 12H6M18 12h-2"/>
              </svg>
            </div>
            <span className="sb-logo-text">ExoticMate</span>
          </div>
          <button className="icon-btn" onClick={onToggle} title="ปิด sidebar">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="3" y="3" width="18" height="18" rx="2"/>
              <line x1="9" y1="3" x2="9" y2="21"/>
            </svg>
          </button>
        </div>

        <button className="new-chat-btn" onClick={onNewChat}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <line x1="12" y1="5" x2="12" y2="19"/>
            <line x1="5" y1="12" x2="19" y2="12"/>
          </svg>
          แชทใหม่
        </button>

        <div className="sb-search">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
          </svg>
          <input
            type="text"
            placeholder="ค้นหาแชท..."
            value={searchQuery}
            onChange={e => onSearch(e.target.value)}
          />
        </div>

        <div className="sb-history">
          {filtered.length === 0 ? (
            <div className="history-empty">
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
              </svg>
              <p>{searchQuery ? 'ไม่พบแชทที่ค้นหา' : 'ยังไม่มีประวัติการสนทนา'}</p>
            </div>
          ) : (
            Object.entries(groups).map(([lbl, items]) => (
              <div key={lbl}>
                <div className="hist-label">{lbl}</div>
                {items.map(s => (
                  <div
                    key={s.id}
                    className={`chat-item ${s.id === currentId ? 'active' : ''}`}
                    onClick={() => onLoadChat(s.id)}
                  >
                    <div className="chat-item-icon">
                      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
                      </svg>
                    </div>
                    <div className="chat-item-body">
                      <div className="chat-item-title">{s.title}</div>
                      <div className="chat-item-time">{new Date(s.time).toLocaleTimeString('th-TH', { hour: '2-digit', minute: '2-digit' })}</div>
                    </div>
                    <button
                      className="chat-del"
                      title="ลบ"
                      onClick={e => { e.stopPropagation(); onDeleteChat(s.id); }}
                    >
                      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <polyline points="3 6 5 6 21 6"/>
                        <path d="M19 6l-1 14H6L5 6"/>
                        <path d="M10 11v6"/><path d="M14 11v6"/>
                      </svg>
                    </button>
                  </div>
                ))}
              </div>
            ))
          )}
        </div>

        <div className="sb-footer">
          <div className="sb-user">
            <div className="sb-avatar">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
                <circle cx="12" cy="7" r="4"/>
              </svg>
            </div>
            <span>ผู้ใช้งาน</span>
          </div>
        </div>

      </aside>
    </>
  );
}
