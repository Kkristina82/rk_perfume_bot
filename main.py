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
CHECK_INTERVAL = 300  # 5 хвилин

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- РОБОТА З ФАЙЛОМ ---
def get_last_id():
    if os.path.exists(ID_FILE):
        with open(ID_FILE, "r") as f:
            return f.read().strip()
    return None

def save_last_id(video_id):
    with open(ID_FILE, "w") as f:
        f.write(str(video_id))

# --- ВЕБ-СЕРВЕР ---
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
        
        # Оновлений підпис із посиланням на конкретне відео
        caption = (
            f"🎬 <b>Подивіться це відео</b>\n\n"
            f"📝 {desc}\n\n"
            f"🔗 <a href='{video_url}'><b>Посилання на відео</b></a>\n"
            f"👤 <a href='{TIKTOK_PROFILE}'><b>Наш TikTok профіль</b></a>"
        )

        with open(file_name, 'rb') as video:
            await bot.send_video(
                chat_id=CHANNEL_ID,
                video=types.BufferedInputFile(video.read(), filename="video.mp4"),
                caption=caption,
                parse_mode=ParseMode.HTML
            )
        return True
    except Exception as e:
        print(f"Помилка завантаження: {e}")
        return False
    finally:
        if os.path.exists(file_name):
            os.remove(file_name)

async def check_and_post(count=1):
    ydl_opts = {'extract_flat': True, 'quiet': True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, lambda: ydl.extract_info(TIKTOK_PROFILE, download=False))
            
            if 'entries' in result and len(result['entries']) > 0:
                entries_to_post = result['entries'][:count]
                entries_to_post.reverse() 
                
                last_saved = get_last_id()
                new_videos_found = 0

                for entry in entries_to_post:
                    v_id = entry['id']
                    if v_id != last_saved:
                        success = await download_and_send(entry['url'], entry.get('title', 'Без опису'))
                        if success:
                            save_last_id(v_id)
                            last_saved = v_id
                            new_videos_found += 1
                            await asyncio.sleep(2)
                
                return new_videos_found
    except Exception as e:
        print(f"Помилка моніторингу: {e}")
    return 0

# --- ОБРОБНИКИ ---

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Запостити останнє")],
            [KeyboardButton(text="Останні 2"), KeyboardButton(text="Останні 3")]
        ],
        resize_keyboard=True
    )
    await message.answer("Бот готовий. Вибери кількість відео для посту або просто скинь посилання на відео!", reply_markup=kb)

@dp.message(F.text.contains("tiktok.com"))
async def manual_link(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    url = message.text.strip()
    msg = await message.answer("Обробляю посилання... 📥")
    
    with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            if await download_and_send(url, info.get('title', 'Без опису'), is_manual=True):
                await msg.edit_text("Відео успішно опубліковано! 🚀")
            else:
                await msg.edit_text("Не вдалося завантажити відео. ❌")
        except Exception as e:
            await msg.edit_text(f"Помилка: {e}")

@dp.message(F.text == "Запостити останнє")
async def post_one(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    await message.answer("Перевіряю TikTok... ⏳")
    count = await check_and_post(1)
    await message.answer(f"Готово! Опубліковано {count} відео.")

@dp.message(F.text == "Останні 2")
async def post_two(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    await message.answer("Завантажую останні 2 відео... ⏳")
    count = await check_and_post(2)
    await message.answer(f"Готово! Опубліковано {count} відео.")

@dp.message(F.text == "Останні 3")
async def post_three(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    await message.answer("Завантажую останні 3 відео... ⏳")
    count = await check_and_post(3)
    await message.answer(f"Готово! Опубліковано {count} відео.")

# --- ЦИКЛИ ---

async def auto_check_loop():
    # Перша перевірка при запуску
    await check_and_post(1)
    while True:
        await asyncio.sleep(CHECK_INTERVAL)
        await check_and_post(1)

async def main():
    keep_alive()
    asyncio.create_task(auto_check_loop())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
