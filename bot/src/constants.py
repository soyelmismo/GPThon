from telethon import TelegramClient
from bot.src.config import (
    api_id, api_hash, bot_token,
    session_name, error_report_channel_id,  # noqa: F401
    error_report_channel_thread, roleplay_enabled,  # noqa: F401
    bot_name, img_styles, img_styles_txt, styles_str,  # noqa: F401
    command_stt, command_image, command_chat,  # noqa: F401
    text_improve_model, bot_prompts  # noqa: F401
)

chat_models = {}
models_txt = ""
img_models = {}
img_models_txt = ""
whisper_models = {}

allowed_chat_mimetypes = ["plain", "javascript"]
allowed_image_mimetypes = ["jpeg", "webp"]


bot = TelegramClient(session_name, api_id, api_hash).start(bot_token=bot_token)
bot.parse_mode = 'md'
bot_data = bot.loop.run_until_complete(bot.get_me())
index_user_instances = {}
index_group_instances = {}
