from re import escape
from asyncio import create_task
from telethon import functions, types, events
from bot.src.logs import logger
from bot.src.constants import bot, bot_data, roleplay_enabled
from bot.src.handlers.commands.ask_mains import gateway



async def post_init():

    logger.info("Adding commands...")
    commands_list = [
        types.BotCommand("ask", "💬"),
        types.BotCommand("stt", "🎤"),
    ]
    if roleplay_enabled:
        commands_list.append(types.BotCommand("rol", "🔞"))
    
    commands_list.extend([types.BotCommand("select", "🖕"),
            types.BotCommand("retry", "🔄"),
            types.BotCommand("reset", "⏮️"),]
    )

    create_task(bot(functions.bots.SetBotCommandsRequest(
        scope = types.BotCommandScopeDefault(), 
        lang_code = '',
        commands = commands_list
    )))
    logger.info("Bot running ✅")

def main():

    """Start the bot."""
    bot.add_event_handler(gateway, events.NewMessage(pattern = f'^/ask(@' + escape(bot_data.username) + r')?(\s|$)'))
    bot.add_event_handler(gateway, events.NewMessage(pattern = f'^/stt(@' + escape(bot_data.username) + r')?(\s|$)'))
    bot.add_event_handler(gateway, events.NewMessage(pattern = f'^/rol(@' + escape(bot_data.username) + r')?(\s|$)'))
    bot.add_event_handler(gateway, events.NewMessage(pattern = f'^/select(@' + escape(bot_data.username) + r')?(\s|$)'))
    bot.add_event_handler(gateway, events.NewMessage(pattern = f'^/retry(@' + escape(bot_data.username) + r')?(\s|$)'))
    bot.add_event_handler(gateway, events.NewMessage(pattern = f'^/reset(@' + escape(bot_data.username) + r')?(\s|$)'))
    bot.add_event_handler(gateway, events.NewMessage(pattern = '(?s)^(?!/).*$'))
    bot.loop.run_until_complete(post_init())
    
    bot.run_until_disconnected()
