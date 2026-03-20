import asyncio
import logging
import sqlite3
from datetime import datetime
from typing import Dict, Optional, Tuple
import re

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes
)
from telegram.constants import ParseMode

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot Token
BOT_TOKEN = "8660234537:AAFt73-hJ58T8aip2q8wrAGGmdn-wZYmcLI"

# Database setup
def init_database():
    conn = sqlite3.connect('forward_bot.db')
    c = conn.cursor()
    
    # Create channels table
    c.execute('''CREATE TABLE IF NOT EXISTS channels
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  source_channel TEXT UNIQUE,
                  target_channel TEXT,
                  created_at TIMESTAMP)''')
    
    # Create forwarded messages table for history
    c.execute('''CREATE TABLE IF NOT EXISTS forwarded_messages
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  source_channel TEXT,
                  source_message_id INTEGER,
                  target_channel TEXT,
                  target_message_id INTEGER,
                  forwarded_at TIMESTAMP,
                  message_text TEXT)''')
    
    conn.commit()
    conn.close()

init_database()

# Helper Functions
def convert_to_small_caps(text: str) -> str:
    """Convert text to small caps style"""
    small_caps_map = {
        'a': 'ᴀ', 'b': 'ʙ', 'c': 'ᴄ', 'd': 'ᴅ', 'e': 'ᴇ', 'f': 'ғ', 'g': 'ɢ',
        'h': 'ʜ', 'i': 'ɪ', 'j': 'ᴊ', 'k': 'ᴋ', 'l': 'ʟ', 'm': 'ᴍ', 'n': 'ɴ',
        'o': 'ᴏ', 'p': 'ᴘ', 'q': 'ǫ', 'r': 'ʀ', 's': 's', 't': 'ᴛ', 'u': 'ᴜ',
        'v': 'ᴠ', 'w': 'ᴡ', 'x': 'x', 'y': 'ʏ', 'z': 'ᴢ',
        'A': 'ᴀ', 'B': 'ʙ', 'C': 'ᴄ', 'D': 'ᴅ', 'E': 'ᴇ', 'F': 'ғ', 'G': 'ɢ',
        'H': 'ʜ', 'I': 'ɪ', 'J': 'ᴊ', 'K': 'ᴋ', 'L': 'ʟ', 'M': 'ᴍ', 'N': 'ɴ',
        'O': 'ᴏ', 'P': 'ᴘ', 'Q': 'ǫ', 'R': 'ʀ', 'S': 's', 'T': 'ᴛ', 'U': 'ᴜ',
        'V': 'ᴠ', 'W': 'ᴡ', 'X': 'x', 'Y': 'ʏ', 'Z': 'ᴢ'
    }
    return ''.join(small_caps_map.get(char, char) for char in text)

def get_main_menu() -> InlineKeyboardMarkup:
    """Get main menu keyboard"""
    keyboard = [
        [
            InlineKeyboardButton("🔗 Connect Channel", callback_data="connect"),
            InlineKeyboardButton("🔌 Disconnect", callback_data="disconnect")
        ],
        [
            InlineKeyboardButton("📊 Status", callback_data="status"),
            InlineKeyboardButton("📜 History", callback_data="history")
        ],
        [
            InlineKeyboardButton("❓ Help", callback_data="help")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_connection_menu() -> InlineKeyboardMarkup:
    """Get connection setup menu"""
    keyboard = [
        [
            InlineKeyboardButton("📢 Source Channel", callback_data="set_source"),
            InlineKeyboardButton("🎯 Target Channel", callback_data="set_target")
        ],
        [
            InlineKeyboardButton("✅ Confirm Setup", callback_data="confirm_setup"),
            InlineKeyboardButton("🔙 Back", callback_data="back")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

# Bot Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command"""
    user = update.effective_user
    welcome_msg = f"""
✨ {convert_to_small_caps('Welcome to Message Forward Bot')} ✨

{convert_to_small_caps('Hello')} {user.first_name}! 👋

{convert_to_small_caps('I can help you forward messages between channels automatically!')}

📌 {convert_to_small_caps('How to use:')}
• {convert_to_small_caps('Add me as admin in both channels')}
• {convert_to_small_caps('Use connect option to setup channels')}
• {convert_to_small_caps('All messages will be forwarded automatically')}

{convert_to_small_caps('Use the buttons below to get started')} 🚀
    """
    
    await update.message.reply_text(
        welcome_msg,
        reply_markup=get_main_menu(),
        parse_mode=ParseMode.HTML
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle button callbacks"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "connect":
        # Store temporary data for connection setup
        context.user_data['setup_mode'] = 'connect'
        await query.edit_message_text(
            f"🔗 {convert_to_small_caps('Channel Connection Setup')}\n\n"
            f"{convert_to_small_caps('Please use the buttons below to set up your channels')}\n\n"
            f"⚠️ {convert_to_small_caps('Make sure I am admin in both channels before connecting!')}",
            reply_markup=get_connection_menu()
        )
    
    elif query.data == "set_source":
        context.user_data['setting'] = 'source'
        await query.edit_message_text(
            f"📢 {convert_to_small_caps('Set Source Channel')}\n\n"
            f"{convert_to_small_caps('Please forward any message from your source channel to me')}\n\n"
            f"{convert_to_small_caps('This will help me identify the channel')} 🔍",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="connect")]])
        )
    
    elif query.data == "set_target":
        context.user_data['setting'] = 'target'
        await query.edit_message_text(
            f"🎯 {convert_to_small_caps('Set Target Channel')}\n\n"
            f"{convert_to_small_caps('Please forward any message from your target channel to me')}\n\n"
            f"{convert_to_small_caps('Messages will be forwarded to this channel')} 📤",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="connect")]])
        )
    
    elif query.data == "confirm_setup":
        if 'source_channel' in context.user_data and 'target_channel' in context.user_data:
            source = context.user_data['source_channel']
            target = context.user_data['target_channel']
            
            # Save to database
            conn = sqlite3.connect('forward_bot.db')
            c = conn.cursor()
            try:
                c.execute(
                    "INSERT INTO channels (source_channel, target_channel, created_at) VALUES (?, ?, ?)",
                    (source, target, datetime.now())
                )
                conn.commit()
                await query.edit_message_text(
                    f"✅ {convert_to_small_caps('Connection Successful!')}\n\n"
                    f"📢 {convert_to_small_caps('Source:')} {source}\n"
                    f"🎯 {convert_to_small_caps('Target:')} {target}\n\n"
                    f"{convert_to_small_caps('Now all messages from source channel will be forwarded to target channel')} 🚀",
                    reply_markup=get_main_menu()
                )
            except sqlite3.IntegrityError:
                await query.edit_message_text(
                    f"⚠️ {convert_to_small_caps('Connection already exists!')}\n\n"
                    f"{convert_to_small_caps('Please disconnect existing connection first')}",
                    reply_markup=get_main_menu()
                )
            finally:
                conn.close()
        else:
            await query.edit_message_text(
                f"❌ {convert_to_small_caps('Please set both channels first!')}",
                reply_markup=get_connection_menu()
            )
    
    elif query.data == "disconnect":
        conn = sqlite3.connect('forward_bot.db')
        c = conn.cursor()
        c.execute("DELETE FROM channels")
        conn.commit()
        conn.close()
        
        # Clear user data
        context.user_data.clear()
        
        await query.edit_message_text(
            f"🔌 {convert_to_small_caps('Disconnected Successfully!')}\n\n"
            f"{convert_to_small_caps('All channel connections have been removed')}",
            reply_markup=get_main_menu()
        )
    
    elif query.data == "status":
        conn = sqlite3.connect('forward_bot.db')
        c = conn.cursor()
        c.execute("SELECT source_channel, target_channel FROM channels LIMIT 1")
        result = c.fetchone()
        conn.close()
        
        if result:
            status_msg = f"""
📊 {convert_to_small_caps('Bot Status')} 📊

✅ {convert_to_small_caps('Status:')} {convert_to_small_caps('Active')}
📢 {convert_to_small_caps('Source Channel:')} {result[0]}
🎯 {convert_to_small_caps('Target Channel:')} {result[1]}
🔄 {convert_to_small_caps('Forwarding:')} {convert_to_small_caps('Enabled')}

{convert_to_small_caps('Bot is actively forwarding messages')} 🚀
            """
        else:
            status_msg = f"""
⚠️ {convert_to_small_caps('Bot Status')} ⚠️

{convert_to_small_caps('Status:')} {convert_to_small_caps('Inactive')}
{convert_to_small_caps('No channels connected')}

{convert_to_small_caps('Use connect button to setup channels')} 🔗
            """
        
        await query.edit_message_text(status_msg, reply_markup=get_main_menu())
    
    elif query.data == "history":
        conn = sqlite3.connect('forward_bot.db')
        c = conn.cursor()
        c.execute(
            "SELECT source_channel, target_channel, forwarded_at, message_text FROM forwarded_messages ORDER BY forwarded_at DESC LIMIT 10"
        )
        messages = c.fetchall()
        conn.close()
        
        if messages:
            history_text = f"📜 {convert_to_small_caps('Forward History')} 📜\n\n"
            for i, msg in enumerate(messages, 1):
                history_text += f"{i}. 📅 {msg[2][:19]}\n"
                history_text += f"   📢 {convert_to_small_caps('From:')} {msg[0]}\n"
                history_text += f"   🎯 {convert_to_small_caps('To:')} {msg[1]}\n"
                if msg[3]:
                    preview = msg[3][:50] + "..." if len(msg[3]) > 50 else msg[3]
                    history_text += f"   💬 {preview}\n"
                history_text += "\n"
        else:
            history_text = f"📜 {convert_to_small_caps('No messages forwarded yet')} 📜\n\n{convert_to_small_caps('Messages will appear here once forwarding starts')}"
        
        await query.edit_message_text(history_text, reply_markup=get_main_menu())
    
    elif query.data == "help":
        help_msg = f"""
❓ {convert_to_small_caps('Help & Instructions')} ❓

{convert_to_small_caps('How to setup:')}

1️⃣ {convert_to_small_caps('Add bot as admin in both channels')}
2️⃣ {convert_to_small_caps('Click Connect button')}
3️⃣ {convert_to_small_caps('Set source channel (forward a message)')}
4️⃣ {convert_to_small_caps('Set target channel (forward a message)')}
5️⃣ {convert_to_small_caps('Confirm setup')}

{convert_to_small_caps('Features:')}
• ✅ {convert_to_small_caps('Automatic message forwarding')}
• 📊 {convert_to_small_caps('Real-time status checking')}
• 📜 {convert_to_small_caps('Forward history tracking')}
• 🔌 {convert_to_small_caps('Easy disconnect option')}

{convert_to_small_caps('Commands:')}
/start - {convert_to_small_caps('Start the bot')}
/status - {convert_to_small_caps('Check bot status')}
/history - {convert_to_small_caps('View forward history')}
/help - {convert_to_small_caps('Show this help')}

{convert_to_small_caps('Need help? Contact @')}
        """
        await query.edit_message_text(help_msg, reply_markup=get_main_menu())
    
    elif query.data == "back":
        await query.edit_message_text(
            f"✨ {convert_to_small_caps('Welcome back')} ✨\n\n{convert_to_small_caps('Choose an option below')}",
            reply_markup=get_main_menu()
        )

async def handle_forwarded_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle forwarded messages for channel setup"""
    if 'setting' in context.user_data:
        forwarded_msg = update.message.forward_from_chat
        
        if forwarded_msg:
            channel_id = f"@{forwarded_msg.username}" if forwarded_msg.username else str(forwarded_msg.id)
            
            if context.user_data['setting'] == 'source':
                context.user_data['source_channel'] = channel_id
                await update.message.reply_text(
                    f"✅ {convert_to_small_caps('Source channel set to:')} {channel_id}\n\n"
                    f"{convert_to_small_caps('Now set your target channel')} 🎯",
                    reply_markup=get_connection_menu()
                )
                context.user_data['setting'] = None
            
            elif context.user_data['setting'] == 'target':
                context.user_data['target_channel'] = channel_id
                await update.message.reply_text(
                    f"✅ {convert_to_small_caps('Target channel set to:')} {channel_id}\n\n"
                    f"{convert_to_small_caps('Click confirm to complete setup')} ✅",
                    reply_markup=get_connection_menu()
                )
                context.user_data['setting'] = None

async def forward_messages(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Forward messages from source to target channel"""
    # Check if message is from a channel
    if update.channel_post:
        message = update.channel_post
        chat_id = message.chat_id
        
        # Get connected channels
        conn = sqlite3.connect('forward_bot.db')
        c = conn.cursor()
        c.execute("SELECT source_channel, target_channel FROM channels LIMIT 1")
        result = c.fetchone()
        
        if result:
            source_channel = result[0]
            target_channel = result[1]
            
            # Check if message is from source channel
            source_id = source_channel.replace('@', '')
            if str(chat_id).endswith(source_id) or f"@{message.chat.username}" == source_channel:
                try:
                    # Forward the message
                    forwarded = await message.copy(
                        chat_id=target_channel,
                        caption=message.caption if message.caption else None
                    )
                    
                    # Save to history
                    message_text = message.caption or message.text or ""
                    c.execute(
                        "INSERT INTO forwarded_messages (source_channel, source_message_id, target_channel, target_message_id, forwarded_at, message_text) VALUES (?, ?, ?, ?, ?, ?)",
                        (source_channel, message.message_id, target_channel, forwarded.message_id, datetime.now(), message_text[:500])
                    )
                    conn.commit()
                    
                    logger.info(f"Forwarded message {message.message_id} to {target_channel}")
                    
                except Exception as e:
                    logger.error(f"Failed to forward message: {e}")
        
        conn.close()

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /status command"""
    conn = sqlite3.connect('forward_bot.db')
    c = conn.cursor()
    c.execute("SELECT source_channel, target_channel FROM channels LIMIT 1")
    result = c.fetchone()
    conn.close()
    
    if result:
        status_msg = f"""
📊 {convert_to_small_caps('Bot Status')} 📊

✅ {convert_to_small_caps('Status:')} {convert_to_small_caps('Active')}
📢 {convert_to_small_caps('Source:')} {result[0]}
🎯 {convert_to_small_caps('Target:')} {result[1]}
🔄 {convert_to_small_caps('Forwarding:')} {convert_to_small_caps('Enabled')}
        """
    else:
        status_msg = f"""
⚠️ {convert_to_small_caps('Bot Status')} ⚠️

{convert_to_small_caps('Status:')} {convert_to_small_caps('Inactive')}
{convert_to_small_caps('No channels connected')}
        """
    
    await update.message.reply_text(status_msg, reply_markup=get_main_menu())

async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /history command"""
    conn = sqlite3.connect('forward_bot.db')
    c = conn.cursor()
    c.execute(
        "SELECT source_channel, target_channel, forwarded_at FROM forwarded_messages ORDER BY forwarded_at DESC LIMIT 10"
    )
    messages = c.fetchall()
    conn.close()
    
    if messages:
        history_text = f"📜 {convert_to_small_caps('Forward History')} 📜\n\n"
        for i, msg in enumerate(messages, 1):
            history_text += f"{i}. 📅 {msg[2][:19]}\n   📢 {msg[0]} → 🎯 {msg[1]}\n\n"
    else:
        history_text = f"📜 {convert_to_small_caps('No messages forwarded yet')} 📜"
    
    await update.message.reply_text(history_text)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command"""
    help_msg = f"""
❓ {convert_to_small_caps('Help & Instructions')} ❓

{convert_to_small_caps('Commands:')}
/start - {convert_to_small_caps('Start the bot')}
/status - {convert_to_small_caps('Check status')}
/history - {convert_to_small_caps('View history')}
/help - {convert_to_small_caps('Show help')}

{convert_to_small_caps('Setup Guide:')}
1️⃣ {convert_to_small_caps('Add bot as admin in both channels')}
2️⃣ {convert_to_small_caps('Click Connect button')}
3️⃣ {convert_to_small_caps('Forward a message from source channel')}
4️⃣ {convert_to_small_caps('Forward a message from target channel')}
5️⃣ {convert_to_small_caps('Confirm connection')}
    """
    await update.message.reply_text(help_msg, reply_markup=get_main_menu())

def main():
    """Main function to run the bot"""
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("history", history_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.FORWARDED, handle_forwarded_message))
    application.add_handler(MessageHandler(filters.ChatType.CHANNEL, forward_messages))
    
    # Start the bot
    print("🤖 Bot is starting...")
    print("✅ Bot is now running!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
