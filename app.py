import logging
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import ChatMemberUpdated

# Bot tokeningizni bura yozing
API_TOKEN = '8351061314:AAEAwTvF16zsMrRvF4PnR-HVCrhYLjd6dDE'

# Loglarni sozlash
logging.basicConfig(level=logging.INFO)

# Bot va Dispatcher obyektlarini yaratish
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

@dp.my_chat_member()
async def delete_join_leave_messages(update: ChatMemberUpdated):
    """
    Kanal yoki guruhga kirdi-chiqdi xabarlarini o'chirish
    """
    try:
        # Yeni a'zolarni yoki chiqib ketganlarni kuzatib olish
        if update.new_chat_member.status in ['member', 'left']:
            logging.info(f"A'zo holati o'zgartirildi: {update.new_chat_member.user.id}")
    except Exception as e:
        logging.error(f"Xabarni qayta ishlashda xatolik: {e}")

async def main():
    await dp.start_polling(bot, skip_updates=True)

if __name__ == '__main__':
    asyncio.run(main())