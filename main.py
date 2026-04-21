import os
import asyncio
import yt_dlp
from threading import Thread
from flask import Flask
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode

# --- СЕКЦІЯ ДЛЯ RENDER (KEEP ALIVE) ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is running!"

def run_web():
    # Render передає порт автоматично
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_web)
    t.start()
# ---------------------------------------

TOKEN = "8700486318:AAHnhE4UNKwQKPGT0ZlW-VPfX906z95heCE"
CHANNEL_ID = "@rkperfume"
TIKTOK_PROFILE = "https://www.tiktok.com/@rk.perfume.krop"

bot = Bot(token=TOKEN)
dp = Dispatcher()

def download_tiktok(url):
    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'outtmpl': 'video.mp4',
        'quiet': True,
        'no_warnings': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return info.get('description', 'Без опису'), 'video.mp4'

@dp.message()
async def handle_message(message: types.Message):
    if message.text and "tiktok.com" in message.text:
        status_msg = await message.answer("Зачекай, завантажую відео... ⏳")
        try:
            description, file_path = download_tiktok(message.text)
            
            caption = (
                f"🌟 <a href='{message.text}'><b>Нова публікація в TikTok</b></a>\n\n"
                f"📝 {description}\n\n"
                f"👤 <b>Наш профіль:</b> {TIKTOK_PROFILE}"
            )

            with open(file_path, 'rb') as video:
                await bot.send_video(
                    chat_id=CHANNEL_ID,
                    video=types.BufferedInputFile(video.read(), filename="video.mp4"),
                    caption=caption,
                    parse_mode=ParseMode.HTML
                )
            
            await status_msg.edit_text("✅ Відео опубліковано в каналі!")
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            await status_msg.edit_text(f"❌ Помилка: {e}")

async def main():
    # ЗАПУСКАЄМО ВЕБ-СЕРВЕР ПЕРЕД БОТОМ
    keep_alive() 
    print("Web server started, starting bot polling...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
