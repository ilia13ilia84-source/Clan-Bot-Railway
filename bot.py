#!/usr/bin/env python3
import os
import sys
import logging
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get("TOKEN", "8374994781:AAEyHplC_nJlyIeBCt3RJGHBfBOoT2r4Agw")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "5528629749"))

logger.info("🚀 Starting Clan Bot...")
logger.info(f"🤖 Bot Token: {TOKEN[:10]}...")
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
from keyboards import (
    main_menu, back_button, cancel_button,
    accounts_list_menu, delete_accounts_menu, update_options_menu,
    admin_panel_menu, admin_users_menu, admin_user_accounts_menu,
    rankings_menu, format_num
)

GET_NAME, GET_ATTACK, GET_DEFENSE = range(3)
UPDATE_VALUE = 3

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شروع ربات"""
    user = update.effective_user
    logger.info(f"User {user.id} started the bot")
    
    db.add_user(user.id, user.username, user.first_name)
    
    if user.id == ADMIN_ID:
        db.set_admin(user.id, True)
        logger.info(f"User {user.id} set as admin")
    
    welcome_text = f"""
سلام {user.first_name}!

به ربات مدیریت کلن xRocket خوش آمدید.
لطفاً از منوی زیر انتخاب کنید:
"""
    
    await update.message.reply_text(welcome_text, reply_markup=main_menu(user.id, db))

async def main_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بازگشت به منوی اصلی"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    await query.edit_message_text(
        "منوی اصلی:",
        reply_markup=main_menu(user_id, db)
    )

async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شروع ثبت اکانت"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if db.get_account_count(user_id) >= 10:
        await query.edit_message_text(
            "❌ حد مجاز: حداکثر ۱۰ اکانت می‌توانید ثبت کنید!",
            reply_markup=main_menu(user_id, db)
        )
        return ConversationHandler.END
    
    await query.edit_message_text(
        "🎮 **مرحله ۱ از ۳**\n\nاسم داخل بازی خود را وارد کنید:",
        reply_markup=cancel_button()
    )
    return GET_NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت نام بازی"""
    game_name = update.message.text.strip()
    
    if len(game_name) < 2:
        await update.message.reply_text(
            "❌ نام باید حداقل ۲ کاراکتر باشد!\nلطفاً دوباره وارد کنید:",
            reply_markup=cancel_button()
        )
        return GET_NAME
    
    context.user_data['game_name'] = game_name
    await update.message.reply_text(
        f"✅ **نام ثبت شد:** {game_name}\n\n"
        f"🎮 **مرحله ۲ از ۳**\n"
        f"نیروی اتک را وارد کنید (عدد انگلیسی):\n"
        f"مثال: 1200000",
        reply_markup=cancel_button()
    )
    return GET_ATTACK

async def get_attack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت نیروی اتک"""
    text = update.message.text.strip().replace(',', '')
    
    if not text.isdigit():
        await update.message.reply_text(
            "❌ فقط عدد انگلیسی وارد کنید!\n"
            "مثال: 1200000 یا 1,200,000",
            reply_markup=cancel_button()
        )
        return GET_ATTACK
    
    attack = int(text)
    if attack < 0:
        await update.message.reply_text(
            "❌ عدد نمی‌تواند منفی باشد!\nلطفاً عدد صحیح وارد کنید:",
            reply_markup=cancel_button()
        )
        return GET_ATTACK
    
    context.user_data['attack'] = attack
    await update.message.reply_text(
        f"✅ **اتک ثبت شد:** {format_num(attack)}\n\n"
        f"🎮 **مرحله ۳ از ۳**\n"
        f"نیروی دفاع را وارد کنید (عدد انگلیسی):\n"
        f"مثال: 500000",
        reply_markup=cancel_button()
    )
    return GET_DEFENSE

async def get_defense(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت نیروی دفاع"""
    text = update.message.text.strip().replace(',', '')
    
    if not text.isdigit():
        await update.message.reply_text(
            "❌ فقط عدد انگلیسی وارد کنید!\n"
            "مثال: 500000 یا 500,000",
            reply_markup=cancel_button()
        )
        return GET_DEFENSE
    
    defense = int(text)
    if defense < 0:
        await update.message.reply_text(
            "❌ عدد نمی‌تواند منفی باشد!\nلطفاً عدد صحیح وارد کنید:",
            reply_markup=cancel_button()
        )
        return GET_DEFENSE
    
    user_id = update.effective_user.id
    game_name = context.user_data['game_name']
    attack = context.user_data['attack']
    
    account_id = db.add_account(user_id, game_name, attack, defense)
    
    if account_id:
        account_count = db.get_account_count(user_id)
        
        success_text = f"""
✅ **اکانت با موفقیت ثبت شد!**

📋 **مشخصات اکانت:**
🎮 نام: {game_name}
⚔️ اتک: {format_num(attack)}
🛡️ دفاع: {format_num(defense)}
📊 مجموع نیرو: {format_num(attack + defense)}

📈 **وضعیت حساب شما:**
👤 تعداد اکانت‌ها: {account_count}/10
➕ برای افزودن اکانت جدید از منوی اصلی استفاده کنید.
"""
        await update.message.reply_text(
            success_text,
            reply_markup=main_menu(user_id, db)
        )
    else:
        await update.message.reply_text(
            "❌ خطا در ثبت اکانت!\nلطفاً دوباره تلاش کنید.",
            reply_markup=main_menu(user_id, db)
        )
    
    context.user_data.clear()
    return ConversationHandler.END

async def my_accounts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش اکانت‌های کاربر"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    accounts = db.get_user_accounts(user_id)
    
    if not accounts:
        await query.edit_message_text(
            "📭 شما هنوز اکانتی ثبت نکرده‌اید!\n\n"
            "برای ثبت اولین اکانت، دکمه زیر را انتخاب کنید:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📝 ثبت اولین اکانت", callback_data="register")],
                [InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]
            ])
        )
        return
    
    total_attack = sum(acc['attack'] for acc in accounts)
    total_defense = sum(acc['defense'] for acc in accounts)
    total_power = total_attack + total_defense
    
    accounts_text = f"""
📋 **اکانت‌های شما**

👤 تعداد اکانت‌ها: {len(accounts)}/10
⚔️ مجموع اتک: {format_num(total_attack)}
🛡️ مجموع دفاع: {format_num(total_defense)}
💪 مجموع نیرو: {format_num(total_power)}

👇 برای مشاهده جزئیات یا مدیریت، اکانت مورد نظر را انتخاب کنید:
"""
    
    await query.edit_message_text(accounts_text, reply_markup=accounts_list_menu(accounts))

async def view_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش جزئیات یک اکانت"""
    query = update.callback_query
    await query.answer()
    
    account_id = int(query.data.split("_")[1])
    account = db.get_account(account_id)
    
    if not account:
        await query.edit_message_text(
            "❌ اکانت پیدا نشد!",
            reply_markup=back_button()
        )
        return
    
    account_text = f"""
🎮 **مدیریت اکانت**

📛 نام: {account['game_name']}
⚔️ اتک: {format_num(account['attack'])}
🛡️ دفاع: {format_num(account['defense'])}
💪 مجموع: {format_num(account['attack'] + account['defense'])}

👇 گزینه مورد نظر را انتخاب کنید:
"""
    
    await query.edit_message_text(account_text, reply_markup=update_options_menu(account_id))

async def delete_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """منوی حذف اکانت"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    accounts = db.get_user_accounts(user_id)
    
    if not accounts:
        await query.edit_message_text(
            "شما اکانتی ندارید!",
            reply_markup=main_menu(user_id, db)
        )
        return
    
    warning_text = f"""
⚠️ **حذف اکانت**

شما {len(accounts)} اکانت دارید.
این عمل غیرقابل بازگشت است!

👇 اکانت مورد نظر برای حذف را انتخاب کنید:
"""
    
    await query.edit_message_text(warning_text, reply_markup=delete_accounts_menu(accounts))

async def delete_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """حذف یک اکانت"""
    query = update.callback_query
    await query.answer()
    
    account_id = int(query.data.split("_")[1])
    
    if db.delete_account(account_id):
        user_id = query.from_user.id
        accounts = db.get_user_accounts(user_id)
        
        if accounts:
            await query.edit_message_text(
                "✅ اکانت با موفقیت حذف شد!",
                reply_markup=accounts_list_menu(accounts)
            )
        else:
            await query.edit_message_text(
                "✅ آخرین اکانت شما حذف شد!\n\n"
                "برای ثبت اکانت جدید از منوی اصلی استفاده کنید.",
                reply_markup=main_menu(user_id, db)
            )
    else:
        await query.edit_message_text(
            "❌ خطا در حذف اکانت!",
            reply_markup=back_button()
        )

async def clan_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش آمار کلن"""
    query = update.callback_query
    await query.answer()
    
    stats = db.get_clan_stats()
    
    if stats['total_accounts'] > 0:
        avg_attack = stats['total_attack'] // stats['total_accounts']
        avg_defense = stats['total_defense'] // stats['total_accounts']
        avg_total = avg_attack + avg_defense
    else:
        avg_attack = avg_defense = avg_total = 0
    
    stats_text = f"""
📊 **آمار کل کلن**

👥 تعداد کاربران: {stats['total_users']}
🎮 تعداد اکانت‌ها: {stats['total_accounts']}
⚔️ مجموع اتک: {format_num(stats['total_attack'])}
🛡️ مجموع دفاع: {format_num(stats['total_defense'])}
💪 مجموع کل: {format_num(stats['total_attack'] + stats['total_defense'])}

📈 **میانگین‌ها:**
⚔️ میانگین اتک: {format_num(avg_attack)}
🛡️ میانگین دفاع: {format_num(avg_defense)}
💪 میانگین کل: {format_num(avg_total)}
"""
    
    await query.edit_message_text(stats_text, reply_markup=back_button())

async def show_rankings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش منوی رتبه‌بندی"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "🏆 **رتبه‌بندی کلن**\n\n"
        "براساس مجموع نیرو (اتک + دفاع)\n"
        "👇 گزینه مورد نظر را انتخاب کنید:",
        reply_markup=rankings_menu()
    )

async def top_rankings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش رتبه‌بندی"""
    query = update.callback_query
    await query.answer()
    
    limit = 10 if query.data == "top10" else 20
    rankings = db.get_rankings(limit)
    
    if not rankings:
        await query.edit_message_text(
            "📭 هنوز اکانتی ثبت نشده است!\n"
            "اولین نفر باشید که اکانت ثبت می‌کند.",
            reply_markup=back_button()
        )
        return
    
    ranking_text = f"🏆 **{limit} نفر برتر کلن**\n\n"
    
    for rank in rankings:
        medal = "🥇" if rank['rank'] == 1 else "🥈" if rank['rank'] == 2 else "🥉" if rank['rank'] == 3 else f"{rank['rank']}."
        
        ranking_text += f"{medal} **{rank['game_name']}**\n"
        ranking_text += f"   👤 {rank['user_display']} (آیدی: {rank['user_id']})\n"
        ranking_text += f"   ⚔️ {format_num(rank['attack'])} | 🛡️ {format_num(rank['defense'])}"
        ranking_text += f" | 💪 {format_num(rank['attack'] + rank['defense'])}\n\n"
    
    await query.edit_message_text(ranking_text, reply_markup=back_button())

async def update_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """منوی تغییر نیروها"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    accounts = db.get_user_accounts(user_id)
    
    if not accounts:
        await query.edit_message_text(
            "شما اکانتی ندارید!",
            reply_markup=main_menu(user_id, db)
        )
        return
    
    await query.edit_message_text(
        "✏️ **تغییر اطلاعات اکانت**\n\n"
        "👇 اکانت مورد نظر را انتخاب کنید:",
        reply_markup=accounts_list_menu(accounts)
    )

async def start_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شروع فرآیند تغییر اطلاعات"""
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split("_")
    update_type = parts[1]
    account_id = int(parts[2])
    
    context.user_data['update_type'] = update_type
    context.user_data['account_id'] = account_id
    
    account = db.get_account(account_id)
    if not account:
        await query.edit_message_text(
            "❌ اکانت پیدا نشد!",
            reply_markup=back_button()
        )
        return ConversationHandler.END
    
    if update_type == "attack":
        prompt = f"✏️ **تغییر اتک**\n\nاکانت: {account['game_name']}\n\nمقدار جدید اتک را وارد کنید:"
    elif update_type == "defense":
        prompt = f"✏️ **تغییر دفاع**\n\nاکانت: {account['game_name']}\n\nمقدار جدید دفاع را وارد کنید:"
    else:  # name
        prompt = f"✏️ **تغییر نام**\n\nاکانت: {account['game_name']}\n\nنام جدید را وارد کنید:"
    
    await query.edit_message_text(prompt, reply_markup=cancel_button())
    return UPDATE_VALUE

async def handle_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پردازش تغییر اطلاعات"""
    text = update.message.text.strip()
    update_type = context.user_data.get('update_type')
    account_id = context.user_data.get('account_id')
    user_id = update.effective_user.id
    
    success = False
    msg = ""
    
    if update_type == "attack":
        text = text.replace(',', '')
        if not text.isdigit():
            await update.message.reply_text(
                "❌ فقط عدد انگلیسی وارد کنید!",
                reply_markup=cancel_button()
            )
            return UPDATE_VALUE
        
        attack = int(text)
        if attack < 0 or attack > 1000000000:
            await update.message.reply_text(
                "❌ عدد نامعتبر! لطفاً عددی بین 0 تا 1,000,000,000 وارد کنید:",
                reply_markup=cancel_button()
            )
            return UPDATE_VALUE
        
        success = db.update_account(account_id, attack=attack)
        msg = f"✅ اتک به {format_num(attack)} بروزرسانی شد!"
    
    elif update_type == "defense":
        text = text.replace(',', '')
        if not text.isdigit():
            await update.message.reply_text(
                "❌ فقط عدد انگلیسی وارد کنید!",
                reply_markup=cancel_button()
            )
            return UPDATE_VALUE
        
        defense = int(text)
        if defense < 0 or defense > 1000000000:
            await update.message.reply_text(
                "❌ عدد نامعتبر! لطفاً عددی بین 0 تا 1,000,000,000 وارد کنید:",
                reply_markup=cancel_button()
            )
            return UPDATE_VALUE
        
        success = db.update_account(account_id, defense=defense)
        msg = f"✅ دفاع به {format_num(defense)} بروزرسانی شد!"
    
    else:  # name
        if len(text) < 2:
            await update.message.reply_text(
                "❌ نام باید حداقل ۲ کاراکتر باشد!",
                reply_markup=cancel_button()
            )
            return UPDATE_VALUE
        
        if len(text) > 50:
            await update.message.reply_text(
                "❌ نام نباید بیشتر از ۵۰ کاراکتر باشد!",
                reply_markup=cancel_button()
            )
            return UPDATE_VALUE
        
        success = db.update_account(account_id, game_name=text)
        msg = f"✅ نام به {text} تغییر یافت!"
    
    if success:
        await update.message.reply_text(msg, reply_markup=main_menu(user_id, db))
    else:
        await update.message.reply_text(
            "❌ خطا در بروزرسانی!",
            reply_markup=main_menu(user_id, db)
        )
    
    context.user_data.clear()
    return ConversationHandler.END

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش پنل ادمین"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if not db.is_admin(user_id):
        await query.edit_message_text(
            "❌ دسترسی غیرمجاز!\nشما ادمین نیستید.",
            reply_markup=main_menu(user_id, db)
        )
        return
    
    username = f"@{query.from_user.username}" if query.from_user.username else query.from_user.first_name
    
    admin_text = f"""
🔐 **پنل مدیریت ادمین**

👑 ادمین: {username}
🆔 آیدی: {user_id}

👇 گزینه مورد نظر را انتخاب کنید:
"""
    
    await query.edit_message_text(admin_text, reply_markup=admin_panel_menu())

async def admin_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت کاربران توسط ادمین"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if not db.is_admin(user_id):
        return
    
    users = db.get_all_users()
    
    if not users:
        await query.edit_message_text(
            "📭 هیچ کاربری ثبت نشده است.",
            reply_markup=back_button()
        )
        return
    
    page = 0
    if query.data.startswith("admin_page_"):
        page = int(query.data.split("_")[2])
    
    total_pages = (len(users) + 4) // 5
    
    users_text = f"""
👥 **مدیریت کاربران**

📊 تعداد کل کاربران: {len(users)}
📄 صفحه {page + 1} از {total_pages}

👇 برای مشاهده جزئیات یا مدیریت، کاربر را انتخاب کنید:
"""
    
    await query.edit_message_text(users_text, reply_markup=admin_users_menu(users, page))

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """آمار پیشرفته برای ادمین"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if not db.is_admin(user_id):
        return
    
    stats = db.get_clan_stats()
    users = db.get_all_users()
    
    users_with_acc = sum(1 for u in users if u['account_count'] > 0)
    
    if stats['total_accounts'] > 0:
        avg_attack = stats['total_attack'] // stats['total_accounts']
        avg_defense = stats['total_defense'] // stats['total_accounts']
    else:
        avg_attack = avg_defense = 0
    
    admin_stats_text = f"""
📈 **آمار پیشرفته کلن**

👥 **کاربران:**
• کل کاربران: {len(users)}
• دارای اکانت: {users_with_acc}
• بدون اکانت: {len(users) - users_with_acc}

🎮 **اکانت‌ها:**
• کل اکانت‌ها: {stats['total_accounts']}
• کاربران فعال: {stats['total_users']}

⚔️ **نیروها:**
• کل اتک: {format_num(stats['total_attack'])}
• کل دفاع: {format_num(stats['total_defense'])}
• کل نیرو: {format_num(stats['total_attack'] + stats['total_defense'])}

📊 **میانگین‌ها:**
• میانگین اتک: {format_num(avg_attack)}
• میانگین دفاع: {format_num(avg_defense)}
"""
    
    await query.edit_message_text(admin_stats_text, reply_markup=back_button())

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """لغو عملیات"""
    query = update.callback_query
    await query.answer("لغو شد")
    
    user_id = query.from_user.id
    context.user_data.clear()
    await query.edit_message_text(
        "منوی اصلی:",
        reply_markup=main_menu(user_id, db)
    )
    return ConversationHandler.END

async def cancel_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """لغو عملیات از طریق متن"""
    user_id = update.effective_user.id
    context.user_data.clear()
    await update.message.reply_text(
        "منوی اصلی:",
        reply_markup=main_menu(user_id, db)
    )
    return ConversationHandler.END

def main():
    """تابع اصلی اجرای ربات"""
    logger.info("Creating application...")
    
    application = Application.builder().token(TOKEN).build()
    
    # ثبت ConversationHandler برای ثبت اکانت
    register_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(register, pattern="^register$"),
            CallbackQueryHandler(register, pattern="^add_account$")
        ],
        states={
            GET_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            GET_ATTACK: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_attack)],
            GET_DEFENSE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_defense)]
        },
        fallbacks=[
            CallbackQueryHandler(cancel, pattern="^cancel$"),
            CommandHandler("cancel", cancel_text)
        ]
    )
    
    # ثبت ConversationHandler برای تغییر اطلاعات
    update_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_update, pattern=r"^up_(attack|defense|name)_\d+$")
        ],
        states={
            UPDATE_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_update)]
        },
        fallbacks=[
            CallbackQueryHandler(cancel, pattern="^cancel$"),
            CommandHandler("cancel", cancel_text)
        ]
    )
    
    # افزودن هندلرهای اصلی
    application.add_handler(CommandHandler("start", start))
    application.add_handler(register_conv)
    application.add_handler(update_conv)
    
    # افزودن هندلرهای callback
    application.add_handler(CallbackQueryHandler(main_menu_callback, pattern="^main_menu$"))
    application.add_handler(CallbackQueryHandler(my_accounts, pattern="^my_accounts$"))
    application.add_handler(CallbackQueryHandler(clan_stats, pattern="^stats$"))
    application.add_handler(CallbackQueryHandler(show_rankings, pattern="^rankings$"))
    application.add_handler(CallbackQueryHandler(top_rankings, pattern="^top10$|^top20$"))
    application.add_handler(CallbackQueryHandler(update_menu, pattern="^update_menu$"))
    application.add_handler(CallbackQueryHandler(delete_menu, pattern="^delete_menu$"))
    application.add_handler(CallbackQueryHandler(admin_panel, pattern="^admin_panel$"))
    application.add_handler(CallbackQueryHandler(admin_users, pattern="^admin_users$"))
    application.add_handler(CallbackQueryHandler(admin_stats, pattern="^admin_stats$"))
    application.add_handler(CallbackQueryHandler(cancel, pattern="^cancel$"))
    
    # هندلرهای دینامیک
    application.add_handler(CallbackQueryHandler(view_account, pattern=r"^view_\d+$"))
    application.add_handler(CallbackQueryHandler(delete_account, pattern=r"^delete_\d+$"))
    application.add_handler(CallbackQueryHandler(admin_users, pattern=r"^admin_page_\d+$"))
    
    application.add_handler(CommandHandler("cancel", cancel_text))
    
    logger.info("🤖 Bot is starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == "__main__":
    main()
