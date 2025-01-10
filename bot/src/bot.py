from bot.src.handlers.gateway import gateway, cancel_callback
from bot.src.handlers.tasks import tasks_identifier, monitor_tasks
from bot.src.handlers import database as rdb
from bot.src.tools.api_utils.api_selector import api_rate_limiter_task
from bot.src.logs import logger
from bot.src import constants as c
from bot.src import config as conf
try:
    from bot.src.tools.api_utils.model_indexer import models_grabber
    logger.info("Imported models grabber.")
except ImportError:
    models_grabber = False
    logger.info("Any model can be set.")

from re import escape
from asyncio import sleep
from telethon import TelegramClient
from telethon.functions import bots
from telethon.tl.types import MessageEntityBlockquote
from telethon.events import CallbackQuery, NewMessage
from telethon.types import BotCommand, BotCommandScopeDefault
from telethon.extensions.markdown import DEFAULT_DELIMITERS
DEFAULT_DELIMITERS['%%'] = lambda *a, **k: MessageEntityBlockquote(*a, **k, collapsed=True)

async def register_events():
    logger.info("Adding commands...")
    commands_list = [
        BotCommand("ask", "💬")]

    conf.bot.add_event_handler(cancel_callback, CallbackQuery(pattern=f'^{tasks_identifier}'))

    conf.bot.add_event_handler(gateway, NewMessage(
    pattern = r'(^' + conf.command_chat + r'(@' + escape(conf.bot_data.username) + r')?(\s|$))' # type: ignore
    ))

    conf.bot.add_event_handler(gateway, NewMessage(
    pattern = r'(^/embed(@' + escape(conf.bot_data.username) + r')?(\s|$))' # type: ignore
    ))

    if c.session_default_tts_model:
        conf.bot.add_event_handler(gateway, NewMessage(
        pattern = r'(^' + conf.command_tts + r'(@' + escape(conf.bot_data.username) + r')?(\s|$))' # type: ignore
        ))

    if c.whisper_models:
        commands_list.extend([BotCommand("stt", "🎤")])
        conf.bot.add_event_handler(gateway, NewMessage(pattern = '^' + conf.command_stt + r'(@' + escape(conf.bot_data.username) + r')?(\s|$)')) # type: ignore

    if c.img_models:
        commands_list.extend([BotCommand("img", "🎨")])
        conf.bot.add_event_handler(gateway, NewMessage(pattern = '^' + conf.command_image + r'(@' + escape(conf.bot_data.username) + r')?(\s|$)')) # type: ignore

    commands_list.extend([BotCommand("vision", "👁️")])
    conf.bot.add_event_handler(gateway, NewMessage(pattern = '^/vision(@' + escape(conf.bot_data.username) + r')?(\s|$)')) # type: ignore

    if conf.roleplay_enabled:
        commands_list.extend([BotCommand("rol", "🔞")])
        conf.bot.add_event_handler(gateway, NewMessage(pattern = '^/rol(@' + escape(conf.bot_data.username) + r')?(\s|$)')) # type: ignore


    conf.bot.add_event_handler(gateway, NewMessage(pattern = '^/select(@' + escape(conf.bot_data.username) + r')?(\s|$)')) # type: ignore
    conf.bot.add_event_handler(gateway, NewMessage(pattern = '^/retry(@' + escape(conf.bot_data.username) + r')?(\s|$)')) # type: ignore
    conf.bot.add_event_handler(gateway, NewMessage(pattern = '^/reset(@' + escape(conf.bot_data.username) + r')?(\s|$)')) # type: ignore
    #conf.bot.add_event_handler(gateway, NewMessage(pattern = '^/burnme(@' + escape(conf.bot_data.username) + r')?(\s|$)')) # type: ignore
    conf.bot.add_event_handler(gateway, NewMessage(pattern = '^/help(@' + escape(conf.bot_data.username) + r')?(\s|$)')) # type: ignore
    conf.bot.add_event_handler(gateway, NewMessage(pattern = '(?s)^(?!/).*$'))

    

    commands_list.extend([
            BotCommand("select", "🖕"),
            #BotCommand("burnme", "🔥"),
            BotCommand("retry", "🔄"),
            BotCommand("reset", "⏮️"),
            BotCommand("help", "☝️🤓"),

            ]
    )
    await conf.bot(bots.SetBotCommandsRequest(
        scope = BotCommandScopeDefault(), 
        lang_code = '',
        commands = commands_list
    ))

async def post_init():
    conf.bot_data = await conf.bot.get_me()
    conf.bot_mention = f"@{conf.bot_data.username}"
    rdb.start_db()
    await rdb.db.initialize_valkey()
    conf.bot._loop.create_task(rdb.db.flush_task())
    conf.bot._loop.create_task(monitor_tasks())
    conf.bot._loop.create_task(api_rate_limiter_task())
    if models_grabber:
        conf.bot._loop.create_task(models_grabber()) # type: ignore
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

    conf.bot = TelegramClient(
        conf.session_name, conf.api_id,
        conf.api_hash, connection_retries=-1
    ).start(bot_token=conf.bot_token)
    conf.bot.parse_mode = 'md'
    
    conf.bot.loop.run_until_complete(post_init())

    #conf.bot.loop.run_forever()
    conf.bot.run_until_disconnected()

    #await conf.bot.run_until_disconnected()
    conf.bot.loop.run_until_complete(rdb.db.flush_task(force = 1))
    logger.info("Closing")
