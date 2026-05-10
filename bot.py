import os
import json
import asyncio
import logging
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import Conflict
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

DATA_FILE = Path(__file__).parent / "data.json"

GAMES = ["CS2", "Valorant", "Dota 2", "Fortnite", "Minecraft", "Brawl Stars", "Roblox", "Other"]

ROLES = {
    "CS2": ["Entry Fragger", "AWPer", "Support", "Lurker", "IGL", "Any"],
    "Valorant": ["Duelist", "Controller", "Initiator", "Sentinel", "Flex", "Any"],
    "Dota 2": ["Carry", "Mid", "Offlane", "Soft Support", "Hard Support", "Any"],
    "Fortnite": ["Fragger", "Builder", "Support", "Any"],
    "Minecraft": ["Builder", "PvP Fighter", "Miner", "Farmer", "Explorer", "Any"],
    "Brawl Stars": ["Tank", "DPS", "Support", "Thrower", "Assassin", "Any"],
    "Roblox": ["Attacker", "Defender", "Support", "Builder", "Any"],
    "Other": ["DPS", "Tank", "Healer", "Support", "Flex", "Any"],
}

SELECT_LANG = 0
REG_NICKNAME, REG_GAME, REG_RANK, REG_ROLE = range(1, 5)
LFG_MESSAGE = 10
FIND_GAME = 20

TRANSLATIONS = {
    "en": {
        "lang_prompt": "🌐 Please select your language:",
        "welcome": (
            "👋 Welcome to the Gaming Teammate Finder, {name}!\n\n"
            "Use these commands:\n"
            "• /register — Create or update your profile\n"
            "• /profile — View your current profile\n"
            "• /lfg — Post a Looking For Group ad\n"
            "• /find — Browse players by game\n"
            "• /language — Change language"
        ),
        "no_profile": "You don't have a profile yet. Use /register to create one!",
        "your_profile": "🎮 *Your Profile*",
        "nickname_label": "🏷 Nickname",
        "game_label": "🕹 Game",
        "rank_label": "🏆 Rank",
        "role_label": "⚔️ Role",
        "reg_start": "Let's set up your profile!\n\nWhat's your in-game nickname?",
        "reg_invalid_nick": "Please enter a valid nickname (1-32 characters).",
        "reg_pick_game": "Nice, *{nickname}*! Now pick your main game:",
        "reg_pick_rank": "Great choice — *{game}*!\n\nWhat's your current rank? (e.g. Gold, Platinum, Global Elite — anything works)",
        "reg_invalid_rank": "Please enter a valid rank (1-32 characters).",
        "reg_pick_role": "Almost done! Choose your preferred role:",
        "reg_saved": (
            "✅ *Profile saved!*\n\n"
            "🏷 Nickname: {nickname}\n"
            "🕹 Game: {game}\n"
            "🏆 Rank: {rank}\n"
            "⚔️ Role: {role}\n\n"
            "Use /lfg to post a Looking For Group ad, or /find to browse players!"
        ),
        "reg_cancelled": "Registration cancelled. Use /register to start again.",
        "lfg_need_profile": "You need a profile first! Use /register to set one up.",
        "lfg_prompt": (
            "📢 Posting as *{nickname}* ({game} — {rank} — {role})\n\n"
            "Add an optional message for your LFG post, or send /skip to post without one:"
        ),
        "lfg_too_long": "Message too long (max 200 characters). Try again or /skip:",
        "lfg_live": "✅ Your LFG ad is live! Other players can find you with /find.",
        "lfg_cancelled": "LFG post cancelled.",
        "find_prompt": "🔍 Which game are you looking for teammates in?",
        "find_all": "🔍 All Games",
        "find_no_posts": "No active LFG posts found for *{game}*.\n\nBe the first — use /lfg to post your own!",
        "find_title": "🔍 LFG Posts — {game}",
        "find_title_all": "🔍 All LFG Posts",
        "find_players": "{count} player",
        "find_players_plural": "{count} players",
        "find_truncated": "_(list truncated)_",
        "find_cancelled": "Browse cancelled.",
        "lang_changed": "✅ Language set to English.",
    },
    "ru": {
        "lang_prompt": "🌐 Пожалуйста, выберите язык:",
        "welcome": (
            "👋 Добро пожаловать в поиск тиммейтов, {name}!\n\n"
            "Доступные команды:\n"
            "• /register — Создать или обновить профиль\n"
            "• /profile — Просмотреть свой профиль\n"
            "• /lfg — Разместить объявление LFG\n"
            "• /find — Найти игроков по игре\n"
            "• /language — Сменить язык"
        ),
        "no_profile": "У вас ещё нет профиля. Используйте /register для создания!",
        "your_profile": "🎮 *Ваш профиль*",
        "nickname_label": "🏷 Никнейм",
        "game_label": "🕹 Игра",
        "rank_label": "🏆 Ранг",
        "role_label": "⚔️ Роль",
        "reg_start": "Давайте создадим ваш профиль!\n\nКак ваш игровой никнейм?",
        "reg_invalid_nick": "Пожалуйста, введите корректный никнейм (1-32 символа).",
        "reg_pick_game": "Отлично, *{nickname}*! Теперь выберите вашу основную игру:",
        "reg_pick_rank": "Хороший выбор — *{game}*!\n\nКакой у вас текущий ранг? (например: Золото, Платина, Global Elite — любой формат)",
        "reg_invalid_rank": "Пожалуйста, введите корректный ранг (1-32 символа).",
        "reg_pick_role": "Почти готово! Выберите предпочтительную роль:",
        "reg_saved": (
            "✅ *Профиль сохранён!*\n\n"
            "🏷 Никнейм: {nickname}\n"
            "🕹 Игра: {game}\n"
            "🏆 Ранг: {rank}\n"
            "⚔️ Роль: {role}\n\n"
            "Используйте /lfg для объявления LFG или /find для поиска игроков!"
        ),
        "reg_cancelled": "Регистрация отменена. Используйте /register для повторного запуска.",
        "lfg_need_profile": "Сначала нужен профиль! Используйте /register для его создания.",
        "lfg_prompt": (
            "📢 Публикация от имени *{nickname}* ({game} — {rank} — {role})\n\n"
            "Добавьте сообщение к объявлению или отправьте /skip, чтобы пропустить:"
        ),
        "lfg_too_long": "Сообщение слишком длинное (макс. 200 символов). Попробуйте снова или /skip:",
        "lfg_live": "✅ Ваше LFG-объявление опубликовано! Другие игроки найдут вас через /find.",
        "lfg_cancelled": "Публикация LFG отменена.",
        "find_prompt": "🔍 В какой игре вы ищете тиммейтов?",
        "find_all": "🔍 Все игры",
        "find_no_posts": "Активных LFG-объявлений для *{game}* не найдено.\n\nБудьте первым — используйте /lfg!",
        "find_title": "🔍 LFG — {game}",
        "find_title_all": "🔍 Все LFG-объявления",
        "find_players": "{count} игрок",
        "find_players_plural": "{count} игроков",
        "find_truncated": "_(список обрезан)_",
        "find_cancelled": "Поиск отменён.",
        "lang_changed": "✅ Язык установлен: Русский.",
    },
}


def t(key: str, lang: str, **kwargs) -> str:
    text = TRANSLATIONS.get(lang, TRANSLATIONS["en"]).get(key, TRANSLATIONS["en"].get(key, key))
    if kwargs:
        text = text.format(**kwargs)
    return text


def load_data() -> dict:
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"users": {}, "lfg_posts": []}


def save_data(data: dict) -> None:
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_user(user_id: int) -> dict | None:
    data = load_data()
    return data["users"].get(str(user_id))


def save_user(user_id: int, profile: dict) -> None:
    data = load_data()
    data["users"][str(user_id)] = profile
    save_data(data)


def get_lang(user_id: int, context: ContextTypes.DEFAULT_TYPE | None = None) -> str:
    if context and context.user_data.get("lang"):
        return context.user_data["lang"]
    user_profile = get_user(user_id)
    if user_profile and user_profile.get("lang"):
        return user_profile["lang"]
    return "en"


def set_lang(user_id: int, lang: str, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data["lang"] = lang
    data = load_data()
    uid = str(user_id)
    if uid not in data["users"]:
        data["users"][uid] = {}
    data["users"][uid]["lang"] = lang
    save_data(data)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    keyboard = [
        [
            InlineKeyboardButton("🇬🇧 English", callback_data="setlang:en"),
            InlineKeyboardButton("🇷🇺 Русский", callback_data="setlang:ru"),
        ]
    ]
    await update.message.reply_text(
        "🌐 Please select your language / Пожалуйста, выберите язык:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return SELECT_LANG


async def select_lang_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    lang = query.data.split(":", 1)[1]
    user_id = update.effective_user.id
    set_lang(user_id, lang, context)

    user = update.effective_user
    await query.edit_message_text(
        t("welcome", lang, name=user.first_name)
    )
    return ConversationHandler.END


async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    keyboard = [
        [
            InlineKeyboardButton("🇬🇧 English", callback_data="setlang:en"),
            InlineKeyboardButton("🇷🇺 Русский", callback_data="setlang:ru"),
        ]
    ]
    lang = get_lang(update.effective_user.id, context)
    await update.message.reply_text(
        t("lang_prompt", lang),
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return SELECT_LANG


async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    lang = get_lang(user_id, context)
    user_profile = get_user(user_id)
    if not user_profile:
        await update.message.reply_text(t("no_profile", lang))
        return

    text = (
        f"{t('your_profile', lang)}\n\n"
        f"{t('nickname_label', lang)}: {user_profile['nickname']}\n"
        f"{t('game_label', lang)}: {user_profile['game']}\n"
        f"{t('rank_label', lang)}: {user_profile['rank']}\n"
        f"{t('role_label', lang)}: {user_profile['role']}"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def register_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = get_lang(update.effective_user.id, context)
    await update.message.reply_text(t("reg_start", lang))
    return REG_NICKNAME


async def reg_nickname(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = get_lang(update.effective_user.id, context)
    nickname = update.message.text.strip()
    if not nickname or len(nickname) > 32:
        await update.message.reply_text(t("reg_invalid_nick", lang))
        return REG_NICKNAME

    context.user_data["reg_nickname"] = nickname

    keyboard = [[InlineKeyboardButton(g, callback_data=f"reg_game:{g}")] for g in GAMES]
    await update.message.reply_text(
        t("reg_pick_game", lang, nickname=nickname),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )
    return REG_GAME


async def reg_game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    lang = get_lang(update.effective_user.id, context)

    game = query.data.split(":", 1)[1]
    context.user_data["reg_game"] = game

    await query.edit_message_text(
        t("reg_pick_rank", lang, game=game),
        parse_mode="Markdown",
    )
    return REG_RANK


async def reg_rank(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = get_lang(update.effective_user.id, context)
    rank = update.message.text.strip()
    if not rank or len(rank) > 32:
        await update.message.reply_text(t("reg_invalid_rank", lang))
        return REG_RANK

    context.user_data["reg_rank"] = rank
    game = context.user_data["reg_game"]
    roles = ROLES.get(game, ROLES["Other"])

    keyboard = [[InlineKeyboardButton(r, callback_data=f"reg_role:{r}")] for r in roles]
    await update.message.reply_text(
        t("reg_pick_role", lang),
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return REG_ROLE


async def reg_role(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    lang = get_lang(update.effective_user.id, context)

    role = query.data.split(":", 1)[1]
    user_id = update.effective_user.id

    profile_data = {
        "nickname": context.user_data["reg_nickname"],
        "game": context.user_data["reg_game"],
        "rank": context.user_data["reg_rank"],
        "role": role,
        "user_id": user_id,
        "username": update.effective_user.username,
        "first_name": update.effective_user.first_name,
        "lang": lang,
    }
    save_user(user_id, profile_data)

    await query.edit_message_text(
        t(
            "reg_saved", lang,
            nickname=profile_data["nickname"],
            game=profile_data["game"],
            rank=profile_data["rank"],
            role=profile_data["role"],
        ),
        parse_mode="Markdown",
    )
    context.user_data.clear()
    context.user_data["lang"] = lang
    return ConversationHandler.END


async def reg_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = get_lang(update.effective_user.id, context)
    context.user_data.clear()
    await update.message.reply_text(t("reg_cancelled", lang))
    return ConversationHandler.END


async def lfg_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    lang = get_lang(user_id, context)
    user_profile = get_user(user_id)

    if not user_profile:
        await update.message.reply_text(t("lfg_need_profile", lang))
        return ConversationHandler.END

    await update.message.reply_text(
        t(
            "lfg_prompt", lang,
            nickname=user_profile["nickname"],
            game=user_profile["game"],
            rank=user_profile["rank"],
            role=user_profile["role"],
        ),
        parse_mode="Markdown",
    )
    return LFG_MESSAGE


async def lfg_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = get_lang(update.effective_user.id, context)
    msg_text = update.message.text.strip()
    if msg_text.startswith("/skip"):
        msg_text = ""
    elif len(msg_text) > 200:
        await update.message.reply_text(t("lfg_too_long", lang))
        return LFG_MESSAGE

    user_id = update.effective_user.id
    user_profile = get_user(user_id)

    data = load_data()
    data["lfg_posts"] = [p for p in data["lfg_posts"] if p["user_id"] != user_id]
    data["lfg_posts"].append({
        "user_id": user_id,
        "nickname": user_profile["nickname"],
        "game": user_profile["game"],
        "rank": user_profile["rank"],
        "role": user_profile["role"],
        "username": user_profile.get("username"),
        "first_name": user_profile.get("first_name"),
        "message": msg_text,
    })
    save_data(data)

    await update.message.reply_text(t("lfg_live", lang))
    return ConversationHandler.END


async def lfg_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = get_lang(update.effective_user.id, context)
    await update.message.reply_text(t("lfg_cancelled", lang))
    return ConversationHandler.END


async def find_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = get_lang(update.effective_user.id, context)
    keyboard = [[InlineKeyboardButton(g, callback_data=f"find_game:{g}")] for g in GAMES]
    keyboard.append([InlineKeyboardButton(t("find_all", lang), callback_data="find_game:all")])
    await update.message.reply_text(
        t("find_prompt", lang),
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return FIND_GAME


async def find_game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    lang = get_lang(update.effective_user.id, context)

    game_filter = query.data.split(":", 1)[1]
    user_id = update.effective_user.id
    data = load_data()

    if game_filter == "all":
        posts = data["lfg_posts"]
        title = t("find_title_all", lang)
    else:
        posts = [p for p in data["lfg_posts"] if p["game"] == game_filter]
        title = t("find_title", lang, game=game_filter)

    posts = [p for p in posts if p["user_id"] != user_id]

    if not posts:
        game_display = game_filter if game_filter != "all" else ("any game" if lang == "en" else "любой игры")
        await query.edit_message_text(
            t("find_no_posts", lang, game=game_display),
            parse_mode="Markdown",
        )
        return ConversationHandler.END

    count = len(posts)
    count_str = t("find_players_plural" if count != 1 else "find_players", lang, count=count)
    lines = [f"*{title}* ({count_str})\n"]

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

    await query.edit_message_text(text, parse_mode="Markdown")
    return ConversationHandler.END


async def find_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = get_lang(update.effective_user.id, context)
    await update.message.reply_text(t("find_cancelled", lang))
    return ConversationHandler.END


async def main() -> None:
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN environment variable is not set.")

    app = Application.builder().token(token).build()

    start_conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            SELECT_LANG: [CallbackQueryHandler(select_lang_callback, pattern=r"^setlang:")],
        },
        fallbacks=[],
    )

    language_conv = ConversationHandler(
        entry_points=[CommandHandler("language", language_command)],
        states={
            SELECT_LANG: [CallbackQueryHandler(select_lang_callback, pattern=r"^setlang:")],
        },
        fallbacks=[],
    )

    register_conv = ConversationHandler(
        entry_points=[CommandHandler("register", register_start)],
        states={
            REG_NICKNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_nickname)],
            REG_GAME: [CallbackQueryHandler(reg_game, pattern=r"^reg_game:")],
            REG_RANK: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_rank)],
            REG_ROLE: [CallbackQueryHandler(reg_role, pattern=r"^reg_role:")],
        },
        fallbacks=[CommandHandler("cancel", reg_cancel)],
    )

    lfg_conv = ConversationHandler(
        entry_points=[CommandHandler("lfg", lfg_start)],
        states={
            LFG_MESSAGE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, lfg_message),
                CommandHandler("skip", lfg_message),
            ],
        },
        fallbacks=[CommandHandler("cancel", lfg_cancel)],
    )

    find_conv = ConversationHandler(
        entry_points=[CommandHandler("find", find_start)],
        states={
            FIND_GAME: [CallbackQueryHandler(find_game, pattern=r"^find_game:")],
        },
        fallbacks=[CommandHandler("cancel", find_cancel)],
    )

    app.add_handler(start_conv)
    app.add_handler(language_conv)
    app.add_handler(CommandHandler("profile", profile))
    app.add_handler(register_conv)
    app.add_handler(lfg_conv)
    app.add_handler(find_conv)

    async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        if isinstance(context.error, Conflict):
            logger.warning("Conflict error — another instance may be running. Waiting 10s...")
            await asyncio.sleep(10)
        else:
            logger.error("Unhandled error:", exc_info=context.error)

    app.add_error_handler(error_handler)

    logger.info("Bot is starting...")
    await app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    asyncio.run(main())
