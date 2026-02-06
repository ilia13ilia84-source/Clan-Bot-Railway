#!/usr/bin/env python3
import os
import sys
import logging

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get("TOKEN", "8374994781:AAEyHplC_nJlyIeBCt3RJGHBfBOoT2r4Agw")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "5528629749"))

logger.info("🚀 Starting Clan Bot on Railway...")
logger.info(f"🤖 Bot: @xrocket_iran_fomo_bot")
logger.info(f"👑 Admin ID: {ADMIN_ID}")

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
    ConversationHandler
)

from database import db
from keyboards import main_menu, back_button

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    logger.info(f"User {user.id} started the bot")
    
    db.add_user(user.id, user.username, user.first_name)
    
    if user.id == ADMIN_ID:
        db.set_admin(user.id, True)
        logger.info(f"User {user.id} set as admin")
    
    await update.message.reply_text(
        f"سلام {user.first_name}! 👋\n\n"
        "🤖 به ربات مدیریت کلن خوش آمدید!\n"
        "🔧 میزبانی: Railway.app\n"
        "💾 ذخیره‌سازی: PostgreSQL\n"
        "🔄 24/7 آنلاین\n\n"
        "لطفاً از منوی زیر انتخاب کنید:",
        reply_markup=main_menu(user.id, db)
    )

async def main_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    await query.edit_message_text(
        "منوی اصلی:",
        reply_markup=main_menu(user_id, db)
    )

async def clan_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    stats = db.get_clan_stats()
    
    text = f"""📊 آمار کلن

👥 کاربران: {stats['total_users']}
🎮 اکانت‌ها: {stats['total_accounts']}
⚔️ کل اتک: {stats['total_attack']:,}
🛡️ کل دفاع: {stats['total_defense']:,}"""
    
    await query.edit_message_text(text, reply_markup=back_button())

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("لغو شد")
    user_id = query.from_user.id
    await query.edit_message_text(
        "منوی اصلی:",
        reply_markup=main_menu(user_id, db)
    )

def main():
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(main_menu_callback, pattern="^main_menu$"))
    application.add_handler(CallbackQueryHandler(clan_stats, pattern="^stats$"))
    application.add_handler(CallbackQueryHandler(cancel, pattern="^cancel$"))
    
    logger.info("🤖 Bot is starting...")
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
