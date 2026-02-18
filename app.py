import asyncio
import sqlite3
import logging
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# --- SOZLAMALAR ---
API_TOKEN = '8466034417:AAFYBovyZBTEk4OA5YUm86HMwhRe7xeJj_k'
ADMIN_ID = 7653548625  # O'zingizning Telegram ID raqamingizni yozing!

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# --- MA'LUMOTLAR BAZASI (SQLite) ---
def init_db():
    conn = sqlite3.connect('bot_bazasi.db')
    cursor = conn.cursor()
    # Foydalanuvchilar jadvali
    cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                      (user_id INTEGER PRIMARY KEY, username TEXT)''')
    conn.commit()
    conn.close()

def add_user(user_id, username):
    conn = sqlite3.connect('bot_bazasi.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)', (user_id, username))
    conn.commit()
    conn.close()

def get_users_count():
    conn = sqlite3.connect('bot_bazasi.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM users')
    count = cursor.fetchone()[0]
    conn.close()
    return count

# --- BOT BUYRUQLARI ---

@dp.message(CommandStart())
async def start_command(message: types.Message):
    # Foydalanuvchini bazaga qo'shish
    add_user(message.from_user.id, message.from_user.username)
    
    # Majburiy obuna tugmasi (Namuna)
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Kanalga obuna bo'lish", url="https://t.me/telegram")],
        [InlineKeyboardButton(text="✅ Obunani tekshirish", callback_data="check_sub")]
    ])
    
    await message.answer(f"Assalomu alaykum, {message.from_user.first_name}!\n\n"
                         f"Kino yoki faylni olish uchun maxsus kodni yuboring. \n"
                         f"Lekin avval kanalimizga obuna bo'lishingiz kerak!", reply_markup=markup)

@dp.callback_query(F.data == "check_sub")
async def check_subscription(callback: types.CallbackQuery):
    # Bu yerda obunani tekshirish mantiqi yoziladi
    await callback.answer("Obuna tekshirildi! Endi fayl kodini yuborishingiz mumkin.", show_alert=True)

# ADMIN PANEL (Faqat ADMIN_ID da ishlaydi)
@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        users_count = get_users_count()
        await message.answer(f"📊 <b>Admin Panel</b>\n\n"
                             f"👥 Botdagi jami foydalanuvchilar: {users_count} ta\n\n"
                             f"Ushbu paneldan kinolar/fayllar qo'shish va reklama tarqatish uchun foydalanishingiz mumkin.", parse_mode="HTML")
    else:
        await message.answer("Siz admin emassiz!")

# KOD ORQALI FAYL BERISH QISMI
@dp.message(F.text.isdigit())
async def send_file_by_code(message: types.Message):
    file_code = message.text
    # Mijoz uchun shu yerga kodga mos kinoni bazadan qidirib topish qismi yoziladi
    await message.answer(f"Siz {file_code} kodini yubordingiz. \n"
                         f"(Bu joyga bazadan kodga mos fayl/kino yuboriladigan qilib sozlanadi)")

async def main():
    init_db()  # Bot ishga tushganda bazani yaratish
    print("Bot muvaffaqiyatli ishga tushdi!")
    await dp.start_polling(bot, skip_updates=True)

if __name__ == '__main__':
    asyncio.run(main())
