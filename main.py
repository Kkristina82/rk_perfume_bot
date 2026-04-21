from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

API_TOKEN = '8700486318:AAHnhE4UNKwQKPGT0ZlW-VPfX906z95heCE'
CHANNEL_ID = '@rkperfume'
TIKTOK_PROFILE_URL = 'https://www.tiktok.com/@rk.perfume.krop'

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# Створюємо головну кнопку внизу екрана (Reply Keyboard)
main_menu = ReplyKeyboardMarkup(resize_keyboard=True)
main_menu.add(KeyboardButton("🔄 Перевірити нові відео"))

@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    await message.answer(
        "Вітаю! Я бот RK Perfume. Натисніть кнопку нижче, щоб перевірити оновлення в TikTok.",
        reply_markup=main_menu
    )

@dp.message_handler(lambda message: message.text == "🔄 Перевірити нові відео")
async def manual_check(message: types.Message):
    await message.answer("🔎 Перевіряю ваш TikTok на наявність нових відео...")
    
    # Тут викликається ваша функція пошуку відео
    # Для прикладу візьмемо умовне відео:
    video_url = "URL_ВІДЕО" 
    video_id = "ID_ВІДЕО"
    is_new = True # Тут має бути логіка перевірки, чи воно вже було опубліковане
    
    if is_new:
        await send_pretty_post(video_url, video_id)
        await message.answer("✅ Нове відео знайдено та опубліковано в канал!")
    else:
        await message.answer("🤷 Нових відео поки немає. Спробуйте пізніше!")

async def send_pretty_post(video_url, video_id):
    # Кнопки під самим постом у каналі
    inline_kb = InlineKeyboardMarkup(row_width=1)
    inline_kb.add(
        InlineKeyboardButton(text="🎬 Дивитись у TikTok", url=f"{TIKTOK_PROFILE_URL}/video/{video_id}"),
        InlineKeyboardButton(text="✨ Наш профіль TikTok", url=TIKTOK_PROFILE_URL)
    )

    caption = (
        "<b>✨ Нове відео від RK Perfume!</b>\n\n"
        "Переходьте за посиланням нижче, щоб дізнатися більше про цей аромат. 👇"
    )

    await bot.send_video(
        chat_id=CHANNEL_ID,
        video=video_url,
        caption=caption,
        parse_mode="HTML",
        reply_markup=inline_kb
    )

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
