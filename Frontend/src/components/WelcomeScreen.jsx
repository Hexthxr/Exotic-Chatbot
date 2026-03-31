import React from 'react';

const QUICK_PROMPTS = [
  'Leopard Gecko ดูแลยังไงสำหรับมือใหม่',
  'Ball Python เลี้ยงได้ในไทยไหม ต้องมีใบอนุญาตไหม',
  'Axolotl ต้องการสภาพแวดล้อมแบบไหน',
  'Tarantula ชนิดไหนเหมาะสำหรับผู้เริ่มต้น',
  'กฎหมายสัตว์ exotic ในประเทศไทย',
  'Chameleon เลี้ยงยากแค่ไหน',
];

export default function WelcomeScreen({ onQuickSend }) {
  return (
    <div className="welcome-wrap">
      <div className="welcome-mark">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round">
          <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2z"/>
          <path d="M8 14s1.5 2 4 2 4-2 4-2"/>
          <path d="M9 9h.01M15 9h.01"/>
          <path d="M7 7c.5-1.5 2-2.5 5-2.5s4.5 1 5 2.5"/>
        </svg>
      </div>

      <h2>ExoticMate</h2>

      <span className="welcome-tagline">Exotic Animal Knowledge Assistant</span>

      <p>
        ให้ความรู้เรื่องสัตว์ exotic ครบจบที่เดียว<br/>
        ชื่อวิทยาศาสตร์ ลักษณะพิเศษ การดูแล และสถานะกฎหมายไทย
      </p>

      <div className="welcome-divider" />

      <div className="welcome-chips">
        {QUICK_PROMPTS.map((q, i) => (
          <button key={i} className="welcome-chip" onClick={() => onQuickSend(q)}>
            {q}
          </button>
        ))}
      </div>
    </div>
  );
}
