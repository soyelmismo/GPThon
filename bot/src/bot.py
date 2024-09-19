from re import escape
from telethon import functions, types, events, helpers
from bot.src.handlers.gateway import gateway
from bot.src.handlers.commands.tasks import cancel_callback, tasks_identifier
from asyncio import sleep

import bot.src.config as conf
from bot.src.logs import logger
from bot.src.handlers.commands.tasks import monitor_tasks
from bot.src.handlers.database import db
from bot.src import constants as c

try:
    from bot.src.tools.api_utils.model_indexer import models_grabber
    logger.info("Imported custom models.")
except ImportError:
    models_grabber = False
    logger.info("Any model can be set.")


async def register_events():
    logger.info("Adding commands...")
    commands_list = [
        types.BotCommand("ask", "💬")]
    
    
    conf.bot.add_event_handler(cancel_callback, events.CallbackQuery(pattern=f'^{tasks_identifier}'))

    conf.bot.add_event_handler(gateway, events.NewMessage(
    pattern = r'(^' + conf.command_chat + r'(@' + escape(conf.bot_data.username) + r')?(\s|$))' # type: ignore
    ))
    
    conf.bot.add_event_handler(gateway, events.NewMessage(
    pattern = r'(^/embed(@' + escape(conf.bot_data.username) + r')?(\s|$))' # type: ignore
    ))

    conf.bot.add_event_handler(gateway, events.NewMessage(
    pattern = r'(^/tts(@' + escape(conf.bot_data.username) + r')?(\s|$))' # type: ignore
    ))

    if c.whisper_models:
        commands_list.extend([types.BotCommand("stt", "🎤")])
        conf.bot.add_event_handler(gateway, events.NewMessage(pattern = '^' + conf.command_stt + r'(@' + escape(conf.bot_data.username) + r')?(\s|$)')) # type: ignore

    if c.img_models:
        commands_list.extend([types.BotCommand("img", "🎨")])
        conf.bot.add_event_handler(gateway, events.NewMessage(pattern = '^' + conf.command_image + r'(@' + escape(conf.bot_data.username) + r')?(\s|$)')) # type: ignore

    commands_list.extend([types.BotCommand("vision", "👁️")])
    conf.bot.add_event_handler(gateway, events.NewMessage(pattern = '^/vision(@' + escape(conf.bot_data.username) + r')?(\s|$)')) # type: ignore

    if conf.roleplay_enabled:
        commands_list.extend([types.BotCommand("rol", "🔞")])
        conf.bot.add_event_handler(gateway, events.NewMessage(pattern = '^/rol(@' + escape(conf.bot_data.username) + r')?(\s|$)')) # type: ignore


    conf.bot.add_event_handler(gateway, events.NewMessage(pattern = '^/select(@' + escape(conf.bot_data.username) + r')?(\s|$)')) # type: ignore
    conf.bot.add_event_handler(gateway, events.NewMessage(pattern = '^/retry(@' + escape(conf.bot_data.username) + r')?(\s|$)')) # type: ignore
    conf.bot.add_event_handler(gateway, events.NewMessage(pattern = '^/reset(@' + escape(conf.bot_data.username) + r')?(\s|$)')) # type: ignore
    conf.bot.add_event_handler(gateway, events.NewMessage(pattern = '^/burnme(@' + escape(conf.bot_data.username) + r')?(\s|$)')) # type: ignore
    conf.bot.add_event_handler(gateway, events.NewMessage(pattern = '^/help(@' + escape(conf.bot_data.username) + r')?(\s|$)')) # type: ignore
    conf.bot.add_event_handler(gateway, events.NewMessage(pattern = '(?s)^(?!/).*$'))

    

    commands_list.extend([
            types.BotCommand("select", "🖕"),
            types.BotCommand("burnme", "🔥"),
            types.BotCommand("retry", "🔄"),
            types.BotCommand("reset", "⏮️"),
            types.BotCommand("help", "☝️🤓"),

            ]
    )
    conf.bot.loop.create_task(conf.bot(functions.bots.SetBotCommandsRequest(
        scope = types.BotCommandScopeDefault(), 
        lang_code = '',
        commands = commands_list
    )))


async def post_init():

    db.initialize_redis()
    conf.bot.loop.create_task(db.flush_task())
    conf.bot.loop.create_task(monitor_tasks())
    if models_grabber:
        conf.bot.loop.create_task(models_grabber()) # type: ignore
        while c.not_yet_ready:
            logger.info("Waiting for models...")
            await sleep(1)
        logger.info("Initiated models!")

    await register_events()
    msg = "Bot running ✅"
    await conf.send_logs_to_channel(msg)
    logger.info(msg)


def start_bot():
    """Start the bot."""

    print('Current loop before post_init', id(helpers.get_running_loop()))
    print('Bot loop before post_init', id(conf.bot.loop))
    conf.bot.loop.run_until_complete(post_init())

    print('Current loop', id(helpers.get_running_loop()))
    print('Bot loop', id(conf.bot.loop))

    conf.bot.run_until_disconnected()
    logger.info("Closing")

