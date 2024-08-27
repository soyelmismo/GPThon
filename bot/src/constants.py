from telethon import TelegramClient
from bot.src.config import api_id, api_hash, bot_token, session_name, error_report_channel_id, error_report_channel_thread#, roleplay_enabled

models_dict = {}
models_txt = ""

bot = TelegramClient(session_name, api_id, api_hash).start(bot_token=bot_token)
bot.parse_mode = 'md'
bot_data = bot.loop.run_until_complete(bot.get_me())
index_user_instances = {}
