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

# --- ВШИТИЙ КЛЮЧ FIREBASE ---
# Дані отримані безпосередньо з вашого файлу serviceAccountKey.json [cite: 1]
firebase_config = {
    "type": "service_account",
    "project_id": "rkbot-db5d6",
    "private_key_id": "0ba1393a3076be02af5baf8cc53757a62faffa72",
    "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQCy7Lknm7fa2mlH\nCHFIvznvWxfj9VBWP0vOg6WQpKRSnhMXS2XL2P7cOdNXH2laWK0dnvdEOLo9k8HA\niLApvA5jQ3/cSx5upoU9c3Ohta+hpRJt1We28WT7tNP/RhKHEXBWq9lV1KGii1rv\nwPq93T0ZKRSFg6Yim4vpU3wvbisBWfcbQd+DIVd06YvmSMCojbCy/vkoQXfCVQpD\nNtbmpDBMIrAenAiWvNjGp9cCDMgKo0p6XXoF1kabhiYjYlooW2GOVzU3I7m5COq4\n3Q/vCj66Q5Lhu9XHXP2PVhEBaTisrKweJZE5MtqFP8Gdd7vL8+G4Q5nmtU2zZW6j\nIxuYvk3dAgMBAAECggEACO/KOxhfDIssE6kjVvj9vz7ukjGsKrUJIVGE4rtY3ZG5\njhUmpB6cjJCsn2I5T4YOPLFDFB3jbkfTxAnS7X0c2KgXRtnCqJytGxnJ3/0UfpXU\nqVzUGN71BmrS/uHq8xYAi8R6e7vxCDUYXIRbRPUiRAz/xYzPu4etq1o14bzJlAAR\neukz9UcxMfeuN/w5UHNSmk+ZgR8uQVTdfpnQ+SfQUUWOVvAXC1XsFQqy0jubSzZ0\nHzfff/qBO2W4f857kYYQnOurMSReW4NNefWvrhlIG8pqikRQ6+oe9hwa3mlLOow+\nnpRXT4R7Ip4jEUrkppq1271Tmg47AM33+Ngh/Ew7yQKBgQDiP47Rq8onHJJPe3M8\nQSzaXcXreyRZ2ct8enN+WWKn3gl+E9UKHUqjBVw1Q0s76zKYk82JdDJe+D1842Gy\n20jg2prDMW9VOEesRaateqFc5H+klOBEnvbmjoV7hekonZ5pL+odHbj3+Bi2y0Vy\nTy1oquZImJSZ6BwqpaQbM10OuQKBgQDKdA91XZ9gVhUc3wP679bhFXLQ8FCHOa4E\nF1ROJANtOw74D0Wc9aZbdC07SoOo6NAF5sQYQ06ydehgXdAMs0Zh870P8A1YfOL/\nwxGnwmOqSFhRrfufB4ZhMDIHLNGaPHcI0xbtdgN0k4lRmq8cQ6LZMkeRndGJSCB6\nduuiFFkGRQKBgH8AFndz60IRM8ASGBmWrErXoKYStdEKBMOXKQWfv1VjughfsZK/\n5omkFKKBZ9X2rKwhK5sg8rWEu19DdDAmD77Id19ifJBlyzXU0z9GOxYd3djRCSL7\n6LR7BErWXI9ECwwYrV4ytQXc6mKRsCX+dArxA9t0atYKCOWXnYr3RiFhAoGBALfx\ndW4kjz7/V5Vwx3QC4BCH5VcTUYdbj9ElxTJuJDLlmvclIRG4W9ryFnqtfCxGw2Lp\nRbfpx6H74RNViUdQx50N0PSfHfENH05UVUFALD+2FZC47EqUkrLREFNWlGZ3k4uQ\nB1/ffso3lmdvjLS4e0iuFzql0pDR2LiMPhF4PV6lAoGBAJsE++YNPG7giy/9vT0N\nhAUUTDLkW2lY6QJg87VURfutUdKI12c79wiCgk47N4hww/cUIXAZdatyIxGpTr4r\nXOZRrlodMSbEMN1Cw/g2wjzzadbfueb4r7OZAxIKsbpOZlyYR35D2ZtYgPJF5kT4\nFG3lgADe4zvWC5fVww1o6EFw\n-----END PRIVATE KEY-----\n".replace('\\n', '\n'),
    "client_email": "firebase-adminsdk-fbsvc@rkbot-db5d6.iam.gserviceaccount.com",
    "client_id": "115494647334000187888",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk-fbsvc%40rkbot-db5d6.iam.gserviceaccount.com",
    "universe_domain": "googleapis.com"
}

if not firebase_admin._apps:
    cred = credentials.Certificate(firebase_config)
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
    file_path = "temp_video.mp4"
    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'outtmpl': file_path,
        'quiet': True
    }
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
        await bot.send_video(
            chat_id=CHANNEL_ID,
            video=BufferedInputFile(video_data, filename="video.mp4"),
            caption=caption,
            parse_mode=ParseMode.HTML
        )
        await bot.send_message(ADMIN_ID, f"✅ Опубліковано: {video_url}")
    except Exception as e:
        print(f"Error posting: {e}")

# --- ОБРОБНИКИ ---
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🔍 Перевірити TikTok")]],
        resize_keyboard=True
    )
    await message.answer(f"Бот запущений. Звіти приходять на ID: {ADMIN_ID}", reply_markup=kb)

@dp.message(F.text == "🔍 Перевірити TikTok")
async def manual_check(message: types.Message):
    msg = await message.answer("Перевіряю TikTok... ⏳")
    latest = get_tiktok_data()
    if latest and latest['id'] != db_last_video.get():
        await post_and_notify(latest['url'], latest['id'], latest.get('title', 'Без опису'))
        db_last_video.set(latest['id'])
        await msg.edit_text("Знайдено нове відео! Опубліковано. 🚀")
    else:
        await msg.edit_text("Нових відео поки немає. ✅")

async def auto_check_loop():
    while True:
        try:
            latest = get_tiktok_data()
            if latest and latest['id'] != db_last_video.get():
                await post_and_notify(latest['url'], latest['id'], latest.get('title', 'Без опису'))
                db_last_video.set(latest['id'])
        except Exception as e:
            print(f"Loop error: {e}")
        await asyncio.sleep(600) # Перевірка кожні 10 хв

# --- СЕРВЕР ДЛЯ RENDER ---
async def handle(request):
    return web.Response(text="Bot is running!")

async def main():
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
