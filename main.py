import asyncio
import logging
from aiogram import Bot
from aiogram.enums import ParseMode
import instaloader
from yt_dlp import YoutubeDL

# --- НАЛАШТУВАННЯ ---
TOKEN = "8700486318:AAHnhE4UNKwQKPGT0ZlW-VPfX906z95heCE"
CHANNEL_ID = "@rkperfume" 
INSTA_USER = "rk.perfume.krop"
TIKTOK_URL = "https://www.tiktok.com/@rk.perfume.krop"

# Якщо Instagram видаватиме помилку, впишіть сюди дані свого (або фейкового) акаунта:
INSTA_LOGIN = "rk.perfume.krop"
INSTA_PASSWORD = "20062007"

bot = Bot(token=TOKEN)
loader = instaloader.Instaloader()

# Авторизація (виконається, якщо вказані дані)
if INSTA_LOGIN:
    try:
        loader.login(INSTA_LOGIN, INSTA_PASSWORD)
        print("Авторизація в Instagram успішна!")
    except Exception as e:
        print(f"Помилка входу в Instagram: {e}")

last_posts = {"insta": None, "tiktok": None}

async def get_last_insta_post():
    try:
        profile = instaloader.Profile.from_username(loader.context, INSTA_USER)
        post = next(profile.get_posts())
        return {
            "id": post.shortcode,
            "url": f"https://www.instagram.com/p/{post.shortcode}/",
            "image": post.url,
            "caption": post.caption[:200] if post.caption else ""
        }
    except Exception as e:
        logging.error(f"Insta error: {e}")
        return None

async def get_last_tiktok_video():
    ydl_opts = {'quiet': True, 'noplaylist': True, 'extract_flat': True}
    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(TIKTOK_URL, download=False)
            video = info['entries'][0]
            return {
                "id": video['id'],
                "url": video['url'],
                "title": video.get('title', '')
            }
    except Exception as e:
        logging.error(f"TikTok error: {e}")
        return None

async def check_updates():
    print(f"Бот запущений! Моніторимо канал {CHANNEL_ID}")
    while True:
        # ПЕРЕВІРКА INSTAGRAM
        insta_post = await get_last_insta_post()
        if insta_post and insta_post['id'] != last_posts["insta"]:
            # Створюємо підпис із клікабельним посиланням через HTML
            caption = (f"📸 <a href='{insta_post['url']}'>Публікація Instagram</a>\n\n"
                       f"{insta_post['caption']}...")
            try:
                await bot.send_photo(CHANNEL_ID, insta_post['image'], caption=caption, parse_mode=ParseMode.HTML)
                last_posts["insta"] = insta_post['id']
                print("Новий пост з Instagram опубліковано!")
            except Exception as e:
                print(f"Помилка надсилання в ТГ: {e}")

        # ПЕРЕВІРКА TIKTOK
        tiktok_video = await get_last_tiktok_video()
        if tiktok_video and tiktok_video['id'] != last_posts["tiktok"]:
            text = (f"🎬 <a href='{tiktok_video['url']}'>Публікація Tik Tok</a>\n\n"
                    f"{tiktok_video['title']}")
            try:
                await bot.send_message(CHANNEL_ID, text, parse_mode=ParseMode.HTML)
                last_posts["tiktok"] = tiktok_video['id']
                print("Нове відео з TikTok опубліковано!")
            except Exception as e:
                print(f"Помилка надсилання в ТГ: {e}")

        await asyncio.sleep(600) # Перевірка кожні 10 хвилин

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(check_updates())
