# working.py
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

logging.basicConfig(level=logging.INFO)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎯 Бот работает!")


def main():
    TOKEN = "8364693331:AAEBGkTN9hqNM1una6glh31Scgwy4CYQeQE"

    print(f"Запуск с токеном: {TOKEN[:15]}...")

    try:
        app = Application.builder().token(TOKEN).build()
        app.add_handler(CommandHandler("start", start))

        print("✅ Бот запускается...")
        app.run_polling()
    except Exception as e:
        print(f"❌ Ошибка: {type(e).__name__}")
        print(f"Подробности: {e}")


if __name__ == "__main__":
    main()
