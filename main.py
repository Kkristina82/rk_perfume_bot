import asyncio
import os
import json
import logging
import instaloader
import requests
import tempfile
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from yt_dlp import YoutubeDL

# ============================================================
# НАЛАШТУВАННЯ — замінити на свої значення
# ============================================================
TOKEN = os.getenv("BOT_TOKEN", "8700486318:AAHnhE4UNKwQKPGT0ZlW-VPfX906z95heCE")
CHANNEL_ID = os.getenv("CHANNEL_ID", "@rkperfume")
ADMIN_ID = int(os.getenv("ADMIN_ID", "7443699603"))  # Ваш Telegram user_id (число)

INSTA_USER = "rk.perfume.krop"
TIKTOK_USER = "rk.perfume.krop"

# Instagram авторизація (обов'язково для отримання постів)
# Задайте через змінні середовища або вставте напряму:
INSTA_SESSION_FILE = os.getenv("INSTA_SESSION_FILE", "")  # шлях до файлу сесії Instaloader
INSTA_LOGIN = os.getenv("INSTA_LOGIN", "rk.perfume.krop")                # логін Instagram (якщо немає session file)
INSTA_PASSWORD = os.getenv("INSTA_PASSWORD", "20072006")          # пароль Instagram (якщо немає session file)

CHECK_INTERVAL = 600  # секунд між автоперевірками (10 хв)
STATE_FILE = "posts_state.json"
MAX_POSTS_HISTORY = 50  # скільки ID постів зберігати

# ============================================================
# ІНІЦІАЛІЗАЦІЯ
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

bot = Bot(token=TOKEN)
dp = Dispatcher()


# ============================================================
# ЗБЕРЕЖЕННЯ СТАНУ (щоб не дублювати після перезапуску)
# ============================================================
def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Помилка завантаження стану: {e}")
    return {
        "published_insta": [],
        "published_tiktok": [],
        "last_check": None,
        "total_published": 0
    }

def save_state(state: dict):
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Помилка збереження стану: {e}")

state = load_state()


# ============================================================
# INSTALOADER — ініціалізація з авторизацією
# ============================================================
def create_instaloader() -> instaloader.Instaloader:
    """Створює та авторизує екземпляр Instaloader."""
    L = instaloader.Instaloader(
        download_pictures=False,
        download_videos=False,
        download_video_thumbnails=False,
        download_geotags=False,
        download_comments=False,
        save_metadata=False,
        quiet=True,
    )
    if INSTA_SESSION_FILE and os.path.exists(INSTA_SESSION_FILE):
        try:
            L.load_session_from_file(INSTA_LOGIN, INSTA_SESSION_FILE)
            logger.info("Instagram: сесія завантажена з файлу")
        except Exception as e:
            logger.warning(f"Не вдалося завантажити сесію: {e}")
    elif INSTA_LOGIN and INSTA_PASSWORD:
        try:
            L.login(INSTA_LOGIN, INSTA_PASSWORD)
            logger.info(f"Instagram: авторизація як {INSTA_LOGIN}")
        except Exception as e:
            logger.error(f"Instagram: помилка авторизації: {e}")
    else:
        logger.warning(
            "Instagram: немає авторизації! "
            "Задайте INSTA_SESSION_FILE або INSTA_LOGIN + INSTA_PASSWORD. "
            "Без авторизації Instagram блокує запити."
        )
    return L


# ============================================================
# ОТРИМАННЯ ПОСТІВ З INSTAGRAM (через Instaloader з авторизацією)
# ============================================================
async def get_new_insta_posts() -> list:
    """Повертає список нових постів (відео або фото) з Instagram."""
    new_posts = []
    try:
        L = await asyncio.to_thread(create_instaloader)
        profile = await asyncio.to_thread(
            instaloader.Profile.from_username, L.context, INSTA_USER
        )
        posts_iter = profile.get_posts()
        count = 0
        for post in posts_iter:
            if count >= 5:
                break
            post_id = post.shortcode
            if post_id and post_id not in state["published_insta"]:
                new_posts.append({
                    "id": post_id,
                    "webpage_url": f"https://www.instagram.com/p/{post_id}/",
                    "title": post.caption[:200] if post.caption else "",
                    "is_video": post.is_video,
                    "media_url": post.video_url if post.is_video else post.url,
                    "caption_raw": post.caption[:300] if post.caption else "",
                    "post_obj": post,
                })
            count += 1
    except instaloader.exceptions.LoginRequiredException:
        logger.error(
            "Instagram вимагає авторизацію! "
            "Задайте INSTA_LOGIN + INSTA_PASSWORD або INSTA_SESSION_FILE."
        )
    except instaloader.exceptions.ProfileNotExistsException:
        logger.error(f"Instagram профіль '{INSTA_USER}' не знайдено.")
    except Exception as e:
        logger.error(f"Instagram get_posts помилка: {e}")
    return new_posts


def _download_media_url(url: str, dest_path: str) -> bool:
    """Завантажує файл за URL у dest_path. Повертає True якщо успішно."""
    try:
        with requests.get(url, stream=True, timeout=60) as r:
            r.raise_for_status()
            with open(dest_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        return True
    except Exception as e:
        logger.warning(f"Помилка завантаження {url}: {e}")
        return False


async def download_insta_post(post: dict) -> dict:
    """Завантажує медіа конкретного Instagram поста."""
    post_obj = post.get("post_obj")
    if post_obj is None:
        return {**post, "filename": None}

    ext = "mp4" if post["is_video"] else "jpg"
    filename = f"insta_{post['id']}.{ext}"
    media_url = post.get("media_url", "")

    if media_url:
        ok = await asyncio.to_thread(_download_media_url, media_url, filename)
        if ok and os.path.exists(filename):
            return {**post, "filename": filename, "ext": ext}

    # Fallback: публікуємо лише посилання
    logger.warning(f"Не вдалося завантажити Instagram пост {post['id']}, публікуємо посилання")
    return {**post, "filename": None}


# ============================================================
# ОТРИМАННЯ ПОСТІВ З TIKTOK
# ============================================================
async def get_new_tiktok_posts() -> list:
    """Повертає список нових відео з TikTok."""
    url = f"https://www.tiktok.com/@{TIKTOK_USER}"
    ydl_opts = {
        "quiet": True,
        "extract_flat": "in_playlist",
        "playlistend": 5,
        "no_warnings": True,
    }
    new_posts = []
    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if not info or "entries" not in info:
                return []
            for entry in info["entries"]:
                post_id = str(entry.get("id", ""))
                if post_id and post_id not in state["published_tiktok"]:
                    new_posts.append({
                        "id": post_id,
                        "url": entry.get("url") or entry.get("webpage_url", ""),
                        "webpage_url": entry.get("webpage_url") or f"https://www.tiktok.com/@{TIKTOK_USER}/video/{post_id}",
                        "title": entry.get("title", "Нове відео"),
                    })
    except Exception as e:
        logger.error(f"TikTok get_posts помилка: {e}")
    return new_posts


async def download_tiktok_video(post: dict) -> dict:
    """Завантажує відео з TikTok."""
    filename = f"tiktok_{post['id']}.mp4"
    ydl_opts = {
        "outtmpl": filename,
        "quiet": True,
        "no_warnings": True,
        "format": "best[filesize<50M]/best",
    }
    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(post["webpage_url"], download=True)
            title = info.get("description", info.get("title", post["title"]))
            return {**post, "filename": filename, "title": title[:300] if title else post["title"]}
    except Exception as e:
        logger.warning(f"Не вдалося завантажити TikTok відео {post['id']}: {e}")
        return {**post, "filename": None}


# ============================================================
# ПУБЛІКАЦІЯ В КАНАЛ
# ============================================================
def make_insta_caption(post: dict) -> str:
    url = post.get("webpage_url", post.get("url", ""))
    text = post.get("caption_raw", "").strip()
    caption = f'📸 <a href="{url}"><b>Instagram • @{INSTA_USER}</b></a>'
    if text:
        caption += f"\n\n{text}"
    return caption


def make_tiktok_caption(post: dict) -> str:
    url = post.get("webpage_url", post.get("url", ""))
    text = post.get("title", "").strip()
    caption = f'🎵 <a href="{url}"><b>TikTok • @{TIKTOK_USER}</b></a>'
    if text:
        caption += f"\n\n{text}"
    return caption


async def publish_insta_post(post_info: dict) -> bool:
    """Публікує Instagram пост у канал. Повертає True якщо успішно."""
    caption = make_insta_caption(post_info)
    filename = post_info.get("filename")
    try:
        if filename and os.path.exists(filename):
            if post_info.get("is_video"):
                await bot.send_video(
                    CHANNEL_ID,
                    FSInputFile(filename),
                    caption=caption,
                    parse_mode=ParseMode.HTML
                )
            else:
                await bot.send_photo(
                    CHANNEL_ID,
                    FSInputFile(filename),
                    caption=caption,
                    parse_mode=ParseMode.HTML
                )
        else:
            # Якщо файл недоступний — публікуємо як текст з посиланням
            await bot.send_message(
                CHANNEL_ID,
                caption,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=False
            )
        return True
    except Exception as e:
        logger.error(f"Помилка публікації Instagram поста {post_info['id']}: {e}")
        return False
    finally:
        if filename and os.path.exists(filename):
            os.remove(filename)


async def publish_tiktok_post(post_info: dict) -> bool:
    """Публікує TikTok відео у канал."""
    caption = make_tiktok_caption(post_info)
    filename = post_info.get("filename")
    try:
        if filename and os.path.exists(filename):
            await bot.send_video(
                CHANNEL_ID,
                FSInputFile(filename),
                caption=caption,
                parse_mode=ParseMode.HTML
            )
        else:
            await bot.send_message(
                CHANNEL_ID,
                caption,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=False
            )
        return True
    except Exception as e:
        logger.error(f"Помилка публікації TikTok відео {post_info['id']}: {e}")
        return False
    finally:
        if filename and os.path.exists(filename):
            os.remove(filename)


# ============================================================
# ОСНОВНА ЛОГІКА СИНХРОНІЗАЦІЇ
# ============================================================
async def run_sync(notify_admin: bool = False) -> tuple[int, int]:
    """Перевіряє та публікує нові пости. Повертає (insta_count, tiktok_count)."""
    global state
    insta_count = 0
    tiktok_count = 0

    logger.info("Починаю перевірку нових постів...")

    # --- Instagram ---
    try:
        new_insta = await get_new_insta_posts()
        for post in reversed(new_insta):  # публікуємо від старіших до новіших
            post_info = await download_insta_post(post)
            if await publish_insta_post(post_info):
                state["published_insta"].append(post["id"])
                state["published_insta"] = state["published_insta"][-MAX_POSTS_HISTORY:]
                state["total_published"] += 1
                insta_count += 1
                save_state(state)
                await asyncio.sleep(3)  # пауза між постами
    except Exception as e:
        logger.error(f"Загальна помилка Instagram: {e}")

    # --- TikTok ---
    try:
        new_tiktok = await get_new_tiktok_posts()
        for post in reversed(new_tiktok):
            post_info = await download_tiktok_video(post)
            if await publish_tiktok_post(post_info):
                state["published_tiktok"].append(post["id"])
                state["published_tiktok"] = state["published_tiktok"][-MAX_POSTS_HISTORY:]
                state["total_published"] += 1
                tiktok_count += 1
                save_state(state)
                await asyncio.sleep(3)
    except Exception as e:
        logger.error(f"Загальна помилка TikTok: {e}")

    state["last_check"] = datetime.now().isoformat()
    save_state(state)

    logger.info(f"Перевірку завершено. Instagram: {insta_count}, TikTok: {tiktok_count}")

    if notify_admin and ADMIN_ID and (insta_count or tiktok_count):
        try:
            await bot.send_message(
                ADMIN_ID,
                f"✅ Авто-публікація:\n📸 Instagram: {insta_count} нових\n🎵 TikTok: {tiktok_count} нових"
            )
        except Exception:
            pass

    return insta_count, tiktok_count


# ============================================================
# КОМАНДИ БОТА
# ============================================================
def main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Перевірити зараз", callback_data="check_now")],
        [InlineKeyboardButton(text="📊 Статус публікацій", callback_data="show_status")],
    ])


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    if ADMIN_ID and message.from_user.id != ADMIN_ID:
        return  # ігноруємо не-адміна
    await message.answer(
        f"👋 <b>Бот синхронізації @{CHANNEL_ID.lstrip('@')}</b>\n\n"
        f"📸 Instagram: <code>{INSTA_USER}</code>\n"
        f"🎵 TikTok: <code>@{TIKTOK_USER}</code>\n\n"
        f"Бот автоматично перевіряє нові пости кожні <b>{CHECK_INTERVAL // 60} хвилин</b> "
        f"та публікує їх у канал.\n\n"
        f"Використовуй кнопки нижче для управління:",
        parse_mode=ParseMode.HTML,
        reply_markup=main_keyboard()
    )


@dp.message(Command("status"))
async def cmd_status(message: types.Message):
    if ADMIN_ID and message.from_user.id != ADMIN_ID:
        return
    await send_status(message.chat.id)


async def send_status(chat_id: int):
    last_check = state.get("last_check")
    if last_check:
        try:
            dt = datetime.fromisoformat(last_check)
            last_check_str = dt.strftime("%d.%m.%Y о %H:%M")
        except Exception:
            last_check_str = last_check
    else:
        last_check_str = "Ще не перевірялось"

    insta_count = len(state.get("published_insta", []))
    tiktok_count = len(state.get("published_tiktok", []))
    total = state.get("total_published", 0)

    text = (
        f"<b>📊 Статус бота</b>\n\n"
        f"🕐 Остання перевірка: <code>{last_check_str}</code>\n"
        f"📦 Всього опубліковано: <b>{total}</b>\n\n"
        f"📸 Instagram постів у базі: <b>{insta_count}</b>\n"
        f"🎵 TikTok відео у базі: <b>{tiktok_count}</b>\n\n"
        f"⏱ Авто-перевірка: кожні <b>{CHECK_INTERVAL // 60} хв</b>"
    )
    await bot.send_message(chat_id, text, parse_mode=ParseMode.HTML, reply_markup=main_keyboard())


@dp.callback_query(F.data == "check_now")
async def cb_check_now(callback: types.CallbackQuery):
    if ADMIN_ID and callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Немає доступу", show_alert=True)
        return

    await callback.answer("⏳ Перевіряю... Це може зайняти хвилину.")
    await callback.message.answer("🔍 Починаю перевірку нових постів у соцмережах...")

    insta_count, tiktok_count = await run_sync()

    if insta_count or tiktok_count:
        result = (
            f"✅ <b>Знайдено нові публікації!</b>\n\n"
            f"📸 Instagram: +{insta_count}\n"
            f"🎵 TikTok: +{tiktok_count}\n\n"
            f"Вони вже опубліковані в каналі {CHANNEL_ID} 🚀"
        )
    else:
        result = "📪 <b>Нічого нового.</b>\nВсі актуальні пости вже опубліковані в каналі."

    await callback.message.answer(result, parse_mode=ParseMode.HTML, reply_markup=main_keyboard())


@dp.callback_query(F.data == "show_status")
async def cb_show_status(callback: types.CallbackQuery):
    if ADMIN_ID and callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Немає доступу", show_alert=True)
        return
    await callback.answer()
    await send_status(callback.message.chat.id)


# ============================================================
# ФОНОВИЙ ЦИКЛ АВТО-ПЕРЕВІРКИ
# ============================================================
async def auto_check_loop():
    await asyncio.sleep(30)  # затримка на старті щоб бот встиг запуститись
    while True:
        try:
            await run_sync(notify_admin=True)
        except Exception as e:
            logger.error(f"Помилка у фоновому циклі: {e}")
        await asyncio.sleep(CHECK_INTERVAL)


# ============================================================
# СТАРТ
# ============================================================
async def main():
    logger.info("Запуск бота...")
    asyncio.create_task(auto_check_loop())
    await dp.start_polling(bot, skip_updates=True)


if __name__ == "__main__":
    asyncio.run(main())
