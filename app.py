import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import sqlite3

# --- SOZLAMALAR ---
TOKEN = '8466034417:AAFYBovyZBTEk4OA5YUm86HMwhRe7xeJj_k'
ADMIN_ID = 7653548625  # O'zingizning Telegram ID raqamingizni yozing
CHANNELS = ['@sobirov_exe', '@PhonkuzX'] # Kanallaringiz useri

bot = telebot.TeleBot(TOKEN)
admin_data = {} # Admin qadamlarini saqlash uchun

# --- LUG'AT (Til sozlamalari) ---
LANG = {
    'uz': {
        'sub_text': "Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling:",
        'sub_btn': "➕ Obuna bo'lish",
        'check_btn': "✅ Tekshirish",
        'success': "Obuna tasdiqlandi! Kino kodini yuboring:",
        'error': "❌ Hali hamma kanallarga obuna bo'lmadingiz!",
        'not_found': "Bunday kodli kino topilmadi."
    },
    'ru': {
        'sub_text': "Для использования бота подпишитесь на следующие каналы:",
        'sub_btn': "➕ Подписаться",
        'check_btn': "✅ Проверить",
        'success': "Подписка подтверждена! Отправьте код фильма:",
        'error': "❌ Вы еще не подписались на все каналы!",
        'not_found': "Фильм с таким кодом не найден."
    }
}

# --- MA'LUMOTLAR BAZASI ---
def init_db():
    conn = sqlite3.connect('movies.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS movies (code INTEGER PRIMARY KEY, file_id TEXT, name TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, lang TEXT)''')
    conn.commit()
    conn.close()

init_db()

def get_user_lang(user_id):
    conn = sqlite3.connect('movies.db')
    c = conn.cursor()
    c.execute("SELECT lang FROM users WHERE user_id=?", (user_id,))
    res = c.fetchone()
    conn.close()
    return res[0] if res else 'uz'

# --- MAJBURIY OBUNA TEKSHIRUVI ---
def check_sub(user_id):
    for ch in CHANNELS:
        try:
            status = bot.get_chat_member(ch, user_id).status
            if status in ['left', 'kicked']:
                return False
        except Exception:
            # Agar bot kanalga admin bo'lmasa xato beradi
            pass
    return True

def sub_keyboard(lang_code):
    markup = InlineKeyboardMarkup()
    for idx, ch in enumerate(CHANNELS):
        markup.add(InlineKeyboardButton(text=f"{LANG[lang_code]['sub_btn']} {idx+1}", url=f"https://t.me/{ch.replace('@', '')}"))
    markup.add(InlineKeyboardButton(text=LANG[lang_code]['check_btn'], callback_data="check_sub"))
    return markup

# --- START VA TIL TANLASH ---
@bot.message_handler(commands=['start'])
def start_cmd(message):
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("🇺🇿 O'zbekcha", callback_data="lang_uz"),
        InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru")
    )
    bot.send_message(message.chat.id, "Tilni tanlang / Выберите язык:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('lang_'))
def set_lang(call):
    lang = call.data.split('_')[1]
    user_id = call.from_user.id

    # Bazaga foydalanuvchini qo'shish yoki yangilash
    conn = sqlite3.connect('movies.db')
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO users (user_id, lang) VALUES (?, ?)", (user_id, lang))
    conn.commit()
    conn.close()

    bot.delete_message(call.message.chat.id, call.message.message_id)

    if check_sub(user_id):
        bot.send_message(user_id, LANG[lang]['success'])
    else:
        bot.send_message(user_id, LANG[lang]['sub_text'], reply_markup=sub_keyboard(lang))

@bot.callback_query_handler(func=lambda call: call.data == "check_sub")
def verify_sub(call):
    user_id = call.from_user.id
    lang = get_user_lang(user_id)

    if check_sub(user_id):
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(user_id, LANG[lang]['success'])
    else:
        bot.answer_callback_query(call.id, LANG[lang]['error'], show_alert=True)

# --- ADMIN PANEL (Kino yuklash) ---
@bot.message_handler(content_types=['video'])
def handle_video(message):
    if message.from_user.id == ADMIN_ID:
        admin_data[ADMIN_ID] = {'file_id': message.video.file_id, 'step': 'name'}
        bot.reply_to(message, "🎬 Video qabul qilindi. Iltimos, kino nomini yozing:")

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and admin_data.get(ADMIN_ID, {}).get('step') == 'name')
def ask_for_code(message):
    admin_data[ADMIN_ID]['name'] = message.text
    admin_data[ADMIN_ID]['step'] = 'code'

    # Bosh kodlarni va oxirgi kodlarni ko'rsatish
    conn = sqlite3.connect('movies.db')
    c = conn.cursor()
    c.execute("SELECT code FROM movies ORDER BY code DESC LIMIT 5")
    codes = c.fetchall()
    conn.close()

    last_codes = ", ".join([str(x[0]) for x in codes]) if codes else "Bazada hali kino yo'q"

    bot.send_message(ADMIN_ID, f"Nomi saqlandi: *{message.text}*\n\n📈 Oxirgi ishlatilgan kodlar: {last_codes}\n\n🔢 Endi bu kino uchun bo'sh bo'lgan raqam (kod) yuboring:", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and admin_data.get(ADMIN_ID, {}).get('step') == 'code')
def save_movie(message):
    if not message.text.isdigit():
        bot.send_message(ADMIN_ID, "⚠️ Iltimos, kod sifatida faqat raqam kiriting!")
        return

    code = int(message.text)
    file_id = admin_data[ADMIN_ID]['file_id']
    name = admin_data[ADMIN_ID]['name']

    conn = sqlite3.connect('movies.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO movies (code, file_id, name) VALUES (?, ?, ?)", (code, file_id, name))
        conn.commit()
        bot.send_message(ADMIN_ID, f"✅ Muvaffaqiyatli saqlandi!\n\n🎬 Kino: {name}\n🔢 Kodi: {code}")
        admin_data.pop(ADMIN_ID) # Admin holatini tozalash
    except sqlite3.IntegrityError:
        bot.send_message(ADMIN_ID, "❌ Bu kod avvalroq band qilingan! Boshqa bo'sh kod kiriting:")
    conn.close()

# --- FOYDALANUVCHILAR UCHUN KINO QIDIRISH ---
@bot.message_handler(func=lambda m: m.text.isdigit())
def send_movie(message):
    user_id = message.from_user.id
    lang = get_user_lang(user_id)

    if not check_sub(user_id):
        bot.send_message(user_id, LANG[lang]['sub_text'], reply_markup=sub_keyboard(lang))
        return

    code = int(message.text)
    conn = sqlite3.connect('movies.db')
    c = conn.cursor()
    c.execute("SELECT file_id, name FROM movies WHERE code=?", (code,))
    res = c.fetchone()
    conn.close()

    if res:
        bot.send_video(chat_id=user_id, video=res[0], caption=f"🎬 {res[1]}")
    else:
        bot.send_message(user_id, LANG[lang]['not_found'])

# Botni ishga tushirish
if __name__ == "__main__":
    print("Bot ishga tushdi...")
    bot.infinity_polling()
