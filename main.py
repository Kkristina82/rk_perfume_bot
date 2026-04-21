import os
import asyncio
import yt_dlp
import firebase_admin
from firebase_admin import credentials, db
from threading import Thread
from flask import Flask
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# --- ІНІЦІАЛІЗАЦІЯ FIREBASE ---
FIREBASE_URL = "https://rkbot-db5d6-default-rtdb.firebaseio.com/"

cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': FIREBASE_URL
})

db_last_video = db.reference('last_video_id')

# --- НАЛАШТУВАННЯ БОТА ---
TOKEN = "8700486318:AAHnhE4UNKwQKPGT0ZlW-VPfX906z95heCE"
CHANNEL_ID = "@rkperfume"
TIKTOK_PROFILE = "https://www.tiktok.com/@rk.perfume.krop"

# ВАШ КОНКРЕТНИЙ ID ДЛЯ ЗВІТІВ
ADMIN_ID = 7443699603 

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- СЕКЦІЯ RENDER / FLASK ---
app = Flask('')
@app.route('/')
def home(): return "Bot is running!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    Thread(target=run_web).start()

# --- ЛОГІКА ТА ОБРОБНИКИ ---

async def post_and_notify(video_url, v_id, desc):
    file_name = 'temp_video.mp4'
    ydl_opts = {'format': 'bestvideo+bestaudio/best', 'outtmpl': file_name, 'quiet': True}
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([video_url])
    
    caption = (
        f"🌟 <b>Нова публікація в TikTok</b>\n\n"
        f"📝 {desc}\n\n"
        f"👤 <a href='{TIKTOK_PROFILE}'><b>Наш профіль</b></a>"
    )

    # 1. Публікація в канал
    with open(file_name, 'rb') as video:
        await bot.send_video(
            chat_id=CHANNEL_ID,
            video=types.BufferedInputFile(video.read(), filename="video.mp4"),
            caption=caption,
            parse_mode=ParseMode.HTML
        )
    
    # 2. Відправка звіту на ваш ID
    try:
        await bot.send_message(
            chat_id=ADMIN_ID, 
            text=f"✅ <b>Відео успішно опубліковано!</b>\n🔗 {video_url}",
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        print(f"Помилка відправки звіту на {ADMIN_ID}: {e}")

    if os.path.exists(file_name):
        os.remove(file_name)

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🔍 Перевірити останні пости")]],
        resize_keyboard=True
    )
    await message.answer(f"Привіт! Звіти будуть приходити на ID: {ADMIN_ID}", reply_markup=kb)

@dp.message(F.text == "🔍 Перевірити останні пости")
async def manual_check(message: types.Message):
    status = await message.answer("Перевіряю TikTok... ⏳")
    
    # Отримання даних через yt-dlp
    ydl_opts = {'extract_flat': True, 'quiet': True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        result = ydl.extract_info(TIKTOK_PROFILE, download=False)
        if 'entries' in result and len(result['entries']) > 0:
            latest = result['entries'][0]
            url, v_id, desc = latest['url'], latest['id'], latest.get('title', 'Без опису')
            
            if v_id != db_last_video.get():
                await post_and_notify(url, v_id, desc)
                db_last_video.set(v_id)
                await status.edit_text("Знайдено нове відео! Опубліковано. 🚀")
            else:
                await status.edit_text("Нових відео поки немає. ✅")

async def auto_check_loop():
    while True:
        try:
            ydl_opts = {'extract_flat': True, 'quiet': True}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                result = ydl.extract_info(TIKTOK_PROFILE, download=False)
                if 'entries' in result and len(result['entries']) > 0:
                    latest = result['entries'][0]
                    v_id = latest['id']
                    if v_id != db_last_video.get():
                        await post_and_notify(latest['url'], v_id, latest.get('title', 'Без опису'))
                        db_last_video.set(v_id)
        except Exception as e:
            print(f"Цикл: {e}")
        await asyncio.sleep(3600)

async def main():
    keep_alive()
    asyncio.create_task(auto_check_loop())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
