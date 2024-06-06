from telethon import TelegramClient
from .config import api_id, api_hash, bot_token, session_name, roleplay_enabled
bot = TelegramClient(session_name, api_id, api_hash).start(bot_token=bot_token)
bot.parse_mode = 'md'
bot_data = bot.loop.run_until_complete(bot.get_me())
index_user_instances = {}
