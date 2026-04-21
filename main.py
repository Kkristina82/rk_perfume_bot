import os
import asyncio
import yt_dlp
import uuid
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
HISTORY_FILE = "history.txt" # Зберігаємо список ID
CHECK_INTERVAL = 300 

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- РОБОТА З ІСТОРІЄЮ ---
def get_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            return f.read().splitlines()
    return []

def save_to_history(video_id):
    history = get_history()
    history.append(video_id)
    # Зберігаємо тільки останні 20 записів, щоб файл не розростався
    with open(HISTORY_FILE, "w") as f:
        f.write("\n".join(history[-20:]))

# --- ВЕБ-СЕРВЕР ---
app = Flask('')
@app.route('/')
def home(): return "Бот на варті контенту! 🔥"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    Thread(target=run_web, daemon=True).start()

# --- ФУНКЦІЯ ПУБЛІКАЦІЇ ---
async def download_and_send(video_url, desc):
    file_name = f"video_{uuid.uuid4().hex[:8]}.mp4"
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': file_name,
        'quiet': True,
        'no_warnings': True,
        'referer': 'https://www.tiktok.com/',
    }
    
    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: yt_dlp.YoutubeDL(ydl_opts).download([video_url]))
        
        caption = (
            f"✨ <b>ПОДИВІТЬСЯ ЦЕ ВІДЕО</b>\n"
            f"────────────────────\n\n"
            f"📝 {desc}\n\n"
            f"💎 <i>Свіжий контент для вас</i>"
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
        return True
    except Exception as e:
        print(f"Помилка: {e}")
        return False
    finally:
        if os.path.exists(file_name):
            os.remove(file_name)

# --- ЧІТКА ПЕРЕВІРКА ---
async def smart_check(limit=5):
    """Шукає нові відео серед останніх 'limit' публікацій"""
    ydl_opts = {'extract_flat': True, 'quiet': True}
    new_count = 0
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, lambda: ydl.extract_info(TIKTOK_PROFILE, download=False))
            
            if 'entries' in result:
                # Беремо останні limit відео
                latest_entries = result['entries'][:limit]
                # Розвертаємо, щоб публікувати від старіших до найновіших
                latest_entries.reverse()
                
                history = get_history()
                
                for entry in latest_entries:
                    v_id = entry['id']
                    if v_id not in history:
                        print(f"Знайдено нове відео: {v_id}")
                        success = await download_and_send(entry['url'], entry.get('title', 'Без опису'))
                        if success:
                            save_to_history(v_id)
                            new_count += 1
                            await asyncio.sleep(5) # Пауза, щоб Telegram не спамив
    except Exception as e:
        print(f"Помилка моніторингу: {e}")
    return new_count

# --- ОБРОБНИКИ ---
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🚀 Перевірити TikTok зараз")]],
        resize_keyboard=True
    )
    await message.answer("<b>Бот у режимі чіткого моніторингу!</b>", reply_markup=kb, parse_mode=ParseMode.HTML)

@dp.message(F.text == "🚀 Перевірити TikTok зараз")
async def manual_check(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    msg = await message.answer("🔍 Сканую останні відео...")
    found = await smart_check(limit=5)
    await msg.edit_text(f"✅ Перевірку завершено. Опубліковано нових: {found}")

@dp.message(F.text.contains("tiktok.com"))
async def manual_link(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    url = message.text.strip()
    msg = await message.answer("📥 Завантажую за посиланням...")
    with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
        info = ydl.extract_info(url, download=False)
        if await download_and_send(url, info.get('title', 'Без опису')):
            # Додаємо в історію, щоб авто-чек не дублював
            save_to_history(info.get('id'))
            await msg.edit_text("✅ Опубліковано!")
        else:
            await msg.edit_text("❌ Помилка.")

# --- ЦИКЛ ---
async def auto_check_loop():
    # При першому запуску просто записуємо поточні відео в історію, 
    # щоб не спамити старим контентом, або публікуємо лише 1 найновіше.
    history = get_history()
    if not history:
        print("Перший запуск. Наповнюю історію...")
        await smart_check(limit=1) 
    
    while True:
        await asyncio.sleep(CHECK_INTERVAL)
        await smart_check(limit=5)

async def main():
    keep_alive()
    asyncio.create_task(auto_check_loop())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
