BOT_TOKEN = "8668847269:AAG1aKg-YX3tE5cFic10mryMmozLqN1aBm0"

# ID форум-супергруппы (общий для всех лобби-топиков)
FORUM_CHAT_ID = -1004345869414

# Каждый лобби-раздел = (chat_id, message_thread_id)
GROUPS = {
    ("5x5", "pro"):     (FORUM_CHAT_ID, 17007),
    ("2x2", "pro"):     (FORUM_CHAT_ID, 17011),
    ("5x5", "default"): (FORUM_CHAT_ID, 17005),
    ("2x2", "default"): (FORUM_CHAT_ID, 17009),
}

# Жеребьёвка и результаты — топики той же группы.
# Если это отдельные КАНАЛЫ, замени на (ID_КАНАЛА, None)
CHANNEL_DRAW    = (FORUM_CHAT_ID, 22)
CHANNEL_RESULTS = (FORUM_CHAT_ID, 25)

OWNER_USERNAME = "nelinner"

MAPS = ["Dune", "Sandstone", "Rust", "Province", "Breeze", "Prison", "Hanami"]
MODE_SIZES = {"5x5": 10, "2x2": 4}
LEAGUES = {"default": "Default league", "pro": "Pro league"}

START_MMR   = 300
WIN_MMR     = 150
LOSS_MMR    = -200
CALIB_GAMES = 10
