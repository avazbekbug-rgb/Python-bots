import os
import sqlite3
import telebot
from telebot.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
)

# --- SOZLAMALAR (PROFESSIONAL) ---
# TOKEN va ADMIN_ID ni environment dan olishga harakat qilamiz.
# Agar topilmasa, mavjud qiymatlarga fallback bo'ladi.
DEFAULT_TOKEN = "8466034417:AAFYBovyZBTEk4OA5YUm86HMwhRe7xeJj_k"
DEFAULT_ADMIN_ID = 7653548625  # O'zingizning Telegram ID raqamingizni yozing

TOKEN = os.getenv("BOT_TOKEN", DEFAULT_TOKEN)
ADMIN_ID = int(os.getenv("ADMIN_ID", DEFAULT_ADMIN_ID))
CHANNELS = ["@as_ex"]  # Kanallaringiz useri

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")
admin_data = {}  # Admin qadamlarini saqlash uchun

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
    with sqlite3.connect("movies.db") as conn:
        c = conn.cursor()
        c.execute(
            """CREATE TABLE IF NOT EXISTS movies (
                code INTEGER PRIMARY KEY,
                file_id TEXT,
                name TEXT
            )"""
        )
        c.execute(
            """CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                lang TEXT,
                is_blocked INTEGER DEFAULT 0
            )"""
        )
        # Agar eski jadval bo'lsa, ustun qo'shishga urinib ko'ramiz
        try:
            c.execute("ALTER TABLE users ADD COLUMN is_blocked INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            # Ustun allaqachon mavjud bo'lishi mumkin
            pass
        conn.commit()

init_db()

def get_user_lang(user_id):
    with sqlite3.connect("movies.db") as conn:
        c = conn.cursor()
        c.execute("SELECT lang FROM users WHERE user_id=?", (user_id,))
        res = c.fetchone()
    return res[0] if res else 'uz'


def is_user_blocked(user_id):
    with sqlite3.connect("movies.db") as conn:
        c = conn.cursor()
        c.execute("SELECT is_blocked FROM users WHERE user_id=?", (user_id,))
        row = c.fetchone()
    return bool(row and row[0])

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
@bot.message_handler(commands=["start"])
def start_cmd(message):
    """Boshlang'ich /start komandasi."""
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("🇺🇿 O'zbekcha", callback_data="lang_uz"),
        InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"),
    )
    bot.send_message(
        message.chat.id,
        "Tilni tanlang / Выберите язык:",
        reply_markup=markup,
    )


@bot.message_handler(commands=["help"])
def help_cmd(message):
    """Foydalanuvchi uchun qisqacha yo'riqnoma."""
    lang = get_user_lang(message.from_user.id)
    if lang == "ru":
        text = (
            "ℹ️ <b>Инструкция по использованию бота</b>\n\n"
            "1️⃣ Подпишитесь на все обязательные каналы.\n"
            "2️⃣ Нажмите кнопку «✅ Проверить».\n"
            "3️⃣ Введите числовой код фильма (например: <code>101</code>).\n"
            "4️⃣ Бот отправит вам фильм, если такой код существует."
        )
    else:
        text = (
            "ℹ️ <b>Botdan foydalanish bo'yicha qo'llanma</b>\n\n"
            "1️⃣ Avval barcha majburiy kanallarga obuna bo'ling.\n"
            "2️⃣ «✅ Tekshirish» tugmasini bosing.\n"
            "3️⃣ Kino kodini raqam ko'rinishida yuboring (masalan: <code>101</code>).\n"
            "4️⃣ Agar bunday kodli kino bo'lsa, bot sizga yuboradi."
        )
    bot.reply_to(message, text)

@bot.callback_query_handler(func=lambda call: call.data.startswith('lang_'))
def set_lang(call):
    lang = call.data.split('_')[1]
    user_id = call.from_user.id

    # Bazaga foydalanuvchini qo'shish yoki yangilash
    with sqlite3.connect("movies.db") as conn:
        c = conn.cursor()
        c.execute(
            """
            INSERT INTO users (user_id, lang, is_blocked)
            VALUES (?, ?, 0)
            ON CONFLICT(user_id) DO UPDATE SET lang=excluded.lang
            """,
            (user_id, lang),
        )
        conn.commit()

    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass

    if check_sub(user_id):
        bot.send_message(user_id, LANG[lang]['success'])
    else:
        bot.send_message(user_id, LANG[lang]['sub_text'], reply_markup=sub_keyboard(lang))

@bot.callback_query_handler(func=lambda call: call.data == "check_sub")
def verify_sub(call):
    user_id = call.from_user.id
    lang = get_user_lang(user_id)

    if check_sub(user_id):
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception:
            pass
        bot.send_message(user_id, LANG[lang]['success'])
    else:
        bot.answer_callback_query(call.id, LANG[lang]['error'], show_alert=True)

# --- ADMIN PANEL (Kino yuklash) ---
@bot.message_handler(content_types=["video"])
def handle_video(message):
    if message.from_user.id == ADMIN_ID:
        admin_data[ADMIN_ID] = {"file_id": message.video.file_id, "step": "name"}
        bot.reply_to(
            message,
            "🎬 Video qabul qilindi.\n\nIltimos, kino nomini yuboring (masalan: <b>Fast & Furious 9</b>):",
        )

@bot.message_handler(
    func=lambda m: m.from_user.id == ADMIN_ID
    and admin_data.get(ADMIN_ID, {}).get("step") == "name"
)
def ask_for_code(message):
    admin_data[ADMIN_ID]["name"] = message.text.strip()
    admin_data[ADMIN_ID]["step"] = "code"

    # Bosh kodlarni va oxirgi kodlarni ko'rsatish
    with sqlite3.connect('movies.db') as conn:
        c = conn.cursor()
        c.execute("SELECT code FROM movies ORDER BY code DESC LIMIT 5")
        codes = c.fetchall()

    last_codes = ", ".join([str(x[0]) for x in codes]) if codes else "Bazada hali kino yo'q"

    bot.send_message(
        ADMIN_ID,
        (
            f"Nomi saqlandi: <b>{admin_data[ADMIN_ID]['name']}</b>\n\n"
            f"📈 Oxirgi ishlatilgan kodlar: {last_codes}\n\n"
            "🔢 Endi bu kino uchun <b>bo'sh</b> bo'lgan raqam (kod) yuboring:"
        ),
    )

@bot.message_handler(
    func=lambda m: m.from_user.id == ADMIN_ID
    and admin_data.get(ADMIN_ID, {}).get("step") == "code"
)
def save_movie(message):
    if not message.text or not message.text.isdigit():
        bot.send_message(ADMIN_ID, "⚠️ Iltimos, kod sifatida faqat raqam kiriting!")
        return

    code = int(message.text)
    movie_info = admin_data.get(ADMIN_ID)
    if not movie_info:
        bot.send_message(
            ADMIN_ID, "⚠️ Sessiya topilmadi. Iltimos, videoni qayta yuboring."
        )
        return

    file_id = movie_info["file_id"]
    name = movie_info["name"]

    with sqlite3.connect('movies.db') as conn:
        c = conn.cursor()
        try:
            c.execute(
                "INSERT INTO movies (code, file_id, name) VALUES (?, ?, ?)",
                (code, file_id, name),
            )
            conn.commit()
            bot.send_message(
                ADMIN_ID,
                (
                    "✅ <b>Kino muvaffaqiyatli saqlandi!</b>\n\n"
                    f"🎬 Nomi: <b>{name}</b>\n"
                    f"🔢 Kodi: <code>{code}</code>"
                ),
            )
            admin_data.pop(ADMIN_ID, None)  # Admin holatini tozalash
        except sqlite3.IntegrityError:
            bot.send_message(
                ADMIN_ID,
                "❌ Bu kod avvalroq band qilingan! Iltimos, boshqa bo'sh kod kiriting:",
            )


@bot.message_handler(commands=["panel"])
def admin_panel(message):
    """Oddiy admin menyu."""
    if message.from_user.id != ADMIN_ID:
        return

    text = (
        "🛠 <b>Admin panel</b>\n\n"
        "📤 Video yuboring → nomini va kodini kiritib, bazaga qo'shing.\n"
        "ℹ️ /help → foydalanuvchilar uchun yo'riqnoma.\n\n"
        "Quyidagi tugmalar orqali ro'yxatlarni ko'rishingiz mumkin."
    )

    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(
        KeyboardButton("🎬 Kinolar ro'yxati"),
        KeyboardButton("👥 Foydalanuvchilar ro'yxati"),
    )
    markup.row(KeyboardButton("🚫 Bloklanganlar ro'yxati"))

    bot.send_message(message.chat.id, text, reply_markup=markup)


@bot.message_handler(
    func=lambda m: m.from_user.id == ADMIN_ID and m.text == "🎬 Kinolar ro'yxati"
)
def list_movies(message):
    with sqlite3.connect("movies.db") as conn:
        c = conn.cursor()
        c.execute("SELECT code, name FROM movies ORDER BY code LIMIT 30")
        rows = c.fetchall()
        c.execute("SELECT COUNT(*) FROM movies")
        total = c.fetchone()[0]

    if not rows:
        bot.reply_to(message, "📂 Bazada hali birorta kino yo'q.")
        return

    lines = ["🎬 <b>Kinolar ro'yxati (birinchi 30 ta)</b>"]
    for code, name in rows:
        lines.append(f"• <code>{code}</code> — {name}")
    lines.append(f"\nJami: <b>{total}</b> ta kino.")

    bot.reply_to(message, "\n".join(lines))


@bot.message_handler(
    func=lambda m: m.from_user.id == ADMIN_ID and m.text == "👥 Foydalanuvchilar ro'yxati"
)
def list_users(message):
    with sqlite3.connect("movies.db") as conn:
        c = conn.cursor()
        c.execute(
            """
            SELECT user_id, lang, is_blocked
            FROM users
            ORDER BY user_id
            LIMIT 30
            """
        )
        rows = c.fetchall()
        c.execute("SELECT COUNT(*) FROM users")
        total = c.fetchone()[0]

    if not rows:
        bot.reply_to(message, "👥 Hali foydalanuvchilar bazaga yozilmagan.")
        return

    lines = ["👥 <b>Foydalanuvchilar ro'yxati (birinchi 30 ta)</b>"]
    for user_id, lang, is_blocked in rows:
        status = "🚫 blok" if is_blocked else "✅ aktiv"
        lines.append(f"• <code>{user_id}</code> — til: {lang}, holat: {status}")
    lines.append(f"\nJami: <b>{total}</b> ta foydalanuvchi.")

    bot.reply_to(message, "\n".join(lines))


@bot.message_handler(
    func=lambda m: m.from_user.id == ADMIN_ID and m.text == "🚫 Bloklanganlar ro'yxati"
)
def list_blocked_users(message):
    with sqlite3.connect("movies.db") as conn:
        c = conn.cursor()
        c.execute(
            """
            SELECT user_id, lang
            FROM users
            WHERE is_blocked = 1
            ORDER BY user_id
            """
        )
        rows = c.fetchall()

    if not rows:
        bot.reply_to(message, "✅ Hozircha bloklangan foydalanuvchi yo'q.")
        return

    lines = ["🚫 <b>Bloklangan foydalanuvchilar ro'yxati</b>"]
    for user_id, lang in rows:
        lines.append(f"• <code>{user_id}</code> — til: {lang}")

    bot.reply_to(message, "\n".join(lines))


@bot.message_handler(commands=["block"])
def block_user(message):
    if message.from_user.id != ADMIN_ID:
        return

    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        bot.reply_to(
            message,
            "🚫 Foydalanuvchini bloklash uchun:\n"
            "<code>/block USER_ID</code> shaklida yuboring.",
        )
        return

    target_id = int(parts[1])
    with sqlite3.connect("movies.db") as conn:
        c = conn.cursor()
        c.execute(
            """
            INSERT INTO users (user_id, lang, is_blocked)
            VALUES (?, 'uz', 1)
            ON CONFLICT(user_id) DO UPDATE SET is_blocked = 1
            """,
            (target_id,),
        )
        conn.commit()

    bot.reply_to(message, f"🚫 <code>{target_id}</code> bloklandi.")


@bot.message_handler(commands=["unblock"])
def unblock_user(message):
    if message.from_user.id != ADMIN_ID:
        return

    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        bot.reply_to(
            message,
            "✅ Foydalanuvchini blokdan chiqarish uchun:\n"
            "<code>/unblock USER_ID</code> shaklida yuboring.",
        )
        return

    target_id = int(parts[1])
    with sqlite3.connect("movies.db") as conn:
        c = conn.cursor()
        c.execute(
            """
            UPDATE users
            SET is_blocked = 0
            WHERE user_id = ?
            """,
            (target_id,),
        )
        conn.commit()

    bot.reply_to(message, f"✅ <code>{target_id}</code> blokdan chiqarildi.")

# --- FOYDALANUVCHILAR UCHUN KINO QIDIRISH ---
@bot.message_handler(func=lambda m: bool(m.text) and m.text.isdigit())
def send_movie(message):
    user_id = message.from_user.id
    lang = get_user_lang(user_id)

    if is_user_blocked(user_id):
        if lang == "ru":
            bot.send_message(user_id, "🚫 Вы были заблокированы в этом боте.")
        else:
            bot.send_message(user_id, "🚫 Siz bu botda bloklangansiz.")
        return

    if not check_sub(user_id):
        bot.send_message(user_id, LANG[lang]['sub_text'], reply_markup=sub_keyboard(lang))
        return

    code = int(message.text)
    with sqlite3.connect('movies.db') as conn:
        c = conn.cursor()
        c.execute("SELECT file_id, name FROM movies WHERE code=?", (code,))
        res = c.fetchone()

    if res:
        file_id, name = res
        try:
            bot.send_video(
                chat_id=user_id,
                video=file_id,
                caption=f"🎬 {name}",
            )
        except Exception as e:
            # Minimal log
            print(f"Failed to send video to {user_id}: {e}")
            bot.send_message(
                user_id,
                "❌ Kino yuborishda xatolik yuz berdi. Iltimos, keyinroq qayta urinib ko'ring.",
            )
    else:
        bot.send_message(user_id, LANG[lang]["not_found"])


@bot.message_handler(func=lambda m: True)
def fallback_handler(message):
    """Har qanday boshqa matn uchun javob."""
    lang = get_user_lang(message.from_user.id)

    if is_user_blocked(message.from_user.id):
        return
    if message.text and message.text.startswith("/"):
        # Noma'lum komandalar
        if lang == "ru":
            bot.reply_to(
                message,
                "❓ Неизвестная команда. Используйте /start или /help.",
            )
        else:
            bot.reply_to(
                message,
                "❓ Noma'lum buyruq. /start yoki /help dan foydalaning.",
            )
        return

    # Oddiy matnlar uchun yo'riqnoma
    if lang == "ru":
        bot.reply_to(
            message,
            "🔢 Пожалуйста, отправьте <b>только числовой код</b> фильма.\nНапример: <code>101</code>",
        )
    else:
        bot.reply_to(
            message,
            "🔢 Iltimos, faqat kino <b>kodini raqam ko'rinishida</b> yuboring.\nMasalan: <code>101</code>",
        )


# Botni ishga tushirish
if __name__ == "__main__":
    print("Bot ishga tushdi...")
    bot.infinity_polling()
