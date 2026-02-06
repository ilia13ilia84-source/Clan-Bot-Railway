from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def format_num(num):
    """قالب‌بندی اعداد با کاما"""
    try:
        return f"{int(num):,}"
    except:
        return "0"

def main_menu(user_id, db):
    """منوی اصلی"""
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
    """دکمه بازگشت"""
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]])

def cancel_button():
    """دکمه لغو"""
    return InlineKeyboardMarkup([[InlineKeyboardButton("❌ لغو", callback_data="cancel")]])

def accounts_list_menu(accounts):
    """منوی لیست اکانت‌ها"""
    keyboard = []
    
    for acc in accounts:
        btn_text = f"🎮 {acc['game_name']} (⚔{format_num(acc['attack'])} 🛡{format_num(acc['defense'])})"
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"view_{acc['id']}")])
    
    keyboard.append([
        InlineKeyboardButton("🗑️ حذف اکانت", callback_data="delete_menu"),
        InlineKeyboardButton("➕ اکانت جدید", callback_data="add_account")
    ])
    keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")])
    
    return InlineKeyboardMarkup(keyboard)

def delete_accounts_menu(accounts):
    """منوی حذف اکانت"""
    keyboard = []
    
    for acc in accounts:
        btn_text = f"🗑️ حذف {acc['game_name']}"
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"delete_{acc['id']}")])
    
    keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="my_accounts")])
    return InlineKeyboardMarkup(keyboard)

def update_options_menu(account_id):
    """منوی تغییر اکانت"""
    keyboard = [
        [InlineKeyboardButton("⚔️ تغییر اتک", callback_data=f"up_attack_{account_id}")],
        [InlineKeyboardButton("🛡️ تغییر دفاع", callback_data=f"up_defense_{account_id}")],
        [InlineKeyboardButton("📝 تغییر نام", callback_data=f"up_name_{account_id}")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="my_accounts")]
    ]
    return InlineKeyboardMarkup(keyboard)

def admin_panel_menu():
    """منوی پنل ادمین"""
    keyboard = [
        [InlineKeyboardButton("👥 مدیریت کاربران", callback_data="admin_users")],
        [InlineKeyboardButton("📊 آمار پیشرفته", callback_data="admin_stats")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def admin_users_menu(users, page=0):
    """منوی مدیریت کاربران"""
    keyboard = []
    
    start = page * 5
    end = start + 5
    page_users = users[start:end]
    
    for user in page_users:
        username = f"@{user['username']}" if user['username'] else user['first_name']
        btn_text = f"{username}"
        
        keyboard.append([
            InlineKeyboardButton(btn_text, callback_data=f"admin_view_{user['user_id']}"),
            InlineKeyboardButton("⚙️ مدیریت", callback_data=f"admin_manage_{user['user_id']}")
        ])
    
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("◀️ قبلی", callback_data=f"admin_page_{page-1}"))
    
    if end < len(users):
        nav_buttons.append(InlineKeyboardButton("▶️ بعدی", callback_data=f"admin_page_{page+1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")])
    return InlineKeyboardMarkup(keyboard)

def admin_user_accounts_menu(user_accounts, user_id):
    """منوی مدیریت اکانت‌های کاربر"""
    keyboard = []
    
    for acc in user_accounts:
        btn_text = f"🎮 {acc['game_name']} (⚔{format_num(acc['attack'])} 🛡{format_num(acc['defense'])})"
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"admin_delete_single_{acc['id']}")])
    
    keyboard.append([
        InlineKeyboardButton("🗑️ حذف همه", callback_data=f"admin_delete_all_{user_id}"),
        InlineKeyboardButton("🔙 بازگشت", callback_data="admin_users")
    ])
    
    return InlineKeyboardMarkup(keyboard)

def rankings_menu():
    """منوی رتبه‌بندی"""
    keyboard = [
        [InlineKeyboardButton("🥇 ۱۰ نفر اول", callback_data="top10")],
        [InlineKeyboardButton("🥈 ۲۰ نفر اول", callback_data="top20")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)
