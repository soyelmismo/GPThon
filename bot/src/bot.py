from re import escape
from asyncio import create_task
from telethon import functions, types, events
from json import load
from pathlib import Path
import os
from bot.src.logs import logger
import bot.src.constants as constants#, roleplay_enabled, 
import bot.src.handlers.commands.userclass as userclass
from bot.src.handlers.commands.ask_mains import gateway

try:
    from bot.src.tools.api_utils.model_indexer import models_grabber
    logger.info("Imported custom models.")
except ImportError:
    models_grabber = False
    logger.info("Any model can be set.")


async def post_init():
    from bot.src.config import openai_style_apis
    basepath = Path(__file__).resolve().parents[1]
    logger.debug(f'Base path: {basepath}')
    apis_files = os.listdir(Path(f'{basepath}/resources/apis'))
    logger.debug(f'apis_files: {basepath}')
    available_api_json_files = [file for file in apis_files if file.endswith(".json")]
    for fetcher in available_api_json_files:
        with open(basepath / "resources" / "apis" / fetcher, "r", encoding="utf-8") as infile:
            openai_style_apis[fetcher] = load(infile)

    userclass.beauty_list = {
        "False": list(openai_style_apis['apis_normal.json'].keys()),
        #"True": list(openai_style_apis["apis_roleplay.json"].keys()),
        "Whisper": [key for key, value in openai_style_apis['apis_normal.json'].items() if len(value) == 3]
        }

    if models_grabber:
        await models_grabber(openai_style_apis)

    logger.info("Adding commands...")
    commands_list = [
        types.BotCommand("ask", "💬"),
        types.BotCommand("stt", "🎤"),
        types.BotCommand("vision", "👁️"),
    ]
    #if roleplay_enabled:
    #    commands_list.append(types.BotCommand("rol", "🔞"))
    
    commands_list.extend([types.BotCommand("select", "🖕"),
            types.BotCommand("retry", "🔄"),
            types.BotCommand("burnme", "🔥"),
            types.BotCommand("reset", "⏮️"),
            ]
    )

    create_task(constants.bot(functions.bots.SetBotCommandsRequest(
        scope = types.BotCommandScopeDefault(), 
        lang_code = '',
        commands = commands_list
    )))
    logger.info("Bot running ✅")

def main():
    """Start the bot."""
    constants.bot.add_event_handler(gateway, events.NewMessage(pattern = f'^/ask(@' + escape(constants.bot_data.username) + r')?(\s|$)'))
    constants.bot.add_event_handler(gateway, events.NewMessage(pattern = f'^/vision(@' + escape(constants.bot_data.username) + r')?(\s|$)'))
    constants.bot.add_event_handler(gateway, events.NewMessage(pattern = f'^/stt(@' + escape(constants.bot_data.username) + r')?(\s|$)'))
    constants.bot.add_event_handler(gateway, events.NewMessage(pattern = f'^/rol(@' + escape(constants.bot_data.username) + r')?(\s|$)'))
    constants.bot.add_event_handler(gateway, events.NewMessage(pattern = f'^/select(@' + escape(constants.bot_data.username) + r')?(\s|$)'))
    constants.bot.add_event_handler(gateway, events.NewMessage(pattern = f'^/retry(@' + escape(constants.bot_data.username) + r')?(\s|$)'))
    constants.bot.add_event_handler(gateway, events.NewMessage(pattern = f'^/reset(@' + escape(constants.bot_data.username) + r')?(\s|$)'))
    constants.bot.add_event_handler(gateway, events.NewMessage(pattern = f'^/burnme(@' + escape(constants.bot_data.username) + r')?(\s|$)'))
    constants.bot.add_event_handler(gateway, events.NewMessage(pattern = '(?s)^(?!/).*$'))
    constants.bot.loop.run_until_complete(post_init())
    
    constants.bot.run_until_disconnected()
