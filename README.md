# ExoticMate — Exotic Animal Knowledge Chatbot

แชทบอทให้ความรู้เกี่ยวกับสัตว์ exotic ครอบคลุมชื่อวิทยาศาสตร์ ลักษณะพิเศษ การดูแล และสถานะทางกฎหมายในประเทศไทย

---

## Features

- ข้อมูลสัตว์ exotic กว่า 100+ ชนิด (สัตว์เลื้อยคลาน แมงมุม นกประดับ สัตว์น้ำ ฯลฯ)
- ชื่อวิทยาศาสตร์และชื่อสามัญครบถ้วน
- สถานะทางกฎหมายไทย (พ.ร.บ.สงวนและคุ้มครองสัตว์ป่า พ.ศ. 2562, CITES)
- บันทึกประวัติการสนทนาใน localStorage
- Responsive รองรับ mobile
- ธีมสีวานิลา + ฟ้าอ่อน

---

## Tech Stack

| Layer    | Technology                  |
|----------|-----------------------------|
| Frontend | React 18, Vite              |
| Backend  | Node.js, Express            |
| AI       | Anthropic Claude (claude-sonnet-4) |
| Style    | Pure CSS (CSS Variables)    |

---

## Project Structure

```
exotic-chatbot/
├── .gitignore
├── package.json
├── README.md
├── client/
│   ├── index.html
│   ├── vite.config.js
│   ├── package.json
│   └── src/
│       ├── main.jsx
│       ├── App.jsx
│       ├── index.css
│       └── components/
│           ├── Sidebar.jsx
│           ├── ChatMessage.jsx
│           ├── TypingIndicator.jsx
│           └── WelcomeScreen.jsx
└── server/
    ├── .env.example
    ├── package.json
    └── src/
        └── index.js
```

---

## Getting Started

### 1. Clone & install

```bash
git clone <your-repo-url>
cd exotic-chatbot
npm run install:all
```

### 2. Set up environment variables

```bash
cp server/.env.example server/.env
```

แก้ไขไฟล์ `server/.env`:

```env
ANTHROPIC_API_KEY=your_anthropic_api_key_here
PORT=3001
CLIENT_URL=http://localhost:5173
```

### 3. Run development server

```bash
npm run dev
```

- Frontend: http://localhost:5173
- Backend API: http://localhost:3001

---

## API Endpoints

| Method | Path         | Description             |
|--------|--------------|-------------------------|
| POST   | /api/chat    | Send message to chatbot |
| GET    | /api/health  | Health check            |

### POST /api/chat

**Request body:**
```json
{
  "messages": [
    { "role": "user", "content": "Leopard Gecko ดูแลยังไง" }
  ]
}
```

**Response:**
```json
{
  "reply": "..."
}
```

---

## Legal Information Coverage

ระบบครอบคลุมข้อมูลกฎหมายจาก:
- **พ.ร.บ.สงวนและคุ้มครองสัตว์ป่า พ.ศ. 2562**
- **CITES Appendix I, II, III**
- **พ.ร.บ.โรคระบาดสัตว์ พ.ศ. 2558**

---

## License

For educational purposes only.
