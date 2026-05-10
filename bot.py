import os
import json
import logging
from pathlib import Path

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    CallbackQueryHandler,
    Filters,
    CallbackContext,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

DATA_FILE = Path(__file__).parent / "data.json"

GAMES = [
    "CS2",
    "Valorant",
    "Dota 2",
    "Fortnite",
    "Minecraft",
    "Brawl Stars",
    "Roblox",
]

ROLES = {
    "CS2":         ["Entry Fragger", "AWPer", "Support", "Lurker", "IGL", "Any"],
    "Valorant":    ["Duelist", "Controller", "Initiator", "Sentinel", "Flex", "Any"],
    "Dota 2":      ["Carry", "Mid", "Offlane", "Soft Support", "Hard Support", "Any"],
    "Fortnite":    ["Fragger", "Builder", "Support", "Any"],
    "Minecraft":   ["Builder", "PvP Fighter", "Miner", "Farmer", "Explorer", "Any"],
    "Brawl Stars": ["Tank", "DPS", "Support", "Thrower", "Assassin", "Any"],
    "Roblox":      ["Attacker", "Defender", "Support", "Builder", "Any"],
}

TRANSLATIONS = {
    "en": {
        "lang_prompt":      "🌐 Please select your language:",
        "welcome":          (
            "👋 Welcome to the Gaming Teammate Finder, {name}!\n\n"
            "Commands:\n"
            "• /register — Create or update your profile\n"
            "• /profile  — View your profile\n"
            "• /lfg      — Post a Looking For Group ad\n"
            "• /find     — Browse players by game\n"
            "• /language — Change language"
        ),
        "no_profile":       "You don't have a profile yet. Use /register to create one!",
        "your_profile":     "🎮 *Your Profile*",
        "nickname_label":   "🏷 Nickname",
        "game_label":       "🕹 Game",
        "rank_label":       "🏆 Rank",
        "role_label":       "⚔️ Role",
        "reg_start":        "Let's set up your profile!\n\nWhat's your in-game nickname?",
        "reg_invalid_nick": "Please enter a valid nickname (1–32 characters).",
        "reg_pick_game":    "Nice, *{nickname}*! Now pick your main game:",
        "reg_pick_rank":    "Great choice — *{game}*!\n\nWhat's your current rank? (e.g. Gold, Platinum, Global Elite)",
        "reg_invalid_rank": "Please enter a valid rank (1–32 characters).",
        "reg_pick_role":    "Almost done! Choose your preferred role:",
        "reg_saved":        (
            "✅ *Profile saved!*\n\n"
            "🏷 Nickname: {nickname}\n"
            "🕹 Game: {game}\n"
            "🏆 Rank: {rank}\n"
            "⚔️ Role: {role}\n\n"
            "Use /lfg to post a Looking For Group ad, or /find to browse players!"
        ),
        "reg_cancelled":    "Registration cancelled. Use /register to start again.",
        "lfg_need_profile": "You need a profile first! Use /register to set one up.",
        "lfg_prompt":       (
            "📢 Posting as *{nickname}* ({game} — {rank} — {role})\n\n"
            "Add an optional message, or send /skip to post without one:"
        ),
        "lfg_too_long":     "Message too long (max 200 chars). Try again or /skip:",
        "lfg_live":         "✅ Your LFG ad is live! Players can find you with /find.",
        "lfg_cancelled":    "LFG post cancelled.",
        "find_prompt":      "🔍 Which game are you looking for teammates in?",
        "find_all":         "🔍 All Games",
        "find_no_posts":    "No active LFG posts for *{game}*.\n\nBe the first — use /lfg!",
        "find_title":       "🔍 LFG Posts — {game}",
        "find_title_all":   "🔍 All LFG Posts",
        "find_count_one":   "{count} player",
        "find_count_many":  "{count} players",
        "find_truncated":   "_(list truncated)_",
        "find_cancelled":   "Browse cancelled.",
    },
    "ru": {
        "lang_prompt":      "🌐 Пожалуйста, выберите язык:",
        "welcome":          (
            "👋 Добро пожаловать в поиск тиммейтов, {name}!\n\n"
            "Команды:\n"
            "• /register — Создать или обновить профиль\n"
            "• /profile  — Просмотреть профиль\n"
            "• /lfg      — Разместить объявление LFG\n"
            "• /find     — Найти игроков по игре\n"
            "• /language — Сменить язык"
        ),
        "no_profile":       "У вас ещё нет профиля. Используйте /register для создания!",
        "your_profile":     "🎮 *Ваш профиль*",
        "nickname_label":   "🏷 Никнейм",
        "game_label":       "🕹 Игра",
        "rank_label":       "🏆 Ранг",
        "role_label":       "⚔️ Роль",
        "reg_start":        "Давайте создадим ваш профиль!\n\nКакой у вас игровой никнейм?",
        "reg_invalid_nick": "Пожалуйста, введите корректный никнейм (1–32 символа).",
        "reg_pick_game":    "Отлично, *{nickname}*! Выберите вашу основную игру:",
        "reg_pick_rank":    "Хороший выбор — *{game}*!\n\nКакой у вас текущий ранг? (например: Золото, Платина, Global Elite)",
        "reg_invalid_rank": "Пожалуйста, введите корректный ранг (1–32 символа).",
        "reg_pick_role":    "Почти готово! Выберите предпочтительную роль:",
        "reg_saved":        (
            "✅ *Профиль сохранён!*\n\n"
            "🏷 Никнейм: {nickname}\n"
            "🕹 Игра: {game}\n"
            "🏆 Ранг: {rank}\n"
            "⚔️ Роль: {role}\n\n"
            "Используйте /lfg для объявления или /find для поиска игроков!"
        ),
        "reg_cancelled":    "Регистрация отменена. Используйте /register для повторного запуска.",
        "lfg_need_profile": "Сначала нужен профиль! Используйте /register.",
        "lfg_prompt":       (
            "📢 Публикация от имени *{nickname}* ({game} — {rank} — {role})\n\n"
            "Добавьте сообщение или отправьте /skip, чтобы пропустить:"
        ),
        "lfg_too_long":     "Сообщение слишком длинное (макс. 200 символов). Попробуйте ещё раз или /skip:",
        "lfg_live":         "✅ Ваше LFG-объявление опубликовано! Игроки найдут вас через /find.",
        "lfg_cancelled":    "Публикация LFG отменена.",
        "find_prompt":      "🔍 В какой игре вы ищете тиммейтов?",
        "find_all":         "🔍 Все игры",
        "find_no_posts":    "Активных LFG-объявлений для *{game}* не найдено.\n\nБудьте первым — используйте /lfg!",
        "find_title":       "🔍 LFG — {game}",
        "find_title_all":   "🔍 Все LFG-объявления",
        "find_count_one":   "{count} игрок",
        "find_count_many":  "{count} игроков",
        "find_truncated":   "_(список обрезан)_",
        "find_cancelled":   "Поиск отменён.",
    },
}

# ── conversation states ────────────────────────────────────────────────────────
SELECT_LANG  = 0
REG_NICKNAME = 1
REG_GAME     = 2
REG_RANK     = 3
REG_ROLE     = 4
LFG_MESSAGE  = 10
FIND_GAME    = 20


# ── helpers ───────────────────────────────────────────────────────────────────

def t(key, lang, **kw):
    text = TRANSLATIONS.get(lang, TRANSLATIONS["en"]).get(
        key, TRANSLATIONS["en"].get(key, key)
    )
    return text.format(**kw) if kw else text


def load_data():
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"users": {}, "lfg_posts": []}


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_user(user_id):
    return load_data()["users"].get(str(user_id))


def save_user(user_id, profile):
    data = load_data()
    data["users"][str(user_id)] = profile
    save_data(data)


def get_lang(user_id, context):
    if context.user_data.get("lang"):
        return context.user_data["lang"]
    user_profile = get_user(user_id)
    if user_profile and user_profile.get("lang"):
        return user_profile["lang"]
    return "en"


def persist_lang(user_id, lang, context):
    context.user_data["lang"] = lang
    data = load_data()
    uid = str(user_id)
    if uid not in data["users"]:
        data["users"][uid] = {}
    data["users"][uid]["lang"] = lang
    save_data(data)


# ── /start & /language ────────────────────────────────────────────────────────

def start(update, context):
    keyboard = [[
        InlineKeyboardButton("🇬🇧 English", callback_data="setlang:en"),
        InlineKeyboardButton("🇷🇺 Русский", callback_data="setlang:ru"),
    ]]
    update.message.reply_text(
        "🌐 Please select your language / Пожалуйста, выберите язык:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return SELECT_LANG


def select_lang_callback(update, context):
    query = update.callback_query
    query.answer()
    lang = query.data.split(":", 1)[1]
    persist_lang(update.effective_user.id, lang, context)
    query.edit_message_text(
        t("welcome", lang, name=update.effective_user.first_name)
    )
    return ConversationHandler.END


def language_command(update, context):
    lang = get_lang(update.effective_user.id, context)
    keyboard = [[
        InlineKeyboardButton("🇬🇧 English", callback_data="setlang:en"),
        InlineKeyboardButton("🇷🇺 Русский", callback_data="setlang:ru"),
    ]]
    update.message.reply_text(
        t("lang_prompt", lang),
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return SELECT_LANG


# ── /profile ──────────────────────────────────────────────────────────────────

def profile(update, context):
    user_id = update.effective_user.id
    lang    = get_lang(user_id, context)
    user_profile = get_user(user_id)
    if not user_profile:
        update.message.reply_text(t("no_profile", lang))
        return
    text = (
        f"{t('your_profile', lang)}\n\n"
        f"{t('nickname_label', lang)}: {user_profile['nickname']}\n"
        f"{t('game_label', lang)}: {user_profile['game']}\n"
        f"{t('rank_label', lang)}: {user_profile['rank']}\n"
        f"{t('role_label', lang)}: {user_profile['role']}"
    )
    update.message.reply_text(text, parse_mode="Markdown")


# ── /register ─────────────────────────────────────────────────────────────────

def register_start(update, context):
    lang = get_lang(update.effective_user.id, context)
    update.message.reply_text(t("reg_start", lang))
    return REG_NICKNAME


def reg_nickname(update, context):
    lang     = get_lang(update.effective_user.id, context)
    nickname = update.message.text.strip()
    if not nickname or len(nickname) > 32:
        update.message.reply_text(t("reg_invalid_nick", lang))
        return REG_NICKNAME
    context.user_data["reg_nickname"] = nickname
    keyboard = [[InlineKeyboardButton(g, callback_data=f"reg_game:{g}")] for g in GAMES]
    update.message.reply_text(
        t("reg_pick_game", lang, nickname=nickname),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )
    return REG_GAME


def reg_game(update, context):
    query = update.callback_query
    query.answer()
    lang  = get_lang(update.effective_user.id, context)
    game  = query.data.split(":", 1)[1]
    context.user_data["reg_game"] = game
    query.edit_message_text(
        t("reg_pick_rank", lang, game=game),
        parse_mode="Markdown",
    )
    return REG_RANK


def reg_rank(update, context):
    lang = get_lang(update.effective_user.id, context)
    rank = update.message.text.strip()
    if not rank or len(rank) > 32:
        update.message.reply_text(t("reg_invalid_rank", lang))
        return REG_RANK
    context.user_data["reg_rank"] = rank
    game  = context.user_data["reg_game"]
    roles = ROLES.get(game, ["Any"])
    keyboard = [[InlineKeyboardButton(r, callback_data=f"reg_role:{r}")] for r in roles]
    update.message.reply_text(
        t("reg_pick_role", lang),
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return REG_ROLE


def reg_role(update, context):
    query   = update.callback_query
    query.answer()
    lang    = get_lang(update.effective_user.id, context)
    role    = query.data.split(":", 1)[1]
    user_id = update.effective_user.id
    profile_data = {
        "nickname":   context.user_data["reg_nickname"],
        "game":       context.user_data["reg_game"],
        "rank":       context.user_data["reg_rank"],
        "role":       role,
        "user_id":    user_id,
        "username":   update.effective_user.username,
        "first_name": update.effective_user.first_name,
        "lang":       lang,
    }
    save_user(user_id, profile_data)
    query.edit_message_text(
        t("reg_saved", lang,
          nickname=profile_data["nickname"],
          game=profile_data["game"],
          rank=profile_data["rank"],
          role=profile_data["role"]),
        parse_mode="Markdown",
    )
    saved_lang = lang
    context.user_data.clear()
    context.user_data["lang"] = saved_lang
    return ConversationHandler.END


def reg_cancel(update, context):
    lang = get_lang(update.effective_user.id, context)
    context.user_data.clear()
    update.message.reply_text(t("reg_cancelled", lang))
    return ConversationHandler.END


# ── /lfg ──────────────────────────────────────────────────────────────────────

def lfg_start(update, context):
    user_id      = update.effective_user.id
    lang         = get_lang(user_id, context)
    user_profile = get_user(user_id)
    if not user_profile:
        update.message.reply_text(t("lfg_need_profile", lang))
        return ConversationHandler.END
    update.message.reply_text(
        t("lfg_prompt", lang,
          nickname=user_profile["nickname"],
          game=user_profile["game"],
          rank=user_profile["rank"],
          role=user_profile["role"]),
        parse_mode="Markdown",
    )
    return LFG_MESSAGE


def lfg_message(update, context):
    lang     = get_lang(update.effective_user.id, context)
    msg_text = update.message.text.strip()
    if msg_text.startswith("/skip"):
        msg_text = ""
    elif len(msg_text) > 200:
        update.message.reply_text(t("lfg_too_long", lang))
        return LFG_MESSAGE
    user_id      = update.effective_user.id
    user_profile = get_user(user_id)
    data = load_data()
    data["lfg_posts"] = [p for p in data["lfg_posts"] if p["user_id"] != user_id]
    data["lfg_posts"].append({
        "user_id":    user_id,
        "nickname":   user_profile["nickname"],
        "game":       user_profile["game"],
        "rank":       user_profile["rank"],
        "role":       user_profile["role"],
        "username":   user_profile.get("username"),
        "first_name": user_profile.get("first_name"),
        "message":    msg_text,
    })
    save_data(data)
    update.message.reply_text(t("lfg_live", lang))
    return ConversationHandler.END


def lfg_cancel(update, context):
    lang = get_lang(update.effective_user.id, context)
    update.message.reply_text(t("lfg_cancelled", lang))
    return ConversationHandler.END


# ── /find ─────────────────────────────────────────────────────────────────────

def find_start(update, context):
    lang     = get_lang(update.effective_user.id, context)
    keyboard = [[InlineKeyboardButton(g, callback_data=f"find_game:{g}")] for g in GAMES]
    keyboard.append([InlineKeyboardButton(t("find_all", lang), callback_data="find_game:all")])
    update.message.reply_text(
        t("find_prompt", lang),
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return FIND_GAME


def find_game(update, context):
    query       = update.callback_query
    query.answer()
    lang        = get_lang(update.effective_user.id, context)
    game_filter = query.data.split(":", 1)[1]
    user_id     = update.effective_user.id
    data        = load_data()

    if game_filter == "all":
        posts = data["lfg_posts"]
        title = t("find_title_all", lang)
    else:
        posts = [p for p in data["lfg_posts"] if p["game"] == game_filter]
        title = t("find_title", lang, game=game_filter)

    posts = [p for p in posts if p["user_id"] != user_id]

    if not posts:
        game_display = game_filter if game_filter != "all" else (
            "any game" if lang == "en" else "любой игры"
        )
        query.edit_message_text(
            t("find_no_posts", lang, game=game_display),
            parse_mode="Markdown",
        )
        return ConversationHandler.END

    count     = len(posts)
    count_key = "find_count_one" if count == 1 else "find_count_many"
    count_str = t(count_key, lang, count=count)
    lines     = [f"*{title}* ({count_str})\n"]

    for p in posts:
        contact = f"@{p['username']}" if p.get("username") else p.get("first_name", "Unknown")
        line = (
            f"\n🎮 *{p['nickname']}*\n"
            f"  🕹 {p['game']} | 🏆 {p['rank']} | ⚔️ {p['role']}\n"
            f"  👤 {contact}"
        )
        if p.get("message"):
            line += f"\n  💬 _{p['message']}_"
        lines.append(line)

    text = "\n".join(lines)
    if len(text) > 4000:
        text = text[:3990] + "\n\n" + t("find_truncated", lang)

    query.edit_message_text(text, parse_mode="Markdown")
    return ConversationHandler.END


def find_cancel(update, context):
    lang = get_lang(update.effective_user.id, context)
    update.message.reply_text(t("find_cancelled", lang))
    return ConversationHandler.END


# ── error handler ─────────────────────────────────────────────────────────────

def error_handler(update, context):
    logger.error("Unhandled error:", exc_info=context.error)


# ── entry point ───────────────────────────────────────────────────────────────

def main():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN environment variable is not set.")

    updater    = Updater(token=token, use_context=True)
    dispatcher = updater.dispatcher

    lang_states = {
        SELECT_LANG: [CallbackQueryHandler(select_lang_callback, pattern=r"^setlang:")]
    }

    dispatcher.add_handler(ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states=lang_states,
        fallbacks=[],
    ))

    dispatcher.add_handler(ConversationHandler(
        entry_points=[CommandHandler("language", language_command)],
        states=lang_states,
        fallbacks=[],
    ))

    dispatcher.add_handler(CommandHandler("profile", profile))

    dispatcher.add_handler(ConversationHandler(
        entry_points=[CommandHandler("register", register_start)],
        states={
            REG_NICKNAME: [MessageHandler(Filters.text & ~Filters.command, reg_nickname)],
            REG_GAME:     [CallbackQueryHandler(reg_game, pattern=r"^reg_game:")],
            REG_RANK:     [MessageHandler(Filters.text & ~Filters.command, reg_rank)],
            REG_ROLE:     [CallbackQueryHandler(reg_role, pattern=r"^reg_role:")],
        },
        fallbacks=[CommandHandler("cancel", reg_cancel)],
    ))

    dispatcher.add_handler(ConversationHandler(
        entry_points=[CommandHandler("lfg", lfg_start)],
        states={
            LFG_MESSAGE: [
                MessageHandler(Filters.text & ~Filters.command, lfg_message),
                CommandHandler("skip", lfg_message),
            ],
        },
        fallbacks=[CommandHandler("cancel", lfg_cancel)],
    ))

    dispatcher.add_handler(ConversationHandler(
        entry_points=[CommandHandler("find", find_start)],
        states={
            FIND_GAME: [CallbackQueryHandler(find_game, pattern=r"^find_game:")],
        },
        fallbacks=[CommandHandler("cancel", find_cancel)],
    ))

    dispatcher.add_error_handler(error_handler)

    logger.info("Bot is starting…")
    updater.start_polling(drop_pending_updates=True)
    updater.idle()


if __name__ == "__main__":
    main()
