import asyncio
import os
import json
import logging
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove, FSInputFile
from yt_dlp import YoutubeDL

# ============================================================

# НАЛАШТУВАННЯ

# ============================================================

TOKEN = os.getenv(“BOT_TOKEN”, “8700486318:AAHnhE4UNKwQKPGT0ZlW-VPfX906z95heCE”)
ADMIN_ID = int(os.getenv(“ADMIN_ID”, “7443699603”))
CHANNEL_ID = os.getenv(“CHANNEL_ID”, “@rkperfume”)
TIKTOK_USER = “rk.perfume.krop”

CONFIG_FILE = “perfume_config.json”
ORDERS_FILE = “orders.json”
STATE_FILE = “tiktok_state.json”

CHECK_INTERVAL = 600  # 10 хвилин
MAX_POSTS_HISTORY = 50

# ============================================================

# ІНІЦІАЛІЗАЦІЯ

# ============================================================

logging.basicConfig(
level=logging.INFO,
format=”%(asctime)s [%(levelname)s] %(message)s”
)
logger = logging.getLogger(**name**)

bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# ============================================================

# СТАНИ

# ============================================================

class OrderStates(StatesGroup):
waiting_for_custom_order = State()
waiting_for_order_notes = State()
admin_waiting_for_password = State()
admin_panel = State()
admin_waiting_for_perfume_name = State()
admin_waiting_for_perfume_price = State()
admin_waiting_for_perfume_description = State()
admin_waiting_for_delete_id = State()
admin_waiting_for_card = State()
admin_waiting_for_card_holder = State()
admin_order_confirmation = State()

# ============================================================

# КОНФІГУРАЦІЯ

# ============================================================

def load_config() -> dict:
“”“Завантажує конфігурацію”””
if os.path.exists(CONFIG_FILE):
try:
with open(CONFIG_FILE, “r”, encoding=“utf-8”) as f:
return json.load(f)
except Exception as e:
logger.error(f”Помилка завантаження конфігу: {e}”)

```
default_config = {
    "perfumes": [
        {"id": 1, "name": "Rose Elegance", "price": 350, "description": "Класичний аромат троянди 🌹"},
        {"id": 2, "name": "Vanilla Dream", "price": 320, "description": "Теплий ванільний запах 🍦"},
        {"id": 3, "name": "Ocean Breeze", "price": 380, "description": "Морська свіжість 🌊"},
    ],
    "card": "4441 1111 1111 1111",
    "card_holder": "ROMAN KROP",
    "admin_password": "admin123",
    "next_id": 4
}
save_config(default_config)
return default_config
```

def save_config(config: dict):
“”“Зберігає конфігурацію”””
try:
with open(CONFIG_FILE, “w”, encoding=“utf-8”) as f:
json.dump(config, f, ensure_ascii=False, indent=2)
except Exception as e:
logger.error(f”Помилка збереження конфігу: {e}”)

# ============================================================

# ЗАМОВЛЕННЯ

# ============================================================

def load_orders() -> list:
“”“Завантажує замовлення”””
if os.path.exists(ORDERS_FILE):
try:
with open(ORDERS_FILE, “r”, encoding=“utf-8”) as f:
return json.load(f)
except Exception as e:
logger.error(f”Помилка завантаження замовлень: {e}”)
return []

def save_orders(orders: list):
“”“Зберігає замовлення”””
try:
with open(ORDERS_FILE, “w”, encoding=“utf-8”) as f:
json.dump(orders, f, ensure_ascii=False, indent=2)
except Exception as e:
logger.error(f”Помилка збереження замовлень: {e}”)

def add_order(user_id: int, username: str, order_type: str, items: list, notes: str = “”) -> dict:
“”“Додає нове замовлення”””
orders = load_orders()
order_id = len(orders) + 1

```
order = {
    "id": order_id,
    "user_id": user_id,
    "username": username,
    "type": order_type,
    "items": items,
    "notes": notes,
    "status": "pending",
    "created_at": datetime.now().isoformat(),
    "confirmed_at": None
}

orders.append(order)
save_orders(orders)
return order
```

# ============================================================

# TIKTOK ФУНКЦІОНАЛ

# ============================================================

def load_tiktok_state() -> dict:
“”“Завантажує стан TikTok постів”””
if os.path.exists(STATE_FILE):
try:
with open(STATE_FILE, “r”, encoding=“utf-8”) as f:
return json.load(f)
except Exception as e:
logger.error(f”Помилка завантаження TikTok стану: {e}”)

```
return {
    "published_tiktok": [],
    "last_check": None,
    "total_published": 0
}
```

def save_tiktok_state(state: dict):
“”“Зберігає стан TikTok постів”””
try:
with open(STATE_FILE, “w”, encoding=“utf-8”) as f:
json.dump(state, f, ensure_ascii=False, indent=2)
except Exception as e:
logger.error(f”Помилка збереження TikTok стану: {e}”)

tiktok_state = load_tiktok_state()

async def get_new_tiktok_posts() -> list:
“”“Отримує нові TikTok видео”””
url = f”https://www.tiktok.com/@{TIKTOK_USER}”
ydl_opts = {
“quiet”: True,
“extract_flat”: “in_playlist”,
“playlistend”: 5,
“no_warnings”: True,
}
new_posts = []
try:
with YoutubeDL(ydl_opts) as ydl:
info = ydl.extract_info(url, download=False)
if not info or “entries” not in info:
return []
for entry in info[“entries”]:
post_id = str(entry.get(“id”, “”))
if post_id and post_id not in tiktok_state[“published_tiktok”]:
new_posts.append({
“id”: post_id,
“url”: entry.get(“url”) or entry.get(“webpage_url”, “”),
“webpage_url”: entry.get(“webpage_url”) or f”https://www.tiktok.com/@{TIKTOK_USER}/video/{post_id}”,
“title”: entry.get(“title”, “Нове відео”),
})
except Exception as e:
logger.error(f”TikTok get_posts помилка: {e}”)
return new_posts

async def download_tiktok_video(post: dict) -> dict:
“”“Завантажує TikTok відео”””
filename = f”tiktok_{post[‘id’]}.mp4”
ydl_opts = {
“outtmpl”: filename,
“quiet”: True,
“no_warnings”: True,
“format”: “best[filesize<50M]/best”,
}
try:
with YoutubeDL(ydl_opts) as ydl:
info = ydl.extract_info(post[“webpage_url”], download=True)
title = info.get(“description”, info.get(“title”, post[“title”]))
return {**post, “filename”: filename, “title”: title[:300] if title else post[“title”]}
except Exception as e:
logger.warning(f”Не вдалося завантажити TikTok видео {post[‘id’]}: {e}”)
return {**post, “filename”: None}

def make_tiktok_caption(post: dict) -> str:
“”“Форматує TikTok пост”””
url = post.get(“webpage_url”, post.get(“url”, “”))
text = post.get(“title”, “”).strip()
caption = f’🎵 <a href="{url}"><b>TikTok • @{TIKTOK_USER}</b></a>’
if text:
caption += f”\n\n{text}”
return caption

async def publish_tiktok_post(post_info: dict) -> bool:
“”“Публікує TikTok видео у канал”””
caption = make_tiktok_caption(post_info)
filename = post_info.get(“filename”)
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
logger.error(f”Помилка публікації TikTok видео {post_info[‘id’]}: {e}”)
return False
finally:
if filename and os.path.exists(filename):
os.remove(filename)

async def run_tiktok_sync(notify_admin: bool = False) -> int:
“”“Перевіряє та публікує нові TikTok видео”””
global tiktok_state
tiktok_count = 0

```
logger.info("Починаю перевірку нових TikTok видео...")

try:
    new_tiktok = await get_new_tiktok_posts()
    for post in reversed(new_tiktok):
        post_info = await download_tiktok_video(post)
        if await publish_tiktok_post(post_info):
            tiktok_state["published_tiktok"].append(post["id"])
            tiktok_state["published_tiktok"] = tiktok_state["published_tiktok"][-MAX_POSTS_HISTORY:]
            tiktok_state["total_published"] += 1
            tiktok_count += 1
            save_tiktok_state(tiktok_state)
            await asyncio.sleep(3)
except Exception as e:
    logger.error(f"Загальна помилка TikTok: {e}")

tiktok_state["last_check"] = datetime.now().isoformat()
save_tiktok_state(tiktok_state)

logger.info(f"Перевірку завершено. TikTok: {tiktok_count}")

if notify_admin and ADMIN_ID and tiktok_count:
    try:
        await bot.send_message(
            ADMIN_ID,
            f"✅ Авто-публікація TikTok:\n🎵 TikTok: {tiktok_count} нових"
        )
    except Exception:
        pass

return tiktok_count
```

# ============================================================

# КЛАВІАТУРИ

# ============================================================

def main_keyboard() -> ReplyKeyboardMarkup:
“”“Основна клавіатура для користувачів”””
return ReplyKeyboardMarkup(
keyboard=[
[KeyboardButton(text=“🌸 Прайс парфумів”)],
[KeyboardButton(text=“📝 Індивідуальне замовлення”)],
],
resize_keyboard=True,
one_time_keyboard=False
)

def admin_keyboard() -> ReplyKeyboardMarkup:
“”“Клавіатура для адміна”””
return ReplyKeyboardMarkup(
keyboard=[
[KeyboardButton(text=“📊 Замовлення”)],
[KeyboardButton(text=“💰 Управління прайсом”)],
[KeyboardButton(text=“💳 Налаштування карти”)],
[KeyboardButton(text=“🎵 TikTok синхронізація”)],
[KeyboardButton(text=“🔐 Вихід”)],
],
resize_keyboard=True,
one_time_keyboard=False
)

def price_action_keyboard() -> InlineKeyboardMarkup:
“”“Клавіатура управління прайсом”””
return InlineKeyboardMarkup(inline_keyboard=[
[InlineKeyboardButton(text=“➕ Додати парфум”, callback_data=“add_perfume”)],
[InlineKeyboardButton(text=“✏️ Редагувати”, callback_data=“edit_perfume”)],
[InlineKeyboardButton(text=“❌ Видалити”, callback_data=“delete_perfume”)],
[InlineKeyboardButton(text=“⬅️ Назад”, callback_data=“back_to_admin”)],
])

def order_action_keyboard(order_id: int) -> InlineKeyboardMarkup:
“”“Клавіатура для дій з замовленнями”””
return InlineKeyboardMarkup(inline_keyboard=[
[InlineKeyboardButton(text=“✅ Підтвердити”, callback_data=f”confirm_order_{order_id}”)],
[InlineKeyboardButton(text=“❌ Відхилити”, callback_data=f”reject_order_{order_id}”)],
])

# ============================================================

# ФОРМАТУВАННЯ ПОВІДОМЛЕНЬ

# ============================================================

def format_price_list(config: dict) -> str:
“”“Форматує прайс як красиву таблицю”””
perfumes = config[“perfumes”]

```
if not perfumes:
    return "📪 На жаль, прайс парфумів порожній"

text = "✨ <b>🌸 ПРАЙС ПАРФУМІВ 🌸</b> ✨\n\n"

for idx, perfume in enumerate(perfumes, 1):
    text += f"<b>🔹 {perfume['name']}</b>\n"
    text += f"   <i>{perfume.get('description', '')}</i>\n"
    text += f"   💵 <code>{perfume['price']} грн</code>\n\n"

text += "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
text += "📦 Для замовлення натисніть кнопку внизу!"

return text
```

def format_order_details(order: dict) -> str:
“”“Форматує деталі замовлення”””
status_emoji = {“pending”: “⏳”, “confirmed”: “✅”, “completed”: “🎁”}

```
text = f"<b>📦 Замовлення #{order['id']}</b>\n\n"
text += f"👤 <b>Користувач:</b> @{order['username']}\n"
text += f"🆔 <b>User ID:</b> <code>{order['user_id']}</code>\n"
text += f"📅 <b>Дата:</b> {order['created_at'][:10]}\n"
text += f"📋 <b>Тип:</b> {'Індивідуальне' if order['type'] == 'custom' else 'З прайсу'}\n"
text += f"🔹 <b>Статус:</b> {status_emoji.get(order['status'], '❓')} {order['status']}\n\n"

if order['type'] == 'custom':
    text += f"<b>✍️ Запит:</b>\n<code>{order['items'][0]}</code>\n"
    if order['notes']:
        text += f"\n<b>📝 Додатково:</b>\n<code>{order['notes']}</code>\n"
else:
    text += "<b>🌸 Парфуми:</b>\n"
    for item in order['items']:
        text += f"  🔹 {item}\n"

return text
```

# ============================================================

# КОМАНДИ КОРИСТУВАЧІВ

# ============================================================

@dp.message(Command(“start”))
async def cmd_start(message: types.Message, state: FSMContext):
“”“Стартова команда”””
config = load_config()

```
welcome_text = (
    "👋 <b>Добро пожалувати в наш магазин парфумів!</b> 🌸\n\n"
    "✨ <i>RK Perfume</i> — це якісні та приємні запахи для вас!\n\n"
    "Виберіть що вас цікавить:"
)

await message.answer(welcome_text, reply_markup=main_keyboard(), parse_mode=ParseMode.HTML)
await state.clear()
```

@dp.message(F.text == “🌸 Прайс парфумів”)
async def show_price_list(message: types.Message):
“”“Показує прайс парфумів”””
config = load_config()
text = format_price_list(config)
await message.answer(text, parse_mode=ParseMode.HTML, reply_markup=main_keyboard())

@dp.message(F.text == “📝 Індивідуальне замовлення”)
async def start_custom_order(message: types.Message, state: FSMContext):
“”“Розпочинає індивідуальне замовлення”””
await state.set_state(OrderStates.waiting_for_custom_order)
await message.answer(
“✍️ <b>Індивідуальне замовлення</b>\n\n”
“📝 Опишіть який парфум ви хочете:\n”
“• Назву або тип запаху\n”
“• Опис ваших переваг\n”
“• Будь-які спеціальні побажання\n\n”
“<i>Напишіть усі деталі в одному повідомленні</i>”,
parse_mode=ParseMode.HTML,
reply_markup=ReplyKeyboardRemove()
)

@dp.message(OrderStates.waiting_for_custom_order)
async def process_custom_order(message: types.Message, state: FSMContext):
“”“Обробляє опис замовлення”””
if not message.text or len(message.text) < 5:
await message.answer(“❌ Будь ласка, напишіть детальніший опис (мінімум 5 символів)”)
return

```
await state.update_data(order_text=message.text)
await state.set_state(OrderStates.waiting_for_order_notes)

await message.answer(
    "✨ Спасибі! Ваш запит записано.\n\n"
    "📞 Хочете щоб ми з вами звʼязались або додати що-небудь ще?\n\n"
    "<i>Напишіть контактні дані, номер телефону або повідомте якщо це не потрібно (\"нi\" або \"-\")</i>",
    parse_mode=ParseMode.HTML
)
```

@dp.message(OrderStates.waiting_for_order_notes)
async def finalize_custom_order(message: types.Message, state: FSMContext):
“”“Завершує індивідуальне замовлення”””
data = await state.get_data()

```
notes = message.text if message.text not in ["нi", "-", "не"] else ""

order = add_order(
    user_id=message.from_user.id,
    username=message.from_user.username or "unknown",
    order_type="custom",
    items=[data["order_text"]],
    notes=notes
)

# Повідомлення користувачу
await message.answer(
    "✅ <b>Ваше замовлення прийнято!</b> 🎉\n\n"
    f"<code>Номер замовлення: #{order['id']}</code>\n\n"
    "⏳ Очікуйте на підтвердження. Ми незабаром вам напишемо!",
    parse_mode=ParseMode.HTML,
    reply_markup=main_keyboard()
)

# Повідомлення адміну
try:
    await bot.send_message(
        ADMIN_ID,
        f"🎉 <b>НОВЕ ЗАМОВЛЕННЯ!</b>\n\n{format_order_details(order)}",
        parse_mode=ParseMode.HTML,
        reply_markup=order_action_keyboard(order['id'])
    )
except Exception as e:
    logger.error(f"Помилка надсилання до адміна: {e}")

await state.clear()
```

# ============================================================

# АДМІНІСТРАТОР

# ============================================================

@dp.message(Command(“admin”))
async def cmd_admin(message: types.Message, state: FSMContext):
“”“Вхід в адміністраторський панель”””
if message.from_user.id != ADMIN_ID:
await message.answer(“❌ У вас немає прав доступу!”)
return

```
config = load_config()
await state.set_state(OrderStates.admin_waiting_for_password)
await message.answer(
    "🔐 <b>Адміністраторський вхід</b>\n\n"
    "Введіть пароль для входу:",
    parse_mode=ParseMode.HTML,
    reply_markup=ReplyKeyboardRemove()
)
```

@dp.message(OrderStates.admin_waiting_for_password)
async def check_admin_password(message: types.Message, state: FSMContext):
“”“Перевіряє пароль адміна”””
config = load_config()

```
if message.text != config["admin_password"]:
    await message.answer("❌ Невірний пароль!")
    await state.clear()
    return

await state.set_state(OrderStates.admin_panel)
await message.answer(
    "✅ <b>Ви увійшли в адміністраторський панель!</b>\n\n"
    "Виберіть дію:",
    parse_mode=ParseMode.HTML,
    reply_markup=admin_keyboard()
)
```

@dp.message(F.text == “📊 Замовлення”)
async def show_orders(message: types.Message, state: FSMContext):
“”“Показує всі замовлення”””
if message.from_user.id != ADMIN_ID:
return

```
orders = load_orders()

if not orders:
    await message.answer("📭 <b>Замовлень немає</b>", parse_mode=ParseMode.HTML)
    return

# Групуємо по статусу
pending = [o for o in orders if o["status"] == "pending"]
confirmed = [o for o in orders if o["status"] == "confirmed"]
completed = [o for o in orders if o["status"] == "completed"]

text = "📊 <b>ЗАМОВЛЕННЯ</b>\n\n"

if pending:
    text += f"⏳ <b>На розгляді ({len(pending)}):</b>\n"
    for o in pending[-3:]:  # останні 3
        text += f"  • #{o['id']} - @{o['username']}\n"
    text += "\n"

if confirmed:
    text += f"✅ <b>Підтверджені ({len(confirmed)}):</b>\n"
    for o in confirmed[-3:]:
        text += f"  • #{o['id']} - @{o['username']}\n"
    text += "\n"

if completed:
    text += f"🎁 <b>Виконані ({len(completed)}):</b>\n"
    for o in completed[-3:]:
        text += f"  • #{o['id']} - @{o['username']}\n"

text += "\n<i>Щоб переглянути деталі замовлення, напишіть номер (приклад: #1)</i>"

await message.answer(text, parse_mode=ParseMode.HTML)
```

@dp.message(F.text.startswith(”#”))
async def show_order_details(message: types.Message, state: FSMContext):
“”“Показує детальну інформацію про замовлення”””
if message.from_user.id != ADMIN_ID:
return

```
try:
    order_id = int(message.text.strip("#"))
    orders = load_orders()
    order = next((o for o in orders if o["id"] == order_id), None)
    
    if not order:
        await message.answer("❌ Замовлення не знайдено")
        return
    
    text = format_order_details(order)
    await message.answer(text, parse_mode=ParseMode.HTML, reply_markup=order_action_keyboard(order_id))
except ValueError:
    await message.answer("❌ Невірний формат. Напишіть #номер (приклад: #1)")
```

@dp.callback_query(F.data.startswith(“confirm_order_”))
async def confirm_order(callback: types.CallbackQuery, state: FSMContext):
“”“Підтверджує замовлення”””
if callback.from_user.id != ADMIN_ID:
await callback.answer(“❌ Немає прав”, show_alert=True)
return

```
try:
    order_id = int(callback.data.split("_")[2])
    orders = load_orders()
    order = next((o for o in orders if o["id"] == order_id), None)
    
    if not order:
        await callback.answer("❌ Замовлення не знайдено", show_alert=True)
        return
    
    order["status"] = "confirmed"
    order["confirmed_at"] = datetime.now().isoformat()
    save_orders(orders)
    
    config = load_config()
    
    # Повідомлення користувачу з картою
    user_message = (
        f"✅ <b>Ваше замовлення #{order['id']} підтверджено!</b>\n\n"
        f"💳 <b>Реквізити для передоплати:</b>\n\n"
        f"<code>{config['card']}</code>\n"
        f"<b>На ім'я:</b> {config['card_holder']}\n\n"
        f"📝 Після передоплати напишіть нам, і ми почнемо готувати ваше замовлення! 🎁"
    )
    
    try:
        await bot.send_message(order["user_id"], user_message, parse_mode=ParseMode.HTML)
    except Exception as e:
        logger.error(f"Помилка надсилання користувачу: {e}")
    
    await callback.answer("✅ Замовлення підтверджено!")
    await callback.message.edit_text(format_order_details(order), parse_mode=ParseMode.HTML)
    
except Exception as e:
    logger.error(f"Помилка підтвердження: {e}")
    await callback.answer("❌ Помилка", show_alert=True)
```

@dp.callback_query(F.data.startswith(“reject_order_”))
async def reject_order(callback: types.CallbackQuery):
“”“Відхиляє замовлення”””
if callback.from_user.id != ADMIN_ID:
await callback.answer(“❌ Немає прав”, show_alert=True)
return

```
try:
    order_id = int(callback.data.split("_")[2])
    orders = load_orders()
    orders = [o for o in orders if o["id"] != order_id]
    save_orders(orders)
    
    await callback.answer("✅ Замовлення відхилено!")
    await callback.message.edit_text("<b>❌ Замовлення видалено</b>", parse_mode=ParseMode.HTML)
except Exception as e:
    logger.error(f"Помилка відхилення: {e}")
```

@dp.message(F.text == “💰 Управління прайсом”)
async def manage_price(message: types.Message, state: FSMContext):
“”“Управління прайсом”””
if message.from_user.id != ADMIN_ID:
return

```
config = load_config()
text = "<b>💰 УПРАВЛІННЯ ПРАЙСОМ</b>\n\n"
text += format_price_list(config)

await message.answer(text, parse_mode=ParseMode.HTML, reply_markup=price_action_keyboard())
```

@dp.callback_query(F.data == “add_perfume”)
async def add_perfume_start(callback: types.CallbackQuery, state: FSMContext):
“”“Розпочинає додавання парфума”””
if callback.from_user.id != ADMIN_ID:
return

```
await state.set_state(OrderStates.admin_waiting_for_perfume_name)
await callback.message.answer(
    "➕ <b>Додавання нового парфума</b>\n\n"
    "Напишіть назву парфума:",
    parse_mode=ParseMode.HTML,
    reply_markup=ReplyKeyboardRemove()
)
await callback.answer()
```

@dp.message(OrderStates.admin_waiting_for_perfume_name)
async def add_perfume_name(message: types.Message, state: FSMContext):
“”“Отримує назву парфума”””
await state.update_data(perfume_name=message.text)
await state.set_state(OrderStates.admin_waiting_for_perfume_price)
await message.answer(“💵 Напишіть ціну (тільки число, в грн):”)

@dp.message(OrderStates.admin_waiting_for_perfume_price)
async def add_perfume_price(message: types.Message, state: FSMContext):
“”“Отримує ціну парфума”””
try:
price = int(message.text)
except ValueError:
await message.answer(“❌ Будь ласка напишіть число!”)
return

```
await state.update_data(perfume_price=price)
await state.set_state(OrderStates.admin_waiting_for_perfume_description)
await message.answer("📝 Напишіть опис парфума (з емодзі, приклад: Класичний аромат 🌹):")
```

@dp.message(OrderStates.admin_waiting_for_perfume_description)
async def add_perfume_description(message: types.Message, state: FSMContext):
“”“Отримує опис та додає парфум”””
data = await state.get_data()
config = load_config()

```
new_perfume = {
    "id": config["next_id"],
    "name": data["perfume_name"],
    "price": data["perfume_price"],
    "description": message.text
}

config["perfumes"].append(new_perfume)
config["next_id"] += 1
save_config(config)

text = (
    f"✅ <b>Парфум додано!</b>\n\n"
    f"🔹 <b>{new_perfume['name']}</b>\n"
    f"{new_perfume['description']}\n"
    f"💵 {new_perfume['price']} грн"
)

await message.answer(text, parse_mode=ParseMode.HTML, reply_markup=admin_keyboard())
await state.clear()
```

@dp.callback_query(F.data == “delete_perfume”)
async def delete_perfume_start(callback: types.CallbackQuery, state: FSMContext):
“”“Розпочинає видалення парфума”””
if callback.from_user.id != ADMIN_ID:
return

```
config = load_config()
text = "<b>❌ Видалення парфума</b>\n\n"
text += "Парфуми:\n"
for p in config["perfumes"]:
    text += f"  ID: <code>{p['id']}</code> - {p['name']} ({p['price']} грн)\n"

text += "\n📝 Напишіть ID парфума для видалення:"

await state.set_state(OrderStates.admin_waiting_for_delete_id)
await callback.message.answer(text, parse_mode=ParseMode.HTML, reply_markup=ReplyKeyboardRemove())
await callback.answer()
```

@dp.message(OrderStates.admin_waiting_for_delete_id)
async def delete_perfume(message: types.Message, state: FSMContext):
“”“Видаляє парфум”””
try:
perfume_id = int(message.text)
except ValueError:
await message.answer(“❌ Напишіть число!”)
return

```
config = load_config()
perfume = next((p for p in config["perfumes"] if p["id"] == perfume_id), None)

if not perfume:
    await message.answer("❌ Парфум не знайдено!")
    return

config["perfumes"] = [p for p in config["perfumes"] if p["id"] != perfume_id]
save_config(config)

await message.answer(
    f"✅ Парфум <b>{perfume['name']}</b> видалено!",
    parse_mode=ParseMode.HTML,
    reply_markup=admin_keyboard()
)
await state.clear()
```

@dp.callback_query(F.data == “edit_perfume”)
async def edit_perfume_start(callback: types.CallbackQuery, state: FSMContext):
“”“Розпочинає редагування парфума”””
if callback.from_user.id != ADMIN_ID:
return

```
config = load_config()
text = "<b>✏️ Редагування парфума</b>\n\n"
for p in config["perfumes"]:
    text += f"ID: <code>{p['id']}</code> - {p['name']}\n"

text += "\n📝 Напишіть ID парфума:"

await state.set_state(OrderStates.admin_waiting_for_delete_id)
await callback.message.answer(text, parse_mode=ParseMode.HTML, reply_markup=ReplyKeyboardRemove())
await callback.answer()
```

@dp.message(F.text == “💳 Налаштування карти”)
async def setup_card(message: types.Message, state: FSMContext):
“”“Налаштування карти”””
if message.from_user.id != ADMIN_ID:
return

```
config = load_config()

text = (
    "💳 <b>НАЛАШТУВАННЯ КАРТИ</b>\n\n"
    f"<b>Поточні реквізити:</b>\n"
    f"<code>{config['card']}</code>\n"
    f"<b>На ім'я:</b> {config['card_holder']}\n\n"
    "Напишіть новий номер карти:"
)

await state.set_state(OrderStates.admin_waiting_for_card)
await message.answer(text, parse_mode=ParseMode.HTML, reply_markup=ReplyKeyboardRemove())
```

@dp.message(OrderStates.admin_waiting_for_card)
async def set_card_number(message: types.Message, state: FSMContext):
“”“Встановлює номер карти”””
await state.update_data(card=message.text)
await state.set_state(OrderStates.admin_waiting_for_card_holder)
await message.answer(“👤 Напишіть ім’я власника карти:”)

@dp.message(OrderStates.admin_waiting_for_card_holder)
async def set_card_holder(message: types.Message, state: FSMContext):
“”“Встановлює ім’я власника карти”””
data = await state.get_data()
config = load_config()

```
config["card"] = data["card"]
config["card_holder"] = message.text
save_config(config)

await message.answer(
    f"✅ <b>Карта оновлена!</b>\n\n"
    f"<code>{config['card']}</code>\n"
    f"<b>На ім'я:</b> {config['card_holder']}",
    parse_mode=ParseMode.HTML,
    reply_markup=admin_keyboard()
)
await state.clear()
```

@dp.message(F.text == “🎵 TikTok синхронізація”)
async def tiktok_sync(message: types.Message):
“”“TikTok синхронізація”””
if message.from_user.id != ADMIN_ID:
return

```
await message.answer("🔄 Перевіряю нові видео на TikTok...", parse_mode=ParseMode.HTML)

tiktok_count = await run_tiktok_sync()

if tiktok_count:
    result = f"✅ <b>Знайдено {tiktok_count} нових видео!</b>\n\nВони опубліковані в каналі {CHANNEL_ID} 🚀"
else:
    result = "📪 <b>Нічого нового</b>. Всі актуальні видео вже опубліковані."

await message.answer(result, parse_mode=ParseMode.HTML)
```

@dp.message(F.text == “🔐 Вихід”)
async def admin_logout(message: types.Message, state: FSMContext):
“”“Вихід з адміністраторського панелю”””
if message.from_user.id != ADMIN_ID:
return

```
await state.clear()
await message.answer(
    "👋 <b>Ви вийшли з адміністраторського панелю</b>",
    parse_mode=ParseMode.HTML,
    reply_markup=main_keyboard()
)
```

# ============================================================

# ФОНОВИЙ ЦИКЛ TIKTOK

# ============================================================

async def auto_tiktok_loop():
“”“Автоматична перевірка TikTok”””
await asyncio.sleep(30)
while True:
try:
await run_tiktok_sync(notify_admin=True)
except Exception as e:
logger.error(f”Помилка у фоновому циклі TikTok: {e}”)
await asyncio.sleep(CHECK_INTERVAL)

# ============================================================

# СТАРТ БОТА

# ============================================================

async def main():
logger.info(“🚀 Запуск бота парфумів…”)
asyncio.create_task(auto_tiktok_loop())
await dp.start_polling(bot, skip_updates=True)

if **name** == “**main**”:
asyncio.run(main())