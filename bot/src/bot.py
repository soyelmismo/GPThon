import bot.src.config as c
from re import escape
from asyncio import create_task, sleep
from telethon import functions, types, events
from bot.src.logs import logger
from bot.src.handlers.gateway import gateway
from bot.src.handlers.commands.tasks import monitor_tasks, cancel_callback, tasks_identifier
from bot.src.handlers.database import db

try:
    from bot.src.tools.api_utils.model_indexer import models_grabber
    logger.info("Imported custom models.")
except ImportError:
    models_grabber = False
    logger.info("Any model can be set.")


async def post_init():
    
    await db.initialize_redis()
    c.bot.loop.create_task(db.flush_task())
    c.bot.loop.create_task(monitor_tasks())
    if models_grabber:
        c.bot.loop.create_task(models_grabber()) # type: ignore

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

    c.bot.loop.create_task(c.bot(functions.bots.SetBotCommandsRequest(
        scope = types.BotCommandScopeDefault(), 
        lang_code = '',
        commands = commands_list
    )))
    msg = "Bot running ✅"
    c.bot.loop.create_task(c.send_logs_to_channel(msg))
    logger.info(msg)

async def main():
    """Start the bot."""
    c.bot.add_event_handler(cancel_callback, events.CallbackQuery(pattern=f'^{tasks_identifier}'))

    c.bot.add_event_handler(gateway, events.NewMessage(
    pattern = r'(^' + c.command_chat + r'(@' + escape(c.bot_data.username) + r')?(\s|$))' # type: ignore
    ))

    if c.roleplay_enabled:
        c.bot.add_event_handler(gateway, events.NewMessage(pattern = '^/rol(@' + escape(c.bot_data.username) + r')?(\s|$)')) # type: ignore


    c.bot.add_event_handler(gateway, events.NewMessage(pattern = '^' + c.command_stt + r'(@' + escape(c.bot_data.username) + r')?(\s|$)')) # type: ignore

    c.bot.add_event_handler(gateway, events.NewMessage(pattern = '^/vision(@' + escape(c.bot_data.username) + r')?(\s|$)')) # type: ignore
    c.bot.add_event_handler(gateway, events.NewMessage(pattern = '^' + c.command_image + r'(@' + escape(c.bot_data.username) + r')?(\s|$)')) # type: ignore
    c.bot.add_event_handler(gateway, events.NewMessage(pattern = '^/select(@' + escape(c.bot_data.username) + r')?(\s|$)')) # type: ignore
    c.bot.add_event_handler(gateway, events.NewMessage(pattern = '^/retry(@' + escape(c.bot_data.username) + r')?(\s|$)')) # type: ignore
    c.bot.add_event_handler(gateway, events.NewMessage(pattern = '^/reset(@' + escape(c.bot_data.username) + r')?(\s|$)')) # type: ignore
    c.bot.add_event_handler(gateway, events.NewMessage(pattern = '^/burnme(@' + escape(c.bot_data.username) + r')?(\s|$)')) # type: ignore
    c.bot.add_event_handler(gateway, events.NewMessage(pattern = '^/help(@' + escape(c.bot_data.username) + r')?(\s|$)')) # type: ignore
    c.bot.add_event_handler(gateway, events.NewMessage(pattern = '(?s)^(?!/).*$'))
    await post_init()
    await c.bot.run_until_disconnected()

def start_bot():
    c.bot.loop.run_until_complete(main())
    logger.info("Closing")
    