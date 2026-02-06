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

logger.info("🚀 Starting Clan Bot...")

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
    admin_panel_menu, admin_users_menu, rankings_menu, format_num,
    admin_user_detail_menu, admin_user_accounts_menu, admin_account_detail_menu,
    confirm_delete_menu, confirm_toggle_admin_menu
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

async def my_accounts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """اکانت‌های کاربر"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    accounts = db.get_user_accounts(user_id)
    
    if not accounts:
        await query.edit_message_text(
            "📭 شما هنوز اکانتی ثبت نکرده‌اید!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📝 ثبت اولین اکانت", callback_data="register")],
                [InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]
            ])
        )
        return
    
    total_attack = sum(acc['attack'] for acc in accounts)
    total_defense = sum(acc['defense'] for acc in accounts)
    
    text = f"""📋 اکانت‌های شما

تعداد: {len(accounts)}/10
مجموع اتک: {format_num(total_attack)}
مجموع دفاع: {format_num(total_defense)}

👇 برای مدیریت انتخاب کنید:"""
    
    await query.edit_message_text(text, reply_markup=accounts_list_menu(accounts))

async def view_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مشاهده اکانت"""
    query = update.callback_query
    await query.answer()
    
    account_id = int(query.data.split("_")[1])
    account = db.get_account(account_id)
    
    if not account:
        await query.edit_message_text("❌ اکانت پیدا نشد!", reply_markup=back_button())
        return
    
    text = f"""🎮 مدیریت اکانت

نام: {account['game_name']}
اتک: {format_num(account['attack'])}
دفاع: {format_num(account['defense'])}

👇 گزینه مورد نظر:"""
    
    await query.edit_message_text(text, reply_markup=update_options_menu(account_id))

async def delete_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """منوی حذف"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    accounts = db.get_user_accounts(user_id)
    
    if not accounts:
        await query.edit_message_text("شما اکانتی ندارید!", reply_markup=main_menu(user_id, db))
        return
    
    text = f"""⚠️ حذف اکانت

شما {len(accounts)} اکانت دارید.
کدام را می‌خواهید حذف کنید؟"""
    
    await query.edit_message_text(text, reply_markup=delete_accounts_menu(accounts))

async def delete_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """حذف اکانت"""
    query = update.callback_query
    await query.answer()
    
    account_id = int(query.data.split("_")[1])
    
    if db.delete_account(account_id):
        user_id = query.from_user.id
        accounts = db.get_user_accounts(user_id)
        
        if accounts:
            await query.edit_message_text(
                "✅ اکانت حذف شد!",
                reply_markup=accounts_list_menu(accounts)
            )
        else:
            await query.edit_message_text(
                "✅ آخرین اکانت حذف شد!",
                reply_markup=main_menu(user_id, db)
            )
    else:
        await query.edit_message_text("❌ خطا در حذف!", reply_markup=back_button())

async def clan_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """آمار کلن"""
    query = update.callback_query
    await query.answer()
    
    stats = db.get_clan_stats()
    
    text = f"""📊 آمار کلن

👥 کاربران: {stats['total_users']}
🎮 اکانت‌ها: {stats['total_accounts']}
⚔️ کل اتک: {format_num(stats['total_attack'])}
🛡️ کل دفاع: {format_num(stats['total_defense'])}"""
    
    await query.edit_message_text(text, reply_markup=back_button())

async def show_rankings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """رتبه‌بندی"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "🏆 رتبه‌بندی:",
        reply_markup=rankings_menu()
    )

async def top_rankings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """۱۰ نفر اول"""
    query = update.callback_query
    await query.answer()
    
    limit = 10 if query.data == "top10" else 20
    rankings = db.get_rankings(limit)
    
    if not rankings:
        text = "📭 هنوز اکانتی ثبت نشده است."
    else:
        text = f"🏆 {limit} نفر برتر\n\n"
        for rank in rankings:
            text += f"{rank['rank']}. {rank['game_name']}\n"
            text += f"   👤 {rank['user_display']}\n"
            text += f"   ⚔️ {format_num(rank['attack'])} | 🛡️ {format_num(rank['defense'])}\n\n"
    
    await query.edit_message_text(text, reply_markup=back_button())

async def update_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """منوی تغییر"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    accounts = db.get_user_accounts(user_id)
    
    if not accounts:
        await query.edit_message_text("شما اکانتی ندارید!", reply_markup=main_menu(user_id, db))
        return
    
    text = "✏️ تغییر نیروها\n\nاکانت مورد نظر را انتخاب کنید:"
    await query.edit_message_text(text, reply_markup=accounts_list_menu(accounts))

async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ثبت اکانت"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if db.get_account_count(user_id) >= 10:
        await query.edit_message_text(
            "❌ حداکثر ۱۰ اکانت!",
            reply_markup=main_menu(user_id, db)
        )
        return ConversationHandler.END
    
    await query.edit_message_text(
        "اسم داخل بازی خود را وارد کنید:",
        reply_markup=cancel_button()
    )
    return GET_NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت نام"""
    game_name = update.message.text.strip()
    
    if len(game_name) < 2:
        await update.message.reply_text(
            "نام باید حداقل ۲ کاراکتر باشد!\nدوباره وارد کنید:",
            reply_markup=cancel_button()
        )
        return GET_NAME
    
    context.user_data['game_name'] = game_name
    await update.message.reply_text(
        f"نام: {game_name}\n\nنیروی اتک را وارد کنید (مثال: 1200000):",
        reply_markup=cancel_button()
    )
    return GET_ATTACK

async def get_attack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت اتک"""
    text = update.message.text.strip()
    
    if not text.isdigit():
        await update.message.reply_text(
            "فقط عدد وارد کنید!\nمثال: 1200000",
            reply_markup=cancel_button()
        )
        return GET_ATTACK
    
    attack = int(text)
    context.user_data['attack'] = attack
    await update.message.reply_text(
        f"اتک: {format_num(attack)}\n\nنیروی دفاع را وارد کنید (مثال: 400000):",
        reply_markup=cancel_button()
    )
    return GET_DEFENSE

async def get_defense(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت دفاع"""
    text = update.message.text.strip()
    
    if not text.isdigit():
        await update.message.reply_text(
            "فقط عدد وارد کنید!\nمثال: 400000",
            reply_markup=cancel_button()
        )
        return GET_DEFENSE
    
    defense = int(text)
    user_id = update.effective_user.id
    game_name = context.user_data['game_name']
    attack = context.user_data['attack']
    
    db.add_account(user_id, game_name, attack, defense)
    account_count = db.get_account_count(user_id)
    
    await update.message.reply_text(
        f"""✅ اکانت ثبت شد!

🎮 نام: {game_name}
⚔️ اتک: {format_num(attack)}
🛡️ دفاع: {format_num(defense)}

تعداد اکانت‌های شما: {account_count}""",
        reply_markup=main_menu(user_id, db)
    )
    
    context.user_data.clear()
    return ConversationHandler.END

async def start_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شروع تغییر"""
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split("_")
    update_type = parts[1]
    account_id = int(parts[2])
    
    context.user_data['update_type'] = update_type
    context.user_data['account_id'] = account_id
    
    if update_type == "attack":
        text = "مقدار جدید اتک را وارد کنید:"
    elif update_type == "defense":
        text = "مقدار جدید دفاع را وارد کنید:"
    else:
        text = "نام جدید را وارد کنید:"
    
    await query.edit_message_text(text, reply_markup=cancel_button())
    return UPDATE_VALUE

async def handle_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پردازش تغییر"""
    text = update.message.text.strip()
    update_type = context.user_data.get('update_type')
    account_id = context.user_data.get('account_id')
    user_id = update.effective_user.id
    
    success = False
    msg = ""
    
    if update_type == "attack":
        if text.isdigit():
            attack = int(text)
            success = db.update_account(account_id, attack=attack)
            msg = f"✅ اتک به {format_num(attack)} بروزرسانی شد!"
    elif update_type == "defense":
        if text.isdigit():
            defense = int(text)
            success = db.update_account(account_id, defense=defense)
            msg = f"✅ دفاع به {format_num(defense)} بروزرسانی شد!"
    elif update_type == "name":
        if len(text) >= 2:
            success = db.update_account(account_id, game_name=text)
            msg = f"✅ نام به {text} تغییر یافت!"
    
    if not success and update_type in ["attack", "defense"]:
        await update.message.reply_text("فقط عدد وارد کنید!", reply_markup=cancel_button())
        return UPDATE_VALUE
    elif not success:
        await update.message.reply_text("نام باید حداقل ۲ کاراکتر باشد!", reply_markup=cancel_button())
        return UPDATE_VALUE
    
    await update.message.reply_text(msg, reply_markup=main_menu(user_id, db))
    context.user_data.clear()
    return ConversationHandler.END

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پنل ادمین"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if not db.is_admin(user_id):
        await query.edit_message_text(
            "❌ شما ادمین نیستید!",
            reply_markup=main_menu(user_id, db)
        )
        return
    
    await query.edit_message_text(
        "🔐 پنل ادمین\n\nلطفاً گزینه مورد نظر را انتخاب کنید:",
        reply_markup=admin_panel_menu()
    )

async def admin_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش لیست کاربران برای ادمین"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if not db.is_admin(user_id):
        await query.edit_message_text(
            "❌ دسترسی غیرمجاز!",
            reply_markup=main_menu(user_id, db)
        )
        return
    
    # دریافت همه کاربران
    users = db.get_all_users()
    
    if not users:
        await query.edit_message_text(
            "📭 هیچ کاربری ثبت نشده است.",
            reply_markup=admin_panel_menu()
        )
        return
    
    # بررسی اگر صفحه‌بندی است
    page = 0
    if query.data.startswith("admin_users_page_"):
        page = int(query.data.split("_")[3])
    
    text = f"""
👥 مدیریت کاربران

📊 تعداد کل کاربران: {len(users)}
📄 صفحه {page + 1} از {(len(users) + 4) // 5}

👑 = ادمین
👇 کاربر مورد نظر را انتخاب کنید:
"""
    
    await query.edit_message_text(
        text,
        reply_markup=admin_users_menu(users, page)
    )

async def admin_user_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش جزئیات یک کاربر"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if not db.is_admin(user_id):
        return
    
    target_user_id = int(query.data.split("_")[3])
    
    # دریافت اطلاعات کاربر
    users = db.get_all_users()
    target_user = None
    
    for user in users:
        if user['user_id'] == target_user_id:
            target_user = user
            break
    
    if not target_user:
        await query.edit_message_text(
            "❌ کاربر پیدا نشد!",
            reply_markup=admin_users_menu(users)
        )
        return
    
    username = f"@{target_user['username']}" if target_user['username'] else target_user['first_name']
    
    text = f"""
👤 جزئیات کاربر

🆔 آیدی: {target_user_id}
👤 نام: {username}
👑 وضعیت: {"ادمین ✅" if target_user['is_admin'] else "کاربر عادی"}
🎮 تعداد اکانت‌ها: {target_user['account_count']}

👇 عملیات مورد نظر را انتخاب کنید:
"""
    
    await query.edit_message_text(
        text,
        reply_markup=admin_user_detail_menu(target_user_id)
    )

async def admin_view_accounts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مشاهده اکانت‌های کاربر توسط ادمین"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if not db.is_admin(user_id):
        return
    
    target_user_id = int(query.data.split("_")[3])
    
    # دریافت اکانت‌های کاربر
    accounts = db.get_user_accounts(target_user_id)
    
    if not accounts:
        await query.edit_message_text(
            f"📭 کاربر {target_user_id} هیچ اکانت فعالی ندارد.",
            reply_markup=admin_user_detail_menu(target_user_id)
        )
        return
    
    total_attack = sum(acc['attack'] for acc in accounts)
    total_defense = sum(acc['defense'] for acc in accounts)
    
    text = f"""
🎮 اکانت‌های کاربر

👤 آیدی کاربر: {target_user_id}
📊 تعداد اکانت‌ها: {len(accounts)}
⚔️ مجموع اتک: {format_num(total_attack)}
🛡️ مجموع دفاع: {format_num(total_defense)}

👇 برای مدیریت انتخاب کنید:
"""
    
    await query.edit_message_text(
        text,
        reply_markup=admin_user_accounts_menu(accounts, target_user_id)
    )

async def admin_account_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """جزئیات یک اکانت خاص"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if not db.is_admin(user_id):
        return
    
    account_id = int(query.data.split("_")[3])
    
    # دریافت اطلاعات اکانت
    account = db.get_account(account_id)
    
    if not account:
        await query.edit_message_text(
            "❌ اکانت پیدا نشد!",
            reply_markup=back_button()
        )
        return
    
    text = f"""
🎮 جزئیات اکانت

🆔 آیدی اکانت: {account_id}
👤 آیدی کاربر: {account['user_id']}
📛 نام: {account['game_name']}
⚔️ اتک: {format_num(account['attack'])}
🛡️ دفاع: {format_num(account['defense'])}
📊 مجموع: {format_num(account['attack'] + account['defense'])}

👇 عملیات مورد نظر را انتخاب کنید:
"""
    
    await query.edit_message_text(
        text,
        reply_markup=admin_account_detail_menu(account_id)
    )

async def admin_delete_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """حذف یک اکانت توسط ادمین"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if not db.is_admin(user_id):
        return
    
    account_id = int(query.data.split("_")[3])
    
    account = db.get_account(account_id)
    
    if not account:
        await query.edit_message_text(
            "❌ اکانت پیدا نشد!",
            reply_markup=back_button()
        )
        return
    
    text = f"""
⚠️ تایید حذف اکانت

🎮 نام اکانت: {account['game_name']}
👤 آیدی کاربر: {account['user_id']}
⚔️ اتک: {format_num(account['attack'])}
🛡️ دفاع: {format_num(account['defense'])}

❌ این عمل غیرقابل بازگشت است!

آیا مطمئن هستید؟
"""
    
    await query.edit_message_text(
        text,
        reply_markup=confirm_delete_menu(account_id, "account")
    )

async def confirm_delete_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تایید نهایی حذف اکانت"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if not db.is_admin(user_id):
        return
    
    account_id = int(query.data.split("_")[3])
    
    account = db.get_account(account_id)
    
    if db.delete_account(account_id):
        text = f"""
✅ اکانت حذف شد!

🎮 نام: {account['game_name']}
👤 آیدی کاربر: {account['user_id']}
"""
    else:
        text = "❌ خطا در حذف اکانت!"
    
    await query.edit_message_text(
        text,
        reply_markup=admin_panel_menu()
    )

async def admin_delete_all_accounts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """حذف همه اکانت‌های یک کاربر"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if not db.is_admin(user_id):
        return
    
    target_user_id = int(query.data.split("_")[4])
    
    # دریافت اطلاعات کاربر
    users = db.get_all_users()
    target_user = None
    
    for user in users:
        if user['user_id'] == target_user_id:
            target_user = user
            break
    
    if not target_user:
        await query.edit_message_text(
            "❌ کاربر پیدا نشد!",
            reply_markup=admin_users_menu(users)
        )
        return
    
    username = f"@{target_user['username']}" if target_user['username'] else target_user['first_name']
    
    text = f"""
⚠️ تایید حذف همه اکانت‌ها

👤 کاربر: {username}
🆔 آیدی: {target_user_id}
🎮 تعداد اکانت‌ها: {target_user['account_count']}

❌ تمام اکانت‌های این کاربر حذف خواهند شد!
این عمل غیرقابل بازگشت است!

آیا مطمئن هستید؟
"""
    
    await query.edit_message_text(
        text,
        reply_markup=confirm_delete_menu(target_user_id, "user_accounts")
    )

async def confirm_delete_all_accounts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تایید نهایی حذف همه اکانت‌ها"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if not db.is_admin(user_id):
        return
    
    target_user_id = int(query.data.split("_")[3])
    
    # دریافت اکانت‌های کاربر
    accounts = db.get_user_accounts(target_user_id)
    deleted_count = 0
    
    for acc in accounts:
        if db.delete_account(acc['id']):
            deleted_count += 1
    
    text = f"""
✅ {deleted_count} اکانت حذف شد!

👤 آیدی کاربر: {target_user_id}
🗑️ تعداد اکانت‌های حذف شده: {deleted_count}
"""
    
    await query.edit_message_text(
        text,
        reply_markup=admin_panel_menu()
    )

async def admin_toggle_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تغییر وضعیت ادمین کاربر"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if not db.is_admin(user_id):
        return
    
    target_user_id = int(query.data.split("_")[3])
    
    # بررسی وضعیت فعلی کاربر
    current_status = db.is_admin(target_user_id)
    
    text = f"""
⚠️ تغییر وضعیت ادمین

👤 آیدی کاربر: {target_user_id}
👑 وضعیت فعلی: {"ادمین ✅" if current_status else "کاربر عادی"}
🔄 وضعیت جدید: {"کاربر عادی" if current_status else "ادمین"}

آیا مطمئن هستید؟
"""
    
    await query.edit_message_text(
        text,
        reply_markup=confirm_toggle_admin_menu(target_user_id)
    )

async def confirm_toggle_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تایید تغییر وضعیت ادمین"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if not db.is_admin(user_id):
        return
    
    target_user_id = int(query.data.split("_")[3])
    
    # تغییر وضعیت ادمین
    current_status = db.is_admin(target_user_id)
    new_status = not current_status
    
    if db.set_admin(target_user_id, new_status):
        text = f"""
✅ وضعیت ادمین تغییر یافت!

👤 آیدی کاربر: {target_user_id}
👑 وضعیت جدید: {"ادمین ✅" if new_status else "کاربر عادی"}
"""
    else:
        text = "❌ خطا در تغییر وضعیت ادمین!"
    
    await query.edit_message_text(
        text,
        reply_markup=admin_panel_menu()
    )

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """آمار پیشرفته برای ادمین"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if not db.is_admin(user_id):
        await query.edit_message_text(
            "❌ دسترسی غیرمجاز!",
            reply_markup=main_menu(user_id, db)
        )
        return
    
    stats = db.get_clan_stats()
    users = db.get_all_users()
    
    # محاسبات پیشرفته
    total_users = len(users)
    users_with_accounts = sum(1 for u in users if u['account_count'] > 0)
    users_without_accounts = total_users - users_with_accounts
    
    admins_count = sum(1 for u in users if u['is_admin'])
    regular_users = total_users - admins_count
    
    if stats['total_accounts'] > 0:
        avg_attack = stats['total_attack'] // stats['total_accounts']
        avg_defense = stats['total_defense'] // stats['total_accounts']
        avg_total = avg_attack + avg_defense
    else:
        avg_attack = avg_defense = avg_total = 0
    
    text = f"""
📈 آمار پیشرفته کلن

👥 **کاربران:**
• کل کاربران: {total_users}
• دارای اکانت: {users_with_accounts}
• بدون اکانت: {users_without_accounts}
• ادمین‌ها: {admins_count}
• کاربران عادی: {regular_users}

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
• میانگین کل: {format_num(avg_total)}

💾 **دیتابیس:**
• PostgreSQL Railway
• 24/7 آنلاین
"""
    
    await query.edit_message_text(
        text,
        reply_markup=admin_panel_menu()
    )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """لغو"""
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
    """لغو متن"""
    user_id = update.effective_user.id
    context.user_data.clear()
    await update.message.reply_text(
        "منوی اصلی:",
        reply_markup=main_menu(user_id, db)
    )
    return ConversationHandler.END

def main():
    """اصلی"""
    logger.info("Creating application...")
    
    app = Application.builder().token(TOKEN).build()
    
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
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(register_conv)
    app.add_handler(update_conv)
    
    app.add_handler(CallbackQueryHandler(main_menu_callback, pattern="^main_menu$"))
    app.add_handler(CallbackQueryHandler(my_accounts, pattern="^my_accounts$"))
    app.add_handler(CallbackQueryHandler(view_account, pattern=r"^view_\d+$"))
    app.add_handler(CallbackQueryHandler(delete_menu, pattern="^delete_menu$"))
    app.add_handler(CallbackQueryHandler(delete_account, pattern=r"^delete_\d+$"))
    app.add_handler(CallbackQueryHandler(clan_stats, pattern="^stats$"))
    app.add_handler(CallbackQueryHandler(show_rankings, pattern="^rankings$"))
    app.add_handler(CallbackQueryHandler(top_rankings, pattern="^top10$|^top20$"))
    app.add_handler(CallbackQueryHandler(update_menu, pattern="^update_menu$"))
    app.add_handler(CallbackQueryHandler(admin_panel, pattern="^admin_panel$"))
    app.add_handler(CallbackQueryHandler(admin_stats, pattern="^admin_stats$"))
    
    # هندلرهای مدیریت ادمین
    app.add_handler(CallbackQueryHandler(admin_users, pattern="^admin_users$"))
    app.add_handler(CallbackQueryHandler(admin_users, pattern=r"^admin_users_page_\d+$"))
    app.add_handler(CallbackQueryHandler(admin_user_detail, pattern=r"^admin_user_detail_\d+$"))
    app.add_handler(CallbackQueryHandler(admin_view_accounts, pattern=r"^admin_view_accounts_\d+$"))
    app.add_handler(CallbackQueryHandler(admin_account_detail, pattern=r"^admin_account_detail_\d+$"))
    app.add_handler(CallbackQueryHandler(admin_delete_account, pattern=r"^admin_delete_account_\d+$"))
    app.add_handler(CallbackQueryHandler(admin_delete_all_accounts, pattern=r"^admin_delete_all_accounts_\d+$"))
    app.add_handler(CallbackQueryHandler(admin_toggle_admin, pattern=r"^admin_toggle_admin_\d+$"))
    app.add_handler(CallbackQueryHandler(confirm_delete_account, pattern=r"^confirm_delete_account_\d+$"))
    app.add_handler(CallbackQueryHandler(confirm_delete_all_accounts, pattern=r"^confirm_delete_user_accounts_\d+$"))
    app.add_handler(CallbackQueryHandler(confirm_toggle_admin, pattern=r"^confirm_toggle_admin_\d+$"))
    
    app.add_handler(CallbackQueryHandler(cancel, pattern="^cancel$"))
    app.add_handler(CommandHandler("cancel", cancel_text))
    
    logger.info("🤖 Bot is starting...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
