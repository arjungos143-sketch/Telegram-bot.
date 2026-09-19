import os
import re
import logging
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ==========================================
# CONFIGURATION
# ==========================================

BOT_TOKEN = os.getenv("BOT_TOKEN", "8911694656:AAESxvckaZILUPQAz_Qj2Kwgp1hqJOSq8pg")

# Apna Telegram numeric User ID yahan add karo
OWNER_ID = int(os.getenv("OWNER_ID", "8543712705"))

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# Temporary request state
user_states = {}

# ==========================================
# KEYBOARDS
# ==========================================

def main_menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔗 Submit Post", callback_data="submit")
        ],
        [
            InlineKeyboardButton("📖 How It Works", callback_data="help"),
            InlineKeyboardButton("👤 Profile", callback_data="profile")
        ],
        [
            InlineKeyboardButton("📞 Support", callback_data="support")
        ],
    ])


def admin_menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📊 Bot Status", callback_data="status")
        ],
        [
            InlineKeyboardButton("📋 Pending Requests", callback_data="requests")
        ],
        [
            InlineKeyboardButton("🏠 Main Menu", callback_data="home")
        ],
    ])


def admin_request_buttons(user_id, request_id):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "✅ Approve",
                callback_data=f"approve_{request_id}"
            ),
            InlineKeyboardButton(
                "❌ Reject",
                callback_data=f"reject_{request_id}"
            ),
        ]
    ])


# ==========================================
# WELCOME + USER DP
# ==========================================

async def send_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    text = (
        f"👋 Welcome {user.first_name}!\n\n"
        "🤖 Channel Post Management Bot\n\n"
        "🔗 Submit your channel post link\n"
        "📋 Your request will be sent to the admin\n\n"
        "👇 Choose an option:"
    )

    try:
        photos = await context.bot.get_user_profile_photos(
            user_id=user.id,
            limit=1
        )

        if photos.total_count > 0:
            photo = photos.photos[0][-1].file_id

            await update.message.reply_photo(
                photo=photo,
                caption=text,
                reply_markup=main_menu()
            )
            return

    except Exception:
        logging.exception("Could not load profile photo")

    await update.message.reply_text(
        text,
        reply_markup=main_menu()
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_welcome(update, context)


# ==========================================
# ADMIN COMMAND
# ==========================================

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    if user.id != OWNER_ID:
        await update.message.reply_text("⛔ Access Denied")
        return

    await update.message.reply_text(
        "👑 OWNER ADMIN PANEL\n\n"
        "Manage incoming post requests below.",
        reply_markup=admin_menu()
    )


# ==========================================
# BUTTON HANDLER
# ==========================================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    user = query.from_user
    data = query.data

    if data == "home":
        await query.edit_message_text(
            "🏠 Main Menu",
            reply_markup=main_menu()
        )

    elif data == "submit":

        user_states[user.id] = {
            "step": "link"
        }

        await query.edit_message_text(
            "🔗 Send your channel post link.\n\n"
            "Example:\n"
            "https://t.me/yourchannel/123\n\n"
            "Send /cancel to stop."
        )

    elif data == "help":

        await query.edit_message_text(
            "📖 HOW IT WORKS\n\n"
            "1️⃣ Submit your channel post link\n"
            "2️⃣ Enter your requested quantity\n"
            "3️⃣ Admin receives your request\n"
            "4️⃣ Admin can approve or reject\n\n"
            "⚠️ This bot does not create fake reactions "
            "or automate multiple accounts.",
            reply_markup=main_menu()
        )

    elif data == "profile":

        await query.edit_message_text(
            f"👤 PROFILE\n\n"
            f"Name: {user.full_name}\n"
            f"User ID: {user.id}",
            reply_markup=main_menu()
        )

    elif data == "support":

        await query.edit_message_text(
            "📞 Contact the bot owner for support.",
            reply_markup=main_menu()
        )

    elif data == "status":

        if user.id != OWNER_ID:
            return

        await query.edit_message_text(
            "📊 BOT STATUS\n\n"
            "🟢 Bot is running\n"
            "☁️ Hosting: Render\n"
            "🛡️ Request management: Active",
            reply_markup=admin_menu()
        )

    elif data == "requests":

        if user.id != OWNER_ID:
            return

        await query.edit_message_text(
            "📋 Pending requests are delivered directly "
            "to this admin chat.\n\n"
            "Use the Approve / Reject buttons on each request.",
            reply_markup=admin_menu()
        )

    elif data.startswith("approve_"):

        if user.id != OWNER_ID:
            return

        request_id = data.replace("approve_", "")

        await query.edit_message_text(
            f"✅ Request #{request_id} marked for approval.\n\n"
            "Please handle any permitted reaction activity "
            "manually through Telegram."
        )

    elif data.startswith("reject_"):

        if user.id != OWNER_ID:
            return

        request_id = data.replace("reject_", "")

        await query.edit_message_text(
            f"❌ Request #{request_id} rejected."
        )


# ==========================================
# MESSAGE HANDLER
# ==========================================

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user
    text = update.message.text.strip()

    if text == "/cancel":
        user_states.pop(user.id, None)

        await update.message.reply_text(
            "❌ Request cancelled.",
            reply_markup=main_menu()
        )
        return

    state = user_states.get(user.id)

    if not state:
        return

    # Step 1: Post link
    if state["step"] == "link":

        if not re.match(r"^https?://t\.me/", text):
            await update.message.reply_text(
                "❌ Please send a valid Telegram post link."
            )
            return

        state["link"] = text
        state["step"] = "quantity"

        await update.message.reply_text(
            "🔢 Enter requested quantity.\n\n"
            "Example: 15\n"
            "Minimum: 1\n"
            "Maximum: 100"
        )
        return

    # Step 2: Quantity
    if state["step"] == "quantity":

        if not text.isdigit():
            await update.message.reply_text(
                "❌ Enter a valid number."
            )
            return

        quantity = int(text)

        if quantity < 1 or quantity > 100:
            await update.message.reply_text(
                "❌ Quantity must be between 1 and 100."
            )
            return

        link = state["link"]
        request_id = f"{user.id}_{update.message.message_id}"

        admin_text = (
            "📩 NEW POST REQUEST\n\n"
            f"🆔 Request: {request_id}\n"
            f"👤 User: {user.full_name}\n"
            f"🔢 Quantity: {quantity}\n"
            f"🔗 Post Link: {link}\n\n"
            "⚠️ Manual review required."
        )

        try:

            await context.bot.send_message(
                chat_id=OWNER_ID,
                text=admin_text,
                reply_markup=admin_request_buttons(
                    user.id,
                    request_id
                )
            )

            await update.message.reply_text(
                "✅ Request submitted successfully!\n\n"
                "👑 Admin has received your request.",
                reply_markup=main_menu()
            )

        except Exception:

            logging.exception("Could not send request to admin")

            await update.message.reply_text(
                "❌ Unable to send request. Please try again later."
            )

        user_states.pop(user.id, None)


# ==========================================
# ERROR HANDLER
# ==========================================

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logging.error("Update error: %s", context.error)


# ==========================================
# MAIN
# ==========================================

def main():

    if BOT_TOKEN == "PASTE_YOUR_BOT_TOKEN_HERE":
        raise ValueError("Please configure BOT_TOKEN")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_command))

    app.add_handler(CallbackQueryHandler(button_handler))

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            message_handler
        )
    )

    app.add_error_handler(error_handler)

    print("🤖 Bot started successfully!")

    app.run_polling()


if __name__ == "__main__":
    main()
