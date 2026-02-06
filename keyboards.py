from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def main_menu(user_id, db):
    account_count = db.get_account_count(user_id)
    is_admin = db.is_admin(user_id)
    
    keyboard = []
    
    if account_count == 0:
        keyboard.append([InlineKeyboardButton("📝 ثبت اولین اکانت", callback_data="register")])
    else:
        keyboard.append([
            InlineKeyboardButton(f"👤 اکانت‌های من ({account_count})", callback_data="my_accounts"),
            InlineKeyboardButton("✏️ تغییر نیرو", callback_data="update_menu")
        ])
    
    if account_count > 0 and account_count < 10:
        keyboard.append([InlineKeyboardButton("➕ اکانت جدید", callback_data="add_account")])
    
    keyboard.append([
        InlineKeyboardButton("📊 آمار کلن", callback_data="stats"),
        InlineKeyboardButton("🏆 رتبه‌بندی", callback_data="rankings")
    ])
    
    if is_admin:
        keyboard.append([InlineKeyboardButton("🔐 پنل ادمین", callback_data="admin_panel")])
    
    return InlineKeyboardMarkup(keyboard)

def back_button():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]])

def cancel_button():
    return InlineKeyboardMarkup([[InlineKeyboardButton("❌ لغو", callback_data="cancel")]])
