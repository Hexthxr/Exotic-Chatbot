import React from 'react';

function parseMarkdown(text) {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/\n\n/g, '<br/><br/>')
    .replace(/\n/g, '<br/>')
    .replace(/^- (.+)/gm, '<li>$1</li>')
    .replace(/(<li>[\s\S]*?<\/li>)/g, '<ul>$1</ul>');
}

export default function ChatMessage({ role, content }) {
  const isUser = role === 'user';

  return (
    <div className={`msg-row ${isUser ? 'user' : 'bot'}`}>
      <div className={`av ${isUser ? 'user' : 'bot'}`}>
        {isUser ? (
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
            <circle cx="12" cy="7" r="4"/>
          </svg>
        ) : (
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10"/>
            <path d="M9 9h.01M15 9h.01"/>
            <path d="M8 14s1.5 2 4 2 4-2 4-2"/>
          </svg>
        )}
      </div>
      <div className={`bubble ${isUser ? 'user' : 'bot'}`}>
        <div className="who">{isUser ? 'คุณ' : 'ExoticMate'}</div>
        <div dangerouslySetInnerHTML={{ __html: isUser ? content.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;') : parseMarkdown(content) }} />
      </div>
    </div>
  );
}
