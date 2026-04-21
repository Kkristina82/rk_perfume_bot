from aiogram import Bot, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import asyncio

# Дані вашого бота та каналу
API_TOKEN = '8700486318:AAHnhE4UNKwQKPGT0ZlW-VPfX906z95heCE'
CHANNEL_ID = '@rkperfume'
TIKTOK_PROFILE_URL = 'https://www.tiktok.com/@rk.perfume.krop'

bot = Bot(token=API_TOKEN)

async def send_pretty_post(video_url, video_id):
    # Створюємо кнопки
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎬 Дивитись у TikTok", url=f"{TIKTOK_PROFILE_URL}/video/{video_id}")
        ],
        [
            InlineKeyboardButton(text="✨ Наш профіль TikTok", url=TIKTOK_PROFILE_URL)
        ]
    ])

    # Текст поста з використанням HTML-розмітки
    caption = (
        "<b>✨ Нове надходження в RK Perfume!</b>\n\n"
        "Ми опублікували свіже відео з нашими ароматами. "
        "Переходьте, ставте вподобайки та підписуйтесь! ❤️\n\n"
        "📍 <i>Кропивницький | Доставка по Україні</i>"
    )

    try:
        # Відправка відео з описом та кнопками
        await bot.send_video(
            chat_id=CHANNEL_ID,
            video=video_url,
            caption=caption,
            parse_mode="HTML",
            reply_markup=keyboard
        )
    except Exception as e:
        print(f"Помилка при відправці: {e}")

# Приклад виклику функції
# asyncio.run(send_pretty_post("URL_ВІДЕО", "ID_ВІДЕО"))
