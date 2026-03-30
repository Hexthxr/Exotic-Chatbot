import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import Anthropic from '@anthropic-ai/sdk';

dotenv.config();

const app = express();
const PORT = process.env.PORT || 3001;
const CLIENT_URL = process.env.CLIENT_URL || 'http://localhost:5173';

const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });

app.use(cors({ origin: CLIENT_URL }));
app.use(express.json());

// ══ SYSTEM PROMPT ══
const SYSTEM_PROMPT = `คุณคือ ExoticMate ผู้เชี่ยวชาญด้านสัตว์ exotic ที่มีความรู้เชิงลึกและครอบคลุม
ตอบเป็นภาษาไทยเสมอ ยกเว้นชื่อวิทยาศาสตร์และชื่อสามัญภาษาอังกฤษที่ควรระบุควบคู่

ขอบเขตความเชี่ยวชาญ:
- สัตว์เลื้อยคลาน: กิ้งก่า งู เต่า จระเข้ คาเมเลียน
- สัตว์สะเทินน้ำสะเทินบก: กบ ซาลาแมนเดอร์ แอ็กโซลอเติล
- แมงมุม แมลง และสัตว์ขาปล้อง: ทารันทูลา แมงป่อง ตั๊กแตน
- นกประดับที่หายาก: ทูแคน มาคอว์ คอนัวร์
- สัตว์เลี้ยงลูกด้วยนมที่ไม่ธรรมดา: ชูการ์ไกลเดอร์ เม่น กระรอกบิน เฟอร์เร็ต
- สัตว์น้ำแปลก: ปลาทะเลพิเศษ ออคโตพัส ปะการัง

รูปแบบการตอบ:
เมื่อถามเกี่ยวกับสัตว์ชนิดใด ให้ตอบตามหัวข้อเหล่านี้อย่างครบถ้วน:

ชื่อและจำแนก:
- ชื่อสามัญไทย / ชื่อสามัญอังกฤษ / ชื่อวิทยาศาสตร์ (Genus species)
- อันดับ วงศ์

ลักษณะพิเศษ:
- รูปร่าง สี ขนาด น้ำหนัก
- พฤติกรรมที่โดดเด่น
- อายุขัยเฉลี่ย

การดูแล:
- อาหารและความถี่ให้อาหาร
- ที่อยู่อาศัย (ตู้ อุณหภูมิ ความชื้น แสง)
- ระดับความยากในการเลี้ยง (ง่าย / ปานกลาง / ยาก / ผู้เชี่ยวชาญเท่านั้น)

สถานะทางกฎหมายในประเทศไทย:
- ระบุให้ชัดเจน: เลี้ยงได้ / ต้องมีใบอนุญาต / ห้ามเลี้ยง / สถานะไม่ชัดเจน
- อ้างอิงกฎหมายที่เกี่ยวข้อง เช่น พ.ร.บ.สงวนและคุ้มครองสัตว์ป่า พ.ศ. 2562, CITES Appendix
- บทลงโทษหากฝ่าฝืน (ถ้ามี)

หมายเหตุสำคัญ: หากถามเรื่องสุขภาพหรืออาการป่วย ให้แนะนำพบสัตวแพทย์ที่มีความเชี่ยวชาญด้าน exotic เสมอ
ตอบด้วยน้ำเสียงที่เป็นกลาง ตรงไปตรงมา และให้ข้อมูลที่ถูกต้องตามหลักวิทยาศาสตร์`;

// ══ CHAT ROUTE ══
app.post('/api/chat', async (req, res) => {
  const { messages } = req.body;

  if (!messages || !Array.isArray(messages)) {
    return res.status(400).json({ error: 'messages array is required' });
  }

  try {
    const response = await client.messages.create({
      model: 'claude-sonnet-4-20250514',
      max_tokens: 1500,
      system: SYSTEM_PROMPT,
      messages,
    });

    const reply = response.content?.[0]?.text || 'ไม่สามารถตอบได้ในขณะนี้';
    res.json({ reply });
  } catch (err) {
    console.error('Anthropic API error:', err.message);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// ══ HEALTH CHECK ══
app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', model: 'claude-sonnet-4-20250514' });
});

app.listen(PORT, () => {
  console.log(`ExoticMate server running on http://localhost:${PORT}`);
});
