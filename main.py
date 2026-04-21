import os
import asyncio
import yt_dlp
import uuid
import re
from threading import Thread
from flask import Flask
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# --- НАЛАШТУВАННЯ ---
TOKEN = "8700486318:AAHnhE4UNKwQKPGT0ZlW-VPfX906z95heCE"
CHANNEL_ID = "@rkperfume"
TIKTOK_PROFILE = "https://www.tiktok.com/@rk.perfume.krop"
ADMIN_ID = 7443699603 
HISTORY_FILE = "history.txt"
CHECK_INTERVAL = 300 

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- ПЕРЕВІРКА ПРАВ ---
def is_admin(user_id):
    return user_id == ADMIN_ID

# --- РОБОТА З ІСТОРІЄЮ ---
def get_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            return f.read().splitlines()
    return []

def save_to_history(video_id):
    history = get_history()
    if video_id not in history:
        history.append(video_id)
        with open(HISTORY_FILE, "w") as f:
            f.write("\n".join(history[-30:]))

# --- ВЕБ-СЕРВЕР ---
app = Flask('')
@app.route('/')
def home(): return "RK Perfume Bot is Active! 🚀"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    Thread(target=run_web, daemon=True).start()

# --- ГОЛОВНА ФУНКЦІЯ ЗАВАНТАЖЕННЯ ---
async def download_and_send(video_url, desc="Без опису"):
    file_name = f"video_{uuid.uuid4().hex[:8]}.mp4"
    
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': file_name,
        'quiet': True,
        'no_warnings': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'referer': 'https://www.tiktok.com/',
    }
    
    try:
        loop = asyncio.get_event_loop()
        # Отримуємо чисте посилання та інфо
        info = await loop.run_in_executor(None, lambda: yt_dlp.YoutubeDL(ydl_opts).extract_info(video_url, download=True))
        video_id = info.get('id')
        video_title = info.get('title', desc)

        caption = (
            f"✨ <b>ПОДИВІТЬСЯ ЦЕ ВІДЕО</b>\n"
            f"────────────────────\n\n"
            f"📝 {video_title}\n\n"
            f"💎 <i>Premium якість для вас</i>"
        )

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎬 Дивитись в TikTok", url=video_url)],
            [InlineKeyboardButton(text="👤 Наш профіль", url=TIKTOK_PROFILE)]
        ])

        with open(file_name, 'rb') as video:
            await bot.send_video(
                chat_id=CHANNEL_ID,
                video=types.BufferedInputFile(video.read(), filename="video.mp4"),
                caption=caption,
                reply_markup=kb,
                parse_mode=ParseMode.HTML
            )
        
        save_to_history(video_id)
        return True, video_id
    except Exception as e:
        print(f"Error: {e}")
        return False, str(e)
    finally:
        if os.path.exists(file_name):
            os.remove(file_name)

# --- АВТО-ПЕРЕВІРКА ---
async def smart_check(limit=5):
    ydl_opts = {'extract_flat': True, 'quiet': True, 'referer': 'https://www.tiktok.com/'}
    new_count = 0
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, lambda: ydl.extract_info(TIKTOK_PROFILE, download=False))
            
            if 'entries' in result:
                entries = result['entries'][:limit]
                entries.reverse()
                history = get_history()
                
                for entry in entries:
                    if entry['id'] not in history:
                        success, _ = await download_and_send(entry['url'], entry.get('title'))
                        if success: new_count += 1
                        await asyncio.sleep(5)
    except Exception as e:
        print(f"Monitoring error: {e}")
    return new_count

# --- ОБРОБНИКИ ---

@dp.message(Command("start"))
async def start(message: types.Message):
    if not is_admin(message.from_user.id): return
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🚀 Перевірити TikTok зараз")],
            [KeyboardButton(text="📦 Останні 3 відео")]
        ],
        resize_keyboard=True
    )
    await message.answer("<b>Бот готовий публікувати контент!</b>\n\nПросто кидай посилання на відео або тисни кнопку.", reply_markup=kb, parse_mode=ParseMode.HTML)

# Обробка посилань (будь-яких TikTok посилань)
@dp.message(F.text.regexp(r'(https?://\S*tiktok\.com\S*)'))
async def link_handler(message: types.Message):
    if not is_admin(message.from_user.id): return
    
    url = re.search(r'(https?://\S*tiktok\.com\S*)', message.text).group(0)
    status_msg = await message.answer("⏳ <b>Обробляю ваш запит...</b>", parse_mode=ParseMode.HTML)
    
    success, result = await download_and_send(url)
    
    if success:
        await status_msg.edit_text(f"✅ <b>Відео успішно опубліковано!</b>\nID: <code>{result}</code>", parse_mode=ParseMode.HTML)
    else:
        await status_msg.edit_text(f"❌ <b>Помилка публікації:</b>\n<code>{result}</code>", parse_mode=ParseMode.HTML)

@dp.message(F.text == "🚀 Перевірити TikTok зараз")
async def manual_btn(message: types.Message):
    if not is_admin(message.from_user.id): return
    m = await message.answer("🔍 Шукаю нові пости...")
    found = await smart_check(limit=2)
    await m.edit_text(f"Перевірку завершено. Опубліковано: {found}")

@dp.message(F.text == "📦 Останні 3 відео")
async def manual_bulk(message: types.Message):
    if not is_admin(message.from_user.id): return
    await message.answer("Завантажую останні 3 пости... 🚀")
    await smart_check(limit=3)

# --- ЗАПУСК ---
async def auto_loop():
    # Наповнюємо історію при старті, щоб не дублювати старе
    await smart_check(limit=1)
    while True:
        await asyncio.sleep(CHECK_INTERVAL)
        await smart_check(limit=5)

async def main():
    keep_alive()
    asyncio.create_task(auto_loop())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
