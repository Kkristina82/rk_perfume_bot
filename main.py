import os
import asyncio
import yt_dlp
from threading import Thread
from flask import Flask
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# --- НАЛАШТУВАННЯ ---
TOKEN = "8700486318:AAHnhE4UNKwQKPGT0ZlW-VPfX906z95heCE"
CHANNEL_ID = "@rkperfume"
TIKTOK_PROFILE = "https://www.tiktok.com/@rk.perfume.krop"
ADMIN_ID = 7443699603 
ID_FILE = "last_video_id.txt"  # Файл для збереження ID останнього відео

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- РОБОТА З ЛОКАЛЬНИМ ФАЙЛОМ ---
def get_last_id():
    if os.path.exists(ID_FILE):
        with open(ID_FILE, "r") as f:
            return f.read().strip()
    return None

def save_last_id(video_id):
    with open(ID_FILE, "w") as f:
        f.write(str(video_id))

# --- СЕКЦІЯ KEEP ALIVE (ДЛЯ RENDER/REPLIT) ---
app = Flask('')
@app.route('/')
def home(): return "Bot is running!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    Thread(target=run_web, daemon=True).start()

# --- ЛОГІКА ЗАВАНТАЖЕННЯ ТА ПОСТИНГУ ---
async def post_and_notify(video_url, v_id, desc):
    file_name = f'video_{v_id}.mp4'
    # Налаштування для завантаження саме відео файлу
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': file_name,
        'quiet': True
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
        
        caption = (
            f"🌟 <b>Нова публікація в TikTok</b>\n\n"
            f"📝 {desc}\n\n"
            f"👤 <a href='{TIKTOK_PROFILE}'><b>Наш профіль</b></a>"
        )

        # Публікація в канал
        with open(file_name, 'rb') as video:
            await bot.send_video(
                chat_id=CHANNEL_ID,
                video=types.BufferedInputFile(video.read(), filename="video.mp4"),
                caption=caption,
                parse_mode=ParseMode.HTML
            )
        
        # Звіт адміну
        await bot.send_message(ADMIN_ID, f"✅ Опубліковано: {video_url}")
        
        # Оновлюємо ID тільки після успішної публікації
        save_last_id(v_id)

    except Exception as e:
        print(f"Помилка публікації: {e}")
        await bot.send_message(ADMIN_ID, f"❌ Помилка при завантаженні: {e}")
    
    finally:
        if os.path.exists(file_name):
            os.remove(file_name)

async def check_tiktok():
    ydl_opts = {'extract_flat': True, 'quiet': True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        result = ydl.extract_info(TIKTOK_PROFILE, download=False)
        if 'entries' in result and len(result['entries']) > 0:
            latest = result['entries'][0]
            v_id = latest['id']
            url = latest['url']
            desc = latest.get('title', 'Без опису')
            
            if v_id != get_last_id():
                await post_and_notify(url, v_id, desc)
                return True
    return False

# --- ОБРОБНИКИ КОМАНД ---
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🔍 Перевірити TikTok")]],
        resize_keyboard=True
    )
    await message.answer(f"Бот працює. Останній збережений ID: {get_last_id()}", reply_markup=kb)

@dp.message(F.text == "🔍 Перевірити TikTok")
async def manual_check(message: types.Message):
    await message.answer("Шукаю нові відео... ⏳")
    found = await check_tiktok()
    if not found:
        await message.answer("Нових відео не знайдено. ✅")

async def auto_check_loop():
    while True:
        try:
            await check_tiktok()
        except Exception as e:
            print(f"Помилка в циклі: {e}")
        await asyncio.sleep(1800) # Перевірка кожні 30 хвилин

async def main():
    keep_alive()
    # Запускаємо фонову перевірку
    asyncio.create_task(auto_check_loop())
    # Запускаємо бота
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
