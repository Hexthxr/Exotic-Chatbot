import React, { useState } from 'react';

export default function AuthModal({ onClose, onAuth }) {
  const [tab,     setTab]     = useState('login');   // 'login' | 'register'
  const [form,    setForm]    = useState({ username: '', email: '', password: '' });
  const [error,   setError]   = useState('');
  const [loading, setLoading] = useState(false);

  const set = (k, v) => { setForm(f => ({ ...f, [k]: v })); setError(''); };

  const submit = async () => {
    setError('');
    if (!form.email || !form.password) { setError('กรุณากรอกข้อมูลให้ครบถ้วน'); return; }
    if (tab === 'register' && !form.username) { setError('กรุณากรอกชื่อผู้ใช้'); return; }

    setLoading(true);
    try {
      const endpoint = tab === 'login' ? '/auth/login' : '/auth/register';
      const body     = tab === 'login'
        ? { email: form.email, password: form.password }
        : { username: form.username, email: form.email, password: form.password };

      const res  = await fetch(`http://localhost:5000${endpoint}`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify(body),
      });
      const data = await res.json();

      if (!res.ok) { setError(data.error || 'เกิดข้อผิดพลาด'); return; }

      // บันทึก token + user ลง localStorage
      localStorage.setItem('exotic_token', data.token);
      localStorage.setItem('exotic_user',  JSON.stringify(data.user));
      onAuth(data.user, data.token);
      onClose();
    } catch {
      setError('ไม่สามารถเชื่อมต่อกับเซิร์ฟเวอร์ได้');
    } finally {
      setLoading(false);
    }
  };

  const handleKey = (e) => { if (e.key === 'Enter') submit(); };

  return (
    <div className="auth-overlay" onClick={onClose}>
      <div className="auth-modal" onClick={e => e.stopPropagation()}>

        {/* Header */}
        <div className="auth-header">
          <div className="auth-logo">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none"
              stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2z"/>
              <path d="M8 14s1.5 2 4 2 4-2 4-2"/>
              <path d="M9 9h.01M15 9h.01"/>
            </svg>
          </div>
          <div>
            <h2 className="auth-title">ExoticMate</h2>
            <p className="auth-subtitle">
              {tab === 'login' ? 'เข้าสู่ระบบเพื่อบันทึกประวัติการสนทนา' : 'สมัครสมาชิกฟรี'}
            </p>
          </div>
          <button className="auth-close" onClick={onClose}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
              stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>

        {/* Tabs */}
        <div className="auth-tabs">
          <button className={`auth-tab ${tab === 'login'    ? 'active' : ''}`} onClick={() => { setTab('login');    setError(''); }}>เข้าสู่ระบบ</button>
          <button className={`auth-tab ${tab === 'register' ? 'active' : ''}`} onClick={() => { setTab('register'); setError(''); }}>สมัครสมาชิก</button>
        </div>

        {/* Form */}
        <div className="auth-form">
          {tab === 'register' && (
            <div className="auth-field">
              <label>ชื่อผู้ใช้</label>
              <div className="auth-input-wrap">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
                  <circle cx="12" cy="7" r="4"/>
                </svg>
                <input
                  type="text" placeholder="เช่น exotic_lover" autoComplete="username"
                  value={form.username} onChange={e => set('username', e.target.value)} onKeyDown={handleKey}
                />
              </div>
            </div>
          )}

          <div className="auth-field">
            <label>อีเมล</label>
            <div className="auth-input-wrap">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/>
                <polyline points="22,6 12,13 2,6"/>
              </svg>
              <input
                type="email" placeholder="your@email.com" autoComplete="email"
                value={form.email} onChange={e => set('email', e.target.value)} onKeyDown={handleKey}
              />
            </div>
          </div>

          <div className="auth-field">
            <label>รหัสผ่าน</label>
            <div className="auth-input-wrap">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
                <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
              </svg>
              <input
                type="password" placeholder={tab === 'register' ? 'อย่างน้อย 6 ตัวอักษร' : '••••••••'}
                autoComplete={tab === 'login' ? 'current-password' : 'new-password'}
                value={form.password} onChange={e => set('password', e.target.value)} onKeyDown={handleKey}
              />
            </div>
          </div>

          {error && (
            <div className="auth-error">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
              </svg>
              {error}
            </div>
          )}

          <button className="auth-submit" onClick={submit} disabled={loading}>
            {loading
              ? <span className="auth-spinner"/>
              : (tab === 'login' ? 'เข้าสู่ระบบ' : 'สมัครสมาชิก')
            }
          </button>
        </div>

        {/* Footer note */}
        <p className="auth-note">
          {tab === 'login'
            ? <>ยังไม่มีบัญชี? <span onClick={() => { setTab('register'); setError(''); }}>สมัครสมาชิก</span></>
            : <>มีบัญชีอยู่แล้ว? <span onClick={() => { setTab('login'); setError(''); }}>เข้าสู่ระบบ</span></>
          }
        </p>

      </div>
    </div>
  );
}