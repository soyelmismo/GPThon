import bot.src.constants as c
from re import escape
from asyncio import create_task
from telethon import functions, types, events
from bot.src.logs import logger
from bot.src.handlers.gateway import gateway
from bot.src.handlers.tasks import monitor_tasks, cancel_callback, tasks_identifier
from bot.src.tools.tg_tools import send_large_message

try:
    from bot.src.tools.api_utils.model_indexer import models_grabber
    logger.info("Imported custom models.")
except ImportError:
    models_grabber = False
    logger.info("Any model can be set.")


async def post_init():
    create_task(monitor_tasks())
    if models_grabber:
        create_task(models_grabber())

    logger.info("Adding commands...")
    commands_list = [
        types.BotCommand("ask", "💬"),
        types.BotCommand("stt", "🎤"),
        types.BotCommand("img", "🎨"),
        types.BotCommand("vision", "👁️"),
    ]
    if c.roleplay_enabled:
        commands_list.append(types.BotCommand("rol", "🔞"))
    
    commands_list.extend([types.BotCommand("select", "🖕"),
            types.BotCommand("burnme", "🔥"),
            types.BotCommand("retry", "🔄"),
            types.BotCommand("reset", "⏮️"),
            types.BotCommand("help", "☝️🤓"),

            ]
    )

    create_task(c.bot(functions.bots.SetBotCommandsRequest(
        scope = types.BotCommandScopeDefault(), 
        lang_code = '',
        commands = commands_list
    )))
    msg = "Bot running ✅"
    create_task(send_large_message(msg))
    logger.info(msg)

def main():
    """Start the bot."""

    c.bot.add_event_handler(cancel_callback, events.CallbackQuery(pattern=f'^{tasks_identifier}'))

    c.bot.add_event_handler(gateway, events.NewMessage(
    pattern = r'(^' + c.command_chat + r'(@' + escape(c.bot_data.username) + r')?(\s|$))'
    ))

    if c.roleplay_enabled:
        c.bot.add_event_handler(gateway, events.NewMessage(pattern = '^/rol(@' + escape(c.bot_data.username) + r')?(\s|$)'))


    c.bot.add_event_handler(gateway, events.NewMessage(pattern = '^' + c.command_stt + r'(@' + escape(c.bot_data.username) + r')?(\s|$)'))

    c.bot.add_event_handler(gateway, events.NewMessage(pattern = '^/vision(@' + escape(c.bot_data.username) + r')?(\s|$)'))
    c.bot.add_event_handler(gateway, events.NewMessage(pattern = '^' + c.command_image + r'(@' + escape(c.bot_data.username) + r')?(\s|$)'))
    c.bot.add_event_handler(gateway, events.NewMessage(pattern = '^/select(@' + escape(c.bot_data.username) + r')?(\s|$)'))
    c.bot.add_event_handler(gateway, events.NewMessage(pattern = '^/retry(@' + escape(c.bot_data.username) + r')?(\s|$)'))
    c.bot.add_event_handler(gateway, events.NewMessage(pattern = '^/reset(@' + escape(c.bot_data.username) + r')?(\s|$)'))
    c.bot.add_event_handler(gateway, events.NewMessage(pattern = '^/burnme(@' + escape(c.bot_data.username) + r')?(\s|$)'))
    c.bot.add_event_handler(gateway, events.NewMessage(pattern = '^/help(@' + escape(c.bot_data.username) + r')?(\s|$)'))
    c.bot.add_event_handler(gateway, events.NewMessage(pattern = '(?s)^(?!/).*$'))
    c.bot.loop.run_until_complete(post_init())

    c.bot.run_until_disconnected()
