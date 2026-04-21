import os
import asyncio
import yt_dlp
import firebase_admin
from firebase_admin import credentials, db
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, BufferedInputFile
from aiohttp import web

# --- КОНФІГУРАЦІЯ ---
TOKEN = "8700486318:AAHnhE4UNKwQKPGT0ZlW-VPfX906z95heCE"
CHANNEL_ID = "@rkperfume"
TIKTOK_PROFILE = "https://www.tiktok.com/@rk.perfume.krop"
ADMIN_ID = 7443699603
FIREBASE_URL = "https://rkbot-db5d6-default-rtdb.firebaseio.com/"

# Ініціалізація Firebase
if not firebase_admin._apps:
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred, {'databaseURL': FIREBASE_URL})

db_last_video = db.reference('last_video_id')

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- ЛОГІКА ТІКТОК ---
def get_tiktok_data():
    ydl_opts = {
        'extract_flat': True, 
        'quiet': True, 
        'no_warnings': True,
        'playlist_items': '1'
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        result = ydl.extract_info(TIKTOK_PROFILE, download=False)
        if 'entries' in result and len(result['entries']) > 0:
            return result['entries'][0]
    return None

async def download_video(url):
    """Завантажує відео в пам'ять (без створення файлу на диску)"""
    file_path = "temp_video.mp4"
    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'outtmpl': file_path,
        'quiet': True
    }
    # Використовуємо run_in_executor для блокуючої операції yt_dlp
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, lambda: yt_dlp.YoutubeDL(ydl_opts).download([url]))
    
    if os.path.exists(file_path):
        with open(file_path, 'rb') as f:
            data = f.read()
        os.remove(file_path)
        return data
    return None

async def post_and_notify(video_url, v_id, desc):
    video_data = await download_video(video_url)
    if not video_data:
        return

    caption = (
        f"🌟 <b>Нова публікація в TikTok</b>\n\n"
        f"📝 {desc}\n\n"
        f"👤 <a href='{TIKTOK_PROFILE}'><b>Наш профіль</b></a>"
    )

    try:
        # Публікація в канал
        await bot.send_video(
            chat_id=CHANNEL_ID,
            video=BufferedInputFile(video_data, filename="video.mp4"),
            caption=caption,
            parse_mode=ParseMode.HTML
        )
        # Звіт адміну
        await bot.send_message(ADMIN_ID, f"✅ Опубліковано: {video_url}")
    except Exception as e:
        print(f"Error posting: {e}")

# --- ОБРОБНИКИ КОМАНД ---
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🔍 Перевірити TikTok")]],
        resize_keyboard=True
    )
    await message.answer(f"Бот працює. Звіти для: {ADMIN_ID}", reply_markup=kb)

@dp.message(F.text == "🔍 Перевірити TikTok")
async def manual_check(message: types.Message):
    msg = await message.answer("Перевіряю... ⏳")
    latest = get_tiktok_data()
    if latest and latest['id'] != db_last_video.get():
        await post_and_notify(latest['url'], latest['id'], latest.get('title', 'Без опису'))
        db_last_video.set(latest['id'])
        await msg.edit_text("Знайдено та опубліковано! 🚀")
    else:
        await msg.edit_text("Нових відео немає. ✅")

# --- ФОНОВА ПЕРЕВІРКА ---
async def auto_check_loop():
    while True:
        try:
            latest = get_tiktok_data()
            if latest and latest['id'] != db_last_video.get():
                await post_and_notify(latest['url'], latest['id'], latest.get('title', 'Без опису'))
                db_last_video.set(latest['id'])
        except Exception as e:
            print(f"Loop error: {e}")
        await asyncio.sleep(600) # Перевірка кожні 10 хвилин

# --- ВЕБ-СЕРВЕР ДЛЯ RENDER ---
async def handle(request):
    return web.Response(text="Bot is alive!")

async def main():
    # Налаштування веб-сервера aiohttp (замість Flask для кращої сумісності)
    server = web.Application()
    server.router.add_get('/', handle)
    runner = web.AppRunner(server)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', int(os.environ.get("PORT", 8080)))
    
    asyncio.create_task(site.start())
    asyncio.create_task(auto_check_loop())
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
