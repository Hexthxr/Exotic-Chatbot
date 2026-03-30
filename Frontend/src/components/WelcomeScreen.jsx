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
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2z"/>
          <path d="M8 14s1.5 2 4 2 4-2 4-2"/>
          <path d="M9 9h.01M15 9h.01"/>
        </svg>
      </div>
      <h2>ExoticMate</h2>
      <p>
        ผู้ช่วยความรู้ด้านสัตว์ exotic ให้ข้อมูลชื่อวิทยาศาสตร์<br/>
        ลักษณะพิเศษ การดูแล และสถานะทางกฎหมายในประเทศไทย
      </p>
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
