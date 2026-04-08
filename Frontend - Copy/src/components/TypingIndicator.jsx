import React from 'react';

export default function TypingIndicator() {
  return (
    <div className="typing-row">
      <div className="av bot">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="10"/>
          <path d="M9 9h.01M15 9h.01"/>
          <path d="M8 14s1.5 2 4 2 4-2 4-2"/>
        </svg>
      </div>
      <div className="typing-dots">
        <span/><span/><span/>
      </div>
    </div>
  );
}
