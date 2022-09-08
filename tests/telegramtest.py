import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler
import json

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Welkom bij Tram22Bot. Gebruik /subscribe om je in te schrijven voor onze message list.")
    await application.bot.send_message(chat_id=731710274, text="Test!")

if __name__ == '__main__':
    application = ApplicationBuilder().token('5495263200:AAFsvsOcFkt0MAgwKgzu6umg6MKlHfwfEX0').build()
    
    start_handler = CommandHandler('start', start)
    application.add_handler(start_handler)
    
    
    application.run_polling()