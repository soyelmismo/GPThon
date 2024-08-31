from re import escape
from asyncio import create_task
from telethon import functions, types, events
from bot.src.logs import logger
import bot.src.constants as constants
import bot.src.config as conf
import bot.src.handlers.commands.userclass as userclass
from bot.src.handlers.commands.ask_mains import gateway
from bot.src.tools import send_large_message

try:
    from bot.src.tools.api_utils.model_indexer import models_grabber
    logger.info("Imported custom models.")
except ImportError:
    models_grabber = False
    logger.info("Any model can be set.")


async def post_init():
    
    userclass.beauty_list = {
        "False": list(conf.openai_style_apis['apis_normal.json'].keys()),
        "True": list(conf.openai_style_apis["apis_roleplay.json"].keys()),
        "Whisper": [key for key, value in conf.openai_style_apis['apis_normal.json'].items() if len(value) == 3]
        }

    if models_grabber:
        await models_grabber()

    logger.info("Adding commands...")
    commands_list = [
        types.BotCommand("ask", "💬"),
        types.BotCommand("stt", "🎤"),
        types.BotCommand("img", "🎨"),
        types.BotCommand("vision", "👁️"),
    ]
    if constants.roleplay_enabled:
        commands_list.append(types.BotCommand("rol", "🔞"))
    
    commands_list.extend([types.BotCommand("select", "🖕"),
            types.BotCommand("burnme", "🔥"),
            types.BotCommand("retry", "🔄"),
            types.BotCommand("reset", "⏮️"),
            ]
    )

    create_task(constants.bot(functions.bots.SetBotCommandsRequest(
        scope = types.BotCommandScopeDefault(), 
        lang_code = '',
        commands = commands_list
    )))
    msg = "Bot running ✅"
    create_task(send_large_message(msg))
    logger.info(msg)

def main():
    """Start the bot."""
    constants.bot.add_event_handler(gateway, events.NewMessage(pattern = r'(^@' + escape(constants.bot_data.username) + r')|(^/ask(@' + escape(constants.bot_data.username) + r')?(\s|$))'))

    if constants.roleplay_enabled:
        constants.bot.add_event_handler(gateway, events.NewMessage(pattern = f'^/rol(@' + escape(constants.bot_data.username) + r')?(\s|$)'))

    constants.bot.add_event_handler(gateway, events.NewMessage(pattern = f'^/img(@' + escape(constants.bot_data.username) + r')?(\s|$)'))
    constants.bot.add_event_handler(gateway, events.NewMessage(pattern = f'^/vision(@' + escape(constants.bot_data.username) + r')?(\s|$)'))
    constants.bot.add_event_handler(gateway, events.NewMessage(pattern = f'^/stt(@' + escape(constants.bot_data.username) + r')?(\s|$)'))
    constants.bot.add_event_handler(gateway, events.NewMessage(pattern = f'^/select(@' + escape(constants.bot_data.username) + r')?(\s|$)'))
    constants.bot.add_event_handler(gateway, events.NewMessage(pattern = f'^/retry(@' + escape(constants.bot_data.username) + r')?(\s|$)'))
    constants.bot.add_event_handler(gateway, events.NewMessage(pattern = f'^/reset(@' + escape(constants.bot_data.username) + r')?(\s|$)'))
    constants.bot.add_event_handler(gateway, events.NewMessage(pattern = f'^/burnme(@' + escape(constants.bot_data.username) + r')?(\s|$)'))
    constants.bot.add_event_handler(gateway, events.NewMessage(pattern = '(?s)^(?!/).*$'))
    constants.bot.loop.run_until_complete(post_init())

    constants.bot.run_until_disconnected()
