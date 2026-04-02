from google import genai
import os
from dotenv import load_dotenv

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def ask_chatbot(user_input):
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",  # ✅ ตัวนี้ใช้ได้แน่
            contents=user_input
        )

        return response.text

    except Exception as e:
        print("ERROR:", e)
        return "ระบบมีปัญหา กรุณาลองใหม่"
    
    