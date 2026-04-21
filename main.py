import os
import asyncio
import yt_dlp
import uuid
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
ID_FILE = "last_video_id.txt"
CHECK_INTERVAL = 300  # Перевірка кожні 5 хвилин (300 секунд)

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- ДОПОМІЖНІ ФУНКЦІЇ ---
def get_last_id():
    if os.path.exists(ID_FILE):
        with open(ID_FILE, "r") as f:
            return f.read().strip()
    return None

def save_last_id(video_id):
    with open(ID_FILE, "w") as f:
        f.write(str(video_id))

# --- ВЕБ-СЕРВЕР ДЛЯ RENDER ---
app = Flask('')
@app.route('/')
def home(): return "Бот активний!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    Thread(target=run_web, daemon=True).start()

# --- ЛОГІКА ПОСТИНГУ ---
async def download_and_send(video_url, desc, is_manual=False):
    file_name = f"video_{uuid.uuid4().hex[:8]}.mp4"
    
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': file_name,
        'quiet': True,
        'no_warnings': True,
    }
    
    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: yt_dlp.YoutubeDL(ydl_opts).download([video_url]))
        
        caption = (
            f"🎬 <b>Подивіться це відео</b>\n\n"
            f"📝 {desc}\n\n"
            f"👤 <a href='{TIKTOK_PROFILE}'><b>Наш TikTok</b></a>"
        )

        with open(file_name, 'rb') as video:
            await bot.send_video(
                chat_id=CHANNEL_ID,
                video=types.BufferedInputFile(video.read(), filename="video.mp4"),
                caption=caption,
                parse_mode=ParseMode.HTML
            )
        
        await bot.send_message(ADMIN_ID, f"✅ Відео опубліковано{' (вручну)' if is_manual else ''}!")
        return True

    except Exception as e:
        print(f"Помилка: {e}")
        return False
    
    finally:
        if os.path.exists(file_name):
            os.remove(file_name)

async def check_and_post_latest():
    ydl_opts = {'extract_flat': True, 'quiet': True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Використовуємо loop для асинхронності
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, lambda: ydl.extract_info(TIKTOK_PROFILE, download=False))
            
            if 'entries' in result and len(result['entries']) > 0:
                latest = result['entries'][0]
                v_id = latest['id']
                
                if v_id != get_last_id():
                    success = await download_and_send(latest['url'], latest.get('title', 'Без опису'))
                    if success:
                        save_last_id(v_id)
                        return True
    except Exception as e:
        print(f"Помилка моніторингу: {e}")
    return False

# --- ОБРОБНИКИ ---

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🔍 Перевірити зараз")]], resize_keyboard=True)
    await message.answer("Бот запущений! Надсилай посилання або чекай авто-постів.", reply_markup=kb)

@dp.message(F.text.contains("tiktok.com"))
async def manual_link(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    url = message.text.strip()
    msg = await message.answer("Завантажую... 📥")
    
    with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
        info = ydl.extract_info(url, download=False)
        if await download_and_send(url, info.get('title', 'Без опису'), is_manual=True):
            await msg.edit_text("Готово! 🚀")
        else:
            await msg.edit_text("Сталася помилка. ❌")

@dp.message(F.text == "🔍 Перевірити зараз")
async def manual_check(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    await message.answer("Шукаю нове... ⏳")
    if not await check_and_post_latest():
        await message.answer("Нових відео немає. ✅")

# --- ЦИКЛ ТА ЗАПУСК ---

async def auto_check_loop():
    # Перша перевірка відразу при підключенні
    print("Виконую першу перевірку...")
    await check_and_post_latest()
    
    while True:
        await asyncio.sleep(CHECK_INTERVAL)
        await check_and_post_latest()

async def main():
    keep_alive()
    # Запускаємо цикл як окрему задачу
    asyncio.create_task(auto_check_loop())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
