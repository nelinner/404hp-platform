from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton as B
from config import MODE_SIZES

def main_menu(is_admin=False):
    rows = [
        [B(text="👤 Профиль", callback_data="menu_profile")],
        [B(text="🎉 Party", callback_data="menu_party")],
        [B(text="🎫 Тикет поддержки", callback_data="menu_ticket")],
        [B(text="🔎 Поиск игры", callback_data="menu_search")],
        [B(text="🖥 My host", callback_data="menu_host")],
    ]
    if is_admin:
        rows.append([B(text="🛡 Админ-панель", callback_data="admin_panel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def confirm_registration():
    return InlineKeyboardMarkup(inline_keyboard=[
        [B(text="✅ Подтвердить", callback_data="reg_confirm")],
        [B(text="❌ Отмена", callback_data="reg_cancel")],
    ])

def back_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [B(text="⬅️ Назад", callback_data="main_menu")]
    ])

def party_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [B(text="➕ Создать лобби", callback_data="party_create")],
        [B(text="🚪 Выйти из пати", callback_data="party_leave")],
        [B(text="⬅️ Назад", callback_data="main_menu")],
    ])

def ticket_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [B(text="🖥 Проблема с хостом", callback_data="ticket:host")],
        [B(text="🚫 Жалоба на игрока", callback_data="ticket:player")],
        [B(text="🛡 Жалоба на админа", callback_data="ticket:admin")],
        [B(text="✍️ Описать проблему", callback_data="ticket:custom")],
        [B(text="⬅️ Назад", callback_data="main_menu")],
    ])

def search_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [B(text="5x5", callback_data="search:5x5"),
         B(text="2x2", callback_data="search:2x2")],
        [B(text="⬅️ Назад", callback_data="main_menu")],
    ])

def league_kb(mode):
    return InlineKeyboardMarkup(inline_keyboard=[
        [B(text="Default league", callback_data=f"league:{mode}:default")],
        [B(text="Pro league",     callback_data=f"league:{mode}:pro")],
        [B(text="⬅️ Назад", callback_data="menu_search")],
    ])

def lobby_kb(lobby_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [B(text="🚪 Присоединиться", callback_data=f"lobby_join:{lobby_id}")],
        [B(text="⬅️ Выйти",         callback_data=f"lobby_leave:{lobby_id}")],
    ])

def host_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [B(text="📋 Мои матчи",         callback_data="host_list")],
        [B(text="✅ Зарегистрировать",  callback_data="host_register")],
        [B(text="🚫 Отменить матч",     callback_data="host_cancel")],
        [B(text="⬅️ Назад",             callback_data="main_menu")],
    ])

def admin_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [B(text="👥 Управление аккаунтом", callback_data="admin_users")],
        [B(text="📃 Список игроков",       callback_data="admin_list")],
        [B(text="⏳ Незарег. матчи",       callback_data="admin_pending")],
        [B(text="✏️ Изменить матч",        callback_data="admin_edit")],
        [B(text="🔄 Обновить лобби",       callback_data="admin_refresh")],
        [B(text="🗺 Поменять карту",       callback_data="admin_map")],
        [B(text="🛡 Выдать админку",       callback_data="admin_grant")],
        [B(text="🚫 Забрать админку",      callback_data="admin_revoke")],
        [B(text="🎫 Тикеты",               callback_data="admin_tickets")],
        [B(text="⬅️ Назад",               callback_data="main_menu")],
    ])
