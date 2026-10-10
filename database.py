import aiosqlite, json, time

DB = "404hp.db"

async def init_db():
    async with aiosqlite.connect(DB) as db:
        await db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            user_id     INTEGER PRIMARY KEY,
            username    TEXT,
            game_id     TEXT,
            nickname    TEXT,
            mmr         INTEGER DEFAULT 300,
            wins        INTEGER DEFAULT 0,
            losses      INTEGER DEFAULT 0,
            kills       INTEGER DEFAULT 0,
            deaths      INTEGER DEFAULT 0,
            games_played INTEGER DEFAULT 0,
            elo         INTEGER DEFAULT 0,
            calibrated  INTEGER DEFAULT 0,
            is_admin    INTEGER DEFAULT 0,
            is_banned   INTEGER DEFAULT 0,
            is_muted    INTEGER DEFAULT 0,
            can_host    INTEGER DEFAULT 1,
            registered  INTEGER DEFAULT 0,
            league      TEXT DEFAULT 'default',
            created_at  INTEGER
        );
        CREATE TABLE IF NOT EXISTS parties (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            leader_id INTEGER,
            members TEXT,
            created_at INTEGER
        );
        CREATE TABLE IF NOT EXISTS lobbies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mode TEXT, league TEXT, map TEXT,
            match_number INTEGER,
            players TEXT,
            ct_team TEXT, t_team TEXT,
            host_id INTEGER,
            status TEXT DEFAULT 'open',
            message_id INTEGER,
            chat_id INTEGER,
            registered INTEGER DEFAULT 0,
            created_at INTEGER
        );
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            type TEXT,
            description TEXT,
            status TEXT DEFAULT 'open',
            created_at INTEGER
        );
        CREATE TABLE IF NOT EXISTS matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lobby_id INTEGER,
            host_id INTEGER,
            ct_team TEXT, t_team TEXT,
            map TEXT, league TEXT, mode TEXT,
            status TEXT DEFAULT 'pending',
            created_at INTEGER
        );
        """)
        await db.commit()

# ---------- USERS ----------
async def get_user(uid):
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM users WHERE user_id=?", (uid,))
        r = await cur.fetchone()
        return dict(r) if r else None

async def create_user(uid, username, game_id, nickname):
    async with aiosqlite.connect(DB) as db:
        await db.execute(
            "INSERT OR REPLACE INTO users (user_id,username,game_id,nickname,registered,league,created_at) "
            "VALUES (?,?,?,?,1,'default',?)",
            (uid, username, game_id, nickname, int(time.time()))
        )
        await db.commit()

async def update_user(uid, **fields):
    if not fields: return
    keys = ", ".join(f"{k}=?" for k in fields)
    vals = list(fields.values()) + [uid]
    async with aiosqlite.connect(DB) as db:
        await db.execute(f"UPDATE users SET {keys} WHERE user_id=?", vals)
        await db.commit()

async def all_users():
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM users ORDER BY mmr DESC")
        return [dict(r) for r in await cur.fetchall()]

async def apply_match_result(uid, win: bool, kills: int, deaths: int):
    u = await get_user(uid)
    if not u: return
    games = u["games_played"] + 1
    mmr = u["mmr"]
    if not u["calibrated"]:
        mmr += WIN_MMR if win else LOSS_MMR
    else:
        mmr += 15 if win else -15
    mmr = max(0, mmr)
    await update_user(
        uid,
        mmr=mmr,
        games_played=games,
        wins=u["wins"] + (1 if win else 0),
        losses=u["losses"] + (0 if win else 1),
        kills=u["kills"] + kills,
        deaths=u["deaths"] + deaths,
        calibrated=1 if games >= 10 else u["calibrated"],
    )

# ---------- PARTY ----------
async def get_party_by_member(uid):
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM parties")
        for r in await cur.fetchall():
            if uid in json.loads(r["members"]):
                return dict(r)
    return None

async def create_party(leader_id):
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute(
            "INSERT INTO parties (leader_id,members,created_at) VALUES (?,?,?)",
            (leader_id, json.dumps([leader_id]), int(time.time()))
        )
        await db.commit()
        return cur.lastrowid

async def update_party(pid, members):
    async with aiosqlite.connect(DB) as db:
        await db.execute("UPDATE parties SET members=? WHERE id=?",
                         (json.dumps(members), pid))
        await db.commit()

async def delete_party(pid):
    async with aiosqlite.connect(DB) as db:
        await db.execute("DELETE FROM parties WHERE id=?", (pid,))
        await db.commit()

# ---------- LOBBIES ----------
async def create_lobby(mode, league, map_name, match_number, chat_id):
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute(
            "INSERT INTO lobbies (mode,league,map,match_number,players,ct_team,t_team,chat_id,created_at) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (mode, league, map_name, match_number, "[]", "[]", "[]", chat_id, int(time.time()))
        )
        await db.commit()
        return cur.lastrowid

async def get_lobby(lid):
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM lobbies WHERE id=?", (lid,))
        r = await cur.fetchone()
        return dict(r) if r else None

async def get_lobby_by_msg(chat_id, message_id):
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM lobbies WHERE chat_id=? AND message_id=?",
            (chat_id, message_id)
        )
        r = await cur.fetchone()
        return dict(r) if r else None

async def get_open_lobby(mode, league):
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM lobbies WHERE mode=? AND league=? AND status='open' "
            "ORDER BY id DESC LIMIT 1", (mode, league)
        )
        r = await cur.fetchone()
        return dict(r) if r else None

async def update_lobby(lid, **f):
    if not f: return
    keys = ", ".join(f"{k}=?" for k in f)
    vals = list(f.values()) + [lid]
    async with aiosqlite.connect(DB) as db:
        await db.execute(f"UPDATE lobbies SET {keys} WHERE id=?", vals)
        await db.commit()

async def next_match_number():
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("SELECT COUNT(*) FROM lobbies")
        (c,) = await cur.fetchone()
        return c + 1

# ---------- TICKETS ----------
async def create_ticket(uid, ttype, desc):
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute(
            "INSERT INTO tickets (user_id,type,description,created_at) VALUES (?,?,?,?)",
            (uid, ttype, desc, int(time.time()))
        )
        await db.commit()
        return cur.lastrowid

async def open_tickets():
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM tickets WHERE status='open' ORDER BY id")
        return [dict(r) for r in await cur.fetchall()]

async def close_ticket(tid):
    async with aiosqlite.connect(DB) as db:
        await db.execute("UPDATE tickets SET status='closed' WHERE id=?", (tid,))
        await db.commit()

# ---------- MATCHES ----------
async def create_match(lobby_id, host_id, ct, t, map_name, league, mode):
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute(
            "INSERT INTO matches (lobby_id,host_id,ct_team,t_team,map,league,mode,created_at) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (lobby_id, host_id, json.dumps(ct), json.dumps(t), map_name, league, mode, int(time.time()))
        )
        await db.commit()
        return cur.lastrowid

async def matches_by_host(host_id):
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM matches WHERE host_id=? AND status='pending'", (host_id,))
        return [dict(r) for r in await cur.fetchall()]

async def get_match(mid):
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM matches WHERE id=?", (mid,))
        r = await cur.fetchone()
        return dict(r) if r else None

async def set_match_status(mid, status):
    async with aiosqlite.connect(DB) as db:
        await db.execute("UPDATE matches SET status=? WHERE id=?", (status, mid))
        await db.commit()

async def all_pending_matches():
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM matches WHERE status='pending'")
        return [dict(r) for r in await cur.fetchall()]
