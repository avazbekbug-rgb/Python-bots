import asyncio
import sqlite3
import logging
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# --- SOZLAMALAR ---
API_TOKEN = '8466034417:AAFYBovyZBTEk4OA5YUm86HMwhRe7xeJj_k'
ADMIN_ID = 7653548625  # Sizning ID raqamingiz

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# --- HOLATLAR (Kino qo'shish jarayoni) ---
class MovieState(StatesGroup):
    waiting_for_video = State()
    waiting_for_code = State()

# --- MA'LUMOTLAR BAZASI ---
def init_db():
    conn = sqlite3.connect('bot_bazasi.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT)''')
    # Endi file_id emas, message_id (xabar raqami) saqlaymiz
    cursor.execute('''CREATE TABLE IF NOT EXISTS movies (code TEXT PRIMARY KEY, message_id INTEGER)''')
    conn.commit()
    conn.close()

def add_user(user_id, username):
    conn = sqlite3.connect('bot_bazasi.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)', (user_id, username))
    conn.commit()
    conn.close()

def add_movie(code, message_id):
    conn = sqlite3.connect('bot_bazasi.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR REPLACE INTO movies (code, message_id) VALUES (?, ?)', (code, message_id))
    conn.commit()
    conn.close()

def get_movie(code):
    conn = sqlite3.connect('bot_bazasi.db')
    cursor = conn.cursor()
    cursor.execute('SELECT message_id FROM movies WHERE code = ?', (code,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def get_users_count():
    conn = sqlite3.connect('bot_bazasi.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM users')
    count = cursor.fetchone()[0]
    conn.close()
    return count

# --- FOYDALANUVCHI QISMI ---
@dp.message(CommandStart())
async def start_command(message: types.Message):
    add_user(message.from_user.id, message.from_user.username)
    
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Kanalga obuna bo'lish", url="https://t.me/telegram")], 
        [InlineKeyboardButton(text="✅ Obunani tekshirish", callback_data="check_sub")]
    ])
    
    await message.answer(f"Assalomu alaykum, {message.from_user.first_name}!\n\n"
                         f"Kino yoki faylni olish uchun maxsus kodni yuboring.", reply_markup=markup)

@dp.callback_query(F.data == "check_sub")
async def check_subscription(callback: types.CallbackQuery):
    await callback.answer("Obuna tekshirildi! Endi fayl kodini yuborishingiz mumkin.", show_alert=True)

# --- ADMIN PANEL QISMI ---
@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        users_count = get_users_count()
        admin_keyboard = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="🎬 Yangi kino qo'shish")]],
            resize_keyboard=True
        )
        await message.answer(f"📊 <b>Admin Panel</b>\n\n"
                             f"👥 Botdagi jami foydalanuvchilar: {users_count} ta", 
                             parse_mode="HTML", reply_markup=admin_keyboard)
    else:
        await message.answer("Siz admin emassiz!")

# --- KINO QO'SHISH JARAYONI ---
@dp.message(F.text == "🎬 Yangi kino qo'shish")
async def ask_for_video(message: types.Message, state: FSMContext):
    if message.from_user.id == ADMIN_ID:
        await message.answer("Iltimos, botga kino (video yoki fayl) yuboring:\n\n"
                             "<i>Eslatma: Telegram botlar 2 GB gacha bo'lgan fayllarni qabul qila oladi!</i>", parse_mode="HTML")
        await state.set_state(MovieState.waiting_for_video)

@dp.message(MovieState.waiting_for_video)
async def ask_for_code(message: types.Message, state: FSMContext):
    if not (message.video or message.document or message.photo):
        await message.answer("Iltimos, faqat video, rasm yoki fayl yuboring!")
        return
        
    # Biz endi yuborilgan xabarning o'zining ID raqamini saqlab olamiz
    await state.update_data(message_id=message.message_id)
    
    await message.answer("Ajoyib! Endi bu kino uchun qandaydir kod o'ylab toping (masalan: 125):")
    await state.set_state(MovieState.waiting_for_code)

@dp.message(MovieState.waiting_for_code)
async def save_movie(message: types.Message, state: FSMContext):
    movie_code = message.text
    user_data = await state.get_data()
    msg_id = user_data['message_id']
    
    # Bazaga kodni va xabar ID sini saqlaymiz
    add_movie(movie_code, msg_id)
    
    await message.answer(f"✅ Kino muvaffaqiyatli saqlandi!\n\nKino kodi: <b>{movie_code}</b>", parse_mode="HTML")
    await state.clear()

# --- MIJOZLARGA KOD ORQALI KINO BERISH ---
@dp.message(F.text.isdigit())
async def send_file_by_code(message: types.Message):
    file_code = message.text
    movie_msg_id = get_movie(file_code) 
    
    if movie_msg_id:
        try:
            # Bot admin chatidagi o'sha xabarni topib, aynan nusxasini mijozga tashlab beradi
            await bot.copy_message(chat_id=message.chat.id, from_chat_id=ADMIN_ID, message_id=movie_msg_id)
        except Exception as e:
            await message.answer("❌ Faylni yuborishda xatolik yuz berdi.")
            logging.error(e)
    else:
        await message.answer("❌ Kechirasiz, bunday kodli kino topilmadi.")

async def main():
    init_db()
    print("Bot muvaffaqiyatli ishga tushdi!")
    await dp.start_polling(bot, skip_updates=True)

if __name__ == '__main__':
    asyncio.run(main())
