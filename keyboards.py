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
        # تعیین آیکون کاراکتر
        character_icon = ""
        if acc['character'] == 'cat':
            character_icon = "🐱"
        elif acc['character'] == 'dog':
            character_icon = "🐶"
        elif acc['character'] == 'frog':
            character_icon = "🐸"
        
        btn_text = f"🎮 {acc['game_name']} {character_icon} (⚔{format_num(acc['attack'])} 🛡{format_num(acc['defense'])})"
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

def character_menu(account_id):
    """منوی انتخاب کاراکتر"""
    keyboard = [
        [InlineKeyboardButton("🐱 گربه", callback_data=f"char_cat_{account_id}")],
        [InlineKeyboardButton("🐶 سگ", callback_data=f"char_dog_{account_id}")],
        [InlineKeyboardButton("🐸 قورباغه", callback_data=f"char_frog_{account_id}")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data=f"view_{account_id}")]
    ]
    return InlineKeyboardMarkup(keyboard)

def update_options_menu(account_id):
    """منوی تغییر اکانت"""
    keyboard = [
        [InlineKeyboardButton("⚔️ تغییر اتک", callback_data=f"up_attack_{account_id}")],
        [InlineKeyboardButton("🛡️ تغییر دفاع", callback_data=f"up_defense_{account_id}")],
        [InlineKeyboardButton("📝 تغییر نام", callback_data=f"up_name_{account_id}")],
        [InlineKeyboardButton("🎭 تغییر کاراکتر", callback_data=f"change_char_{account_id}")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="my_accounts")]
    ]
    return InlineKeyboardMarkup(keyboard)

def admin_panel_menu():
    """منوی پنل ادمین"""
    keyboard = [
        [InlineKeyboardButton("👥 مدیریت کاربران", callback_data="admin_users")],
        [InlineKeyboardButton("📊 آمار پیشرفته", callback_data="admin_stats")],
        [InlineKeyboardButton("📅 تاریخ بروزرسانی‌ها", callback_data="admin_update_history")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def admin_users_menu(users, page=0, items_per_page=5):
    """منوی مدیریت کاربران (برای ادمین)"""
    keyboard = []
    
    start_idx = page * items_per_page
    end_idx = start_idx + items_per_page
    paginated_users = users[start_idx:end_idx]
    
    for user in paginated_users:
        username = f"@{user['username']}" if user['username'] else user['first_name']
        admin_status = " 👑" if user['is_admin'] else ""
        
        btn_text = f"{username}{admin_status} ({user['account_count']} اکانت)"
        
        keyboard.append([
            InlineKeyboardButton(btn_text, callback_data=f"admin_user_detail_{user['user_id']}"),
            InlineKeyboardButton("⚙️ مدیریت", callback_data=f"admin_manage_{user['user_id']}")
        ])
    
    # دکمه‌های صفحه‌بندی
    navigation = []
    if page > 0:
        navigation.append(InlineKeyboardButton("◀️ قبلی", callback_data=f"admin_users_page_{page-1}"))
    
    if end_idx < len(users):
        navigation.append(InlineKeyboardButton("▶️ بعدی", callback_data=f"admin_users_page_{page+1}"))
    
    if navigation:
        keyboard.append(navigation)
    
    keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")])
    
    return InlineKeyboardMarkup(keyboard)

def admin_user_detail_menu(user_id):
    """منوی جزئیات کاربر (برای ادمین)"""
    keyboard = [
        [InlineKeyboardButton("👁️ مشاهده اکانت‌ها", callback_data=f"admin_view_accounts_{user_id}")],
        [InlineKeyboardButton("➕/➖ ادمین کردن", callback_data=f"admin_toggle_admin_{user_id}")],
        [InlineKeyboardButton("🗑️ حذف همه اکانت‌ها", callback_data=f"admin_delete_all_{user_id}")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_users")]
    ]
    return InlineKeyboardMarkup(keyboard)

def admin_user_accounts_menu(accounts, user_id):
    """منوی اکانت‌های کاربر (برای ادمین)"""
    keyboard = []
    
    for acc in accounts:
        # تعیین آیکون کاراکتر
        character_icon = ""
        if acc['character'] == 'cat':
            character_icon = "🐱"
        elif acc['character'] == 'dog':
            character_icon = "🐶"
        elif acc['character'] == 'frog':
            character_icon = "🐸"
        
        btn_text = f"🎮 {acc['game_name']} {character_icon}"
        keyboard.append([
            InlineKeyboardButton(btn_text, callback_data=f"admin_account_detail_{acc['id']}"),
            InlineKeyboardButton("🗑️", callback_data=f"admin_delete_account_{acc['id']}")
        ])
    
    keyboard.append([
        InlineKeyboardButton("🗑️ حذف همه", callback_data=f"admin_delete_all_accounts_{user_id}"),
        InlineKeyboardButton("🔙 بازگشت", callback_data=f"admin_user_detail_{user_id}")
    ])
    
    return InlineKeyboardMarkup(keyboard)

def admin_account_detail_menu(account_id):
    """منوی جزئیات اکانت (برای ادمین)"""
    keyboard = [
        [InlineKeyboardButton("⚔️ تغییر اتک", callback_data=f"admin_update_attack_{account_id}")],
        [InlineKeyboardButton("🛡️ تغییر دفاع", callback_data=f"admin_update_defense_{account_id}")],
        [InlineKeyboardButton("📝 تغییر نام", callback_data=f"admin_update_name_{account_id}")],
        [InlineKeyboardButton("🎭 تغییر کاراکتر", callback_data=f"admin_update_character_{account_id}")],
        [InlineKeyboardButton("🗑️ حذف این اکانت", callback_data=f"admin_delete_single_{account_id}")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_users")]
    ]
    return InlineKeyboardMarkup(keyboard)

def confirm_delete_menu(target_id, action_type="account"):
    """منوی تایید حذف"""
    keyboard = [
        [
            InlineKeyboardButton("✅ بله، حذف کن", callback_data=f"confirm_delete_{action_type}_{target_id}"),
            InlineKeyboardButton("❌ خیر، لغو", callback_data="admin_users")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def confirm_toggle_admin_menu(user_id):
    """منوی تایید تغییر وضعیت ادمین"""
    keyboard = [
        [
            InlineKeyboardButton("✅ بله، تغییر بده", callback_data=f"confirm_toggle_admin_{user_id}"),
            InlineKeyboardButton("❌ خیر، لغو", callback_data=f"admin_user_detail_{user_id}")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def rankings_menu():
    """منوی رتبه‌بندی"""
    keyboard = [
        [InlineKeyboardButton("🥇 ۱۰ نفر اول", callback_data="top10")],
        [InlineKeyboardButton("🥈 ۲۰ نفر اول", callback_data="top20")],
        [InlineKeyboardButton("📊 رتبه‌بندی کامل", callback_data="full_rankings")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def admin_update_history_menu():
    """منوی تاریخ بروزرسانی برای ادمین"""
    keyboard = [
        [InlineKeyboardButton("📅 امروز", callback_data="admin_updates_today")],
        [InlineKeyboardButton("📅 دیروز", callback_data="admin_updates_yesterday")],
        [InlineKeyboardButton("📅 ۷ روز گذشته", callback_data="admin_updates_week")],
        [InlineKeyboardButton("📅 ۳۰ روز گذشته", callback_data="admin_updates_month")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]
    ]
    return InlineKeyboardMarkup(keyboard)

def character_selection_menu():
    """منوی انتخاب کاراکتر برای ثبت اکانت جدید"""
    keyboard = [
        [InlineKeyboardButton("🐱 گربه", callback_data="char_cat_new")],
        [InlineKeyboardButton("🐶 سگ", callback_data="char_dog_new")],
        [InlineKeyboardButton("🐸 قورباغه", callback_data="char_frog_new")],
        [InlineKeyboardButton("❌ لغو", callback_data="cancel")]
    ]
    return InlineKeyboardMarkup(keyboard)
