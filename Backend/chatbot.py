from google import genai
import os
from dotenv import load_dotenv

load_dotenv()  # พอแล้ว ไม่ต้อง path ก็ได้ถ้าอยู่ root

api_key = os.getenv("GEMINI_API_KEY")
print("DEBUG KEY:", api_key)  # เช็ค

client = genai.Client(api_key=api_key)

def ask_chatbot(user_input):
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=user_input
        )
        return response.text

    except Exception as e:
        print("ERROR:", e)
        return "ระบบมีปัญหา กรุณาลองใหม่"