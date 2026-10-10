import asyncio, random, json, time
import aiosqlite
from aiogram import Bot, Dispatcher, F, Router
from aiogram.types import (Message, CallbackQuery, InlineKeyboardMarkup,
                           InlineKeyboardButton as B)
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import *
from levels import get_level
import database as db

router = Router()
bot: Bot = None
REFRESH_INTERVAL = 15 * 60  # 15 минут


# ============================================================
#                       KEYBOARDS
# ============================================================
def main_menu(is_admin_flag=False):
    rows = [
        [B(text="👤 Профиль", callback_data="menu_profile")],
        [B(text="🎉 Party", callback_data="menu_party")],
        [B(text="🎫 Тикет поддержки", callback_data="menu_ticket")],
        [B(text="🔎 Поиск игры", callback_data="menu_search")],
        [B(text="🖥 My host", callback_data="menu_host")],
    ]
    if is_admin_flag:
        rows.append([B(text="🛡 Админ-панель", callback_data="admin_panel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def confirm_registration():
    return InlineKeyboardMarkup(inline_keyboard=[
        [B(text="✅ Подтвердить", callback_data="reg_confirm")],
        [B(text="❌ Отмена", callback_data="reg_cancel")],
    ])


def back_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [B(text="⬅️ Назад", callback_data="main_menu")]])


def party_kb(has_party=False):
    rows = []
    if not has_party:
        rows.append([B(text="➕ Создать лобби", callback_data="party_create")])
    else:
        rows.append([B(text="➕ Пригласить тиммейта", callback_data="party_invite")])
        rows.append([B(text="🚪 Выйти из пати", callback_data="party_leave")])
    rows.append([B(text="⬅️ Назад", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def ticket_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [B(text="🖥 Проблема с хостом", callback_data="ticket:host")],
        [B(text="🚫 Жалоба на игрока", callback_data="ticket:player")],
        [B(text="🛡 Жалоба на админа", callback_data="ticket:admin")],
        [B(text="✍️ Описать проблему", callback_data="ticket:custom")],
        [B(text="⬅️ Назад", callback_data="main_menu")]])


def search_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [B(text="5x5", callback_data="search:5x5"),
         B(text="2x2", callback_data="search:2x2")],
        [B(text="⬅️ Назад", callback_data="main_menu")]])


def league_kb(mode):
    return InlineKeyboardMarkup(inline_keyboard=[
        [B(text="Default league", callback_data=f"league:{mode}:default")],
        [B(text="Pro league",     callback_data=f"league:{mode}:pro")],
        [B(text="⬅️ Назад", callback_data="menu_search")]])


def lobby_kb(lobby_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [B(text="🚪 Присоединиться", callback_data=f"lobby_join:{lobby_id}")],
        [B(text="⬅️ Выйти",         callback_data=f"lobby_leave:{lobby_id}")]])


def host_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [B(text="📋 Мои матчи",         callback_data="host_list")],
        [B(text="✅ Зарегистрировать",  callback_data="host_register")],
        [B(text="🚫 Отменить матч",     callback_data="host_cancel")],
        [B(text="⬅️ Назад",             callback_data="main_menu")]])


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
        [B(text="⬅️ Назад",               callback_data="main_menu")]])


# ============================================================
#                       HELPERS
# ============================================================
def is_admin(u):
    if not u:
        return False
    if u.get("is_admin"):
        return True
    return (u.get("username") or "").lstrip("@").lower() == OWNER_USERNAME.lower()


async def edit_or_send(c: CallbackQuery, text: str, kb=None):
    try:
        await c.message.edit_text(text, reply_markup=kb)
    except Exception:
        await c.message.answer(text, reply_markup=kb)


# ============================================================
#                       REGISTRATION
# ============================================================
class Reg(StatesGroup):
    game_id = State()
    nickname = State()
    confirm = State()


@router.message(CommandStart())
async def cmd_start(m: Message, state: FSMContext):
    if m.chat.type != "private":
        return
    u = await db.get_user(m.from_user.id)
    if u and u["registered"]:
        return await m.answer("🏠 <b>404hp faceit</b>\nГлавное меню:",
                              reply_markup=main_menu(is_admin(u)))
    await state.set_state(Reg.game_id)
    await m.answer("🎮 Добро пожаловать в <b>404hp faceit</b>!\n\n"
                   "Шаг 1/3 — отправь свой <b>игровой ID</b> (Standoff 2):")


@router.message(Reg.game_id)
async def reg_gid(m: Message, state: FSMContext):
    if not m.text or not m.text.isdigit():
        return await m.answer("⚠️ Игровой ID должен состоять из цифр.")
    await state.update_data(game_id=m.text)
    await state.set_state(Reg.nickname)
    await m.answer("Шаг 2/3 — отправь свой <b>игровой ник</b>:")


@router.message(Reg.nickname)
async def reg_nick(m: Message, state: FSMContext):
    if not m.text or len(m.text) > 32:
        return await m.answer("⚠️ Ник должен быть от 1 до 32 символов.")
    # проверка уникальности ника
    existing = await db.find_user_by_login(m.text)
    if existing and existing["user_id"] != m.from_user.id:
        return await m.answer("⚠️ Этот ник уже занят. Введи другой.")
    await state.update_data(nickname=m.text)
    d = await state.get_data()
    await state.set_state(Reg.confirm)
    txt = (f"Шаг 3/3 — подтверди свои данные:\n\n"
           f"🆔 ID: <code>{d['game_id']}</code>\n"
           f"👤 Ник: <b>{d['nickname']}</b>\n"
           f"📛 Telegram: @{m.from_user.username or '—'}")
    await m.answer(txt, reply_markup=confirm_registration())


@router.callback_query(F.data == "reg_confirm", Reg.confirm)
async def reg_done(c: CallbackQuery, state: FSMContext):
    d = await state.get_data()
    await db.create_user(c.from_user.id, c.from_user.username or "",
                         d["game_id"], d["nickname"])
    if (c.from_user.username or "").lstrip("@").lower() == OWNER_USERNAME.lower():
        await db.update_user(c.from_user.id, is_admin=1)
    await state.clear()
    u = await db.get_user(c.from_user.id)
    await c.message.edit_text(
        "✅ Регистрация успешно завершена!\n\n"
        "ℹ️ Твой LVL скрыт до <b>10 калибровочных игр</b>.\n"
        "Стартовый MMR: <b>300</b> (скрыт).\n"
        "Лига: <b>🟦 Default league</b>.",
        reply_markup=main_menu(is_admin(u)))


@router.callback_query(F.data == "reg_cancel", Reg.confirm)
async def reg_cancel(c: CallbackQuery, state: FSMContext):
    await state.clear()
    await c.message.edit_text("❌ Регистрация отменена. /start чтобы попробовать снова.")


# ============================================================
#                       MAIN MENU
# ============================================================
@router.callback_query(F.data == "main_menu")
async def goto_main(c: CallbackQuery):
    u = await db.get_user(c.from_user.id)
    await edit_or_send(c, "🏠 <b>404hp faceit</b>\nГлавное меню:",
                       main_menu(is_admin(u)))


# ============================================================
#                         PROFILE
# ============================================================
@router.callback_query(F.data == "menu_profile")
async def profile(c: CallbackQuery):
    u = await db.get_user(c.from_user.id)
    if not u:
        return await c.answer("Сначала зарегистрируйся: /start", show_alert=True)
    kd = round(u["kills"] / u["deaths"], 2) if u["deaths"] else u["kills"]
    lvl_txt = "🔒 Скрыт (калибровка)"
    if u["calibrated"]:
        lvl, name = get_level(u["mmr"])
        lvl_txt = f"<b>{lvl}</b> — {name} ({u['mmr']} MMR)"
    league_txt = "💎 <b>Pro league</b>" if (u.get("league") or "default") == "pro" else "🟦 <b>Default league</b>"
    txt = (
        f"[👤] <b>{u['nickname']}</b>\n"
        f"@{u['username'] or '—'}\n"
        f"Game ID: <code>{u['game_id']}</code>\n\n"
        f"💠 <b>Статистика:</b>\n"
        f"League: {league_txt}\n"
        f"K/D: <b>{kd}</b>\n"
        f"Сыграно игр: <b>{u['games_played']}</b>\n"
        f"Побед: <b>{u['wins']}</b>\n"
        f"Поражений: <b>{u['losses']}</b>\n"
        f"AVG: <b>{round(u['kills']/max(1,u['games_played']),2)}</b>\n"
        f"LVL: {lvl_txt}\n"
        f"ELO: <b>{u['elo']}</b>"
    )
    await c.message.edit_text(txt, reply_markup=back_menu())


# ============================================================
#                         PARTY
# ============================================================
class PartyInvite(StatesGroup):
    wait_login = State()


async def render_party(c: CallbackQuery):
    p = await db.get_party_by_member(c.from_user.id)
    if not p:
        txt = ("🎉 <b>Party</b>\n\nТы не в пати.\n"
               "Нажми «Создать лобби», чтобы собрать команду до 3 игроков.")
        return await edit_or_send(c, txt, party_kb(has_party=False))
    members = json.loads(p["members"])
    lines = []
    for uid in members:
        u = await db.get_user(uid)
        tag = "👑 " if uid == p["leader_id"] else "• "
        if u:
            lines.append(f"{tag}<b>{u['nickname']}</b> | @{u['username'] or '—'}")
        else:
            lines.append(f"{tag}{uid}")
    txt = (f"🎉 <b>Party</b>\n\n"
           f"Участников: <b>{len(members)}/3</b>\n\n" + "\n".join(lines))
    await edit_or_send(c, txt, party_kb(has_party=True))


@router.callback_query(F.data == "menu_party")
async def party_menu(c: CallbackQuery):
    await render_party(c)


@router.callback_query(F.data == "party_create")
async def party_create(c: CallbackQuery):
    if await db.get_party_by_member(c.from_user.id):
        return await c.answer("Ты уже в пати!", show_alert=True)
    await db.create_party(c.from_user.id)
    await c.answer("✅ Лобби пати создано!")
    await render_party(c)


@router.callback_query(F.data == "party_invite")
async def party_invite(c: CallbackQuery, state: FSMContext):
    p = await db.get_party_by_member(c.from_user.id)
    if not p:
        return await c.answer("Сначала создай пати.", show_alert=True)
    if p["leader_id"] != c.from_user.id:
        return await c.answer("Только лидер пати может приглашать.", show_alert=True)
    if len(json.loads(p["members"])) >= 3:
        return await c.answer("Пати уже заполнено (макс. 3).", show_alert=True)
    await state.set_state(PartyInvite.wait_login)
    await c.message.edit_text(
        "✉️ <b>Приглашение в пати</b>\n\n"
        "Отправь <b>@username</b> или <b>игровой ник</b> игрока.\n"
        "Например: <code>@ivan_petrov</code> или <code>IVAN228</code>",
        reply_markup=back_menu())


@router.message(PartyInvite.wait_login)
async def party_invite_do(m: Message, state: FSMContext):
    login = (m.text or "").strip()
    if not login:
        return await m.answer("⚠️ Введи @username или ник.")

    target = await db.find_user_by_login(login)
    if not target:
        await state.clear()
        return await m.answer("❌ Игрок не найден. Проверь @username или ник.",
                              reply_markup=back_menu())

    p = await db.get_party_by_member(m.from_user.id)
    if not p or p["leader_id"] != m.from_user.id:
        await state.clear()
        return await m.answer("Только лидер может приглашать.", reply_markup=back_menu())

    members = json.loads(p["members"])
    if len(members) >= 3:
        await state.clear()
        return await m.answer("Пати уже заполнено.", reply_markup=back_menu())

    if target["user_id"] in members:
        await state.clear()
        return await m.answer("Игрок уже в пати.", reply_markup=back_menu())

    if await db.get_party_by_member(target["user_id"]):
        await state.clear()
        return await m.answer("Этот игрок уже в другой пати.", reply_markup=back_menu())

    members.append(target["user_id"])
    await db.update_party(p["id"], members)
    await state.clear()

    await m.answer(
        f"✅ <b>{target['nickname']}</b> добавлен в пати.\n"
        f"Участников: <b>{len(members)}/3</b>",
        reply_markup=back_menu())

    try:
        leader = await db.get_user(m.from_user.id)
        await bot.send_message(
            target["user_id"],
            f"✉️ Тебя пригласили в пати к <b>{leader['nickname']}</b>!\n"
            f"Открой <b>🎉 Party</b> в главном меню.",
            parse_mode=ParseMode.HTML)
    except Exception:
        pass


@router.callback_query(F.data == "party_leave")
async def party_leave(c: CallbackQuery):
    p = await db.get_party_by_member(c.from_user.id)
    if not p:
        return await c.answer("Ты не в пати.", show_alert=True)
    members = [x for x in json.loads(p["members"]) if x != c.from_user.id]
    if not members:
        await db.delete_party(p["id"])
    else:
        await db.update_party(p["id"], members)
    await c.answer("🚪 Ты вышел из пати.")
    await render_party(c)


# ============================================================
#                       TICKETS
# ============================================================
class Ticket(StatesGroup):
    custom = State()


@router.callback_query(F.data == "menu_ticket")
async def ticket_menu(c: CallbackQuery):
    await c.message.edit_text("🎫 <b>Тикет поддержки</b>\n\nВыбери тип:",
                              reply_markup=ticket_kb())


@router.callback_query(F.data.startswith("ticket:"))
async def ticket_type(c: CallbackQuery, state: FSMContext):
    t = c.data.split(":")[1]
    names = {"host": "Проблема с хостом", "player": "Жалоба на игрока",
             "admin": "Жалоба на администратора", "custom": "Описание проблемы"}
    await state.update_data(ticket_type=names[t])
    await state.set_state(Ticket.custom)
    await c.message.edit_text(f"📝 Опиши свою проблему ({names[t]}):")


@router.message(Ticket.custom)
async def ticket_submit(m: Message, state: FSMContext):
    d = await state.get_data()
    tid = await db.create_ticket(m.from_user.id, d["ticket_type"], m.text)
    await state.clear()
    await m.answer(f"✅ Тикет #{tid} отправлен. Ожидай ответа администрации.",
                   reply_markup=back_menu())


# ============================================================
#                       SEARCH GAME
# ============================================================
@router.callback_query(F.data == "menu_search")
async def search_menu(c: CallbackQuery):
    await c.message.edit_text("🔎 <b>Поиск игры</b>\n\nВыбери режим:",
                              reply_markup=search_kb())


@router.callback_query(F.data.startswith("search:"))
async def search_mode(c: CallbackQuery):
    mode = c.data.split(":")[1]
    await c.message.edit_text(f"🔎 Режим <b>{mode}</b>\nВыбери лигу:",
                              reply_markup=league_kb(mode))


@router.callback_query(F.data.startswith("league:"))
async def search_league(c: CallbackQuery):
    _, mode, league = c.data.split(":")
    u = await db.get_user(c.from_user.id)
    if not u:
        return await c.answer("Сначала зарегистрируйся.", show_alert=True)
    if league == "pro" and (u.get("league") or "default") != "pro":
        return await c.answer("🚫 Тебе недоступна Pro league.", show_alert=True)
    lobby = await db.get_open_lobby(mode, league)
    if not lobby:
        return await c.answer("❌ Открытых лобби нет. Подожди обновления.", show_alert=True)
    await c.message.edit_text(
        f"✅ Игра найдена!\n\n"
        f"Режим: <b>{mode}</b>\nЛига: <b>{LEAGUES[league]}</b>\n"
        f"Карта: <b>{lobby['map']}</b>\n\n"
        f"➡️ Переходи в чат лобби и нажми «Присоединиться».",
        reply_markup=back_menu())


# ============================================================
#                    LOBBIES
# ============================================================
def render_lobby(lobby, players):
    lines = [
        "📝 <b>Регистрация игроков на матч | 404hp faceit</b>",
        "━━━━━━━━━━━━━━━━━━━",
        f"> {LEAGUES[lobby['league']]}",
        f"> Maps: <b>{lobby['map']}</b>",
        f"> Номер матча: <b>{lobby['match_number']}</b>",
        "━━━━━━━━━━━━━━━━━━━",
        "📃 <b>Список игроков</b>",
        f"— Собрано игроков {len(players)}/{MODE_SIZES[lobby['mode']]}",
        "━━━━━━━━━━━━━━━━━━━",
        "",
        "🔵 <b>CT:</b>",
    ]
    ct = players[::2]
    t = players[1::2]
    for p in ct:
        lines.append(f"[👤] {p['nickname']} | {p['game_id']} | LV {p['lvl']}")
    lines += ["", "🔴 <b>T:</b>"]
    for p in t:
        lines.append(f"[👤] {p['nickname']} | {p['game_id']} | LV {p['lvl']}")
    lines += ["", "━━━━━━━━━━━━━━━━━━━"]
    return "\n".join(lines)


async def render_players(uids):
    out = []
    for uid in uids:
        u = await db.get_user(uid)
        if not u:
            continue
        lvl = get_level(u["mmr"])[0] if u["calibrated"] else 0
        out.append({"nickname": u["nickname"], "game_id": u["game_id"], "lvl": lvl})
    return out


async def refresh_lobby_message(lobby_id):
    l = await db.get_lobby(lobby_id)
    if not l:
        return
    players = await render_players(json.loads(l["players"]))
    try:
        await bot.edit_message_text(
            chat_id=l["chat_id"], message_id=l["message_id"],
            text=render_lobby(l, players),
            reply_markup=lobby_kb(l["id"]))
    except Exception as e:
        print("edit lobby err:", e)


@router.callback_query(F.data.startswith("lobby_join:"))
async def lobby_join(c: CallbackQuery):
    lid = int(c.data.split(":")[1])
    l = await db.get_lobby(lid)
    if not l or l["status"] != "open":
        return await c.answer("Лобби закрыто.", show_alert=True)
    u = await db.get_user(c.from_user.id)
    if not u:
        return await c.answer("Сначала /start в ЛС бота.", show_alert=True)
    if l["league"] == "pro" and (u.get("league") or "default") != "pro":
        return await c.answer("🚫 Только для Pro league игроков.", show_alert=True)

    players = json.loads(l["players"])
    if c.from_user.id in players:
        return await c.answer("Ты уже в лобби.", show_alert=True)
    if len(players) >= MODE_SIZES[l["mode"]]:
        return await c.answer("Лобби заполнено.", show_alert=True)

    players.append(c.from_user.id)
    await db.update_lobby(lid, players=json.dumps(players))
    await refresh_lobby_message(lid)
    await c.answer("✅ Ты присоединился к лобби!")

    if len(players) == MODE_SIZES[l["mode"]]:
        await finalize_lobby(lid)


@router.callback_query(F.data.startswith("lobby_leave:"))
async def lobby_leave(c: CallbackQuery):
    lid = int(c.data.split(":")[1])
    l = await db.get_lobby(lid)
    if not l:
        return await c.answer("Лобби не найдено.", show_alert=True)
    players = json.loads(l["players"])
    if c.from_user.id not in players:
        return await c.answer("Тебя нет в лобби.", show_alert=True)
    players.remove(c.from_user.id)
    await db.update_lobby(lid, players=json.dumps(players))
    await refresh_lobby_message(lid)
    await c.answer("⬅️ Ты вышел из лобби.")


async def finalize_lobby(lid):
    l = await db.get_lobby(lid)
    players = json.loads(l["players"])
    random.shuffle(players)
    size = MODE_SIZES[l["mode"]]
    half = size // 2
    ct, t = players[:half], players[half:]
    host_id = ct[0]
    host = await db.get_user(host_id)

    await db.update_lobby(lid, ct_team=json.dumps(ct), t_team=json.dumps(t),
                          host_id=host_id, status="full")
    await db.create_match(lid, host_id, ct, t, l["map"], l["league"], l["mode"])

    ct_p = await render_players(ct)
    t_p = await render_players(t)
    lines = [
        "🔄 <b>Жеребьёвка игроков</b>",
        "━━━━━━━━━━━━━━━━━━━",
        f"> {LEAGUES[l['league']]}",
        f"> Maps: <b>{l['map']}</b>",
        f"> Host: <b>{host['nickname']}</b> (@{host['username'] or '—'})",
        f"> Номер матча: <b>{l['match_number']}</b>",
        "━━━━━━━━━━━━━━━━━━━",
        "📃 <b>Список игроков</b>",
        "",
        "🔵 <b>CT:</b>",
    ]
    for p in ct_p:
        lines.append(f"[👤] {p['nickname']} | {p['game_id']} | LV {p['lvl']}")
    lines += ["", "🔴 <b>T:</b>"]
    for p in t_p:
        lines.append(f"[👤] {p['nickname']} | {p['game_id']} | LV {p['lvl']}")
    lines += [
        "━━━━━━━━━━━━━━━━━━━",
        "ℹ️ Дается 10 минут на сборы игроков в лобби, если произошли ошибки "
        "с хостом или с созданием лобби, то обратитесь в тех поддержку канала"
    ]
    try:
        await bot.send_message(CHANNEL_DRAW, "\n".join(lines))
    except Exception as e:
        print("draw send err:", e)

    try:
        await bot.send_message(
            host_id,
            f"🖥 Ты стал <b>хостом</b> матча #{l['match_number']}!\n"
            f"Зайди в <b>My host</b> и зарегистрируй игру.",
            parse_mode=ParseMode.HTML)
    except Exception:
        pass

    await spawn_lobby(l["mode"], l["league"], l["chat_id"])


async def spawn_lobby(mode, league, chat_id):
    map_name = random.choice(MAPS)
    num = await db.next_match_number()
    lid = await db.create_lobby(mode, league, map_name, num, chat_id)
    l = await db.get_lobby(lid)
    msg = await bot.send_message(
        chat_id, render_lobby(l, []), reply_markup=lobby_kb(lid))
    await db.update_lobby(lid, message_id=msg.message_id)


async def close_and_respawn(mode, league, chat_id):
    """Удаляет открытые лобби в чате и создаёт новое."""
    async with aiosqlite.connect(db.DB) as conn:
        conn.row_factory = aiosqlite.Row
        cur = await conn.execute(
            "SELECT * FROM lobbies WHERE chat_id=? AND status='open'",
            (chat_id,))
        old = [dict(r) for r in await cur.fetchall()]
    for l in old:
        try:
            await bot.delete_message(l["chat_id"], l["message_id"])
        except Exception:
            pass
        await db.update_lobby(l["id"], status="closed")
    await spawn_lobby(mode, league, chat_id)


async def refresh_all_lobbies():
    """Ручное обновление всех лобби (кнопка в админке)."""
    for (mode, league), chat_id in GROUPS.items():
        try:
            await close_and_respawn(mode, league, chat_id)
        except Exception as e:
            print(f"refresh {mode}/{league} err:", e)


async def auto_refresh_loop():
    """Фоновая задача: обновляет все лобби каждые 15 минут."""
    # Первая публикация сразу при старте
    await asyncio.sleep(3)  # небольшая задержка, чтобы бот успел подняться
    try:
        await refresh_all_lobbies()
        print("✅ Первичная публикация лобби выполнена")
    except Exception as e:
        print("Первичная публикация err:", e)

    while True:
        await asyncio.sleep(REFRESH_INTERVAL)
        try:
            await refresh_all_lobbies()
            print(f"🔄 Автообновление лобби ({time.strftime('%H:%M:%S')})")
        except Exception as e:
            print("auto refresh err:", e)


# ============================================================
#                          MY HOST
# ============================================================
@router.callback_query(F.data == "menu_host")
async def host_menu(c: CallbackQuery):
    u = await db.get_user(c.from_user.id)
    if not u or not u["can_host"]:
        return await c.answer("🚫 У тебя нет прав хоста.", show_alert=True)
    await c.message.edit_text("🖥 <b>My host</b>\n\nУправление твоими матчами:",
                              reply_markup=host_kb())


@router.callback_query(F.data == "host_list")
async def host_list(c: CallbackQuery):
    ms = await db.matches_by_host(c.from_user.id)
    if not ms:
        return await c.message.edit_text("У тебя нет активных матчей.",
                                         reply_markup=back_menu())
    lines = ["📋 <b>Мои матчи:</b>", ""]
    btns = []
    for m in ms:
        lines.append(f"#{m['id']} | {m['mode']} | {LEAGUES[m['league']]} | 🗺 {m['map']}")
        btns.append([B(text=f"Зарегистрировать #{m['id']}",
                       callback_data=f"host_reg:{m['id']}")])
    btns.append([B(text="⬅️ Назад", callback_data="menu_host")])
    await c.message.edit_text("\n".join(lines),
                              reply_markup=InlineKeyboardMarkup(inline_keyboard=btns))


@router.callback_query(F.data == "host_register")
async def host_register_menu(c: CallbackQuery):
    await host_list(c)


@router.callback_query(F.data.startswith("host_reg:"))
async def host_register(c: CallbackQuery):
    mid = int(c.data.split(":")[1])
    m = await db.get_match(mid)
    if not m:
        return await c.answer("Матч не найден.", show_alert=True)
    if m["host_id"] != c.from_user.id:
        return await c.answer("Ты не хост этого матча.", show_alert=True)
    if m["status"] != "pending":
        return await c.answer("Уже зарегистрирован.", show_alert=True)
    await db.set_match_status(mid, "registered")
    await c.answer("✅ Матч зарегистрирован!")
    await c.message.edit_text("Матч зарегистрирован. Ожидай результатов.",
                              reply_markup=back_menu())


@router.callback_query(F.data == "host_cancel")
async def host_cancel(c: CallbackQuery):
    await c.message.edit_text(
        "🚫 Заявка на отмену матча отправлена администрации.\nОжидай одобрения.",
        reply_markup=back_menu())


# ============================================================
#                       RESULTS
# ============================================================
async def publish_results(mid):
    m = await db.get_match(mid)
    if not m:
        return
    ct = json.loads(m["t_team"])
    t = json.loads(m["ct_team"])
    ct_p = await render_players(ct)
    t_p = await render_players(t)
    host = await db.get_user(m["host_id"])
    lines = [
        "🔥 <b>Результаты матча</b>",
        "━━━━━━━━━━━━━━━━━━━",
        f"> {LEAGUES[m['league']]}",
        f"> Host: <b>{host['nickname']}</b>",
        f"> Матч: <b>{mid}</b>",
        "━━━━━━━━━━━━━━━━━━━",
        "📃 <b>Список команд</b>",
        "",
        "🔵 <b>CT:</b>",
    ]
    for p in ct_p:
        lines.append(f"[👤] {p['nickname']} | {p['game_id']} | LV {p['lvl']}")
    lines += ["", "🔴 <b>T:</b>"]
    for p in t_p:
        lines.append(f"[👤] {p['nickname']} | {p['game_id']} | LV {p['lvl']}")
    lines.append("━━━━━━━━━━━━━━━━━━━")
    try:
        await bot.send_message(CHANNEL_RESULTS, "\n".join(lines))
    except Exception as e:
        print("results err:", e)
    for uid in ct:
        await db.apply_match_result(uid, True, 0, 0)
    for uid in t:
        await db.apply_match_result(uid, False, 0, 0)
    await db.set_match_status(mid, "finished")


# ============================================================
#                       ADMIN PANEL
# ============================================================
@router.callback_query(F.data == "admin_panel")
async def admin_panel(c: CallbackQuery):
    u = await db.get_user(c.from_user.id)
    if not is_admin(u):
        return await c.answer("Нет доступа.", show_alert=True)
    await c.message.edit_text("🛡 <b>Админ-панель</b>", reply_markup=admin_kb())


@router.callback_query(F.data == "admin_list")
async def admin_list(c: CallbackQuery):
    u = await db.get_user(c.from_user.id)
    if not is_admin(u):
        return await c.answer("Нет доступа.", show_alert=True)
    users = await db.all_users()
    lines = ["📃 <b>Список игроков:</b>", ""]
    for x in users[:50]:
        lg = "💎" if (x.get("league") or "default") == "pro" else "🟦"
        lines.append(
            f"<b>{x['nickname']}</b> | @{x['username'] or '—'} | {x['game_id']} | "
            f"{lg} | {'💠' if x['calibrated'] else '🔒'} {x['mmr']} MMR"
        )
    await c.message.edit_text("\n".join(lines), reply_markup=back_menu())


class AdminAct(StatesGroup):
    target = State()
    action = State()


@router.callback_query(F.data == "admin_users")
async def admin_users(c: CallbackQuery, state: FSMContext):
    u = await db.get_user(c.from_user.id)
    if not is_admin(u):
        return await c.answer("Нет доступа.", show_alert=True)
    await state.set_state(AdminAct.target)
    await c.message.edit_text(
        "Введи <b>@username</b> или <b>игровой ник</b> игрока:\n"
        "Например: <code>@ivan_petrov</code> или <code>IVAN228</code>")


@router.message(AdminAct.target)
async def admin_pick(m: Message, state: FSMContext):
    target = await db.find_user_by_login(m.text or "")
    if not target:
        return await m.answer("❌ Игрок не найден. Попробуй снова.")
    await state.update_data(target=target["user_id"])
    await state.set_state(AdminAct.action)

    cur_league = target.get("league") or "default"
    btns = [
        [B(text="🔨 Бан",        callback_data="act:ban"),
         B(text="✅ Разбан",      callback_data="act:unban")],
        [B(text="🔇 Мут",        callback_data="act:mute"),
         B(text="🔊 Размут",      callback_data="act:unmute")],
        [B(text="🚫 Запретить host", callback_data="act:nohost"),
         B(text="✅ Разрешить host", callback_data="act:yeshost")],
        [B(text="🟦 League: Default", callback_data="act:league_default"),
         B(text="💎 League: Pro",     callback_data="act:league_pro")],
    ]
    await m.answer(
        f"Игрок: <b>{target['nickname']}</b> (@{target['username'] or '—'})\n"
        f"Текущая лига: <b>{cur_league}</b>\n\nВыбери действие:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=btns))


@router.callback_query(F.data.startswith("act:"))
async def admin_do(c: CallbackQuery, state: FSMContext):
    u = await db.get_user(c.from_user.id)
    if not is_admin(u):
        return await c.answer("Нет доступа.", show_alert=True)
    d = await state.get_data()
    uid = d.get("target")
    act = c.data.split(":")[1]

    if act == "league_default":
        await db.update_user(uid, league="default")
        await c.message.edit_text("✅ Выдана <b>Default league</b>.", reply_markup=back_menu())
        await state.clear(); return
    if act == "league_pro":
        await db.update_user(uid, league="pro")
        await c.message.edit_text("✅ Выдана <b>Pro league</b>.", reply_markup=back_menu())
        await state.clear(); return

    field = {"ban": ("is_banned", 1), "unban": ("is_banned", 0),
             "mute": ("is_muted", 1), "unmute": ("is_muted", 0),
             "nohost": ("can_host", 0), "yeshost": ("can_host", 1)}[act]
    await db.update_user(uid, **{field[0]: field[1]})
    await c.message.edit_text(f"✅ Действие <b>{act}</b> выполнено.",
                              reply_markup=back_menu())
    await state.clear()


@router.callback_query(F.data == "admin_pending")
async def admin_pending(c: CallbackQuery):
    u = await db.get_user(c.from_user.id)
    if not is_admin(u):
        return await c.answer("Нет доступа.", show_alert=True)
    ms = await db.all_pending_matches()
    if not ms:
        return await c.message.edit_text("Нет незарегистрированных матчей.",
                                         reply_markup=back_menu())
    lines = ["⏳ <b>Незарегистрированные матчи:</b>", ""]
    btns = []
    for m in ms:
        lines.append(f"#{m['id']} | {m['mode']} | {LEAGUES[m['league']]} | 🗺 {m['map']}")
        btns.append([B(text=f"Зарегистрировать #{m['id']}",
                       callback_data=f"admin_reg:{m['id']}")])
    btns.append([B(text="⬅️ Назад", callback_data="admin_panel")])
    await c.message.edit_text("\n".join(lines),
                              reply_markup=InlineKeyboardMarkup(inline_keyboard=btns))


@router.callback_query(F.data.startswith("admin_reg:"))
async def admin_register(c: CallbackQuery):
    u = await db.get_user(c.from_user.id)
    if not is_admin(u):
        return await c.answer("Нет доступа.", show_alert=True)
    mid = int(c.data.split(":")[1])
    await db.set_match_status(mid, "registered")
    await c.answer("✅ Зарегистрировано.")
    await admin_pending(c)


@router.callback_query(F.data == "admin_edit")
async def admin_edit(c: CallbackQuery):
    u = await db.get_user(c.from_user.id)
    if not is_admin(u):
        return await c.answer("Нет доступа.", show_alert=True)
    await c.message.edit_text(
        "✏️ Введи ID матча для публикации результатов:\n"
        "Пример: <code>/result 5</code>",
        reply_markup=back_menu())


@router.message(Command("result"))
async def cmd_result(m: Message):
    u = await db.get_user(m.from_user.id)
    if not is_admin(u):
        return
    args = m.text.split()
    if len(args) < 2 or not args[1].isdigit():
        return await m.answer("Использование: /result <match_id>")
    await publish_results(int(args[1]))
    await m.answer("✅ Результаты опубликованы.")


@router.callback_query(F.data == "admin_refresh")
async def admin_refresh(c: CallbackQuery):
    u = await db.get_user(c.from_user.id)
    if not is_admin(u):
        return await c.answer("Нет доступа.", show_alert=True)
    await refresh_all_lobbies()
    await c.answer("🔄 Лобби обновлены.")


@router.callback_query(F.data == "admin_map")
async def admin_map(c: CallbackQuery):
    u = await db.get_user(c.from_user.id)
    if not is_admin(u):
        return await c.answer("Нет доступа.", show_alert=True)
    btns = []
    for (mode, league), _ in GROUPS.items():
        btns.append([B(text=f"{mode} | {LEAGUES[league]}",
                       callback_data=f"admin_setmap:{mode}:{league}")])
    btns.append([B(text="⬅️ Назад", callback_data="admin_panel")])
    await c.message.edit_text("🗺 Выбери лобби:",
                              reply_markup=InlineKeyboardMarkup(inline_keyboard=btns))


@router.callback_query(F.data.startswith("admin_setmap:"))
async def admin_setmap(c: CallbackQuery):
    u = await db.get_user(c.from_user.id)
    if not is_admin(u):
        return await c.answer("Нет доступа.", show_alert=True)
    _, mode, league = c.data.split(":")
    l = await db.get_open_lobby(mode, league)
    if not l:
        return await c.answer("Лобби не найдено.", show_alert=True)
    new_map = random.choice([x for x in MAPS if x != l["map"]])
    await db.update_lobby(l["id"], map=new_map)
    await refresh_lobby_message(l["id"])
    await c.answer(f"🗺 Карта изменена: {new_map}")


class AdminGrant(StatesGroup):
    target = State()


@router.callback_query(F.data == "admin_grant")
async def admin_grant(c: CallbackQuery, state: FSMContext):
    u = await db.get_user(c.from_user.id)
    if not is_admin(u):
        return await c.answer("Нет доступа.", show_alert=True)
    await state.set_state(AdminGrant.target)
    await c.message.edit_text("Введи <b>@username</b> или <b>ник</b> игрока, "
                              "которому выдать админку:")


@router.message(AdminGrant.target)
async def admin_grant_do(m: Message, state: FSMContext):
    target = await db.find_user_by_login(m.text or "")
    if not target:
        return await m.answer("❌ Игрок не найден.")
    await db.update_user(target["user_id"], is_admin=1)
    await state.clear()
    await m.answer(f"✅ <b>{target['nickname']}</b> получил админку.",
                   reply_markup=back_menu())
    try:
        await bot.send_message(target["user_id"], "🛡 Тебе выдана админка в 404hp faceit!")
    except Exception:
        pass


@router.callback_query(F.data == "admin_revoke")
async def admin_revoke(c: CallbackQuery, state: FSMContext):
    u = await db.get_user(c.from_user.id)
    if not is_admin(u):
        return await c.answer("Нет доступа.", show_alert=True)
    await state.set_state(AdminGrant.target)
    await c.message.edit_text("Введи <b>@username</b> или <b>ник</b> игрока, "
                              "у которого забрать админку:")


@router.message(AdminGrant.target)
async def admin_revoke_do(m: Message, state: FSMContext):
    target = await db.find_user_by_login(m.text or "")
    if not target:
        return await m.answer("❌ Игрок не найден.")
    if (target.get("username") or "").lstrip("@").lower() == OWNER_USERNAME.lower():
        return await m.answer("Нельзя забрать админку у владельца.")
    await db.update_user(target["user_id"], is_admin=0)
    await state.clear()
    await m.answer(f"✅ У <b>{target['nickname']}</b> забрана админка.",
                   reply_markup=back_menu())


@router.callback_query(F.data == "admin_tickets")
async def admin_tickets(c: CallbackQuery):
    u = await db.get_user(c.from_user.id)
    if not is_admin(u):
        return await c.answer("Нет доступа.", show_alert=True)
    ts = await db.open_tickets()
    if not ts:
        return await c.message.edit_text("Нет открытых тикетов.", reply_markup=back_menu())
    lines = ["🎫 <b>Открытые тикеты:</b>", ""]
    btns = []
    for t in ts:
        author = await db.get_user(t["user_id"])
        who = f"{author['nickname']} (@{author['username'] or '—'})" if author else t["user_id"]
        lines.append(f"#{t['id']} | {t['type']} | {who}\n<i>{t['description'][:80]}</i>")
        btns.append([B(text=f"Закрыть #{t['id']}", callback_data=f"tclose:{t['id']}")])
    btns.append([B(text="⬅️ Назад", callback_data="admin_panel")])
    await c.message.edit_text("\n\n".join(lines),
                              reply_markup=InlineKeyboardMarkup(inline_keyboard=btns))


@router.callback_query(F.data.startswith("tclose:"))
async def ticket_close(c: CallbackQuery):
    u = await db.get_user(c.from_user.id)
    if not is_admin(u):
        return await c.answer("Нет доступа.", show_alert=True)
    await db.close_ticket(int(c.data.split(":")[1]))
    await c.answer("✅ Тикет закрыт.")
    await admin_tickets(c)


# ============================================================
#                       ADMIN COMMANDS
# ============================================================
@router.message(Command("admin"))
async def cmd_admin(m: Message):
    u = await db.get_user(m.from_user.id)
    if not is_admin(u):
        return
    await m.answer("🛡 Админ-панель", reply_markup=admin_kb())


@router.message(Command("start_lobbies"))
async def cmd_start_lobbies(m: Message):
    u = await db.get_user(m.from_user.id)
    if not is_admin(u):
        return
    await refresh_all_lobbies()
    await m.answer("✅ Лобби инициализированы во всех группах.")


@router.message(Command("next"))
async def cmd_next(m: Message):
    u = await db.get_user(m.from_user.id)
    if not is_admin(u):
        return
    for (mode, league), chat_id in GROUPS.items():
        if chat_id == m.chat.id:
            await close_and_respawn(mode, league, chat_id)
            return
    await m.answer("Этот чат не является лобби-группой.")


# ============================================================
#                            MAIN
# ============================================================
async def main():
    global bot
    await db.init_db()
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(router)

    # Запускаем фоновую задачу авто-обновления лобби
    asyncio.create_task(auto_refresh_loop())

    print("🤖 404hp faceit bot started")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Stopped.")
