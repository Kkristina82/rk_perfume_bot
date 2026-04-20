import asyncio
import os
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
import instaloader
from yt_dlp import YoutubeDL

# --- НАЛАШТУВАННЯ ---
TOKEN = "8700486318:AAHnhE4UNKwQKPGT0ZlW-VPfX906z95heCE"
CHANNEL_ID = "@rkperfume" 
INSTA_USER = "rk.perfume.krop"
TIKTOK_URL = "https://www.tiktok.com/@rk.perfume.krop"

bot = Bot(token=TOKEN)
dp = Dispatcher()
loader = instaloader.Instaloader()

# Сховище останніх постів
last_posts = {"insta": None, "tiktok": None}

# --- ФУНКЦІЇ ПЕРЕВІРКИ (Ті самі, що були раніше) ---
async def get_last_insta_post():
    try:
        profile = instaloader.Profile.from_username(loader.context, INSTA_USER)
        post = next(profile.get_posts())
        return {"id": post.shortcode, "url": f"https://www.instagram.com/p/{post.shortcode}/", "image": post.url, "caption": post.caption[:200] if post.caption else ""}
    except: return None

async def download_tiktok_video():
    ydl_opts = {'outtmpl': 'video.mp4', 'quiet': True, 'format': 'best'}
    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(TIKTOK_URL, download=True)
            video = info['entries'][0]
            return {"id": video['id'], "url": video['webpage_url'], "title": video.get('title', 'Нове відео!')}
    except: return None

# --- ЛОГІКА ПУБЛІКАЦІЇ ---
async def run_sync():
    new_found = False
    # Перевірка інсти
    insta = await get_last_insta_post()
    if insta and insta['id'] != last_posts["insta"]:
        caption = f"📸 <a href='{insta['url']}'>Публікація Instagram</a>\n\n{insta['caption']}"
        await bot.send_photo(CHANNEL_ID, insta['image'], caption=caption, parse_mode=ParseMode.HTML)
        last_posts["insta"] = insta['id']
        new_found = True

    # Перевірка тіктоку
    tiktok = await download_tiktok_video()
    if tiktok and tiktok['id'] != last_posts["tiktok"]:
        caption = f"🎬 <a href='{tiktok['url']}'>Публікація Tik Tok</a>\n\n{tiktok['title']}"
        await bot.send_video(CHANNEL_ID, FSInputFile("video.mp4"), caption=caption, parse_mode=ParseMode.HTML)
        last_posts["tiktok"] = tiktok['id']
        if os.path.exists("video.mp4"): os.remove("video.mp4")
        new_found = True
    
    return new_found

# --- ОБРОБКА КОМАНД ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Перевірити оновлення", callback_data="check_now")]
    ])
    await message.answer("Привіт! Я бот для синхронізації @rkperfume.\nНатисніть кнопку нижче, щоб перевірити нові пости в соцмережах.", reply_markup=kb)

@dp.callback_query(F.data == "check_now")
async def manual_check(callback: types.Callback_query):
    await callback.answer("Перевіряю... Зачекайте кілька секунд.")
    found = await run_sync()
    if found:
        await callback.message.answer("✅ Знайдено нові публікації! Вони вже в каналі.")
    else:
        await callback.message.answer("📪 Нічого нового немає. Всі пости вже опубліковані.")

# --- АВТОМАТИЧНИЙ ЦИКЛ (Фонова робота) ---
async def auto_check():
    while True:
        await run_sync()
        await asyncio.sleep(600) # Кожні 10 хв автоматично

async def main():
    # Запускаємо і бота, і фонову перевірку одночасно
    asyncio.create_task(auto_check())
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
