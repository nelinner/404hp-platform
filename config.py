BOT_TOKEN = "ВАШ_ТОКЕН_ОТ_BOTFATHER"

# Супергруппы для лобби (замени на реальные -100... ID)
GROUPS = {
    ("5x5", "pro"):     -10017007,
    ("2x2", "pro"):     -10017011,
    ("5x5", "default"): -10017005,
    ("2x2", "default"): -10017009,
}

CHANNEL_DRAW    = -1000022   # канал жеребьёвки
CHANNEL_RESULTS = -1000025   # канал результатов

OWNER_USERNAME = "nelinner"   # владелец проекта (получает админку)

MAPS = ["Dune", "Sandstone", "Rust", "Province", "Breeze", "Prison", "Hanami"]

MODE_SIZES = {"5x5": 10, "2x2": 4}

LEAGUES = {"default": "Default league", "pro": "Pro league"}

START_MMR   = 300      # скрытый стартовый MMR
WIN_MMR     = 150      # +за победу при калибровке
LOSS_MMR    = -200     # -за поражение при калибровке
CALIB_GAMES = 10       # сколько игр нужно до открытия LVL
