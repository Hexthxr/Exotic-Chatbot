import React, { useState } from 'react';
import './AuthPage.css';

const API = 'http://localhost:5000';

export default function LoginPage({ onAuth, onGoRegister, onBack }) {
  const [form,    setForm]    = useState({ email: '', password: '' });
  const [error,   setError]   = useState('');
  const [loading, setLoading] = useState(false);
  const [showPw,  setShowPw]  = useState(false);

  const set = (k, v) => { setForm(f => ({ ...f, [k]: v })); setError(''); };

  const submit = async () => {
    setError('');
    if (!form.email || !form.password) { setError('กรุณากรอกข้อมูลให้ครบถ้วน'); return; }
    setLoading(true);
    try {
      const res  = await fetch(`${API}/auth/login`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ email: form.email, password: form.password }),
      });
      const data = await res.json();
      if (!res.ok) { setError(data.error || 'เกิดข้อผิดพลาด'); return; }
      localStorage.setItem('exotic_token', data.token);
      localStorage.setItem('exotic_user',  JSON.stringify(data.user));
      onAuth(data.user, data.token);
    } catch {
      setError('ไม่สามารถเชื่อมต่อกับเซิร์ฟเวอร์ได้');
    } finally {
      setLoading(false);
    }
  };

  const handleKey = (e) => { if (e.key === 'Enter') submit(); };

  return (
    <div className="auth-page">
      {/* Decorative background */}
      <div className="auth-bg">
        <div className="auth-bg-orb orb-1" />
        <div className="auth-bg-orb orb-2" />
        <div className="auth-bg-orb orb-3" />
        <div className="auth-bg-leaves" aria-hidden="true">
          {[...Array(6)].map((_, i) => (
            <div key={i} className={`leaf leaf-${i+1}`} />
          ))}
        </div>
      </div>

      <div className="auth-split">
        {/* Left panel */}
        <div className="auth-panel auth-panel--brand">
          <div className="brand-content">
            <div className="brand-logo">
              <svg viewBox="0 0 56 56" fill="none" xmlns="http://www.w3.org/2000/svg">
                <circle cx="28" cy="28" r="27" stroke="rgba(255,255,255,0.3)" strokeWidth="1.5"/>
                <circle cx="28" cy="28" r="20" stroke="rgba(255,255,255,0.5)" strokeWidth="1"/>
                <path d="M28 12C19.16 12 12 19.16 12 28s7.16 16 16 16 16-7.16 16-16S36.84 12 28 12z" fill="rgba(255,255,255,0.12)" stroke="white" strokeWidth="1.5"/>
                <path d="M22 32s2 3 6 3 6-3 6-3" stroke="white" strokeWidth="2" strokeLinecap="round"/>
                <circle cx="23" cy="26" r="1.5" fill="white"/>
                <circle cx="33" cy="26" r="1.5" fill="white"/>
                <path d="M20 20c1-3 4-5 8-5s7 2 8 5" stroke="rgba(255,255,255,0.7)" strokeWidth="1.5" strokeLinecap="round"/>
              </svg>
            </div>
            <h1 className="brand-name">ExoticMate</h1>
            <p className="brand-tagline">Exotic Animal Knowledge Assistant</p>
            <div className="brand-divider" />
            <ul className="brand-features">
              <li>
                <span className="feature-icon">🦎</span>
                <span>ข้อมูลสัตว์ exotic ครบถ้วน</span>
              </li>
              <li>
                <span className="feature-icon">⚖️</span>
                <span>กฎหมาย CITES และกฎหมายไทย</span>
              </li>
              <li>
                <span className="feature-icon">💬</span>
                <span>บันทึกประวัติการสนทนา</span>
              </li>
              <li>
                <span className="feature-icon">🌿</span>
                <span>คำแนะนำการดูแลแบบผู้เชี่ยวชาญ</span>
              </li>
            </ul>
          </div>
          <div className="brand-footer-art" aria-hidden="true">
            <svg viewBox="0 0 300 120" fill="none" xmlns="http://www.w3.org/2000/svg">
              <ellipse cx="150" cy="110" rx="130" ry="18" fill="rgba(255,255,255,0.06)"/>
              {/* Gecko */}
              <g transform="translate(60,30)">
                <ellipse cx="0" cy="0" rx="12" ry="7" fill="rgba(255,255,255,0.15)" transform="rotate(-10)"/>
                <circle cx="-8" cy="-4" r="5" fill="rgba(255,255,255,0.18)"/>
                <line x1="12" y1="2" x2="30" y2="8" stroke="rgba(255,255,255,0.2)" strokeWidth="2" strokeLinecap="round"/>
                <line x1="-4" y1="5" x2="-10" y2="16" stroke="rgba(255,255,255,0.2)" strokeWidth="1.5" strokeLinecap="round"/>
                <line x1="4" y1="6" x2="6" y2="18" stroke="rgba(255,255,255,0.2)" strokeWidth="1.5" strokeLinecap="round"/>
              </g>
              {/* Snake */}
              <path d="M160 80 Q180 50 200 70 Q220 90 240 65" stroke="rgba(255,255,255,0.18)" strokeWidth="5" fill="none" strokeLinecap="round"/>
              {/* Leaf decorations */}
              <path d="M20 100 Q35 70 50 90" stroke="rgba(255,255,255,0.12)" strokeWidth="3" fill="none"/>
              <path d="M250 95 Q265 65 280 85" stroke="rgba(255,255,255,0.12)" strokeWidth="3" fill="none"/>
            </svg>
          </div>
        </div>

        {/* Right panel - form */}
        <div className="auth-panel auth-panel--form">
          <div className="auth-form-container">

            <div className="auth-form-header">
              {onBack && (
                <button className="auth-back-btn" onClick={onBack} aria-label="กลับ">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <polyline points="15 18 9 12 15 6"/>
                  </svg>
                  กลับ
                </button>
              )}
              <h2>ยินดีต้อนรับกลับ</h2>
              <p>เข้าสู่ระบบเพื่อเข้าถึงประวัติการสนทนาของคุณ</p>
            </div>

            <div className="auth-fields">
              {/* Email */}
              <div className="auth-field-group">
                <label htmlFor="email">อีเมล</label>
                <div className="auth-input-box">
                  <span className="input-icon">
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/>
                      <polyline points="22,6 12,13 2,6"/>
                    </svg>
                  </span>
                  <input
                    id="email"
                    type="email"
                    placeholder="your@email.com"
                    autoComplete="email"
                    value={form.email}
                    onChange={e => set('email', e.target.value)}
                    onKeyDown={handleKey}
                  />
                </div>
              </div>

              {/* Password */}
              <div className="auth-field-group">
                <div className="field-label-row">
                  <label htmlFor="password">รหัสผ่าน</label>
                </div>
                <div className="auth-input-box">
                  <span className="input-icon">
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
                      <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
                    </svg>
                  </span>
                  <input
                    id="password"
                    type={showPw ? 'text' : 'password'}
                    placeholder="••••••••"
                    autoComplete="current-password"
                    value={form.password}
                    onChange={e => set('password', e.target.value)}
                    onKeyDown={handleKey}
                  />
                  <button
                    type="button"
                    className="pw-toggle"
                    onClick={() => setShowPw(p => !p)}
                    tabIndex={-1}
                    aria-label={showPw ? 'ซ่อนรหัสผ่าน' : 'แสดงรหัสผ่าน'}
                  >
                    {showPw ? (
                      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/>
                        <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/>
                        <line x1="1" y1="1" x2="23" y2="23"/>
                      </svg>
                    ) : (
                      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                        <circle cx="12" cy="12" r="3"/>
                      </svg>
                    )}
                  </button>
                </div>
              </div>

              {error && (
                <div className="auth-error-box">
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                    <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
                  </svg>
                  {error}
                </div>
              )}

              <button className="auth-submit-btn" onClick={submit} disabled={loading}>
                {loading ? (
                  <span className="btn-spinner" />
                ) : (
                  <>
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"/>
                      <polyline points="10 17 15 12 10 7"/>
                      <line x1="15" y1="12" x2="3" y2="12"/>
                    </svg>
                    เข้าสู่ระบบ
                  </>
                )}
              </button>
            </div>

            <div className="auth-switch">
              <span>ยังไม่มีบัญชี?</span>
              <button className="auth-switch-btn" onClick={onGoRegister}>
                สมัครสมาชิกฟรี
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="9 18 15 12 9 6"/>
                </svg>
              </button>
            </div>

            <div className="auth-guest-hint">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
              </svg>
              สามารถใช้งานแบบ Guest ได้โดยไม่ต้องเข้าสู่ระบบ แต่จะไม่บันทึกประวัติ
            </div>

          </div>
        </div>
      </div>
    </div>
  );
}
