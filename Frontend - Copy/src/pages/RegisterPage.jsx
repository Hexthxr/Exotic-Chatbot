import React, { useState } from 'react';
import './AuthPage.css';

const API = 'http://localhost:5000';

export default function RegisterPage({ onAuth, onGoLogin, onBack }) {
  const [form,    setForm]    = useState({ username: '', email: '', password: '', confirm: '' });
  const [error,   setError]   = useState('');
  const [loading, setLoading] = useState(false);
  const [showPw,  setShowPw]  = useState(false);
  const [success, setSuccess] = useState(false);

  const set = (k, v) => { setForm(f => ({ ...f, [k]: v })); setError(''); };

  const getStrength = (pw) => {
    if (!pw) return 0;
    let score = 0;
    if (pw.length >= 6)  score++;
    if (pw.length >= 10) score++;
    if (/[A-Z]/.test(pw)) score++;
    if (/[0-9]/.test(pw)) score++;
    if (/[^A-Za-z0-9]/.test(pw)) score++;
    return score;
  };

  const strength = getStrength(form.password);
  const strengthLabel = ['', 'อ่อนแอมาก', 'อ่อนแอ', 'ปานกลาง', 'แข็งแกร่ง', 'แข็งแกร่งมาก'][strength];
  const strengthColor = ['', '#d86b6b', '#e8974a', '#e8c24a', '#5ba37c', '#2f7d5a'][strength];

  const submit = async () => {
    setError('');
    if (!form.username || !form.email || !form.password) { setError('กรุณากรอกข้อมูลให้ครบถ้วน'); return; }
    if (form.password.length < 6) { setError('รหัสผ่านต้องมีอย่างน้อย 6 ตัวอักษร'); return; }
    if (form.password !== form.confirm) { setError('รหัสผ่านไม่ตรงกัน'); return; }
    setLoading(true);
    try {
      const res  = await fetch(`${API}/auth/register`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ username: form.username, email: form.email, password: form.password }),
      });
      const data = await res.json();
      if (!res.ok) { setError(data.error || 'เกิดข้อผิดพลาด'); return; }
      setSuccess(true);
      setTimeout(() => {
        localStorage.setItem('exotic_token', data.token);
        localStorage.setItem('exotic_user',  JSON.stringify(data.user));
        onAuth(data.user, data.token);
      }, 1200);
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

      <div className="auth-split auth-split--reverse">
        {/* Left panel - form */}
        <div className="auth-panel auth-panel--form">
          <div className="auth-form-container">

            {success ? (
              <div className="auth-success">
                <div className="success-icon">
                  <svg viewBox="0 0 56 56" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <circle cx="28" cy="28" r="26" fill="var(--accent-soft)" stroke="var(--accent)" strokeWidth="2"/>
                    <path d="M18 28l8 8 14-16" stroke="var(--accent)" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                </div>
                <h2>สมัครสมาชิกสำเร็จ!</h2>
                <p>กำลังพาคุณเข้าสู่ระบบ...</p>
              </div>
            ) : (
              <>
                <div className="auth-form-header">
                  {onBack && (
                    <button className="auth-back-btn" onClick={onBack} aria-label="กลับ">
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                        <polyline points="15 18 9 12 15 6"/>
                      </svg>
                      กลับ
                    </button>
                  )}
                  <h2>สร้างบัญชีใหม่</h2>
                  <p>เริ่มต้นการสนทนากับ ExoticMate วันนี้</p>
                </div>

                <div className="auth-fields">
                  {/* Username */}
                  <div className="auth-field-group">
                    <label htmlFor="username">ชื่อผู้ใช้</label>
                    <div className="auth-input-box">
                      <span className="input-icon">
                        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
                          <circle cx="12" cy="7" r="4"/>
                        </svg>
                      </span>
                      <input
                        id="username"
                        type="text"
                        placeholder="เช่น exotic_lover"
                        autoComplete="username"
                        value={form.username}
                        onChange={e => set('username', e.target.value)}
                        onKeyDown={handleKey}
                      />
                    </div>
                  </div>

                  {/* Email */}
                  <div className="auth-field-group">
                    <label htmlFor="reg-email">อีเมล</label>
                    <div className="auth-input-box">
                      <span className="input-icon">
                        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/>
                          <polyline points="22,6 12,13 2,6"/>
                        </svg>
                      </span>
                      <input
                        id="reg-email"
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
                    <label htmlFor="reg-password">รหัสผ่าน</label>
                    <div className="auth-input-box">
                      <span className="input-icon">
                        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
                          <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
                        </svg>
                      </span>
                      <input
                        id="reg-password"
                        type={showPw ? 'text' : 'password'}
                        placeholder="อย่างน้อย 6 ตัวอักษร"
                        autoComplete="new-password"
                        value={form.password}
                        onChange={e => set('password', e.target.value)}
                        onKeyDown={handleKey}
                      />
                      <button
                        type="button"
                        className="pw-toggle"
                        onClick={() => setShowPw(p => !p)}
                        tabIndex={-1}
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
                    {form.password && (
                      <div className="pw-strength">
                        <div className="pw-strength-bar">
                          {[1,2,3,4,5].map(i => (
                            <div
                              key={i}
                              className="pw-strength-seg"
                              style={{ background: i <= strength ? strengthColor : 'var(--border-strong)' }}
                            />
                          ))}
                        </div>
                        <span style={{ color: strengthColor }}>{strengthLabel}</span>
                      </div>
                    )}
                  </div>

                  {/* Confirm Password */}
                  <div className="auth-field-group">
                    <label htmlFor="confirm">ยืนยันรหัสผ่าน</label>
                    <div className={`auth-input-box ${form.confirm && form.confirm !== form.password ? 'input-error' : ''} ${form.confirm && form.confirm === form.password ? 'input-ok' : ''}`}>
                      <span className="input-icon">
                        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
                        </svg>
                      </span>
                      <input
                        id="confirm"
                        type={showPw ? 'text' : 'password'}
                        placeholder="••••••••"
                        autoComplete="new-password"
                        value={form.confirm}
                        onChange={e => set('confirm', e.target.value)}
                        onKeyDown={handleKey}
                      />
                      {form.confirm && (
                        <span className="input-status">
                          {form.confirm === form.password ? (
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#2f7d5a" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                              <polyline points="20 6 9 17 4 12"/>
                            </svg>
                          ) : (
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#d86b6b" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                              <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
                            </svg>
                          )}
                        </span>
                      )}
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
                          <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
                          <circle cx="8.5" cy="7" r="4"/>
                          <line x1="20" y1="8" x2="20" y2="14"/><line x1="23" y1="11" x2="17" y2="11"/>
                        </svg>
                        สมัครสมาชิก
                      </>
                    )}
                  </button>
                </div>

                <div className="auth-switch">
                  <span>มีบัญชีอยู่แล้ว?</span>
                  <button className="auth-switch-btn" onClick={onGoLogin}>
                    เข้าสู่ระบบ
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                      <polyline points="9 18 15 12 9 6"/>
                    </svg>
                  </button>
                </div>
              </>
            )}
          </div>
        </div>

        {/* Right panel - brand */}
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
            <p className="brand-tagline">เพื่อนคู่ใจของนักเลี้ยงสัตว์ exotic</p>
            <div className="brand-divider" />
            <div className="brand-stats">
              <div className="stat-item">
                <span className="stat-num">250+</span>
                <span className="stat-lbl">ชนิดสัตว์</span>
              </div>
              <div className="stat-sep" />
              <div className="stat-item">
                <span className="stat-num">CITES</span>
                <span className="stat-lbl">ครอบคลุม</span>
              </div>
              <div className="stat-sep" />
              <div className="stat-item">
                <span className="stat-num">24/7</span>
                <span className="stat-lbl">พร้อมใช้งาน</span>
              </div>
            </div>
            <p className="brand-desc">
              ค้นหาข้อมูลสัตว์ exotic ทุกชนิด ตั้งแต่การดูแลรักษา ไปจนถึงกฎหมายในประเทศไทย ด้วย AI ที่เชี่ยวชาญเฉพาะด้าน
            </p>
          </div>
          <div className="brand-footer-art" aria-hidden="true">
            <svg viewBox="0 0 300 120" fill="none" xmlns="http://www.w3.org/2000/svg">
              <ellipse cx="150" cy="110" rx="130" ry="18" fill="rgba(255,255,255,0.06)"/>
              <g transform="translate(80,40)">
                <ellipse cx="0" cy="0" rx="14" ry="8" fill="rgba(255,255,255,0.15)" transform="rotate(-15)"/>
                <circle cx="-10" cy="-5" r="6" fill="rgba(255,255,255,0.18)"/>
                <line x1="14" y1="2" x2="35" y2="10" stroke="rgba(255,255,255,0.2)" strokeWidth="2.5" strokeLinecap="round"/>
              </g>
              <path d="M170 75 Q195 45 215 65 Q235 85 255 55" stroke="rgba(255,255,255,0.2)" strokeWidth="6" fill="none" strokeLinecap="round"/>
              <path d="M25 100 Q40 68 55 88" stroke="rgba(255,255,255,0.14)" strokeWidth="3.5" fill="none"/>
              <path d="M248 92 Q263 60 278 80" stroke="rgba(255,255,255,0.14)" strokeWidth="3.5" fill="none"/>
            </svg>
          </div>
        </div>
      </div>
    </div>
  );
}
