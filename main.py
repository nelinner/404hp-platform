import asyncio, random, json, time
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
import keyboards as kb

router = Router()
bot: Bot = None


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
        is_admin_flag = bool(u["is_admin"]) or (m.from_user.username == OWNER_USERNAME)
        return await m.answer(
            "🏠 <b>404hp faceit</b>\nГлавное меню:",
            reply_markup=kb.main_menu(is_admin_flag)
        )
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
    await state.update_data(nickname=m.text)
    d = await state.get_data()
    await state.set_state(Reg.confirm)
    txt = (f"Шаг 3/3 — подтверди свои данные:\n\n"
           f"🆔 ID: <code>{d['game_id']}</code>\n"
           f"👤 Ник: <b>{d['nickname']}</b>")
    await m.answer(txt, reply_markup=kb.confirm_registration())


@router.callback_query(F.data == "reg_confirm", Reg.confirm)
async def reg_done(c: CallbackQuery, state: FSMContext):
    d = await state.get_data()
    await db.create_user(c.from_user.id, c.from_user.username or "", d["game_id"], d["nickname"])
    await state.clear()
    await c.message.edit_text(
        "✅ Регистрация успешно завершена!\n\n"
        "ℹ️ Твой LVL скрыт до <b>10 калибровочных игр</b>.\n"
        "Стартовый MMR: <b>300</b> (скрыт).\n"
        "Твоя лига по умолчанию: <b>🟦 Default league</b>.",
        reply_markup=kb.main_menu(False)
    )


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
    is_admin_flag = bool(u["is_admin"]) if u else False
    await c.message.edit_text("🏠 <b>404hp faceit</b>\nГлавное меню:",
                              reply_markup=kb.main_menu(is_admin_flag))


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

    league = u.get("league") or "default"
    if league == "pro":
        league_txt = "💎 <b>Pro league</b>"
    else:
        league_txt = "🟦 <b>Default league</b>"

    txt = (
        f"[👤] <b>{u['nickname']}</b>\n"
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
    await c.message.edit_text(txt, reply_markup=kb.back_menu())


# ============================================================
#                         PARTY
# ============================================================
@router.callback_query(F.data == "menu_party")
async def party_menu(c: CallbackQuery):
    p = await db.get_party_by_member(c.from_user.id)
    if not p:
        txt = "🎉 <b>Party</b>\n\nТы не в пати."
    else:
        members = json.loads(p["members"])
        mentions = []
        for uid in members:
            u = await db.get_user(uid)
            mentions.append(f"• {u['nickname'] if u else uid}")
        txt = (f"🎉 <b>Party</b>\n\n"
               f"👑 Лидер: <code>{p['leader_id']}</code>\n"
               f"Участников: <b>{len(members)}/3</b>\n\n" + "\n".join(mentions))
    await c.message.edit_text(txt, reply_markup=kb.party_kb())


@router.callback_query(F.data == "party_create")
async def party_create(c: CallbackQuery):
    p = await db.get_party_by_member(c.from_user.id)
    if p:
        return await c.answer("Ты уже в пати!", show_alert=True)
    await db.create_party(c.from_user.id)
    await c.answer("✅ Лобби пати создано!")
    await party_menu(c)


@router.callback_query(F.data == "party_leave")
async def party_leave(c: CallbackQuery):
    p = await db.get_party_by_member(c.from_user.id)
    if not p:
        return await c.answer("Ты не в пати.", show_alert=True)
    members = json.loads(p["members"])
    members = [x for x in members if x != c.from_user.id]
    if not members:
        await db.delete_party(p["id"])
    else:
        await db.update_party(p["id"], members)
    await c.answer("🚪 Ты вышел из пати.")
    await party_menu(c)


# ============================================================
#                       TICKETS
# ============================================================
class Ticket(StatesGroup):
    custom = State()


@router.callback_query(F.data == "menu_ticket")
async def ticket_menu(c: CallbackQuery):
    await c.message.edit_text(
        "🎫 <b>Тикет поддержки</b>\n\nВыбери тип обращения:",
        reply_markup=kb.ticket_kb()
    )


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
                   reply_markup=kb.back_menu())


# ============================================================
#                       SEARCH GAME
# ============================================================
@router.callback_query(F.data == "menu_search")
async def search_menu(c: CallbackQuery):
    await c.message.edit_text("🔎 <b>Поиск игры</b>\n\nВыбери режим:",
                              reply_markup=kb.search_kb())


@router.callback_query(F.data.startswith("search:"))
async def search_mode(c: CallbackQuery):
    mode = c.data.split(":")[1]
    await c.message.edit_text(f"🔎 Режим <b>{mode}</b>\nВыбери лигу:",
                              reply_markup=kb.league_kb(mode))


@router.callback_query(F.data.startswith("league:"))
async def search_league(c: CallbackQuery):
    _, mode, league = c.data.split(":")
    u = await db.get_user(c.from_user.id)
    if not u:
        return await c.answer("Сначала зарегистрируйся.", show_alert=True)

    user_league = u.get("league") or "default"
    if league == "pro" and user_league != "pro":
        return await c.answer("🚫 Тебе недоступна Pro league. Обратись к админам.",
                              show_alert=True)

    lobby = await db.get_open_lobby(mode, league)
    if not lobby:
        return await c.answer("❌ Открытых лобби нет. Подожди обновления.", show_alert=True)

    await c.message.edit_text(
        f"✅ Игра найдена!\n\n"
        f"Режим: <b>{mode}</b>\nЛига: <b>{LEAGUES[league]}</b>\n"
        f"Карта: <b>{lobby['map']}</b>\n\n"
        f"➡️ Переходи в чат лобби и нажми «Присоединиться».",
        reply_markup=kb.back_menu()
    )


# ============================================================
#                    LOBBIES (supergroups)
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
        if not u: continue
        lvl = get_level(u["mmr"])[0] if u["calibrated"] else 0
        out.append({"nickname": u["nickname"], "game_id": u["game_id"], "lvl": lvl})
    return out


async def refresh_lobby_message(lobby_id):
    l = await db.get_lobby(lobby_id)
    if not l: return
    players = await render_players(json.loads(l["players"]))
    try:
        await bot.edit_message_text(
            chat_id=l["chat_id"], message_id=l["message_id"],
            text=render_lobby(l, players),
            reply_markup=kb.lobby_kb(l["id"])
        )
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
    if not l: return await c.answer("Лобби не найдено.", show_alert=True)
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
    await db.update_lobby(
        lid,
        ct_team=json.dumps(ct), t_team=json.dumps(t),
        host_id=host_id, status="full"
    )
    mid = await db.create_match(lid, host_id, ct, t, l["map"], l["league"], l["mode"])

    ct_p = await render_players(ct)
    t_p = await render_players(t)
    lines = [
        "🔄 <b>Жеребьёвка игроков</b>",
        "━━━━━━━━━━━━━━━━━━━",
        f"> {LEAGUES[l['league']]}",
        f"> Maps: <b>{l['map']}</b>",
        f"> Host: <b>{host['nickname']}</b>",
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
            parse_mode=ParseMode.HTML
        )
    except Exception:
        pass

    await spawn_lobby(l["mode"], l["league"], l["chat_id"])


async def spawn_lobby(mode, league, chat_id):
    map_name = random.choice(MAPS)
    num = await db.next_match_number()
    lid = await db.create_lobby(mode, league, map_name, num, chat_id)
    l = await db.get_lobby(lid)
    msg = await bot.send_message(
        chat_id, render_lobby(l, []), reply_markup=kb.lobby_kb(lid)
    )
    await db.update_lobby(lid, message_id=msg.message_id)


async def refresh_all_lobbies():
    for (mode, league), chat_id in GROUPS.items():
        try:
            await bot.send_message(
                chat_id,
                f"🔄 Обновление лобби <b>{mode}</b> | {LEAGUES[league]}",
                parse_mode=ParseMode.HTML
            )
        except Exception:
            pass
        await spawn_lobby(mode, league, chat_id)


# ============================================================
#                          MY HOST
# ============================================================
@router.callback_query(F.data == "menu_host")
async def host_menu(c: CallbackQuery):
    u = await db.get_user(c.from_user.id)
    if not u or not u["can_host"]:
        return await c.answer("🚫 У тебя нет прав хоста.", show_alert=True)
    await c.message.edit_text("🖥 <b>My host</b>\n\nУправление твоими матчами:",
                              reply_markup=kb.host_kb())


@router.callback_query(F.data == "host_list")
async def host_list(c: CallbackQuery):
    ms = await db.matches_by_host(c.from_user.id)
    if not ms:
        return await c.message.edit_text("У тебя нет активных матчей.",
                                         reply_markup=kb.back_menu())
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
                              reply_markup=kb.back_menu())


@router.callback_query(F.data == "host_cancel")
async def host_cancel(c: CallbackQuery):
    await c.message.edit_text(
        "🚫 Заявка на отмену матча отправлена администрации.\n"
        "Ожидай одобрения.", reply_markup=kb.back_menu()
    )


# ============================================================
#                       RESULTS
# ============================================================
async def publish_results(mid, ct_scores=None):
    m = await db.get_match(mid)
    if not m: return
    ct = json.loads(m["t_team"])
    t  = json.loads(m["ct_team"])
    ct_p = await render_players(ct)
    t_p  = await render_players(t)
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
def is_admin(u):
    return u and (u["is_admin"] or (u["username"] == OWNER_USERNAME))


@router.callback_query(F.data == "admin_panel")
async def admin_panel(c: CallbackQuery):
    u = await db.get_user(c.from_user.id)
    if not is_admin(u):
        return await c.answer("Нет доступа.", show_alert=True)
    await c.message.edit_text("🛡 <b>Админ-панель</b>", reply_markup=kb.admin_kb())


@router.callback_query(F.data == "admin_list")
async def admin_list(c: CallbackQuery):
    u = await db.get_user(c.from_user.id)
    if not is_admin(u): return await c.answer("Нет доступа.", show_alert=True)
    users = await db.all_users()
    lines = ["📃 <b>Список игроков:</b>", ""]
    for x in users[:50]:
        lg = "💎" if (x.get("league") or "default") == "pro" else "🟦"
        lines.append(
            f"<code>{x['user_id']}</code> | {x['nickname']} | "
            f"{x['game_id']} | {lg} | {'💠' if x['calibrated'] else '🔒'} {x['mmr']} MMR"
        )
    await c.message.edit_text("\n".join(lines), reply_markup=kb.back_menu())


class AdminAct(StatesGroup):
    target = State()
    action = State()
    map_choice = State()


@router.callback_query(F.data == "admin_users")
async def admin_users(c: CallbackQuery, state: FSMContext):
    u = await db.get_user(c.from_user.id)
    if not is_admin(u): return await c.answer("Нет доступа.", show_alert=True)
    await state.set_state(AdminAct.target)
    await c.message.edit_text(
        "Отправь <b>user_id</b> игрока, с которым нужно взаимодействовать:"
    )


@router.message(AdminAct.target)
async def admin_pick(m: Message, state: FSMContext):
    if not m.text.isdigit():
        return await m.answer("Введи числовой user_id.")
    target = await db.get_user(int(m.text))
    if not target:
        return await m.answer("Игрок не найден.")
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
        f"Игрок: <b>{target['nickname']}</b>\n"
        f"Текущая лига: <b>{cur_league}</b>\n\n"
        f"Выбери действие:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=btns)
    )


@router.callback_query(F.data.startswith("act:"))
async def admin_do(c: CallbackQuery, state: FSMContext):
    u = await db.get_user(c.from_user.id)
    if not is_admin(u): return await c.answer("Нет доступа.", show_alert=True)

    d = await state.get_data()
    uid = d.get("target")
    act = c.data.split(":")[1]

    if act == "league_default":
        await db.update_user(uid, league="default")
        await c.message.edit_text("✅ Игроку выдана <b>Default league</b>.",
                                  reply_markup=kb.back_menu())
        await state.clear()
        return
    if act == "league_pro":
        await db.update_user(uid, league="pro")
        await c.message.edit_text("✅ Игроку выдана <b>Pro league</b>.",
                                  reply_markup=kb.back_menu())
        await state.clear()
        return

    field = {
        "ban":   ("is_banned", 1), "unban": ("is_banned", 0),
        "mute":  ("is_muted", 1),  "unmute":("is_muted", 0),
        "nohost":("can_host", 0),  "yeshost":("can_host", 1),
    }[act]
    await db.update_user(uid, **{field[0]: field[1]})
    await c.message.edit_text(f"✅ Действие <b>{act}</b> выполнено.",
                              reply_markup=kb.back_menu())
    await state.clear()


@router.callback_query(F.data == "admin_pending")
async def admin_pending(c: CallbackQuery):
    u = await db.get_user(c.from_user.id)
    if not is_admin(u): return await c.answer("Нет доступа.", show_alert=True)
    ms = await db.all_pending_matches()
    if not ms:
        return await c.message.edit_text("Нет незарегистрированных матчей.",
                                         reply_markup=kb.back_menu())
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
    if not is_admin(u): return await c.answer("Нет доступа.", show_alert=True)
    mid = int(c.data.split(":")[1])
    await db.set_match_status(mid, "registered")
    await c.answer("✅ Зарегистрировано.")
    await admin_pending(c)


@router.callback_query(F.data == "admin_edit")
async def admin_edit(c: CallbackQuery):
    u = await db.get_user(c.from_user.id)
    if not is_admin(u): return await c.answer("Нет доступа.", show_alert=True)
    await c.message.edit_text(
        "✏️ Введи ID матча для публикации/редактирования результатов:\n"
        "Пример: <code>/result 5</code>",
        reply_markup=kb.back_menu()
    )


@router.message(Command("result"))
async def cmd_result(m: Message):
    u = await db.get_user(m.from_user.id)
    if not is_admin(u): return
    args = m.text.split()
    if len(args) < 2 or not args[1].isdigit():
        return await m.answer("Использование: /result <match_id>")
    await publish_results(int(args[1]))
    await m.answer("✅ Результаты опубликованы.")


@router.callback_query(F.data == "admin_refresh")
async def admin_refresh(c: CallbackQuery):
    u = await db.get_user(c.from_user.id)
    if not is_admin(u): return await c.answer("Нет доступа.", show_alert=True)
    await refresh_all_lobbies()
    await c.answer("🔄 Лобби обновлены.")


@router.callback_query(F.data == "admin_map")
async def admin_map(c: CallbackQuery):
    u = await db.get_user(c.from_user.id)
    if not is_admin(u): return await c.answer("Нет доступа.", show_alert=True)
    btns = []
    for (mode, league), chat_id in GROUPS.items():
        btns.append([B(text=f"{mode} | {LEAGUES[league]}",
                       callback_data=f"admin_setmap:{mode}:{league}")])
    btns.append([B(text="⬅️ Назад", callback_data="admin_panel")])
    await c.message.edit_text("🗺 Выбери лобби:",
                              reply_markup=InlineKeyboardMarkup(inline_keyboard=btns))


@router.callback_query(F.data.startswith("admin_setmap:"))
async def admin_setmap(c: CallbackQuery):
    u = await db.get_user(c.from_user.id)
    if not is_admin(u): return await c.answer("Нет доступа.", show_alert=True)
    _, mode, league = c.data.split(":")
    l = await db.get_open_lobby(mode, league)
    if not l:
        return await c.answer("Лобби не найдено.", show_alert=True)
    new_map = random.choice([x for x in MAPS if x != l["map"]])
    await db.update_lobby(l["id"], map=new_map)
    await refresh_lobby_message(l["id"])
    await c.answer(f"🗺 Карта изменена: {new_map}")


@router.callback_query(F.data == "admin_grant")
async def admin_grant(c: CallbackQuery, state: FSMContext):
    u = await db.get_user(c.from_user.id)
    if not is_admin(u): return await c.answer("Нет доступа.", show_alert=True)
    await state.set_state(AdminAct.target)
    await c.message.edit_text("Отправь user_id игрока, которому выдать админку:")


@router.callback_query(F.data == "admin_revoke")
async def admin_revoke(c: CallbackQuery, state: FSMContext):
    u = await db.get_user(c.from_user.id)
    if not is_admin(u): return await c.answer("Нет доступа.", show_alert=True)
    await state.set_state(AdminAct.target)
    await c.message.edit_text("Отправь user_id игрока, у которого забрать админку:")


@router.callback_query(F.data == "admin_tickets")
async def admin_tickets(c: CallbackQuery):
    u = await db.get_user(c.from_user.id)
    if not is_admin(u): return await c.answer("Нет доступа.", show_alert=True)
    ts = await db.open_tickets()
    if not ts:
        return await c.message.edit_text("Нет открытых тикетов.",
                                         reply_markup=kb.back_menu())
    lines = ["🎫 <b>Открытые тикеты:</b>", ""]
    btns = []
    for t in ts:
        lines.append(f"#{t['id']} | {t['type']} | <code>{t['user_id']}</code>\n"
                     f"<i>{t['description'][:80]}</i>")
        btns.append([B(text=f"Закрыть #{t['id']}",
                       callback_data=f"tclose:{t['id']}")])
    btns.append([B(text="⬅️ Назад", callback_data="admin_panel")])
    await c.message.edit_text("\n\n".join(lines),
                              reply_markup=InlineKeyboardMarkup(inline_keyboard=btns))


@router.callback_query(F.data.startswith("tclose:"))
async def ticket_close(c: CallbackQuery):
    u = await db.get_user(c.from_user.id)
    if not is_admin(u): return await c.answer("Нет доступа.", show_alert=True)
    tid = int(c.data.split(":")[1])
    await db.close_ticket(tid)
    await c.answer("✅ Тикет закрыт.")
    await admin_tickets(c)


# ============================================================
#                       ADMIN COMMANDS
# ============================================================
@router.message(Command("admin"))
async def cmd_admin(m: Message):
    u = await db.get_user(m.from_user.id)
    if not is_admin(u): return
    await m.answer("🛡 Админ-панель", reply_markup=kb.admin_kb())


@router.message(Command("start_lobbies"))
async def cmd_start_lobbies(m: Message):
    u = await db.get_user(m.from_user.id)
    if not is_admin(u): return
    await refresh_all_lobbies()
    await m.answer("✅ Лобби инициализированы во всех группах.")


@router.message(Command("next"))
async def cmd_next(m: Message):
    u = await db.get_user(m.from_user.id)
    if not is_admin(u): return
    for (mode, league), chat_id in GROUPS.items():
        if chat_id == m.chat.id:
            await spawn_lobby(mode, league, chat_id)
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
    print("🤖 404hp faceit bot started")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Stopped.")
