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

GAMES = ["CS2", "Valorant", "Dota 2", "Fortnite", "Other"]

ROLES = {
    "CS2": ["Entry Fragger", "AWPer", "Support", "Lurker", "IGL", "Any"],
    "Valorant": ["Duelist", "Controller", "Initiator", "Sentinel", "Flex", "Any"],
    "Dota 2": ["Carry", "Mid", "Offlane", "Soft Support", "Hard Support", "Any"],
    "Fortnite": ["Fragger", "Builder", "Support", "Any"],
    "Other": ["DPS", "Tank", "Healer", "Support", "Flex", "Any"],
}

REG_NICKNAME, REG_GAME, REG_RANK, REG_ROLE = range(4)
LFG_MESSAGE = 10
FIND_GAME = 20


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


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    text = (
        f"👋 Welcome to the Gaming Teammate Finder, {user.first_name}!\n\n"
        "Use these commands:\n"
        "• /register — Create or update your profile\n"
        "• /profile — View your current profile\n"
        "• /lfg — Post a Looking For Group ad\n"
        "• /find — Browse players by game\n"
    )
    await update.message.reply_text(text)


async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    user_profile = get_user(user_id)
    if not user_profile:
        await update.message.reply_text(
            "You don't have a profile yet. Use /register to create one!"
        )
        return

    text = (
        f"🎮 *Your Profile*\n\n"
        f"🏷 Nickname: {user_profile['nickname']}\n"
        f"🕹 Game: {user_profile['game']}\n"
        f"🏆 Rank: {user_profile['rank']}\n"
        f"⚔️ Role: {user_profile['role']}"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def register_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Let's set up your profile!\n\nWhat's your in-game nickname?"
    )
    return REG_NICKNAME


async def reg_nickname(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    nickname = update.message.text.strip()
    if not nickname or len(nickname) > 32:
        await update.message.reply_text("Please enter a valid nickname (1-32 characters).")
        return REG_NICKNAME

    context.user_data["reg_nickname"] = nickname

    keyboard = [[InlineKeyboardButton(g, callback_data=f"reg_game:{g}")] for g in GAMES]
    await update.message.reply_text(
        f"Nice, *{nickname}*! Now pick your main game:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )
    return REG_GAME


async def reg_game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    game = query.data.split(":", 1)[1]
    context.user_data["reg_game"] = game

    await query.edit_message_text(
        f"Great choice — *{game}*!\n\nWhat's your current rank? (e.g. Gold, Platinum, Global Elite — anything works)",
        parse_mode="Markdown",
    )
    return REG_RANK


async def reg_rank(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    rank = update.message.text.strip()
    if not rank or len(rank) > 32:
        await update.message.reply_text("Please enter a valid rank (1-32 characters).")
        return REG_RANK

    context.user_data["reg_rank"] = rank
    game = context.user_data["reg_game"]
    roles = ROLES.get(game, ROLES["Other"])

    keyboard = [[InlineKeyboardButton(r, callback_data=f"reg_role:{r}")] for r in roles]
    await update.message.reply_text(
        "Almost done! Choose your preferred role:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return REG_ROLE


async def reg_role(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

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
    }
    save_user(user_id, profile_data)

    await query.edit_message_text(
        f"✅ *Profile saved!*\n\n"
        f"🏷 Nickname: {profile_data['nickname']}\n"
        f"🕹 Game: {profile_data['game']}\n"
        f"🏆 Rank: {profile_data['rank']}\n"
        f"⚔️ Role: {profile_data['role']}\n\n"
        "Use /lfg to post a Looking For Group ad, or /find to browse players!",
        parse_mode="Markdown",
    )
    context.user_data.clear()
    return ConversationHandler.END


async def reg_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text("Registration cancelled. Use /register to start again.")
    return ConversationHandler.END


async def lfg_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    user_profile = get_user(user_id)

    if not user_profile:
        await update.message.reply_text(
            "You need a profile first! Use /register to set one up."
        )
        return ConversationHandler.END

    await update.message.reply_text(
        f"📢 Posting as *{user_profile['nickname']}* ({user_profile['game']} — {user_profile['rank']} — {user_profile['role']})\n\n"
        "Add an optional message for your LFG post, or send /skip to post without one:",
        parse_mode="Markdown",
    )
    return LFG_MESSAGE


async def lfg_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    msg_text = update.message.text.strip()
    if msg_text.startswith("/skip"):
        msg_text = ""
    elif len(msg_text) > 200:
        await update.message.reply_text("Message too long (max 200 characters). Try again or /skip:")
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

    await update.message.reply_text(
        "✅ Your LFG ad is live! Other players can find you with /find."
    )
    return ConversationHandler.END


async def lfg_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("LFG post cancelled.")
    return ConversationHandler.END


async def find_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    keyboard = [[InlineKeyboardButton(g, callback_data=f"find_game:{g}")] for g in GAMES]
    keyboard.append([InlineKeyboardButton("🔍 All Games", callback_data="find_game:all")])
    await update.message.reply_text(
        "🔍 Which game are you looking for teammates in?",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return FIND_GAME


async def find_game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    game_filter = query.data.split(":", 1)[1]
    user_id = update.effective_user.id
    data = load_data()

    if game_filter == "all":
        posts = data["lfg_posts"]
        title = "🔍 All LFG Posts"
    else:
        posts = [p for p in data["lfg_posts"] if p["game"] == game_filter]
        title = f"🔍 LFG Posts — {game_filter}"

    posts = [p for p in posts if p["user_id"] != user_id]

    if not posts:
        await query.edit_message_text(
            f"No active LFG posts found for *{game_filter if game_filter != 'all' else 'any game'}*.\n\n"
            "Be the first — use /lfg to post your own!",
            parse_mode="Markdown",
        )
        return ConversationHandler.END

    lines = [f"*{title}* ({len(posts)} player{'s' if len(posts) != 1 else ''})\n"]
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
        text = text[:3990] + "\n\n_(list truncated)_"

    await query.edit_message_text(text, parse_mode="Markdown")
    return ConversationHandler.END


async def find_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Browse cancelled.")
    return ConversationHandler.END


def main() -> None:
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN environment variable is not set.")

    app = Application.builder().token(token).build()

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

    app.add_handler(CommandHandler("start", start))
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
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
