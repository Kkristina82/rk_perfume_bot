import asyncio
import os
import logging
from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.types import FSInputFile
import instaloader
from yt_dlp import YoutubeDL

# --- НАЛАШТУВАННЯ ---
TOKEN = "8700486318:AAHnhE4UNKwQKPGT0ZlW-VPfX906z95heCE"
CHANNEL_ID = "@rkperfume" 
INSTA_USER = "rk.perfume.krop"
TIKTOK_URL = "https://www.tiktok.com/@rk.perfume.krop"

bot = Bot(token=TOKEN)
loader = instaloader.Instaloader()

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

async def download_tiktok_video():
    # Налаштування для завантаження відео
    ydl_opts = {
        'outtmpl': 'video.mp4',
        'quiet': True,
        'format': 'bestvideo+bestaudio/best',
    }
    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(TIKTOK_URL, download=True)
            video_data = info['entries'][0]
            return {
                "id": video_data['id'],
                "url": video_data['webpage_url'],
                "title": video_data.get('title', 'Нове відео!')
            }
    except Exception as e:
        logging.error(f"TikTok download error: {e}")
        return None

async def check_updates():
    print("Бот працює...")
    while True:
        # ПЕРЕВІРКА INSTAGRAM (ФОТО)
        insta_post = await get_last_insta_post()
        if insta_post and insta_post['id'] != last_posts["insta"]:
            caption = f"📸 <a href='{insta_post['url']}'>Публікація Instagram</a>\n\n{insta_post['caption']}"
            await bot.send_photo(CHANNEL_ID, insta_post['image'], caption=caption, parse_mode=ParseMode.HTML)
            last_posts["insta"] = insta_post['id']

        # ПЕРЕВІРКА TIKTOK (ВІДЕО)
        tiktok_data = await download_tiktok_video()
        if tiktok_data and tiktok_data['id'] != last_posts["tiktok"]:
            caption = f"🎬 <a href='{tiktok_data['url']}'>Публікація Tik Tok</a>\n\n{tiktok_data['title']}"
            video_file = FSInputFile("video.mp4")
            await bot.send_video(CHANNEL_ID, video_file, caption=caption, parse_mode=ParseMode.HTML)
            last_posts["tiktok"] = tiktok_data['id']
            if os.path.exists("video.mp4"):
                os.remove("video.mp4") # Видаляємо файл після відправки

        await asyncio.sleep(600) # Перевірка кожні 10 хв

if __name__ == "__main__":
    asyncio.run(check_updates())
